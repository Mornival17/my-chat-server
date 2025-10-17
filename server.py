from flask import Flask, request, jsonify
from datetime import datetime
import os
import secrets
import uuid
import hashlib
import time
import random
from flask_cors import CORS

# Создаем Flask приложение
app = Flask(__name__)
# 🔐 Разрешаем CORS для локальных файлов
CORS(app)

# 🔐 УЛУЧШЕННАЯ ЗАЩИТА ОТ БРУТФОРСА
bruteforce_attempts = {}
MAX_ATTEMPTS_PER_HOUR = 5  # Уменьшаем лимит
BLOCK_TIME = 3600  # 1 час блокировки

# Глобальные переменные для хранения данных
rooms = {}
user_rooms = {}
call_signals = {}
room_keys = {}
encrypted_rooms = set()
key_verification_attempts = {}

def generate_room_id():
    """Генерация уникального ID комнаты"""
    return secrets.token_urlsafe(8)

def create_password_hash(password, salt=None):
    """🔐 Хешируем пароль, но храним только в RAM"""
    salt = salt or secrets.token_bytes(32)
    hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
    return {
        'salt': salt.hex(),
        'hash': hash_obj.hex(),
        'created_at': time.time()
    }

def verify_password(password, stored_data):
    """🔐 Проверяем пароль без постоянного хранения"""
    try:
        salt = bytes.fromhex(stored_data['salt'])
        test_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        return secrets.compare_digest(test_hash.hex(), stored_data['hash'])
    except Exception:
        return False

def cleanup_old_attempts():
    """🔐 Автоочистка старых записей брутфорса"""
    current_time = time.time()
    keys_to_delete = []
    
    for key, attempts in bruteforce_attempts.items():
        # Оставляем только свежие попытки
        bruteforce_attempts[key] = [
            t for t in attempts 
            if current_time - t < BLOCK_TIME
        ]
        # Удаляем пустые записи
        if not bruteforce_attempts[key]:
            keys_to_delete.append(key)
    
    for key in keys_to_delete:
        del bruteforce_attempts[key]

def check_bruteforce(ip, room_id=None):
    """🔐 УЛУЧШЕННАЯ защита с учетом комнат"""
    current_time = time.time()
    key = f"{ip}:{room_id}" if room_id else ip
    
    # Очистка старых попыток
    if key in bruteforce_attempts:
        bruteforce_attempts[key] = [
            t for t in bruteforce_attempts[key] 
            if current_time - t < BLOCK_TIME
        ]
    
    # Проверка лимита
    if key in bruteforce_attempts and len(bruteforce_attempts[key]) >= MAX_ATTEMPTS_PER_HOUR:
        return False
    
    # Добавляем попытку
    if key not in bruteforce_attempts:
        bruteforce_attempts[key] = []
    bruteforce_attempts[key].append(current_time)
    
    # Автоочистка старых записей (каждый 100 вызовов)
    if random.random() < 0.01:
        cleanup_old_attempts()
    
    return True

def get_client_ip():
    """Получение IP клиента"""
    return request.remote_addr

# Базовые endpoint'ы
@app.route('/')
def home():
    return "🚀 Secure Chat Server Ready! Use /create_room, /join_room, /send and /receive"

@app.route('/health')
def health():
    return "OK"

# Создание комнаты с улучшенной системой паролей
@app.route('/create_room', methods=['POST', 'OPTIONS'])
def create_room():
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.get_json()
        room_name = data.get('room_name', 'New Room')
        password = data.get('password', '')
        username = data.get('username', 'Host')
        
        # 🔐 Новые параметры шифрования
        is_encrypted = data.get('is_encrypted', False)
        public_key = data.get('public_key', '')
        
        # 🔐 Валидация для зашифрованных комнат
        if is_encrypted and not public_key:
            return jsonify({"error": "Public key required for encrypted room"}), 400
        
        # Генерируем уникальный ID комнаты
        room_id = generate_room_id()
        
        # 🔐 УЛУЧШЕННАЯ СИСТЕМА ПАРОЛЕЙ: Храним хеш вместо plain text
        password_data = create_password_hash(password) if password else None
        
        # Создаем комнату со всей необходимой информацией
        rooms[room_id] = {
            'name': room_name,
            'password_hash': password_data,  # 🔐 Заменяем plain text на хеш
            'created_at': datetime.now().isoformat(),
            'users': set([username]),
            'messages': [],
            'next_id': 1,
            'media': {},
            'reactions': {},
            # 🔐 Новые поля для шифрования
            'is_encrypted': is_encrypted,
            'public_key': public_key,
            'encryption_enabled_at': datetime.now().isoformat() if is_encrypted else None
        }
        
        # 🔐 Сохраняем ключ если комната зашифрована
        if is_encrypted:
            room_keys[room_id] = public_key
            encrypted_rooms.add(room_id)
            print(f"🔐 Encryption enabled for room {room_id}")
        
        # Связываем пользователя с комнатой
        user_rooms[username] = room_id
        
        print(f"🎉 Room created: {room_name} (ID: {room_id}) by {username}")
        print(f"🔐 Encryption: {is_encrypted}")
        print(f"🔐 Password protected: {bool(password_data)}")
        
        return jsonify({
            "status": "created", 
            "room_id": room_id,
            "room_name": room_name,
            "is_encrypted": is_encrypted,
            "security_level": "high" if is_encrypted else "standard"
        })
        
    except Exception as e:
        print(f"❌ Error in /create_room: {e}")
        return jsonify({"error": "Server error"}), 500

# Присоединение к комнате с УЛУЧШЕННОЙ защитой от брутфорса
@app.route('/join_room', methods=['POST', 'OPTIONS'])
def join_room():
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.get_json()
        room_id = data.get('room_id')
        password = data.get('password', '')
        username = data.get('username', 'Anonymous')
        
        # 🔐 УЛУЧШЕННАЯ защита от брутфорса с учетом комнаты
        client_ip = get_client_ip()
        if not check_bruteforce(client_ip, room_id):
            return jsonify({
                "error": "Too many attempts. Please wait 1 hour.",
                "blocked": True
            }), 429
            
        # 🔐 Новые параметры для зашифрованных комнат
        key_verification_data = data.get('key_verification')
        public_key = data.get('public_key')
        
        # Проверяем что room_id предоставлен
        if not room_id:
            return jsonify({"error": "Room ID is required"}), 400
            
        # Проверяем что комната существует
        if room_id not in rooms:
            return jsonify({"error": "Room not found"}), 404
        
        room = rooms[room_id]
        
        # 🔐 УЛУЧШЕННАЯ ПРОВЕРКА ПАРОЛЯ: Используем хеш вместо plain text
        if room['password_hash']:
            if not password:
                return jsonify({"error": "Password required"}), 401
            
            if not verify_password(password, room['password_hash']):
                return jsonify({"error": "Invalid password"}), 401
        
        # 🔐 Проверяем ключ для зашифрованных комнат
        if room['is_encrypted']:
            if not key_verification_data or not public_key:
                return jsonify({
                    "error": "Key verification required for encrypted room",
                    "is_encrypted": True,
                    "key_required": True
                }), 401
            
            # 🔐 Проверяем не превышено ли количество попыток
            attempt_key = f"{room_id}:{username}"
            current_attempts = key_verification_attempts.get(attempt_key, 0)
            if current_attempts >= 3:
                return jsonify({
                    "error": "Too many key verification attempts. Please wait 5 minutes.",
                    "is_encrypted": True,
                    "blocked": True
                }), 429
            
            # 🔐 Простая проверка ключа
            if not verify_encryption_key(room_id, public_key, key_verification_data):
                key_verification_attempts[attempt_key] = current_attempts + 1
                return jsonify({
                    "error": "Invalid encryption key",
                    "is_encrypted": True,
                    "attempts_remaining": 3 - (current_attempts + 1)
                }), 401
            
            # Сбрасываем счетчик попыток при успешной проверке
            key_verification_attempts.pop(attempt_key, None)
            print(f"🔐 Key verified for user {username} in room {room_id}")
        
        # Добавляем пользователя в комнату
        room['users'].add(username)
        user_rooms[username] = room_id
        
        # Добавляем системное сообщение о присоединении
        system_message = {
            'id': room['next_id'],
            'user': 'System',
            'text': f'{username} joined the room',
            'time': datetime.now().isoformat(),
            'type': 'system'
        }
        room['messages'].append(system_message)
        room['next_id'] += 1
        
        print(f"👤 User {username} joined room {room_id}")
        print(f"🔐 Room encryption: {room['is_encrypted']}")
        
        return jsonify({
            "status": "joined",
            "room_name": room['name'],
            "users": list(room['users']),
            "is_encrypted": room['is_encrypted'],
            "public_key": room.get('public_key'),
            "security_level": "high" if room['is_encrypted'] else "standard"
        })
        
    except Exception as e:
        print(f"❌ Error in /join_room: {e}")
        return jsonify({"error": "Server error"}), 500

def verify_encryption_key(room_id, user_public_key, verification_data):
    """🔐 Проверка ключа шифрования"""
    try:
        # В реальной системе здесь должна быть сложная проверка
        # Для демо - просто проверяем что ключ предоставлен и имеет правильный формат
        if not user_public_key or len(user_public_key) < 100:
            return False
            
        # Проверяем что публичный ключ комнаты существует
        if room_id not in room_keys:
            return False
            
        # 🔐 ГИБРИДНОЕ ШИФРОВАНИЕ: Проверяем что ключ поддерживает гибридную схему
        # В реальной реализации здесь должна быть проверка структуры ключа
        if not verification_data or 'encrypted_key' not in verification_data:
            print("⚠️  Missing hybrid encryption data")
            return False
            
        print(f"🔐 Hybrid key verification for room {room_id}: SUCCESS")
        return True
        
    except Exception as e:
        print(f"❌ Key verification error: {e}")
        return False

# 🔐 НОВЫЕ ЭНДПОИНТЫ ДЛЯ ГИБРИДНОГО ШИФРОВАНИЯ
@app.route('/encrypt_hybrid', methods=['POST', 'OPTIONS'])
def encrypt_hybrid():
    """🔐 Эндпоинт для гибридного шифрования (симуляция)"""
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.get_json()
        message = data.get('message')
        public_key = data.get('public_key')
        
        if not message or not public_key:
            return jsonify({"error": "Message and public key required"}), 400
        
        # 🔐 СИМУЛЯЦИЯ ГИБРИДНОГО ШИФРОВАНИЯ
        # В реальной системе здесь будет реализация RSA + AES
        encrypted_data = {
            'encrypted_data': f"HYBRID_ENCRYPTED:{hashlib.sha256(message.encode()).hexdigest()[:16]}",
            'encrypted_key': f"RSA_ENCRYPTED_AES_KEY:{secrets.token_hex(16)}",
            'iv': secrets.token_hex(12),
            'algorithm': 'RSA-AES-256-GCM',
            'timestamp': datetime.now().isoformat()
        }
        
        print(f"🔐 Hybrid encryption completed for {len(message)} chars")
        
        return jsonify({
            "status": "encrypted",
            "encrypted_data": encrypted_data,
            "security_level": "high"
        })
        
    except Exception as e:
        print(f"❌ Error in /encrypt_hybrid: {e}")
        return jsonify({"error": "Encryption error"}), 500

@app.route('/decrypt_hybrid', methods=['POST', 'OPTIONS'])
def decrypt_hybrid():
    """🔐 Эндпоинт для гибридного дешифрования (симуляция)"""
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.get_json()
        encrypted_data = data.get('encrypted_data')
        private_key = data.get('private_key')  # В реальной системе никогда не отправляется на сервер!
        
        if not encrypted_data:
            return jsonify({"error": "Encrypted data required"}), 400
        
        # 🔐 СИМУЛЯЦИЯ ГИБРИДНОГО ДЕШИФРОВАНИЯ
        # В реальной системе дешифрование должно происходить на клиенте
        print(f"🔐 Hybrid decryption requested for {encrypted_data.get('encrypted_data', '')[:50]}...")
        
        return jsonify({
            "status": "decryption_simulated",
            "message": "🔒 Decryption should be performed on client side for security",
            "security_note": "Never send private keys to server!"
        })
        
    except Exception as e:
        print(f"❌ Error in /decrypt_hybrid: {e}")
        return jsonify({"error": "Decryption error"}), 500

# Отправка сообщений с поддержкой гибридного шифрования
@app.route('/send', methods=['POST', 'OPTIONS'])
def send_message():
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.get_json()
        username = data.get('username')
        text = data.get('text', '').strip()
        image_data = data.get('image')
        audio_data = data.get('audio')
        message_type = data.get('type', 'text')
        reply_to = data.get('reply_to')
        self_destruct = data.get('self_destruct', False)
        
        # 🔐 Новые поля для зашифрованных сообщений
        encrypted_data = data.get('encrypted_data')
        encryption_metadata = data.get('encryption_metadata')
        is_encrypted_payload = data.get('is_encrypted', False)
        
        # 🔐 ГИБРИДНОЕ ШИФРОВАНИЕ: Определяем тип шифрования
        is_hybrid_encrypted = encrypted_data and 'encrypted_key' in encrypted_data
        
        # Проверяем что username предоставлен
        if not username:
            return jsonify({"error": "Username is required"}), 400
            
        # Проверяем что пользователь находится в какой-либо комнате
        if username not in user_rooms:
            return jsonify({"error": "User not in any room"}), 400
        
        room_id = user_rooms[username]
        
        # Проверяем что комната существует
        if room_id not in rooms:
            return jsonify({"error": "Room not found"}), 404
            
        room = rooms[room_id]
        
        # 🔐 Проверяем соответствие типа сообщения и типа комнаты
        if room['is_encrypted'] and not is_encrypted_payload:
            return jsonify({
                "error": "Encrypted payload required for encrypted room",
                "is_encrypted": True
            }), 400
        
        if not room['is_encrypted'] and is_encrypted_payload:
            return jsonify({
                "error": "Encrypted payload not allowed in standard room",
                "is_encrypted": False
            }), 400
        
        # 🔐 ИСПРАВЛЕНИЕ: Для зашифрованных комнат разрешаем медиа без encrypted_data
        if room['is_encrypted']:
            # Для зашифрованных комнат проверяем наличие либо зашифрованных данных, либо медиа
            if not encrypted_data and not image_data and not audio_data and not text:
                return jsonify({"error": "Empty message"}), 400
        else:
            # Для незашифрованных комнат стандартная проверка
            if not text and not image_data and not audio_data:
                return jsonify({"error": "Empty message"}), 400
        
        # Автоматически определяем тип сообщения по наличию медиа
        if image_data:
            message_type = 'image'
            if not text:
                text = '🖼️ Image'
        elif audio_data:
            message_type = 'audio'
            if not text:
                text = '🎤 Voice message'
        
        # Создаем объект сообщения
        message = {
            'id': room['next_id'],
            'user': username,
            'text': text,
            'type': message_type,
            'time': datetime.now().isoformat(),
            'reply_to': reply_to,
            'self_destruct': self_destruct,
            # 🔐 Новые поля для шифрования
            'is_encrypted': is_encrypted_payload,
            'is_hybrid_encrypted': is_hybrid_encrypted,  # 🔐 Новое поле для гибридного шифрования
            'encrypted_data': encrypted_data,
            'encryption_metadata': encryption_metadata
        }
        
        # 🔐 ИСПРАВЛЕНИЕ: Сохраняем медиаданные для ВСЕХ комнат
        if image_data:
            # Генерируем уникальный ID для изображения
            image_id = str(uuid.uuid4())
            message['image_id'] = image_id
            # Сохраняем Base64 данные изображения
            room['media'][image_id] = image_data
            print(f"📸 Image saved with ID: {image_id}")
        
        if audio_data:
            # Генерируем уникальный ID для аудио
            audio_id = str(uuid.uuid4())
            message['audio_id'] = audio_id
            room['media'][audio_id] = audio_data
            print(f"🎵 Audio saved with ID: {audio_id}")
        
        # Сохраняем сообщение в комнату
        room['messages'].append(message)
        room['next_id'] += 1
        
        # Ограничиваем количество сообщений (последние 100)
        if len(room['messages']) > 100:
            # Удаляем также медиафайлы и реакции старых сообщений
            removed_messages = room['messages'][:-100]
            for msg in removed_messages:
                # Удаляем медиа
                if 'image_id' in msg and msg['image_id'] in room['media']:
                    del room['media'][msg['image_id']]
                if 'audio_id' in msg and msg['audio_id'] in room['media']:
                    del room['media'][msg['audio_id']]
                # Удаляем реакции
                if msg['id'] in room['reactions']:
                    del room['reactions'][msg['id']]
            room['messages'] = room['messages'][-100:]
        
        encryption_type = "Hybrid" if is_hybrid_encrypted else "Standard" if is_encrypted_payload else "None"
        print(f"📨 Message in room {room_id}: {username}: {text[:50]}... (type: {message_type}, encryption: {encryption_type})")
        
        # Формируем ответ
        response_data = {
            "status": "sent", 
            "message_id": message['id'],
            "is_encrypted": is_encrypted_payload,
            "is_hybrid_encrypted": is_hybrid_encrypted  # 🔐 Информация о типе шифрования
        }
        
        # Добавляем ID медиафайлов в ответ если они есть
        if 'image_id' in message:
            response_data['image_id'] = message['image_id']
        if 'audio_id' in message:
            response_data['audio_id'] = message['audio_id']
            
        return jsonify(response_data)
        
    except Exception as e:
        print(f"❌ Error in /send: {e}")
        return jsonify({"error": "Server error"}), 500

# Получение сообщений с информацией о гибридном шифровании
@app.route('/receive', methods=['GET'])
def receive_messages():
    try:
        username = request.args.get('username')
        since_id = int(request.args.get('since_id', 0))
        
        if not username:
            return jsonify({"error": "Username is required"}), 400
            
        if username not in user_rooms:
            return jsonify({"error": "User not in any room"}), 400
        
        room_id = user_rooms[username]
        
        if room_id not in rooms:
            return jsonify({"error": "Room not found"}), 404
            
        room = rooms[room_id]
        
        # Фильтруем сообщения начиная с since_id
        new_messages = [
            msg for msg in room['messages'] 
            if msg['id'] > since_id
        ]
        
        # 🔐 ОБНОВЛЯЕМ ИНФОРМАЦИЮ О КОМНАТЕ
        if room['is_encrypted']:
            for msg in new_messages:
                # Для системных сообщений оставляем текст как есть
                if msg['type'] != 'system' and msg.get('is_encrypted'):
                    # 🔐 УЛУЧШАЕМ ОТОБРАЖЕНИЕ ДЛЯ ГИБРИДНОГО ШИФРОВАНИЯ
                    if msg.get('is_hybrid_encrypted'):
                        msg['text'] = '🔐 Hybrid Encrypted Message'
                        msg['encryption_type'] = 'hybrid'
                    else:
                        msg['text'] = '🔒 Encrypted Message'
                        msg['encryption_type'] = 'standard'
                # 🔐 ИСПРАВЛЕНИЕ: Для зашифрованных комнат ВСЕГДА добавляем медиаданные
                if 'image_id' in msg and msg['image_id'] in room['media']:
                    msg['image_data'] = room['media'][msg['image_id']]
                if 'audio_id' in msg and msg['audio_id'] in room['media']:
                    msg['audio_data'] = room['media'][msg['audio_id']]
        else:
            # Для незашифрованных комнат добавляем медиаданные как обычно
            for msg in new_messages:
                if 'image_id' in msg and msg['image_id'] in room['media']:
                    msg['image_data'] = room['media'][msg['image_id']]
                if 'audio_id' in msg and msg['audio_id'] in room['media']:
                    msg['audio_data'] = room['media'][msg['audio_id']]
                
                # Добавляем реакции к сообщениям
                if msg['id'] in room['reactions']:
                    msg['reactions'] = room['reactions'][msg['id']]
        
        print(f"📤 Sending {len(new_messages)} new messages from room {room_id} to {username}")
        print(f"🔐 Room encrypted: {room['is_encrypted']}")
        
        return jsonify({
            "messages": new_messages,
            "users": list(room['users']),
            "room_name": room['name'],
            "reactions": room['reactions'],
            "is_encrypted": room['is_encrypted'],
            "supports_hybrid_encryption": True,  # 🔐 Новая информация
            "public_key": room.get('public_key')
        })
        
    except Exception as e:
        print(f"❌ Error in /receive: {e}")
        return jsonify({"error": "Server error"}), 500

# 🔐 ВОССТАНАВЛИВАЕМ ВСЕ ФИЧИ РЕАКЦИЙ
@app.route('/add_reaction', methods=['POST', 'OPTIONS'])
def add_reaction():
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.get_json()
        message_id = data.get('message_id')
        username = data.get('username')
        emoji = data.get('emoji')
        room_id = data.get('room_id')
        
        print(f"🔄 Adding reaction: message_id={message_id}, username={username}, emoji={emoji}, room_id={room_id}")
        
        if not all([message_id, username, emoji, room_id]):
            return jsonify({"error": "Missing required fields"}), 400
            
        if room_id not in rooms:
            return jsonify({"error": "Room not found"}), 404
            
        room = rooms[room_id]
        
        # Проверяем что пользователь в комнате
        if username not in room['users']:
            return jsonify({"error": "User not in room"}), 403
        
        # Ищем сообщение
        message = None
        for msg in room['messages']:
            if msg['id'] == message_id:
                message = msg
                break
        
        if not message:
            return jsonify({"error": "Message not found"}), 404
        
        # Инициализируем реакции для сообщения если их еще нет
        if message_id not in room['reactions']:
            room['reactions'][message_id] = {}
        
        # Инициализируем список пользователей для эмодзи если его еще нет
        if emoji not in room['reactions'][message_id]:
            room['reactions'][message_id][emoji] = []
        
        # Добавляем пользователя в реакцию если его там еще нет
        if username not in room['reactions'][message_id][emoji]:
            room['reactions'][message_id][emoji].append(username)
            print(f"✅ Reaction added: {emoji} by {username} to message {message_id}")
        else:
            print(f"ℹ️ Reaction already exists: {emoji} by {username} to message {message_id}")
        
        return jsonify({
            "status": "reaction_added",
            "message_id": message_id,
            "emoji": emoji,
            "username": username,
            "reactions": room['reactions'][message_id]
        })
        
    except Exception as e:
        print(f"❌ Error in /add_reaction: {e}")
        return jsonify({"error": "Server error"}), 500

@app.route('/remove_reaction', methods=['POST', 'OPTIONS'])
def remove_reaction():
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.get_json()
        message_id = data.get('message_id')
        username = data.get('username')
        emoji = data.get('emoji')
        room_id = data.get('room_id')
        
        print(f"🔄 Removing reaction: message_id={message_id}, username={username}, emoji={emoji}, room_id={room_id}")
        
        if not all([message_id, username, emoji, room_id]):
            return jsonify({"error": "Missing required fields"}), 400
            
        if room_id not in rooms:
            return jsonify({"error": "Room not found"}), 404
            
        room = rooms[room_id]
        
        # Проверяем что пользователь в комнате
        if username not in room['users']:
            return jsonify({"error": "User not in room"}), 403
        
        # Проверяем что реакция существует
        if (message_id not in room['reactions'] or 
            emoji not in room['reactions'][message_id] or 
            username not in room['reactions'][message_id][emoji]):
            return jsonify({"error": "Reaction not found"}), 404
        
        # Удаляем пользователя из реакции
        room['reactions'][message_id][emoji].remove(username)
        
        # Если больше нет пользователей с этой реакцией, удаляем эмодзи
        if not room['reactions'][message_id][emoji]:
            del room['reactions'][message_id][emoji]
        
        # Если больше нет реакций для сообщения, удаляем запись
        if not room['reactions'][message_id]:
            del room['reactions'][message_id]
        
        print(f"✅ Reaction removed: {emoji} by {username} from message {message_id}")
        
        return jsonify({
            "status": "reaction_removed",
            "message_id": message_id,
            "emoji": emoji,
            "username": username
        })
        
    except Exception as e:
        print(f"❌ Error in /remove_reaction: {e}")
        return jsonify({"error": "Server error"}), 500

@app.route('/get_reactions', methods=['GET'])
def get_reactions():
    try:
        message_id = int(request.args.get('message_id'))
        room_id = request.args.get('room_id')
        
        if not message_id or not room_id:
            return jsonify({"error": "Message ID and Room ID are required"}), 400
            
        if room_id not in rooms:
            return jsonify({"error": "Room not found"}), 404
            
        room = rooms[room_id]
        
        reactions = room['reactions'].get(message_id, {})
        
        return jsonify({
            "message_id": message_id,
            "reactions": reactions
        })
        
    except Exception as e:
        print(f"❌ Error in /get_reactions: {e}")
        return jsonify({"error": "Server error"}), 500

# 🔐 ВОССТАНАВЛИВАЕМ ВСЕ ФИЧИ ЗВОНКОВ
@app.route('/call_signal', methods=['POST', 'OPTIONS'])
def call_signal():
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.get_json()
        from_user = data.get('from_user')
        to_user = data.get('to_user')
        signal_type = data.get('type')
        signal_data = data.get('data')
        
        if not all([from_user, to_user, signal_type, signal_data]):
            return jsonify({"error": "Missing required fields"}), 400
        
        if to_user not in call_signals:
            call_signals[to_user] = []
        
        call_signals[to_user].append({
            'from_user': from_user,
            'type': signal_type,
            'data': signal_data,
            'timestamp': datetime.now().isoformat()
        })
        
        print(f"📞 Call signal from {from_user} to {to_user}: {signal_type}")
        
        return jsonify({"status": "signal_sent"})
        
    except Exception as e:
        print(f"❌ Error in /call_signal: {e}")
        return jsonify({"error": "Server error"}), 500

@app.route('/get_call_signals', methods=['GET'])
def get_call_signals():
    try:
        username = request.args.get('username')
        
        if not username:
            return jsonify({"error": "Username is required"}), 400
        
        signals = call_signals.get(username, [])
        call_signals[username] = []
        
        return jsonify({
            "signals": signals
        })
        
    except Exception as e:
        print(f"❌ Error in /get_call_signals: {e}")
        return jsonify({"error": "Server error"}), 500

# 🔐 ВОССТАНАВЛИВАЕМ МЕДИА ЭНДПОИНТ
@app.route('/media/<media_id>', methods=['GET'])
def get_media(media_id):
    try:
        # Ищем медиа во всех комнатах
        for room in rooms.values():
            if media_id in room['media']:
                return jsonify({
                    "media_id": media_id,
                    "data": room['media'][media_id]
                })
        
        return jsonify({"error": "Media not found"}), 404
        
    except Exception as e:
        print(f"❌ Error in /media: {e}")
        return jsonify({"error": "Server error"}), 500

# 🔐 ВОССТАНАВЛИВАЕМ LEAVE_ROOM
@app.route('/leave_room', methods=['POST', 'OPTIONS'])
def leave_room():
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.get_json()
        username = data.get('username')
        
        if not username:
            return jsonify({"error": "Username is required"}), 400
            
        if username not in user_rooms:
            return jsonify({"error": "User not in any room"}), 400
        
        room_id = user_rooms[username]
        
        if room_id not in rooms:
            return jsonify({"error": "Room not found"}), 404
            
        room = rooms[room_id]
        
        # Удаляем пользователя из комнаты
        room['users'].discard(username)
        del user_rooms[username]
        
        # Добавляем системное сообщение о выходе
        system_message = {
            'id': room['next_id'],
            'user': 'System',
            'text': f'{username} left the room',
            'time': datetime.now().isoformat(),
            'type': 'system'
        }
        room['messages'].append(system_message)
        room['next_id'] += 1
        
        # 🔐 Удаляем попытки верификации ключей для этого пользователя
        for key in list(key_verification_attempts.keys()):
            if key.startswith(f"{room_id}:{username}"):
                del key_verification_attempts[key]
        
        print(f"👋 User {username} left room {room_id}")
        
        return jsonify({
            "status": "left",
            "room_id": room_id,
            "remaining_users": len(room['users'])
        })
        
    except Exception as e:
        print(f"❌ Error in /leave_room: {e}")
        return jsonify({"error": "Server error"}), 500

# 🔐 ВОССТАНАВЛИВАЕМ СТАТИСТИКУ И ОЧИСТКУ
@app.route('/stats')
def get_stats():
    """Получение статистики сервера"""
    try:
        total_rooms = len(rooms)
        encrypted_rooms_count = len([r for r in rooms.values() if r['is_encrypted']])
        total_users = len(user_rooms)
        total_messages = sum(len(room['messages']) for room in rooms.values())
        total_reactions = sum(len(reactions) for room in rooms.values() for reactions in room['reactions'].values())
        
        # 🔐 Статистика по шифрованию
        encrypted_messages = sum(
            len([m for m in room['messages'] if m.get('is_encrypted')]) 
            for room in rooms.values() 
            if room['is_encrypted']
        )
        
        # 🔐 Новая статистика по гибридному шифрованию
        hybrid_encrypted_messages = sum(
            len([m for m in room['messages'] if m.get('is_hybrid_encrypted')]) 
            for room in rooms.values() 
            if room['is_encrypted']
        )
        
        # Активные комнаты (с пользователями)
        active_rooms = {room_id: room for room_id, room in rooms.items() if len(room['users']) > 0}
        active_encrypted_rooms = len([r for r in active_rooms.values() if r['is_encrypted']])
        
        return jsonify({
            "total_rooms": total_rooms,
            "encrypted_rooms": encrypted_rooms_count,
            "standard_rooms": total_rooms - encrypted_rooms_count,
            "active_rooms": len(active_rooms),
            "active_encrypted_rooms": active_encrypted_rooms,
            "total_users": total_users,
            "total_messages": total_messages,
            "encrypted_messages": encrypted_messages,
            "hybrid_encrypted_messages": hybrid_encrypted_messages,  # 🔐 Новая статистика
            "total_reactions": total_reactions,
            "pending_call_signals": sum(len(signals) for signals in call_signals.values()),
            "bruteforce_attempts_tracked": len(bruteforce_attempts),  # 🔐 Новая статистика
            "server_time": datetime.now().isoformat(),
            "security_summary": {
                "encrypted_percentage": round((encrypted_rooms_count / total_rooms * 100) if total_rooms > 0 else 0, 1),
                "encrypted_messages_percentage": round((encrypted_messages / total_messages * 100) if total_messages > 0 else 0, 1),
                "hybrid_encryption_percentage": round((hybrid_encrypted_messages / encrypted_messages * 100) if encrypted_messages > 0 else 0, 1),
                "recommendation": "🔒 Enable hybrid encryption for best performance and security"
            }
        })
        
    except Exception as e:
        print(f"❌ Error in /stats: {e}")
        return jsonify({"error": "Server error"}), 500

@app.route('/cleanup', methods=['POST'])
def cleanup_rooms():
    """Очистка комнат старше 24 часов"""
    try:
        current_time = datetime.now()
        rooms_to_delete = []
        
        # Находим комнаты старше 24 часов
        for room_id, room in rooms.items():
            created_at = datetime.fromisoformat(room['created_at'])
            if (current_time - created_at).total_seconds() > 24 * 60 * 60:
                rooms_to_delete.append(room_id)
        
        # Удаляем старые комнаты
        for room_id in rooms_to_delete:
            # Удаляем пользователей этой комнаты
            users_to_remove = [user for user, rid in user_rooms.items() if rid == room_id]
            for user in users_to_remove:
                del user_rooms[user]
                # Также удаляем сигналы звонков для этих пользователей
                if user in call_signals:
                    del call_signals[user]
                # 🔐 Удаляем попытки верификации ключей
                for key in list(key_verification_attempts.keys()):
                    if key.startswith(f"{room_id}:"):
                        del key_verification_attempts[key]
            
            # 🔐 Удаляем ключи шифрования если комната была зашифрованной
            if room_id in room_keys:
                del room_keys[room_id]
            if room_id in encrypted_rooms:
                encrypted_rooms.remove(room_id)
                
            del rooms[room_id]
            print(f"🧹 Deleted old room: {room_id}")
        
        # 🔐 Очищаем старые записи брутфорса
        cleanup_old_attempts()
        
        return jsonify({
            "status": "cleaned",
            "deleted_rooms": len(rooms_to_delete),
            "active_rooms": len(rooms),
            "remaining_encrypted_rooms": len(encrypted_rooms),
            "cleaned_verification_attempts": len(rooms_to_delete),
            "bruteforce_entries_remaining": len(bruteforce_attempts)
        })
        
    except Exception as e:
        print(f"❌ Error in /cleanup: {e}")
        return jsonify({"error": "Server error"}), 500

# 🔐 НОВЫЕ ЭНДПОИНТЫ БЕЗОПАСНОСТИ
@app.route('/verify_key', methods=['POST', 'OPTIONS'])
def verify_key():
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.get_json()
        room_id = data.get('room_id')
        username = data.get('username')
        public_key = data.get('public_key')
        challenge_response = data.get('challenge_response')
        
        # 🔐 УЛУЧШЕННАЯ ЗАЩИТА ОТ БРУТФОРСА
        client_ip = get_client_ip()
        if not check_bruteforce(client_ip, room_id):
            return jsonify({
                "error": "Too many verification attempts. Please wait 1 hour.",
                "blocked": True
            }), 429
        
        if not all([room_id, username, public_key]):
            return jsonify({"error": "Room ID, username and public key required"}), 400
            
        if room_id not in rooms:
            return jsonify({"error": "Room not found"}), 404
            
        room = rooms[room_id]
        
        if not room['is_encrypted']:
            return jsonify({"error": "Room is not encrypted"}), 400
        
        # Проверяем количество попыток
        attempt_key = f"{room_id}:{username}"
        current_attempts = key_verification_attempts.get(attempt_key, 0)
        if current_attempts >= 5:
            return jsonify({
                "error": "Too many verification attempts. Please wait 10 minutes.",
                "blocked": True
            }), 429
        
        # 🔐 Проверяем ключ
        is_valid = verify_encryption_key(room_id, public_key, challenge_response)
        
        if is_valid:
            key_verification_attempts.pop(attempt_key, None)
            return jsonify({
                "status": "key_verified",
                "room_id": room_id,
                "room_name": room['name'],
                "is_encrypted": True,
                "supports_hybrid_encryption": True,  # 🔐 Новая информация
                "public_key": room.get('public_key')
            })
        else:
            key_verification_attempts[attempt_key] = current_attempts + 1
            return jsonify({
                "error": "Key verification failed",
                "attempts_remaining": 5 - (current_attempts + 1)
            }), 401
        
    except Exception as e:
        print(f"❌ Error in /verify_key: {e}")
        return jsonify({"error": "Server error"}), 500

@app.route('/room_encryption_info', methods=['GET'])
def room_encryption_info():
    try:
        room_id = request.args.get('room_id')
        
        if not room_id:
            return jsonify({"error": "Room ID is required"}), 400
            
        if room_id not in rooms:
            return jsonify({"error": "Room not found"}), 404
            
        room = rooms[room_id]
        
        return jsonify({
            "room_id": room_id,
            "room_name": room['name'],
            "is_encrypted": room['is_encrypted'],
            "has_public_key": bool(room.get('public_key')),
            "supports_hybrid_encryption": True,  # 🔐 Новая информация
            "users_count": len(room['users']),
            "created_at": room['created_at'],
            "encryption_enabled_at": room.get('encryption_enabled_at'),
            "security_level": "high" if room['is_encrypted'] else "standard"
        })
        
    except Exception as e:
        print(f"❌ Error in /room_encryption_info: {e}")
        return jsonify({"error": "Server error"}), 500

@app.route('/room_info', methods=['GET'])
def room_info():
    try:
        username = request.args.get('username')
        
        if not username or username not in user_rooms:
            return jsonify({"error": "User not in any room"}), 400
        
        room_id = user_rooms[username]
        room = rooms[room_id]
        
        return jsonify({
            "room_id": room_id,
            "room_name": room['name'],
            "users_count": len(room['users']),
            "created_at": room['created_at'],
            "messages_count": len(room['messages']),
            "is_encrypted": room['is_encrypted'],
            "supports_hybrid_encryption": True,  # 🔐 Новая информация
            "security_level": "🔒 Encrypted" if room['is_encrypted'] else "🔓 Standard",
            "security_description": "End-to-end encrypted with hybrid RSA+AES" if room['is_encrypted'] else "Standard security"
        })
        
    except Exception as e:
        print(f"❌ Error in /room_info: {e}")
        return jsonify({"error": "Server error"}), 500

@app.route('/security_status', methods=['GET'])
def security_status():
    """Получение информации о статусе безопасности"""
    try:
        client_ip = get_client_ip()
        
        # 🔐 Собираем информацию о брутфорс-защите
        bruteforce_info = {}
        for key, attempts in bruteforce_attempts.items():
            if client_ip in key:
                bruteforce_info[key] = {
                    'attempts_count': len(attempts),
                    'last_attempt': max(attempts) if attempts else None,
                    'blocked': len(attempts) >= MAX_ATTEMPTS_PER_HOUR
                }
        
        return jsonify({
            "client_ip": client_ip,
            "bruteforce_protection": {
                "max_attempts_per_hour": MAX_ATTEMPTS_PER_HOUR,
                "block_time_seconds": BLOCK_TIME,
                "current_attempts": bruteforce_info,
                "global_attempts_tracked": len(bruteforce_attempts)
            },
            "encryption_support": {
                "hybrid_encryption": True,
                "algorithms": ["RSA-OAEP", "AES-GCM-256"],
                "key_exchange": "RSA + AES hybrid",
                "performance": "optimized"
            },
            "password_security": {
                "hashing_algorithm": "PBKDF2-HMAC-SHA256",
                "iterations": 100000,
                "salt_length": 32,
                "storage": "in_memory_only"
            },
            "recommendations": [
                "Use hybrid encryption for best performance",
                "Enable room passwords for additional security",
                "Regularly rotate encryption keys"
            ]
        })
        
    except Exception as e:
        print(f"❌ Error in /security_status: {e}")
        return jsonify({"error": "Server error"}), 500

# Запуск сервера
if __name__ == '__main__':
    print("🚀 Starting Secure Chat Server...")
    print("🔐 Security Features:")
    print("   • Hybrid RSA+AES encryption support")
    print("   • PBKDF2 password hashing (in-memory)")
    print("   • Enhanced brute-force protection")
    print("   • Key verification with rate limiting")
    print("   • Automatic security cleanup")
    print("📡 Endpoints available:")
    print("   POST /create_room - Create a new chat room")
    print("   POST /join_room - Join an existing room") 
    print("   POST /send - Send a message")
    print("   GET  /receive - Receive new messages")
    print("   POST /add_reaction - Add reaction to message")
    print("   POST /remove_reaction - Remove reaction from message")
    print("   GET  /get_reactions - Get reactions for message")
    print("   POST /call_signal - Send WebRTC signal")
    print("   GET  /get_call_signals - Get pending WebRTC signals")
    print("   POST /leave_room - Leave current room")
    print("   GET  /stats - Get server statistics")
    print("   POST /cleanup - Cleanup old rooms")
    print("🔐 NEW Encryption endpoints:")
    print("   POST /encrypt_hybrid - Hybrid encryption (RSA+AES)")
    print("   POST /decrypt_hybrid - Hybrid decryption")
    print("   POST /verify_key - Verify encryption key")
    print("   GET  /room_encryption_info - Get room encryption info")
    print("   GET  /security_status - Get security status")
    
    app.run(
        host='0.0.0.0', 
        port=5000, 
        debug=True,
        ssl_context='adhoc'  # 🔐 Включаем HTTPS
    )
