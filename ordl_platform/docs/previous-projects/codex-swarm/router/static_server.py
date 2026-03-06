"""Static file serving for Web IDE"""
from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import os

STATIC_DIR = "/var/www/supreme-ide"

def setup_static_routes(app: FastAPI):
    """Add static file routes to FastAPI app."""
    
    @app.get("/", response_class=HTMLResponse)
    async def serve_ide():
        """Serve the Web IDE."""
        html_file = os.path.join(STATIC_DIR, "index.html")
        if os.path.exists(html_file):
            with open(html_file) as f:
                return f.read()
        return HTMLResponse(content="<h1>SUPREME IDE</h1><p>Frontend not installed</p>", status_code=200)
    
    @app.get("/ide")
    async def redirect_to_ide():
        """Redirect /ide to root."""
        return await serve_ide()
