import secrets
import uuid
from datetime import datetime

def generate_room_id():
    """Генерация уникального ID комнаты"""
    return secrets.token_urlsafe(8)

def get_current_time():
    """Получение текущего времени в ISO формате"""
    return datetime.now().isoformat()

def generate_media_id():
    """Генерация уникального ID для медиа"""
    return str(uuid.uuid4())
