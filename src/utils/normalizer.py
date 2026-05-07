import re 

def normalize_reference(Reference: str):

    match = re.search(r"(\d+)\s*[Xx]\s*(\d+)", Reference)

    if not match:
        return None
    
    return f"{match.group(1)}*{match.group(2)}"