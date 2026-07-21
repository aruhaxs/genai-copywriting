from django.contrib import admin
from django.contrib.auth.models import Group
from .models import GayaCopywriting

admin.site.unregister(Group)
admin.site.site_header = "Panel Admin AI Copywriting"
admin.site.site_title = "Admin Studio Copywriting"
admin.site.index_title = "Manajemen Database Copywriting"

@admin.register(GayaCopywriting)
class GayaCopywritingAdmin(admin.ModelAdmin):
    list_display = ('nama', 'tampilkan_prompt_pendek')
    
    search_fields = ('nama', 'prompt')
    
    # Mengurutkan daftar berdasarkan abjad nama gaya
    ordering = ('nama',)

    # Fungsi agar teks instruksi/prompt yang terlalu panjang dipotong di tabel
    # supaya tampilan tabel tidak melebar dan berantakan
    def tampilkan_prompt_pendek(self, obj):
        if len(obj.prompt) > 80:
            return f"{obj.prompt[:80]}..."
        return obj.prompt
    
    # Mengubah nama kolom tabel
    tampilkan_prompt_pendek.short_description = "Instruksi AI"