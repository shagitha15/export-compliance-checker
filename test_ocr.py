from ocr import extract_text_from_pdf

page_text = extract_text_from_pdf(
    "uploads/bilexor-commercial-invoice-template_78ddd12ab7.pdf"
)

for page_num, text in page_text.items():
    print(f"--- Page {page_num} ---")
    print(text)