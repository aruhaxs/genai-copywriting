from django.db import models

class GayaCopywriting(models.Model):
    nama = models.CharField(max_length=100, verbose_name="Nama Gaya (Contoh: Casual)")
    prompt = models.TextField(verbose_name="Instruksi AI (Contoh: Gunakan bahasa santai, gaul, dan kekinian)")

    def __str__(self):
        return self.nama