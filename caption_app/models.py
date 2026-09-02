from django.db import models
from django.core.validators import FileExtensionValidator
from django.contrib.auth.models import User

import os
from io import BytesIO
from PIL import Image as PILImage
from django.contrib.auth.hashers import make_password, check_password
from django.core.files.uploadedfile import InMemoryUploadedFile

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
    """
    Kredensial Global untuk Sistem (AI Engine & Cloud Storage/Cloudinary).
    """
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

    cloudinary_creds = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        verbose_name="Kredensial Cloudinary",
        help_text="Format: CloudName,APIKey,APISecret"
    )
    
    fb_app_id = models.CharField(max_length=100, blank=True, null=True, verbose_name="Facebook App ID (Legacy, tidak dipakai lagi)")
    fb_app_secret = models.CharField(max_length=255, blank=True, null=True, verbose_name="Facebook App Secret (Legacy, tidak dipakai lagi)")

    ig_app_id = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Instagram App ID",
        help_text="Diambil dari App Dashboard → Instagram → API setup with Instagram login"
    )
    ig_app_secret = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="Instagram App Secret",
        help_text="Diambil dari App Dashboard → Instagram → API setup with Instagram login"
    )

    diperbarui_pada = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Pengaturan API & Sistem Global"

    class Meta:
        verbose_name_plural = "Pengaturan API & Sistem"


class AkunInstagram(models.Model):
    """
    Model untuk mendukung Multi-Akun Instagram.
    """
    nama_akun = models.CharField(max_length=100, help_text="Contoh: @humas_pemkot / @diskominfo")
    ig_account_id = models.CharField(max_length=100, verbose_name="ID Akun Instagram")
    ig_access_token = models.TextField(verbose_name="Token Akses IG (Long-Lived)")
    
    pengelola = models.ManyToManyField(
        'PenggunaBiasa',
        related_name='akun_instagram_list',
        blank=True,
        help_text="Pengguna Biasa yang diizinkan mengunggah ke akun ini"
    )
    
    is_active = models.BooleanField(default=True, verbose_name="Status Aktif")
    dibuat_pada = models.DateTimeField(auto_now_add=True)
    diperbarui_pada = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.nama_akun} (ID: {self.ig_account_id})"

    class Meta:
        verbose_name_plural = "Akun Instagram"


class BidangUsaha(models.Model):
    """
    Kategori Konten / Sektor Pelayanan Publik
    """
    nama = models.CharField(max_length=100, verbose_name="Kategori Konten")
    ikon = models.CharField(
        max_length=20, blank=True, null=True,
        verbose_name="Ikon (Emoji)",
        help_text="Opsional. Gunakan Emoji/Ikon teks, contoh: 📌. Boleh dikosongkan kalau pakai upload gambar di bawah."
    )
    ikon_gambar = models.FileField(
        upload_to='ikon_bidang/', blank=True, null=True,
        verbose_name="Ikon (File Gambar)",
        validators=[FileExtensionValidator(allowed_extensions=['svg', 'png', 'jpg', 'jpeg', 'gif', 'webp'])],
        help_text="Opsional. Unggah file ikon (SVG, PNG, JPG, GIF, atau WEBP). Kalau diisi, ini dipakai duluan daripada emoji di atas."
    )

    def __str__(self):
        return self.nama
    
    class Meta:
        verbose_name_plural = "Kategori Konten"


class FieldBidang(models.Model):
    """
    Inputan dinamis yang muncul di form berdasarkan Kategori Konten
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
    pilihan_select = models.CharField(
        max_length=500, blank=True, null=True,
        verbose_name="Pilihan (khusus tipe Dropdown Select)",
        help_text="Isi pilihan dipisah koma. Contoh: Aktif,Nonaktif,Pending"
    )
    is_required = models.BooleanField(default=True, verbose_name="Wajib Diisi?")

    def get_pilihan_list(self):
        """Dipakai di template untuk render <option> pada tipe select."""
        if not self.pilihan_select:
            return []
        return [p.strip() for p in self.pilihan_select.split(',') if p.strip()]

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

    target_akun_ig = models.ForeignKey(
        AkunInstagram, 
        on_delete=models.SET_NULL, 
        null=True,
        blank=True,
        related_name='postingan',
        verbose_name="Target Akun Instagram"
    )

    kategori_konten = models.ForeignKey(BidangUsaha, on_delete=models.SET_NULL, null=True)
    gaya_copywriting = models.ForeignKey(GayaCopywriting, on_delete=models.SET_NULL, null=True)
    pemohon = models.ForeignKey('PenggunaBiasa', on_delete=models.CASCADE, related_name='postingan_dibuat')
    
    dynamic_form_data = models.JSONField(
        default=dict, 
        blank=True,
        help_text="Menyimpan pasangan {name_attribute: value} dari FieldBidang"
    )

    media_url = models.TextField(verbose_name="URL File Media (Bisa JSON List untuk Carousel / Text URL)")
    tipe_media = models.CharField(max_length=20, choices=TIPE_MEDIA_CHOICES, default='IMAGE')
    caption_generated = models.TextField(verbose_name="Caption Hasil AI / Final")
    hashtag = models.TextField(blank=True, null=True, help_text="Tagar wajib instansi & tagar tambahan")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    waktu_dijadwalkan = models.DateTimeField(blank=True, null=True, verbose_name="Jadwal Upload IG")
    waktu_dipublikasi = models.DateTimeField(blank=True, null=True)

    ig_post_id = models.CharField(max_length=100, blank=True, null=True, verbose_name="ID Postingan Instagram")
    error_log = models.TextField(blank=True, null=True, verbose_name="Log Error API (Jika Gagal)")

    dibuat_pada = models.DateTimeField(auto_now_add=True)
    diperbarui_pada = models.DateTimeField(auto_now=True)

    def __str__(self):
        target = self.target_akun_ig.nama_akun if self.target_akun_ig else "Belum Ditetapkan"
        return f"[{self.get_status_display()}] {target} - {self.pemohon.nama}"

    class Meta:
        verbose_name_plural = "Konten Postingan Instagram"


class CatatanApproval(models.Model):
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

# ==========================================
# 3. AKUN PENGGUNA BIASA (TERPISAH DARI ADMIN)
# ==========================================
# PENTING: Model ini SENGAJA dipisah total dari django.contrib.auth.User
# yang dipakai untuk login Admin/Panel Django Admin. Tabel, proses
# autentikasi, dan session-nya semua berjalan independen supaya akun
# admin dan akun pengguna biasa tidak pernah bisa saling dipakai untuk
# login di form yang salah.

class PenggunaBiasa(models.Model):
    nama = models.CharField(max_length=150, verbose_name="Nama Lengkap")
    email = models.EmailField(max_length=255, unique=True, verbose_name="Email")
    no_telepon = models.CharField(max_length=20, blank=True, null=True, verbose_name="Nomor Telepon")

    # Hash password (Django PBKDF2 by default). TIDAK PERNAH menyimpan plaintext,
    # dan tidak pernah ditampilkan mentah di admin maupun di frontend mana pun.
    password = models.CharField(max_length=255, verbose_name="Password (Hash)")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Terdaftar Pada")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Diperbarui Pada")

    class Meta:
        verbose_name = "Pengguna"
        verbose_name_plural = "Daftar Pengguna"
        ordering = ['-created_at']

    def __str__(self):
        return self.nama

    # ---- Password handling ----
    def set_password(self, raw_password):
        """Hash & simpan password. Selalu panggil ini, jangan set .password langsung."""
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        """Verifikasi password saat login tanpa pernah membongkar hash-nya."""
        return check_password(raw_password, self.password)

    # ---- Masking untuk ditampilkan ke Admin (dilakukan di backend/server) ----
    @staticmethod
    def _mask_tail(value, keep_start=2, star_count=8):
        if not value:
            return "-"
        value = str(value)
        keep = value[:keep_start]
        return f"{keep}{'*' * star_count}"

    @property
    def nama_masked(self):
        return self._mask_tail(self.nama, keep_start=2)

    @property
    def email_masked(self):
        if not self.email or '@' not in self.email:
            return self._mask_tail(self.email, keep_start=3)
        local, domain = self.email.split('@', 1)
        keep = local[:3]
        return f"{keep}{'*' * 8}@{domain}"

    @property
    def telepon_masked(self):
        if not self.no_telepon:
            return "-"
        tel = self.no_telepon
        if len(tel) <= 4:
            return "*" * 8
        return f"{tel[:2]}{'*' * 8}{tel[-2:]}"

    @property
    def password_masked(self):
        return "********"