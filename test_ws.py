import asyncio, websockets

async def test(route):
    url = f"ws://localhost:8080{route}"
    try:
        async with websockets.connect(url, open_timeout=3) as ws:
            print(f"✅ {route} -> CONECTADO")
            return True
    except Exception as e:
        print(f"❌ {route} -> {type(e).__name__}")
        return False

async def main():
    for r in ["/showdown/websocket", "/websocket", "/showdown", "/"]:
        await test(r)

asyncio.run(main())
