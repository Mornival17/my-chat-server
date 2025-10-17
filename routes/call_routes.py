from flask import Blueprint, request, jsonify
from models.data_store import call_signals
from utils.helpers import get_current_time

call_bp = Blueprint('call', __name__)

@call_bp.route('/call_signal', methods=['POST', 'OPTIONS'])
def call_signal():
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.get_json()
        from_user = data.get('from_user')
        to_user = data.get('to_user')
        signal_type = data.get('type')
        signal_data = data.get('data')
        
        if not all([from_user, to_user, signal_type, signal_data]):
            return jsonify({"error": "Missing required fields"}), 400
        
        if to_user not in call_signals:
            call_signals[to_user] = []
        
        call_signals[to_user].append({
            'from_user': from_user,
            'type': signal_type,
            'data': signal_data,
            'timestamp': get_current_time()
        })
        
        print(f"📞 Call signal from {from_user} to {to_user}: {signal_type}")
        
        return jsonify({"status": "signal_sent"})
        
    except Exception as e:
        print(f"❌ Error in /call_signal: {e}")
        return jsonify({"error": "Server error"}), 500

@call_bp.route('/get_call_signals', methods=['GET'])
def get_call_signals():
    try:
        username = request.args.get('username')
        
        if not username:
            return jsonify({"error": "Username is required"}), 400
        
        signals = call_signals.get(username, [])
        call_signals[username] = []
        
        return jsonify({
            "signals": signals
        })
        
    except Exception as e:
        print(f"❌ Error in /get_call_signals: {e}")
        return jsonify({"error": "Server error"}), 500
