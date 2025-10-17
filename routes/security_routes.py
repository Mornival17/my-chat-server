from flask import Blueprint, request, jsonify
from datetime import datetime
from models.data_store import rooms, user_rooms, room_keys, encrypted_rooms, key_verification_attempts, call_signals
from security.encryption import verify_encryption_key
from utils.helpers import get_current_time
from config import Config

security_bp = Blueprint('security', __name__)


@security_bp.route('/verify_key', methods=['POST', 'OPTIONS'])
def verify_key():
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.get_json()
        room_id = data.get('room_id')
        username = data.get('username')
        public_key = data.get('public_key')
        challenge_response = data.get('challenge_response')
        
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

@security_bp.route('/room_encryption_info', methods=['GET'])
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
            "users_count": len(room['users']),
            "created_at": room['created_at'],
            "encryption_enabled_at": room.get('encryption_enabled_at'),
            "security_level": "high" if room['is_encrypted'] else "standard"
        })
        
    except Exception as e:
        print(f"❌ Error in /room_encryption_info: {e}")
        return jsonify({"error": "Server error"}), 500

@security_bp.route('/room_info', methods=['GET'])
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
            "security_level": "🔒 Encrypted" if room['is_encrypted'] else "🔓 Standard",
            "security_description": "End-to-end encrypted" if room['is_encrypted'] else "Standard security"
        })
        
    except Exception as e:
        print(f"❌ Error in /room_info: {e}")
        return jsonify({"error": "Server error"}), 500

@security_bp.route('/stats')
def get_stats():
    """Получение статистики сервера"""
    try:
        total_rooms = len(rooms)
        encrypted_rooms_count = len([r for r in rooms.values() if r['is_encrypted']])
        total_users = len(user_rooms)
        total_messages = sum(len(room['messages']) for room in rooms.values())
        total_reactions = sum(len(reactions) for room in rooms.values() for reactions in room['reactions'].values())
        
        # Активные комнаты (с пользователями)
        active_rooms = {room_id: room for room_id, room in rooms.items() if len(room['users']) > 0}
        active_encrypted_rooms = len([r for r in active_rooms.values() if r['is_encrypted']])
        
        # 🔐 Статистика по шифрованию
        encrypted_messages = sum(
            len([m for m in room['messages'] if m.get('is_encrypted')]) 
            for room in rooms.values() 
            if room['is_encrypted']
        )
        
        return jsonify({
            "total_rooms": total_rooms,
            "encrypted_rooms": encrypted_rooms_count,
            "standard_rooms": total_rooms - encrypted_rooms_count,
            "active_rooms": len(active_rooms),
            "active_encrypted_rooms": active_encrypted_rooms,
            "total_users": total_users,
            "total_messages": total_messages,
            "encrypted_messages": encrypted_messages,
            "total_reactions": total_reactions,
            "pending_call_signals": sum(len(signals) for signals in call_signals.values()),
            "server_time": get_current_time(),
            "security_summary": {
                "encrypted_percentage": round((encrypted_rooms_count / total_rooms * 100) if total_rooms > 0 else 0, 1),
                "encrypted_messages_percentage": round((encrypted_messages / total_messages * 100) if total_messages > 0 else 0, 1),
                "recommendation": "🔒 Enable encryption for sensitive conversations"
            }
        })
        
    except Exception as e:
        print(f"❌ Error in /stats: {e}")
        return jsonify({"error": "Server error"}), 500

@security_bp.route('/cleanup', methods=['POST'])
def cleanup_rooms():
    """Очистка комнат старше 24 часов"""
    try:
        current_time = datetime.now()
        rooms_to_delete = []
        
        # Находим комнаты старше 24 часов
        for room_id, room in rooms.items():
            created_at = datetime.fromisoformat(room['created_at'])
            if (current_time - created_at).total_seconds() > Config.ROOM_CLEANUP_HOURS * 60 * 60:
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
        
        return jsonify({
            "status": "cleaned",
            "deleted_rooms": len(rooms_to_delete),
            "active_rooms": len(rooms),
            "remaining_encrypted_rooms": len(encrypted_rooms),
            "cleaned_verification_attempts": len(rooms_to_delete)
        })
        
    except Exception as e:
        print(f"❌ Error in /cleanup: {e}")
        return jsonify({"error": "Server error"}), 500
