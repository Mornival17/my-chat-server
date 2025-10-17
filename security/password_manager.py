import hashlib
import secrets
import time
import random

class PasswordManager:
    def __init__(self):
        self.password_storage = {}
    
    def create_password_hash(self, password, salt=None):
        """Хешируем пароль, но храним только в RAM"""
        salt = salt or secrets.token_bytes(32)
        hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        return {
            'salt': salt.hex(),
            'hash': hash_obj.hex(),
            'created_at': time.time()
        }
    
    def verify_password(self, password, stored_data):
        """Проверяем пароль без постоянного хранения"""
        try:
            salt = bytes.fromhex(stored_data['salt'])
            test_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
            return secrets.compare_digest(test_hash.hex(), stored_data['hash'])
        except (KeyError, ValueError):
            return False
    
    def store_room_password(self, room_id, password):
        """Сохраняем хеш пароля комнаты"""
        if password:  # Только если пароль установлен
            self.password_storage[room_id] = self.create_password_hash(password)
        elif room_id in self.password_storage:
            del self.password_storage[room_id]  # Удаляем если пароль убран
    
    def verify_room_password(self, room_id, password):
        """Проверяем пароль комнаты"""
        if room_id not in self.password_storage:
            return True  # Если пароль не установлен - доступ открыт
        
        return self.verify_password(password, self.password_storage[room_id])
    
    def cleanup_old_passwords(self, max_age_hours=24):
        """Очистка старых паролей"""
        current_time = time.time()
        rooms_to_remove = []
        
        for room_id, data in self.password_storage.items():
            if current_time - data['created_at'] > max_age_hours * 3600:
                rooms_to_remove.append(room_id)
        
        for room_id in rooms_to_remove:
            del self.password_storage[room_id]
        
        return len(rooms_to_remove)

# Глобальный экземпляр менеджера паролей
password_manager = PasswordManager()
