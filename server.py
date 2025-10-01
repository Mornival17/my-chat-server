from flask import Flask, request, jsonify
import sqlite3
import datetime
import threading
import time

app = Flask(__name__)

# Инициализация БД
def init_db():
    conn = sqlite3.connect('chat.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS messages
                 (id INTEGER PRIMARY KEY, 
                  username TEXT, 
                  text TEXT, 
                  timestamp TEXT)''')
    conn.commit()
    conn.close()

init_db()

# Храним последние сообщения (в памяти для скорости)
recent_messages = []
connected_clients = set()

@app.route('/')
def home():
    return "Chat Server is Running! ✅"

@app.route('/health')
def health():
    return "OK"

@app.route('/send', methods=['POST'])
def send_message():
    data = request.json
    
    # Проверка токена
    if data.get('token') != 'secret_app_token_12345':
        return jsonify({"error": "Invalid token"}), 401
    
    # Сохраняем в БД
    conn = sqlite3.connect('chat.db')
    c = conn.cursor()
    c.execute("INSERT INTO messages (username, text, timestamp) VALUES (?, ?, ?)",
              (data['username'], data['text'], datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()
    
    # Добавляем в память
    message = {
        'id': len(recent_messages) + 1,
        'username': data['username'],
        'text': data['text'],
        'timestamp': datetime.datetime.now().isoformat()
    }
    recent_messages.append(message)
    
    # Держим только последние 100 сообщений
    if len(recent_messages) > 100:
        recent_messages.pop(0)
    
    return jsonify({"status": "sent", "id": message['id']})

@app.route('/messages', methods=['GET'])
def get_messages():
    token = request.args.get('token')
    
    if token != 'secret_app_token_12345':
        return jsonify({"error": "Invalid token"}), 401
    
    # Возвращаем последние 50 сообщений
    return jsonify({"messages": recent_messages[-50:]})

@app.route('/poll', methods=['GET'])
def poll_messages():
    token = request.args.get('token')
    last_id = int(request.args.get('last_id', 0))
    
    if token != 'secret_app_token_12345':
        return jsonify({"error": "Invalid token"}), 401
    
    # Ждем новые сообщения (лонг-поллинг)
    for i in range(30):  # 30 секунд максимум
        new_messages = [msg for msg in recent_messages if msg['id'] > last_id]
        if new_messages:
            return jsonify({"messages": new_messages})
        time.sleep(1)
    
    return jsonify({"messages": []})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
