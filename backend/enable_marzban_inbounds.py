#!/usr/bin/env python3
"""
Auto-enable Marzban Inbounds
Запускается при создании первого пользователя
"""

import sqlite3
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('marzban-inbound-enabler')

def enable_inbounds():
    """Включение VLESS Reality и Trojan TLS через БД"""
    db_path = "/var/lib/marzban/db.sqlite3"
    
    if not os.path.exists(db_path):
        logger.error(f"Database not found: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Проверяем таблицу
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='inbounds'")
        if not cursor.fetchone():
            logger.warning("Inbounds table not found")
            conn.close()
            return False
        
        # Включаем все inbound с нужными тегами
        cursor.execute("UPDATE inbounds SET enabled = 1 WHERE tag IN ('VLESS Reality', 'Trojan TLS')")
        changes = cursor.rowcount
        
        if changes > 0:
            conn.commit()
            logger.info(f"✅ Enabled {changes} inbounds!")
        else:
            logger.info("All inbounds already enabled")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return False

if __name__ == "__main__":
    enable_inbounds()
