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
        'data_limit_gb': 0,  # 0 = безлимитный трафик
        'description': '30 дней подписки, безлимитный трафик'
    }
}


def get_tariff_by_id(tariff_id):
    """Получить тариф по ID"""
    return TARIFFS.get(tariff_id)


def get_all_tariffs():
    """Получить все тарифы"""
    return list(TARIFFS.values())
