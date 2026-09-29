def calculate_total(items):
    total = 0

    for item in items:
        quantity = item.get("quantity", 1)
        total += item["price"] * quantity

    return total
