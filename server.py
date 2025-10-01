from flask import Flask, request, jsonify
from datetime import datetime
import os
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Разрешаем все CORS запросы

# Глобальные переменные для хранения данных
chat_data = {
    'messages': [],
    'users': set(),
    'next_id': 1
}

@app.route('/')
def home():
    return "🚀 Chat Server Ready! Use /send and /receive"

@app.route('/health')
def health():
    return "OK"

@app.route('/send', methods=['POST', 'OPTIONS'])
def send_message():
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.get_json()
        
        if not data or data.get('token') != 'secret_app_token_12345':
            return jsonify({"error": "Invalid token"}), 401
        
        username = data.get('username', 'Anonymous')
        text = data.get('text', '').strip()
        
        if not text:
            return jsonify({"error": "Empty message"}), 400
        
        # Создаем сообщение
        message = {
            'id': chat_data['next_id'],
            'user': username,
            'text': text,
            'time': datetime.now().isoformat()
        }
        
        # Сохраняем
        chat_data['messages'].append(message)
        chat_data['users'].add(username)
        chat_data['next_id'] += 1
        
        # Лимит сообщений (последние 100)
        if len(chat_data['messages']) > 100:
            chat_data['messages'] = chat_data['messages'][-100:]
        
        print(f"📨 Message saved: {username}: {text}")
        return jsonify({"status": "sent", "message_id": message['id']})
        
    except Exception as e:
        print(f"❌ Error in /send: {e}")
        return jsonify({"error": "Server error"}), 500

@app.route('/receive', methods=['GET'])
def receive_messages():
    try:
        token = request.args.get('token')
        
        if token != 'secret_app_token_12345':
            return jsonify({"error": "Invalid token"}), 401
        
        since_id = int(request.args.get('since_id', 0))
        
        # Фильтруем сообщения
        new_messages = [
            msg for msg in chat_data['messages'] 
            if msg['id'] > since_id
        ]
        
        print(f"📤 Sending {len(new_messages)} new messages")
        return jsonify({
            "messages": new_messages,
            "users": list(chat_data['users'])
        })
        
    except Exception as e:
        print(f"❌ Error in /receive: {e}")
        return jsonify({"error": "Server error"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    print(f"🚀 Starting Flask server with CORS on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
