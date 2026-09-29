from src.calculator import calculate_total


def test_calculate_total():
    items = [
        {"price": 100, "quantity": 2},
        {"price": 50, "quantity": 3},
    ]

    assert calculate_total(items) == 350
