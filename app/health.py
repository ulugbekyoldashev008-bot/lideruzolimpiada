import os

from aiohttp import web


async def healthcheck(_request):
    return web.json_response({"ok": True, "service": "olympiad-bot"})


async def start_health_server():
    port = os.getenv("PORT")
    if not port:
        return None

    app = web.Application()
    app.router.add_get("/", healthcheck)
    app.router.add_get("/health", healthcheck)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(port))
    await site.start()
    return runner
