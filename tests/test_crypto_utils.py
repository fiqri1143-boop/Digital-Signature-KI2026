"""Unit tests for the digital-signature helpers in crypto_utils.py."""

import hashlib
import tempfile
import unittest
from pathlib import Path

import crypto_utils
from Crypto.PublicKey import RSA


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class CryptoUtilsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.private_key, cls.public_key = crypto_utils.generate_keys()
        cls.other_private_key, cls.other_public_key = crypto_utils.generate_keys()

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.pdf_path = self.root / "sample.pdf"
        # hash_pdf treats input as bytes and does not parse PDF structure.
        self.pdf_bytes = b"%PDF-1.4\nUnit test document\n%%EOF\n"
        self.pdf_path.write_bytes(self.pdf_bytes)

    def test_crypto_utils_is_imported_from_repository_root(self):
        self.assertEqual(
            Path(crypto_utils.__file__).resolve(),
            (REPOSITORY_ROOT / "crypto_utils.py").resolve(),
        )

    def test_generate_keys_returns_matching_rsa_2048_key_pair(self):
        private_key, public_key = crypto_utils.generate_keys()

        self.assertIsInstance(private_key, RSA.RsaKey)
        self.assertEqual(private_key.size_in_bits(), 2048)
        self.assertTrue(private_key.has_private())
        self.assertFalse(public_key.has_private())
        self.assertEqual(private_key.public_key().export_key(), public_key.export_key())

    def test_hash_pdf_matches_known_sha256(self):
        expected = hashlib.sha256(self.pdf_bytes).hexdigest()

        self.assertEqual(crypto_utils.hash_pdf(self.pdf_path), expected)

    def test_hash_pdf_handles_file_larger_than_one_mebibyte(self):
        large_path = self.root / "large.pdf"
        large_bytes = (b"large-pdf-test-block\x00" * 70000)[: 1024 * 1024 + 123]
        large_path.write_bytes(large_bytes)

        self.assertEqual(
            crypto_utils.hash_pdf(large_path), hashlib.sha256(large_bytes).hexdigest()
        )

    def test_sign_document_returns_rsa_2048_signature(self):
        signature = crypto_utils.sign_document(self.pdf_path, self.private_key)

        self.assertIsInstance(signature, bytes)
        self.assertEqual(len(signature), 256)

    def test_sign_document_accepts_private_key_pem(self):
        signature = crypto_utils.sign_document(
            self.pdf_path, self.private_key.export_key()
        )

        self.assertEqual(len(signature), 256)

    def test_sign_document_rejects_public_key_as_private_key(self):
        with self.assertRaisesRegex(ValueError, "bukan private key"):
            crypto_utils.sign_document(self.pdf_path, self.public_key)

    def test_verify_document_accepts_original_document_and_matching_key(self):
        signature = crypto_utils.sign_document(self.pdf_path, self.private_key)

        self.assertTrue(
            crypto_utils.verify_document(self.pdf_path, signature, self.public_key)
        )

    def test_verify_document_rejects_document_tampered_by_one_byte(self):
        signature = crypto_utils.sign_document(self.pdf_path, self.private_key)
        tampered_bytes = bytearray(self.pdf_path.read_bytes())
        tampered_bytes[len(tampered_bytes) // 2] ^= 0x01
        self.pdf_path.write_bytes(tampered_bytes)

        self.assertFalse(
            crypto_utils.verify_document(self.pdf_path, signature, self.public_key)
        )

    def test_verify_document_rejects_signature_from_wrong_public_key(self):
        signature = crypto_utils.sign_document(self.pdf_path, self.private_key)

        self.assertFalse(
            crypto_utils.verify_document(
                self.pdf_path, signature, self.other_public_key
            )
        )

    def test_verify_document_rejects_modified_or_malformed_signature(self):
        signature = bytearray(
            crypto_utils.sign_document(self.pdf_path, self.private_key)
        )
        signature[0] ^= 0x01
        self.assertFalse(
            crypto_utils.verify_document(
                self.pdf_path, bytes(signature), self.public_key
            )
        )
        self.assertFalse(
            crypto_utils.verify_document(
                self.pdf_path, b"not-a-valid-signature", self.public_key
            )
        )


if __name__ == "__main__":
    unittest.main()
