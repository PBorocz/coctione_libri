"""WSGI entry point for production server."""
from app import create_app

app = create_app()
