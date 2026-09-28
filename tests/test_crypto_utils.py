# Memeriksa fungsi pembentukan kunci, hashing, tanda tangan, dan verifikasi.
import hashlib
import tempfile
import unittest
from pathlib import Path

import crypto_utils
from Crypto.PublicKey import RSA


DIREKTORI_REPO = Path(__file__).resolve().parents[1]


# Kumpulan pengujian untuk fungsi kriptografi.
class CryptoUtilsTests(unittest.TestCase):
    # Membuat pasangan kunci yang dipakai bersama oleh pengujian.
    @classmethod
    def setUpClass(cls):
        cls.kunci_privat, cls.kunci_publik = crypto_utils.generate_keys()
        cls.kunci_privat_lain, cls.kunci_publik_lain = crypto_utils.generate_keys()

    # Menyiapkan PDF sementara untuk satu kasus pengujian.
    def setUp(self):
        self.direktori_sementara = tempfile.TemporaryDirectory()
        self.addCleanup(self.direktori_sementara.cleanup)
        self.direktori_akar = Path(self.direktori_sementara.name)
        self.jalur_pdf = self.direktori_akar / "sample.pdf"
        # Fungsi hash membaca isi berkas tanpa mengurai struktur PDF.
        self.isi_pdf = b"%PDF-1.4\nUnit test document\n%%EOF\n"
        self.jalur_pdf.write_bytes(self.isi_pdf)

    # Memastikan modul kriptografi diimpor dari folder proyek.
    def test_crypto_utils_is_imported_from_repository_root(self):
        self.assertEqual(
            Path(crypto_utils.__file__).resolve(),
            (DIREKTORI_REPO / "crypto_utils.py").resolve(),
        )

    # Memastikan pasangan kunci yang dibuat memakai RSA 2048-bit.
    def test_generate_keys_returns_matching_rsa_2048_key_pair(self):
        kunci_privat, kunci_publik = crypto_utils.generate_keys()

        self.assertIsInstance(kunci_privat, RSA.RsaKey)
        self.assertEqual(kunci_privat.size_in_bits(), 2048)
        self.assertTrue(kunci_privat.has_private())
        self.assertFalse(kunci_publik.has_private())
        self.assertEqual(kunci_privat.public_key().export_key(), kunci_publik.export_key())

    # Memastikan hash PDF sama dengan hasil SHA-256 yang dihitung langsung.
    def test_hash_pdf_matches_known_sha256(self):
        hasil_yang_diharapkan = hashlib.sha256(self.isi_pdf).hexdigest()

        self.assertEqual(crypto_utils.hash_pdf(self.jalur_pdf), hasil_yang_diharapkan)

    # Memastikan hashing tetap benar untuk PDF yang lebih besar dari satu MiB.
    def test_hash_pdf_handles_file_larger_than_one_mebibyte(self):
        jalur_besar = self.direktori_akar / "large.pdf"
        isi_besar = (b"large-pdf-test-block\x00" * 70000)[: 1024 * 1024 + 123]
        jalur_besar.write_bytes(isi_besar)

        self.assertEqual(
            crypto_utils.hash_pdf(jalur_besar), hashlib.sha256(isi_besar).hexdigest()
        )

    # Memastikan tanda tangan RSA 2048-bit menghasilkan 256 byte.
    def test_sign_document_returns_rsa_2048_signature(self):
        tanda_tangan = crypto_utils.sign_document(self.jalur_pdf, self.kunci_privat)

        self.assertIsInstance(tanda_tangan, bytes)
        self.assertEqual(len(tanda_tangan), 256)

    # Memastikan fungsi dapat menerima kunci privat berformat PEM.
    def test_sign_document_accepts_private_key_pem(self):
        tanda_tangan = crypto_utils.sign_document(
            self.jalur_pdf, self.kunci_privat.export_key()
        )

        self.assertEqual(len(tanda_tangan), 256)

    # Memastikan kunci publik tidak diterima sebagai kunci penandatangan.
    def test_sign_document_rejects_public_key_as_private_key(self):
        with self.assertRaisesRegex(ValueError, "bukan private key"):
            crypto_utils.sign_document(self.jalur_pdf, self.kunci_publik)

    # Memastikan PDF asli lolos verifikasi dengan kunci pasangannya.
    def test_verify_document_accepts_original_document_and_matching_key(self):
        tanda_tangan = crypto_utils.sign_document(self.jalur_pdf, self.kunci_privat)

        self.assertTrue(
            crypto_utils.verify_document(self.jalur_pdf, tanda_tangan, self.kunci_publik)
        )

    # Memastikan perubahan satu byte membuat verifikasi gagal.
    def test_verify_document_rejects_document_tampered_by_one_byte(self):
        tanda_tangan = crypto_utils.sign_document(self.jalur_pdf, self.kunci_privat)
        isi_diubah = bytearray(self.jalur_pdf.read_bytes())
        isi_diubah[len(isi_diubah) // 2] ^= 0x01
        self.jalur_pdf.write_bytes(isi_diubah)

        self.assertFalse(
            crypto_utils.verify_document(self.jalur_pdf, tanda_tangan, self.kunci_publik)
        )

    # Memastikan kunci publik yang berbeda menolak tanda tangan.
    def test_verify_document_rejects_signature_from_wrong_public_key(self):
        tanda_tangan = crypto_utils.sign_document(self.jalur_pdf, self.kunci_privat)

        self.assertFalse(
            crypto_utils.verify_document(
                self.jalur_pdf, tanda_tangan, self.kunci_publik_lain
            )
        )

    # Memastikan tanda tangan yang diubah atau rusak ditolak.
    def test_verify_document_rejects_modified_or_malformed_signature(self):
        tanda_tangan = bytearray(
            crypto_utils.sign_document(self.jalur_pdf, self.kunci_privat)
        )
        tanda_tangan[0] ^= 0x01
        self.assertFalse(
            crypto_utils.verify_document(
                self.jalur_pdf, bytes(tanda_tangan), self.kunci_publik
            )
        )
        self.assertFalse(
            crypto_utils.verify_document(
                self.jalur_pdf, b"not-a-valid-signature", self.kunci_publik
            )
        )


if __name__ == "__main__":
    unittest.main()
