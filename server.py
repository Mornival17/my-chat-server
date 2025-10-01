import asyncio
import websockets
import json
import os
from aiohttp import web

# === HTTP СЕРВЕР ДЛЯ HEALTH CHECK ===
async def health_check(request):
    return web.Response(text="OK")

async def start_http_server():
    app = web.Application()
    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    # HTTP сервер на порту 8080
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    print("🌐 HTTP Health Check server running on port 8080")
    return runner

# === WEBSOCKET СЕРВЕР ===
connected_clients = set()
valid_tokens = {"secret_app_token_12345"}

async def websocket_handler(websocket, path):
    try:
        # Авторизация
        auth_data = await websocket.recv()
        auth = json.loads(auth_data)
        
        if auth.get('token') not in valid_tokens:
            await websocket.close(1008, "Invalid token")
            return
        
        connected_clients.add(websocket)
        username = auth.get('username', 'Anonymous')
        print(f"✅ {username} connected")
        
        # Приветствие
        await websocket.send(json.dumps({
            "type": "system", 
            "text": f"Welcome {username}!",
            "users": len(connected_clients)
        }))
        
        # Обработка сообщений
        async for message in websocket:
            data = json.loads(message)
            if data.get('type') == 'message':
                broadcast_msg = json.dumps({
                    "type": "message",
                    "from": username,
                    "text": data.get('text', ''),
                    "timestamp": data.get('timestamp')
                })
                
                # Рассылка всем
                disconnected = set()
                for client in connected_clients:
                    if client != websocket:  # Не отправляем отправителю
                        try:
                            await client.send(broadcast_msg)
                        except:
                            disconnected.add(client)
                connected_clients.difference_update(disconnected)
                
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
    finally:
        if websocket in connected_clients:
            connected_clients.remove(websocket)
            print(f"📤 User disconnected")

async def start_websocket_server():
    port = int(os.environ.get('PORT', 10000))
    server = await websockets.serve(websocket_handler, "0.0.0.0", port)
    print(f"🚀 WebSocket server running on port {port}")
    return server

# === ГЛАВНАЯ ФУНКЦИЯ ===
async def main():
    print("🔄 Starting servers...")
    
    # Запускаем оба сервера
    http_runner = await start_http_server()
    websocket_server = await start_websocket_server()
    
    print("✅ All servers are running!")
    print("📡 WebSocket: wss://mornival.onrender.com")
    print("🌐 Health check: https://mornival.onrender.com")
    
    # Бесконечный цикл
    await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
