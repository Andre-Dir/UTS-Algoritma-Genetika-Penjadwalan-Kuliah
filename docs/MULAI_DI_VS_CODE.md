# Panduan Ngoding dari Nol di VS Code

## Tujuan tahap pertama

Berhasil membuka aplikasi **GENETICA** di browser, memahami letak kode antarmuka dan logika Algoritma Genetika, lalu melakukan 10 run dengan data simulasi.

### 1. Buka folder

1. Download dan ekstrak ZIP.
2. Di VS Code pilih **File → Open Folder**.
3. Pilih folder `UTS_AG_TI_VSCode`. Pastikan terlihat `app.py`.
4. Install ekstensi `Python` dari Microsoft jika belum ada.

### 2. Buat lingkungan Python

Buka `Terminal → New Terminal`, lalu jalankan:

```powershell
py --version
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Jangan copy tanda `$` atau `PS >`. Jika `py` tidak ditemukan, gunakan `python`.

### 3. Jalankan aplikasi

```powershell
.venv\Scripts\python.exe -m streamlit run app.py
```

Browser: http://localhost:8501

Kalau terminal bertuliskan `You can now view your Streamlit app in your browser`, aplikasi sudah berjalan.

### 4. Mulai baca kode

Buka dua file utama:

- **`app.py`**: menyusun halaman UI, tombol, tabel, grafik, dan interaksi pengguna.
- **`src/genetic_timetable.py`**: memuat proses evolusi sebenarnya—populasi, fitness, seleksi, crossover, mutasi, elitisme.

Contoh pengaturan aplikasi di `app.py`:

```python
st.set_page_config(
    page_title='GENETICA • Optimasi Jadwal',
    page_icon='🧬',
    layout='wide'
)
```

Fungsi yang menjalankan inti algoritma:

```python
result = run_ga(
    courses, rooms, days, slots,
    seed=101,
    config=GAConfig(),
    selection='tournament',
    crossover='uniform'
)
```

### 5. Coba demo dari UI

1. Menu **Optimasi AG** → `1 run • coba cepat` → **Jalankan**.
2. Perhatikan fitness dan grafiknya.
3. Menu **Jadwal Kuliah** → lihat hasil.
4. Ulangi **10 run • UTS** untuk mendapatkan bukti pengujian.
5. Unduh jadwal Excel.

### 6. Kalau ada error umum

- `No module named streamlit`: jalankan perintah install lagi menggunakan interpreter `.venv\Scripts\python.exe`.
- `python/py is not recognized`: instal Python dari python.org, centang *Add Python to PATH*, lalu buka terminal baru.
- Port `8501` terpakai: jalankan `... -m streamlit run app.py --server.port 8502`, lalu buka http://localhost:8502.
- `Dataset belum bisa dibaca`: pastikan menjalankan dari folder akar yang berisi `data/` dan file CSV tidak berubah nama/kolom.
- Layar kosong setelah update CSS: hentikan terminal dengan Ctrl+C, jalankan lagi, lalu refresh browser.

### 7. Setelah bisa berjalan

Pelajari urutan fungsi AG: `load_data → random_population → count_violations → fitness → roulette_selection/tournament_selection → one_point_crossover/uniform_crossover → mutate → run_ga → schedule_records`.

**Batasan model:** kapasitas ruang dan beberapa kelas menggunakan simulasi; jangan mengklaim sebagai data riil.
