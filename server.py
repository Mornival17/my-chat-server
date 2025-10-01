from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

messages = []
users = set()

@app.route('/')
def home():
    return "🚀 Chat Server Ready! Use /send and /receive"

@app.route('/health')
def health():
    return "OK"

@app.route('/send', methods=['POST'])
def send_message():
    data = request.json
    
    if data.get('token') != 'secret_app_token_12345':
        return jsonify({"error": "Invalid token"}), 401
    
    message = {
        'id': len(messages) + 1,
        'user': data.get('username', 'Anonymous'),
        'text': data.get('text', ''),
        'time': datetime.now().isoformat()
    }
    
    messages.append(message)
    users.add(data.get('username', 'Anonymous'))
    
    if len(messages) > 100:
        messages.pop(0)
    
    return jsonify({"status": "sent", "message_id": message['id']})

@app.route('/receive', methods=['GET'])
def receive_messages():
    token = request.args.get('token')
    
    if token != 'secret_app_token_12345':
        return jsonify({"error": "Invalid token"}), 401
    
    since_id = int(request.args.get('since_id', 0))
    new_messages = [msg for msg in messages if msg['id'] > since_id]
    
    return jsonify({
        "messages": new_messages,
        "users": list(users)
    })

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
