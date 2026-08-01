from django.db import models

class GayaCopywriting(models.Model):
    nama = models.CharField(max_length=100)
    prompt = models.TextField()

    def __str__(self):
        return self.nama

class PengaturanAPI(models.Model):
    PROVIDER_CHOICES = [
        ('gemini', 'Google Gemini'),
        ('groq', 'Groq Cloud'),
    ]
    
    ai_provider = models.CharField(
        max_length=20, 
        choices=PROVIDER_CHOICES, 
        default='gemini', 
        verbose_name="Penyedia AI Aktif"
    )
    
    gemini_api_key = models.CharField(max_length=255, blank=True, null=True, verbose_name="API Key Gemini")
    gemini_model = models.CharField(max_length=100, default='gemini-flash-latest', verbose_name="Nama Model Gemini")

    groq_api_key = models.CharField(max_length=255, blank=True, null=True, verbose_name="API Key Groq")
    groq_model = models.CharField(max_length=100, default='llama-3.3-70b-versatile', verbose_name="Nama Model Groq")

    ig_access_token = models.TextField(blank=True, null=True, verbose_name="Token Akses IG")
    ig_account_id = models.CharField(max_length=100, blank=True, null=True, verbose_name="ID Akun IG")
    cloudinary_creds = models.CharField(max_length=255, blank=True, null=True, verbose_name="Kredensial Cloudinary")
    
    fb_app_id = models.CharField(max_length=100, blank=True, null=True, verbose_name="Facebook App ID")
    fb_app_secret = models.CharField(max_length=255, blank=True, null=True, verbose_name="Facebook App Secret")

    diperbarui_pada = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Pengaturan Sistem, API & Kredensial"

class BidangUsaha(models.Model):
    nama = models.CharField(max_length=100, verbose_name="Nama Bidang Usaha")
    ikon = models.CharField(max_length=20, default="📌", help_text="Gunakan Emoji/Ikon")

    def __str__(self):
        return self.nama
    
    class Meta:
        verbose_name_plural = "Bidang Usaha"

class FieldBidang(models.Model):
    bidang = models.ForeignKey(BidangUsaha, related_name='fields', on_delete=models.CASCADE)
    label = models.CharField(max_length=100, help_text="Teks yang tampil, Contoh: Nama Resto/Cafe")
    name_attribute = models.SlugField(max_length=50, help_text="Variabel sistem (Huruf kecil & tanpa spasi), Contoh: nama_resto")
    placeholder = models.CharField(max_length=150, blank=True, null=True, help_text="Teks bayangan di dalam kotak")

    def __str__(self):
        return self.label
    