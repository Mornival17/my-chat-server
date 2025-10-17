import time
import random
from config import Config

class AdvancedBruteForceProtection:
    def __init__(self):
        self.bruteforce_attempts = {}
        self.MAX_ATTEMPTS_PER_HOUR = 5  # Уменьшаем лимит
        self.BLOCK_TIME = 3600  # 1 час блокировки
        self.cleanup_counter = 0
    
    def check_bruteforce(self, ip, room_id=None):
        """Улучшенная защита с учетом комнат"""
        current_time = time.time()
        key = f"{ip}:{room_id}" if room_id else ip
        
        # Очистка старых попыток
        if key in self.bruteforce_attempts:
            self.bruteforce_attempts[key] = [
                t for t in self.bruteforce_attempts[key] 
                if current_time - t < self.BLOCK_TIME
            ]
        
        # Проверка лимита
        if key in self.bruteforce_attempts and len(self.bruteforce_attempts[key]) >= self.MAX_ATTEMPTS_PER_HOUR:
            return False
        
        # Добавляем попытку
        if key not in self.bruteforce_attempts:
            self.bruteforce_attempts[key] = []
        self.bruteforce_attempts[key].append(current_time)
        
        # Автоочистка старых записей (каждый 100 вызовов)
        self.cleanup_counter += 1
        if self.cleanup_counter >= 100:
            self.cleanup_old_attempts()
            self.cleanup_counter = 0
        
        return True
    
    def cleanup_old_attempts(self):
        """Очистка старых записей о попытках"""
        current_time = time.time()
        keys_to_remove = []
        
        for key, attempts in self.bruteforce_attempts.items():
            # Удаляем пустые списки или очень старые
            if not attempts or (current_time - max(attempts) > self.BLOCK_TIME * 2):
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.bruteforce_attempts[key]
    
    def get_attempts_info(self, ip, room_id=None):
        """Получение информации о попытках"""
        key = f"{ip}:{room_id}" if room_id else ip
        if key in self.bruteforce_attempts:
            return {
                'attempts_count': len(self.bruteforce_attempts[key]),
                'last_attempt': max(self.bruteforce_attempts[key]),
                'blocked': len(self.bruteforce_attempts[key]) >= self.MAX_ATTEMPTS_PER_HOUR
            }
        return {'attempts_count': 0, 'blocked': False}

# Глобальный экземпляр защиты
advanced_bruteforce_protection = AdvancedBruteForceProtection()
