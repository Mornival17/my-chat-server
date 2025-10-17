# security/advanced_bruteforce.py
import time
import random
from config import Config

class AdvancedBruteForceProtection:
    def __init__(self):
        self.bruteforce_attempts = {}
        self.suspicious_ips = {}
        self.MAX_ATTEMPTS_PER_HOUR = 5
        self.BLOCK_TIME = 3600  # 1 час блокировки
        self.SUSPICIOUS_THRESHOLD = 3
        self.cleanup_counter = 0
    
    def check_bruteforce(self, ip, room_id=None, username=None):
        """Улучшенная защита с учетом комнат и пользователей"""
        current_time = time.time()
        
        # Создаем ключ для отслеживания
        if room_id and username:
            key = f"{ip}:{room_id}:{username}"
        elif room_id:
            key = f"{ip}:{room_id}"
        else:
            key = ip
        
        # Очистка старых попыток
        if key in self.bruteforce_attempts:
            self.bruteforce_attempts[key] = [
                t for t in self.bruteforce_attempts[key] 
                if current_time - t < self.BLOCK_TIME
            ]
        
        # Проверка лимита
        if key in self.bruteforce_attempts and len(self.bruteforce_attempts[key]) >= self.MAX_ATTEMPTS_PER_HOUR:
            # Помечаем IP как подозрительный
            if ip not in self.suspicious_ips:
                self.suspicious_ips[ip] = 0
            self.suspicious_ips[ip] += 1
            return False
        
        # Добавляем попытку
        if key not in self.bruteforce_attempts:
            self.bruteforce_attempts[key] = []
        self.bruteforce_attempts[key].append(current_time)
        
        # Добавляем небольшую задержку для подозрительных IP
        if ip in self.suspicious_ips and self.suspicious_ips[ip] >= self.SUSPICIOUS_THRESHOLD:
            time.sleep(0.5)  # 500ms задержка
        
        # Автоочистка старых записей
        self.cleanup_counter += 1
        if self.cleanup_counter >= 100:
            self.cleanup_old_attempts()
            self.cleanup_counter = 0
        
        return True
    
    def cleanup_old_attempts(self):
        """Очистка старых записей о попытках"""
        current_time = time.time()
        keys_to_remove = []
        ips_to_remove = []
        
        # Очищаем попытки брутфорса
        for key, attempts in self.bruteforce_attempts.items():
            if not attempts or (current_time - max(attempts) > self.BLOCK_TIME * 2):
                keys_to_remove.append(key)
        
        # Очищаем подозрительные IP
        for ip, count in self.suspicious_ips.items():
            if count == 0:
                ips_to_remove.append(ip)
        
        for key in keys_to_remove:
            del self.bruteforce_attempts[key]
        
        for ip in ips_to_remove:
            del self.suspicious_ips[ip]
        
        print(f"🧹 Cleaned {len(keys_to_remove)} brute-force records and {len(ips_to_remove)} suspicious IPs")
    
    def get_attempts_info(self, ip, room_id=None, username=None):
        """Получение информации о попытках"""
        if room_id and username:
            key = f"{ip}:{room_id}:{username}"
        elif room_id:
            key = f"{ip}:{room_id}"
        else:
            key = ip
            
        if key in self.bruteforce_attempts:
            attempts = self.bruteforce_attempts[key]
            return {
                'attempts_count': len(attempts),
                'last_attempt': max(attempts) if attempts else None,
                'blocked': len(attempts) >= self.MAX_ATTEMPTS_PER_HOUR,
                'suspicious_level': self.suspicious_ips.get(ip, 0)
            }
        return {
            'attempts_count': 0, 
            'blocked': False,
            'suspicious_level': self.suspicious_ips.get(ip, 0)
        }
    
    def report_successful_auth(self, ip, room_id=None, username=None):
        """Отмечаем успешную аутентификацию для сброса счетчиков"""
        if room_id and username:
            key = f"{ip}:{room_id}:{username}"
        elif room_id:
            key = f"{ip}:{room_id}"
        else:
            key = ip
            
        # Сбрасываем счетчики для этого ключа
        if key in self.bruteforce_attempts:
            del self.bruteforce_attempts[key]
        
        # Уменьшаем уровень подозрительности
        if ip in self.suspicious_ips and self.suspicious_ips[ip] > 0:
            self.suspicious_ips[ip] -= 1
    
    def get_security_report(self):
        """Получение отчета о безопасности"""
        total_attempts = sum(len(attempts) for attempts in self.bruteforce_attempts.values())
        blocked_ips = len([attempts for attempts in self.bruteforce_attempts.values() 
                          if len(attempts) >= self.MAX_ATTEMPTS_PER_HOUR])
        
        return {
            'total_tracked_entities': len(self.bruteforce_attempts),
            'total_attempts': total_attempts,
            'blocked_entities': blocked_ips,
            'suspicious_ips': len([ip for ip, count in self.suspicious_ips.items() if count > 0]),
            'protection_level': 'high'
        }

# Глобальный экземпляр защиты
advanced_bruteforce_protection = AdvancedBruteForceProtection()