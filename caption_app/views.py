import os
import time
import hashlib
import requests
import urllib.parse
import io
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

        if action == 'post_ig':
            final_caption = request.POST.get('final_caption')
            raw_image_url = request.POST.get('image_url')
            
            if not raw_image_url or raw_image_url.strip() == "":
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
                    raise ValueError("Format kunci salah! Pastikan mengisi dengan format: CloudName,APIKey,APISecret (dipisahkan koma tanpa spasi).")
                
                kredensial = api_kunci_gabungan.split(',')
                if len(kredensial) != 3:
                    raise ValueError("Format kunci tidak lengkap! Harus berisi 3 bagian: CloudName, APIKey, dan APISecret.")
                
                cloud_name = kredensial[0].strip()
                cloudinary_api_key = kredensial[1].strip()
                cloudinary_api_secret = kredensial[2].strip()

                filename = raw_image_url.split('/')[-1].split('?')[0]
                fs = FileSystemStorage()
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
                
                trusted_image_url = cloud_res_json['secure_url']

                container_payload = {
                    'image_url': trusted_image_url,
                    'caption': final_caption,
                    'access_token': ig_access_token
                }
                container_req = requests.post(f"{graph_url}/{ig_account_id}/media", data=container_payload, timeout=20)
                container_res = container_req.json()
                
                if 'error' in container_res:
                    raise Exception(f"Gagal membuat kontainer IG: {container_res['error']['message']}")
                
                creation_id = container_res['id']
                
                publish_payload = {
                    'creation_id': creation_id,
                    'access_token': ig_access_token
                }
                publish_req = requests.post(f"{graph_url}/{ig_account_id}/media_publish", data=publish_payload, timeout=20)
                publish_res = publish_req.json()
                
                if 'error' in publish_res:
                    raise Exception(f"Gagal mempublikasikan ke IG: {publish_res['error']['message']}")
                
                context['success_msg'] = "🎉 Sukses! Postingan berhasil diunggah ke Instagram! Form telah dibersihkan."
                
            except Exception as e:
                context['error_ig'] = str(e)
                context['hasil_caption'] = final_caption
                context['image_url'] = raw_image_url

        elif action in ['generate', 'regenerate']:
            bidang = request.POST.get('bidang')
            gaya_id = request.POST.get('gaya')
            gambar = request.FILES.get('gambar')
            existing_image_url = request.POST.get('image_url')

            uploaded_file_url = None

            if bidang and gaya_id:
                try:
                    if action == 'generate':
                        if not gambar:
                            raise Exception("Harap unggah gambar terlebih dahulu untuk memulai!")
                            
                        allowed_extensions = ['.jpg', '.jpeg', '.png']
                        ext = os.path.splitext(gambar.name)[1].lower()
                        
                        if ext not in allowed_extensions:
                            raise Exception(f"Format gambar '{ext}' tidak dikenali. Harap unggah foto .jpg, .jpeg, atau .png!")
                            
                        img = Image.open(gambar)
                        if img.mode != 'RGB':
                            img = img.convert('RGB')
                        
                        max_width = 1080
                        if img.width > max_width:
                            ratio = max_width / float(img.width)
                            new_height = int((float(img.height) * float(ratio)))
                            img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
                        
                        base_name = os.path.splitext(get_valid_filename(gambar.name))[0]
                        meta_safe_filename = f"{base_name}_igready.jpg"
                        
                        img_io = io.BytesIO()
                        img.save(img_io, format='JPEG', quality=85)
                        img_io.seek(0)
                        
                        fs = FileSystemStorage()
                        filename = fs.save(meta_safe_filename, ContentFile(img_io.read()))
                        uploaded_file_url = request.build_absolute_uri(fs.url(filename))
                    
                    elif action == 'regenerate':
                        if not existing_image_url:
                            raise Exception("Data gambar hilang, silakan mulai ulang proses.")
                        uploaded_file_url = existing_image_url

                except Exception as e:
                    context['error'] = str(e)

            if uploaded_file_url and not context.get('error'):
                try:
                    context['image_url'] = uploaded_file_url
                    gaya_terpilih = GayaCopywriting.objects.get(id=gaya_id)

                    detail_info = ""
                    for key, value in request.POST.items():
                        if key not in ['csrfmiddlewaretoken', 'bidang', 'gaya', 'action', 'image_url', 'final_caption', 'gambar'] and value.strip() != "":
                            label = key.replace('_', ' ').title()
                            detail_info += f"- {label}: {value}\n"

                    prompt = f"Sebagai seorang copywriter, buat caption Instagram menarik untuk bisnis {bidang}.\n\n"
                    prompt += f"Detail info:\n{detail_info}\n\nInstruksi Gaya:\n{gaya_terpilih.prompt}\n\n"
                    prompt += "Berikan SATU hasil akhir caption saja (tidak perlu alternatif). Jangan pakai teks struktur [HEADER]. Berikan call-to-action dan hashtag."

                    provider = pengaturan.ai_provider if pengaturan else 'gemini'

                    if provider == 'gemini':
                        if not pengaturan or not pengaturan.gemini_api_key:
                            raise Exception("API Key Gemini belum diisi di Panel Admin!")
                        nama_model = pengaturan.gemini_model if pengaturan.gemini_model else 'gemini-flash-latest'
                        genai.configure(api_key=pengaturan.gemini_api_key)
                        model = genai.GenerativeModel(nama_model)
                        response = model.generate_content(prompt)
                        context['hasil_caption'] = response.text

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
                            
                        context['hasil_caption'] = res_json['choices'][0]['message']['content']

                except Exception as e:
                    context['error'] = f"Gagal menghasilkan caption ({provider.upper()} - Model: {nama_model}): {str(e)}"

    return render(request, 'index.html', context)
