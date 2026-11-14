import io
from pathlib import Path

from pypdf import PdfReader


def pdf_text(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    return "\n\n".join(
        f"[Page {i}]\n{text}"
        for i, page in enumerate(reader.pages, 1)
        if (text := page.extract_text() or "").strip()
    )


def load_file(path: Path) -> tuple[str, str, str]:
    path = path.resolve(strict=True)
    if path.suffix.lower() == ".pdf":
        text = pdf_text(path.read_bytes())
    elif path.suffix.lower() in {".txt", ".md"}:
        text = path.read_text(encoding="utf-8-sig")
    else:
        raise ValueError("Supported formats: .txt, .md, .pdf")
    if not text.strip():
        raise ValueError("No text extracted. Scanned PDFs need OCR before ingestion.")
    return path.stem, path.as_uri(), text
