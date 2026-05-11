import re
import ast


VALID_CONSTANTS = ["MAHIZ", "BAJA", "ALTA", "PP"]

SECTION_DELIMITERS = [
    "Composiciones",
    r"Extrusi[oó]n",
    r"Fuelles\s+de\s+Extrusi[oó]n",
    r"Impresi[oó]n",
    "Sellado",
    "Troquelado",
    r"Presentaci[oó]n\s+Final",
]

_SECTION_PATTERN = re.compile(
    r"^(" + "|".join(SECTION_DELIMITERS) + r")\s*$",
    re.IGNORECASE | re.MULTILINE,
)


# ---------------------------------------------------------------------------
# Preprocesamiento
# ---------------------------------------------------------------------------

def normalize_pdf_text(text: str) -> str:
    if not text:
        return ""

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"[|¦]", " ", text)
    text = re.sub(r"_{3,}", " ", text)
    text = re.sub(r"\.{3,}", " ", text)
    text = re.sub(r"\x0c", "", text)
    text = "".join(char for char in text if char.isprintable() or char == "\n")

    lines = [line.strip() for line in text.split("\n")]
    cleaned = []
    prev_empty = False
    for line in lines:
        if not line:
            if not prev_empty:
                cleaned.append("")
            prev_empty = True
        else:
            cleaned.append(line)
            prev_empty = False

    return "\n".join(cleaned).strip()


# ---------------------------------------------------------------------------
# División en Secciones
# ---------------------------------------------------------------------------

def split_sections(text: str) -> dict[str, str]:
    normalized = normalize_pdf_text(text)

    section_markers = [
        ("composiciones", re.compile(r"^Composiciones\s*$", re.I | re.M)),
        ("extrusion", re.compile(r"^Extrusi[oó]n\s*$", re.I | re.M)),
        ("fuelles", re.compile(r"^Fuelles\s+de\s+Extrusi[oó]n\s*$", re.I | re.M)),
        ("impresion", re.compile(r"^Impresi[oó]n\s*$", re.I | re.M)),
        ("sellado", re.compile(r"^Sellado\s*$", re.I | re.M)),
        ("troquelado", re.compile(r"^Troquelado\s*$", re.I | re.M)),
        ("presentacion", re.compile(r"^Presentaci[oó]n\s+Final\s*$", re.I | re.M)),
    ]

    found = []
    for name, pattern in section_markers:
        match = pattern.search(normalized)
        if match:
            found.append((match.start(), match.end(), name))

    found.sort(key=lambda x: x[0])

    sections = {}

    header_end = found[0][0] if found else len(normalized)
    header_text = normalized[:header_end]

    info_match = re.search(
        r"Informaci[oó]n\s+General\s+y\s+Producto",
        header_text, re.IGNORECASE,
    )
    if info_match:
        sections["header"] = header_text[:info_match.start()].strip()
        sections["general"] = header_text[info_match.end():].strip()
    else:
        sections["header"] = header_text.strip()
        sections["general"] = ""

    for i, (start, end, name) in enumerate(found):
        next_start = found[i + 1][0] if i + 1 < len(found) else len(normalized)
        sections[name] = normalized[end:next_start].strip()

    return sections


# ---------------------------------------------------------------------------
# Lógica de Cálculo (SIN CAMBIOS)
# ---------------------------------------------------------------------------

def safe_math_eval(expr: str) -> float:
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
                if isinstance(node.op, ast.Add): return left + right
                elif isinstance(node.op, ast.Sub): return left - right
                elif isinstance(node.op, ast.Mult): return left * right
                elif isinstance(node.op, ast.Div): return left / right if right != 0 else 0
            elif isinstance(node, ast.UnaryOp):
                operand = _eval(node.operand)
                if isinstance(node.op, ast.USub): return -operand
                return operand
            raise ValueError("Operación no soportada")

        return float(_eval(node))
    except Exception:
        return 0.0


def validate_measure(calculated_width, extrusion_width, tolerance=1.0):
    if calculated_width is None or extrusion_width is None:
        return False
    try:
        calc = float(calculated_width)
        ext = float(str(extrusion_width).replace(",", "."))
        return abs(calc - ext) <= tolerance
    except (ValueError, TypeError):
        return False


def extract_measure(reference: str):
    if not reference:
        return None, None, None

    # Normalizar comas a puntos para evaluación matemática
    ref_norm = reference.replace(",", ".")
    ref_line = ref_norm.split("\n")[0]

    # Regex mejorada para capturar ancho (expresión) y largo (expresión + texto extra)
    pattern = r"((?:\d+(?:\.\d+)?\s*[\+\-\*\/]\s*)*\d+(?:\.\d+)?)\s*[Xx*]\s*([^,\n]+)"
    match = re.search(pattern, ref_line)

    if not match:
        return None, None, None

    width_expr = match.group(1).strip()
    largo_raw = match.group(2).strip()

    # 1. Detección de Solapa
    is_sl = bool(re.search(r"\bSL\b", largo_raw, re.I))
    is_doble = bool(re.search(r"\bDOBLE\b", largo_raw, re.I))

    # Evaluar ancho
    width = safe_math_eval(width_expr)
    
    # 2. Procesar Largo con lógica de Solapa
    if is_sl:
        # Extraer la parte matemática del largo eliminando "SL" y lo que siga
        largo_math_part = re.sub(r"\bSL\b.*", "", largo_raw, flags=re.I).strip()
        
        # 3. Separar el último número (la solapa)
        sl_match = re.search(r"^(.*?)\s*([\+\-])\s*(\d+(?:\.\d+)?)$", largo_math_part)
        
        if sl_match:
            base_expr = sl_match.group(1).strip()
            signo = sl_match.group(2)
            solapa_val = float(sl_match.group(3))
            
            # Evaluar la base matemática
            base_val = safe_math_eval(base_expr) if base_expr else 0.0
            
            # 4. Aplicar regla: SL sencilla -> mitad, SL DOBLE -> completo
            ajuste = solapa_val if is_doble else (solapa_val / 2)
            
            if signo == "+":
                height = base_val + ajuste
            else:
                height = base_val - ajuste
        else:
            # Fallback si no hay signos
            height = safe_math_eval(largo_math_part)
    else:
        # Caso normal sin solapa
        largo_clean = re.sub(r"[^\d\+\-\*\/\.\s].*", "", largo_raw).strip()
        height = safe_math_eval(largo_clean)

    # 5. Conversión a pulgadas
    is_inches = bool(re.search(r'\b(IN|INCH|INCHES|PULG)\b|"', reference, re.IGNORECASE))

    if is_inches:
        width = round(width * 2.54, 2)
        height = round(height * 2.54, 2)
    else:
        width = round(width, 2)
        height = round(height, 2)

    def format_num(n):
        if n is None: return None
        return str(int(n)) if float(n).is_integer() else str(n)

    ancho_f = format_num(width)
    largo_f = format_num(height)
    return ancho_f, largo_f, f"{ancho_f}*{largo_f}"


# ---------------------------------------------------------------------------
# Utilidades de Limpieza
# ---------------------------------------------------------------------------

def _clean(value: str | None) -> str | None:
    if not value:
        return None
    value = re.sub(r"\s+", " ", value).strip()
    value = re.sub(r"^[|:\s.\-]+|[|:\s.\-]+$", "", value)
    return value or None


def _find_field(text: str, label: str, multiline: bool = False) -> str | None:
    pattern = rf"{label}\s*:?\s*(.+)"
    if multiline:
        match = re.search(pattern, text, re.IGNORECASE)
    else:
        match = re.search(pattern, text, re.IGNORECASE)

    if not match:
        return None

    value = match.group(1)
    if not multiline:
        value = value.split("\n")[0]
    return _clean(value)


def _find_number(text: str, label: str) -> str | None:
    pattern = rf"{label}\s*:?\s*([\d.,]+)"
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1).strip() if match else None


# ---------------------------------------------------------------------------
# Extractores por Sección
# ---------------------------------------------------------------------------

def extract_header(text: str) -> dict:
    data = {}

    data["Fecha de Entrega"] = _find_field(text, r"Fecha\s+de\s+Entrega")

    ref_match = re.search(r"Referencia\s*:?\s*(.+?)(?=\nOrden\s+de\s+Compra|\Z)", text, re.I | re.DOTALL)
    if ref_match:
        ref_lines = ref_match.group(1).strip().split("\n")
        data["Referencia"] = _clean(" ".join(line.strip() for line in ref_lines))
    else:
        data["Referencia"] = None

    data["Orden de Compra(OC)"] = _find_field(text, r"Orden\s+de\s+Compra\s*\(?OC\)?\s*")

    return data


def extract_general_info(text: str) -> dict:
    data = {}
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    all_text = " ".join(lines)

    # 1. Orden de Trabajo
    ot_match = re.search(r"\bOT\d+\b", all_text, re.I)
    data["Orden de Trabajo"] = ot_match.group(0) if ot_match else None

    # 2. Cantidad Planificada
    # Buscar un número que esté cerca de "Cant" o "Cliente" (por el intercalado)
    cant_val = None
    cant_match = re.search(r"(?:Cant\.?|Cliente)\s+([\d,.]+)", all_text, re.I)
    if cant_match:
        cant_val = cant_match.group(1)
    
    if not cant_val:
        # Buscar el número más grande que no sea la OT
        numbers = re.findall(r"\b\d{1,3}(?:[.,]\d{3})*\b", all_text)
        for num in numbers:
            if num not in (data["Orden de Trabajo"] or ""):
                cant_val = num
                break
    
    data["Cant. Planificada"] = cant_val

    # 3. Procesos
    process_keywords = [
        "Extrusi[oó]n", "Impresi[oó]n", "Sellado", 
        "Troquelado", "Presentaci[oó]n\s+Final"
    ]
    found_processes = []
    for kw_pattern in process_keywords:
        m = re.search(kw_pattern, all_text, re.I)
        if m:
            found_processes.append(m.group(0))
    
    if found_processes:
        data["Procesos"] = ", ".join(found_processes)
    else:
        data["Procesos"] = None

    # 4. Cliente
    # Limpieza agresiva de lo que NO es cliente
    rem = all_text
    if data["Orden de Trabajo"]:
        rem = rem.replace(data["Orden de Trabajo"], "")
    if data["Cant. Planificada"]:
        rem = rem.replace(data["Cant. Planificada"], "")
    
    labels_to_remove = [
        r"Orden\s+de\s+Trabajo", r"Orden\s+de", r"Trabajo",
        r"Procesos", r"Cliente", r"Cant\.?\s*Planificada", 
        r"Cant\.", r"Planificada", r"Informaci[oó]n\s+General\s+y\s+Producto"
    ]
    for lbl in labels_to_remove:
        rem = re.sub(lbl, "", rem, flags=re.I)
    
    for kw in found_processes:
        rem = rem.replace(kw, "")

    # Eliminar comas sueltas que queden del intercalado de procesos
    rem = re.sub(r",\s*,", ",", rem)
    rem = re.sub(r"^[,\s]+|[,\s]+$", "", rem)
    
    data["Cliente"] = _clean(rem)

    # Post-procesar cantidad
    if data.get("Cant. Planificada"):
        val = re.sub(r"[.,\s]", "", str(data["Cant. Planificada"]))
        data["Cant. Planificada"] = val if val.isdigit() else data["Cant. Planificada"]

    return data


def extract_composiciones(text: str) -> list:
    compositions = []
    pattern = re.findall(
        r"(BPREF\d+)\s+(MAHIZ|BAJA|ALTA|PP)\s+([\d.,]+)\s*%\s*(.*?)\s*([\d.,]+)\s*%",
        text, re.IGNORECASE,
    )
    for item in pattern:
        compositions.append({
            "Referencia Materia Prima": item[0],
            "Constante": item[1].upper(),
            "% Materia Prima": item[2],
            "Materia Secundaria": item[3].strip() or None,
            "% Secundario": item[4],
        })
    return compositions


def extract_extrusion(text: str) -> dict:
    data = {}
    data["Peso Bolsa (gr)"] = _find_number(text, r"Peso\s+Bolsa\s*\(gr\)")
    data["Formato Bolsa"] = _find_field(text, r"Formato\s+Bolsa")
    data["Caras"] = _find_number(text, r"Caras")
    data["Calibre Extrusión"] = _find_number(text, r"Calibre")
    data["Ancho Extrusión (cm)"] = _find_number(text, r"Ancho\s+Extrusi[oó]n\s*\(cm\)")
    data["Largo Extrusión (cm)"] = _find_number(text, r"Largo\s+Extrusi[oó]n\s*\(cm\)")
    data["Metros"] = _find_number(text, r"Metros")
    data["Kilos"] = _find_number(text, r"Kilos")

    obs = _extract_section_observations(text)
    data["Observaciones Extrusión"] = obs
    return data


def extract_fuelles(text: str) -> list:
    fuelles = []
    pattern = re.findall(
        r"(Lateral|Central|Superior|Inferior)\s+([\d.,]+)\s+([\d.,]+)",
        text, re.IGNORECASE,
    )
    for item in pattern:
        fuelles.append({
            "Tipo": item[0].capitalize(),
            "Medida 1": item[1],
            "Medida 2": item[2],
        })
    return fuelles


def extract_impresion(text: str) -> dict:
    data = {}

    caras = []
    for m in re.finditer(r"Cara\s+Impresi[oó]n\s+\d+\s+(.+)", text, re.I):
        val = _clean(m.group(1))
        if val:
            caras.append(val)
    data["Impresión por Cara"] = caras

    data["Rodillo"] = _find_number(text, r"Rodillo")
    data["Repeticiones"] = _find_number(text, r"Repeticiones")

    obs = _extract_section_observations(text)
    data["Observaciones Impresión"] = obs
    return data


def extract_sellado(text: str) -> dict:
    data = {}
    data["Largo Sellado (cm)"] = _find_number(text, r"(?:Ancho|Largo)\s+General\s*\(cm\)")
    data["Tipo Sellado"] = _find_field(text, r"Tipo\s+Sellado")
    data["Calibre Sellado"] = _find_number(text, r"Calibre")

    obs = _extract_section_observations(text)
    data["Observaciones Sellado"] = obs
    return data


def extract_troquelado(text: str) -> dict:
    data = {}
    data["Tipo Troquelado"] = _find_field(text, r"Tipo\s+Troquel(?:ado)?")

    obs = _extract_section_observations(text)
    data["Observaciones Troquelado"] = obs
    return data


def extract_presentacion(text: str) -> dict:
    data = {}
    data["Paquetes de (Unidades)"] = _find_number(text, r"Paquetes\s+de\s*\(Unidades\)")
    data["Bultos de (paquetes)"] = _find_number(text, r"Bultos\s+de\s*\(paquetes\)")

    obs_lines = []
    obs_match = re.search(r"Observaciones\s*(.+)", text, re.I | re.DOTALL)
    if obs_match:
        for line in obs_match.group(1).strip().split("\n"):
            cleaned = line.strip()
            if cleaned:
                obs_lines.append(cleaned)

    data["Observaciones"] = obs_lines
    return data


def _extract_section_observations(text: str) -> str | None:
    obs_match = re.search(r"Observaciones\s*(.+?)$", text, re.I | re.DOTALL)
    if not obs_match:
        return None

    raw = obs_match.group(1).strip()
    lines = [l.strip() for l in raw.split("\n") if l.strip()]

    stop = re.compile(
        r"^(Fuelles|Impreso\s+Tratado|Detalle\s+de\s+Impresi[oó]n|"
        r"[ÁA]rea\s+Pantone|Rodillo|Repeticiones|Cara\s+Impresi[oó]n)",
        re.I,
    )

    result = []
    for line in lines:
        if stop.match(line):
            break
        result.append(line)

    return _clean(" ".join(result)) if result else None


# ---------------------------------------------------------------------------
# Constante
# ---------------------------------------------------------------------------

def _extract_constant(composiciones: list, reference: str | None) -> str | None:
    for comp in composiciones:
        c = comp.get("Constante")
        if c:
            return c.upper()

    if reference:
        match = re.search(r"\b(MAHIZ|BAJA|ALTA|PP)\b", reference, re.I)
        if match:
            return match.group(1).upper()
    return None


# ---------------------------------------------------------------------------
# Extractor Principal
# ---------------------------------------------------------------------------

def extract_ot(raw_text: str) -> dict:
    sections = split_sections(raw_text)

    header_data = extract_header(sections.get("header", ""))
    general_data = extract_general_info(sections.get("general", ""))
    composiciones = extract_composiciones(sections.get("composiciones", ""))
    extrusion_data = extract_extrusion(sections.get("extrusion", ""))
    fuelles_data = extract_fuelles(sections.get("fuelles", ""))
    impresion_data = extract_impresion(sections.get("impresion", ""))
    sellado_data = extract_sellado(sections.get("sellado", ""))
    troquelado_data = extract_troquelado(sections.get("troquelado", ""))
    presentacion_data = extract_presentacion(sections.get("presentacion", ""))

    data = {}

    data["Fecha de Entrega"] = header_data.get("Fecha de Entrega")
    data["Referencia"] = header_data.get("Referencia")
    data["Orden de Compra(OC)"] = header_data.get("Orden de Compra(OC)")

    data["Orden de Trabajo"] = general_data.get("Orden de Trabajo")
    data["Cliente"] = general_data.get("Cliente")
    data["Cant. Planificada"] = general_data.get("Cant. Planificada")
    data["Procesos"] = general_data.get("Procesos")

    data["Composiciones"] = composiciones

    data["Peso Bolsa (gr)"] = extrusion_data.get("Peso Bolsa (gr)")
    data["Formato Bolsa"] = extrusion_data.get("Formato Bolsa")
    data["Caras"] = extrusion_data.get("Caras")
    data["Calibre Extrusión"] = extrusion_data.get("Calibre Extrusión")
    data["Ancho Extrusión (cm)"] = extrusion_data.get("Ancho Extrusión (cm)")
    data["Largo Extrusión (cm)"] = extrusion_data.get("Largo Extrusión (cm)")
    data["Metros"] = extrusion_data.get("Metros")
    data["Kilos"] = extrusion_data.get("Kilos")

    data["Fuelles"] = fuelles_data

    data["Impresión por Cara"] = impresion_data.get("Impresión por Cara", [])

    data["Largo Sellado (cm)"] = sellado_data.get("Largo Sellado (cm)")
    data["Tipo Sellado"] = sellado_data.get("Tipo Sellado")
    data["Calibre Sellado"] = sellado_data.get("Calibre Sellado")

    data["Tipo Troquelado"] = troquelado_data.get("Tipo Troquelado")

    data["Paquetes de (Unidades)"] = presentacion_data.get("Paquetes de (Unidades)")
    data["Bultos de (paquetes)"] = presentacion_data.get("Bultos de (paquetes)")

    data["Observaciones"] = presentacion_data.get("Observaciones", [])

    data["Constante"] = _extract_constant(composiciones, data.get("Referencia"))

    ancho, largo, medida = extract_measure(data.get("Referencia"))
    data["Ancho General (cm)"] = ancho
    data["Largo General (cm)"] = largo
    data["Medida"] = medida

    data["Validación Ancho"] = validate_measure(ancho, data.get("Ancho Extrusión (cm)"))

    return data
