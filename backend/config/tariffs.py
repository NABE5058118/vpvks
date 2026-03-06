"""
Конфигурация тарифов VPN
Централизованное хранилище информации о тарифах
"""

TARIFFS = {
    'month': {
        'id': 'month',
        'name': '1 месяц',
        'price': 110,
        'currency': 'RUB',
        'days': 30,
        'data_limit_gb': 0,  # 0 = безлимитный трафик
        'description': '30 дней подписки, безлимитный трафик'
    },
    'quarter': {
        'id': 'quarter',
        'name': '3 месяца',
        'price': 290,
        'currency': 'RUB',
        'days': 90,
        'data_limit_gb': 0,
        'description': '90 дней подписки, безлимитный трафик'
    },
    'year': {
        'id': 'year',
        'name': '12 месяцев',
        'price': 500,
        'currency': 'RUB',
        'days': 365,
        'data_limit_gb': 0,
        'description': '365 дней подписки, безлимитный трафик'
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
    if tariff and tariff['data_limit_gb'] > 0:
        return tariff['data_limit_gb'] * 1024**3
    return 0  # 0 = безлимитно
