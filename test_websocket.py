import asyncio
import websockets

async def test_route(route):
    url = f"ws://localhost:8080{route}"
    try:
        async with websockets.connect(url, open_timeout=3) as ws:
            print(f"✅ {route} -> CONECTADO")
            return True
    except Exception as e:
        print(f"❌ {route} -> {type(e).__name__}: {e}")
        return False

async def main():
    routes = [
        "/showdown/websocket",
        "/websocket", 
        "/showdown",
        "/",
        "/api/websocket"
    ]
    print("🔍 Probando rutas WebSocket en localhost:8080...\n")
    for r in routes:
        await test_route(r)

if __name__ == "__main__":
    asyncio.run(main())
