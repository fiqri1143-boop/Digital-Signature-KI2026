# Menyediakan halaman dan endpoint untuk tanda tangan serta verifikasi PDF.
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
from werkzeug.utils import secure_filename
from Crypto.PublicKey import RSA

import crypto_utils

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024
DIREKTORI_DATA = Path(app.instance_path)
JALUR_KUNCI = DIREKTORI_DATA / "keys" / "signing_private.pem.enc"
DIREKTORI_CATATAN = DIREKTORI_DATA / "verification_records"


@app.get("/")
# Menampilkan halaman beranda aplikasi.
def index():
    return render_template("index.html", halaman_aktif="home")


@app.get("/sign")
# Menampilkan halaman untuk membuat tanda tangan digital.
def sign_page():
    return render_template("sign.html", halaman_aktif="sign")


# Membuka kunci privat terenkripsi atau membuatnya saat pertama digunakan.
def get_or_create_signing_key(frasa_sandi):
    JALUR_KUNCI.parent.mkdir(parents=True, exist_ok=True)
    if JALUR_KUNCI.exists():
        try:
            kunci_privat = RSA.import_key(JALUR_KUNCI.read_bytes(), passphrase=frasa_sandi)
        except (ValueError, IndexError, TypeError) as kesalahan:
            raise ValueError("Passphrase salah atau berkas kunci tidak valid.") from kesalahan
        return kunci_privat

    kunci_privat, _ = crypto_utils.generate_keys()
    pem_terenkripsi = kunci_privat.export_key(
        format="PEM",
        passphrase=frasa_sandi,
        pkcs=8,
        protection="scryptAndAES128-CBC",
    )
    JALUR_KUNCI.write_bytes(pem_terenkripsi)
    return kunci_privat


# Menambahkan QR verifikasi pada halaman terakhir PDF.
def add_verification_qr(isi_pdf, tautan_verifikasi):
    gambar_qr = qrcode.make(
        tautan_verifikasi,
        image_factory=qrcode.image.svg.SvgPathImage,
        box_size=6,
        border=2,
    )
    penyangga_svg = BytesIO()
    gambar_qr.save(penyangga_svg)
    dokumen_svg = pymupdf.open(stream=penyangga_svg.getvalue(), filetype="svg")
    gambar_qr = dokumen_svg[0].get_pixmap(matrix=pymupdf.Matrix(3, 3), alpha=False).tobytes("png")

    dokumen = pymupdf.open(stream=isi_pdf, filetype="pdf")
    halaman = dokumen[-1]
    ukuran_qr = 105
    jarak_tepi = 24
    area = pymupdf.Rect(
        halaman.rect.width - ukuran_qr - jarak_tepi,
        halaman.rect.height - ukuran_qr - jarak_tepi,
        halaman.rect.width - jarak_tepi,
        halaman.rect.height - jarak_tepi,
    )
    halaman.draw_rect(area + (-5, -5, 5, 5), color=(1, 1, 1), fill=(1, 1, 1), overlay=True)
    halaman.insert_image(area, stream=gambar_qr, overlay=True)
    return dokumen.tobytes(garbage=4, deflate=True)


# Mengganti nama contoh pada PDF jika teksnya tersedia.
def replace_sample_name(isi_pdf, nama_penanda_tangan):
    dokumen = pymupdf.open(stream=isi_pdf, filetype="pdf")
    kecocokan = []
    for halaman in dokumen:
        kecocokan.extend((halaman, area) for area in halaman.search_for("MAHASISWA CONTOH"))

    if not kecocokan:
        dokumen.close()
        return isi_pdf

    for halaman, area in kecocokan:
        halaman.add_redact_annot(area, fill=(1, 1, 1))
    for halaman in dokumen:
        halaman.apply_redactions()

    for halaman, area in kecocokan:
        # Menjaga nama pengganti tetap rata tengah dalam satu baris.
        kotak_teks = pymupdf.Rect(
            50, area.y0 - 4, halaman.rect.width - 50, area.y1 + 6
        )
        lebar_teks_awal = pymupdf.get_text_length(
            nama_penanda_tangan, fontname="hebo", fontsize=1
        )
        ukuran_font = min(20, kotak_teks.width / max(lebar_teks_awal, 1))
        halaman.insert_textbox(
            kotak_teks,
            nama_penanda_tangan,
            fontname="hebo",
            fontsize=ukuran_font,
            align=pymupdf.TEXT_ALIGN_CENTER,
            color=(0.141, 0.349, 0.812),
        )

    pdf_personalisasi = dokumen.tobytes(garbage=4, deflate=True)
    dokumen.close()
    return pdf_personalisasi


# Menyiapkan nama arsip unduhan yang aman dan mudah dikenali.
def buat_nama_arsip(nama_pilihan, nama_pdf):
    nama_dasar = nama_pilihan.strip() or f"{Path(nama_pdf).stem}_bertanda_tangan"
    nama_dasar = Path(nama_dasar).stem
    nama_aman = secure_filename(nama_dasar).strip("._-")
    return f"{nama_aman or 'hasil_tanda_tangan'}.zip"


@app.post("/sign")
# Memvalidasi masukan, menandatangani PDF, lalu mengirim arsip hasilnya.
def sign():
    berkas_pdf = request.files.get("pdf")
    frasa_sandi = request.form.get("passphrase", "")
    nama_arsip = buat_nama_arsip(request.form.get("archive_name", ""), berkas_pdf.filename if berkas_pdf else "")
    metadata_penanda_tangan = {
        "name": request.form.get("name", "").strip(),
        "title": request.form.get("title", "").strip(),
        "institution": request.form.get("institution", "").strip(),
        "date": request.form.get("date", "").strip() or date.today().isoformat(),
    }
    if not berkas_pdf or not berkas_pdf.filename:
        return jsonify(error="Pilih file PDF yang akan ditandatangani."), 400
    if Path(berkas_pdf.filename).suffix.lower() != ".pdf":
        return jsonify(error="File yang dipilih harus berformat PDF."), 400
    if len(frasa_sandi) < 8:
        return jsonify(error="Passphrase kunci minimal 8 karakter."), 400
    if not metadata_penanda_tangan["name"] or not metadata_penanda_tangan["title"] or not metadata_penanda_tangan["institution"]:
        return jsonify(error="Lengkapi nama, jabatan, dan institusi penandatangan."), 400
    if any(len(nilai) > 120 for nama_field, nilai in metadata_penanda_tangan.items() if nama_field != "institution") or len(metadata_penanda_tangan["institution"]) > 200:
        return jsonify(error="Metadata terlalu panjang; pendekkan nama, jabatan, atau institusi."), 400

    try:
        with tempfile.TemporaryDirectory() as direktori_sementara:
            jalur_masukan = Path(direktori_sementara) / "source.pdf"
            berkas_pdf.save(jalur_masukan)
            pdf_asli = jalur_masukan.read_bytes()
            # Tanda tangan mencakup PDF akhir bersama QR verifikasi.
            token = secrets.token_urlsafe(18)
            tautan_verifikasi = url_for(
                "verify_by_token",
                token=token,
                _external=True,
                name=metadata_penanda_tangan["name"],
                title=metadata_penanda_tangan["title"],
                institution=metadata_penanda_tangan["institution"],
                date=metadata_penanda_tangan["date"],
            )
            pdf_personalisasi = replace_sample_name(pdf_asli, metadata_penanda_tangan["name"])
            pdf_bertanda_tangan = add_verification_qr(pdf_personalisasi, tautan_verifikasi)
            jalur_final = Path(direktori_sementara) / "signed.pdf"
            jalur_final.write_bytes(pdf_bertanda_tangan)
            kunci_privat = get_or_create_signing_key(frasa_sandi)
            kunci_publik = kunci_privat.public_key()
            tanda_tangan = crypto_utils.sign_document(jalur_final, kunci_privat)
    except ValueError as kesalahan:
        return jsonify(error=str(kesalahan)), 400
    except Exception as kesalahan:
        # Menyembunyikan jalur lokal dan rincian error internal dari browser.
        app.logger.exception("Failed to sign uploaded PDF")
        return jsonify(error="PDF tidak dapat diproses. Pastikan berkas PDF valid."), 400

    pem_publik = kunci_publik.export_key(format="PEM")
    DIREKTORI_CATATAN.mkdir(parents=True, exist_ok=True)
    catatan = {
        **metadata_penanda_tangan,
        "verification_url": tautan_verifikasi,
        "signature": base64.b64encode(tanda_tangan).decode("ascii"),
        "public_key": pem_publik.decode("ascii"),
    }
    (DIREKTORI_CATATAN / f"{token}.json").write_text(json.dumps(catatan), encoding="utf-8")

    arsip = BytesIO()
    with ZipFile(arsip, "w", ZIP_DEFLATED) as paket:
        paket.writestr("signed_document.pdf", pdf_bertanda_tangan)
        paket.writestr("signature.sig", tanda_tangan)
        paket.writestr("public_key.pem", pem_publik)
        paket.writestr(
            "README.txt",
            "Dokumen PDF sudah memuat QR-Code verifikasi. Pindai QR untuk membuka "
            "halaman verifikasi. Simpan signature.sig dan public_key.pem untuk "
            "verifikasi manual. Kunci privat tersimpan terenkripsi di server lokal.\n",
        )
    arsip.seek(0)
    return send_file(
        arsip,
        mimetype="application/zip",
        as_attachment=True,
        download_name=nama_arsip,
    )


# Memuat catatan verifikasi berdasarkan token yang aman.
def load_verification_record(token):
    if not token or not all(karakter.isalnum() or karakter in "_-" for karakter in token):
        return None
    jalur = DIREKTORI_CATATAN / f"{token}.json"
    if not jalur.is_file():
        return None
    try:
        return json.loads(jalur.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


@app.route("/verify/<token>", methods=["GET", "POST"])
# Memverifikasi PDF melalui tautan QR yang memiliki token.
def verify_by_token(token):
    catatan = load_verification_record(token)
    if catatan is None:
        return render_template("verify.html", pesan_error="Data verifikasi tidak ditemukan."), 404
    if request.method == "GET":
        return render_template("verify.html", catatan=catatan, token=token)

    berkas_pdf = request.files.get("pdf")
    if not berkas_pdf or not berkas_pdf.filename or Path(berkas_pdf.filename).suffix.lower() != ".pdf":
        return jsonify(error="Pilih dokumen PDF yang akan diverifikasi."), 400
    try:
        with tempfile.TemporaryDirectory() as direktori_sementara:
            jalur_pdf = Path(direktori_sementara) / "document.pdf"
            berkas_pdf.save(jalur_pdf)
            valid = crypto_utils.verify_document(
                jalur_pdf,
                base64.b64decode(catatan["signature"], validate=True),
                catatan["public_key"],
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


@app.get("/verify")
# Menampilkan halaman untuk memeriksa tanda tangan secara manual.
def verify_page():
    return render_template("verify_manual.html", halaman_aktif="verify")


@app.post("/verify")
# Memeriksa PDF menggunakan file tanda tangan dan kunci publik.
def verify():
    berkas_pdf = request.files.get("pdf")
    tanda_tangan = request.files.get("signature")
    kunci_publik = request.files.get("public_key")
    if not all((berkas_pdf, tanda_tangan, kunci_publik)):
        return jsonify(error="Pilih PDF, file signature.sig, dan public_key.pem."), 400
    if not berkas_pdf.filename or Path(berkas_pdf.filename).suffix.lower() != ".pdf":
        return jsonify(error="Dokumen yang diverifikasi harus berformat PDF."), 400
    try:
        with tempfile.TemporaryDirectory() as direktori_sementara:
            jalur_pdf = Path(direktori_sementara) / "document.pdf"
            berkas_pdf.save(jalur_pdf)
            valid = crypto_utils.verify_document(jalur_pdf, tanda_tangan.read(), kunci_publik.read())
    except (ValueError, TypeError, IndexError):
        return jsonify(error="File kunci publik atau tanda tangan tidak valid."), 400
    return jsonify(
        valid=valid,
        message=(
            "Tanda tangan valid. Dokumen cocok dengan tanda tangan."
            if valid
            else "Tanda tangan tidak valid atau dokumen telah berubah."
        ),
    )


@app.errorhandler(413)
# Mengirim pesan saat unggahan melebihi batas ukuran.
def file_too_large(_kesalahan):
    return jsonify(error="Ukuran file maksimal 20 MB."), 413


if __name__ == "__main__":
    # Membuka server untuk akses komputer atau ponsel di jaringan lokal.
    app.run(host="0.0.0.0", port=5000, debug=True)
