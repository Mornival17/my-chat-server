from flask import Blueprint, request, jsonify
from models.data_store import rooms

reaction_bp = Blueprint('reaction', __name__)

@reaction_bp.route('/add_reaction', methods=['POST', 'OPTIONS'])
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

@reaction_bp.route('/remove_reaction', methods=['POST', 'OPTIONS'])
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

@reaction_bp.route('/get_reactions', methods=['GET'])
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
