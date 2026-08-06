from django.db import migrations

def populate_initial_data(apps, schema_editor):
    # Ambil model dari konteks migrasi
    GayaCopywriting = apps.get_model('caption_app', 'GayaCopywriting')
    BidangUsaha = apps.get_model('caption_app', 'BidangUsaha')
    FieldBidang = apps.get_model('caption_app', 'FieldBidang')

    # ==========================================
    # 1. ISI MODEL: GayaCopywriting
    # ==========================================
    gaya_data = [
        {
            "nama": "Formal & Resmi",
            "prompt": (
                "Kamu adalah Spesialis Kehumasan Pemerintah. Buat caption Instagram resmi berdasarkan data berikut:\n"
                "- Topik: {topik}\n- Poin Utama: {poin_utama}\n- Target Audiens: {target_audiens}\n- Tagar Wajib: {hashtag}\n- CTA: {cta}\n\n"
                "Gunakan Bahasa Indonesia baku (PUEBI), bernada presisi, lugas, tanpa jargon gaul, dan terstruktur rapi."
            )
        },
        {
            "nama": "Edukatif & Ramah",
            "prompt": (
                "Kamu adalah Pranata Humas yang ramah dan edukatif. Buat caption Instagram yang komunikatif berdasarkan data berikut:\n"
                "- Topik: {topik}\n- Poin Utama: {poin_utama}\n- Target Audiens: {target_audiens}\n- Tagar Wajib: {hashtag}\n- CTA: {cta}\n\n"
                "Gunakan bahasa yang hangat, sertakan emoji relevan, buat hook menarik di awal, dan susun poin informasi menggunakan penomoran/bullet."
            )
        },
        {
            "nama": "Imbauan Publik (Urgent)",
            "prompt": (
                "Kamu adalah Tim Peringatan Dini & Imbauan Publik Pemerintah. Buat caption Instagram peringatan/imbauan mendesak:\n"
                "- Topik: {topik}\n- Poin Utama: {poin_utama}\n- Target Audiens: {target_audiens}\n- Tagar Wajib: {hashtag}\n- CTA: {cta}\n\n"
                "Gunakan nada tegas, instruktif, diawali kata kunci kapital seperti [IMBAUAN PENTING], letakkan informasi krusial di paling atas."
            )
        },
        {
            "nama": "Apresiatif & Hari Besar",
            "prompt": (
                "Kamu adalah Tim Kreatif Kehumasan Instansi Pemerintah. Buat caption Instagram bernada inspiratif dan apresiatif:\n"
                "- Topik: {topik}\n- Poin Utama: {poin_utama}\n- Target Audiens: {target_audiens}\n- Tagar Wajib: {hashtag}\n- CTA: {cta}\n\n"
                "Gunakan bahasa yang mengunggah semangat, bernada humanis, sampaikan apresiasi/pesan moral, dan ajakan untuk maju bersama."
            )
        },
    ]

    for item in gaya_data:
        GayaCopywriting.objects.get_or_create(
            nama=item["nama"],
            defaults={"prompt": item["prompt"]}
        )

    # ==========================================
    # 2. ISI MODEL: BidangUsaha & FieldBidang
    # ==========================================
    kategori_fields_map = [
        {
            "nama": "Layanan & Fasilitas Publik",
            "ikon": "🏛️",
            "fields": [
                {"label": "Nama Layanan/Fasilitas", "name_attribute": "nama_layanan", "tipe_field": "text", "placeholder": "Contoh: Layanan Paspor Simpatik / Taman Kota"},
                {"label": "Jam Operasional & Lokasi", "name_attribute": "jam_lokasi", "tipe_field": "text", "placeholder": "Contoh: Senin-Jumat 08.00-15.00 WIB di Kantor Pusat"},
                {"label": "Persyaratan Utama", "name_attribute": "persyaratan", "tipe_field": "textarea", "placeholder": "Sebutkan dokumen/syarat yang wajib dibawa warga"},
            ]
        },
        {
            "nama": "Pengumuman & Kebijakan Resmi",
            "ikon": "📢",
            "fields": [
                {"label": "Nomor & Judul Regulasi", "name_attribute": "no_regulasi", "tipe_field": "text", "placeholder": "Contoh: Permen No. 12 Tahun 2026 tentang..."},
                {"label": "Poin Kebijakan Utama", "name_attribute": "poin_kebijakan", "tipe_field": "textarea", "placeholder": "Apa perubahan/aturan baru yang berdampak ke publik?"},
                {"label": "Tanggal Tanggal Tanggal Berlaku", "name_attribute": "tanggal_berlaku", "tipe_field": "date", "placeholder": ""},
            ]
        },
        {
            "nama": "Himbauan & Peringatan Dini",
            "ikon": "⚠️",
            "fields": [
                {"label": "Jenis Potensi Bahaya/Risiko", "name_attribute": "jenis_risiko", "tipe_field": "text", "placeholder": "Contoh: Cuaca Ekstrem / Batas Akhir Pelaporan Pajak"},
                {"label": "Wilayah / Sasaran Dampak", "name_attribute": "wilayah_dampak", "tipe_field": "text", "placeholder": "Contoh: Seluruh Warga Pesisir / Wajib Pajak Badan"},
                {"label": "Langkah Tindakan Masyarakat", "name_attribute": "langkah_tindakan", "tipe_field": "textarea", "placeholder": "Sebutkan apa yang harus dan tidak boleh dilakukan"},
            ]
        },
        {
            "nama": "Laporan Kegiatan & Field Report",
            "ikon": "📸",
            "fields": [
                {"label": "Nama Agenda Kegiatan", "name_attribute": "nama_kegiatan", "tipe_field": "text", "placeholder": "Contoh: Inspecsi Lapangan Pembangunan Jembatan A"},
                {"label": "Pejabat / Pimpinan yang Hadir", "name_attribute": "pejabat_hadir", "tipe_field": "text", "placeholder": "Contoh: Dihadiri oleh Kepala Dinas & Camat"},
                {"label": "Hasil / Output Kegiatan", "name_attribute": "hasil_kegiatan", "tipe_field": "textarea", "placeholder": "Apa capaian atau kesepakatan dari acara tersebut?"},
            ]
        },
    ]

    for item in kategori_fields_map:
        bidang_obj, _ = BidangUsaha.objects.get_or_create(
            nama=item["nama"],
            defaults={"ikon": item["ikon"]}
        )
        
        for field in item["fields"]:
            FieldBidang.objects.get_or_create(
                bidang=bidang_obj,
                name_attribute=field["name_attribute"],
                defaults={
                    "label": field["label"],
                    "tipe_field": field["tipe_field"],
                    "placeholder": field["placeholder"],
                    "is_required": True,
                }
            )

def reverse_populate(apps, schema_editor):
    # Fungsi rollback jika migrasi dibatalkan
    GayaCopywriting = apps.get_model('caption_app', 'GayaCopywriting')
    BidangUsaha = apps.get_model('caption_app', 'BidangUsaha')
    FieldBidang = apps.get_model('caption_app', 'FieldBidang')

    GayaCopywriting.objects.all().delete()
    FieldBidang.objects.all().delete()
    BidangUsaha.objects.all().delete()

class Migration(migrations.Migration):

    dependencies = [
        # Pastikan menunjuk ke migrasi sebelum file ini
        ('caption_app', '0010_alter_bidangusaha_options_and_more'), 
    ]

    operations = [
        migrations.RunPython(populate_initial_data, reverse_populate),
    ]