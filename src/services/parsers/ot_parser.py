import re


VALID_CONSTANTS = ["MAHIZ", "BAJA", "ALTA", "PP"]


def clean_value(value: str):

    if not value:
        return None

    return value.strip()


def extract_constant(text: str):

    composition_match = re.search(
        r"BPREF\d+\s+(MAHIZ|BAJA|ALTA|PP)",
        text,
        re.IGNORECASE
    )

    if composition_match:
        return composition_match.group(1).upper()

    reference_match = re.search(
        r"Referencia:\s*(.+)",
        text,
        re.IGNORECASE
    )

    if reference_match:

        reference_text = reference_match.group(1)

        constant_match = re.search(
            r"(MAHIZ|BAJA|ALTA|PP)",
            reference_text,
            re.IGNORECASE
        )

        if constant_match:
            return constant_match.group(1).upper()

    return None


def extract_measure(reference: str):

    if not reference:
        return None

    match = re.search(
        r"(\d+)\s*[Xx]\s*(\d+)",
        reference
    )

    if not match:
        return None

    return f"{match.group(1)}*{match.group(2)}"


def extract_compositions(text: str):

    compositions = []

    pattern = re.findall(
        r"(BPREF\d+)\s+"
        r"(MAHIZ|BAJA|ALTA|PP)\s+"
        r"([\d.,]+)\s*%\s+"
        r"(.+?)\s+"
        r"([\d.,]+)\s*%",
        text,
        re.IGNORECASE
    )

    for item in pattern:

        compositions.append({
            "Referencia Materia Prima": item[0],
            "Constante": item[1].upper(),
            "% Materia Prima": item[2],
            "Materia Secundaria": item[3],
            "% Secundario": item[4]
        })

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
        "Ancho General (cm)": r"Ancho General \(cm\)\s*([\d.,]+)",
        "Largo General (cm)": r"Largo General \(cm\)\s*([\d.,]+)",
        "Tipo Sellado": r"Tipo Sellado\s*(.+)",
        "Paquetes de (Unidades)": r"Paquetes de \(Unidades\):\s*([\d.,]+)",
        "Bultos de (paquetes)": r"Bultos de \(paquetes\):\s*([\d.,]+)",
    }

    for field_name, pattern in fields.items():

        match = re.search(
            pattern,
            text,
            re.IGNORECASE | re.DOTALL
        )

        data[field_name] = clean_value(
            match.group(1)
        ) if match else None

    data["Constante"] = extract_constant(text)

    data["Medida"] = extract_measure(
        data.get("Referencia")
    )

    data["Composiciones"] = extract_compositions(text)

    observations = re.findall(
        r"Observaciones\s*(.+?)(?=\n[A-ZÁÉÍÓÚ][a-z]|$)",
        text,
        re.DOTALL
    )

    data["Observaciones"] = [
        obs.strip()
        for obs in observations
        if obs.strip()
    ]

    return data