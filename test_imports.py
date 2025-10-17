#!/usr/bin/env python3

try:
    from server import app
    from models.data_store import rooms, user_rooms
    from security.password_manager import password_manager
    from security.advanced_bruteforce import advanced_bruteforce_protection
    from security.encryption import verify_encryption_key
    from security.bruteforce_protection import check_bruteforce, get_client_ip
    from utils.helpers import generate_room_id, get_current_time
    
    print("✅ Все импорты работают корректно!")
    print("🚀 Сервер готов к запуску")
    
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("Проверьте структуру файлов и импорты")
