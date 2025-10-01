import asyncio
import websockets
import json
import secrets
import os

connected_clients = {}
valid_tokens = {"secret_app_token_12345"}

async def handle_client(websocket, path):
    try:
        auth_data = await websocket.recv()
        auth = json.loads(auth_data)
        
        if auth.get('token') not in valid_tokens:
            await websocket.send(json.dumps({"error": "Invalid token"}))
            await websocket.close()
            return
        
        client_id = secrets.token_hex(8)
        connected_clients[client_id] = {
            'websocket': websocket,
            'username': auth.get('username', 'Anonymous')
        }
        
        print(f"Client {client_id} connected")
        
        online_users = [client['username'] for client in connected_clients.values()]
        broadcast_message = {
            'type': 'user_list',
            'users': online_users
        }
        await broadcast(json.dumps(broadcast_message))
        
        async for message in websocket:
            data = json.loads(message)
            if data['type'] == 'message':
                chat_message = {
                    'type': 'message',
                    'from': connected_clients[client_id]['username'],
                    'text': data['text'],
                    'timestamp': data.get('timestamp')
                }
                await broadcast(json.dumps(chat_message))
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if client_id in connected_clients:
            del connected_clients[client_id]
            online_users = [client['username'] for client in connected_clients.values()]
            broadcast_message = {
                'type': 'user_list',
                'users': online_users
            }
            await broadcast(json.dumps(broadcast_message))

async def broadcast(message):
    disconnected = []
    for client_id, client in connected_clients.items():
        try:
            await client['websocket'].send(message)
        except:
            disconnected.append(client_id)
    for client_id in disconnected:
        if client_id in connected_clients:
            del connected_clients[client_id]

async def main():
    port = int(os.environ.get("PORT", 8765))
    server = await websockets.serve(handle_client, "0.0.0.0", port)
    print(f"Chat server running on port {port}")
    await server.wait_forever()

if __name__ == "__main__":
    asyncio.run(main())
