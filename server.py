from flask import Flask, request, jsonify
from datetime import datetime
import os
import secrets
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Глобальные переменные для хранения данных
rooms = {}  # {room_id: {name: str, password: str, created_at: str, users: set, messages: [], next_id: int}}
user_rooms = {}  # {username: room_id}

def generate_room_id():
    return secrets.token_urlsafe(8)

@app.route('/')
def home():
    return "🚀 Chat Server Ready! Use /create_room, /join_room, /send and /receive"

@app.route('/health')
def health():
    return "OK"

@app.route('/create_room', methods=['POST'])
def create_room():
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
            'next_id': 1
        }
        
        # Связываем пользователя с комнатой
        user_rooms[username] = room_id
        
        print(f"🎉 Room created: {room_name} (ID: {room_id})")
        return jsonify({
            "status": "created", 
            "room_id": room_id,
            "room_name": room_name
        })
        
    except Exception as e:
        print(f"❌ Error in /create_room: {e}")
        return jsonify({"error": "Server error"}), 500

@app.route('/join_room', methods=['POST'])
def join_room():
    try:
        data = request.get_json()
        room_id = data.get('room_id')
        password = data.get('password', '')
        username = data.get('username', 'Anonymous')
        
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
            'time': datetime.now().isoformat()
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

@app.route('/send', methods=['POST'])
def send_message():
    try:
        data = request.get_json()
        username = data.get('username')
        text = data.get('text', '').strip()
        
        if not username or username not in user_rooms:
            return jsonify({"error": "User not in any room"}), 400
        
        room_id = user_rooms[username]
        room = rooms[room_id]
        
        if not text:
            return jsonify({"error": "Empty message"}), 400
        
        # Создаем сообщение
        message = {
            'id': room['next_id'],
            'user': username,
            'text': text,
            'time': datetime.now().isoformat()
        }
        
        # Сохраняем
        room['messages'].append(message)
        room['next_id'] += 1
        
        # Лимит сообщений (последние 100)
        if len(room['messages']) > 100:
            room['messages'] = room['messages'][-100:]
        
        print(f"📨 Message in room {room_id}: {username}: {text}")
        return jsonify({"status": "sent", "message_id": message['id']})
        
    except Exception as e:
        print(f"❌ Error in /send: {e}")
        return jsonify({"error": "Server error"}), 500

@app.route('/receive', methods=['GET'])
def receive_messages():
    try:
        username = request.args.get('username')
        since_id = int(request.args.get('since_id', 0))
        
        if not username or username not in user_rooms:
            return jsonify({"error": "User not in any room"}), 400
        
        room_id = user_rooms[username]
        room = rooms[room_id]
        
        # Фильтруем сообщения
        new_messages = [
            msg for msg in room['messages'] 
            if msg['id'] > since_id
        ]
        
        print(f"📤 Sending {len(new_messages)} new messages from room {room_id}")
        return jsonify({
            "messages": new_messages,
            "users": list(room['users']),
            "room_name": room['name']
        })
        
    except Exception as e:
        print(f"❌ Error in /receive: {e}")
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
            "created_at": room['created_at']
        })
        
    except Exception as e:
        print(f"❌ Error in /room_info: {e}")
        return jsonify({"error": "Server error"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    print(f"🚀 Starting Flask server with CORS on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
