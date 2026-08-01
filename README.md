# AI Copywriting & Auto-Post IG Studio

Aplikasi web berbasis Django untuk membantu pengguna membuat caption Instagram menggunakan AI dan mempublikasikan konten secara langsung ke Instagram.

Mendukung Google Gemini dan Groq untuk pembuatan caption, serta Meta Graph API dan Cloudinary untuk proses publikasi dan pengelolaan media.

## Fitur

* Generate caption menggunakan Google Gemini atau Groq.
* Pilihan gaya penulisan yang dapat dikelola melalui Django Admin.
* Form dinamis berdasarkan bidang usaha.
* Upload dan crop gambar menggunakan Cropper.js.
* Publikasi otomatis ke Instagram Business.
* Mendukung Single Image dan Carousel.
* Penyimpanan media menggunakan Cloudinary.
* Pengelolaan API Key dan kredensial melalui Django Admin.

## Teknologi

* Python 3
* Django 5
* Google Gemini
* Groq
* Meta Graph API
* Cloudinary
* Cropper.js
* Pillow
* SQLite
* HTML, CSS, JavaScript

## Instalasi

Clone repository:

```bash
git clone https://github.com/aruhaxs/genai-copywriting.git
cd genai-copywriting
```

Buat virtual environment:

```bash
python -m venv venv
```

Aktifkan virtual environment.

Windows:

```bash
venv\Scripts\activate
```

Linux/macOS:

```bash
source venv/bin/activate
```

Install dependency:

```bash
pip install -r requirements.txt
```

Jalankan migration:

```bash
python manage.py migrate
```

Buat akun administrator:

```bash
python manage.py createsuperuser
```

Jalankan aplikasi:

```bash
python manage.py runserver
```

Akses aplikasi melalui:

```text
http://127.0.0.1:8000/
```

Panel admin:

```text
http://127.0.0.1:8000/admin/
```

## Konfigurasi

Konfigurasi API dan kredensial dapat dilakukan melalui Django Admin.

Beberapa konfigurasi yang diperlukan:

* Gemini API Key
* Groq API Key
* Cloudinary Credentials
* Facebook App ID
* Facebook App Secret
* Instagram Account ID
* Instagram Access Token

## Penggunaan

1. Upload satu atau beberapa gambar.
2. Sesuaikan gambar menggunakan fitur crop.
3. Pilih bidang usaha.
4. Isi informasi konten.
5. Pilih gaya penulisan.
6. Generate caption.
7. Periksa hasil caption.
8. Publikasikan ke Instagram.

## Keamanan

Jangan menyimpan API Key, Access Token, App Secret, atau kredensial lainnya secara langsung di repository.

Gunakan environment variable atau konfigurasi Django Admin dan pastikan kredensial sensitif tidak di-*commit* ke Git.

## Repository

https://github.com/aruhaxs/genai-copywriting.git
