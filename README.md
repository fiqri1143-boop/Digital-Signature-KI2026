# TandaTera

TandaTera adalah aplikasi web sederhana untuk menandatangani dokumen PDF dan memeriksa apakah dokumen tersebut masih sama seperti saat ditandatangani. Proyek ini dibuat untuk tugas kuliah Keamanan Informasi, sebagai contoh penggunaan hash dan tanda tangan digital.

Aplikasi menggunakan SHA-256 untuk membuat ringkasan isi PDF, lalu menandatanganinya dengan RSA-PSS. PDF hasil tanda tangan diberi QR-Code yang mengarah ke halaman verifikasi. Pengguna juga dapat memeriksa dokumen secara manual dengan mengunggah PDF, `signature.sig`, dan `public_key.pem`.

## Menjalankan aplikasi

Pastikan Python sudah terpasang. Buka terminal pada folder proyek, lalu jalankan:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Setelah server berjalan, buka `http://127.0.0.1:5000` di browser.

Jika PowerShell menolak aktivasi lingkungan virtual, kamu bisa menjalankan program pip dan Flask langsung dari folder `venv` atau gunakan Command Prompt:

```bat
venv\Scripts\activate.bat
```

## Cara memakai

### Menandatangani PDF

1. Buka halaman **Tanda tangani** dan pilih dokumen PDF. Ukuran maksimum unggahan adalah 20 MB.
2. Isi nama, jabatan, institusi, tanggal, dan passphrase.
3. Nama ZIP hasil unduhan boleh diisi sendiri. Jika dibiarkan kosong, namanya mengikuti nama PDF.
4. Tekan **Tanda tangani & unduh**.
5. ZIP berisi PDF yang sudah ditandatangani, `signature.sig`, `public_key.pem`, dan petunjuk singkat.

Saat pertama kali digunakan, passphrase mengenkripsi kunci privat yang dibuat aplikasi. Untuk penandatanganan berikutnya pada instalasi yang sama, gunakan passphrase yang sama untuk membuka kunci tersebut. Passphrase tidak disimpan sebagai teks. File kunci terenkripsi berada di `instance/keys/`.

### Memeriksa PDF

Untuk pemeriksaan melalui QR, pindai kode pada PDF dan unggah PDF hasil tanda tangan pada halaman yang terbuka.

Untuk pemeriksaan manual, buka halaman **Verifikasi**, lalu pilih PDF hasil tanda tangan bersama `signature.sig` dan `public_key.pem` dari ZIP. Gunakan PDF persis seperti hasil unduhan. Jika PDF disunting atau disimpan ulang oleh aplikasi lain, tanda tangan bisa dinyatakan tidak valid meskipun tampilannya tampak sama.

## Membuka tautan QR dari ponsel

Ponsel dan komputer harus berada di jaringan Wi-Fi yang sama. Buka aplikasi di komputer menggunakan alamat IP lokal komputer, misalnya `http://192.168.1.20:5000`, sebelum membuat tanda tangan. Dengan begitu, QR akan berisi alamat yang dapat dibuka ponsel. Alamat `127.0.0.1` atau `localhost` hanya menunjuk ke perangkat yang sedang dipakai.

## Isi folder utama

- `app.py` — route Flask, proses tanda tangan, QR, dan verifikasi.
- `crypto_utils.py` — pembuatan kunci RSA, hash SHA-256, serta tanda tangan dan verifikasi RSA-PSS.
- `templates/` — halaman dan formulir website.
- `static/` — JavaScript, CSS, dan logo.
- `tests/` — pengujian fungsi kriptografi.
- `performance_test.py` — skrip untuk mengukur waktu tanda tangan dan verifikasi.
- `instance/` — kunci privat terenkripsi dan catatan QR yang dibuat saat aplikasi digunakan; folder ini tidak dimasukkan ke Git.

## Catatan penggunaan

Ini adalah demo kuliah yang dijalankan secara lokal. Server memakai mode debug untuk pengembangan, jadi jangan membukanya ke internet atau menggunakannya untuk dokumen penting. Jaga passphrase dan jangan bagikan tangkapan layar yang memperlihatkannya.
