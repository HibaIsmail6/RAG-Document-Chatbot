import re
from pypdf import PdfReader


def extract_text(pdf_path: str):
    reader = PdfReader(pdf_path)

    pages = []

    for page_number, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text()

        if page_text:
            page_text = page_text.replace("\r", "\n")

            # Keep line breaks, but clean excessive whitespace
            page_text = re.sub(r"[ \t]+", " ", page_text)
            page_text = re.sub(r"\n{2,}", "\n\n", page_text)

            pages.append({
                "text": page_text.strip(),
                "page": page_number
            })

    return pages