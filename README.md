# Mirai Self Studio 📸

Mirai Self Studio adalah aplikasi photobooth berbasis web dengan fitur **Augmented Reality (AR)** yang memungkinkan pengguna untuk berinteraksi dengan model 3D dan stiker 2D secara real-time.

## 🚀 Fitur Utama

-   **AR Interaktif**: Tampilkan model 3D (GLTF/GLB/FBX/OBJ) dan stiker 2D di dunia nyata melalui kamera.
-   **Kontrol Lengkap**:
    -   **Skala**: Sesuaikan ukuran model dari 0.1x hingga 5.0x.
    -   **Orientasi**: Putar model ke segala arah (Atas, Bawah, Kiri, Kanan) atau reset ke posisi awal.
-   **Hand Gesture**: Tunjukkan **Telapak Tangan (Open Palm)** ke kamera untuk mengambil foto secara otomatis!
-   **Multi-Format**: Mendukung berbagai format file 3D (.obj, .fbx, .gltf) dan gambar (.png, .jpg).

## 🛠️ Persyaratan Sistem

Pastikan Anda telah menginstal:
-   **Python 3.8+**
-   **Node.js** (opsional, untuk manajemen aset frontend jika diperlukan)

## 📦 Instalasi & Setup

1.  **Clone Repository** (jika belum):
    ```bash
    git clone https://github.com/your-repo/mirai.git
    cd mirai
    ```

2.  **Aktifkan Virtual Environment**:
    Project ini menggunakan environment yang berada di folder `ml-self-studio`.
    ```bash
    # Windows
    ..\ml-self-studio\.venv\Scripts\activate
    # Mac/Linux
    source ../ml-self-studio/.venv/bin/activate
    ```

3.  **Install Dependencies**:
    Dependencies project (termasuk Django) ada di `ml-self-studio/requirements.txt`.
    ```bash
    pip install -r ..\ml-self-studio\requirements.txt
    ```

4.  **Migrasi Database**:
    ```bash
    python manage.py migrate
    ```

5.  **Jalankan Server**:
    ```bash
    python manage.py runserver
    ```
    Akses aplikasi di: `http://127.0.0.1:8000/studio/`

## 🎮 Cara Penggunaan

### Menggunakan AR Studio
1.  Buka halaman Studio di browser.
2.  Izinkan akses kamera saat diminta.
3.  **Pilih Karakter**: Klik tombol ikon di bawah (misal: 🥷 Ninja, 🐦 Mordo) untuk memunculkan model.
4.  **Atur Posisi**:
    -   **Geser**: Klik dan tahan pada model untuk memindahkannya.
    -   **Zoom**: Gunakan scroll mouse atau cubit (di layar sentuh) untuk memperbesar/memperkecil (atau gunakan Slider).
    -   **Putar**: Gunakan tombol panah di layar untuk memutar model.
5.  **Ambil Foto**:
    -   Klik tombol **Shutter** di layar, ATAU
    -   Angkat **Telapak Tangan ✋** ke arah kamera. Hitung mundur akan dimulai otomatis!

### Menambahkan Model Baru
1.  Siapkan file model 3D (.fbx, .obj) atau gambar (.png).
2.  Simpan file ke dalam folder statis, misalnya `mirai/3d/`.
3.  Tambahkan tombol baru di `index.html` dengan format:
    ```html
    <button class="character-btn ..." data-model="{% static 'nama-file-anda.fbx' %}">
        <!-- Ikon/Gambar Tombol -->
    </button>
    ```

## 📂 Struktur Project
-   `mirai/` - Folder konfigurasi utama Django.
-   `studio/` - Aplikasi utama.
    -   `static/studio/js/ar_logic.js` - Logika inti AR (Three.js).
    -   `templates/studio/index.html` - Tampilan antarmuka utama.
-   `3d/` - Direktori penyimpanan aset model 3D.
