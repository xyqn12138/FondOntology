"""Extract text from the CNFO standard reference PDFs into .txt files."""
import pathlib
import sys

from pypdf import PdfReader

SRC_DIR = pathlib.Path(r"E:\LX\LX_fund\基金行业文档\国内数据标准资料")
OUT_DIR = SRC_DIR / "extracted_txt"
OUT_DIR.mkdir(exist_ok=True)


def extract(pdf_path: pathlib.Path) -> str:
    reader = PdfReader(str(pdf_path))
    parts = []
    for i, page in enumerate(reader.pages, 1):
        try:
            text = page.extract_text() or ""
        except Exception as exc:  # noqa: BLE001
            text = f"[page {i} extraction error: {exc}]"
        parts.append(f"\n===== PAGE {i} =====\n{text}")
    return "".join(parts)


def main() -> None:
    pdfs = sorted(SRC_DIR.glob("*.pdf"))
    for pdf in pdfs:
        out = OUT_DIR / (pdf.stem + ".txt")
        try:
            text = extract(pdf)
            out.write_text(text, encoding="utf-8")
            print(f"OK  {pdf.name} -> {out.name} ({len(text)} chars, {len(pdf.stem)} )")
        except Exception as exc:  # noqa: BLE001
            print(f"FAIL {pdf.name}: {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
