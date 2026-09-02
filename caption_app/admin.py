from django.contrib import admin
from django.contrib.auth.models import Group
from .models import GayaCopywriting, PengaturanAPI, BidangUsaha, FieldBidang, PenggunaBiasa, AkunInstagram
from django.urls import reverse
from django.utils.html import format_html
from django.conf import settings 
# Impor helper get_config dari views.py Anda
from .views import get_config

admin.site.unregister(Group)
admin.site.site_header = "Panel Admin"
admin.site.site_title = "Admin Studio Copywriting"
admin.site.index_title = "Manajemen Database Copywriting"

@admin.register(GayaCopywriting)
class GayaCopywritingAdmin(admin.ModelAdmin):
    list_display = ('nama', 'tampilkan_prompt_pendek')
    search_fields = ('nama', 'prompt')
    ordering = ('nama',)

    def tampilkan_prompt_pendek(self, obj):
        if len(obj.prompt) > 80:
            return f"{obj.prompt[:80]}..."
        return obj.prompt
    
    tampilkan_prompt_pendek.short_description = "Instruksi AI"


# @admin.register(PengaturanAPI)
# class PengaturanAPIAdmin(admin.ModelAdmin):
#     list_display = ("__str__", "ai_provider", "diperbarui_pada")

#     # Tambahkan 'tampil_token_facebook' ke dalam readonly_fields
#     readonly_fields = (
#         "tombol_oauth_facebook",
#         "tampil_token_facebook",
#         "status_env_gemini",
#         "status_env_groq",
#     )

#     fieldsets = (
#         (
#             "MESIN AI UTAMA",
#             {
#                 "fields": ("ai_provider",),
#                 "description": "Pilih mesin AI yang aktif untuk memproses caption.",
#             },
#         ),
#         (
#             "STATUS KREDENSIAL (.ENV)",
#             {
#                 "fields": ("status_env_gemini", "status_env_groq"),
#                 "description": "Status kunci API yang terdeteksi dari file .env server.",
#             },
#         ),
#         (
#             "OTORISASI METADATA / FACEBOOK",
#             {
#                 "fields": ("tombol_oauth_facebook", "tampil_token_facebook"),
#                 "description": "Klik tombol di bawah untuk memperbarui token akses Meta. Token yang aktif akan ditampilkan di bawah ini.",
#             },
#         ),
#     )

#     def status_env_gemini(self, obj):
#         key = getattr(settings, "GEMINI_API_KEY", "")
#         if key:
#             return format_html(
#                 '<span style="color: green; font-weight: bold;">✔ Terhubung</span>'
#             )
#         return format_html(
#             '<span style="color: red; font-weight: bold;">❌ Belum Diset di .env</span>'
#         )

#     status_env_gemini.short_description = "Gemini API Key"

#     def status_env_groq(self, obj):
#         key = getattr(settings, "GROQ_API_KEY", "")
#         if key:
#             return format_html(
#                 '<span style="color: green; font-weight: bold;">✔ Terhubung</span>'
#             )
#         return format_html(
#             '<span style="color: red; font-weight: bold;">❌ Belum Diset di .env</span>'
#         )

#     status_env_groq.short_description = "Groq API Key"

#     def tombol_oauth_facebook(self, obj):
#         url = reverse("facebook_login")
#         return format_html(
#             '<a class="button" style="background-color: #1877F2; color: white; padding: 10px 15px; text-decoration: none; border-radius: 4px; font-weight: bold; display: inline-block;" href="{}" target="_blank">'
#             "🔗 Otorisasi & Ambil Access Token Otomatis"
#             "</a>",
#             url,
#         )

#     tombol_oauth_facebook.short_description = "Otorisasi Meta / Facebook"

#     # METHOD BARU: Menampilkan Token dan Detail Meta di Admin Panel
#     def tampil_token_facebook(self, obj):
#         config = get_config()
#         token = config.ig_access_token
#         ig_id = config.ig_account_id

#         if token:
#             return format_html(
#                 '<div style="background: #2d3748; color: #68d391; padding: 12px; border-radius: 6px; font-family: monospace;">'
#                 '<strong>Status:</strong> <span style="color: #68d391;">✔ TERHUBUNG</span><br>'
#                 '<strong>IG Account ID:</strong> {}<br><br>'
#                 '<strong>Access Token:</strong><br>'
#                 '<textarea readonly onclick="this.select()" style="width: 100%; height: 70px; background: #1a202c; color: #68d391; border: 1px solid #4a5568; border-radius: 4px; padding: 6px; font-family: monospace; font-size: 11px;">{}</textarea>'
#                 '</div>',
#                 ig_id or "Belum Diset",
#                 token
#             )
#         return format_html(
#             '<span style="color: red; font-weight: bold;">❌ Token belum tersedia. Klik tombol otorisasi di atas.</span>'
#         )

#     tampil_token_facebook.short_description = "Detail Access Token Terambil"

#     def has_add_permission(self, request):
#         if self.model.objects.exists():
#             return False
#         return True
    


class FieldBidangInline(admin.TabularInline):
    model = FieldBidang
    extra = 1

@admin.register(BidangUsaha)
class BidangUsahaAdmin(admin.ModelAdmin):
    list_display = ('nama', 'preview_ikon')
    fields = ('nama', 'ikon', 'ikon_gambar')
    inlines = [FieldBidangInline]

    def preview_ikon(self, obj):
        if obj.ikon_gambar:
            return format_html('<img src="{}" style="height:24px; width:24px; object-fit:contain;">', obj.ikon_gambar.url)
        if obj.ikon:
            return obj.ikon
        return "-"

    preview_ikon.short_description = "Ikon"


# ==========================================
# AKUN INSTAGRAM — assign manual "pengelola" (PenggunaBiasa)
# ==========================================
# Koneksi OAuth (facebook_login/facebook_callback) tidak lagi auto-assign
# pengelola, karena yang memicu OAuth itu Staff/Admin (django auth User),
# sedangkan pengelola akun IG sekarang PenggunaBiasa (sistem login terpisah).
# Jadi staff WAJIB assign manual di sini siapa saja PenggunaBiasa yang boleh
# pakai akun Instagram tertentu.
@admin.register(AkunInstagram)
class AkunInstagramAdmin(admin.ModelAdmin):
    # Template custom yang menambahkan tombol "Hubungkan Akun Instagram Baru"
    # di halaman daftar (lihat caption_app/templates/admin/caption_app/akuninstagram/change_list.html)
    change_list_template = "admin/caption_app/akuninstagram/change_list.html"

    list_display = ('nama_akun', 'ig_account_id', 'is_active', 'jumlah_pengelola', 'diperbarui_pada')
    list_filter = ('is_active',)
    search_fields = ('nama_akun', 'ig_account_id')
    filter_horizontal = ('pengelola',)  # widget dua-kolom, mudah dicari & pilih banyak

    # ig_account_id & ig_access_token SELALU diisi otomatis lewat proses OAuth
    # Instagram Login -- tidak pernah diketik manual, makanya read-only di sini.
    readonly_fields = ('ig_account_id', 'ig_access_token', 'dibuat_pada', 'diperbarui_pada')
    fields = ('nama_akun', 'ig_account_id', 'is_active', 'pengelola', 'ig_access_token', 'dibuat_pada', 'diperbarui_pada')

    def jumlah_pengelola(self, obj):
        return obj.pengelola.count()
    jumlah_pengelola.short_description = "Jml Pengelola"

    def has_add_permission(self, request):
        # Penambahan akun HANYA lewat tombol "Hubungkan Akun Instagram Baru"
        # (redirect ke OAuth Instagram Login) -- bukan form tambah manual,
        # supaya ig_account_id & ig_access_token tidak pernah salah ketik.
        return False

# ==========================================
# DAFTAR PENGGUNA (READ-ONLY & MASKED)
# ==========================================
# Halaman ini murni untuk MELIHAT bahwa akun sudah terdaftar.
# - Semua kolom yang ditampilkan sudah dimasking di level model (models.py),
#   jadi admin tidak pernah melihat nama/email/telepon/password asli di sini.
# - Tidak ada form tambah/ubah data pengguna sama sekali dari admin.
@admin.register(PenggunaBiasa)
class PenggunaBiasaAdmin(admin.ModelAdmin):
    list_display = ('nama_col', 'email_col', 'telepon_col', 'password_col', 'created_at')
    list_display_links = None  # baris tidak diklik agar tidak masuk ke form apa pun
    ordering = ('-created_at',)
    list_per_page = 25
    search_fields = []  # sengaja kosong: cegah admin mencari data asli lewat query pencarian

    # Kalau suatu saat ada yang bisa klik ke halaman detail (view-only),
    # PASTIKAN field yang tampil tetap versi masked, BUKAN field mentah model.
    fields = ('nama_col', 'email_col', 'telepon_col', 'password_col', 'created_at', 'updated_at')
    readonly_fields = fields

    def nama_col(self, obj):
        return obj.nama_masked
    nama_col.short_description = "Nama"

    def email_col(self, obj):
        return obj.email_masked
    email_col.short_description = "Email"

    def telepon_col(self, obj):
        return obj.telepon_masked
    telepon_col.short_description = "No. Telepon"

    def password_col(self, obj):
        return obj.password_masked
    password_col.short_description = "Password"

    # Admin (bahkan superuser) tidak boleh menambah/mengubah/membongkar data pengguna manual.
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_staff

    def has_delete_permission(self, request, obj=None):
        # Opsional: hanya superuser yang boleh menghapus akun bermasalah.
        # Data tetap tidak pernah bisa dibaca mentah walau dihapus.
        return request.user.is_superuser