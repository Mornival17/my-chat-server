import asyncio
import websockets
import json
import os
from aiohttp import web

# Храним подключенных клиентов
connected_clients = set()
valid_tokens = {"secret_app_token_12345"}

# HTTP обработчик для health check
async def handle_http(request):
    return web.Response(text="WebSocket Chat Server is Running! ✅")

# WebSocket обработчик
async def websocket_handler(websocket, path):
    try:
        # Ждем авторизацию
        auth_data = await websocket.recv()
        auth = json.loads(auth_data)
        
        if auth.get('token') not in valid_tokens:
            await websocket.close(1008, "Invalid token")
            return
        
        # Регистрируем клиента
        connected_clients.add(websocket)
        username = auth.get('username', 'Anonymous')
        print(f"✅ {username} connected")
        
        # Уведомляем о новом пользователе
        welcome_msg = json.dumps({
            "type": "system",
            "text": f"{username} joined the chat",
            "users": len(connected_clients)
        })
        await broadcast(welcome_msg, websocket)
        
        # Обрабатываем сообщения
        async for message in websocket:
            data = json.loads(message)
            if data.get('type') == 'message':
                chat_msg = json.dumps({
                    "type": "message",
                    "from": username,
                    "text": data.get('text', ''),
                    "timestamp": data.get('timestamp')
                })
                await broadcast(chat_msg, websocket)
                
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
    finally:
        # Удаляем клиента
        if websocket in connected_clients:
            connected_clients.remove(websocket)
            print(f"📤 User disconnected")

async def broadcast(message, sender=None):
    # Отправляем сообщение всем клиентам кроме отправителя
    disconnected = set()
    for client in connected_clients:
        if client != sender:  # Не отправляем обратно отправителю
            try:
                await client.send(message)
            except:
                disconnected.add(client)
    connected_clients.difference_update(disconnected)

async def start_websocket_server():
    port = int(os.environ.get('PORT', 10000))
    print(f"🚀 Starting WebSocket server on port {port}...")
    return await websockets.serve(websocket_handler, "0.0.0.0", port)

async def start_http_server():
    app = web.Application()
    app.router.add_get('/', handle_http)
    app.router.add_get('/health', handle_http)
    
    port = int(os.environ.get('PORT', 10000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"🌐 HTTP server running on port {port}")
    return runner

async def main():
    print("🔄 Starting servers...")
    
    # Запускаем оба сервера
    http_runner = await start_http_server()
    websocket_server = await start_websocket_server()
    
    print("✅ All servers are running!")
    print("📡 WebSocket URL: wss://your-app.onrender.com")
    print("🌐 HTTP URL: https://your-app.onrender.com")
    
    # Бесконечный цикл
    await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
