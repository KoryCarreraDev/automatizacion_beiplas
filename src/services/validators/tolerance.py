def within_tolerance(expected, actually, tolerance_percent=3):

    difference = abs(expected - actually)

    max_difference = expected * (tolerance_percent / 100)

    return difference <= max_difference