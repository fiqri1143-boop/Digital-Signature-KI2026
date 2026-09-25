"""Measure signing and verification latency for the current crypto_utils API.

Run from the repository root with ``python performance_test.py``.
The benchmark uses a temporary PDF-like byte fixture and never writes into the
project files. Key generation and a warm-up operation are excluded from timing.
"""

import statistics
import tempfile
import time
from pathlib import Path

import crypto_utils


TRIALS = 30
REPOSITORY_ROOT = Path(__file__).resolve().parent


def main():
    module_path = Path(crypto_utils.__file__).resolve()
    if module_path != (REPOSITORY_ROOT / "crypto_utils.py").resolve():
        raise RuntimeError(
            f"Expected crypto_utils.py in repository root, imported {module_path}"
        )

    # Key generation is deliberately outside every timed section.
    private_key, public_key = crypto_utils.generate_keys()
    pdf_bytes = (
        b"%PDF-1.4\n"
        b"Digital signature performance test fixture.\n"
        b"This temporary content is used for repeatable signing and verification.\n"
        b"%%EOF\n"
    )

    with tempfile.TemporaryDirectory(prefix="digital-signature-performance-") as temp_dir:
        pdf_path = Path(temp_dir) / "performance-sample.pdf"
        pdf_path.write_bytes(pdf_bytes)

        # Warm up the cryptographic path and prepare a valid signature before
        # starting verification measurements.
        verification_signature = crypto_utils.sign_document(pdf_path, private_key)
        if not crypto_utils.verify_document(
            pdf_path, verification_signature, public_key
        ):
            raise RuntimeError("Warm-up signature did not verify")

        signing_times = []
        last_signature = None
        for _ in range(TRIALS):
            start = time.perf_counter()
            signature = crypto_utils.sign_document(pdf_path, private_key)
            signing_times.append(time.perf_counter() - start)
            if not isinstance(signature, bytes):
                raise RuntimeError("sign_document did not return signature bytes")
            last_signature = signature

        verification_times = []
        for _ in range(TRIALS):
            start = time.perf_counter()
            valid = crypto_utils.verify_document(
                pdf_path, verification_signature, public_key
            )
            verification_times.append(time.perf_counter() - start)
            if not valid:
                raise RuntimeError("Verification failed during performance run")

    public_key_pem = public_key.export_key(format="PEM")
    if isinstance(public_key_pem, str):
        public_key_pem = public_key_pem.encode("ascii")

    # Tabular output is easy to paste into the report's results table.
    rows = [
        ("Repository crypto_utils.py", str(module_path)),
        ("Trials per operation", str(TRIALS)),
        ("Average signing time (ms)", f"{statistics.mean(signing_times) * 1000:.3f}"),
        (
            "Average verification time (ms)",
            f"{statistics.mean(verification_times) * 1000:.3f}",
        ),
        ("Signature size (bytes)", str(len(last_signature))),
        ("Public key size, PEM (bytes)", str(len(public_key_pem))),
        ("Test document size (bytes)", str(len(pdf_bytes))),
    ]

    print("Metric\tValue")
    for metric, value in rows:
        print(f"{metric}\t{value}")


if __name__ == "__main__":
    main()
