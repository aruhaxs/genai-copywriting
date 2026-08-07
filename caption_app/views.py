import os
import time
import hashlib
import requests
import urllib.parse
import io
import base64
import json
from PIL import Image
import google.generativeai as genai

from django.shortcuts import render, redirect
from django.urls import reverse
from django.core.files.storage import FileSystemStorage
from django.core.files.base import ContentFile
from django.contrib import messages
from django.conf import settings
from django.http import JsonResponse

from .models import GayaCopywriting, PengaturanAPI, BidangUsaha

# Versi Graph API Meta diseragamkan
GRAPH_API_VERSION = "v25.0"
GRAPH_BASE_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


# ==========================================
# HELPER: MENDAPATKAN PENGATURAN DENGAN PRIORITAS .ENV
# ==========================================
def get_config():
    """
    Mengambil konfigurasi aplikasi.
    PRIORITAS:
    1. os.getenv() (.env file)
    2. Database PengaturanAPI (Fallback jika .env kosong)
    3. Default value
    """
    db_config = PengaturanAPI.objects.first()
    
    def fetch_val(db_attr, env_key, default=""):
        # 1. Cek .env terlebih dahulu
        env_val = os.getenv(env_key, "").strip()
        if env_val:
            return env_val
            
        # 2. Fallback ke Database jika .env kosong
        if db_config and getattr(db_config, db_attr, None):
            db_val = getattr(db_config, db_attr).strip()
            if db_val:
                return db_val
                
        # 3. Fallback ke default value
        return default

    class ConfigWrapper:
        pass

    config = ConfigWrapper()
    config.db_obj = db_config
    
    config.fb_app_id = fetch_val('fb_app_id', 'FB_APP_ID')
    config.fb_app_secret = fetch_val('fb_app_secret', 'FB_APP_SECRET')
    config.ig_account_id = fetch_val('ig_account_id', 'IG_ACCOUNT_ID')
    config.ig_access_token = fetch_val('ig_access_token', 'IG_ACCESS_TOKEN')
    
    config.gemini_api_key = fetch_val('gemini_api_key', 'GEMINI_API_KEY')
    config.gemini_model = fetch_val('gemini_model', 'GEMINI_MODEL', 'gemini-2.5-flash')
    
    config.groq_api_key = fetch_val('groq_api_key', 'GROQ_API_KEY')
    config.groq_model = fetch_val('groq_model', 'GROQ_MODEL', 'llama-3.3-70b-versatile')
    
    config.cloudinary_creds = fetch_val('cloudinary_creds', 'CLOUDINARY_CREDS')
    
    # Prioritas AI Provider dari .env terlebih dahulu
    env_ai_provider = os.getenv('AI_PROVIDER', '').strip()
    if env_ai_provider:
        config.ai_provider = env_ai_provider
    elif db_config and hasattr(db_config, 'ai_provider') and db_config.ai_provider:
        config.ai_provider = db_config.ai_provider
    else:
        config.ai_provider = 'gemini'

    return config


def update_env_file(key, value):
    env_path = os.path.join(settings.BASE_DIR, '.env')
    if not os.path.exists(env_path):
        with open(env_path, 'w', encoding='utf-8') as f:
            f.write(f"{key}={value}\n")
        return

    lines = []
    key_updated = False
    with open(env_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines = []
    for line in lines:
        if line.strip().startswith(f"{key}="):
            new_lines.append(f"{key}={value}\n")
            key_updated = True
        else:
            new_lines.append(line)

    if not key_updated:
        new_lines.append(f"{key}={value}\n")

    with open(env_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)


def save_access_token_to_db_and_env(access_token, ig_account_id=None):
    pengaturan, _ = PengaturanAPI.objects.get_or_create(id=1)
    pengaturan.ig_access_token = access_token
    if ig_account_id:
        pengaturan.ig_account_id = ig_account_id
    pengaturan.save()

    update_env_file("IG_ACCESS_TOKEN", access_token)
    if ig_account_id:
        update_env_file("IG_ACCOUNT_ID", ig_account_id)


# ==========================================
# META OAUTH & TOKEN MANAGEMENT
# ==========================================
def verify_and_upgrade_token(config):
    if not config.fb_app_id or not config.fb_app_secret:
        return config.ig_access_token
        
    app_id = config.fb_app_id
    app_secret = config.fb_app_secret
    current_token = config.ig_access_token
    
    debug_url = f"https://graph.facebook.com/debug_token?input_token={current_token}&access_token={app_id}|{app_secret}"
    try:
        debug_res = requests.get(debug_url, timeout=10).json()
        data = debug_res.get('data', {})
        
        if data.get('is_valid') and data.get('type') == 'PAGE' and data.get('expires_at') == 0:
            return current_token 
            
        if not data.get('is_valid'):
            raise Exception("Token kedaluwarsa. Silakan Klik 'Login Facebook' untuk memperbarui token.")
            
    except Exception as e:
        if "kedaluwarsa" in str(e):
            raise e

    url_long = f"{GRAPH_BASE_URL}/oauth/access_token?grant_type=fb_exchange_token&client_id={app_id}&client_secret={app_secret}&fb_exchange_token={current_token}"
    res_long = requests.get(url_long, timeout=15).json()
    
    if 'error' in res_long:
        raise Exception(f"Gagal Upgrade Token (Langkah 1): {res_long['error']['message']}")
        
    long_lived_token = res_long['access_token']
    
    url_page = f"{GRAPH_BASE_URL}/me/accounts?fields=instagram_business_account,access_token&access_token={long_lived_token}"
    res_page = requests.get(url_page, timeout=15).json()
    
    if 'error' in res_page:
        raise Exception(f"Gagal Upgrade Token (Langkah 2): {res_page['error']['message']}")
        
    target_ig_id = str(config.ig_account_id) if config.ig_account_id else ""
    for page in res_page.get('data', []):
        ig_account = page.get('instagram_business_account', {})
        if str(ig_account.get('id')) == target_ig_id:
            permanent_token = page.get('access_token')
            save_access_token_to_db_and_env(permanent_token, target_ig_id)
            return permanent_token
            
    if res_page.get('data'):
        permanent_token = res_page['data'][0]['access_token']
        save_access_token_to_db_and_env(permanent_token)
        return permanent_token
        
    raise Exception("Tidak menemukan Halaman Facebook yang terhubung ke Instagram.")


def facebook_login(request):
    config = get_config()
    if not config.fb_app_id:
        messages.error(request, "⚠️ GAGAL: FB App ID belum diisi di .env maupun di Admin!")
        return redirect('/')

    redirect_uri = request.build_absolute_uri(reverse('facebook_callback'))
    if redirect_uri.startswith('http://'):
        redirect_uri = redirect_uri.replace('http://', 'https://', 1)

    scope = "instagram_basic,instagram_content_publish,pages_show_list,pages_read_engagement"
    
    fb_auth_url = (
        f"https://www.facebook.com/{GRAPH_API_VERSION}/dialog/oauth?"
        f"client_id={config.fb_app_id}&"
        f"redirect_uri={urllib.parse.quote(redirect_uri)}&"
        f"scope={scope}&"
        f"response_type=code"
    )
    return redirect(fb_auth_url)


def facebook_callback(request):
    code = request.GET.get('code')
    error_reason = request.GET.get('error_description') or request.GET.get('error_message')

    if error_reason or not code:
        messages.error(request, f"❌ GAGAL OTORISASI: {error_reason or 'Pengguna membatalkan login.'}")
        return redirect('/')

    config = get_config()
    redirect_uri = request.build_absolute_uri(reverse('facebook_callback'))
    if redirect_uri.startswith('http://'):
        redirect_uri = redirect_uri.replace('http://', 'https://', 1)

    try:
        # 1. Tukar 'code' dengan Short-Lived Access Token
        token_url = (
            f"{GRAPH_BASE_URL}/oauth/access_token?"
            f"client_id={config.fb_app_id}&"
            f"redirect_uri={redirect_uri}&"
            f"client_secret={config.fb_app_secret}&"
            f"code={code}"
        )
        res_token = requests.get(token_url, timeout=15).json()
        if 'error' in res_token:
            raise Exception(res_token['error']['message'])

        short_lived_token = res_token['access_token']

        # 2. Tukar menjadi Long-Lived User Token
        long_url = (
            f"{GRAPH_BASE_URL}/oauth/access_token?"
            f"grant_type=fb_exchange_token&"
            f"client_id={config.fb_app_id}&"
            f"client_secret={config.fb_app_secret}&"
            f"fb_exchange_token={short_lived_token}"
        )
        res_long = requests.get(long_url, timeout=15).json()
        if 'error' in res_long:
            raise Exception(res_long['error']['message'])

        long_lived_token = res_long['access_token']

        # 3. Ambil Permanent Page Access Token
        page_url = f"{GRAPH_BASE_URL}/me/accounts?fields=instagram_business_account,access_token&access_token={long_lived_token}"
        res_page = requests.get(page_url, timeout=15).json()
        if 'error' in res_page:
            raise Exception(res_page['error']['message'])

        selected_page_token = None
        target_ig_id = config.ig_account_id if config.ig_account_id else None

        for page in res_page.get('data', []):
            ig_account = page.get('instagram_business_account', {})
            page_ig_id = str(ig_account.get('id', ''))

            if target_ig_id and page_ig_id == target_ig_id:
                selected_page_token = page.get('access_token')
                break
            elif not target_ig_id and page_ig_id:
                selected_page_token = page.get('access_token')
                target_ig_id = page_ig_id
                break

        if not selected_page_token and res_page.get('data'):
            selected_page_token = res_page['data'][0].get('access_token')

        if not selected_page_token:
            raise Exception("Tidak ada Halaman Facebook terhubung dengan Instagram Business yang ditemukan.")

        save_access_token_to_db_and_env(selected_page_token, target_ig_id)

        # SIMPAN TOKEN KE SESSION UNTUK TESTING DI UI
        request.session['debug_token_info'] = {
            'short_lived_token': short_lived_token,
            'long_lived_token': long_lived_token,
            'permanent_page_token': selected_page_token,
            'ig_account_id': target_ig_id
        }

        messages.success(request, "🎉 SUKSES! Access Token berhasil didapatkan dan disinkronkan!")

    except Exception as e:
        messages.error(request, f"❌ GAGAL MEMPERBARUI TOKEN: {str(e)}")

    return redirect('/admin/caption_app/pengaturanapi/1/change/#otorisasi-metadata-facebook-tab')


# ==========================================
# MAIN APP VIEW: GENERATE CAPTION & POST IG
# ==========================================
def generate_caption(request):
    daftar_gaya = GayaCopywriting.objects.all()
    daftar_bidang = BidangUsaha.objects.prefetch_related('fields').all()
    config = get_config()

    if request.method == 'POST':
        for bidang in daftar_bidang:
            for field in bidang.fields.all():
                field.submitted_value = request.POST.get(field.name_attribute, '')

    context = {
        'daftar_gaya': daftar_gaya,
        'daftar_bidang': daftar_bidang,
        'config': config
    }

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'post_ig':
            final_caption = request.POST.get('final_caption')
            image_urls_json = request.POST.get('image_urls', '[]')
            
            try:
                raw_image_urls = json.loads(image_urls_json)
            except Exception:
                raw_image_urls = []

            if not raw_image_urls or len(raw_image_urls) == 0:
                context['error_ig'] = "PENTING: Sistem Instagram tidak mengizinkan postingan teks saja. Anda wajib menggunakan gambar."
                context['hasil_caption'] = final_caption
                return render(request, 'index.html', context)
            
            try:
                if not config.ig_access_token or not config.ig_account_id:
                    raise ValueError("Token Instagram atau ID Akun tidak ditemukan! Silakan klik 'Login dengan Facebook'.")
                
                ig_access_token = verify_and_upgrade_token(config)
                ig_account_id = config.ig_account_id
                
                if not config.cloudinary_creds:
                    raise ValueError("Kredensial Cloudinary belum diisi di .env/Admin!")

                api_kunci_gabungan = config.cloudinary_creds.strip()
                if "," not in api_kunci_gabungan:
                    raise ValueError("Format CLOUDINARY_CREDS salah! Gunakan: CloudName,APIKey,APISecret")
                
                kredensial = api_kunci_gabungan.split(',')
                if len(kredensial) != 3:
                    raise ValueError("Format CLOUDINARY_CREDS tidak lengkap!")
                
                cloud_name = kredensial[0].strip()
                cloudinary_api_key = kredensial[1].strip()
                cloudinary_api_secret = kredensial[2].strip()

                fs = FileSystemStorage()
                trusted_image_urls = []

                for raw_url in raw_image_urls:
                    filename = raw_url.split('/')[-1].split('?')[0]
                    
                    timestamp = str(int(time.time()))
                    string_to_sign = f"timestamp={timestamp}{cloudinary_api_secret}"
                    signature = hashlib.sha1(string_to_sign.encode('utf-8')).hexdigest()

                    payload = {
                        'api_key': cloudinary_api_key,
                        'timestamp': timestamp,
                        'signature': signature
                    }
                    
                    with fs.open(filename, "rb") as file_obj:
                        cloudinary_response = requests.post(
                            f"https://api.cloudinary.com/v1_1/{cloud_name}/image/upload",
                            data=payload,
                            files={"file": file_obj},
                            timeout=20
                        )
                    
                    cloud_res_json = cloudinary_response.json()
                    if not cloudinary_response.ok:
                        err_msg = cloud_res_json.get('error', {}).get('message', 'Ditolak oleh Cloudinary.')
                        raise Exception(f"Gagal mengunggah ke Cloudinary: {err_msg}")
                    
                    trusted_image_urls.append(cloud_res_json['secure_url'])

                # Mengunggah Single / Carousel ke Instagram Graph API
                if len(trusted_image_urls) == 1:
                    container_payload = {
                        'image_url': trusted_image_urls[0],
                        'caption': final_caption,
                        'access_token': ig_access_token
                    }
                    container_req = requests.post(f"{GRAPH_BASE_URL}/{ig_account_id}/media", data=container_payload, timeout=20)
                    container_res = container_req.json()
                    
                    if 'error' in container_res:
                        raise Exception(f"Gagal membuat kontainer IG: {container_res['error']['message']}")
                    
                    creation_id = container_res['id']
                else:
                    children_ids = []
                    for t_url in trusted_image_urls:
                        item_payload = {
                            'image_url': t_url,
                            'is_carousel_item': 'true',
                            'access_token': ig_access_token
                        }
                        item_req = requests.post(f"{GRAPH_BASE_URL}/{ig_account_id}/media", data=item_payload, timeout=20)
                        item_res = item_req.json()
                        if 'error' in item_res:
                            raise Exception(f"Gagal membuat item carousel: {item_res['error']['message']}")
                        children_ids.append(item_res['id'])
                    
                    carousel_payload = {
                        'media_type': 'CAROUSEL',
                        'children': ','.join(children_ids),
                        'caption': final_caption,
                        'access_token': ig_access_token
                    }
                    carousel_req = requests.post(f"{GRAPH_BASE_URL}/{ig_account_id}/media", data=carousel_payload, timeout=20)
                    carousel_res = carousel_req.json()
                    if 'error' in carousel_res:
                        raise Exception(f"Gagal merakit Carousel IG: {carousel_res['error']['message']}")
                    
                    creation_id = carousel_res['id']

                publish_payload = {
                    'creation_id': creation_id,
                    'access_token': ig_access_token
                }
                publish_req = requests.post(f"{GRAPH_BASE_URL}/{ig_account_id}/media_publish", data=publish_payload, timeout=20)
                publish_res = publish_req.json()
                
                if 'error' in publish_res:
                    raise Exception(f"Gagal mempublikasikan ke IG: {publish_res['error']['message']}")
                
                context['success_msg'] = "🎉 Sukses! Postingan Anda berhasil diunggah ke Instagram!"
                
            except Exception as e:
                context['error_ig'] = str(e)
                context['hasil_caption'] = final_caption
                context['image_urls_json'] = image_urls_json
                context['image_urls'] = raw_image_urls 

        elif action in ['generate', 'regenerate']:
            bidang = request.POST.get('bidang')
            gaya_id = request.POST.get('gaya')
            
            cropped_images_json_str = request.POST.get('cropped_images_json', '[]')
            existing_image_urls_json = request.POST.get('image_urls', '[]')

            uploaded_file_urls = []

            if bidang and gaya_id:
                try:
                    if action == 'generate':
                        cropped_images_data = json.loads(cropped_images_json_str)
                        if not cropped_images_data or len(cropped_images_data) == 0:
                            raise Exception("Harap unggah minimal 1 gambar terlebih dahulu untuk memulai!")
                        
                        fs = FileSystemStorage()
                        for idx, img_b64 in enumerate(cropped_images_data):
                            if img_b64.strip() != "":
                                format, imgstr = img_b64.split(';base64,')
                                image_data = base64.b64decode(imgstr)
                                img = Image.open(io.BytesIO(image_data))
                                
                                if img.mode != 'RGB':
                                    img = img.convert('RGB')
                                    
                                img_io = io.BytesIO()
                                img.save(img_io, format='JPEG', quality=90)
                                img_io.seek(0)
                                
                                meta_safe_filename = f"igready_post_{int(time.time())}_{idx}.jpg"
                                filename = fs.save(meta_safe_filename, ContentFile(img_io.read()))
                                uploaded_file_urls.append(request.build_absolute_uri(fs.url(filename)))

                    elif action == 'regenerate':
                        uploaded_file_urls = json.loads(existing_image_urls_json)
                        if not uploaded_file_urls:
                            raise Exception("Data gambar hilang, silakan mulai ulang proses.")

                except Exception as e:
                    context['error'] = str(e)

            if len(uploaded_file_urls) > 0 and not context.get('error'):
                nama_model = ""
                provider = config.ai_provider
                
                try:
                    context['image_urls'] = uploaded_file_urls
                    context['image_urls_json'] = json.dumps(uploaded_file_urls)
                    
                    gaya_terpilih = GayaCopywriting.objects.get(id=gaya_id)

                    detail_info = ""
                    for key, value in request.POST.items():
                        if key not in ['csrfmiddlewaretoken', 'bidang', 'gaya', 'action', 'image_urls', 'final_caption', 'gambar', 'cropped_images_json'] and value.strip() != "":
                            label = key.replace('_', ' ').title()
                            detail_info += f"- {label}: {value}\n"

                    prompt = f"Sebagai seorang copywriter yang bekerja di Bagian Humas Kecamatan Mojoroto, Kota Kediri, buat caption Instagram menarik untuk kategori konten {bidang}.\n\n"
                    prompt += f"Detail info:\n{detail_info}\n\nInstruksi Gaya:\n{gaya_terpilih.prompt}\n\n"
                    prompt += "Berikan SATU hasil akhir caption saja (tidak perlu alternatif). Jangan pakai teks struktur [HEADER]. Berikan call-to-action dan hashtag. PENTING: JANGAN gunakan format markdown seperti bintang (**) untuk menebalkan teks, berikan teks polos biasa tanpa simbol bintang."

                    hasil_raw = ""

                    if provider == 'gemini':
                        if not config.gemini_api_key:
                            raise Exception("API Key Gemini tidak ditemukan di .env/Admin!")

                        # Konfigurasi API Key untuk SDK lama
                        genai.configure(api_key=config.gemini_api_key)
                        
                        nama_model = config.gemini_model.replace('models/', '').strip()
                        
                        # Inisialisasi GenerativeModel (sintaks SDK lama)
                        model = genai.GenerativeModel(nama_model)
                        response = model.generate_content(prompt)
                        hasil_raw = response.text

                    elif provider == 'groq':
                        if not config.groq_api_key:
                            raise Exception("API Key Groq tidak ditemukan di .env/Admin!")
                        
                        nama_model = config.groq_model
                        
                        headers = {
                            "Authorization": f"Bearer {config.groq_api_key}",
                            "Content-Type": "application/json"
                        }
                        payload = {
                            "model": nama_model,
                            "messages": [
                                {"role": "system", "content": "Anda adalah spesialis Social Media Copywriter."},
                                {"role": "user", "content": prompt}
                            ]
                        }
                        
                        res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
                        res_json = res.json()
                        
                        if not res.ok:
                            raise Exception(res_json.get('error', {}).get('message', 'Error pada server Groq.'))
                            
                        hasil_raw = res_json['choices'][0]['message']['content']

                    context['hasil_caption'] = hasil_raw.replace('**', '')

                except Exception as e:
                    context['error'] = f"Gagal menghasilkan caption ({provider.upper()} - Model: {nama_model}): {str(e)}"

    return render(request, 'index.html', context)