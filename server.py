from flask import Flask
from flask_cors import CORS
from config import Config
from routes import register_routes

def create_app():
    app = Flask(__name__)
    CORS(app)
    
    # Инициализация компонентов (этот код не нужен, так как модули уже импортируют data_store)
    # from security.bruteforce_protection import bruteforce_attempts
    # from models.data_store import rooms, user_rooms, call_signals, room_keys, encrypted_rooms, key_verification_attempts
    
    # Регистрация маршрутов
    register_routes(app)
    
    return app

if __name__ == '__main__':
    app = create_app()
    print("🚀 Starting Secure Chat Server...")
    print("🔐 Added bruteforce protection (10 attempts per 5 minutes)")
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
    print("🔐 Encryption features enabled")
    
    app.run(host='0.0.0.0', port=5000, debug=True)