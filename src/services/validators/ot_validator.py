from src.services.validators.tolerance import within_tolerance

from src.services.business.constants import constants_values

from src.services.calculators.calculator_ot import (
    calculator_bag_weight,
    calculator_total_weight,
)

from src.utils.string_parser import parse_number


def ot_validation(data, extra_percent=3):

    ancho_val = data.get("Ancho General (cm)") or data.get("Ancho Extrusión (cm)")
    ancho = parse_number(ancho_val)

    largo_val = data.get("Largo General (cm)") or data.get("Largo Extrusión (cm)")
    largo = parse_number(largo_val)

    calibre = parse_number(
        data.get("Calibre Extrusión")
    )


    cantidad = parse_number(
        data["Cant. Planificada"]
    )

    peso_bolsa_ot = parse_number(
        data["Peso Bolsa (gr)"]
    )

    kilos_ot = parse_number(
        data["Kilos"]
    )

    constant_value = constants_values.get(
        data["Constante"]
    )

    # -----------------------------------
    # Peso bolsa
    # -----------------------------------

    calculated_bag_weight = (
        calculator_bag_weight(
            ancho,
            largo,
            calibre,
            constant_value,
        )
    )

    # -----------------------------------
    # Kilos
    # -----------------------------------

    calculated_total_weight = (
        calculator_total_weight(
            calculated_bag_weight,
            cantidad,
            extra_percent
        )
    )

    # -----------------------------------
    # Validaciones
    # -----------------------------------

    bag_weight_valid = within_tolerance(
        calculated_bag_weight,
        peso_bolsa_ot,
        3
    )

    kilos_valid = within_tolerance(
        calculated_total_weight,
        kilos_ot,
        3
    )

    return {

        "valid": (
            bag_weight_valid and
            kilos_valid
        ),

        "extra_percent": extra_percent,

        "Peso Bolsa": {

            "ot": peso_bolsa_ot,

            "calculated": round(
                calculated_bag_weight,
                2
            ),

            "valid": bag_weight_valid
        },

        "Kilos": {

            "ot": kilos_ot,

            "calculated": round(
                calculated_total_weight,
                2
            ),

            "valid": kilos_valid
        }
    }