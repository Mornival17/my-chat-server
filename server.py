import asyncio
import websockets
import json
import os
from aiohttp import web

# HTTP сервер для health check
async def handle_health_check(request):
    return web.Response(text="Chat Server OK")

async def start_http_server():
    app = web.Application()
    app.router.add_get('/', handle_health_check)
    app.router.add_get('/health', handle_health_check)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    # HTTP сервер на порту 8080
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    print("🌐 HTTP server running on port 8080")
    return runner

# WebSocket сервер
connected_clients = set()
valid_tokens = {"secret_app_token_12345"}

async def websocket_handler(websocket, path):
    try:
        # Ждем авторизацию
        auth_data = await websocket.recv()
        auth = json.loads(auth_data)
        
        if auth.get('token') not in valid_tokens:
            await websocket.close(1008, "Invalid token")
            return
        
        connected_clients.add(websocket)
        username = auth.get('username', 'Anonymous')
        print(f"✅ {username} connected")
        
        # Отправляем приветствие
        await websocket.send(json.dumps({
            "type": "system",
            "text": f"Welcome {username}!",
            "users": len(connected_clients)
        }))
        
        # Обрабатываем сообщения
        async for message in websocket:
            data = json.loads(message)
            if data.get('type') == 'message':
                # Отправляем всем клиентам
                broadcast_msg = json.dumps({
                    "type": "message",
                    "from": username,
                    "text": data.get('text', ''),
                    "timestamp": data.get('timestamp')
                })
                
                disconnected = set()
                for client in connected_clients:
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

async def main():
    print("🔄 Starting servers...")
    
    # Запускаем оба сервера
    http_runner = await start_http_server()
    websocket_server = await start_websocket_server()
    
    print("✅ All servers are running!")
    print("📡 WebSocket URL: wss://mornival.onrender.com")
    print("🌐 Health check: https://mornival.onrender.com")
    
    # Бесконечный цикл
    await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
