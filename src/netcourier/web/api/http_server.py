import socket
import threading
import json
import os
import urllib.parse

WEB_UI_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")

class HttpServer:
    def __init__(self, host='0.0.0.0', port=8080, api_handler=None):
        self.host = host
        self.port = port
        self.api_handler = api_handler
        self.running = False
        
    def start(self):
        self.running = True
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(100)
        print(f"Web UI & API Server running at http://{self.host}:{self.port}")
        
        while self.running:
            try:
                conn, addr = self.server_socket.accept()
                threading.Thread(target=self.handle_client, args=(conn, addr), daemon=True).start()
            except Exception as e:
                if self.running:
                    print(f"Accept error: {e}")

    def handle_client(self, conn, addr):
        try:
            try:
                conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            except Exception as e:
                pass
            req = b""
            MAX_HEADER_SIZE = 65536
            while b"\r\n\r\n" not in req:
                chunk = conn.recv(8192)
                if not chunk:
                    break
                req += chunk
                if len(req) > MAX_HEADER_SIZE:
                    break
            
            if not req or b"\r\n\r\n" not in req:
                conn.close()
                return

            headers_part, body_part = req.split(b"\r\n\r\n", 1)
            lines = headers_part.decode('utf-8', errors='ignore').split("\r\n")
            
            request_line = lines[0]
            parts = request_line.split(" ")
            if len(parts) < 2:
                conn.close()
                return
                
            method, path = parts[0], parts[1]
            
            headers = {}
            for line in lines[1:]:
                if ":" in line:
                    k, v = line.split(":", 1)
                    headers[k.strip().lower()] = v.strip()
                    
            content_length = int(headers.get("content-length", 0))
            
            if content_length > 1024 * 1024 * 1024:
                self.send_response(conn, 413, {"error": "Request entity too large"})
                return

            body = body_part
            while len(body) < content_length:
                chunk = conn.recv(min(1024 * 1024, content_length - len(body)))
                if not chunk:
                    break
                body += chunk

            self.route_request(conn, method, path, headers, body)
        except Exception as e:
            print(f"Error handling HTTP client: {e}")
        finally:
            try:
                conn.close()
            except:
                pass

    def send_response(self, conn, status_code, body, content_type="application/json"):
        if isinstance(body, dict) or isinstance(body, list):
            body = json.dumps(body).encode('utf-8')
        elif isinstance(body, str):
            body = body.encode('utf-8')
            
        status_text = "OK" if status_code == 200 else "Bad Request" if status_code == 400 else "Internal Server Error"
        response = f"HTTP/1.1 {status_code} {status_text}\r\n"
        response += f"Content-Type: {content_type}\r\n"
        response += "Access-Control-Allow-Origin: *\r\n"
        response += "Access-Control-Allow-Headers: Content-Type, Authorization, Session-Id\r\n"
        response += f"Content-Length: {len(body)}\r\n"
        response += "\r\n"
        try:
            conn.sendall(response.encode('utf-8') + body)
        except Exception as e:
            pass

    def serve_static(self, conn, path):
        if path == "/":
            path = "/index.html"
        file_path = os.path.join(WEB_UI_DIR, path.lstrip("/"))
        if not os.path.exists(file_path):
            self.send_response(conn, 404, "Not Found", "text/plain")
            return
            
        ext = os.path.splitext(file_path)[1]
        content_types = {
            ".html": "text/html",
            ".js": "application/javascript",
            ".css": "text/css",
            ".json": "application/json",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".svg": "image/svg+xml"
        }
        ct = content_types.get(ext, "application/octet-stream")
        
        with open(file_path, "rb") as f:
            body = f.read()
            self.send_response(conn, 200, body, ct)

    def route_request(self, conn, method, path, headers, body):
        if method == "OPTIONS":
            self.send_response(conn, 200, "")
            return

        parsed_url = urllib.parse.urlparse(path)
        path_only = parsed_url.path
        qs_params = dict(urllib.parse.parse_qsl(parsed_url.query))
        
        for k, v in qs_params.items():
            if isinstance(v, list) and len(v) == 1:
                qs_params[k] = v[0]

        if path_only.startswith("/api/"):
            if self.api_handler:
                self.api_handler(conn, method, path_only, headers, body, qs_params, self.send_response)
            else:
                self.send_response(conn, 501, {"error": "API not implemented"})
        else:
            self.serve_static(conn, path_only)
