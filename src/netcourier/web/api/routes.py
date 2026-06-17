import json
import threading
import uuid
from netcourier.web.api.session import WebSession
from netcourier.common.constants import DEFAULT_GATEWAY_HOST, DEFAULT_GATEWAY_CLIENT_PORT

class APIHandler:
    def __init__(self, gateway_host=DEFAULT_GATEWAY_HOST, gateway_port=DEFAULT_GATEWAY_CLIENT_PORT):
        self.gateway_host = gateway_host
        self.gateway_port = gateway_port
        self.sessions = {}

    def get_session(self, headers, qs_params=None):
        session_id = headers.get("session-id")
        if not session_id and qs_params and "session_id" in qs_params:
            session_id = qs_params["session_id"]
        if session_id and session_id in self.sessions:
            return self.sessions[session_id]
        return None

    def _sync_request(self, conn_obj, msg_type, payload):
        if not conn_obj:
            return None
        ev = threading.Event()
        res_container = {}
        def cb(header):
            res_container["header"] = header
            ev.set()
        
        try:
            if not conn_obj.send_request(msg_type, payload, callback=cb):
                return None
        except Exception as e:
            print(f"Sync request send error: {e}")
            return None
            
        if not ev.wait(timeout=5):
            print(f"Sync request {msg_type} timed out")
            return None
        return res_container.get("header")

    def handle_request(self, conn, method, path, headers, raw_body, qs, send_response):
        session = self.get_session(headers, qs)
        
        is_upload = (path == "/api/rooms/files/upload")
        json_body = {}
        if raw_body and not is_upload:
            try:
                json_body = json.loads(raw_body.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                json_body = {}
                
        body = json_body

        if path == "/api/register" and method == "POST":
            try:
                temp_session = WebSession("temp-" + str(uuid.uuid4()), self.gateway_host, self.gateway_port)
                resp = self._sync_request(temp_session.gateway_conn, "REGISTER", body)
                temp_session.gateway_conn.disconnect()
                if resp and resp.get("type") == "REGISTER_OK":
                    send_response(conn, 200, {"success": True, "username": resp["payload"]["username"]})
                else:
                    send_response(conn, 400, {"success": False, "error": resp.get("type") if resp else "TIMEOUT"})
            except Exception as e:
                send_response(conn, 500, {"error": str(e)})
            return

        if path == "/api/login" and method == "POST":
            session_id = str(uuid.uuid4())
            try:
                new_session = WebSession(session_id, self.gateway_host, self.gateway_port)
                resp = self._sync_request(new_session.gateway_conn, "LOGIN", body)
                if resp and resp.get("type") == "LOGIN_OK":
                    new_session.app.token = resp.get("token")
                    new_session.username = body.get("username")
                    self.sessions[session_id] = new_session
                    send_response(conn, 200, {
                        "success": True, 
                        "session_id": session_id, 
                        "user": resp["payload"]
                    })
                else:
                    new_session.gateway_conn.disconnect()
                    send_response(conn, 400, {"success": False, "error": resp.get("payload", {}).get("message") if resp else "Gateway timeout"})
            except Exception as e:
                send_response(conn, 500, {"error": f"Login failed: {e}"})
            return

        if not session:
            send_response(conn, 401, {"error": "Unauthorized"})
            return

        if path == "/api/events" and method == "GET":
            events = session.get_events(timeout=25)
            send_response(conn, 200, {"events": events})
            return

        if path == "/api/users" and method == "GET":
            resp = self._sync_request(session.gateway_conn, "LIST_ONLINE_USERS", {})
            if resp and resp.get("type") == "ONLINE_USERS_RESPONSE":
                send_response(conn, 200, {"users": resp["payload"]["users"]})
            else:
                send_response(conn, 400, {"error": "Failed to get users"})
            return

        if path == "/api/pm" and method == "POST":
            session.gateway_conn.send_request("PRIVATE_MESSAGE_SEND", body)
            send_response(conn, 200, {"success": True})
            return

        if path == "/api/pm/history" and method == "GET":
            resp = self._sync_request(session.gateway_conn, "PM_HISTORY_REQUEST", {"other_username": qs.get("other_username")})
            if resp and resp.get("type") == "PM_HISTORY_RESPONSE":
                send_response(conn, 200, {"messages": resp["payload"]["messages"]})
            else:
                send_response(conn, 400, {"error": "Failed to get PM history"})
            return

        if path == "/api/rooms" and method == "GET":
            resp = self._sync_request(session.gateway_conn, "LIST_ROOMS", {})
            if resp and resp.get("type") == "ROOM_LIST_RESPONSE":
                send_response(conn, 200, {"rooms": resp["payload"]["rooms"]})
            else:
                send_response(conn, 400, {"error": "Failed to get rooms"})
            return

        if path == "/api/rooms" and method == "POST":
            resp = self._sync_request(session.gateway_conn, "CREATE_ROOM", body)
            if resp and resp.get("type") == "ROOM_ASSIGNED":
                send_response(conn, 200, {"room": resp["payload"]})
            else:
                send_response(conn, 400, {"error": "Failed to create room"})
            return

        if path == "/api/rooms/join" and method == "POST":
            room_name = body.get("room_name")
            resp = self._sync_request(session.gateway_conn, "JOIN_ROOM", {"room_name": room_name})
            if resp and resp.get("type") == "ROOM_LOCATION":
                loc = resp["payload"]
                if session.room_conn:
                    session.room_conn.disconnect()
                
                from netcourier.client.room_connection import RoomConnection
                session.room_conn = RoomConnection(loc["host"], loc["port"], session.app)
                if session.room_conn.connect():
                    auth_resp = self._sync_request(session.room_conn, "AUTH_BACKEND", {})
                    if auth_resp and auth_resp.get("type") == "AUTH_BACKEND_OK":
                        join_resp = self._sync_request(session.room_conn, "JOIN_ROOM_BACKEND", {"room_name": room_name})
                        if join_resp and join_resp.get("type") == "JOIN_ROOM_OK":
                            send_response(conn, 200, {"success": True, "room_name": room_name})
                            return
                send_response(conn, 500, {"error": "Failed to join room backend"})
            else:
                send_response(conn, 400, {"error": "Failed to locate room", "details": resp})
            return

        if path == "/api/rooms/leave" and method == "POST":
            if session.room_conn:
                session.room_conn.send_request("LEAVE_ROOM", {})
                session.room_conn.disconnect()
                session.room_conn = None
            send_response(conn, 200, {"success": True})
            return

        if path == "/api/rooms/messages" and method == "GET":
            if session.room_conn:
                resp = self._sync_request(session.room_conn, "ROOM_HISTORY_REQUEST", {"room_name": qs.get("room_name")})
                if resp and resp.get("type") == "ROOM_HISTORY_RESPONSE":
                    send_response(conn, 200, {"messages": resp["payload"]["messages"]})
                    return
            send_response(conn, 400, {"error": "Failed to get room history"})
            return

        if path == "/api/rooms/members" and method == "GET":
            if session.room_conn:
                resp = self._sync_request(session.room_conn, "ROOM_MEMBER_LIST_REQUEST", {"room_name": qs.get("room_name")})
                if resp and resp.get("type") == "ROOM_MEMBER_LIST_RESPONSE":
                    send_response(conn, 200, {"members": resp["payload"]["members"]})
                    return
            send_response(conn, 400, {"error": "Failed to get room members"})
            return

        if path == "/api/rooms/messages" and method == "POST":
            if session.room_conn:
                session.room_conn.send_request("ROOM_CHAT_SEND", body)
                send_response(conn, 200, {"success": True})
            else:
                send_response(conn, 400, {"error": "Not connected to a room"})
            return

        if path == "/api/rooms/reactions" and method == "POST":
            if session.room_conn:
                session.room_conn.send_request("ROOM_MESSAGE_REACTION", body)
                send_response(conn, 200, {"success": True})
            else:
                send_response(conn, 400, {"error": "Not connected to a room"})
            return

        if path == "/api/rooms/typing" and method == "POST":
            if session.room_conn:
                session.room_conn.send_request("ROOM_TYPING_INDICATOR", body)
                send_response(conn, 200, {"success": True})
            else:
                send_response(conn, 400, {"error": "Not connected to a room"})
            return

        if path == "/api/rooms/kick" and method == "POST":
            if session.room_conn:
                session.room_conn.send_request("ROOM_KICK_USER", body)
                send_response(conn, 200, {"success": True})
            else:
                send_response(conn, 400, {"error": "Not connected to a room"})
            return

        if path == "/api/rooms/files/delete" and method == "POST":
            if session.room_conn:
                session.room_conn.send_request("ROOM_DELETE_FILE", body)
                send_response(conn, 200, {"success": True})
            else:
                send_response(conn, 400, {"error": "Not connected to a room"})
            return

        if path == "/api/rooms/files" and method == "GET":
            if session.room_conn:
                resp = self._sync_request(session.room_conn, "FILE_LIST_REQUEST", {"room_name": qs.get("room_name")})
                if resp and resp.get("type") == "FILE_LIST_RESPONSE":
                    send_response(conn, 200, {"files": resp["payload"]["files"]})
                    return
            send_response(conn, 400, {"error": "Failed to get file list"})
            return

        if path == "/api/rooms/files/resume" and method == "GET":
            if not session.room_conn:
                send_response(conn, 400, {"error": "Not connected to room"})
                return
            transfer_id = qs.get("transfer_id")
            direction = qs.get("direction", "upload")
            if not transfer_id:
                send_response(conn, 400, {"error": "Missing transfer_id"})
                return
            
            resp = self._sync_request(session.room_conn, "RESUME_TRANSFER", {
                "transfer_id": int(transfer_id),
                "direction": direction
            })
            if resp and resp.get("type") in ["UPLOAD_READY", "DOWNLOAD_READY"]:
                send_response(conn, 200, resp["payload"])
            else:
                send_response(conn, 400, {"error": "Resume failed", "details": resp})
            return

        if path == "/api/rooms/files/upload" and method == "POST":
            if not session.room_conn:
                send_response(conn, 400, {"error": "Not connected to room"})
                return
            room_name = qs.get("room_name")
            filename = qs.get("filename")
            action = qs.get("action")

            if not room_name or not filename:
                send_response(conn, 400, {"error": "Missing params"})
                return

            chunk_size = 1024 * 1024
            filesize = int(qs.get("filesize", 0))
            if filesize > 100 * 1024 * 1024:
                import math
                mb = math.ceil(filesize / (100 * 1024 * 1024))
                chunk_size = min(16, mb) * 1024 * 1024

            if action:
                if action == "init":
                    filesize = int(qs.get("filesize", 0))
                    checksum = qs.get("checksum_sha256", "")
                    total_chunks = (filesize + chunk_size - 1) // chunk_size if filesize > 0 else 0
                    
                    init_resp = self._sync_request(session.room_conn, "UPLOAD_INIT", {
                        "room_name": room_name,
                        "filename": filename,
                        "filesize": filesize,
                        "chunk_size": chunk_size,
                        "total_chunks": total_chunks,
                        "checksum_sha256": checksum
                    })
                    
                    if not init_resp or init_resp.get("type") != "UPLOAD_READY":
                        send_response(conn, 400, {"error": f"Upload init failed: {init_resp.get('payload', {}).get('message') if init_resp else 'Timeout'}"})
                        return
                    
                    transfer_id = init_resp["payload"]["transfer_id"]
                    send_response(conn, 200, {"success": True, "transfer_id": transfer_id})
                    return

                elif action == "chunk":
                    transfer_id = int(qs.get("transfer_id", 0))
                    chunk_index = int(qs.get("chunk_index", 0))
                    
                    chunk_payload = {
                        "transfer_id": transfer_id,
                        "chunk_index": chunk_index,
                        "chunk_size": len(raw_body)
                    }
                    import struct
                    from netcourier.common.protocol import build_packet
                    packet = build_packet("UPLOAD_CHUNK", chunk_payload, token=session.app.token)
                    packet["payload_size"] = len(raw_body)
                    header_json = json.dumps(packet).encode('utf-8')
                    
                    ev = threading.Event()
                    ack_res = {}
                    def cb(h):
                        ack_res["h"] = h
                        ev.set()
                    
                    with session.room_conn.lock:
                        session.room_conn.pending_requests[packet["request_id"]] = cb
                    
                    try:
                        with session.room_conn.write_lock:
                            session.room_conn.sock.sendall(struct.pack(">I", len(header_json)) + header_json + raw_body)
                    except Exception as e:
                        send_response(conn, 500, {"error": f"Socket send error: {e}"})
                        return
                    
                    if not ev.wait(30):
                        send_response(conn, 400, {"error": f"Chunk {chunk_index} timeout"})
                        return
                    
                    ack = ack_res.get("h")
                    if not ack or ack.get("type") != "CHUNK_ACK":
                        send_response(conn, 400, {"error": f"Chunk {chunk_index} failed"})
                        return
                        
                    send_response(conn, 200, {"success": True})
                    return

                elif action == "finish":
                    transfer_id = int(qs.get("transfer_id", 0))
                    finish_resp = self._sync_request(session.room_conn, "UPLOAD_FINISH", {"transfer_id": transfer_id})
                    if finish_resp and finish_resp.get("type") == "UPLOAD_SUCCESS":
                        send_response(conn, 200, {"success": True, "transfer_id": transfer_id})
                    else:
                        send_response(conn, 400, {"error": "Upload finish failed"})
                    return

                else:
                    send_response(conn, 400, {"error": f"Invalid action: {action}"})
                    return
            else:
                existing_transfer_id = qs.get("transfer_id")
                start_chunk = int(qs.get("start_chunk", 0))
                import hashlib
                filesize = len(raw_body) + (start_chunk * chunk_size if start_chunk > 0 else 0)
                total_chunks = (filesize + chunk_size - 1) // chunk_size
                
                sha256 = ""
                if start_chunk == 0:
                    sha256 = hashlib.sha256(raw_body).hexdigest()

                if not existing_transfer_id:
                    init_resp = self._sync_request(session.room_conn, "UPLOAD_INIT", {
                        "room_name": room_name,
                        "filename": filename,
                        "filesize": filesize,
                        "chunk_size": chunk_size,
                        "total_chunks": total_chunks,
                        "checksum_sha256": sha256
                    })

                    if not init_resp or init_resp.get("type") != "UPLOAD_READY":
                        send_response(conn, 400, {"error": f"Upload init failed: {init_resp.get('payload', {}).get('message') if init_resp else 'Timeout'}"})
                        return
                    transfer_id = init_resp["payload"]["transfer_id"]
                else:
                    transfer_id = int(existing_transfer_id)

                for i in range(len(raw_body) // chunk_size + (1 if len(raw_body) % chunk_size > 0 else 0)):
                    current_chunk_idx = start_chunk + i
                    chunk_data = raw_body[i*chunk_size : (i+1)*chunk_size]
                    chunk_payload = {
                        "transfer_id": transfer_id,
                        "chunk_index": current_chunk_idx,
                        "chunk_size": len(chunk_data)
                    }
                    import struct
                    from netcourier.common.protocol import build_packet
                    packet = build_packet("UPLOAD_CHUNK", chunk_payload, token=session.app.token)
                    packet["payload_size"] = len(chunk_data)
                    header_json = json.dumps(packet).encode('utf-8')
                    
                    ev = threading.Event()
                    ack_res = {}
                    def cb(h):
                        ack_res["h"] = h
                        ev.set()
                    
                    with session.room_conn.lock:
                        session.room_conn.pending_requests[packet["request_id"]] = cb
                    
                    session.room_conn.sock.sendall(struct.pack(">I", len(header_json)) + header_json + chunk_data)
                    
                    if not ev.wait(10):
                        send_response(conn, 400, {"error": f"Chunk {current_chunk_idx} timeout"})
                        return
                    
                    ack = ack_res.get("h")
                    if not ack or ack.get("type") != "CHUNK_ACK":
                        send_response(conn, 400, {"error": f"Chunk {current_chunk_idx} failed"})
                        return

                finish_resp = self._sync_request(session.room_conn, "UPLOAD_FINISH", {"transfer_id": transfer_id})
                if finish_resp and finish_resp.get("type") == "UPLOAD_SUCCESS":
                    send_response(conn, 200, {"success": True, "transfer_id": transfer_id})
                else:
                    if finish_resp and finish_resp.get("type") == "ERROR":
                         send_response(conn, 200, {"success": True, "transfer_id": transfer_id, "status": "partial"})
                    else:
                         send_response(conn, 200, {"success": True, "transfer_id": transfer_id})
                return

        if path == "/api/rooms/files/download" and method == "GET":
            if not session.room_conn:
                send_response(conn, 400, {"error": "Not connected to room"})
                return
            file_id = qs.get("file_id")
            if not file_id:
                send_response(conn, 400, {"error": "Missing file_id"})
                return
                
            dl_resp = self._sync_request(session.room_conn, "DOWNLOAD_REQUEST", {"file_id": int(file_id)})
            if not dl_resp or dl_resp.get("type") != "DOWNLOAD_READY":
                send_response(conn, 400, {"error": "Download request failed"})
                return
                
            total_chunks = dl_resp["payload"]["total_chunks"]
            transfer_id = dl_resp["payload"]["transfer_id"]
            
            response_headers = "HTTP/1.1 200 OK\r\n"
            response_headers += "Content-Type: application/octet-stream\r\n"
            response_headers += "Transfer-Encoding: chunked\r\n"
            response_headers += "Access-Control-Allow-Origin: *\r\n"
            response_headers += "Access-Control-Allow-Headers: Content-Type, Authorization, Session-Id\r\n"
            response_headers += "\r\n"
            
            try:
                conn.sendall(response_headers.encode('utf-8'))
            except Exception as e:
                print(f"Failed to send download headers: {e}")
                return
            
            ev = threading.Event()
            error_occurred = [False]
            
            class StreamDownloader:
                def __init__(self):
                    self.expected_chunk = 0
                
                def handle_chunk(self, idx, data):
                    if error_occurred[0]:
                        return
                    try:
                        chunk_header = f"{len(data):X}\r\n".encode('utf-8')
                        conn.sendall(chunk_header + data + b"\r\n")
                        self.expected_chunk += 1
                        if self.expected_chunk >= total_chunks:
                            ev.set()
                    except Exception as e:
                        print(f"Error streaming download chunk: {e}")
                        error_occurred[0] = True
                        ev.set()
            
            session.app.active_downloader = StreamDownloader()
            ev.wait(300)
            session.app.active_downloader = None
            
            if not error_occurred[0]:
                try:
                    conn.sendall(b"0\r\n\r\n")
                except:
                    pass
            return

        send_response(conn, 404, {"error": "Not Found"})
