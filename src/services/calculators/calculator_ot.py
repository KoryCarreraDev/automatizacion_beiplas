def calculator_bag_weight(broad: int, large: int, caliber: int, constant: float) -> float:

    return broad * large * caliber * constant

def calculator_total_weight(
    bag_weight_grams,
    quantity,
    extra_percent=3
):

    total_grams = (
        bag_weight_grams *
        quantity
    )

    total_grams = total_grams * (
        1 + (extra_percent / 100)
    )

    total_kilos = total_grams / 1000

    return round(total_kilos, 2)
    