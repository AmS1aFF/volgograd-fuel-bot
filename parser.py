import re

# Известные бренды заправок в Волгограде
BRANDS = [
    "Лукойл", "ЛУКОЙЛ",
    "Газпром", "Газпромнефть", "Газпром нефть",
    "Роснефть", "РОСНЕФТЬ",
    "Татнефть", "ТАТНЕФТЬ",
    "Shell", "Шелл",
    "Башнефть", "БашНефть",
    "Сургутнефтегаз",
    "Нефтьмагистраль",
    "ТНК", "ТНК-BP",
    "Plus", "Плюс",
]

# Типы топлива
FUEL_KEYWORDS = {
    "АИ-92": ["92", "аи92", "аи-92", "92й", "92-й", "92ого"],
    "АИ-95": ["95", "аи95", "аи-95", "95й", "95-й", "95ого"],
    "АИ-98": ["98", "аи98", "аи-98", "98й", "98-й", "98ого"],
    "АИ-100": ["100", "аи100", "аи-100", "100й", "100-й"],
    "ДТ": ["дт", "дизель", "диз", "солярка", "соляра"],
    "Газ": ["газ", "пропан", "метан", "пбу", "снгу"],
}

NEGATIVE_WORDS = [
    "нет", "нету", "отсутствует", "закончился", "закончилось",
    "пусто", "пустой", "пустая", "ноль", "не льют",
]


def detect_fuel_type(text):
    """Определяет тип топлива в сообщении"""
    text_lower = text.lower()
    for fuel_type, keywords in FUEL_KEYWORDS.items():
        for kw in keywords:
            pattern = rf'\b{re.escape(kw)}\b|{re.escape(kw)}'
            if re.search(pattern, text_lower):
                return fuel_type
    return None


def detect_station(text):
    """Определяет бренд заправки"""
    text_lower = text.lower()
    for brand in BRANDS:
        if brand.lower() in text_lower:
            return brand
    return None


def detect_address(text):
    """Ищет адрес в тексте (ул., пр., и т.д.)"""
    patterns = [
        r'((?:ул|улиц[аы])\.?\s+[А-Яа-яЁё\s]+?)(?:,|\.|$|\s+\d)',
        r'((?:пр|проспект|пр-т)\.?\s+[А-Яа-яЁё\s]+?)(?:,|\.|$|\s+\d)',
        r'((?:ш|шоссе)\.?\s+[А-Яа-яЁё\s]+?)(?:,|\.|$|\s+\d)',
        r'((?:пер|переулок)\.?\s+[А-Яа-яЁё\s]+?)(?:,|\.|$|\s+\d)',
        r'(на\s+[А-Яа-яЁё]+)',
        r'(по\s+[А-Яа-яЁё]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def detect_price(text):
    """Ищет цену в тексте"""
    patterns = [
        r'(\d+[.,]\d{1,2})\s*₽',
        r'(\d+[.,]\d{1,2})\s*руб',
        r'(\d{2,3})\s*₽',
        r'(\d{2,3})\s*руб',
        r'(\d{2,3})\s*р\.',
        r'(?:по|за|цена)\s*(\d+[.,]?\d*)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            try:
                price_str = match.group(1).replace(',', '.')
                price = float(price_str)
                if 30 <= price <= 200:
                    return price
            except (ValueError, IndexError):
                continue
    return None


def detect_availability(text):
    """Определяет наличие топлива"""
    text_lower = text.lower()
    for word in NEGATIVE_WORDS:
        if re.search(rf'\b{word}\b', text_lower):
            return 0
    return 1


def parse_fuel_message(text):
    """Главная функция парсинга"""
    if not text or len(text) < 5:
        return None

    fuel_type = detect_fuel_type(text)
    if not fuel_type:
        return None

    return {
        "station": detect_station(text) or "Неизвестно",
        "address": detect_address(text),
        "fuel_type": fuel_type,
        "price": detect_price(text),
        "available": detect_availability(text),
    }


if __name__ == "__main__":
    tests = [
        "Лукойл на ул. Мира есть 95-й, 56.80",
        "Газпром по пр-ту Ленина нет дизеля",
        "Роснефть АИ-92 55₽ в наличии",
        "Случайный текст про погоду",
        "Татнефть 95 есть по 57 рублей",
        "Shell дизель закончился на ул. Рабоче-Крестьянской",
    ]
    for t in tests:
        result = parse_fuel_message(t)
        print(f"📝 '{t}'")
        print(f"   → {result}\n")
