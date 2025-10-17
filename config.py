class Config:
    # Защита от брутфорса
    MAX_ATTEMPTS_PER_IP = 10
    BLOCK_TIME = 300  # 5 минут
    
    # Улучшенная защита
    MAX_ATTEMPTS_PER_HOUR = 5
    ADVANCED_BLOCK_TIME = 3600  # 1 час
    
    # Лимиты сообщений
    MESSAGE_LIMIT = 100
    
    # Очистка комнат
    ROOM_CLEANUP_HOURS = 24
    
    # Верификация ключей
    MAX_KEY_VERIFICATION_ATTEMPTS = 3
    MAX_KEY_VERIFICATION_GLOBAL_ATTEMPTS = 5
    
    # Безопасность паролей
    PASSWORD_HASH_ITERATIONS = 100000
    PASSWORD_SALT_LENGTH = 32