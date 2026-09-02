import os
import time
import hashlib
import requests
import re
import urllib.parse
import io
import base64
import json
from PIL import Image
import google.generativeai as genai
from functools import wraps

from django.shortcuts import render, redirect
from django.urls import reverse
from django.core.files.storage import FileSystemStorage
from django.core.files.base import ContentFile
from django.contrib import messages
from django.conf import settings
from django.utils import timezone

from .models import GayaCopywriting, PengaturanAPI, BidangUsaha, AkunInstagram, KontenPosting, PenggunaBiasa

GRAPH_API_VERSION = "v25.0"
GRAPH_BASE_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"  # Legacy, sudah tidak dipakai untuk flow Instagram Login

# Instagram API with Instagram Login (Business Login for Instagram)
# Tidak butuh Facebook Page / Business Portfolio sama sekali.
IG_GRAPH_BASE_URL = "https://graph.instagram.com"

# ==========================================
# AUTENTIKASI PENGGUNA BIASA (TERPISAH DARI ADMIN)
# ==========================================
# CATATAN PENTING:
# Sistem ini SENGAJA tidak memakai django.contrib.auth.login()/logout()
# (itu dipakai khusus untuk Admin lewat /admin/). Pengguna biasa memakai
# session key sendiri ('pengguna_id'), jadi kedua sistem login (admin vs
# user) berjalan 100% independen: session admin disimpan Django di key
# '_auth_user_id', session pengguna biasa disimpan di key 'pengguna_id'.
# Tidak ada titik temu antara keduanya.

PENGGUNA_SESSION_KEY = 'pengguna_id'
EMAIL_REGEX = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


def get_current_pengguna(request):
    """Ambil objek PenggunaBiasa yang sedang login dari session, atau None."""
    pengguna_id = request.session.get(PENGGUNA_SESSION_KEY)
    if not pengguna_id:
        return None
    try:
        return PenggunaBiasa.objects.get(id=pengguna_id)
    except PenggunaBiasa.DoesNotExist:
        # Session basi (akun sudah dihapus admin misalnya) -> bersihkan
        request.session.pop(PENGGUNA_SESSION_KEY, None)
        return None


def login_required_pengguna(view_func):
    """Decorator khusus rute pengguna biasa. TIDAK memakai @login_required
    bawaan Django (itu untuk sistem auth admin/staff)."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        pengguna = get_current_pengguna(request)
        if not pengguna:
            messages.warning(request, "Silakan login terlebih dahulu untuk mengakses halaman ini.")
            return redirect('login_user')
        request.pengguna = pengguna
        return view_func(request, *args, **kwargs)
    return wrapper


def landing_page(request):
    """Halaman pertama website. Kalau pengguna sudah login, langsung arahkan ke dashboard."""
    if get_current_pengguna(request):
        return redirect('dashboard')
    return render(request, 'landing.html')


def signup_pengguna(request):
    if get_current_pengguna(request):
        return redirect('dashboard')

    if request.method == 'POST':
        nama = (request.POST.get('nama') or '').strip()
        email = (request.POST.get('email') or '').strip().lower()
        no_telepon = (request.POST.get('no_telepon') or '').strip()
        password = request.POST.get('password') or ''
        konfirmasi_password = request.POST.get('konfirmasi_password') or ''

        errors = []

        if not nama or len(nama) < 2:
            errors.append("Nama wajib diisi (minimal 2 karakter).")

        if not email or not EMAIL_REGEX.match(email):
            errors.append("Format email tidak valid.")
        elif PenggunaBiasa.objects.filter(email=email).exists():
            errors.append("Email ini sudah terdaftar. Silakan login.")

        if not password or len(password) < 8:
            errors.append("Password minimal 8 karakter.")

        if password != konfirmasi_password:
            errors.append("Konfirmasi password tidak sama dengan password.")

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, 'signup.html', {
                'nama': nama, 'email': email, 'no_telepon': no_telepon
            })

        pengguna = PenggunaBiasa(nama=nama, email=email, no_telepon=no_telepon or None)
        pengguna.set_password(password)  # selalu di-hash, tidak pernah plaintext
        pengguna.save()

        messages.success(request, "🎉 Akun berhasil dibuat! Silakan login.")
        return redirect('login_user')

    return render(request, 'signup.html')


def login_pengguna(request):
    if get_current_pengguna(request):
        return redirect('dashboard')

    if request.method == 'POST':
        email = (request.POST.get('email') or '').strip().lower()
        password = request.POST.get('password') or ''

        error = None
        if not email or not password:
            error = "Email dan password wajib diisi."
        else:
            try:
                pengguna = PenggunaBiasa.objects.get(email=email)
            except PenggunaBiasa.DoesNotExist:
                pengguna = None

            # Pesan error digeneralisir (tidak bilang "email tidak ada" secara spesifik)
            # supaya tidak membocorkan email mana saja yang terdaftar.
            if not pengguna or not pengguna.check_password(password):
                error = "Email atau password salah."

        if error:
            messages.error(request, error)
            return render(request, 'login_user.html', {'email': email})

        # Cegah session fixation: regenerasi session key sebelum set data login
        request.session.cycle_key()
        request.session[PENGGUNA_SESSION_KEY] = pengguna.id
        messages.success(request, f"Selamat datang kembali, {pengguna.nama}!")
        return redirect('dashboard')

    return render(request, 'login_user.html')


def logout_pengguna(request):
    request.session.pop(PENGGUNA_SESSION_KEY, None)
    request.session.flush()
    messages.success(request, "Anda telah logout.")
    return redirect('home')


def get_config():
    db_config = PengaturanAPI.objects.first()
    
    def fetch_val(db_attr, env_key, default=""):
        env_val = os.getenv(env_key, "").strip()
        if env_val:
            return env_val
        if db_config and getattr(db_config, db_attr, None):
            db_val = getattr(db_config, db_attr).strip()
            if db_val:
                return db_val
        return default

    class ConfigWrapper:
        pass

    config = ConfigWrapper()
    config.db_obj = db_config
    config.fb_app_id = fetch_val('fb_app_id', 'FB_APP_ID')
    config.fb_app_secret = fetch_val('fb_app_secret', 'FB_APP_SECRET')
    config.ig_app_id = fetch_val('ig_app_id', 'IG_APP_ID')
    config.ig_app_secret = fetch_val('ig_app_secret', 'IG_APP_SECRET')
    config.gemini_api_key = fetch_val('gemini_api_key', 'GEMINI_API_KEY')
    config.gemini_model = fetch_val('gemini_model', 'GEMINI_MODEL', 'gemini-2.5-flash')
    config.groq_api_key = fetch_val('groq_api_key', 'GROQ_API_KEY')
    config.groq_model = fetch_val('groq_model', 'GROQ_MODEL', 'llama-3.3-70b-versatile')
    config.cloudinary_creds = fetch_val('cloudinary_creds', 'CLOUDINARY_CREDS')
    
    env_ai_provider = os.getenv('AI_PROVIDER', '').strip()
    if env_ai_provider:
        config.ai_provider = env_ai_provider
    elif db_config and hasattr(db_config, 'ai_provider') and db_config.ai_provider:
        config.ai_provider = db_config.ai_provider
    else:
        config.ai_provider = 'gemini'

    return config


def wait_for_container_ready(container_id, access_token, max_retries=10, delay_seconds=2):
    status_url = f"{IG_GRAPH_BASE_URL}/{container_id}"
    params = {'fields': 'status_code,status', 'access_token': access_token}
    
    for _ in range(max_retries):
        time.sleep(delay_seconds)
        res = requests.get(status_url, params=params, timeout=15).json()
        status_code = res.get('status_code')
        
        if status_code == 'FINISHED':
            return True
        elif status_code in ['ERROR', 'EXPIRED']:
            raise Exception(f"Instagram gagal memproses media container (Status: {status_code}).")
            
    raise Exception("Waktu tunggu pemrosesan media Instagram habis (Timeout). Coba lagi.")


def verify_and_upgrade_token(config, ig_account_obj):
    """
    Instagram Login (Business Login for Instagram) memberi long-lived token
    yang berlaku 60 hari dan wajib di-refresh secara berkala (bisa di-refresh
    kalau umurnya sudah >24 jam, sebelum expired). Tidak ada lagi konsep
    "Page Access Token" di sini — refresh dilakukan langsung atas token IG-nya.
    """
    current_token = ig_account_obj.ig_access_token

    if not current_token:
        raise Exception(f"Token untuk {ig_account_obj.nama_akun} belum ada. Hubungkan ulang akun ini.")

    refresh_url = (
        f"{IG_GRAPH_BASE_URL}/refresh_access_token"
        f"?grant_type=ig_refresh_token&access_token={current_token}"
    )
    try:
        res_refresh = requests.get(refresh_url, timeout=15).json()
    except Exception as e:
        # Kalau refresh gagal karena jaringan dsb, tetap coba pakai token lama
        return current_token

    if 'error' in res_refresh:
        error_msg = res_refresh['error'].get('message', '')
        # Token benar-benar invalid/expired -> user harus login ulang
        if res_refresh['error'].get('code') in (190,) or 'expired' in error_msg.lower():
            raise Exception(f"Token untuk {ig_account_obj.nama_akun} kedaluwarsa. Hubungkan ulang akun ini.")
        # Error lain (misal token belum genap 24 jam) -> aman pakai token lama
        return current_token

    new_token = res_refresh.get('access_token')
    if new_token:
        ig_account_obj.ig_access_token = new_token
        ig_account_obj.save()
        return new_token

    return current_token

@login_required_pengguna
def instagram_logout(request):
    """
    Melepas akun Instagram yang sedang aktif DARI SESSION PENGGUNA INI SAJA.
    TIDAK menonaktifkan akun di database -- karena satu akun IG bisa dipakai
    banyak PenggunaBiasa (lewat 'pengelola'), jadi "logout" di sini cuma
    berarti "un-pilih akun ini untuk sesi saya", bukan mematikan akun untuk
    semua pengguna lain. Menonaktifkan akun (is_active) itu wewenang Admin
    lewat Django Admin Panel, bukan lewat tombol di dashboard pengguna biasa.
    """
    if 'active_ig_account_id' in request.session:
        del request.session['active_ig_account_id']

    messages.success(request, "👋 Berhasil melepas akun Instagram dari sesi Anda.")
    return redirect('/dashboard/')


def facebook_login(request):
    """
    Memicu dialog otorisasi Instagram Login (Business Login for Instagram).
    Login langsung lewat Instagram, TANPA Facebook Page / Business Portfolio.
    Bisa dipicu dari mana saja (mis. tombol di Admin Panel) -- lewat ?next=
    kita simpan ke mana harus kembali setelah OAuth selesai.
    """
    config = get_config()
    if not config.ig_app_id:
        messages.error(request, "⚠️ GAGAL: Instagram App ID belum diisi di .env maupun di Admin!")
        return redirect('/')

    # Simpan tujuan redirect setelah callback (default: halaman utama)
    request.session['ig_login_next'] = request.GET.get('next') or '/'

    redirect_uri = request.build_absolute_uri(reverse('facebook_callback'))
    if redirect_uri.startswith('http://'):
        redirect_uri = redirect_uri.replace('http://', 'https://', 1)

    scope = "instagram_business_basic,instagram_business_content_publish"
    ig_auth_url = (
        f"https://www.instagram.com/oauth/authorize?"
        f"client_id={config.ig_app_id}&"
        f"redirect_uri={urllib.parse.quote(redirect_uri)}&"
        f"scope={scope}&response_type=code"
    )
    return redirect(ig_auth_url)


def facebook_callback(request):
    """
    Callback untuk Instagram Login. Tidak ada langkah cari Facebook Page lagi --
    token yang didapat sudah langsung terikat ke satu akun Instagram (user_id).
    """
    next_url = request.session.pop('ig_login_next', '/')

    code = request.GET.get('code')
    error_reason = request.GET.get('error_description') or request.GET.get('error_message')

    if error_reason or not code:
        messages.error(request, f"❌ GAGAL OTORISASI: {error_reason or 'Pengguna membatalkan login.'}")
        return redirect(next_url)

    config = get_config()
    redirect_uri = request.build_absolute_uri(reverse('facebook_callback'))
    if redirect_uri.startswith('http://'):
        redirect_uri = redirect_uri.replace('http://', 'https://', 1)

    try:
        # 1) Tukar authorization code -> short-lived token (POST, bukan GET)
        token_payload = {
            'client_id': config.ig_app_id,
            'client_secret': config.ig_app_secret,
            'grant_type': 'authorization_code',
            'redirect_uri': redirect_uri,
            'code': code,
        }
        res_token = requests.post(
            "https://api.instagram.com/oauth/access_token",
            data=token_payload, timeout=15
        ).json()

        if 'error_message' in res_token or 'error' in res_token:
            raise Exception(res_token.get('error_message') or res_token.get('error'))

        # Response Instagram Login membungkus hasil di dalam data[0]
        token_data = res_token.get('data', [res_token])[0] if isinstance(res_token.get('data'), list) else res_token
        short_lived_token = token_data.get('access_token') or res_token.get('access_token')
        ig_user_id = token_data.get('user_id') or res_token.get('user_id')

        if not short_lived_token or not ig_user_id:
            raise Exception("Response token tidak lengkap dari Instagram.")

        # 2) Tukar short-lived -> long-lived token (berlaku 60 hari)
        long_url = (
            f"{IG_GRAPH_BASE_URL}/access_token"
            f"?grant_type=ig_exchange_token&client_secret={config.ig_app_secret}"
            f"&access_token={short_lived_token}"
        )
        res_long = requests.get(long_url, timeout=15).json()
        if 'error' in res_long:
            raise Exception(res_long['error'].get('message', 'Gagal upgrade ke long-lived token.'))

        long_lived_token = res_long['access_token']

        # 3) Ambil data profil akun IG yang baru login (langsung dari graph.instagram.com,
        #    tidak perlu lagi cari lewat /me/accounts karena tidak ada Page yang terlibat)
        profile_url = f"{IG_GRAPH_BASE_URL}/me?fields=user_id,username,account_type&access_token={long_lived_token}"
        res_profile = requests.get(profile_url, timeout=15).json()
        if 'error' in res_profile:
            raise Exception(res_profile['error'].get('message', 'Gagal mengambil data profil.'))

        username = res_profile.get('username', f'ig_{ig_user_id}')

        akun_obj, created = AkunInstagram.objects.get_or_create(
            ig_account_id=str(ig_user_id),
            defaults={
                'nama_akun': f"@{username}",
                'ig_access_token': long_lived_token,
                'is_active': True
            }
        )
        if not created:
            akun_obj.nama_akun = f"@{username}"
            akun_obj.ig_access_token = long_lived_token
            akun_obj.is_active = True
            akun_obj.save()

        # Catatan: pengelola (PenggunaBiasa mana yang boleh pakai akun ini) TIDAK
        # di-auto-assign di sini lagi. Proses connect ini dipicu oleh Staff/Admin
        # (django auth User) lewat Admin Panel, sedangkan pengelola akun IG adalah
        # PenggunaBiasa (sistem login terpisah) -- dua identitas ini tidak bisa
        # disatukan otomatis. Assign pengelola secara manual lewat Admin Panel:
        # Akun Instagram -> pilih akun -> centang Pengguna Biasa yang berhak pakai.

        request.session['active_ig_account_id'] = akun_obj.id
        messages.success(request, f"🎉 SUKSES! Akun @{username} berhasil terhubung!")

    except Exception as e:
        messages.error(request, f"❌ GAGAL MEMPERBARUI TOKEN: {str(e)}")

    return redirect(next_url)

@login_required_pengguna
def generate_caption(request):
    daftar_gaya = GayaCopywriting.objects.all()
    daftar_bidang = BidangUsaha.objects.prefetch_related('fields').all()
    config = get_config()

    # Hanya ambil akun yang is_active=True DAN memang di-assign ke pengguna ini
    # (pengelola sekarang PenggunaBiasa, konsisten dengan sistem login dashboard).
    daftar_akun_ig = AkunInstagram.objects.filter(is_active=True, pengelola=request.pengguna)

    # Cek session aktif
    ig_account_pk = request.session.get('active_ig_account_id')
    akun_ig_terpilih = None

    if ig_account_pk:
        akun_ig_terpilih = daftar_akun_ig.filter(pk=ig_account_pk).first()

    # Auto-pilih akun IG yang sudah di-assign ke pengguna ini kalau belum ada
    # yang aktif di session (misal baru pertama kali login, atau akun baru
    # di-assign lewat Admin setelah pengguna sudah login sebelumnya).
    # Sebelumnya logic ini dimatikan -- itu penyebab akun yang sudah di-assign
    # tidak pernah otomatis terhubung dan seolah perlu "login Instagram lagi".
    if not akun_ig_terpilih and daftar_akun_ig.exists():
        akun_ig_terpilih = daftar_akun_ig.first()
        request.session['active_ig_account_id'] = akun_ig_terpilih.id

    context = {
        'pengguna': request.pengguna,
        'daftar_gaya': daftar_gaya,
        'daftar_bidang': daftar_bidang,
        'daftar_akun_ig': daftar_akun_ig,
        'akun_ig_terpilih': akun_ig_terpilih,
        'config': config,
        'field_values': {}
    }

    # Kunci-kunci non-dynamic-field yang tidak boleh ikut dianggap sebagai
    # nilai FieldBidang (supaya tidak salah prefill ke input yang salah).
    NON_FIELD_KEYS = {
        'csrfmiddlewaretoken', 'bidang', 'gaya', 'action',
        'image_urls', 'final_caption', 'gambar', 'cropped_images_json',
        'ig_account_id', 'image_urls_json'
    }

    if request.method == 'POST':
        # Simpan semua nilai field dinamis yang disubmit, supaya kalau user
        # klik "Regenerate" (atau generate gagal karena error lain), isian
        # yang sudah mereka ketik TIDAK hilang -- form auto-terisi ulang.
        context['field_values'] = {
            k: v for k, v in request.POST.items() if k not in NON_FIELD_KEYS
        }

        action = request.POST.get('action')

        # ==========================================
        # ACTION: POST TO INSTAGRAM & SAVE TO DATABASE
        # ==========================================
        if action == 'post_ig':
            final_caption = request.POST.get('final_caption')
            image_urls_json = request.POST.get('image_urls', '[]')

            # Ambil akun IG dari PILIHAN DROPDOWN yang disubmit pengguna,
            # dicocokkan ke daftar_akun_ig yang SUDAH difilter pengelola=request.pengguna
            # (jadi tetap aman -- pengguna tidak bisa pilih akun yang bukan miliknya
            # walau iseng ubah value di HTML).
            # Sebelumnya kode ini cuma mengandalkan session 'active_ig_account_id',
            # padahal itu diisi dari sesi Admin saat OAuth -- bukan sesi pengguna biasa
            # yang sedang mengisi form ini, makanya selalu dianggap "belum terhubung".
            selected_ig_pk = request.POST.get('ig_account_id')
            if selected_ig_pk:
                akun_ig_terpilih = daftar_akun_ig.filter(pk=selected_ig_pk).first()
                if akun_ig_terpilih:
                    context['akun_ig_terpilih'] = akun_ig_terpilih
                    # Simpan juga ke session pengguna ini supaya header preview
                    # konsisten kalau halaman di-refresh setelahnya.
                    request.session['active_ig_account_id'] = akun_ig_terpilih.id

            try:
                raw_image_urls = json.loads(image_urls_json) if isinstance(image_urls_json, str) else image_urls_json
            except Exception:
                raw_image_urls = []

            if not raw_image_urls:
                context['error_ig'] = "PENTING: Sistem Instagram wajib menggunakan gambar."
                context['hasil_caption'] = final_caption
                return render(request, 'index.html', context)

            if not akun_ig_terpilih:
                context['error_ig'] = "PENTING: Harap hubungkan akun Instagram tujuan terlebih dahulu."
                context['hasil_caption'] = final_caption
                context['image_urls_json'] = json.dumps(raw_image_urls)
                context['image_urls'] = raw_image_urls
                return render(request, 'index.html', context)
            
            try:
                ig_access_token = verify_and_upgrade_token(config, akun_ig_terpilih)
                ig_account_id = akun_ig_terpilih.ig_account_id
                
                if not config.cloudinary_creds:
                    raise ValueError("Kredensial Cloudinary belum diisi di .env/Admin!")

                api_kunci_gabungan = config.cloudinary_creds.strip()
                kredensial = api_kunci_gabungan.split(',')
                cloud_name, cloudinary_api_key, cloudinary_api_secret = [k.strip() for k in kredensial]

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
                            data=payload, files={"file": file_obj}, timeout=20
                        )
                    
                    cloud_res_json = cloudinary_response.json()
                    if not cloudinary_response.ok:
                        raise Exception("Unggah gambar ke Cloudinary ditolak.")
                    
                    trusted_image_urls.append(cloud_res_json['secure_url'])

                tipe_media = 'IMAGE' if len(trusted_image_urls) == 1 else 'CAROUSEL'

                if tipe_media == 'IMAGE':
                    container_payload = {
                        'image_url': trusted_image_urls[0],
                        'caption': final_caption,
                        'access_token': ig_access_token
                    }
                    container_req = requests.post(f"{IG_GRAPH_BASE_URL}/{ig_account_id}/media", data=container_payload, timeout=20)
                    container_res = container_req.json()
                    if 'error' in container_res:
                        raise Exception(f"Gagal membuat kontainer IG: {container_res['error']['message']}")
                    
                    creation_id = container_res['id']
                    wait_for_container_ready(creation_id, ig_access_token)

                else:
                    children_ids = []
                    for t_url in trusted_image_urls:
                        item_payload = {'image_url': t_url, 'is_carousel_item': 'true', 'access_token': ig_access_token}
                        item_req = requests.post(f"{IG_GRAPH_BASE_URL}/{ig_account_id}/media", data=item_payload, timeout=20)
                        item_res = item_req.json()
                        if 'error' in item_res:
                            raise Exception(f"Gagal membuat item carousel: {item_res['error']['message']}")
                        
                        item_id = item_res['id']
                        wait_for_container_ready(item_id, ig_access_token)
                        children_ids.append(item_id)
                    
                    carousel_payload = {
                        'media_type': 'CAROUSEL',
                        'children': ','.join(children_ids),
                        'caption': final_caption,
                        'access_token': ig_access_token
                    }
                    carousel_req = requests.post(f"{IG_GRAPH_BASE_URL}/{ig_account_id}/media", data=carousel_payload, timeout=20)
                    carousel_res = carousel_req.json()
                    if 'error' in carousel_res:
                        raise Exception(f"Gagal merakit Carousel IG: {carousel_res['error']['message']}")
                    
                    creation_id = carousel_res['id']
                    wait_for_container_ready(creation_id, ig_access_token)

                publish_payload = {'creation_id': creation_id, 'access_token': ig_access_token}
                publish_req = requests.post(f"{IG_GRAPH_BASE_URL}/{ig_account_id}/media_publish", data=publish_payload, timeout=20)
                publish_res = publish_req.json()
                
                if 'error' in publish_res:
                    raise Exception(f"Gagal mempublikasikan ke IG: {publish_res['error']['message']}")
                
                published_post_id = publish_res.get('id')

                # SIMPAN DATA KE DATABASE (KontenPosting)
                # request.pengguna dijamin ada karena view ini di-guard oleh
                # @login_required_pengguna -- bukan lagi cek request.user.is_authenticated
                # (itu punya sistem auth Admin/staff yang terpisah, selalu Anonymous di sini).
                bidang_nama = request.POST.get('bidang')
                gaya_id = request.POST.get('gaya')

                kategori_obj = BidangUsaha.objects.filter(nama=bidang_nama).first()
                gaya_obj = GayaCopywriting.objects.filter(id=gaya_id).first()

                KontenPosting.objects.create(
                    target_akun_ig=akun_ig_terpilih,
                    kategori_konten=kategori_obj,
                    gaya_copywriting=gaya_obj,
                    pemohon=request.pengguna,
                    media_url=json.dumps(trusted_image_urls),
                    tipe_media=tipe_media,
                    caption_generated=final_caption,
                    status='PUBLISHED',
                    waktu_dipublikasi=timezone.now(),
                    ig_post_id=published_post_id
                )

                context['success_msg'] = f"🎉 Sukses! Postingan berhasil diunggah ke {akun_ig_terpilih.nama_akun} dan tersimpan di Database!"
                
            except Exception as e:
                context['error_ig'] = str(e)
                context['hasil_caption'] = final_caption
                context['image_urls_json'] = json.dumps(raw_image_urls)
                context['image_urls'] = raw_image_urls 

        # ==========================================
        # ACTION: GENERATE / REGENERATE CAPTION
        # ==========================================
        elif action in ['generate', 'regenerate']:
            bidang = request.POST.get('bidang')
            gaya_id = request.POST.get('gaya')
            cropped_images_json_str = request.POST.get('cropped_images_json', '[]')
            existing_image_urls_json = request.POST.get('image_urls', '[]')

            uploaded_file_urls = []
            local_file_paths = []

            if bidang and gaya_id:
                try:
                    fs = FileSystemStorage()
                    if action == 'generate':
                        cropped_images_data = json.loads(cropped_images_json_str)
                        if not cropped_images_data:
                            raise Exception("Harap unggah minimal 1 gambar terlebih dahulu untuk memulai!")
                        
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
                                local_file_paths.append(fs.path(filename))

                    elif action == 'regenerate':
                        uploaded_file_urls = json.loads(existing_image_urls_json) if isinstance(existing_image_urls_json, str) else existing_image_urls_json
                        for url in uploaded_file_urls:
                            fname = url.split('/')[-1]
                            if fs.exists(fname):
                                local_file_paths.append(fs.path(fname))

                except Exception as e:
                    context['error'] = str(e)

            if len(uploaded_file_urls) > 0 and not context.get('error'):
                provider = config.ai_provider
                try:
                    context['image_urls'] = uploaded_file_urls
                    context['image_urls_json'] = json.dumps(uploaded_file_urls)
                    gaya_terpilih = GayaCopywriting.objects.get(id=gaya_id)

                    detail_info = ""
                    for key, value in request.POST.items():
                        if key not in ['csrfmiddlewaretoken', 'bidang', 'gaya', 'action', 'image_urls', 'final_caption', 'gambar', 'cropped_images_json', 'ig_account_id'] and value.strip() != "":
                            label = key.replace('_', ' ').title()
                            detail_info += f"- {label}: {value}\n"

                    prompt = f"Sebagai seorang copywriter Humas Kecamatan Mojoroto Kota Kediri, buat caption Instagram menarik untuk kategori {bidang}.\n\nDetail:\n{detail_info}\nInstruksi Gaya:\n{gaya_terpilih.prompt}\n"
                    prompt += "Berikan SATU hasil caption saja. Tanpa tag [HEADER], sertakan CTA dan hashtag. JANGAN gunakan bintang (**) untuk cetak tebal."

                    if provider == 'gemini':
                        genai.configure(api_key=config.gemini_api_key)
                        model = genai.GenerativeModel(config.gemini_model.replace('models/', '').strip())

                        # Perkecil gambar KHUSUS untuk dikirim ke AI (mempercepat upload &
                        # inferensi) -- file asli di disk (yang dipakai untuk posting ke IG)
                        # TIDAK disentuh sama sekali, resolusinya tetap penuh.
                        MAX_DIM_FOR_AI = 1024
                        pil_images = []
                        for p in local_file_paths:
                            if os.path.exists(p):
                                im = Image.open(p)
                                im.thumbnail((MAX_DIM_FOR_AI, MAX_DIM_FOR_AI), Image.LANCZOS)
                                pil_images.append(im)

                        response = model.generate_content([prompt] + pil_images)
                        hasil_raw = response.text
                    elif provider == 'groq':
                        headers = {"Authorization": f"Bearer {config.groq_api_key}", "Content-Type": "application/json"}
                        payload = {"model": config.groq_model, "messages": [{"role": "user", "content": prompt}]}
                        res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
                        hasil_raw = res.json()['choices'][0]['message']['content']

                    context['hasil_caption'] = hasil_raw.replace('**', '')

                except Exception as e:
                    err_str = str(e)

                    # Coba ekstrak waktu tunggu (retry_delay) dari error rate-limit
                    # Gemini, entah dari format "retry_delay { seconds: 19 }" atau
                    # "Please retry in 19.71s".
                    retry_seconds = None
                    m = re.search(r'retry_delay\s*\{\s*seconds:\s*(\d+)', err_str)
                    if not m:
                        m = re.search(r'retry in\s*([\d.]+)\s*s', err_str, re.IGNORECASE)
                    if m:
                        retry_seconds = int(float(m.group(1))) + 1  # +1 detik buffer

                    if '429' in err_str or 'quota' in err_str.lower() or 'RESOURCE_EXHAUSTED' in err_str:
                        context['error'] = "⚠️ Batas kuota API Gemini tercapai untuk saat ini."
                        if retry_seconds:
                            context['retry_after'] = retry_seconds
                    else:
                        # Error lain: potong biar tidak menampilkan traceback/JSON panjang
                        short_msg = err_str.strip().split('\n')[0]
                        if len(short_msg) > 180:
                            short_msg = short_msg[:180] + '...'
                        context['error'] = f"Gagal menghasilkan caption: {short_msg}"

    return render(request, 'index.html', context)