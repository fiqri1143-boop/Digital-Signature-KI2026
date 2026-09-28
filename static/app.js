// Mengatur interaksi formulir, kalender, dan pesan pada antarmuka web.
(() => {
  // Menampilkan status proses atau pesan kesalahan pada formulir.
  const tampilkanStatus = (elemen, pesan, jenis = '') => {
    if (!elemen) return;
    elemen.className = `status${jenis ? ` is-${jenis}` : ''}`;
    elemen.textContent = pesan;
  };

  // Mengambil pesan kesalahan yang dikirim oleh server.
  const pesanKesalahan = async (respons) => {
    try {
      const hasil = await respons.json();
      const pesan = hasil.error || 'Permintaan gagal. Coba lagi.';
      if (pesan.toLowerCase().includes('passphrase salah')) {
        return 'Passphrase tidak cocok dengan kunci privat tersimpan. Gunakan passphrase yang sama seperti saat pertama kali menandatangani.';
      }
      return pesan;
    } catch {
      return 'Permintaan gagal. Periksa koneksi lalu coba lagi.';
    }
  };

  // Menampilkan nama berkas setelah pengguna memilih dokumen.
  document.querySelectorAll('.file-drop input[type="file"]').forEach((masukan) => {
    masukan.addEventListener('change', () => {
      const areaUnggah = masukan.closest('.file-drop');
      const namaBerkas = areaUnggah?.querySelector('[data-file-name]');
      const berkas = masukan.files?.[0];
      if (namaBerkas) namaBerkas.textContent = berkas ? `${berkas.name} · ${(berkas.size / (1024 * 1024)).toFixed(2)} MB` : 'Belum ada file dipilih';
      areaUnggah?.classList.toggle('is-selected', Boolean(berkas));
    });
  });

  // Mengatur tombol untuk menampilkan atau menyamarkan passphrase.
  document.querySelectorAll('[data-password-toggle]').forEach((tombolToggle) => {
    tombolToggle.addEventListener('click', () => {
      const masukan = document.querySelector('#key-passphrase');
      if (!masukan) return;
      const tampilkan = masukan.type === 'password';
      masukan.type = tampilkan ? 'text' : 'password';
      tombolToggle.textContent = tampilkan ? 'SEMBUNYIKAN' : 'LIHAT';
      tombolToggle.setAttribute('aria-label', tampilkan ? 'Sembunyikan passphrase' : 'Tampilkan passphrase');
      tombolToggle.setAttribute('aria-pressed', String(tampilkan));
      masukan.focus();
    });
  });

  // Menjalankan kalender tanggal kustom pada halaman tanda tangan.
  const kolomTanggal = document.querySelector('#date-field');
  if (kolomTanggal) {
    const masukanTanggal = kolomTanggal.querySelector('#sign-date');
    const tampilanTanggal = kolomTanggal.querySelector('#sign-date-display');
    const kalender = kolomTanggal.querySelector('#signature-calendar');
    const labelBulan = kalender.querySelector('[data-calendar-month]');
    const kisiHari = kalender.querySelector('[data-calendar-days]');
    const pemicu = kolomTanggal.querySelector('.date-trigger');
    const formatBulan = new Intl.DateTimeFormat('id-ID', { month: 'long', year: 'numeric' });
    const formatTanggal = new Intl.DateTimeFormat('id-ID', { day: 'numeric', month: 'long', year: 'numeric' });
    const formatTanggalLengkap = new Intl.DateTimeFormat('id-ID', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
    const tanggalIso = (tanggal) => `${tanggal.getFullYear()}-${String(tanggal.getMonth() + 1).padStart(2, '0')}-${String(tanggal.getDate()).padStart(2, '0')}`;
    const uraiTanggal = (nilai) => {
      const [tahun, bulan, hari] = nilai.split('-').map(Number);
      return new Date(tahun, bulan - 1, hari);
    };
    const hariIni = new Date();
    let tanggalDipilih = masukanTanggal.value ? uraiTanggal(masukanTanggal.value) : hariIni;
    let bulanTampil = new Date(tanggalDipilih.getFullYear(), tanggalDipilih.getMonth(), 1);

    // Menyimpan tanggal pilihan ke input formulir dan tampilan.
    const selaraskanTanggal = () => {
      masukanTanggal.value = tanggalIso(tanggalDipilih);
      tampilanTanggal.value = formatTanggal.format(tanggalDipilih);
    };

    // Menutup kalender dan mengembalikan fokus bila diperlukan.
    const tutupKalender = (kembalikanFokus = false) => {
      kalender.hidden = true;
      pemicu.setAttribute('aria-expanded', 'false');
      tampilanTanggal.setAttribute('aria-expanded', 'false');
      if (kembalikanFokus) tampilanTanggal.focus();
    };

    // Menggambar tanggal untuk bulan yang sedang ditampilkan.
    const gambarKalender = () => {
      labelBulan.textContent = formatBulan.format(bulanTampil);
      kisiHari.replaceChildren();
      const tahun = bulanTampil.getFullYear();
      const bulan = bulanTampil.getMonth();
      const offsetHariPertama = (new Date(tahun, bulan, 1).getDay() + 6) % 7;
      const jumlahHariDalamBulan = new Date(tahun, bulan + 1, 0).getDate();
      const jumlahSel = Math.ceil((offsetHariPertama + jumlahHariDalamBulan) / 7) * 7;

      for (let urutan = 0; urutan < jumlahSel; urutan += 1) {
        const nomorHari = urutan - offsetHariPertama + 1;
        const tanggalSel = new Date(tahun, bulan, nomorHari);
        const tanggalSelIso = tanggalIso(tanggalSel);
        const tombolHari = document.createElement('button');
        tombolHari.type = 'button';
        tombolHari.className = 'calendar-day';
        tombolHari.textContent = String(tanggalSel.getDate());
        tombolHari.setAttribute('aria-label', formatTanggalLengkap.format(tanggalSel));
        tombolHari.setAttribute('aria-pressed', String(tanggalSelIso === tanggalIso(tanggalDipilih)));
        if (tanggalSelIso === tanggalIso(tanggalDipilih)) tombolHari.classList.add('is-selected');
        if (tanggalSelIso === tanggalIso(hariIni)) tombolHari.classList.add('is-today');
        if (tanggalSel.getMonth() !== bulan) tombolHari.classList.add('is-outside');
        tombolHari.addEventListener('click', () => {
          tanggalDipilih = tanggalSel;
          bulanTampil = new Date(tanggalSel.getFullYear(), tanggalSel.getMonth(), 1);
          selaraskanTanggal();
          tutupKalender(true);
        });
        kisiHari.append(tombolHari);
      }
    };

    // Membuka kalender pada bulan tanggal pilihan.
    const bukaKalender = () => {
      bulanTampil = new Date(tanggalDipilih.getFullYear(), tanggalDipilih.getMonth(), 1);
      gambarKalender();
      kalender.hidden = false;
      pemicu.setAttribute('aria-expanded', 'true');
      tampilanTanggal.setAttribute('aria-expanded', 'true');
      kalender.querySelector('.is-selected')?.focus();
    };

    selaraskanTanggal();
    pemicu.addEventListener('click', () => kalender.hidden ? bukaKalender() : tutupKalender());
    tampilanTanggal.addEventListener('click', bukaKalender);
    tampilanTanggal.addEventListener('keydown', (peristiwa) => {
      if (peristiwa.key === 'Enter' || peristiwa.key === ' ') {
        peristiwa.preventDefault();
        bukaKalender();
      }
    });
    kalender.querySelector('[data-calendar-prev]').addEventListener('click', () => {
      bulanTampil = new Date(bulanTampil.getFullYear(), bulanTampil.getMonth() - 1, 1);
      gambarKalender();
    });
    kalender.querySelector('[data-calendar-next]').addEventListener('click', () => {
      bulanTampil = new Date(bulanTampil.getFullYear(), bulanTampil.getMonth() + 1, 1);
      gambarKalender();
    });
    kalender.querySelector('[data-calendar-today]').addEventListener('click', () => {
      tanggalDipilih = new Date();
      bulanTampil = new Date(tanggalDipilih.getFullYear(), tanggalDipilih.getMonth(), 1);
      selaraskanTanggal();
      tutupKalender(true);
    });
    kalender.querySelector('[data-calendar-close]').addEventListener('click', () => tutupKalender(true));
    document.addEventListener('pointerdown', (peristiwa) => {
      if (!kalender.hidden && !kolomTanggal.contains(peristiwa.target)) tutupKalender();
    });
    document.addEventListener('keydown', (peristiwa) => {
      if (peristiwa.key === 'Escape' && !kalender.hidden) tutupKalender(true);
    });
  }

  // Mengirim dokumen ke server untuk ditandatangani.
  const formTandaTangan = document.querySelector('#sign-form');
  formTandaTangan?.addEventListener('submit', async (peristiwa) => {
    peristiwa.preventDefault();
    const tombol = formTandaTangan.querySelector('button[type="submit"]');
    const labelTombol = tombol.querySelector('span:first-child');
    const statusTampilan = formTandaTangan.querySelector('.status');
    tombol.disabled = true;
    labelTombol.textContent = 'Sedang menandatangani…';
    tampilkanStatus(statusTampilan, 'Memproses PDF dan membuat tanda tangan aman.', 'loading');
    try {
      const respons = await fetch('/sign', { method: 'POST', body: new FormData(formTandaTangan) });
      if (!respons.ok) throw new Error(await pesanKesalahan(respons));
      const dataUnduhan = await respons.blob();
      const alamatUrl = URL.createObjectURL(dataUnduhan);
      const tautan = document.createElement('a');
      tautan.href = alamatUrl;
      tautan.download = 'hasil_tanda_tangan.zip';
      document.body.appendChild(tautan);
      tautan.click();
      window.setTimeout(() => { URL.revokeObjectURL(alamatUrl); tautan.remove(); }, 1500);
      tampilkanStatus(statusTampilan, 'Selesai. ZIP berisi PDF bertanda tangan, signature.sig, dan public_key.pem sudah diunduh.', 'success');
    } catch (kesalahan) {
      tampilkanStatus(statusTampilan, kesalahan.message, 'error');
    } finally {
      tombol.disabled = false;
      labelTombol.textContent = 'Tanda tangani & unduh';
    }
  });

  // Mengirim PDF dan data tanda tangan ke endpoint verifikasi.
  const pasangFormVerifikasi = (formulir, titikAkses) => {
    formulir?.addEventListener('submit', async (peristiwa) => {
      peristiwa.preventDefault();
      const tombol = formulir.querySelector('button[type="submit"]');
      const labelTombol = tombol.querySelector('span:first-child');
      const statusTampilan = formulir.querySelector('.status');
      tombol.disabled = true;
      labelTombol.textContent = 'Sedang memeriksa…';
      tampilkanStatus(statusTampilan, 'Membandingkan dokumen dengan tanda tangannya.', 'loading');
      try {
        const respons = await fetch(titikAkses, { method: 'POST', body: new FormData(formulir) });
        const hasil = await respons.json();
        if (!respons.ok) throw new Error(hasil.error || 'Verifikasi gagal. Periksa kembali file yang dipilih.');
        tampilkanStatus(statusTampilan, hasil.message, hasil.valid ? 'success' : 'error');
      } catch (kesalahan) {
        tampilkanStatus(statusTampilan, kesalahan.message, 'error');
      } finally {
        tombol.disabled = false;
        labelTombol.textContent = formulir.id === 'qr-verify-form' ? 'Verifikasi dokumen' : 'Periksa tanda tangan';
      }
    });
  };

  pasangFormVerifikasi(document.querySelector('#verify-form'), '/verify');
  pasangFormVerifikasi(document.querySelector('#qr-verify-form'), window.location.pathname);
})();
