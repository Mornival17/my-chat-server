# security/hybrid_encryption.py
import base64
import secrets
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import os
import time

class HybridEncryption:
    def __init__(self):
        self.sessions = {}
    
    def generate_session_key(self):
        """Генерируем случайный сессионный ключ для AES"""
        return secrets.token_bytes(32)  # 256-bit AES key
    
    def derive_key_from_password(self, password, salt=None):
        """Производный ключ из пароля для дополнительной защиты"""
        salt = salt or secrets.token_bytes(16)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = kdf.derive(password.encode('utf-8'))
        return key, salt
    
    def encrypt_with_aes(self, data, key):
        """Шифруем данные с помощью AES-GCM"""
        iv = secrets.token_bytes(12)  # 96-bit IV для GCM
        cipher = Cipher(algorithms.AES(key), modes.GCM(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        
        encrypted_data = encryptor.update(data) + encryptor.finalize()
        
        return {
            'encrypted_data': base64.b64encode(encrypted_data).decode('utf-8'),
            'iv': base64.b64encode(iv).decode('utf-8'),
            'tag': base64.b64encode(encryptor.tag).decode('utf-8')
        }
    
    def decrypt_with_aes(self, encrypted_package, key):
        """Дешифруем данные с помощью AES-GCM"""
        try:
            encrypted_data = base64.b64decode(encrypted_package['encrypted_data'])
            iv = base64.b64decode(encrypted_package['iv'])
            tag = base64.b64decode(encrypted_package['tag'])
            
            cipher = Cipher(algorithms.AES(key), modes.GCM(iv, tag), backend=default_backend())
            decryptor = cipher.decryptor()
            
            decrypted_data = decryptor.update(encrypted_data) + decryptor.finalize()
            return decrypted_data
        except Exception as e:
            print(f"❌ Decryption error: {e}")
            return None
    
    def create_hybrid_package(self, plaintext, public_key_info=None):
        """Создаем гибридный зашифрованный пакет"""
        # Генерируем сессионный ключ
        session_key = self.generate_session_key()
        
        # Шифруем данные с помощью AES
        encrypted_package = self.encrypt_with_aes(
            plaintext.encode('utf-8') if isinstance(plaintext, str) else plaintext,
            session_key
        )
        
        # В реальной системе здесь бы мы зашифровали session_key с помощью RSA публичного ключа
        # Для демо просто кодируем его в base64
        encrypted_package['encrypted_session_key'] = base64.b64encode(session_key).decode('utf-8')
        encrypted_package['timestamp'] = time.time()
        
        return encrypted_package
    
    def decrypt_hybrid_package(self, encrypted_package, private_key_info=None):
        """Дешифруем гибридный зашифрованный пакет"""
        try:
            # В реальной системе здесь бы мы дешифровали session_key с помощью RSA приватного ключа
            # Для демо просто декодируем из base64
            session_key = base64.b64decode(encrypted_package['encrypted_session_key'])
            
            # Дешифруем данные с помощью AES
            decrypted_data = self.decrypt_with_aes(encrypted_package, session_key)
            
            if decrypted_data:
                return decrypted_data.decode('utf-8')
            return None
        except Exception as e:
            print(f"❌ Hybrid decryption error: {e}")
            return None
    
    def validate_encryption_package(self, package):
        """Валидируем структуру зашифрованного пакета"""
        required_fields = ['encrypted_data', 'iv', 'tag', 'encrypted_session_key']
        return all(field in package for field in required_fields)

# Глобальный экземпляр гибридного шифрования
hybrid_encryption = HybridEncryption()
