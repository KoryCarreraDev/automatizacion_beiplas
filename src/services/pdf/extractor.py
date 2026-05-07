import pdfplumber

def extract_text(pdf_source):
    """
    Extrae el texto de un archivo PDF.
    pdf_source puede ser una ruta (str) o un objeto tipo archivo (file-like object).
    """
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