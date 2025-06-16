import http.server
import socketserver
import threading
import os
import socket
import logging

logger = logging.getLogger("APT-LOCAL")

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s || %(levelname)s || %(message)s",
    datefmt="%H:%M:%S"
)

class AptServer:
    def __init__(self, port=8000, directory="debian_packages", max_retries=10):
        self.port = port
        self.directory = directory
        self.max_retries = max_retries

    def start(self):

        for attempt in range(self.max_retries):
            self.port = self.port + 1
            try:
                handler = lambda *args, **kwargs: http.server.SimpleHTTPRequestHandler(*args, directory=self.directory, **kwargs)
                httpd = socketserver.TCPServer(("", self.port), handler)
                logger.info(f"Serving {self.directory} as HTTP on port {self.port}...")
                server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
                server_thread.start()
                return server_thread
            except OSError as e:
                print(e)
                if isinstance(e, socket.error) or "Address already in use" in str(e):
                    logger.warning(f"Port {self.port} is in use. Retrying... ({attempt + 1}/{self.max_retries})")
                else:
                    raise Exception(e)

        raise RuntimeError(f"Could not start server on port {self.port} after {self.max_retries} retries.")
