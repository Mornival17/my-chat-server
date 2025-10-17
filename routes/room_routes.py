from flask import Blueprint, request, jsonify
from datetime import datetime
from utils.helpers import generate_room_id, get_current_time
from models.data_store import rooms, user_rooms, room_keys, encrypted_rooms
from security.bruteforce_protection import check_bruteforce, get_client_ip
from security.encryption import verify_encryption_key

room_bp = Blueprint('room', __name__)

@room_bp.route('/')
def home():
    return "🚀 Secure Chat Server Ready! Use /create_room, /join_room, /send and /receive"

@room_bp.route('/health')
def health():
    return "OK"

@room_bp.route('/create_room', methods=['POST', 'OPTIONS'])
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
        
        # Создаем комнату со всей необходимой информацией
        rooms[room_id] = {
            'name': room_name,
            'password': password,
            'created_at': get_current_time(),
            'users': set([username]),
            'messages': [],
            'next_id': 1,
            'media': {},
            'reactions': {},
            # 🔐 Новые поля для шифрования
            'is_encrypted': is_encrypted,
            'public_key': public_key,
            'encryption_enabled_at': get_current_time() if is_encrypted else None
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

@room_bp.route('/join_room', methods=['POST', 'OPTIONS'])
def join_room():
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        # 🔐 Проверяем защиту от брутфорса
        client_ip = get_client_ip(request)
        if not check_bruteforce(client_ip):
            return jsonify({
                "error": "Too many attempts. Please wait 5 minutes.",
                "blocked": True
            }), 429
            
        data = request.get_json()
        room_id = data.get('room_id')
        password = data.get('password', '')
        username = data.get('username', 'Anonymous')
        
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
        
        # Проверяем пароль если он установлен
        if room['password'] and room['password'] != password:
            return jsonify({"error": "Invalid password"}), 401
        
        # 🔐 Проверяем ключ для зашифрованных комнат
        if room['is_encrypted']:
            from models.data_store import key_verification_attempts
            
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
            'time': get_current_time(),
            'type': 'system'
        }
        room['messages'].append(system_message)
        room['next_id'] += 1
        
        print(f"👤 User {username} joined room {room_id}")
        print(f"🔐 Room encryption: {room['is_encrypted']}")
        
        return jsonify({
            "status": "joined",
            "room_name": room['name'],
            "users': list(room['users']),
            "is_encrypted": room['is_encrypted'],
            "public_key": room.get('public_key'),
            "security_level": "high" if room['is_encrypted'] else "standard"
        })
        
    except Exception as e:
        print(f"❌ Error in /join_room: {e}")
        return jsonify({"error": "Server error"}), 500

@room_bp.route('/leave_room', methods=['POST', 'OPTIONS'])
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
            'time': get_current_time(),
            'type': 'system'
        }
        room['messages'].append(system_message)
        room['next_id'] += 1
        
        print(f"👋 User {username} left room {room_id}")
        
        return jsonify({"status": "left"})
        
    except Exception as e:
        print(f"❌ Error in /leave_room: {e}")
        return jsonify({"error": "Server error"}), 500
