from django.db import models

class GayaCopywriting(models.Model):
    nama = models.CharField(max_length=100)
    prompt = models.TextField()

    def __str__(self):
        return self.nama

class PengaturanAPI(models.Model):
    gemini_api_key = models.CharField(max_length=255, blank=True, null=True)
    ig_access_token = models.TextField(blank=True, null=True)
    ig_account_id = models.CharField(max_length=100, blank=True, null=True)
    diperbarui_pada = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Pengaturan API & Token (Hanya ada 1 baris data)"