"""
Конфигурация тарифов VPN
Централизованное хранилище информации о тарифах
"""

TARIFFS = {
    'month': {
        'id': 'month',
        'name': '1 месяц',
        'price': 1,
        'currency': 'RUB',
        'days': 30,
        'data_limit_gb': 10,
        'description': '30 дней подписки'
    },
    'quarter': {
        'id': 'quarter',
        'name': '3 месяца',
        'price': 3,
        'currency': 'RUB',
        'days': 90,
        'data_limit_gb': 50,
        'description': '90 дней подписки',
        'popular': True  # Пометка "Популярный"
    },
    'year': {
        'id': 'year',
        'name': '12 месяцев',
        'price': 5,
        'currency': 'RUB',
        'days': 365,
        'data_limit_gb': 100,
        'description': '365 дней подписки',
        'popular': False
    }
}


def get_data_limit_bytes(tariff_id):
    """Получить лимит трафика в байтах для тарифа"""
    tariff = get_tariff_by_id(tariff_id)
    if tariff:
        return tariff['data_limit_gb'] * 1024**3
    return 10 * 1024**3  # Default 10GB


def get_tariff_by_id(tariff_id):
    """Получить тариф по ID"""
    return TARIFFS.get(tariff_id)


def get_tariff_by_price(price):
    """Получить тариф по цене"""
    for tariff in TARIFFS.values():
        if tariff['price'] == price:
            return tariff
    return None


def get_all_tariffs():
    """Получить все тарифы"""
    return list(TARIFFS.values())
