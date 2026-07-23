from django.contrib import admin
from django.contrib.auth.models import Group
from .models import GayaCopywriting, PengaturanAPI

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

# --- MENAMBAHKAN PENGATURAN API KE ADMIN ---
@admin.register(PengaturanAPI)
class PengaturanAPIAdmin(admin.ModelAdmin):
    # Tampilan kolom di tabel depan
    list_display = ('__str__', 'diperbarui_pada')
    
    # Mengelompokkan form agar terlihat sangat rapi dan modern
    fieldsets = (
        ('🤖 Kunci API (Google Gemini)', {
            'fields': ('gemini_api_key',),
            'description': 'Masukkan API Key Gemini di sini agar AI dapat membuat caption.',
        }),
        ('📱 Token Meta (Instagram)', {
            'fields': ('ig_access_token', 'ig_account_id'),
            'description': 'Masukkan Token Akses dan ID Akun IG. Perbarui token di sini jika sudah kadaluarsa (expired).',
        }),
    )

    # Memastikan Admin HANYA BISA mengedit, tidak bisa menambah baris baru 
    # jika pengaturan pertama sudah dibuat (karena kita hanya butuh 1 slot pengaturan)
    def has_add_permission(self, request):
        if self.model.objects.exists():
            return False
        return True
    