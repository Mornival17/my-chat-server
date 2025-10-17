class Config:
    # Защита от брутфорса
    MAX_ATTEMPTS_PER_IP = 10
    BLOCK_TIME = 300  # 5 минут
    
    # Лимиты сообщений
    MESSAGE_LIMIT = 100
    
    # Очистка комнат
    ROOM_CLEANUP_HOURS = 24
    
    # Верификация ключей
    MAX_KEY_VERIFICATION_ATTEMPTS = 3
    MAX_KEY_VERIFICATION_GLOBAL_ATTEMPTS = 5
