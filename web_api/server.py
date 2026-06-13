import socket
import threading
import json
import uuid
import time
import os
import urllib.parse
from client.gateway_connection import GatewayConnection
from client.room_connection import RoomConnection
from common.constants import DEFAULT_GATEWAY_HOST, DEFAULT_GATEWAY_CLIENT_PORT

WEB_UI_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web_ui")

class MockApp:
    def __init__(self, session):
        self.session = session
        self.token = None
        
    def run_in_ui(self, callback, *args, **kwargs):
        try:
            callback(*args, **kwargs)
        except Exception as e:
            print(f"Callback error: {e}")

    def on_pm_received(self, payload):
        self.session.push_event({"type": "PM_RECEIVED", "payload": payload})
        
    def on_room_message(self, payload):
        self.session.push_event({"type": "ROOM_MESSAGE", "payload": payload})
        
    def on_room_system_event(self, payload):
        self.session.push_event({"type": "SYSTEM_EVENT", "payload": payload})
        
    def on_gateway_disconnected(self):
        self.session.push_event({"type": "DISCONNECTED", "server": "gateway"})
        
    def on_room_disconnected(self):
        self.session.push_event({"type": "DISCONNECTED", "server": "room"})
        
    def show_error(self, message):
        self.session.push_event({"type": "ERROR", "message": message})

class WebSession:
    def __init__(self, session_id):
        self.session_id = session_id
        self.app = MockApp(self)
        self.gateway_conn = GatewayConnection(DEFAULT_GATEWAY_HOST, DEFAULT_GATEWAY_CLIENT_PORT, self.app)
        self.room_conn = None
        self.events = []
        self.lock = threading.Lock()
        self.cond = threading.Condition(self.lock)
        self.username = None
        
        self.gateway_conn.connect()

    def push_event(self, event):
        with self.cond:
            self.events.append(event)
            self.cond.notify_all()

    def get_events(self, timeout=30):
        with self.cond:
            if not self.events:
                self.cond.wait(timeout)
            events_to_return = self.events[:]
            self.events = []
            return events_to_return

class WebServer:
    def __init__(self, host='0.0.0.0', port=8080):
        self.host = host
        self.port = port
        self.sessions = {}
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
            req = b""
            while b"\r\n\r\n" not in req:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                req += chunk
                if len(req) > 1024 * 1024 * 10: # 10MB limit
                    break
            
            if not req:
                conn.close()
                return

            headers_part, body_part = req.split(b"\r\n\r\n", 1)
            lines = headers_part.decode('utf-8', errors='ignore').split("\r\n")
            if not lines or not lines[0]:
                conn.close()
                return
                
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
            body = body_part
            while len(body) < content_length:
                chunk = conn.recv(4096)
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

    def get_session(self, headers, qs_params=None):
        session_id = headers.get("session-id")
        if not session_id and qs_params and "session_id" in qs_params:
            session_id = qs_params["session_id"]
        if session_id and session_id in self.sessions:
            return self.sessions[session_id]
        return None

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
            try:
                json_body = json.loads(body.decode('utf-8')) if body else {}
            except (json.JSONDecodeError, UnicodeDecodeError):
                json_body = {}
                
            self.handle_api(conn, method, path_only, headers, json_body, qs_params, raw_body=body)
        else:
            self.serve_static(conn, path_only)

    def _sync_request(self, conn_obj, msg_type, payload):
        ev = threading.Event()
        res_container = {}
        def cb(header):
            res_container["header"] = header
            ev.set()
        if not conn_obj.send_request(msg_type, payload, callback=cb):
            return None
        ev.wait(timeout=10)
        return res_container.get("header")

    def handle_api(self, conn, method, path, headers, body, qs, raw_body=b""):
        session = self.get_session(headers, qs)
        
        if path == "/api/register" and method == "POST":
            # Temporarily use a fresh session to register
            temp_session = WebSession("temp")
            resp = self._sync_request(temp_session.gateway_conn, "REGISTER", body)
            temp_session.gateway_conn.disconnect()
            if resp and resp.get("type") == "REGISTER_OK":
                self.send_response(conn, 200, {"success": True, "username": resp["payload"]["username"]})
            else:
                self.send_response(conn, 400, {"success": False, "error": resp.get("type") if resp else "TIMEOUT"})
            return

        if path == "/api/login" and method == "POST":
            session_id = str(uuid.uuid4())
            new_session = WebSession(session_id)
            resp = self._sync_request(new_session.gateway_conn, "LOGIN", body)
            if resp and resp.get("type") == "LOGIN_OK":
                new_session.app.token = resp.get("token")
                new_session.username = body.get("username")
                self.sessions[session_id] = new_session
                self.send_response(conn, 200, {
                    "success": True, 
                    "session_id": session_id, 
                    "user": resp["payload"]
                })
            else:
                new_session.gateway_conn.disconnect()
                self.send_response(conn, 400, {"success": False, "error": resp.get("type") if resp else "TIMEOUT"})
            return

        if not session:
            self.send_response(conn, 401, {"error": "Unauthorized"})
            return

        if path == "/api/events" and method == "GET":
            events = session.get_events(timeout=25)
            self.send_response(conn, 200, {"events": events})
            return

        if path == "/api/users" and method == "GET":
            resp = self._sync_request(session.gateway_conn, "LIST_ONLINE_USERS", {})
            if resp and resp.get("type") == "ONLINE_USERS_RESPONSE":
                self.send_response(conn, 200, {"users": resp["payload"]["users"]})
            else:
                self.send_response(conn, 400, {"error": "Failed to get users"})
            return

        if path == "/api/pm" and method == "POST":
            session.gateway_conn.send_request("PRIVATE_MESSAGE_SEND", body)
            self.send_response(conn, 200, {"success": True})
            return

        if path == "/api/pm/history" and method == "GET":
            resp = self._sync_request(session.gateway_conn, "PM_HISTORY_REQUEST", {"other_username": qs.get("other_username")})
            if resp and resp.get("type") == "PM_HISTORY_RESPONSE":
                self.send_response(conn, 200, {"messages": resp["payload"]["messages"]})
            else:
                self.send_response(conn, 400, {"error": "Failed to get PM history"})
            return

        if path == "/api/rooms" and method == "GET":
            resp = self._sync_request(session.gateway_conn, "LIST_ROOMS", {})
            if resp and resp.get("type") == "ROOM_LIST_RESPONSE":
                self.send_response(conn, 200, {"rooms": resp["payload"]["rooms"]})
            else:
                self.send_response(conn, 400, {"error": "Failed to get rooms"})
            return

        if path == "/api/rooms" and method == "POST":
            resp = self._sync_request(session.gateway_conn, "CREATE_ROOM", body)
            if resp and resp.get("type") == "ROOM_ASSIGNED":
                self.send_response(conn, 200, {"room": resp["payload"]})
            else:
                self.send_response(conn, 400, {"error": "Failed to create room"})
            return

        if path == "/api/rooms/join" and method == "POST":
            room_name = body.get("room_name")
            print(f"DEBUG /api/rooms/join: joining room {room_name}")
            resp = self._sync_request(session.gateway_conn, "JOIN_ROOM", {"room_name": room_name})
            print(f"DEBUG JOIN_ROOM resp: {resp}")
            if resp and resp.get("type") == "ROOM_LOCATION":
                loc = resp["payload"]
                if session.room_conn:
                    session.room_conn.disconnect()
                
                print(f"DEBUG connecting to backend {loc['host']}:{loc['port']}")
                session.room_conn = RoomConnection(loc["host"], loc["port"], session.app)
                if session.room_conn.connect():
                    auth_resp = self._sync_request(session.room_conn, "AUTH_BACKEND", {})
                    print(f"DEBUG AUTH_BACKEND resp: {auth_resp}")
                    if auth_resp and auth_resp.get("type") == "AUTH_BACKEND_OK":
                        join_resp = self._sync_request(session.room_conn, "JOIN_ROOM_BACKEND", {"room_name": room_name})
                        print(f"DEBUG JOIN_ROOM_BACKEND resp: {join_resp}")
                        if join_resp and join_resp.get("type") == "JOIN_ROOM_OK":
                            self.send_response(conn, 200, {"success": True, "room_name": room_name})
                            return
                self.send_response(conn, 500, {"error": "Failed to join room backend"})
            else:
                self.send_response(conn, 400, {"error": "Failed to locate room", "details": resp})
            return

        if path == "/api/rooms/leave" and method == "POST":
            if session.room_conn:
                session.room_conn.send_request("LEAVE_ROOM", {})
                session.room_conn.disconnect()
                session.room_conn = None
            self.send_response(conn, 200, {"success": True})
            return

        if path == "/api/rooms/messages" and method == "GET":
            if session.room_conn:
                resp = self._sync_request(session.room_conn, "ROOM_HISTORY_REQUEST", {"room_name": qs.get("room_name")})
                if resp and resp.get("type") == "ROOM_HISTORY_RESPONSE":
                    self.send_response(conn, 200, {"messages": resp["payload"]["messages"]})
                    return
            self.send_response(conn, 400, {"error": "Failed to get room history"})
            return

        if path == "/api/rooms/messages" and method == "POST":
            if session.room_conn:
                session.room_conn.send_request("ROOM_CHAT_SEND", body)
                self.send_response(conn, 200, {"success": True})
            else:
                self.send_response(conn, 400, {"error": "Not connected to a room"})
            return

        if path == "/api/rooms/files" and method == "GET":
            if session.room_conn:
                resp = self._sync_request(session.room_conn, "FILE_LIST_REQUEST", {"room_name": qs.get("room_name")})
                if resp and resp.get("type") == "FILE_LIST_RESPONSE":
                    self.send_response(conn, 200, {"files": resp["payload"]["files"]})
                    return
            self.send_response(conn, 400, {"error": "Failed to get file list"})
            return

        if path == "/api/rooms/files/upload" and method == "POST":
            if not session.room_conn:
                self.send_response(conn, 400, {"error": "Not connected to room"})
                return
            room_name = qs.get("room_name")
            filename = qs.get("filename")
            if not room_name or not filename:
                self.send_response(conn, 400, {"error": "Missing params"})
                return

            import hashlib
            filesize = len(raw_body)
            chunk_size = 65536
            total_chunks = (filesize + chunk_size - 1) // chunk_size
            sha256 = hashlib.sha256(raw_body).hexdigest()

            init_resp = self._sync_request(session.room_conn, "UPLOAD_INIT", {
                "room_name": room_name,
                "filename": filename,
                "filesize": filesize,
                "chunk_size": chunk_size,
                "total_chunks": total_chunks,
                "checksum_sha256": sha256
            })

            if not init_resp or init_resp.get("type") != "UPLOAD_READY":
                self.send_response(conn, 400, {"error": "Upload init failed"})
                return

            transfer_id = init_resp["payload"]["transfer_id"]

            for i in range(total_chunks):
                chunk_data = raw_body[i*chunk_size : (i+1)*chunk_size]
                chunk_payload = {
                    "transfer_id": transfer_id,
                    "chunk_index": i
                }
                import struct
                from common.protocol import build_packet
                packet = build_packet("UPLOAD_CHUNK", chunk_payload, token=session.app.token)
                packet["payload_size"] = len(chunk_data)
                header_json = json.dumps(packet).encode('utf-8')
                
                ev = threading.Event()
                ack_res = {}
                def cb(h):
                    ack_res["h"] = h
                    ev.set()
                session.room_conn.pending_requests[packet["request_id"]] = cb
                
                session.room_conn.sock.sendall(struct.pack(">I", len(header_json)) + header_json + chunk_data)
                ev.wait(5)

            finish_resp = self._sync_request(session.room_conn, "UPLOAD_FINISH", {"transfer_id": transfer_id})
            if finish_resp and finish_resp.get("type") == "UPLOAD_SUCCESS":
                self.send_response(conn, 200, {"success": True})
            else:
                self.send_response(conn, 400, {"error": "Upload finish failed"})
            return

        if path == "/api/rooms/files/download" and method == "GET":
            if not session.room_conn:
                self.send_response(conn, 400, {"error": "Not connected to room"})
                return
            file_id = qs.get("file_id")
            if not file_id:
                self.send_response(conn, 400, {"error": "Missing file_id"})
                return
                
            dl_resp = self._sync_request(session.room_conn, "DOWNLOAD_REQUEST", {"file_id": int(file_id)})
            if not dl_resp or dl_resp.get("type") != "DOWNLOAD_READY":
                self.send_response(conn, 400, {"error": "Download request failed"})
                return
                
            total_chunks = dl_resp["payload"]["total_chunks"]
            transfer_id = dl_resp["payload"]["transfer_id"]
            
            # Wait to gather chunks (MockApp needs to handle it or we intercept)
            # Since RoomConnection parses DOWNLOAD_CHUNK, we can temporarily monkey-patch MockApp
            downloaded_chunks = {}
            ev = threading.Event()
            
            def on_chunk(chunk_index, data):
                downloaded_chunks[chunk_index] = data
                if len(downloaded_chunks) == total_chunks:
                    ev.set()
                    
            # Setup fake downloader interface
            class FakeDownloader:
                def handle_chunk(self, idx, data):
                    on_chunk(idx, data)
            session.app.active_downloader = FakeDownloader()
            
            ev.wait(30) # wait up to 30s
            session.app.active_downloader = None
            
            if len(downloaded_chunks) == total_chunks:
                file_bytes = b"".join(downloaded_chunks[i] for i in range(total_chunks))
                self.send_response(conn, 200, file_bytes, "application/octet-stream")
            else:
                self.send_response(conn, 500, {"error": "Download timeout"})
            return

        self.send_response(conn, 404, {"error": "Not Found"})

if __name__ == "__main__":
    server = WebServer(port=8080)
    server.start()
