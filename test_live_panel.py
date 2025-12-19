"""
Test Live Panel Routes
"""
import asyncio
from aiohttp import web
from pathlib import Path

async def test_routes():
    """Test if routes are working"""
    from web_panel_live import WebPanel
    
    panel = WebPanel(Path.cwd())
    app = web.Application()
    
    # Add routes
    app.router.add_get('/live', panel.handle_panel_html)
    app.router.add_get('/api/view-logs', panel.handle_view_logs)
    app.router.add_post('/api/terminal', panel.handle_terminal_command)
    
    print("✅ Routes registered successfully!")
    print("\nAvailable routes:")
    for route in app.router.routes():
        print(f"  {route.method:6} {route.resource.canonical}")
    
    print("\n🌐 Test URLs:")
    print("  http://localhost:8080/live")
    print("  http://localhost:8080/api/view-logs")
    
    # Start test server
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    
    print("\n🚀 Test server started on http://localhost:8080")
    print("   Open browser and test /live endpoint")
    print("\n   Press Ctrl+C to stop")
    
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped")

if __name__ == "__main__":
    asyncio.run(test_routes())
