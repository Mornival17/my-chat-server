def verify_encryption_key(room_id, user_public_key, verification_data):
    """🔐 Проверка ключа шифрования"""
    try:
        # В реальной системе здесь должна быть сложная проверка
        # Для демо - просто проверяем что ключ предоставлен и имеет правильный формат
        if not user_public_key or len(user_public_key) < 100:
            return False
            
        # Проверяем что публичный ключ комнаты существует
        from models.data_store import room_keys
        if room_id not in room_keys:
            return False
            
        # Здесь можно добавить реальную криптографическую проверку
        
        print(f"🔐 Key verification for room {room_id}: SUCCESS")
        return True
        
    except Exception as e:
        print(f"❌ Key verification error: {e}")
        return False
