from django.db import models
from django.contrib.auth.models import User

# ==========================================
# 1. PENGATURAN & MASTER DATA SISTEM
# ==========================================

class GayaCopywriting(models.Model):
    nama = models.CharField(max_length=100)
    prompt = models.TextField(help_text="Gunakan placeholder seperti {topik}, {poin_utama}, {cta}, dll.")

    def __str__(self):
        return self.nama

    class Meta:
        verbose_name_plural = "Gaya Copywriting"


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

    class Meta:
        verbose_name_plural = "Pengaturan API & Sistem"


class BidangUsaha(models.Model):
    """
    Dalam konteks pemerintah, ini berfungsi sebagai 'Kategori Konten' / 'Sektor Pelayanan'
    Contoh: Layanan Publik, Kebijakan/Regulasi, Peringatan Dini, Event/Kegiatan
    """
    nama = models.CharField(max_length=100, verbose_name="Kategori Konten")
    ikon = models.CharField(max_length=20, default="📌", help_text="Gunakan Emoji/Ikon")

    def __str__(self):
        return self.nama
    
    class Meta:
        verbose_name_plural = "Kategori Konten"


class FieldBidang(models.Model):
    """
    Inputan dinamis yang akan muncul di form berdasarkan Kategori Konten yang dipilih
    """
    TIPE_FIELD_CHOICES = [
        ('text', 'Text Input'),
        ('textarea', 'Textarea / Paragraf'),
        ('select', 'Dropdown Select'),
        ('date', 'Tanggal / Date'),
    ]

    bidang = models.ForeignKey(BidangUsaha, related_name='fields', on_delete=models.CASCADE)
    label = models.CharField(max_length=100, help_text="Teks yang tampil, Contoh: Nama Regulasi / Lokasi Acara")
    name_attribute = models.SlugField(max_length=50, help_text="Variabel sistem (Huruf kecil & tanpa spasi), Contoh: nama_regulasi")
    tipe_field = models.CharField(max_length=20, choices=TIPE_FIELD_CHOICES, default='text')
    placeholder = models.CharField(max_length=150, blank=True, null=True, help_text="Teks bayangan di dalam kotak")
    is_required = models.BooleanField(default=True, verbose_name="Wajib Diisi?")

    def __str__(self):
        return f"{self.bidang.nama} - {self.label}"


# ==========================================
# 2. TRANSAKSI, POSTINGAN & WORKFLOW APPROVAL
# ==========================================

class KontenPosting(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'Draft / AI Generated'),
        ('PENDING_APPROVAL', 'Menunggu Persetujuan Humas'),
        ('APPROVED', 'Disetujui (Siap Posting / Terjadwal)'),
        ('REJECTED', 'Ditolak / Perlu Revisi'),
        ('PUBLISHED', 'Berhasil Dipublikasi'),
        ('FAILED', 'Gagal Dipublikasi'),
    ]

    TIPE_MEDIA_CHOICES = [
        ('IMAGE', 'Single Image'),
        ('CAROUSEL', 'Carousel (Multiple Images)'),
        ('REELS', 'Reels / Video Short'),
    ]

    # Relasi Form & Input Meta
    kategori_konten = models.ForeignKey(BidangUsaha, on_delete=models.SET_NULL, null=True)
    gaya_copywriting = models.ForeignKey(GayaCopywriting, on_delete=models.SET_NULL, null=True)
    pemohon = models.ForeignKey(User, on_delete=models.CASCADE, related_name='postingan_dibuat')
    
    # Inputan Dinamis Form (Disimpan dalam format JSON)
    dynamic_form_data = models.JSONField(
        default=dict, 
        help_text="Menyimpan pasangan {name_attribute: value} dari FieldBidang"
    )

    # Media & Hasil AI
    media_url = models.URLField(max_length=500, verbose_name="URL File Media (Cloudinary/S3)")
    tipe_media = models.CharField(max_length=20, choices=TIPE_MEDIA_CHOICES, default='IMAGE')
    caption_generated = models.TextField(verbose_name="Caption Hasil AI / Final")
    hashtag = models.TextField(blank=True, null=True, help_text="Tagar wajib instansi & tagar tambahan")

    # Workflow Status & Penjadwalan
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    waktu_dijadwalkan = models.DateTimeField(blank=True, null=True, verbose_name="Jadwal Upload IG")
    waktu_dipublikasi = models.DateTimeField(blank=True, null=True)

    # Response dari Meta Instagram API
    ig_post_id = models.CharField(max_length=100, blank=True, null=True, verbose_name="ID Postingan Instagram")
    error_log = models.TextField(blank=True, null=True, verbose_name="Log Error API (Jika Gagal)")

    dibuat_pada = models.DateTimeField(auto_now_add=True)
    diperbarui_pada = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"[{self.get_status_display()}] {self.kategori_konten} - {self.pemohon.username}"

    class Meta:
        verbose_name_plural = "Konten Postingan Instagram"


class CatatanApproval(models.Model):
    """
    Model untuk menampung riwayat persetujuan/revisi dari atasan/subbag Humas
    """
    konten = models.ForeignKey(KontenPosting, on_delete=models.CASCADE, related_name='approval_history')
    approver = models.ForeignKey(User, on_delete=models.CASCADE)
    status_keputusan = models.CharField(
        max_length=20, 
        choices=[('APPROVED', 'Disetujui'), ('REJECTED', 'Ditolak/Revisi')]
    )
    catatan_revisi = models.TextField(blank=True, null=True, help_text="Alasan penolakan atau instruksi revisi")
    waktu_keputusan = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.status_keputusan} oleh {self.approver.username} untuk ID #{self.konten.id}"