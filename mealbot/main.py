import logging
import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from mealbot import org
from mealbot.auth import _AuthError, auth_error_handler
from mealbot.cors import setup_cors

logging.basicConfig(level=logging.DEBUG)

app = FastAPI(title="Mealbot API", version="1.0.0")

setup_cors(app)

# Register exception handler for auth errors
app.add_exception_handler(_AuthError, auth_error_handler)

# Include routers
app.include_router(org.router)

# Mount static files at root path to match Go behavior:
# Go serves http.FileServer(http.Dir("./static")) at "/"
# This means /privacy.html serves static/privacy.html
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
static_dir = os.path.join(_project_root, "static")
if os.path.isdir(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
