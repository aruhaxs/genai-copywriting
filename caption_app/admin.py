from django.contrib import admin
from django.contrib.auth.models import Group
from .models import GayaCopywriting, PengaturanAPI, BidangUsaha, FieldBidang
from django.urls import reverse
from django.utils.html import format_html
from django.conf import settings 
# Impor helper get_config dari views.py Anda
from .views import get_config

admin.site.unregister(Group)
admin.site.site_header = "Panel Admin AI Copywriting"
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
    list_display = ('nama', 'ikon')
    inlines = [FieldBidangInline]