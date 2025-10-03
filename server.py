from flask import Flask, request, jsonify
from datetime import datetime
import os
import secrets
import uuid
from flask_cors import CORS

# Создаем Flask приложение
app = Flask(__name__)
# Разрешаем все CORS запросы (чтобы фронтенд мог общаться с сервером)
CORS(app)

# Глобальные переменные для хранения данных

# rooms хранит информацию о всех комнатах
# Формат: {room_id: {name: str, password: str, created_at: str, users: set, messages: [], next_id: int, media: {}, reactions: {}}}
rooms = {}

# user_rooms хранит связь пользователь -> комната
# Формат: {username: room_id}
user_rooms = {}

# call_signals хранит сигналы звонков для пользователей
# Формат: {username: [list_of_signals]}
call_signals = {}

def generate_room_id():
    """Генерация уникального ID комнаты"""
    return secrets.token_urlsafe(8)

# Базовые endpoint'ы
@app.route('/')
def home():
    return "🚀 Chat Server Ready! Use /create_room, /join_room, /send and /receive"

@app.route('/health')
def health():
    return "OK"

# Создание комнаты
@app.route('/create_room', methods=['POST', 'OPTIONS'])
def create_room():
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        # Получаем данные из запроса
        data = request.get_json()
        room_name = data.get('room_name', 'New Room')
        password = data.get('password', '')
        username = data.get('username', 'Host')
        
        # Генерируем уникальный ID комнаты
        room_id = generate_room_id()
        
        # Создаем комнату со всей необходимой информацией
        rooms[room_id] = {
            'name': room_name,                    # Название комнаты
            'password': password,                 # Пароль (может быть пустым)
            'created_at': datetime.now().isoformat(),  # Время создания
            'users': set([username]),             # Множество пользователей
            'messages': [],                       # Список сообщений
            'next_id': 1,                         # Следующий ID сообщения
            'media': {},                          # Хранилище медиафайлов
            'reactions': {}                       # Хранилище реакций: {message_id: {emoji: [usernames]}}
        }
        
        # Связываем пользователя с комнатой
        user_rooms[username] = room_id
        
        print(f"🎉 Room created: {room_name} (ID: {room_id}) by {username}")
        
        # Возвращаем успешный ответ
        return jsonify({
            "status": "created", 
            "room_id": room_id,
            "room_name": room_name
        })
        
    except Exception as e:
        print(f"❌ Error in /create_room: {e}")
        return jsonify({"error": "Server error"}), 500

# Присоединение к комнате
@app.route('/join_room', methods=['POST', 'OPTIONS'])
def join_room():
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.get_json()
        room_id = data.get('room_id')
        password = data.get('password', '')
        username = data.get('username', 'Anonymous')
        
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
        
        return jsonify({
            "status": "joined",
            "room_name": room['name'],
            "users": list(room['users'])
        })
        
    except Exception as e:
        print(f"❌ Error in /join_room: {e}")
        return jsonify({"error": "Server error"}), 500

# Отправка сообщений
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
        reply_to = data.get('reply_to')  # ID сообщения, на которое отвечаем
        self_destruct = data.get('self_destruct', False)  # Самоуничтожающееся сообщение
        
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
        
        # Для медиа-сообщений текст может быть пустым
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
            'reply_to': reply_to,  # Добавляем информацию о reply
            'self_destruct': self_destruct  # Добавляем флаг самоуничтожения
        }
        
        # Сохраняем медиаданные если они есть
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
        
        print(f"📨 Message in room {room_id}: {username}: {text[:50]}... (type: {message_type}, reply_to: {reply_to})")
        
        # Формируем ответ
        response_data = {
            "status": "sent", 
            "message_id": message['id']
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

# Получение сообщений
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
        
        # Добавляем медиаданные к сообщениям
        for msg in new_messages:
            if 'image_id' in msg and msg['image_id'] in room['media']:
                msg['image_data'] = room['media'][msg['image_id']]
            if 'audio_id' in msg and msg['audio_id'] in room['media']:
                msg['audio_data'] = room['media'][msg['audio_id']]
            
            # Добавляем реакции к сообщениям
            if msg['id'] in room['reactions']:
                msg['reactions'] = room['reactions'][msg['id']]
        
        print(f"📤 Sending {len(new_messages)} new messages from room {room_id} to {username}")
        
        return jsonify({
            "messages": new_messages,
            "users": list(room['users']),
            "room_name": room['name'],
            "reactions": room['reactions']  # Отправляем все реакции комнаты
        })
        
    except Exception as e:
        print(f"❌ Error in /receive: {e}")
        return jsonify({"error": "Server error"}), 500

# Добавление реакции к сообщению
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
        
        # Проверяем обязательные поля
        if not all([message_id, username, emoji, room_id]):
            return jsonify({"error": "Missing required fields"}), 400
            
        # Проверяем что комната существует
        if room_id not in rooms:
            return jsonify({"error": "Room not found"}), 404
            
        room = rooms[room_id]
        
        # Проверяем что сообщение существует
        message_exists = any(msg['id'] == message_id for msg in room['messages'])
        if not message_exists:
            return jsonify({"error": "Message not found"}), 404
            
        # Проверяем что пользователь находится в этой комнате
        if username not in room['users']:
            return jsonify({"error": "User not in room"}), 403
        
        # Инициализируем хранилище реакций для сообщения если его нет
        if message_id not in room['reactions']:
            room['reactions'][message_id] = {}
        
        # Инициализируем список пользователей для эмодзи если его нет
        if emoji not in room['reactions'][message_id]:
            room['reactions'][message_id][emoji] = []
        
        # Добавляем пользователя в реакцию если его там еще нет
        if username not in room['reactions'][message_id][emoji]:
            room['reactions'][message_id][emoji].append(username)
            print(f"✅ Reaction added: {username} reacted with {emoji} to message {message_id}")
        else:
            print(f"ℹ️ User {username} already reacted with {emoji} to message {message_id}")
        
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

# Удаление реакции с сообщения
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
        
        # Проверяем обязательные поля
        if not all([message_id, username, emoji, room_id]):
            return jsonify({"error": "Missing required fields"}), 400
            
        # Проверяем что комната существует
        if room_id not in rooms:
            return jsonify({"error": "Room not found"}), 404
            
        room = rooms[room_id]
        
        # Проверяем что сообщение существует
        message_exists = any(msg['id'] == message_id for msg in room['messages'])
        if not message_exists:
            return jsonify({"error": "Message not found"}), 404
            
        # Проверяем что пользователь находится в этой комнате
        if username not in room['users']:
            return jsonify({"error": "User not in room"}), 403
        
        # Проверяем что реакция существует
        if (message_id not in room['reactions'] or 
            emoji not in room['reactions'][message_id] or
            username not in room['reactions'][message_id][emoji]):
            return jsonify({"error": "Reaction not found"}), 404
        
        # Удаляем пользователя из реакции
        room['reactions'][message_id][emoji].remove(username)
        
        # Если после удаления список пользователей пуст, удаляем эмодзи
        if not room['reactions'][message_id][emoji]:
            del room['reactions'][message_id][emoji]
        
        # Если после удаления сообщение не имеет реакций, удаляем запись
        if not room['reactions'][message_id]:
            del room['reactions'][message_id]
        
        print(f"🗑️ Reaction removed: {username} removed {emoji} from message {message_id}")
        
        return jsonify({
            "status": "reaction_removed",
            "message_id": message_id,
            "emoji": emoji,
            "username": username
        })
        
    except Exception as e:
        print(f"❌ Error in /remove_reaction: {e}")
        return jsonify({"error": "Server error"}), 500

# Получение реакций для сообщения
@app.route('/get_reactions', methods=['GET'])
def get_reactions():
    try:
        room_id = request.args.get('room_id')
        message_id = int(request.args.get('message_id'))
        
        if not room_id or not message_id:
            return jsonify({"error": "Room ID and Message ID are required"}), 400
            
        if room_id not in rooms:
            return jsonify({"error": "Room not found"}), 404
            
        room = rooms[room_id]
        
        # Возвращаем реакции для сообщения или пустой объект
        reactions = room['reactions'].get(message_id, {})
        
        return jsonify({
            "message_id": message_id,
            "reactions": reactions
        })
        
    except Exception as e:
        print(f"❌ Error in /get_reactions: {e}")
        return jsonify({"error": "Server error"}), 500

# Получение медиафайлов (альтернативный способ)
@app.route('/media/<room_id>/<media_id>')
def get_media(room_id, media_id):
    """Эндпоинт для получения медиафайлов по отдельности"""
    try:
        if room_id not in rooms:
            return jsonify({"error": "Room not found"}), 404
            
        room = rooms[room_id]
        
        if media_id not in room['media']:
            return jsonify({"error": "Media not found"}), 404
            
        media_data = room['media'][media_id]
        
        # Определяем тип контента по префиксу data URL
        if media_data.startswith('data:image'):
            return jsonify({"data": media_data})
        elif media_data.startswith('data:audio'):
            return jsonify({"data": media_data})
        else:
            return jsonify({"error": "Unknown media type"}), 400
            
    except Exception as e:
        print(f"❌ Error in /media: {e}")
        return jsonify({"error": "Server error"}), 500

# Информация о комнате
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

# Система звонков - обработка сигналов
@app.route('/call_signal', methods=['POST', 'OPTIONS'])
def handle_call_signal():
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.get_json()
        signal_type = data.get('type')
        target_user = data.get('target_user')
        room_id = data.get('room_id')
        caller = data.get('caller')
        
        print(f"📞 Call signal: {signal_type} from {caller} to {target_user} in room {room_id}")
        
        # Проверяем что целевой пользователь существует и находится в той же комнате
        if (target_user not in user_rooms or 
            user_rooms[target_user] != room_id or
            target_user == caller):
            return jsonify({"error": "Target user not available"}), 404
        
        # Создаем очередь сигналов для пользователя если её нет
        if target_user not in call_signals:
            call_signals[target_user] = []
        
        # Создаем объект сигнала
        signal_data = {
            'type': signal_type,
            'caller': caller,
            'room_id': room_id,
            'timestamp': datetime.now().isoformat()
        }
        
        # Добавляем специфичные данные в зависимости от типа сигнала
        if signal_type == 'call-offer':
            signal_data['offer'] = data.get('offer')
        elif signal_type == 'call-answer':
            signal_data['answer'] = data.get('answer')
        elif signal_type == 'ice-candidate':
            signal_data['candidate'] = data.get('candidate')
        
        # Добавляем сигнал в очередь целевого пользователя
        call_signals[target_user].append(signal_data)
        
        # Ограничиваем размер очереди сигналов
        if len(call_signals[target_user]) > 10:
            call_signals[target_user] = call_signals[target_user][-10:]
        
        print(f"✅ Call signal stored for {target_user}. Queue size: {len(call_signals[target_user])}")
        
        return jsonify({
            "status": "signal_delivered",
            "target_user": target_user
        })
        
    except Exception as e:
        print(f"❌ Error in /call_signal: {e}")
        return jsonify({"error": "Server error"}), 500

# Получение сигналов звонков
@app.route('/get_call_signals', methods=['GET'])
def get_call_signals():
    try:
        username = request.args.get('username')
        
        if not username:
            return jsonify({"error": "Username is required"}), 400
        
        # Получаем все сигналы для пользователя
        user_signals = call_signals.get(username, [])
        
        # Очищаем очередь после чтения (сигналы доставляются один раз)
        if username in call_signals:
            call_signals[username] = []
        
        print(f"📡 Sending {len(user_signals)} call signals to {username}")
        
        return jsonify({
            "signals": user_signals
        })
        
    except Exception as e:
        print(f"❌ Error in /get_call_signals: {e}")
        return jsonify({"error": "Server error"}), 500

# Завершение звонка
@app.route('/end_call', methods=['POST'])
def handle_end_call():
    try:
        data = request.get_json()
        target_user = data.get('target_user')
        caller = data.get('caller')
        room_id = data.get('room_id')
        
        print(f"📞 Call ended: {caller} to {target_user}")
        
        # Отправляем сигнал завершения целевому пользователю
        if target_user and target_user in call_signals:
            end_signal = {
                'type': 'call-end',
                'caller': caller,
                'room_id': room_id,
                'timestamp': datetime.now().isoformat()
            }
            call_signals[target_user].append(end_signal)
        
        return jsonify({"status": "call_ended"})
        
    except Exception as e:
        print(f"❌ Error in /end_call: {e}")
        return jsonify({"error": "Server error"}), 500

# Очистка старых комнат (для обслуживания)
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

# Статистика сервера
@app.route('/stats')
def get_stats():
    """Получение статистики сервера"""
    try:
        total_rooms = len(rooms)
        total_users = len(user_rooms)
        total_messages = sum(len(room['messages']) for room in rooms.values())
        total_reactions = sum(len(reactions) for room in rooms.values() for reactions in room['reactions'].values())
        
        # Активные комнаты (с пользователями)
        active_rooms = {room_id: room for room_id, room in rooms.items() if len(room['users']) > 0}
        
        return jsonify({
            "total_rooms": total_rooms,
            "active_rooms": len(active_rooms),
            "total_users": total_users,
            "total_messages": total_messages,
            "total_reactions": total_reactions,
            "pending_call_signals": sum(len(signals) for signals in call_signals.values()),
            "server_time": datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"❌ Error in /stats: {e}")
        return jsonify({"error": "Server error"}), 500

# Запуск сервера
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    print(f"🚀 Starting Flask server with CORS on port {port}")
    print(f"📊 Available endpoints:")
    print(f"   POST /create_room - Create new room")
    print(f"   POST /join_room - Join existing room") 
    print(f"   POST /send - Send message")
    print(f"   GET  /receive - Receive messages")
    print(f"   POST /add_reaction - Add reaction to message")
    print(f"   POST /remove_reaction - Remove reaction from message")
    print(f"   GET  /get_reactions - Get reactions for message")
    print(f"   GET  /room_info - Get room info")
    print(f"   POST /call_signal - Send call signal")
    print(f"   GET  /get_call_signals - Get pending call signals")
    print(f"   POST /end_call - End call")
    print(f"   GET  /stats - Server statistics")
    print(f"   POST /cleanup - Cleanup old rooms")
    app.run(host='0.0.0.0', port=port, debug=False)