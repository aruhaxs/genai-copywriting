import os
import google.generativeai as genai
from django.shortcuts import render
from django.conf import settings
from .models import GayaCopywriting
from dotenv import load_dotenv

env_path = os.path.join(settings.BASE_DIR, '.env')
load_dotenv(env_path)

api_key = os.getenv("GEMINI_API_KEY")

if api_key:
    genai.configure(api_key=api_key)

def generate_caption(request):
    daftar_gaya = GayaCopywriting.objects.all()
    context = {'daftar_gaya': daftar_gaya}

    if request.method == 'POST':
        bidang = request.POST.get('bidang')
        gaya_id = request.POST.get('gaya')

        if bidang and gaya_id:
            try:
                if not api_key:
                    raise ValueError("API Key tidak terbaca! Pastikan nama file adalah '.env' (bukan .env.txt) dan berisi GEMINI_API_KEY=kuncimu")

                gaya_terpilih = GayaCopywriting.objects.get(id=gaya_id)

                detail_info = ""
                for key, value in request.POST.items():
                    if key not in ['csrfmiddlewaretoken', 'bidang', 'gaya'] and value.strip() != "":
                        label = key.replace('_', ' ').title()
                        detail_info += f"- {label}: {value}\n"

                model = genai.GenerativeModel('gemini-flash-latest')
                
                prompt = f"Sebagai seorang copywriter profesional, buat caption Instagram yang menarik untuk bisnis di bidang {bidang}.\n\n"
                prompt += f"Berikut adalah detail informasinya:\n{detail_info}\n\n"
                prompt += f"Instruksi Gaya Penulisan:\n{gaya_terpilih.prompt}\n\n"
                prompt += "Aturan PENTING untuk hasil akhir:\n"
                prompt += "1. Buatkan 3 alternatif caption yang berbeda (Tandai dengan judul Alternatif 1, Alternatif 2, dan Alternatif 3).\n"
                prompt += "2. JANGAN PERNAH menggunakan teks penanda struktur seperti [HEADER], [BODY COPY], atau sejenisnya. Tulis teksnya mengalir begitu saja.\n"
                prompt += "3. Hasilkan teks yang bersih, rapi, dan langsung siap disalin-tempel (copy-paste).\n"
                prompt += "4. Kurangi penggunaan simbol atau emoji yang berlebihan (Maksimal 2-3 emoji per caption saja).\n"
                prompt += "5. Sertakan call-to-action dan beberapa hashtag relevan di akhir setiap alternatif caption."
                
                response = model.generate_content(prompt)
                
                context['hasil_caption'] = response.text
                context['bidang_sebelumnya'] = bidang
            except Exception as e:
                context['error'] = f"Terjadi kesalahan saat menghubungi AI: {str(e)}"

    return render(request, 'index.html', context)
