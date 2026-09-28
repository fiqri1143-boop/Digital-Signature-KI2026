"""Flask web app for signing and verifying PDF files."""

import base64
from datetime import date
from io import BytesIO
import json
from pathlib import Path
import secrets
import tempfile
from zipfile import ZIP_DEFLATED, ZipFile

import pymupdf
import qrcode
import qrcode.image.svg
from flask import Flask, jsonify, render_template, request, send_file, url_for
from Crypto.PublicKey import RSA

import crypto_utils

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024
DATA_DIR = Path(app.instance_path)
KEY_PATH = DATA_DIR / "keys" / "signing_private.pem.enc"
RECORDS_DIR = DATA_DIR / "verification_records"


@app.get("/")
def index():
    return render_template("index.html")


def get_or_create_signing_key(passphrase):
    """Load the persistent encrypted key, or create it on first use."""
    KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
    if KEY_PATH.exists():
        try:
            private_key = RSA.import_key(KEY_PATH.read_bytes(), passphrase=passphrase)
        except (ValueError, IndexError, TypeError) as error:
            raise ValueError("Passphrase salah atau berkas kunci tidak valid.") from error
        return private_key

    private_key, _ = crypto_utils.generate_keys()
    encrypted_pem = private_key.export_key(
        format="PEM",
        passphrase=passphrase,
        pkcs=8,
        protection="scryptAndAES128-CBC",
    )
    KEY_PATH.write_bytes(encrypted_pem)
    return private_key


def add_verification_qr(pdf_bytes, verification_url):
    """Append a scannable verification link to the final PDF page."""
    qr = qrcode.make(
        verification_url,
        image_factory=qrcode.image.svg.SvgPathImage,
        box_size=6,
        border=2,
    )
    svg_buffer = BytesIO()
    qr.save(svg_buffer)
    svg_doc = pymupdf.open(stream=svg_buffer.getvalue(), filetype="svg")
    qr_png = svg_doc[0].get_pixmap(matrix=pymupdf.Matrix(3, 3), alpha=False).tobytes("png")

    document = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    page = document[-1]
    qr_size = 105
    margin = 24
    rect = pymupdf.Rect(
        page.rect.width - qr_size - margin,
        page.rect.height - qr_size - margin,
        page.rect.width - margin,
        page.rect.height - margin,
    )
    page.draw_rect(rect + (-5, -5, 5, 5), color=(1, 1, 1), fill=(1, 1, 1), overlay=True)
    page.insert_image(rect, stream=qr_png, overlay=True)
    return document.tobytes(garbage=4, deflate=True)


@app.post("/sign")
def sign():
    pdf = request.files.get("pdf")
    passphrase = request.form.get("passphrase", "")
    metadata = {
        "name": request.form.get("name", "").strip(),
        "title": request.form.get("title", "").strip(),
        "institution": request.form.get("institution", "").strip(),
        "date": request.form.get("date", "").strip() or date.today().isoformat(),
    }
    if not pdf or not pdf.filename:
        return jsonify(error="Pilih file PDF yang akan ditandatangani."), 400
    if Path(pdf.filename).suffix.lower() != ".pdf":
        return jsonify(error="File yang dipilih harus berformat PDF."), 400
    if len(passphrase) < 8:
        return jsonify(error="Passphrase kunci minimal 8 karakter."), 400
    if not metadata["name"] or not metadata["title"] or not metadata["institution"]:
        return jsonify(error="Lengkapi nama, jabatan, dan institusi penandatangan."), 400
    if any(len(value) > 120 for key, value in metadata.items() if key != "institution") or len(metadata["institution"]) > 200:
        return jsonify(error="Metadata terlalu panjang; pendekkan nama, jabatan, atau institusi."), 400

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "source.pdf"
            pdf.save(input_path)
            original_pdf = input_path.read_bytes()
            # The link points to a record created below; the signature covers
            # the final PDF, including this QR code.
            token = secrets.token_urlsafe(18)
            verification_url = url_for(
                "verify_by_token",
                token=token,
                _external=True,
                name=metadata["name"],
                title=metadata["title"],
                institution=metadata["institution"],
                date=metadata["date"],
            )
            signed_pdf = add_verification_qr(original_pdf, verification_url)
            final_path = Path(temp_dir) / "signed.pdf"
            final_path.write_bytes(signed_pdf)
            private_key = get_or_create_signing_key(passphrase)
            public_key = private_key.public_key()
            signature = crypto_utils.sign_document(final_path, private_key)
    except ValueError as error:
        return jsonify(error=str(error)), 400
    except Exception as error:
        # Do not leak local paths or internal exceptions to the browser.
        app.logger.exception("Failed to sign uploaded PDF")
        return jsonify(error="PDF tidak dapat diproses. Pastikan berkas PDF valid."), 400

    public_pem = public_key.export_key(format="PEM")
    RECORDS_DIR.mkdir(parents=True, exist_ok=True)
    record = {
        **metadata,
        "verification_url": verification_url,
        "signature": base64.b64encode(signature).decode("ascii"),
        "public_key": public_pem.decode("ascii"),
    }
    (RECORDS_DIR / f"{token}.json").write_text(json.dumps(record), encoding="utf-8")

    archive = BytesIO()
    with ZipFile(archive, "w", ZIP_DEFLATED) as bundle:
        bundle.writestr("signed_document.pdf", signed_pdf)
        bundle.writestr("signature.sig", signature)
        bundle.writestr("public_key.pem", public_pem)
        bundle.writestr(
            "README.txt",
            "Dokumen PDF sudah memuat QR-Code verifikasi. Pindai QR untuk membuka "
            "halaman verifikasi. Simpan signature.sig dan public_key.pem untuk "
            "verifikasi manual. Kunci privat tersimpan terenkripsi di server lokal.\n",
        )
    archive.seek(0)
    return send_file(
        archive,
        mimetype="application/zip",
        as_attachment=True,
        download_name="hasil_tanda_tangan.zip",
    )


def load_verification_record(token):
    if not token or not all(char.isalnum() or char in "_-" for char in token):
        return None
    path = RECORDS_DIR / f"{token}.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


@app.route("/verify/<token>", methods=["GET", "POST"])
def verify_by_token(token):
    record = load_verification_record(token)
    if record is None:
        return render_template("verify.html", error="Data verifikasi tidak ditemukan."), 404
    if request.method == "GET":
        return render_template("verify.html", record=record, token=token)

    pdf = request.files.get("pdf")
    if not pdf or not pdf.filename or Path(pdf.filename).suffix.lower() != ".pdf":
        return jsonify(error="Pilih dokumen PDF yang akan diverifikasi."), 400
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "document.pdf"
            pdf.save(pdf_path)
            valid = crypto_utils.verify_document(
                pdf_path,
                base64.b64decode(record["signature"], validate=True),
                record["public_key"],
            )
    except (ValueError, TypeError, KeyError):
        return jsonify(error="Data tanda tangan tidak valid."), 400
    return jsonify(
        valid=valid,
        message=(
            "Tanda tangan valid. Dokumen cocok dengan data penandatangan."
            if valid
            else "Tanda tangan tidak valid atau dokumen telah berubah."
        ),
    )


@app.post("/verify")
def verify():
    pdf = request.files.get("pdf")
    signature = request.files.get("signature")
    public_key = request.files.get("public_key")
    if not all((pdf, signature, public_key)):
        return jsonify(error="Pilih PDF, file signature.sig, dan public_key.pem."), 400
    if not pdf.filename or Path(pdf.filename).suffix.lower() != ".pdf":
        return jsonify(error="Dokumen yang diverifikasi harus berformat PDF."), 400
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "document.pdf"
            pdf.save(pdf_path)
            is_valid = crypto_utils.verify_document(pdf_path, signature.read(), public_key.read())
    except (ValueError, TypeError, IndexError):
        return jsonify(error="File kunci publik atau tanda tangan tidak valid."), 400
    return jsonify(
        valid=is_valid,
        message=(
            "Tanda tangan valid. Dokumen cocok dengan tanda tangan."
            if is_valid
            else "Tanda tangan tidak valid atau dokumen telah berubah."
        ),
    )


@app.errorhandler(413)
def file_too_large(_error):
    return jsonify(error="Ukuran file maksimal 20 MB."), 413


if __name__ == "__main__":
    app.run(debug=True)
