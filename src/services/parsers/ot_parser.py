import re
import ast


VALID_CONSTANTS = ["MAHIZ", "BAJA", "ALTA", "PP"]

KNOWN_LABELS = (
    r"Fecha de Entrega|Referencia|Orden de Compra|Orden de Trabajo|Cliente|"
    r"Cant\.|Procesos|Peso Bolsa|Formato Bolsa|Calibre|Caras|Ancho Extrusi[oó]n|"
    r"Largo Extrusi[oó]n|Metros|Kilos|Observaciones|Sellado|Troquelado|"
    r"Presentaci[oó]n|Paquetes|Bultos|Tipo|Impresi[oó]n|Fuelle|Lateral|Repeticiones"
)


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


def validate_measure(calculated_width, extrusion_width, tolerance=1.0):
    """
    Valida si el ancho calculado coincide con el ancho de extrusión.
    Soporta una tolerancia predefinida (por defecto 1.0 cm).
    """
    if calculated_width is None or extrusion_width is None:
        return False
    try:
        calc = float(calculated_width)
        ext = float(str(extrusion_width).replace(",", "."))
        return abs(calc - ext) <= tolerance
    except (ValueError, TypeError):
        return False


def clean_value(value: str):
    if not value:
        return None
    cleaned = value.strip()
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned or None


def clean_single_line(value: str) -> str | None:
    if not value:
        return None
    line = value.split("\n")[0].strip()
    line = re.sub(r"\s{2,}", " ", line)
    return line or None


def extract_constant(text: str):
    composition_match = re.search(
        r"BPREF\d+\s+(MAHIZ|BAJA|ALTA|PP)", text, re.IGNORECASE
    )

    if composition_match:
        return composition_match.group(1).upper()

    reference_match = re.search(r"Referencia[:\s]+(.+)", text, re.IGNORECASE)

    if reference_match:
        reference_text = reference_match.group(1)

        constant_match = re.search(
            r"\b(MAHIZ|BAJA|ALTA|PP)\b", reference_text, re.IGNORECASE
        )

        if constant_match:
            return constant_match.group(1).upper()

    return None


def extract_measure(reference: str):
    if not reference:
        return None, None, None

    ref_norm = reference.replace(",", ".")
    ref_line = ref_norm.split("\n")[0]

    pattern = r"((?:\d+(?:\.\d+)?\s*[\+\-\*\/]\s*)*\d+(?:\.\d+)?)\s*[Xx*]\s*(\d+(?:\.\d+)?)"

    match = re.search(pattern, ref_line)

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
        r"([\d.,]+)\s*%\s*"
        r"(.*?)\s*"
        r"([\d.,]+)\s*%",
        text,
        re.IGNORECASE,
    )

    for item in pattern:
        # Limpiar el nombre de la materia secundaria si quedó con espacios
        mat_sec = item[3].strip() if item[3] else None
        
        compositions.append(
            {
                "Referencia Materia Prima": item[0],
                "Constante": item[1].upper(),
                "% Materia Prima": item[2],
                "Materia Secundaria": mat_sec,
                "% Secundario": item[4],
            }
        )

    return compositions


def extract_fuelles(text: str):
    fuelles = []
    pattern = re.findall(
        r"(Lateral|Central|Superior|Inferior)\s+([\d.,]+)\s+([\d.,]+)",
        text,
        re.IGNORECASE,
    )
    for item in pattern:
        fuelles.append(
            {
                "Tipo": item[0].capitalize(),
                "Medida 1": item[1],
                "Medida 2": item[2],
            }
        )
    return fuelles


def extract_impresion(text: str):
    impresiones = []
    caras_matches = re.findall(
        r"Cara Impresi[oó]n\s*\d+\s+(.+?)(?=\n|Cara Impresi[oó]n|Rodillo|$)",
        text,
        re.IGNORECASE,
    )
    for cara in caras_matches:
        valor = cara.strip()
        if valor:
            impresiones.append(valor)
    return impresiones


def extract_ot(text: str):
    data = {}

    fields = {
        "Fecha de Entrega": r"Fecha de Entrega[:\s]+(\d{2}/\d{2}/\d{4})",
        "Referencia": r"Referencia[:\s]+(.+?)(?=\n|Orden de Compra|$)",
        "Orden de Compra(OC)": r"Orden de Compra\(OC\)[:\s]*([\w\-]*)",
        "Orden de Trabajo": r"Orden de Trabajo[:\s]+(OT\d+)",
        "Cliente": r"Cliente[:\s]+(.+?)(?=\s{2,}|\s+Cant\.|\s+Procesos|\n|$)",
        "Cant. Planificada": r"Cant\. Planificada[:\s]*([\d,. ]+?)(?=\n|$)",
        "Procesos": r"Procesos[:\s]+(.+?)(?=\n|Cant\.|$)",
        "Peso Bolsa (gr)": r"Peso Bolsa \(gr\)[:\s]*([\d.,]+)",
        "Formato Bolsa": r"Formato Bolsa[:\s]*(.+?)(?=\n|Caras|Calibre|$)",
        "Caras": r"Caras[:\s]*([\d]+)(?=\n|$)",
        "Calibre Extrusión": r"(?:^|\n)Calibre[:\s]*([\d.,]+)",
        "Ancho Extrusión (cm)": r"Ancho Extrusi[oó]n \(cm\)[:\s]*([\d.,]+)",
        "Largo Extrusión (cm)": r"Largo Extrusi[oó]n \(cm\)[:\s]*([\d.,]+)",
        "Metros": r"(?<!\w)Metros[:\s]*([\d.,]+)",
        "Kilos": r"(?<!\w)Kilos[:\s]*([\d.,]+)",
        "Largo Sellado (cm)": r"Largo General \(cm\)[:\s]*([\d.,]+)",
        "Tipo Sellado": r"Tipo Sellado[:\s]*(.+?)(?=\n|Calibre|$)",
        "Calibre Sellado": r"Sellado.*?\nCalibre[:\s]*([\d.,]+)",
        "Tipo Troquelado": r"Tipo Troquel[:\s]*(.+?)(?=\n|$)",
        "Paquetes de (Unidades)": r"Paquetes de \(Unidades\)[:\s]*([\d.,]+)",
        "Bultos de (paquetes)": r"Bultos de \(paquetes\)[:\s]*([\d.,]+)",
    }

    for field_name, pattern in fields.items():
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        raw = match.group(1) if match else None
        data[field_name] = clean_single_line(raw)

    if data.get("Cant. Planificada"):
        data["Cant. Planificada"] = re.sub(r"[,\s]", "", data["Cant. Planificada"].replace(".", ""))

    data["Constante"] = extract_constant(text)

    ancho, largo, medida = extract_measure(data.get("Referencia"))

    data["Ancho General (cm)"] = ancho
    data["Largo General (cm)"] = largo
    data["Medida"] = medida

    data["Validación Ancho"] = validate_measure(
        ancho, data.get("Ancho Extrusión (cm)")
    )

    data["Composiciones"] = extract_compositions(text)
    data["Fuelles"] = extract_fuelles(text)
    data["Impresión por Cara"] = extract_impresion(text)

    observations_raw = re.findall(
        r"Observaciones[:\s]*(.+?)(?=\n(?:" + KNOWN_LABELS + r")|\Z)",
        text,
        re.DOTALL | re.IGNORECASE,
    )

    data["Observaciones"] = [
        re.sub(r"\s{2,}", " ", obs).strip()
        for obs in observations_raw
        if obs.strip()
    ]

    return data
