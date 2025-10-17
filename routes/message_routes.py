from flask import Blueprint, request, jsonify
import uuid
from datetime import datetime
from utils.helpers import get_current_time
from models.data_store import rooms, user_rooms
from config import Config

message_bp = Blueprint('message', __name__)

@message_bp.route('/send', methods=['POST', 'OPTIONS'])
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
            'time': get_current_time(),
            'reply_to': reply_to,
            'self_destruct': self_destruct,
            # 🔐 Новые поля для шифрования
            'is_encrypted': is_encrypted_payload,
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
        if len(room['messages']) > Config.MESSAGE_LIMIT:
            # Удаляем также медиафайлы и реакции старых сообщений
            removed_messages = room['messages'][:-Config.MESSAGE_LIMIT]
            for msg in removed_messages:
                # Удаляем медиа
                if 'image_id' in msg and msg['image_id'] in room['media']:
                    del room['media'][msg['image_id']]
                if 'audio_id' in msg and msg['audio_id'] in room['media']:
                    del room['media'][msg['audio_id']]
                # Удаляем реакции
                if msg['id'] in room['reactions']:
                    del room['reactions'][msg['id']]
            room['messages'] = room['messages'][-Config.MESSAGE_LIMIT:]
        
        print(f"📨 Message in room {room_id}: {username}: {text[:50]}... (type: {message_type}, reply_to: {reply_to})")
        print(f"🔐 Encrypted: {is_encrypted_payload}")
        
        # Формируем ответ
        response_data = {
            "status": "sent", 
            "message_id": message['id'],
            "is_encrypted": is_encrypted_payload
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

@message_bp.route('/receive', methods=['GET'])
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
                    # Не показываем исходный текст, только зашифрованные данные
                    msg['text'] = '🔒 Encrypted message'
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
            "public_key": room.get('public_key')
        })
        
    except Exception as e:
        print(f"❌ Error in /receive: {e}")
        return jsonify({"error": "Server error"}), 500
