import os
import requests
import google.generativeai as genai
from django.shortcuts import render
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from .models import GayaCopywriting
from dotenv import load_dotenv

load_dotenv(os.path.join(settings.BASE_DIR, '.env'))

# Kredensial API
api_key = os.getenv("GEMINI_API_KEY")
ig_access_token = os.getenv("IG_ACCESS_TOKEN")
ig_account_id = os.getenv("IG_ACCOUNT_ID")

if api_key:
    genai.configure(api_key=api_key)

def generate_caption(request):
    daftar_gaya = GayaCopywriting.objects.all()
    context = {'daftar_gaya': daftar_gaya}

    if request.method == 'POST':
        action = request.POST.get('action')

        # AKSI 1: POSTING KE INSTAGRAM
        if action == 'post_ig':
            final_caption = request.POST.get('final_caption')
            image_url = request.POST.get('image_url')
            
            # Instagram API Endpoint
            graph_url = 'https://graph.facebook.com/v19.0'
            
            try:
                if not ig_access_token or not ig_account_id:
                    raise ValueError("Token Instagram atau ID Akun belum diatur di file .env")

                # Step 1: Buat Media Container di server IG
                container_payload = {
                    'image_url': image_url,
                    'caption': final_caption,
                    'access_token': ig_access_token
                }
                container_req = requests.post(f"{graph_url}/{ig_account_id}/media", data=container_payload)
                container_res = container_req.json()
                
                if 'error' in container_res:
                    raise Exception(f"Gagal membuat kontainer IG: {container_res['error']['message']}")
                
                creation_id = container_res['id']
                
                # Step 2: Publikasikan Media Container tersebut
                publish_payload = {
                    'creation_id': creation_id,
                    'access_token': ig_access_token
                }
                publish_req = requests.post(f"{graph_url}/{ig_account_id}/media_publish", data=publish_payload)
                publish_res = publish_req.json()
                
                if 'error' in publish_res:
                    raise Exception(f"Gagal mempublikasikan ke IG: {publish_res['error']['message']}")
                
                context['success_msg'] = "🎉 Sukses! Postingan berhasil diunggah ke Instagram!"
            except Exception as e:
                context['error_ig'] = str(e)
                context['hasil_caption'] = final_caption
                context['image_url'] = image_url


        # AKSI 2: GENERATE CAPTION & UPLOAD GAMBAR
        elif action == 'generate':
            bidang = request.POST.get('bidang')
            gaya_id = request.POST.get('gaya')
            gambar = request.FILES.get('gambar')

            if bidang and gaya_id and gambar:
                try:
                    # Simpan gambar ke dalam folder /media/
                    fs = FileSystemStorage()
                    filename = fs.save(gambar.name, gambar)
                    
                    # Membuat URL gambar (Catatan: Ini butuh domain publik agar IG bisa membacanya)
                    uploaded_file_url = request.build_absolute_uri(fs.url(filename))
                    context['image_url'] = uploaded_file_url

                    # Ambil instruksi gaya
                    gaya_terpilih = GayaCopywriting.objects.get(id=gaya_id)

                    detail_info = ""
                    for key, value in request.POST.items():
                        if key not in ['csrfmiddlewaretoken', 'bidang', 'gaya', 'action'] and value.strip() != "":
                            label = key.replace('_', ' ').title()
                            detail_info += f"- {label}: {value}\n"

                    # Panggil AI
                    model = genai.GenerativeModel('gemini-flash-latest')
                    prompt = f"Sebagai seorang copywriter, buat caption Instagram menarik untuk bisnis {bidang}.\n\n"
                    prompt += f"Detail info:\n{detail_info}\n\nInstruksi Gaya:\n{gaya_terpilih.prompt}\n\n"
                    prompt += "Berikan SATU hasil akhir caption saja (tidak perlu alternatif). Jangan pakai teks struktur [HEADER]. Berikan call-to-action dan hashtag."
                    
                    response = model.generate_content(prompt)
                    context['hasil_caption'] = response.text

                except Exception as e:
                    context['error'] = f"Terjadi kesalahan AI: {str(e)}"
            else:
                context['error'] = "Mohon lengkapi pilihan bidang, gaya penulisan, dan jangan lupa unggah gambar!"

    return render(request, 'index.html', context)
