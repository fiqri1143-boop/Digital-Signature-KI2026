"""Helpers for hashing PDF files and creating/verifying RSA signatures."""

import hashlib
from pathlib import Path

from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import pss


def generate_keys():
    """Generate and return an RSA-2048 private key and its public key."""
    private_key = RSA.generate(2048)
    return private_key, private_key.public_key()


def hash_pdf(file_path):
    """Return the lowercase hexadecimal SHA-256 digest of a PDF file.

    Reads in chunks so large documents do not need to fit in memory.
    """
    digest = hashlib.sha256()
    with Path(file_path).open("rb") as pdf_file:
        for chunk in iter(lambda: pdf_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sign_document(pdf_path, private_key):
    """Sign a PDF's SHA-256 digest with RSA-PSS and return signature bytes.

    ``private_key`` may be a PyCryptodome RSA key object or PEM bytes/string.
    """
    if not isinstance(private_key, RSA.RsaKey):
        private_key = RSA.import_key(private_key)
    if not private_key.has_private():
        raise ValueError("Kunci yang diberikan bukan private key.")

    digest = SHA256.new()
    with Path(pdf_path).open("rb") as pdf_file:
        for chunk in iter(lambda: pdf_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return pss.new(private_key).sign(digest)


def verify_document(pdf_path, signature, public_key):
    """Verify an RSA-PSS signature; return True if valid, otherwise False.

    ``signature`` is the bytes returned by :func:`sign_document`.
    ``public_key`` may be a PyCryptodome RSA key object or PEM bytes/string.
    """
    if not isinstance(public_key, RSA.RsaKey):
        public_key = RSA.import_key(public_key)

    digest = SHA256.new()
    with Path(pdf_path).open("rb") as pdf_file:
        for chunk in iter(lambda: pdf_file.read(1024 * 1024), b""):
            digest.update(chunk)
    try:
        pss.new(public_key).verify(digest, signature)
        return True
    except (ValueError, TypeError):
        return False
