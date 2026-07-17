import re
from pypdf import PdfReader


def extract_text(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)

    pages = []

    for page in reader.pages:
        page_text = page.extract_text()

        if page_text:
            # normalize whitespace
            page_text = page_text.replace("\r", " ")
            page_text = page_text.replace("\n", " ")

            # collapse repeated spaces
            page_text = re.sub(r"\s+", " ", page_text)

            pages.append(page_text.strip())

    return "\n\n".join(pages)