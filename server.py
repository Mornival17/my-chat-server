from flask import Flask, request, jsonify
from datetime import datetime
import os
import secrets
import uuid
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Разрешаем все CORS запросы

# Глобальные переменные для хранения данных
rooms = {}  # {room_id: {name: str, password: str, created_at: str, users: set, messages: [], next_id: int, media: {}}}
user_rooms = {}  # {username: room_id}

def generate_room_id():
    """Генерация уникального ID комнаты"""
    return secrets.token_urlsafe(8)

@app.route('/')
def home():
    return "🚀 Chat Server Ready! Use /create_room, /join_room, /send and /receive"

@app.route('/health')
def health():
    return "OK"

@app.route('/create_room', methods=['POST', 'OPTIONS'])
def create_room():
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.get_json()
        room_name = data.get('room_name', 'New Room')
        password = data.get('password', '')
        username = data.get('username', 'Host')
        
        # Генерируем уникальный ID комнаты
        room_id = generate_room_id()
        
        # Создаем комнату
        rooms[room_id] = {
            'name': room_name,
            'password': password,
            'created_at': datetime.now().isoformat(),
            'users': set([username]),
            'messages': [],
            'next_id': 1,
            'media': {}  # Для хранения медиафайлов
        }
        
        # Связываем пользователя с комнатой
        user_rooms[username] = room_id
        
        print(f"🎉 Room created: {room_name} (ID: {room_id}) by {username}")
        return jsonify({
            "status": "created", 
            "room_id": room_id,
            "room_name": room_name
        })
        
    except Exception as e:
        print(f"❌ Error in /create_room: {e}")
        return jsonify({"error": "Server error"}), 500

@app.route('/join_room', methods=['POST', 'OPTIONS'])
def join_room():
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.get_json()
        room_id = data.get('room_id')
        password = data.get('password', '')
        username = data.get('username', 'Anonymous')
        
        if not room_id:
            return jsonify({"error": "Room ID is required"}), 400
            
        if room_id not in rooms:
            return jsonify({"error": "Room not found"}), 404
        
        room = rooms[room_id]
        
        # Проверка пароля
        if room['password'] and room['password'] != password:
            return jsonify({"error": "Invalid password"}), 401
        
        # Добавляем пользователя в комнату
        room['users'].add(username)
        user_rooms[username] = room_id
        
        # Добавляем системное сообщение
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
        return jsonify({
            "status": "joined",
            "room_name": room['name'],
            "users": list(room['users'])
        })
        
    except Exception as e:
        print(f"❌ Error in /join_room: {e}")
        return jsonify({"error": "Server error"}), 500

@app.route('/send', methods=['POST', 'OPTIONS'])
def send_message():
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.get_json()
        username = data.get('username')
        text = data.get('text', '').strip()
        image_data = data.get('image')  # Base64 encoded image
        audio_data = data.get('audio')  # Base64 encoded audio
        message_type = data.get('type', 'text')  # text, image, audio
        
        if not username:
            return jsonify({"error": "Username is required"}), 400
            
        if username not in user_rooms:
            return jsonify({"error": "User not in any room"}), 400
        
        room_id = user_rooms[username]
        
        if room_id not in rooms:
            return jsonify({"error": "Room not found"}), 404
            
        room = rooms[room_id]
        
        # Для медиа-сообщений текст может быть пустым
        if not text and not image_data and not audio_data:
            return jsonify({"error": "Empty message"}), 400
        
        # Автоматически определяем тип сообщения
        if image_data:
            message_type = 'image'
            if not text:
                text = '🖼️ Image'
        elif audio_data:
            message_type = 'audio'
            if not text:
                text = '🎤 Voice message'
        
        # Создаем сообщение с типом
        message = {
            'id': room['next_id'],
            'user': username,
            'text': text,
            'type': message_type,
            'time': datetime.now().isoformat()
        }
        
        # Сохраняем медиаданные если есть
        if image_data:
            # Генерируем уникальный ID для изображения
            image_id = str(uuid.uuid4())
            message['image_id'] = image_id
            # Сохраняем в памяти (для продакшена лучше использовать облачное хранилище)
            room['media'][image_id] = image_data
            print(f"📸 Image saved with ID: {image_id}")
        
        if audio_data:
            # Генерируем уникальный ID для аудио
            audio_id = str(uuid.uuid4())
            message['audio_id'] = audio_id
            room['media'][audio_id] = audio_data
            print(f"🎵 Audio saved with ID: {audio_id}")
        
        # Сохраняем сообщение
        room['messages'].append(message)
        room['next_id'] += 1
        
        # Лимит сообщений (последние 100)
        if len(room['messages']) > 100:
            # Удаляем также медиафайлы старых сообщений
            removed_messages = room['messages'][:-100]
            for msg in removed_messages:
                if 'image_id' in msg and msg['image_id'] in room['media']:
                    del room['media'][msg['image_id']]
                if 'audio_id' in msg and msg['audio_id'] in room['media']:
                    del room['media'][msg['audio_id']]
            room['messages'] = room['messages'][-100:]
        
        print(f"📨 Message in room {room_id}: {username}: {text[:50]}... (type: {message_type})")
        
        response_data = {
            "status": "sent", 
            "message_id": message['id']
        }
        
        # Добавляем ID медиафайлов в ответ
        if 'image_id' in message:
            response_data['image_id'] = message['image_id']
        if 'audio_id' in message:
            response_data['audio_id'] = message['audio_id']
            
        return jsonify(response_data)
        
    except Exception as e:
        print(f"❌ Error in /send: {e}")
        return jsonify({"error": "Server error"}), 500

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
        
        # Фильтруем сообщения
        new_messages = [
            msg for msg in room['messages'] 
            if msg['id'] > since_id
        ]
        
        # Добавляем медиаданные к сообщениям
        for msg in new_messages:
            if 'image_id' in msg and msg['image_id'] in room['media']:
                msg['image_data'] = room['media'][msg['image_id']]
            if 'audio_id' in msg and msg['audio_id'] in room['media']:
                msg['audio_data'] = room['media'][msg['audio_id']]
        
        print(f"📤 Sending {len(new_messages)} new messages from room {room_id} to {username}")
        
        return jsonify({
            "messages": new_messages,
            "users": list(room['users']),
            "room_name": room['name']
        })
        
    except Exception as e:
        print(f"❌ Error in /receive: {e}")
        return jsonify({"error": "Server error"}), 500

@app.route('/media/<room_id>/<media_id>')
def get_media(room_id, media_id):
    """Эндпоинт для получения медиафайлов (альтернативный способ)"""
    try:
        if room_id not in rooms:
            return jsonify({"error": "Room not found"}), 404
            
        room = rooms[room_id]
        
        if media_id not in room['media']:
            return jsonify({"error": "Media not found"}), 404
            
        media_data = room['media'][media_id]
        
        # Определяем тип контента
        if media_data.startswith('data:image'):
            return jsonify({"data": media_data})
        elif media_data.startswith('data:audio'):
            return jsonify({"data": media_data})
        else:
            return jsonify({"error": "Unknown media type"}), 400
            
    except Exception as e:
        print(f"❌ Error in /media: {e}")
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
            "messages_count": len(room['messages'])
        })
        
    except Exception as e:
        print(f"❌ Error in /room_info: {e}")
        return jsonify({"error": "Server error"}), 500

@app.route('/cleanup', methods=['POST'])
def cleanup_rooms():
    """Очистка старых комнат (для обслуживания)"""
    try:
        current_time = datetime.now()
        rooms_to_delete = []
        
        for room_id, room in rooms.items():
            created_at = datetime.fromisoformat(room['created_at'])
            # Удаляем комнаты старше 24 часов
            if (current_time - created_at).total_seconds() > 24 * 60 * 60:
                rooms_to_delete.append(room_id)
        
        for room_id in rooms_to_delete:
            # Удаляем пользователей этой комнаты
            users_to_remove = [user for user, rid in user_rooms.items() if rid == room_id]
            for user in users_to_remove:
                del user_rooms[user]
            del rooms[room_id]
            print(f"🧹 Deleted old room: {room_id}")
        
        return jsonify({
            "status": "cleaned",
            "deleted_rooms": len(rooms_to_delete),
            "active_rooms": len(rooms)
        })
        
    except Exception as e:
        print(f"❌ Error in /cleanup: {e}")
        return jsonify({"error": "Server error"}), 500

@app.route('/stats')
def get_stats():
    """Статистика сервера"""
    try:
        total_rooms = len(rooms)
        total_users = len(user_rooms)
        total_messages = sum(len(room['messages']) for room in rooms.values())
        
        # Комнаты с пользователями
        active_rooms = {room_id: room for room_id, room in rooms.items() if len(room['users']) > 0}
        
        return jsonify({
            "total_rooms": total_rooms,
            "active_rooms": len(active_rooms),
            "total_users": total_users,
            "total_messages": total_messages,
            "server_time": datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"❌ Error in /stats: {e}")
        return jsonify({"error": "Server error"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    print(f"🚀 Starting Flask server with CORS on port {port}")
    print(f"📊 Available endpoints:")
    print(f"   POST /create_room - Create new room")
    print(f"   POST /join_room - Join existing room") 
    print(f"   POST /send - Send message")
    print(f"   GET  /receive - Receive messages")
    print(f"   GET  /room_info - Get room info")
    print(f"   GET  /stats - Server statistics")
    print(f"   POST /cleanup - Cleanup old rooms")
    app.run(host='0.0.0.0', port=port, debug=False)
