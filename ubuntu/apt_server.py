import http.server
import socketserver
import threading
import os
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger(__name__)

class AptServer:
    def __init__(self, port=8000, directory="debian_packages", max_retries=5):
        self.port = port
        self.initial_port = port
        self.directory = directory
        self.handler = http.server.SimpleHTTPRequestHandler
        self.max_retries = max_retries
        self.httpd = None
        self.thread = None

    def start(self):
        os.chdir(self.directory)

        for i in range(self.max_retries + 1):
            try:
                self.port = self.initial_port + i
                self.httpd = socketserver.TCPServer(("", self.port), self.handler)
                break
            except OSError as e:
                if i == self.max_retries:
                    logger.error(f"Failed to start server on port {self.port}: {e}")
                    raise Exception(f"Could not start server on port {self.initial_port} after {self.max_retries} retries.")
                logger.warning(f"Port {self.port} is in use. Retrying... ({i + 1}/{self.max_retries})")
                continue

        logger.info(f"Serving {self.directory} as HTTP on port {self.port}...")
        self.thread = threading.Thread(target=self.httpd.serve_forever)
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()
            logger.info(f"Server stopped on port {self.port}.")
