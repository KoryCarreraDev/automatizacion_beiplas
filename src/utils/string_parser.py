def parse_number(value):

    if value is None:
        return 0

    value = str(value)

    value = value.replace(",", "")

    return float(value)