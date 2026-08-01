from django.contrib import admin
from django.contrib.auth.models import Group
from .models import GayaCopywriting, PengaturanAPI, BidangUsaha, FieldBidang

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

@admin.register(PengaturanAPI)
class PengaturanAPIAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'ai_provider', 'diperbarui_pada')
    
    fieldsets = (
        ('MESIN AI UTAMA', {
            'fields': ('ai_provider',),
            'description': 'Pilih mesin AI yang aktif untuk memproses caption.',
        }),
        ('GOOGLE GEMINI', {
            'fields': ('gemini_api_key', 'gemini_model'),
            'description': 'Pengaturan untuk Google Gemini.',
            'classes': ('collapse',),
        }),
        ('GROQ CLOUD', {
            'fields': ('groq_api_key', 'groq_model'),
            'description': 'Pengaturan untuk model super cepat Groq.',
            'classes': ('collapse',),
        }),
        ('KREDENSIAL Cloudinary', {
            'fields': ('cloudinary_creds',),
            'description': 'Format: CloudName,APIKey,APISecret (tanpa spasi).',
        }),
        ('TOKEN Instagram', {
            'fields': ('ig_access_token', 'ig_account_id', 'fb_app_id', 'fb_app_secret'),
        }),
    )

    def has_add_permission(self, request):
        if self.model.objects.exists():
            return False
        return True

class FieldBidangInline(admin.TabularInline):
    model = FieldBidang
    extra = 1

@admin.register(BidangUsaha)
class BidangUsahaAdmin(admin.ModelAdmin):
    list_display = ('nama', 'ikon')
    inlines = [FieldBidangInline]
    