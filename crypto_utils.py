# Menyediakan fungsi hash SHA-256 dan tanda tangan RSA-PSS untuk PDF.
import hashlib
from pathlib import Path

from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import pss


# Menghasilkan pasangan kunci RSA 2048-bit.
def generate_keys():
    kunci_privat = RSA.generate(2048)
    return kunci_privat, kunci_privat.public_key()


# Menghitung hash SHA-256 berkas PDF secara bertahap.
def hash_pdf(jalur_pdf):
    intisari = hashlib.sha256()
    with Path(jalur_pdf).open("rb") as berkas_pdf:
        for potongan_data in iter(lambda: berkas_pdf.read(1024 * 1024), b""):
            intisari.update(potongan_data)
    return intisari.hexdigest()


# Menandatangani hash PDF menggunakan RSA-PSS.
def sign_document(jalur_pdf, kunci_privat):
    if not isinstance(kunci_privat, RSA.RsaKey):
        kunci_privat = RSA.import_key(kunci_privat)
    if not kunci_privat.has_private():
        raise ValueError("Kunci yang diberikan bukan private key.")

    intisari = SHA256.new()
    with Path(jalur_pdf).open("rb") as berkas_pdf:
        for potongan_data in iter(lambda: berkas_pdf.read(1024 * 1024), b""):
            intisari.update(potongan_data)
    return pss.new(kunci_privat).sign(intisari)


# Memeriksa tanda tangan RSA-PSS terhadap isi PDF.
def verify_document(jalur_pdf, tanda_tangan, kunci_publik):
    if not isinstance(kunci_publik, RSA.RsaKey):
        kunci_publik = RSA.import_key(kunci_publik)

    intisari = SHA256.new()
    with Path(jalur_pdf).open("rb") as berkas_pdf:
        for potongan_data in iter(lambda: berkas_pdf.read(1024 * 1024), b""):
            intisari.update(potongan_data)
    try:
        pss.new(kunci_publik).verify(intisari, tanda_tangan)
        return True
    except (ValueError, TypeError):
        return False
