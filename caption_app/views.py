import os
import time
import requests
import urllib.parse
import google.generativeai as genai
from django.shortcuts import render
from django.core.files.storage import FileSystemStorage
from django.utils.text import get_valid_filename
from .models import GayaCopywriting, PengaturanAPI

def generate_caption(request):
    daftar_gaya = GayaCopywriting.objects.all()
    context = {'daftar_gaya': daftar_gaya}
    
    # 1. AMBIL PENGATURAN DARI DATABASE SECARA OTOMATIS
    pengaturan = PengaturanAPI.objects.first()
    
    # Mengaktifkan Gemini API jika kuncinya sudah ada
    if pengaturan and pengaturan.gemini_api_key:
        genai.configure(api_key=pengaturan.gemini_api_key)

    if request.method == 'POST':
        action = request.POST.get('action')

        # -------------------------------------------------------------
        # AKSI 1: POSTING KE INSTAGRAM
        # -------------------------------------------------------------
        if action == 'post_ig':
            final_caption = request.POST.get('final_caption')
            raw_image_url = request.POST.get('image_url')
            
            # Membersihkan URL
            filename = raw_image_url.split('/')[-1].split('?')[0]
            safe_filename = urllib.parse.quote(filename)
            timestamp = int(time.time())
            
            image_url = f"https://aruha.pythonanywhere.com/media/{safe_filename}?v={timestamp}"
            graph_url = 'https://graph.facebook.com/v19.0'
            
            try:
                if not pengaturan or not pengaturan.ig_access_token or not pengaturan.ig_account_id:
                    raise ValueError("Token Instagram atau ID Akun belum diisi di Panel Admin!")

                ig_access_token = pengaturan.ig_access_token
                ig_account_id = pengaturan.ig_account_id

                # Step 1: Buat Media Container
                container_payload = {
                    'image_url': image_url,
                    'caption': final_caption,
                    'access_token': ig_access_token
                }
                
                container_req = requests.post(f"{graph_url}/{ig_account_id}/media", data=container_payload, timeout=20)
                container_res = container_req.json()
                
                if 'error' in container_res:
                    raise Exception(f"Gagal membuat kontainer IG: {container_res['error']['message']} | URL yg dikirim: {image_url}")
                
                creation_id = container_res['id']
                
                # Step 2: Publikasikan Media
                publish_payload = {
                    'creation_id': creation_id,
                    'access_token': ig_access_token
                }
                publish_req = requests.post(f"{graph_url}/{ig_account_id}/media_publish", data=publish_payload, timeout=20)
                publish_res = publish_req.json()
                
                if 'error' in publish_res:
                    raise Exception(f"Gagal mempublikasikan ke IG: {publish_res['error']['message']}")
                
                context['success_msg'] = "🎉 Sukses! Postingan berhasil diunggah ke Instagram!"
            except requests.exceptions.Timeout:
                context['error_ig'] = "Koneksi Timeout. Server terlalu lambat merespons permintaan Instagram."
                context['hasil_caption'] = final_caption
                context['image_url'] = raw_image_url
            except Exception as e:
                context['error_ig'] = str(e)
                context['hasil_caption'] = final_caption
                context['image_url'] = raw_image_url

        # -------------------------------------------------------------
        # AKSI 2 & 3: GENERATE AWAL ATAU GENERATE ULANG
        # -------------------------------------------------------------
        elif action in ['generate', 'regenerate']:
            bidang = request.POST.get('bidang')
            gaya_id = request.POST.get('gaya')
            gambar = request.FILES.get('gambar')
            existing_image_url = request.POST.get('image_url')  # Diambil jika aksi 'regenerate'

            uploaded_file_url = None

            # Validasi input sesuai aksi
            if action == 'generate':
                if not (bidang and gaya_id and gambar):
                    context['error'] = "Mohon lengkapi pilihan bidang, gaya penulisan, dan jangan lupa unggah gambar!"
                else:
                    # Cek ekstensi file gambar baru
                    allowed_extensions = ['.jpg', '.jpeg', '.png']
                    ext = os.path.splitext(gambar.name)[1].lower()
                    
                    if ext not in allowed_extensions:
                        context['error'] = f"Gagal: Format gambar '{ext}' tidak diterima Instagram. Harap unggah foto berekstensi .jpg, .jpeg, atau .png!"
                    else:
                        fs = FileSystemStorage()
                        safe_name = get_valid_filename(gambar.name)
                        filename = fs.save(safe_name, gambar)
                        uploaded_file_url = request.build_absolute_uri(fs.url(filename))

            elif action == 'regenerate':
                if not (bidang and gaya_id and existing_image_url):
                    context['error'] = "Data tidak lengkap untuk membuat ulang caption."
                else:
                    # Menggunakan gambar yang sudah diunggah sebelumnya
                    uploaded_file_url = existing_image_url

            # Jika validasi lolos & URL gambar tersedia, jalankan AI Gemini
            if uploaded_file_url and not context.get('error'):
                try:
                    if not pengaturan or not pengaturan.gemini_api_key:
                        raise Exception("API Key Gemini belum dimasukkan di Panel Admin!")

                    context['image_url'] = uploaded_file_url
                    gaya_terpilih = GayaCopywriting.objects.get(id=gaya_id)

                    # Mengumpulkan detail dinamis dari form
                    detail_info = ""
                    for key, value in request.POST.items():
                        if key not in ['csrfmiddlewaretoken', 'bidang', 'gaya', 'action', 'image_url', 'final_caption'] and value.strip() != "":
                            label = key.replace('_', ' ').title()
                            detail_info += f"- {label}: {value}\n"

                    # Pemanggilan model Gemini API
                    model = genai.GenerativeModel('gemini-flash-latest')
                    prompt = f"Sebagai seorang copywriter, buat caption Instagram menarik untuk bisnis {bidang}.\n\n"
                    prompt += f"Detail info:\n{detail_info}\n\nInstruksi Gaya:\n{gaya_terpilih.prompt}\n\n"
                    prompt += "Berikan SATU hasil akhir caption saja (tidak perlu alternatif). Jangan pakai teks struktur [HEADER]. Berikan call-to-action dan hashtag."
                    
                    response = model.generate_content(prompt)
                    context['hasil_caption'] = response.text

                except Exception as e:
                    context['error'] = f"Terjadi kesalahan AI: {str(e)}"

    return render(request, 'index.html', context)