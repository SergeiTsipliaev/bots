#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Настройка логирования для бота анализа CATIUSDT.
"""

import os
import logging
from config import CONFIG

def setup_logger():
    """Настройка логирования"""
    
    # Создаем директорию логов, если её нет
    log_dir = os.path.dirname(CONFIG["log_file"])
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Настраиваем логирование
    logging.basicConfig(
        level=getattr(logging, CONFIG["log_level"]),
        format=CONFIG["log_format"],
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(CONFIG["log_file"])
        ]
    )
    
    return logging.getLogger("CATI_Bot")

# Глобальный логгер для использования во всех модулях
logger = setup_logger()