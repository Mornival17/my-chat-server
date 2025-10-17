# config.py
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
    
    # Гибридное шифрование
    SESSION_KEY_LENGTH = 32  # 256-bit
    AES_IV_LENGTH = 12       # 96-bit для GCM
    AES_TAG_LENGTH = 16      # 128-bit tag
    
    # Защита от timing attacks
    MIN_PASSWORD_LENGTH = 6
    MAX_PASSWORD_LENGTH = 128