# GENETICA — Optimasi Penjadwalan Kuliah dengan Algoritma Genetika Kelompok 5

**Proyek Ujian Tengah Semester (UTS) — Algoritma Genetika**  
**Program Studi S-1 Teknik Informatika**

GENETICA adalah aplikasi berbasis **Python dan Streamlit** untuk menyusun jadwal perkuliahan secara otomatis menggunakan **Algoritma Genetika (AG)**. Sistem mencari kombinasi hari, waktu, dan ruang yang meminimalkan bentrok dosen, kelas mahasiswa, dan penggunaan ruangan, dengan tetap memperhatikan kapasitas ruang.

> [!IMPORTANT]
> **Status proyek: SIMULASI AKADEMIK.** Mata kuliah dan penugasan dosen mengikuti dataset sumber, sedangkan kapasitas ruangan dan sebagian identitas kelas masih menggunakan asumsi simulasi. Jadwal dengan *fitness* 1,0 berarti tidak ditemukan pelanggaran pada **model dan data simulasi**, bukan jaminan jadwal siap diterapkan secara resmi.

**Repository:** https://github.com/Andre-Dir/UTS-Algoritma-Genetika-Penjadwalan-Kuliah

## Daftar Isi

- [1. Tujuan Proyek](#1-tujuan-proyek)
- [2. Teknologi dan Fitur](#2-teknologi-dan-fitur)
- [3. Dataset dan Batasan](#3-dataset-dan-batasan)
- [4. Cara Kerja Algoritma](#4-cara-kerja-algoritma)
- [5. Konfigurasi Otomatis dan Manual](#5-konfigurasi-otomatis-dan-manual)
- [6. Instalasi dan Menjalankan Aplikasi](#6-instalasi-dan-menjalankan-aplikasi)
- [7. Panduan Penggunaan UI](#7-panduan-penggunaan-ui)
- [8. Pengujian dan Hasil](#8-pengujian-dan-hasil)
- [9. Struktur Folder](#9-struktur-folder)
- [10. Mengubah Dataset](#10-mengubah-dataset)
- [11. Kontribusi dan Pengumpulan UTS](#11-kontribusi-dan-pengumpulan-uts)

## 1. Tujuan Proyek

Penyusunan jadwal kuliah secara manual berisiko menyebabkan dosen mengajar pada dua tempat sekaligus, kelas mahasiswa mendapatkan jadwal yang bertabrakan, atau satu ruangan digunakan oleh beberapa sesi pada waktu yang sama.

Proyek ini bertujuan untuk:

1. Memodelkan penjadwalan kuliah sebagai persoalan optimasi.
2. Mengimplementasikan operator Algoritma Genetika **dari awal**, tanpa pustaka AG siap pakai seperti DEAP atau PyGAD.
3. Menghasilkan jadwal dengan pelanggaran kendala keras sesedikit mungkin.
4. Mengevaluasi hasil melalui **minimal 10 percobaan dengan random seed berbeda**.
5. Menyajikan hasil dalam tabel jadwal, grafik konvergensi, serta berkas CSV/Excel.

**Alur utama:** `Dataset → Populasi jadwal → Evaluasi fitness → Seleksi → Crossover → Mutasi + Elitisme → Jadwal terbaik`.

## 2. Teknologi dan Fitur

### Teknologi

| Teknologi | Kegunaan |
| --- | --- |
| Python | Implementasi logika penjadwalan dan Algoritma Genetika |
| Streamlit | Antarmuka web lokal (*dashboard*) |
| Plotly | Visualisasi hasil dan grafik interaktif |
| Matplotlib | Grafik konvergensi yang diekspor sebagai gambar |
| CSV / XLSX | Dataset input dan berkas hasil penjadwalan |
| Git dan GitHub | Penyimpanan serta kolaborasi kode |

Dependensi aplikasi tercantum dalam `requirements.txt`. Operator AG diimplementasikan sendiri di `src/genetic_timetable.py`.

### Fitur yang tersedia

- Dashboard ringkasan data perkuliahan.
- Penampil dataset dan penjelasan aturan penjadwalan.
- **Mode konfigurasi Otomatis dan Manual (Advanced)**.
- Optimasi 1 percobaan atau pengujian **10 percobaan**.
- Pemeriksaan bentrok dosen, kelas, ruang, kapasitas, dan indeks penempatan.
- Ringkasan *fitness*, jumlah pelanggaran, dan generasi solusi valid pertama.
- Grafik konvergensi dan analisis hasil per percobaan.
- Tabel jadwal yang dapat difilter menurut hari, kelas, atau ruangan.
- Unduh jadwal CSV serta hasil optimasi Excel.

> **Catatan:** aplikasi saat ini membaca dataset dari berkas CSV dalam folder `data/`. **Unggah Excel langsung melalui UI belum tersedia**; fitur tersebut termasuk pengembangan yang dapat dikerjakan untuk UAS.

## 3. Dataset dan Batasan

Target skala UTS:

| Komponen | Jumlah |
| --- | ---: |
| Mata kuliah | 20 |
| Dosen | 8 |
| Ruangan | 5 |
| Hari perkuliahan | 5 (Senin–Jumat) |
| Slot waktu | 5 per hari (masing-masing 50 menit) |

Dataset berasal dari berkas proyek S-1 Teknik Informatika yang telah disederhanakan. **Kapasitas ruang dan identitas sebagian kelas belum terverifikasi sebagai data resmi.**

### Kendala keras (*hard constraints*)

1. **Bentrok dosen:** dosen tidak boleh mengampu dua sesi pada slot yang sama.
2. **Bentrok kelas:** kelompok mahasiswa yang sama tidak boleh mengikuti dua sesi bersamaan.
3. **Bentrok ruangan:** satu ruang tidak boleh digunakan dua sesi sekaligus.
4. **Kapasitas:** peserta kuliah tidak boleh melebihi kapasitas ruang.
5. **Validitas indeks:** penempatan hari, slot, dan ruang harus valid serta tidak melewati batas hari.

Kendala lunak (*soft constraints*), seperti preferensi dosen dan jeda jadwal mahasiswa, **belum dioptimalkan pada tahap UTS**.

### Durasi mata kuliah

Satu slot berdurasi 50 menit. Mata kuliah **2 SKS** menggunakan dua slot berurutan (100 menit), sedangkan **3 SKS** menggunakan tiga slot berurutan (150 menit). Satu sesi tidak boleh melewati akhir hari.

## 4. Cara Kerja Algoritma

Setiap **kromosom** adalah satu kandidat jadwal lengkap yang terdiri dari 20 gen. Satu **gen** menyatakan penempatan sebuah mata kuliah:

```text
(indeks_hari, indeks_slot_mulai, indeks_ruang)
```

Setiap kandidat diperiksa dan diberi nilai *fitness* berdasarkan jumlah pelanggaran:

```text
fitness = 1 / (1 + total_pelanggaran)
```

| Total pelanggaran | Fitness | Arti |
| ---: | ---: | --- |
| 0 | 1,000 | Jadwal valid pada model simulasi |
| 1 | 0,500 | Masih ada pelanggaran |
| 2 | 0,333 | Masih ada pelanggaran |

Tahapan evolusi yang diterapkan:

1. **Inisialisasi populasi:** membangkitkan sejumlah kandidat jadwal acak.
2. **Evaluasi fitness:** menghitung jumlah pelanggaran tiap kandidat.
3. **Seleksi:** memilih induk melalui **roulette wheel** atau **tournament selection**.
4. **Crossover:** mengombinasikan dua induk melalui **one-point** atau **uniform crossover**.
5. **Mutasi:** secara acak mengubah hari, waktu mulai, atau ruang suatu gen.
6. **Elitisme:** mempertahankan individu terbaik ke generasi berikutnya.
7. **Terminasi:** berhenti ketika ditemukan jadwal valid atau batas generasi tercapai.

Algoritma berusaha **meminimalkan pelanggaran**, tetapi tidak menjamin selalu menemukan jadwal valid pada setiap dataset dan konfigurasi.

## 5. Konfigurasi Otomatis dan Manual

### Mode Otomatis (Default)

Saat mode **Otomatis** dipilih, aplikasi menggunakan parameter preset berikut:

| Parameter | Default |
| --- | ---: |
| Ukuran populasi | 100 |
| Maksimum generasi | 350 |
| Probabilitas crossover | 0,85 (85%) |
| Probabilitas mutasi per gen | 0,09 (9%) |
| Elitisme | 2 |
| Ukuran turnamen | 3 |
| Random seed awal | 101 |

- **1 run:** menggunakan tournament selection dan uniform crossover.
- **10 run:** menggunakan seed **101–110**; lima percobaan pertama memakai roulette + one-point, lima berikutnya tournament + uniform.

Parameter di atas adalah **pilihan implementasi**, bukan nilai yang ditetapkan wajib oleh dosen.

### Mode Manual (Advanced)

Pengguna dapat mengatur populasi, jumlah generasi, crossover, mutasi, elitisme, seed, serta metode seleksi dan crossover. Pilihan **1 run** dan **10 run** tersedia pada kedua mode.

Perubahan konfigurasi tidak langsung menjalankan algoritma. Pengguna harus menekan **Jalankan Optimasi Sekarang**.

## 6. Instalasi dan Menjalankan Aplikasi

### Persyaratan

- Windows 10/11 dengan Python yang kompatibel dengan dependensi proyek (disarankan Python 3.11 atau 3.12).
- Visual Studio Code dan ekstensi Python.
- Internet saat instalasi pustaka pertama kali.

### A. Mengunduh repository (pengguna baru)

Buka terminal PowerShell/VS Code di folder tempat proyek akan disimpan:

```powershell
git clone https://github.com/Andre-Dir/UTS-Algoritma-Genetika-Penjadwalan-Kuliah.git
cd UTS-Algoritma-Genetika-Penjadwalan-Kuliah
```

**Jika repository sudah di-clone, jangan ulangi `git clone`.** Cukup buka folder repository tersebut melalui **File → Open Folder** di VS Code.

### B. Menyiapkan Python dan menjalankan Streamlit (Windows)

Jalankan perintah berikut dari **folder yang berisi `app.py`**:

```powershell
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m streamlit run app.py
```

Buka **http://localhost:8501** jika browser tidak terbuka otomatis.

Alternatif Windows: jalankan `Jalankan_Genetica.bat` dari folder proyek.

> **PowerShell:** jika aktivasi `.venv\Scripts\Activate.ps1` diblokir, tetap jalankan `.venv\Scripts\python.exe` seperti perintah di atas. Aktivasi *virtual environment* tidak diperlukan.

### C. Linux/macOS

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m streamlit run app.py
```

Untuk menghentikan aplikasi, tekan **Ctrl + C** di terminal yang menjalankannya.

## 7. Panduan Penggunaan UI

1. **Beranda:** periksa jumlah mata kuliah, dosen, ruangan, dan slot.
2. **Dataset & Aturan:** lihat data simulasi dan kendala yang dihitung.
3. **Optimasi AG:** pilih mode Otomatis atau Manual; untuk UTS pilih **10 run • UTS**, lalu klik **Jalankan Optimasi Sekarang**.
4. **Jadwal Kuliah:** periksa hasil penempatan, nilai bentrok, filter jadwal, dan matriks hari × slot.
5. **Analisis Pengujian:** baca hasil setiap run, *fitness* rata-rata, generasi solusi valid pertama, dan durasi.
6. **Unduh hasil:** simpan berkas Excel atau CSV dari tombol yang disediakan.

Hasil aktif dalam UI disimpan pada sesi Streamlit. Setelah aplikasi/server dimulai ulang, jalankan optimasi kembali untuk menampilkan hasil dalam sesi baru. Berkas keluaran yang telah ditulis ke folder `hasil/` tetap tersedia di disk.

## 8. Pengujian dan Hasil

### Pengujian fungsi

```powershell
.venv\Scripts\python.exe test_ag.py
```

Berkas `test_ag.py` digunakan untuk menguji operator genetika dan pemeriksaan kendala.

### Eksperimen 10 run tanpa UI

```powershell
.venv\Scripts\python.exe main.py
```

Skrip ini menjalankan 10 percobaan dengan seed berbeda menggunakan konfigurasi bawaan, mencatat hasil, dan menulis keluaran di `hasil/`, antara lain:

- `hasil_10_run.csv` — hasil setiap percobaan.
- `jadwal_terbaik.csv` — jadwal terbaik yang ditemukan.
- `konvergensi_run_terbaik.csv` — data *fitness* per generasi.
- `grafik_konvergensi.png` — visualisasi konvergensi.
- `ringkasan.json` — rangkuman pengujian dan parameter.

Jika optimasi dijalankan melalui **UI**, aplikasi juga menghasilkan `Hasil_Optimasi_Genetica.xlsx` dan berkas keluaran terkait di folder `hasil/`.

**Metrik yang dilaporkan:** *fitness* terbaik, *fitness* rata-rata, jumlah pelanggaran, generasi saat solusi valid pertama ditemukan, dan waktu komputasi. Nilai aktual bisa berbeda jika dataset, parameter, atau seed diubah; jangan menganggap hasil contoh sebagai hasil semua percobaan.

## 9. Struktur Folder

```text
UTS-Algoritma-Genetika-Penjadwalan-Kuliah/
├── .streamlit/
│   └── config.toml             # Tema Streamlit
├── assets/
│   └── style.css               # Styling antarmuka
├── data/
│   ├── Data_Mentah_Asli.xlsx   # Arsip data sumber
│   ├── mata_kuliah.csv         # Data mata kuliah dan pengampu
│   ├── dosen.csv               # Data dosen
│   ├── ruangan.csv             # Data ruangan dan kapasitas simulasi
│   ├── hari.csv                # Daftar hari
│   └── slot_jam.csv            # Daftar slot waktu
├── docs/                       # Dokumentasi tambahan
├── hasil/                      # Hasil pengujian dan ekspor
├── src/
│   ├── __init__.py
│   ├── config_modes.py         # Konfigurasi Otomatis/Manual
│   ├── genetic_timetable.py    # Implementasi AG dan validasi
│   └── excel_export.py         # Pembuatan berkas Excel
├── app.py                      # Aplikasi Streamlit
├── main.py                     # Eksperimen terminal (10 run)
├── test_ag.py                  # Pengujian fungsi
├── Jalankan_Genetica.bat       # Launcher Windows
├── requirements.txt           # Dependensi Python
├── .gitignore                  # Berkas/folder yang tidak di-commit
└── README.md                   # Dokumentasi proyek
```

Struktur di atas menunjukkan berkas inti proyek; isi `docs/` dan `hasil/` dapat bertambah setelah eksperimen baru.

## 10. Mengubah Dataset

Algoritma membaca **CSV di folder `data/`**, bukan langsung dari berkas XLSX arsip. Saat mengedit, pertahankan nama kolom dan simpan dengan format **CSV UTF-8**.

Kolom `ID_Dosen_Pengampu` boleh memuat beberapa ID yang dipisahkan titik koma, misalnya:

```text
D01;D03
```

Dalam kasus tersebut, **kedua dosen** diperiksa pada validasi bentrok. Model juga menggunakan `ID_Kelas`, jumlah mahasiswa, SKS, serta kapasitas ruangan.

Saat ini fungsi `load_data()` memvalidasi skala **tepat 20 mata kuliah, 8 dosen, 5 ruang, 5 hari, dan 5 slot**. Perubahan skala untuk UAS memerlukan penyesuaian validasi serta pengujian ulang.

## 11. Kontribusi dan Pengumpulan UTS

### Anggota kelompok

| Nama | NIM | Peran |
| --- | --- | --- |
| _Muhammad Aziz Arrahman_ | _2430305030020_ | _Ketua/Analis_ |
| _Fajar Oktavian Ramadhan_ | _2430205030023_ | _Programmer AG_ |
| _Kelvin Andre Hardian_ | _2430305030011_ | _Fitness dan Validasi_ |
| _Giovanni Maranatha_ | _2430305030022_ | _Eksperimen/Pengujian_ |
| _Muhamad Shaufi Wafa Bawjazani Shodiqin_ | _2430205030028_ | _Dokumentasi/Presentasi_ |

