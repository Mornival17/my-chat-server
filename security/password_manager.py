# security/password_manager.py
import hashlib
import secrets
import time
import random
from datetime import datetime

class PasswordManager:
    def __init__(self):
        self.password_storage = {}
        self.cleanup_counter = 0
    
    def create_password_hash(self, password, salt=None):
        """Хешируем пароль с использованием PBKDF2"""
        salt = salt or secrets.token_bytes(32)
        hash_obj = hashlib.pbkdf2_hmac(
            'sha256', 
            password.encode('utf-8'), 
            salt, 
            100000,  # 100,000 итераций
            dklen=64  # Длина ключа 64 байта
        )
        return {
            'salt': salt.hex(),
            'hash': hash_obj.hex(),
            'created_at': time.time(),
            'attempts': 0,
            'last_attempt': None
        }
    
    def verify_password(self, password, stored_data):
        """Проверяем пароль с защитой от timing attacks"""
        try:
            salt = bytes.fromhex(stored_data['salt'])
            test_hash = hashlib.pbkdf2_hmac(
                'sha256', 
                password.encode('utf-8'), 
                salt, 
                100000,
                dklen=64
            )
            
            # Используем compare_digest для защиты от timing attacks
            return secrets.compare_digest(test_hash.hex(), stored_data['hash'])
        except (KeyError, ValueError, TypeError):
            return False
    
    def store_room_password(self, room_id, password):
        """Сохраняем хеш пароля комнаты"""
        if password and len(password) > 0:
            self.password_storage[room_id] = self.create_password_hash(password)
            print(f"🔐 Password stored for room {room_id}")
        elif room_id in self.password_storage:
            del self.password_storage[room_id]
            print(f"🔓 Password removed for room {room_id}")
    
    def verify_room_password(self, room_id, password):
        """Проверяем пароль комнаты с защитой от брутфорса"""
        # Если пароль не установлен - доступ открыт
        if room_id not in self.password_storage:
            return True
        
        stored_data = self.password_storage[room_id]
        current_time = time.time()
        
        # Проверяем количество попыток
        if stored_data['attempts'] >= 10:
            # Если прошло больше 15 минут с последней попытки - сбрасываем счетчик
            if stored_data['last_attempt'] and (current_time - stored_data['last_attempt'] > 900):
                stored_data['attempts'] = 0
                stored_data['last_attempt'] = None
            else:
                print(f"🚫 Too many password attempts for room {room_id}")
                return False
        
        # Проверяем пароль
        is_valid = self.verify_password(password, stored_data)
        
        # Обновляем счетчик попыток
        stored_data['attempts'] += 1
        stored_data['last_attempt'] = current_time
        
        if is_valid:
            # Сбрасываем счетчик при успешной проверке
            stored_data['attempts'] = 0
            stored_data['last_attempt'] = None
            print(f"✅ Password verified for room {room_id}")
        else:
            print(f"❌ Password failed for room {room_id} (attempt {stored_data['attempts']})")
        
        # Периодическая очистка старых паролей
        self.cleanup_counter += 1
        if self.cleanup_counter >= 50:
            self.cleanup_old_passwords()
            self.cleanup_counter = 0
        
        return is_valid
    
    def get_password_strength(self, password):
        """Оцениваем сложность пароля"""
        if len(password) < 6:
            return "very_weak"
        
        score = 0
        if len(password) >= 8:
            score += 1
        if any(c.islower() for c in password):
            score += 1
        if any(c.isupper() for c in password):
            score += 1
        if any(c.isdigit() for c in password):
            score += 1
        if any(not c.isalnum() for c in password):
            score += 1
        
        strength_levels = ["very_weak", "weak", "medium", "strong", "very_strong"]
        return strength_levels[min(score, 4)]
    
    def cleanup_old_passwords(self, max_age_hours=24):
        """Очистка старых паролей"""
        current_time = time.time()
        rooms_to_remove = []
        
        for room_id, data in self.password_storage.items():
            if current_time - data['created_at'] > max_age_hours * 3600:
                rooms_to_remove.append(room_id)
        
        for room_id in rooms_to_remove:
            del self.password_storage[room_id]
        
        if rooms_to_remove:
            print(f"🧹 Cleaned up {len(rooms_to_remove)} old passwords")
        
        return len(rooms_to_remove)

# Глобальный экземпляр менеджера паролей
password_manager = PasswordManager()