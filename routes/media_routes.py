from flask import Blueprint, request, jsonify
from models.data_store import rooms

media_bp = Blueprint('media', __name__)

@media_bp.route('/media/<media_id>', methods=['GET'])
def get_media(media_id):
    try:
        # Ищем медиа во всех комнатах
        for room in rooms.values():
            if media_id in room['media']:
                return jsonify({
                    "media_id": media_id,
                    "data": room['media'][media_id]
                })
        
        return jsonify({"error": "Media not found"}), 404
        
    except Exception as e:
        print(f"❌ Error in /media: {e}")
        return jsonify({"error": "Server error"}), 500
