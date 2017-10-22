from ..motors import _calculate_value_in_range


def test_calculate_value_in_range_max():
    result = _calculate_value_in_range(
        min_val=1525,
        max_val=1900,
        percentage=1,
    )
    assert result == 1900


def test_calculate_value_in_range_min():
    result = _calculate_value_in_range(
        min_val=1525,
        max_val=1900,
        percentage=0,
    )
    assert result == 1525


def test_calculate_value_in_range_mid():
    result = _calculate_value_in_range(
        min_val=1525,
        max_val=1900,
        percentage=0.5,
    )
    assert result == 1525 + (1900 - 1525) // 2


def test_calculate_value_in_range_neg_max():
    result = _calculate_value_in_range(
        min_val=1475,
        max_val=1100,
        percentage=1,
    )
    assert result == 1100


def test_calculate_value_in_range_neg_min():
    result = _calculate_value_in_range(
        min_val=1475,
        max_val=1100,
        percentage=0,
    )
    assert result == 1475


def test_calculate_value_in_range_neg_mid():
    result = _calculate_value_in_range(
        min_val=1475,
        max_val=1100,
        percentage=0.5,
    )
    assert result == 1475 - (1475 - 1100) // 2


