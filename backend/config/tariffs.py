"""
Конфигурация тарифов VPN
Централизованное хранилище информации о тарифах
"""

TARIFFS = {
    'month': {
        'id': 'month',
        'name': '1 месяц',
        'price': 99,
        'currency': 'RUB',
        'days': 30,
        'data_limit_gb': 10,
        'description': '30 дней подписки'
    },
    'quarter': {
        'id': 'quarter',
        'name': '3 месяца',
        'price': 299,
        'currency': 'RUB',
        'days': 90,
        'data_limit_gb': 50,
        'description': '90 дней подписки',
        'popular': True  # Пометка "Популярный"
    },
    'halfyear': {
        'id': 'halfyear',
        'name': '6 месяцев',
        'price': 599,
        'currency': 'RUB',
        'days': 180,
        'data_limit_gb': 100,
        'description': '180 дней подписки'
    }
}


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


def get_data_limit_bytes(tariff_id):
    """Получить лимит трафика в байтах для тарифа"""
    tariff = get_tariff_by_id(tariff_id)
    if tariff:
        return tariff['data_limit_gb'] * 1024**3
    return 10 * 1024**3  # Default 10GB
