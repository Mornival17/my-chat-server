import time
from config import Config

bruteforce_attempts = {}

def check_bruteforce(ip):
    """🔐 Проверка защиты от брутфорса"""
    current_time = time.time()
    
    # Очищаем старые записи
    if ip in bruteforce_attempts:
        bruteforce_attempts[ip] = [
            attempt_time for attempt_time in bruteforce_attempts[ip]
            if current_time - attempt_time < Config.BLOCK_TIME
        ]
    
    # Проверяем лимит
    if ip in bruteforce_attempts and len(bruteforce_attempts[ip]) >= Config.MAX_ATTEMPTS_PER_IP:
        return False  # Блокировка
    
    # Добавляем текущую попытку
    if ip not in bruteforce_attempts:
        bruteforce_attempts[ip] = []
    bruteforce_attempts[ip].append(current_time)
    
    return True  # Разрешено

def get_client_ip(request):
    """Получение IP клиента"""
    return request.remote_addr
