from .room_routes import room_bp
from .message_routes import message_bp
from .security_routes import security_bp
from .media_routes import media_bp
from .call_routes import call_bp
from .reaction_routes import reaction_bp

def register_routes(app):
    app.register_blueprint(room_bp)
    app.register_blueprint(message_bp)
    app.register_blueprint(security_bp)
    app.register_blueprint(media_bp)
    app.register_blueprint(call_bp)
    app.register_blueprint(reaction_bp)
