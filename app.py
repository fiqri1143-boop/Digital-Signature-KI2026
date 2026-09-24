"""Flask entry point for the digital signature demo."""

from flask import Flask, render_template

app = Flask(__name__)


@app.get("/")
def index():
    """Render the simple landing page."""
    return render_template("index.html")


@app.post("/sign")
def sign():
    """Placeholder endpoint for signing a PDF (implementation to follow)."""
    return {"message": "Signing endpoint belum diimplementasikan."}, 501


@app.post("/verify")
def verify():
    """Placeholder endpoint for verifying a PDF (implementation to follow)."""
    return {"message": "Verification endpoint belum diimplementasikan."}, 501


if __name__ == "__main__":
    # Debug mode is convenient locally; disable it in production.
    app.run(debug=True)
