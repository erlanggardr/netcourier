import socket
import threading
import logging
import argparse
import time
import sys
from datetime import datetime

from common.constants import (
    DEFAULT_GATEWAY_HOST,
    DEFAULT_GATEWAY_BACKEND_PORT,
    PROJECT_ROOT
)
from common.protocol import receive_packet, send_packet, build_packet, build_error_packet
from common.logging_config import setup_logging
from common.db import get_db_connection

class ProcessServer:
    def __init__(self, server_id, host, port, gateway_host, gateway_port):
        self.server_id = server_id
        self.host = host
        self.port = port
        self.gateway_host = gateway_host
        self.gateway_port = gateway_port
        
        self.logger = setup_logging(f"server_{server_id.lower()}")
        
        # client_socket -> {user_id, username, current_room}
        self.clients = {}
        # room_name -> set(client_sockets)
        self.rooms = {}
        
        self.running = False
        self.gateway_sock = None
        self.lock = threading.Lock()

    def start(self):
        self.running = True
        
        # 1. Connect to Gateway
        if not self._connect_to_gateway():
            self.logger.error("Failed to connect to Gateway. Exiting.")
            return

        # 2. Start heartbeat thread
        threading.Thread(target=self._heartbeat_loop, daemon=True).start()
        
        # 3. Start client server
        client_thread = threading.Thread(target=self._run_client_server, daemon=True)
        client_thread.start()
        
        self.logger.info(f"Process Server {self.server_id} started on {self.host}:{self.port}")
        
        try:
            while self.running:
                threading.Event().wait(1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        self.logger.info(f"Stopping Process Server {self.server_id}...")
        self.running = False
        if self.gateway_sock:
            self.gateway_sock.close()

    def _connect_to_gateway(self):
        try:
            self.gateway_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.gateway_sock.connect((self.gateway_host, self.gateway_port))
            
            # Register backend
            reg_packet = build_packet("REGISTER_BACKEND", {
                "server_id": self.server_id,
                "host": self.host,
                "port": self.port
            })
            send_packet(self.gateway_sock, reg_packet)
            
            header, _ = receive_packet(self.gateway_sock)
            if header.get("type") == "BACKEND_REGISTERED":
                self.logger.info(f"Successfully registered with Gateway as {self.server_id}")
                # Start gateway message listener (for VALIDATE_TOKEN responses etc)
                threading.Thread(target=self._listen_to_gateway, daemon=True).start()
                return True
            else:
                self.logger.error(f"Gateway rejected registration: {header}")
                return False
        except Exception as e:
            self.logger.exception(f"Error connecting to Gateway: {e}")
            return False

    def _listen_to_gateway(self):
        """Listen for unsolicited messages from Gateway if any, or just handle responses if needed."""
        # For now, most communication is request-response initiated by this server.
        # But we need to handle incoming packets if we use a shared socket for requests.
        # Actually, for VALIDATE_TOKEN, we'll send and wait for response.
        pass

    def _heartbeat_loop(self):
        while self.running:
            try:
                with self.lock:
                    active_rooms = len(self.rooms)
                    active_clients = len(self.clients)
                
                hb_packet = build_packet("HEARTBEAT", {
                    "server_id": self.server_id,
                    "stats": {
                        "active_rooms": active_rooms,
                        "active_clients": active_clients,
                        "active_transfers": 0 # Phase 7
                    }
                })
                send_packet(self.gateway_sock, hb_packet)
            except Exception as e:
                self.logger.error(f"Heartbeat failed: {e}")
                # Try to reconnect?
            
            time.sleep(5)

    def _run_client_server(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((self.host, self.port))
            s.listen()
            self.logger.info(f"Client server listening on {self.host}:{self.port}")
            
            while self.running:
                conn, addr = s.accept()
                threading.Thread(target=self._handle_client, args=(conn, addr), daemon=True).start()

    def _handle_client(self, conn, addr):
        self.logger.info(f"New client connection from {addr}")
        try:
            with conn:
                while self.running:
                    header, binary_payload = receive_packet(conn)
                    msg_type = header.get("type")
                    req_id = header.get("request_id")
                    token = header.get("token")
                    payload = header.get("payload", {})
                    
                    if msg_type == "AUTH_BACKEND":
                        self._handle_auth_backend(conn, req_id, token, payload)
                    elif msg_type == "JOIN_ROOM_BACKEND":
                        self._handle_join_room(conn, req_id, payload)
                    elif msg_type == "LEAVE_ROOM":
                        self._handle_leave_room(conn, req_id)
                    elif msg_type == "PING":
                        send_packet(conn, build_packet("PONG", request_id=req_id))
                    else:
                        # Ensure authenticated for other messages (Phase 6+)
                        if conn not in self.clients:
                            send_packet(conn, build_error_packet("INVALID_TOKEN", request_id=req_id))
                            continue
                        
                        if msg_type == "ROOM_CHAT_SEND":
                            self._handle_room_chat_send(conn, req_id, payload)
                        elif msg_type == "ROOM_HISTORY_REQUEST":
                            self._handle_room_history_request(conn, req_id, payload)
                        elif msg_type == "FILE_LIST_REQUEST":
                            self._handle_file_list_request(conn, req_id, payload)
                        elif msg_type == "UPLOAD_INIT":
                            self._handle_upload_init(conn, req_id, payload)
                        elif msg_type == "UPLOAD_CHUNK":
                            self._handle_upload_chunk(conn, req_id, payload, binary_payload)
                        elif msg_type == "UPLOAD_FINISH":
                            self._handle_upload_finish(conn, req_id, payload)
                        elif msg_type == "DOWNLOAD_REQUEST":
                            self._handle_download_request(conn, req_id, payload)
                        else:
                            self.logger.warning(f"Unhandled message type: {msg_type}")
        except (ConnectionError, socket.error):
            self.logger.info(f"Client {addr} disconnected")
        except Exception as e:
            self.logger.exception(f"Error handling client {addr}: {e}")
        finally:
            self._cleanup_client(conn)

    def _handle_auth_backend(self, conn, req_id, token, payload):
        if not token:
            send_packet(conn, build_error_packet("MISSING_FIELD", request_id=req_id))
            return

        # Validate token with Gateway
        # Note: Since we are using a single gateway_sock, we need to be careful with concurrent requests.
        # For simplicity in this phase, we use a lock or a fresh connection.
        # Let's use a fresh connection for validation to avoid multiplexing complexity on the control channel.
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as g_sock:
                g_sock.connect((self.gateway_host, self.gateway_port))
                val_packet = build_packet("VALIDATE_TOKEN", {"token": token})
                send_packet(g_sock, val_packet)
                
                header, _ = receive_packet(g_sock)
                if header.get("type") == "TOKEN_VALID":
                    res_payload = header.get("payload")
                    user_id = res_payload["user_id"]
                    username = res_payload["username"]
                    
                    self.logger.info(f"Token validation successful for user: {username}")
                    with self.lock:
                        self.clients[conn] = {
                            "user_id": user_id,
                            "username": username,
                            "current_room": None
                        }
                    
                    send_packet(conn, build_packet("AUTH_BACKEND_OK", {
                        "user_id": user_id,
                        "username": username
                    }, request_id=req_id))
                else:
                    send_packet(conn, build_error_packet("INVALID_TOKEN", request_id=req_id))
        except Exception as e:
            self.logger.error(f"Token validation failed: {e}")
            send_packet(conn, build_error_packet("INTERNAL_ERROR", request_id=req_id))

    def _handle_join_room(self, conn, req_id, payload):
        room_name = payload.get("room_name")
        if not room_name:
            send_packet(conn, build_error_packet("MISSING_FIELD", request_id=req_id))
            return
            
        if conn not in self.clients:
            send_packet(conn, build_error_packet("INVALID_TOKEN", request_id=req_id))
            return

        user_info = self.clients[conn]
        
        with self.lock:
            # Leave previous room if any
            if user_info["current_room"]:
                self._leave_room_logic(conn)
            
            # Join new room
            if room_name not in self.rooms:
                self.rooms[room_name] = set()
            self.rooms[room_name].add(conn)
            user_info["current_room"] = room_name
            
        # Update presence via Gateway
        self._update_presence_gateway(user_info["user_id"], user_info["username"], "in_room", room_name)
        
        # Add members list to system event
        members = self._get_room_members(room_name)
        
        # Broadcast join message
        self._broadcast_system_event(room_name, f"User {user_info['username']} joined the room.", members)
        
        # In Phase 6, we would send history here
        # Actually client requests history via ROOM_HISTORY_REQUEST after JOIN_ROOM_OK
        send_packet(conn, build_packet("JOIN_ROOM_OK", {"room_name": room_name}, request_id=req_id))
        self.logger.info(f"User {user_info['username']} joined room {room_name}")

    def _handle_leave_room(self, conn, req_id):
        if conn not in self.clients:
            send_packet(conn, build_error_packet("INVALID_TOKEN", request_id=req_id))
            return

        user_info = self.clients[conn]
        room_name = user_info["current_room"]
        
        if room_name:
            self._leave_room_logic(conn)
            self._update_presence_gateway(user_info["user_id"], user_info["username"], "waiting")
            send_packet(conn, build_packet("LEAVE_ROOM_OK", {"room_name": room_name}, request_id=req_id))
            self.logger.info(f"User {user_info['username']} left room {room_name}")
            
            members = self._get_room_members(room_name)
            self._broadcast_system_event(room_name, f"User {user_info['username']} left the room.", members)
        else:
            send_packet(conn, build_error_packet("NOT_IN_ROOM", request_id=req_id))

    def _leave_room_logic(self, conn):
        user_info = self.clients[conn]
        room_name = user_info["current_room"]
        if room_name and room_name in self.rooms:
            self.rooms[room_name].discard(conn)
            if not self.rooms[room_name]:
                del self.rooms[room_name]
            user_info["current_room"] = None

    def _get_room_members(self, room_name):
        with self.lock:
            if room_name not in self.rooms:
                return []
            return [self.clients[c]["username"] for c in self.rooms[room_name]]

    def _broadcast_system_event(self, room_name, message, members=None):
        if not members:
            members = self._get_room_members(room_name)
        packet = build_packet("SYSTEM_EVENT", {
            "room_name": room_name,
            "event_type": "room_event",
            "message": message,
            "members": members
        })
        self._broadcast_to_room(room_name, packet)

    def _broadcast_to_room(self, room_name, packet):
        with self.lock:
            if room_name not in self.rooms:
                return
            for c in self.rooms[room_name]:
                try:
                    send_packet(c, packet)
                except Exception as e:
                    self.logger.error(f"Error broadcasting to client in {room_name}: {e}")

    def _get_room_id(self, room_name):
        with get_db_connection() as db_conn:
            cursor = db_conn.cursor()
            cursor.execute("SELECT room_id FROM rooms WHERE room_name = ?", (room_name,))
            row = cursor.fetchone()
            if row:
                return row["room_id"]
        return None

    def _handle_room_chat_send(self, conn, req_id, payload):
        room_name = payload.get("room_name")
        message = payload.get("message")
        
        if not room_name or not message:
            send_packet(conn, build_error_packet("MISSING_FIELD", request_id=req_id))
            return
            
        user_info = self.clients[conn]
        if user_info["current_room"] != room_name:
            send_packet(conn, build_error_packet("NOT_IN_ROOM", request_id=req_id))
            return

        room_id = self._get_room_id(room_name)
        if not room_id:
            send_packet(conn, build_error_packet("ROOM_NOT_FOUND", request_id=req_id))
            return

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Save to DB
        try:
            with get_db_connection() as db_conn:
                cursor = db_conn.cursor()
                cursor.execute("""
                    INSERT INTO room_messages (room_id, server_id, sender_id, sender_username, message_type, content, created_at)
                    VALUES (?, ?, ?, ?, 'text', ?, ?)
                """, (room_id, self.server_id, user_info["user_id"], user_info["username"], message, now))
                db_conn.commit()
        except Exception as e:
            self.logger.error(f"Failed to save room message: {e}")
            send_packet(conn, build_error_packet("INTERNAL_ERROR", request_id=req_id))
            return

        # Broadcast
        broadcast_packet = build_packet("ROOM_CHAT_BROADCAST", {
            "room_id": room_id,
            "room_name": room_name,
            "sender_username": user_info["username"],
            "message": message,
            "timestamp": now
        }, request_id=req_id)
        
        self._broadcast_to_room(room_name, broadcast_packet)

    def _handle_room_history_request(self, conn, req_id, payload):
        room_name = payload.get("room_name")
        limit = payload.get("limit", 50)
        
        user_info = self.clients[conn]
        if user_info["current_room"] != room_name:
            send_packet(conn, build_error_packet("NOT_IN_ROOM", request_id=req_id))
            return

        room_id = self._get_room_id(room_name)
        if not room_id:
            send_packet(conn, build_error_packet("ROOM_NOT_FOUND", request_id=req_id))
            return

        try:
            with get_db_connection() as db_conn:
                cursor = db_conn.cursor()
                cursor.execute("""
                    SELECT sender_username, content, created_at, message_type
                    FROM room_messages
                    WHERE room_id = ? AND is_deleted = 0
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (room_id, limit))
                
                rows = cursor.fetchall()
                messages = []
                for row in reversed(rows): # Reverse to chronological
                    messages.append({
                        "sender_username": row["sender_username"],
                        "message": row["content"],
                        "timestamp": row["created_at"],
                        "message_type": row["message_type"]
                    })
                
                response = build_packet("ROOM_HISTORY_RESPONSE", {
                    "room_name": room_name,
                    "messages": messages
                }, request_id=req_id)
                send_packet(conn, response)
        except Exception as e:
            self.logger.error(f"Failed to fetch room history: {e}")
            send_packet(conn, build_error_packet("INTERNAL_ERROR", request_id=req_id))

    def _update_presence_gateway(self, user_id, username, status, room_name=None):
        """Notify Gateway about user presence change."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as g_sock:
                g_sock.connect((self.gateway_host, self.gateway_port))
                packet = build_packet("USER_ROOM_STATUS_UPDATE", {
                    "user_id": user_id,
                    "username": username,
                    "status": status,
                    "server_id": self.server_id,
                    "room_name": room_name
                })
                send_packet(g_sock, packet)
                # No need to wait for response for fire-and-forget notification
        except Exception as e:
            self.logger.error(f"Failed to update presence to Gateway: {e}")

    def _handle_file_list_request(self, conn, req_id, payload):
        room_name = payload.get("room_name")
        if not room_name:
            send_packet(conn, build_error_packet("MISSING_FIELD", request_id=req_id))
            return
            
        room_id = self._get_room_id(room_name)
        if not room_id:
            send_packet(conn, build_error_packet("ROOM_NOT_FOUND", request_id=req_id))
            return
            
        try:
            with get_db_connection() as db_conn:
                cursor = db_conn.cursor()
                cursor.execute("""
                    SELECT f.file_id, f.original_filename, f.size_bytes, u.username as uploader_username
                    FROM files f
                    JOIN users u ON f.uploader_id = u.user_id
                    WHERE f.room_id = ? AND f.status = 'available'
                """, (room_id,))
                
                files = [dict(row) for row in cursor.fetchall()]
                
                response = build_packet("FILE_LIST_RESPONSE", {
                    "room_name": room_name,
                    "files": files
                }, request_id=req_id)
                send_packet(conn, response)
        except Exception as e:
            self.logger.error(f"Failed to fetch file list: {e}")
            send_packet(conn, build_error_packet("INTERNAL_ERROR", request_id=req_id))

    def _handle_upload_init(self, conn, req_id, payload):
        room_id = payload.get("room_id")
        room_name = payload.get("room_name")
        filename = payload.get("filename")
        filesize = payload.get("filesize")
        chunk_size = payload.get("chunk_size")
        total_chunks = payload.get("total_chunks")
        checksum = payload.get("checksum_sha256")
        
        user_info = self.clients[conn]
        
        if not room_id and room_name:
            room_id = self._get_room_id(room_name)
            
        if not all([room_id, filename, filesize, chunk_size, total_chunks, checksum]):
            send_packet(conn, build_error_packet("MISSING_FIELD", request_id=req_id))
            return
            
        try:
            with get_db_connection() as db_conn:
                cursor = db_conn.cursor()
                from datetime import datetime
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                import os
                import hashlib
                from common.constants import PROJECT_ROOT
                storage_dir = os.path.join(PROJECT_ROOT, "storage", self.server_id, str(room_id))
                os.makedirs(storage_dir, exist_ok=True)
                stored_filename = f"{int(datetime.now().timestamp())}_{filename}"
                stored_path = os.path.join(storage_dir, stored_filename)
                
                cursor.execute("""
                    INSERT INTO files (room_id, server_id, uploader_id, original_filename, stored_filename, stored_path, size_bytes, checksum_sha256, chunk_size, total_chunks, status, uploaded_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'uploading', ?)
                """, (room_id, self.server_id, user_info["user_id"], filename, stored_filename, stored_path, filesize, checksum, chunk_size, total_chunks, now))
                file_id = cursor.lastrowid
                
                cursor.execute("""
                    INSERT INTO file_transfers (file_id, room_id, server_id, user_id, direction, status, total_chunks, started_at, last_activity_at)
                    VALUES (?, ?, ?, ?, 'upload', 'in_progress', ?, ?, ?)
                """, (file_id, room_id, self.server_id, user_info["user_id"], total_chunks, now, now))
                transfer_id = cursor.lastrowid
                db_conn.commit()
                
                send_packet(conn, build_packet("UPLOAD_READY", {
                    "transfer_id": transfer_id,
                    "start_chunk": 0
                }, request_id=req_id))
        except Exception as e:
            self.logger.error(f"Upload init failed: {e}")
            send_packet(conn, build_error_packet("INTERNAL_ERROR", request_id=req_id))

    def _handle_upload_chunk(self, conn, req_id, payload, binary_payload):
        transfer_id = payload.get("transfer_id")
        chunk_index = payload.get("chunk_index")
        
        try:
            with get_db_connection() as db_conn:
                cursor = db_conn.cursor()
                cursor.execute("""
                    SELECT f.stored_path, f.chunk_size, ft.status
                    FROM file_transfers ft
                    JOIN files f ON ft.file_id = f.file_id
                    WHERE ft.transfer_id = ?
                """, (transfer_id,))
                row = cursor.fetchone()
                if not row or row["status"] != "in_progress":
                    send_packet(conn, build_error_packet("INVALID_PACKET", request_id=req_id))
                    return
                    
                stored_path = row["stored_path"]
                chunk_size = row["chunk_size"]
                
                with open(stored_path, "ab" if chunk_index > 0 else "wb") as f:
                    f.write(binary_payload)
                    
                cursor.execute("""
                    INSERT INTO transfer_chunks (transfer_id, chunk_index, size_bytes, status)
                    VALUES (?, ?, ?, 'received')
                """, (transfer_id, chunk_index, len(binary_payload)))
                
                cursor.execute("""
                    UPDATE file_transfers SET completed_chunks = completed_chunks + 1, bytes_transferred = bytes_transferred + ? WHERE transfer_id = ?
                """, (len(binary_payload), transfer_id))
                db_conn.commit()
                
                send_packet(conn, build_packet("CHUNK_ACK", {
                    "transfer_id": transfer_id,
                    "chunk_index": chunk_index,
                    "status": "received"
                }, request_id=req_id))
        except Exception as e:
            self.logger.error(f"Upload chunk failed: {e}")

    def _handle_upload_finish(self, conn, req_id, payload):
        transfer_id = payload.get("transfer_id")
        
        try:
            with get_db_connection() as db_conn:
                cursor = db_conn.cursor()
                cursor.execute("""
                    SELECT f.file_id, f.stored_path, f.checksum_sha256, f.original_filename, f.room_id
                    FROM file_transfers ft
                    JOIN files f ON ft.file_id = f.file_id
                    WHERE ft.transfer_id = ?
                """, (transfer_id,))
                row = cursor.fetchone()
                
                if row:
                    import hashlib
                    sha256 = hashlib.sha256()
                    with open(row["stored_path"], "rb") as f:
                        for chunk in iter(lambda: f.read(65536), b""):
                            sha256.update(chunk)
                    calc_checksum = sha256.hexdigest()
                    
                    if calc_checksum == row["checksum_sha256"]:
                        cursor.execute("UPDATE files SET status = 'available' WHERE file_id = ?", (row["file_id"],))
                        cursor.execute("UPDATE file_transfers SET status = 'completed' WHERE transfer_id = ?", (transfer_id,))
                        db_conn.commit()
                        
                        send_packet(conn, build_packet("UPLOAD_SUCCESS", {
                            "transfer_id": transfer_id
                        }, request_id=req_id))
                        
                        # Broadcast system event
                        user_info = self.clients[conn]
                        cursor.execute("SELECT room_name FROM rooms WHERE room_id = ?", (row["room_id"],))
                        room_row = cursor.fetchone()
                        if room_row:
                            self._broadcast_system_event(room_row["room_name"], f"User {user_info['username']} uploaded {row['original_filename']}")
                    else:
                        send_packet(conn, build_error_packet("CHECKSUM_FAILED", request_id=req_id))
        except Exception as e:
            self.logger.error(f"Upload finish failed: {e}")
            send_packet(conn, build_error_packet("INTERNAL_ERROR", request_id=req_id))

    def _handle_download_request(self, conn, req_id, payload):
        file_id = payload.get("file_id")
        user_info = self.clients[conn]
        
        try:
            with get_db_connection() as db_conn:
                cursor = db_conn.cursor()
                cursor.execute("SELECT * FROM files WHERE file_id = ?", (file_id,))
                file_row = cursor.fetchone()
                
                if not file_row or file_row["status"] != "available":
                    send_packet(conn, build_error_packet("FILE_NOT_FOUND", request_id=req_id))
                    return
                
                from datetime import datetime
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute("""
                    INSERT INTO file_transfers (file_id, room_id, server_id, user_id, direction, status, total_chunks, started_at, last_activity_at)
                    VALUES (?, ?, ?, ?, 'download', 'in_progress', ?, ?, ?)
                """, (file_id, file_row["room_id"], self.server_id, user_info["user_id"], file_row["total_chunks"], now, now))
                transfer_id = cursor.lastrowid
                db_conn.commit()
                
                send_packet(conn, build_packet("DOWNLOAD_READY", {
                    "transfer_id": transfer_id,
                    "total_chunks": file_row["total_chunks"],
                    "chunk_size": file_row["chunk_size"],
                    "checksum_sha256": file_row["checksum_sha256"]
                }, request_id=req_id))
                
                # Start pushing chunks in a thread to avoid blocking client loop
                import threading
                threading.Thread(target=self._push_download_chunks, args=(conn, transfer_id, file_row), daemon=True).start()
        except Exception as e:
            self.logger.error(f"Download request failed: {e}")
            send_packet(conn, build_error_packet("INTERNAL_ERROR", request_id=req_id))

    def _push_download_chunks(self, conn, transfer_id, file_row):
        stored_path = file_row["stored_path"]
        chunk_size = file_row["chunk_size"]
        total_chunks = file_row["total_chunks"]
        
        try:
            with open(stored_path, "rb") as f:
                for i in range(total_chunks):
                    chunk_data = f.read(chunk_size)
                    import json
                    import struct
                    packet = build_packet("DOWNLOAD_CHUNK", {
                        "transfer_id": transfer_id,
                        "chunk_index": i
                    })
                    packet["payload_size"] = len(chunk_data)
                    header_json = json.dumps(packet).encode('utf-8')
                    try:
                        conn.sendall(struct.pack(">I", len(header_json)) + header_json + chunk_data)
                    except Exception as e:
                        self.logger.error(f"Error sending download chunk {i}: {e}")
                        break
        except Exception as e:
            self.logger.error(f"Failed to push download chunks: {e}")

    def _cleanup_client(self, conn):
        with self.lock:
            if conn in self.clients:
                user_info = self.clients[conn]
                if user_info["current_room"]:
                    self._leave_room_logic(conn)
                    # Notify gateway user is now back to 'waiting' or 'offline'
                    # If they disconnect, they are offline. Gateway will handle this via session cleanup too,
                    # but we can be explicit.
                    self._update_presence_gateway(user_info["user_id"], user_info["username"], "offline")
                del self.clients[conn]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NetCourier Process Server")
    parser.add_argument("--server-id", required=True, help="S1, S2, etc.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--gateway-host", default=DEFAULT_GATEWAY_HOST)
    parser.add_argument("--gateway-port", type=int, default=DEFAULT_GATEWAY_BACKEND_PORT)
    
    args = parser.parse_args()
    
    server = ProcessServer(args.server_id, args.host, args.port, args.gateway_host, args.gateway_port)
    server.start()
