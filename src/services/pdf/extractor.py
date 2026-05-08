import pdfplumber

def extract_text(pdf_source):
    text = ""
    try:
        with pdfplumber.open(pdf_source) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"Error al extraer texto del PDF: {e}")
        return ""
    
    return text