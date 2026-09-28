# Mengukur waktu proses tanda tangan dan verifikasi dokumen.
import statistics
import tempfile
import time
from pathlib import Path

import crypto_utils


JUMLAH_UJI = 30
DIREKTORI_REPO = Path(__file__).resolve().parent


# Menjalankan pengukuran waktu tanda tangan dan verifikasi.
def main():
    jalur_modul = Path(crypto_utils.__file__).resolve()
    if jalur_modul != (DIREKTORI_REPO / "crypto_utils.py").resolve():
        raise RuntimeError(
            f"Expected crypto_utils.py in repository root, imported {jalur_modul}"
        )

    # Pembuatan kunci berada di luar bagian yang diukur.
    kunci_privat, kunci_publik = crypto_utils.generate_keys()
    isi_pdf = (
        b"%PDF-1.4\n"
        b"Digital signature performance test fixture.\n"
        b"This temporary content is used for repeatable signing and verification.\n"
        b"%%EOF\n"
    )

    with tempfile.TemporaryDirectory(prefix="digital-signature-performance-") as direktori_sementara:
        jalur_pdf = Path(direktori_sementara) / "performance-sample.pdf"
        jalur_pdf.write_bytes(isi_pdf)

        # Menyiapkan tanda tangan valid sebelum mengukur waktu verifikasi.
        tanda_tangan_verifikasi = crypto_utils.sign_document(jalur_pdf, kunci_privat)
        if not crypto_utils.verify_document(
            jalur_pdf, tanda_tangan_verifikasi, kunci_publik
        ):
            raise RuntimeError("Warm-up signature did not verify")

        durasi_penandatanganan = []
        tanda_tangan_terakhir = None
        for _ in range(JUMLAH_UJI):
            waktu_mulai = time.perf_counter()
            tanda_tangan = crypto_utils.sign_document(jalur_pdf, kunci_privat)
            durasi_penandatanganan.append(time.perf_counter() - waktu_mulai)
            if not isinstance(tanda_tangan, bytes):
                raise RuntimeError("sign_document did not return signature bytes")
            tanda_tangan_terakhir = tanda_tangan

        durasi_verifikasi = []
        for _ in range(JUMLAH_UJI):
            waktu_mulai = time.perf_counter()
            valid = crypto_utils.verify_document(
                jalur_pdf, tanda_tangan_verifikasi, kunci_publik
            )
            durasi_verifikasi.append(time.perf_counter() - waktu_mulai)
            if not valid:
                raise RuntimeError("Verification failed during performance run")

    pem_kunci_publik = kunci_publik.export_key(format="PEM")
    if isinstance(pem_kunci_publik, str):
        pem_kunci_publik = pem_kunci_publik.encode("ascii")

    # Menyusun tabel hasil agar mudah dimasukkan ke laporan.
    baris_hasil = [
        ("Repository crypto_utils.py", str(jalur_modul)),
        ("Trials per operation", str(JUMLAH_UJI)),
        ("Average signing time (ms)", f"{statistics.mean(durasi_penandatanganan) * 1000:.3f}"),
        (
            "Average verification time (ms)",
            f"{statistics.mean(durasi_verifikasi) * 1000:.3f}",
        ),
        ("Signature size (bytes)", str(len(tanda_tangan_terakhir))),
        ("Public key size, PEM (bytes)", str(len(pem_kunci_publik))),
        ("Test document size (bytes)", str(len(isi_pdf))),
    ]

    print("Metric\tValue")
    for metrik, nilai in baris_hasil:
        print(f"{metrik}\t{nilai}")


if __name__ == "__main__":
    main()
