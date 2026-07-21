# ✨ AI Copywriting Studio

Aplikasi web berbasis Django yang terintegrasi dengan Google Gemini API untuk membantu *copywriter* dan pemilik usaha membuat *caption* Instagram secara otomatis, cepat, dan profesional.

## 🚀 Fitur Utama

*   **20+ Pilihan Bidang Usaha:** Form dinamis menggunakan JavaScript yang otomatis menyesuaikan isian berdasarkan bidang yang dipilih (Kuliner, Fashion, Jasa, Properti, dll).
*   **Gaya Penulisan Dinamis (Database-Driven):** Admin dapat menambahkan, mengedit, atau menghapus instruksi (*prompt*) gaya penulisan secara bebas melalui panel Admin Django (misal: Casual, Profesional, Persuasif).
*   **3 Alternatif Caption AI:** Terintegrasi dengan model AI terbaru (Gemini 1.5 Flash) yang dikonfigurasi secara ketat untuk langsung memberikan 3 pilihan *caption* yang rapi, bersih, dan siap disalin.

## 🛠️ Teknologi yang Digunakan

*   **Backend:** Python 3, Django 5
*   **Frontend:** HTML5, CSS3, Vanilla JavaScript
*   **AI Engine:** Google Generative AI SDK
*   **Database:** SQLite (Bawaan Django)

---

## ⚙️ Cara Menjalankan Proyek (Panduan Kolaborator)

Ikuti langkah-langkah di bawah ini untuk menjalankan dan mengembangkan proyek ini di komputer lokalmu.

### 1. Clone Repositori
Buka terminal/CMD dan jalankan perintah berikut untuk mengunduh kode:
```bash
git clone [https://github.com/aruhaxs/genai-copywriting.git](https://github.com/aruhaxs/genai-copywriting.git)
cd genai-copywriting
```

### 2. Instal Library yang Dibutuhkan
Pastikan Python sudah terinstal, lalu jalankan:
```bash
pip install django google-generativeai python-dotenv
```

### 3. Konfigurasi API Key (Wajib)
Proyek ini membutuhkan API Key dari Google Gemini agar AI bisa bekerja.
1. Buat file baru bernama persis `.env` di folder utama proyek (sejajar dengan file `manage.py`).
2. Buka file `.env` tersebut dan isi dengan kode berikut (tanpa tanda kutip):
```text
GEMINI_API_KEY=masukkan_api_key_kamu_di_sini
```

### 4. Persiapkan Database & Akun Admin
Jalankan migrasi agar struktur database terbentuk, lalu buat akun admin untuk mengelola "Gaya Penulisan":
```bash
python manage.py migrate
python manage.py createsuperuser
```
*(Ikuti instruksi di layar untuk mengisi username, email, dan password admin).*

### 5. Jalankan Server Lokal
```bash
python manage.py runserver
```

### 6. Mulai Menggunakan
*   **Halaman Utama (Generator):** Buka `http://127.0.0.1:8000/` di browsermu.
*   **Halaman Admin (Kelola Gaya):** Buka `http://127.0.0.1:8000/admin/` dan login menggunakan akun yang baru saja dibuat untuk menambahkan jenis gaya *copywriting*.
