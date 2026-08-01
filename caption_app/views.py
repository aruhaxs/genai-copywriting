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
from django.shortcuts import render
from django.core.files.storage import FileSystemStorage
from django.core.files.base import ContentFile
from django.utils.text import get_valid_filename
from .models import GayaCopywriting, PengaturanAPI, BidangUsaha

def generate_caption(request):
    daftar_gaya = GayaCopywriting.objects.all()
    daftar_bidang = BidangUsaha.objects.prefetch_related('fields').all()
    pengaturan = PengaturanAPI.objects.first()

    # Simpan nilai form dinamis ke memori agar tidak hilang
    if request.method == 'POST':
        for bidang in daftar_bidang:
            for field in bidang.fields.all():
                field.submitted_value = request.POST.get(field.name_attribute, '')

    context = {
        'daftar_gaya': daftar_gaya,
        'daftar_bidang': daftar_bidang
    }

    if request.method == 'POST':
        action = request.POST.get('action')

        # -------------------------------------------------------------
        # AKSI 1: POSTING KE INSTAGRAM (Mendukung Single & Carousel)
        # -------------------------------------------------------------
        if action == 'post_ig':
            final_caption = request.POST.get('final_caption')
            # Menerima data JSON berisi list URL gambar
            image_urls_json = request.POST.get('image_urls', '[]')
            
            try:
                raw_image_urls = json.loads(image_urls_json)
            except:
                raw_image_urls = []

            if not raw_image_urls or len(raw_image_urls) == 0:
                context['error_ig'] = "PENTING: Sistem Instagram tidak mengizinkan postingan teks saja. Anda wajib menggunakan gambar."
                context['hasil_caption'] = final_caption
                return render(request, 'index.html', context)
            
            graph_url = 'https://graph.facebook.com/v19.0'
            
            try:
                if not pengaturan or not pengaturan.ig_access_token or not pengaturan.ig_account_id:
                    raise ValueError("Token Instagram atau ID Akun belum diisi di Panel Admin!")
                
                if not pengaturan.cloudinary_creds:
                    raise ValueError("Kredensial Cloudinary belum diisi! Masukkan di Panel Admin dengan format: CloudName,APIKey,APISecret")

                ig_access_token = pengaturan.ig_access_token
                ig_account_id = pengaturan.ig_account_id
                
                api_kunci_gabungan = pengaturan.cloudinary_creds.strip()
                if "," not in api_kunci_gabungan:
                    raise ValueError("Format kunci salah! Pastikan mengisi format: CloudName,APIKey,APISecret.")
                
                kredensial = api_kunci_gabungan.split(',')
                if len(kredensial) != 3:
                    raise ValueError("Format kunci tidak lengkap!")
                
                cloud_name = kredensial[0].strip()
                cloudinary_api_key = kredensial[1].strip()
                cloudinary_api_secret = kredensial[2].strip()

                fs = FileSystemStorage()
                trusted_image_urls = []

                # STEP 1: UPLOAD SEMUA GAMBAR KE CLOUDINARY
                for raw_url in raw_image_urls:
                    filename = raw_url.split('/')[-1].split('?')[0]
                    file_path = fs.path(filename)
                    
                    timestamp = str(int(time.time()))
                    string_to_sign = f"timestamp={timestamp}{cloudinary_api_secret}"
                    signature = hashlib.sha1(string_to_sign.encode('utf-8')).hexdigest()

                    payload = {
                        'api_key': cloudinary_api_key,
                        'timestamp': timestamp,
                        'signature': signature
                    }
                    
                    with open(file_path, "rb") as file:
                        cloudinary_response = requests.post(
                            f"https://api.cloudinary.com/v1_1/{cloud_name}/image/upload",
                            data=payload,
                            files={"file": file},
                            timeout=20
                        )
                    
                    cloud_res_json = cloudinary_response.json()
                    
                    if not cloudinary_response.ok:
                        err_msg = cloud_res_json.get('error', {}).get('message', 'Ditolak oleh Cloudinary.')
                        raise Exception(f"Gagal mengunggah gambar ke Cloudinary: {err_msg}")
                    
                    trusted_image_urls.append(cloud_res_json['secure_url'])

                # STEP 2: POSTING KE INSTAGRAM (LOGIKA CAROUSEL VS SINGLE)
                if len(trusted_image_urls) == 1:
                    # LOGIKA 1 GAMBAR
                    container_payload = {
                        'image_url': trusted_image_urls[0],
                        'caption': final_caption,
                        'access_token': ig_access_token
                    }
                    container_req = requests.post(f"{graph_url}/{ig_account_id}/media", data=container_payload, timeout=20)
                    container_res = container_req.json()
                    
                    if 'error' in container_res:
                        raise Exception(f"Gagal membuat kontainer IG: {container_res['error']['message']}")
                    
                    creation_id = container_res['id']
                
                else:
                    # LOGIKA CAROUSEL (LEBIH DARI 1 GAMBAR)
                    children_ids = []
                    # A. Buat container item untuk setiap gambar
                    for t_url in trusted_image_urls:
                        item_payload = {
                            'image_url': t_url,
                            'is_carousel_item': 'true',
                            'access_token': ig_access_token
                        }
                        item_req = requests.post(f"{graph_url}/{ig_account_id}/media", data=item_payload, timeout=20)
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
                    carousel_req = requests.post(f"{graph_url}/{ig_account_id}/media", data=carousel_payload, timeout=20)
                    carousel_res = carousel_req.json()
                    if 'error' in carousel_res:
                        raise Exception(f"Gagal merakit Carousel IG: {carousel_res['error']['message']}")
                    
                    creation_id = carousel_res['id']

                # STEP 3: PUBLISH POSTINGAN (Single maupun Carousel)
                publish_payload = {
                    'creation_id': creation_id,
                    'access_token': ig_access_token
                }
                publish_req = requests.post(f"{graph_url}/{ig_account_id}/media_publish", data=publish_payload, timeout=20)
                publish_res = publish_req.json()
                
                if 'error' in publish_res:
                    raise Exception(f"Gagal mempublikasikan ke IG: {publish_res['error']['message']}")
                
                context['success_msg'] = "🎉 Sukses! Postingan Anda berhasil diunggah ke Instagram!"
                
            except Exception as e:
                context['error_ig'] = str(e)
                context['hasil_caption'] = final_caption
                context['image_urls_json'] = image_urls_json
                context['image_urls'] = raw_image_urls # Untuk preview ulang di form

        # -------------------------------------------------------------
        # AKSI 2 & 3: GENERATE AWAL ATAU GENERATE ULANG
        # -------------------------------------------------------------
        elif action in ['generate', 'regenerate']:
            bidang = request.POST.get('bidang')
            gaya_id = request.POST.get('gaya')
            
            # JSON yang berisi array gambar (Multiple) dari Cropper JS
            cropped_images_json_str = request.POST.get('cropped_images_json', '[]')
            
            # Fallback untuk regenerate
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

            # Jika URL gambar siap, eksekusi AI Generatif
            if len(uploaded_file_urls) > 0 and not context.get('error'):
                try:
                    context['image_urls'] = uploaded_file_urls
                    context['image_urls_json'] = json.dumps(uploaded_file_urls)
                    
                    gaya_terpilih = GayaCopywriting.objects.get(id=gaya_id)

                    detail_info = ""
                    for key, value in request.POST.items():
                        # Exclude sistem & form array variables
                        if key not in ['csrfmiddlewaretoken', 'bidang', 'gaya', 'action', 'image_urls', 'final_caption', 'gambar', 'cropped_images_json'] and value.strip() != "":
                            label = key.replace('_', ' ').title()
                            detail_info += f"- {label}: {value}\n"

                    prompt = f"Sebagai seorang copywriter, buat caption Instagram menarik untuk bisnis {bidang}.\n\n"
                    prompt += f"Detail info:\n{detail_info}\n\nInstruksi Gaya:\n{gaya_terpilih.prompt}\n\n"
                    prompt += "Berikan SATU hasil akhir caption saja (tidak perlu alternatif). Jangan pakai teks struktur [HEADER]. Berikan call-to-action dan hashtag. PENTING: JANGAN gunakan format markdown seperti bintang (**) untuk menebalkan teks, berikan teks polos biasa tanpa simbol bintang."

                    provider = pengaturan.ai_provider if pengaturan else 'gemini'
                    hasil_raw = ""

                    if provider == 'gemini':
                        if not pengaturan or not pengaturan.gemini_api_key:
                            raise Exception("API Key Gemini belum diisi di Panel Admin!")
                        nama_model = pengaturan.gemini_model if pengaturan.gemini_model else 'gemini-flash-latest'
                        genai.configure(api_key=pengaturan.gemini_api_key)
                        model = genai.GenerativeModel(nama_model)
                        response = model.generate_content(prompt)
                        hasil_raw = response.text

                    elif provider == 'groq':
                        if not pengaturan or not pengaturan.groq_api_key:
                            raise Exception("API Key Groq belum diisi di Panel Admin!")
                        
                        nama_model = pengaturan.groq_model if pengaturan.groq_model else 'llama-3.3-70b-versatile'
                        
                        headers = {
                            "Authorization": f"Bearer {pengaturan.groq_api_key.strip()}",
                            "Content-Type": "application/json"
                        }
                        payload = {
                            "model": nama_model,
                            "messages": [
                                {"role": "system", "content": "Anda adalah spesialis Social Media Copywriter."},
                                {"role": "user", "content": prompt}
                            ]
                        }
                        
                        res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
                        res_json = res.json()
                        
                        if not res.ok:
                            raise Exception(res_json.get('error', {}).get('message', 'Error pada server Groq.'))
                            
                        hasil_raw = res_json['choices'][0]['message']['content']

                    context['hasil_caption'] = hasil_raw.replace('**', '')

                except Exception as e:
                    context['error'] = f"Gagal menghasilkan caption ({provider.upper()} - Model: {nama_model}): {str(e)}"

    return render(request, 'index.html', context)
