"""
SmartServe GIS - Frontend Static HTTP Server Launcher
Serves the WebGIS frontend at http://127.0.0.1:5500 with proper MIME types.
"""

import http.server
import socketserver
import os
import sys
import webbrowser

PORT = 5500
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        # Enable CORS and disable caching during development
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()

def main():
    print("=" * 70)
    print("  SMARTSERVE GIS - WEBGIS FRONTEND PORTAL")
    print("  Pune & Pimpri-Chinchwad Multi-Service Spatial Platform")
    print("=" * 70)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(f"\n[INFO] Serving frontend files from: {DIRECTORY}")
    print(f"[SUCCESS] Frontend URL: http://127.0.0.1:{PORT}")
    print(f"[INFO] Make sure your FastAPI backend is running on http://127.0.0.1:8000")
    print("\n[INFO] Press Ctrl + C to stop the frontend server.\n")

    # Attempt to open browser automatically
    try:
        webbrowser.open(f"http://127.0.0.1:{PORT}")
    except Exception:
        pass

    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[INFO] Shutting down frontend server.")
            sys.exit(0)

if __name__ == "__main__":
    main()
