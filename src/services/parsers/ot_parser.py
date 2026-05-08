import re
import ast



VALID_CONSTANTS = ["MAHIZ", "BAJA", "ALTA", "PP"]


def safe_math_eval(expr: str) -> float:
    """Evalúa de forma segura una expresión matemática simple sin usar eval()."""
    try:
        node = ast.parse(expr.replace(" ", "").replace(",", "."), mode="eval").body

        def _eval(node):
            if isinstance(node, ast.Constant):
                return node.value
            elif isinstance(node, (ast.Num)):
                return node.n
            elif isinstance(node, ast.BinOp):
                left = _eval(node.left)
                right = _eval(node.right)
                if isinstance(node.op, ast.Add):
                    return left + right
                elif isinstance(node.op, ast.Sub):
                    return left - right
                elif isinstance(node.op, ast.Mult):
                    return left * right
                elif isinstance(node.op, ast.Div):
                    return left / right if right != 0 else 0
            elif isinstance(node, ast.UnaryOp):
                operand = _eval(node.operand)
                if isinstance(node.op, ast.USub):
                    return -operand
                return operand
            raise ValueError("Operación no soportada")

        return float(_eval(node))
    except Exception:
        return 0.0


def inches_to_cm(value):
    return round(float(value) * 2.54, 2)


def validate_measure(calculated_width, extrusion_width, tolerance=0.5):
    """
    Valida si el ancho calculado coincide con el ancho de extrusión.
    Soporta una tolerancia predefinida (por defecto 0.5 cm).
    """
    if calculated_width is None or extrusion_width is None:
        return False
    try:
        calc = float(calculated_width)
        ext_str = str(extrusion_width).replace(",", ".")
        ext = float(ext_str)
        return abs(calc - ext) <= tolerance
    except (ValueError, TypeError):
        return False




def clean_value(value: str):

    if not value:
        return None

    return value.strip()


def extract_constant(text: str):

    composition_match = re.search(
        r"BPREF\d+\s+(MAHIZ|BAJA|ALTA|PP)", text, re.IGNORECASE
    )

    if composition_match:
        return composition_match.group(1).upper()

    reference_match = re.search(r"Referencia:\s*(.+)", text, re.IGNORECASE)

    if reference_match:

        reference_text = reference_match.group(1)

        constant_match = re.search(
            r"(MAHIZ|BAJA|ALTA|PP)", reference_text, re.IGNORECASE
        )

        if constant_match:
            return constant_match.group(1).upper()

    return None


def extract_measure(reference: str):
    if not reference:
        return None, None, None

    ref_norm = reference.replace(",", ".")

    pattern = r"((?:\d+(?:\.\d+)?\s*[\+\-\*\/]\s*)*\d+(?:\.\d+)?)\s*[Xx*]\s*(\d+(?:\.\d+)?)"

    match = re.search(pattern, ref_norm)

    if not match:
        return None, None, None

    width_expr = match.group(1).strip()
    height_str = match.group(2).strip()

    width = safe_math_eval(width_expr)
    height = float(height_str)

    is_inches = bool(
        re.search(r'\b(IN|INCH|INCHES|PULG)\b|"', reference, re.IGNORECASE)
    )

    if is_inches:
        width = round(width * 2.54, 2)
        height = round(height * 2.54, 2)
    else:
        width = round(width, 2)
        height = round(height, 2)

    def format_num(n):
        """Formatea el número eliminando .0 si es entero."""
        if n is None:
            return None
        return str(int(n)) if float(n).is_integer() else str(n)

    ancho_f = format_num(width)
    largo_f = format_num(height)
    medida_formateada = f"{ancho_f}*{largo_f}"

    return ancho_f, largo_f, medida_formateada





def extract_compositions(text: str):

    compositions = []

    pattern = re.findall(
        r"(BPREF\d+)\s+"
        r"(MAHIZ|BAJA|ALTA|PP)\s+"
        r"([\d.,]+)\s*%\s+"
        r"(.+?)\s+"
        r"([\d.,]+)\s*%",
        text,
        re.IGNORECASE,
    )

    for item in pattern:

        compositions.append(
            {
                "Referencia Materia Prima": item[0],
                "Constante": item[1].upper(),
                "% Materia Prima": item[2],
                "Materia Secundaria": item[3],
                "% Secundario": item[4],
            }
        )

    return compositions


def extract_ot(text: str):

    data = {}

    fields = {
        "Fecha de Entrega": r"Fecha de Entrega:\s*(\d{2}/\d{2}/\d{4})",
        "Referencia": r"Referencia:\s*(.+)",
        "Orden de Compra(OC)": r"Orden de Compra\(OC\):\s*(.*)",
        "Orden de Trabajo": r"Orden de Trabajo\s+(OT\d+)",
        "Cliente": r"Cliente\s+(.+?)\s+Cant\.",
        "Cant. Planificada": r"Cant\. Planificada\s*([\d,]+)",
        "Peso Bolsa (gr)": r"Peso Bolsa \(gr\)\s*([\d.,]+)",
        "Formato Bolsa": r"Formato Bolsa\s*(.+)",
        "Calibre Extrusión": r"Extrusión.*?Calibre\s*([\d.,]+)",
        "Ancho Extrusión (cm)": r"Ancho Extrusión \(cm\)\s*([\d.,]+)",
        "Largo Extrusión (cm)": r"Largo Extrusión \(cm\)\s*([\d.,]+)",
        "Metros": r"Metros\s*([\d.,]+)",
        "Kilos": r"Kilos\s*([\d.,]+)",
        "Tipo Sellado": r"Tipo Sellado\s*(.+)",
        "Paquetes de (Unidades)": r"Paquetes de \(Unidades\):\s*([\d.,]+)",
        "Bultos de (paquetes)": r"Bultos de \(paquetes\):\s*([\d.,]+)",
    }

    for field_name, pattern in fields.items():

        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)

        data[field_name] = clean_value(match.group(1)) if match else None

    data["Constante"] = extract_constant(text)

    ancho, largo, medida = extract_measure(data.get("Referencia"))

    data["Ancho General (cm)"] = ancho
    data["Largo General (cm)"] = largo
    data["Medida"] = medida

    data["Validación Ancho"] = validate_measure(
        ancho, data.get("Ancho Extrusión (cm)")
    )


    data["Composiciones"] = extract_compositions(text)

    observations = re.findall(
        r"Observaciones\s*(.+?)(?=\n[A-ZÁÉÍÓÚ][a-z]|$)", text, re.DOTALL
    )

    data["Observaciones"] = [obs.strip() for obs in observations if obs.strip()]

    return data
