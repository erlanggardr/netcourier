import socket
import threading
import logging
import argparse
import sys
import uuid
import hashlib
from datetime import datetime

from common.constants import (
    DEFAULT_GATEWAY_HOST,
    DEFAULT_GATEWAY_CLIENT_PORT,
    DEFAULT_GATEWAY_BACKEND_PORT
)
from common.protocol import receive_packet, send_packet, build_packet, build_error_packet
from common.db import initialize_db
from common.logging_config import setup_logging
from gateway.auth_service import AuthService

class Gateway:
    def __init__(self, host, client_port, backend_port):
        self.host = host
        self.client_port = client_port
        self.backend_port = backend_port
        
        self.logger = setup_logging("gateway")
        self.auth_service = AuthService()
        
        # session_token -> {user_id, username, socket, last_seen}
        self.active_sessions = {}
        # username -> session_token
        self.user_to_token = {}
        
        self.running = False
        self.lock = threading.Lock()

    def start(self):
        self.logger.info("Initializing database...")
        initialize_db()
        self.running = True
        
        # Start client-facing server
        client_thread = threading.Thread(target=self._run_client_server, daemon=True)
        client_thread.start()
        
        # Start backend-control server
        backend_thread = threading.Thread(target=self._run_backend_server, daemon=True)
        backend_thread.start()
        
        self.logger.info(f"Gateway started. Client port: {self.client_port}, Backend port: {self.backend_port}")
        
        try:
            while self.running:
                threading.Event().wait(1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        self.logger.info("Stopping Gateway...")
        self.running = False

    def _run_client_server(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((self.host, self.client_port))
            s.listen()
            self.logger.info(f"Client-facing server listening on {self.host}:{self.client_port}")
            
            while self.running:
                conn, addr = s.accept()
                threading.Thread(target=self._handle_client, args=(conn, addr), daemon=True).start()

    def _run_backend_server(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((self.host, self.backend_port))
            s.listen()
            self.logger.info(f"Backend-control server listening on {self.host}:{self.backend_port}")
            
            while self.running:
                conn, addr = s.accept()
                threading.Thread(target=self._handle_backend, args=(conn, addr), daemon=True).start()

    def _handle_client(self, conn, addr):
        self.logger.info(f"New client connection from {addr}")
        current_token = None
        try:
            with conn:
                while self.running:
                    header, binary_payload = receive_packet(conn)
                    msg_type = header.get("type")
                    req_id = header.get("request_id")
                    token = header.get("token")
                    json_payload = header.get("payload", {})
                    
                    self.logger.debug(f"Received {msg_type} from {addr}")
                    
                    if msg_type == "REGISTER":
                        self._handle_register(conn, req_id, json_payload)
                    elif msg_type == "LOGIN":
                        token = self._handle_login(conn, req_id, json_payload, addr)
                        if token:
                            current_token = token
                    elif msg_type == "LOGOUT":
                        self._handle_logout(conn, req_id, token)
                        current_token = None
                    elif msg_type == "PING":
                        send_packet(conn, build_packet("PONG", request_id=req_id))
                    else:
                        # Other types require authentication
                        if not token or token not in self.active_sessions:
                            send_packet(conn, build_error_packet("INVALID_TOKEN", request_id=req_id))
                            continue
                        
                        # Forward to specialized handlers in Phase 3+
                        self.logger.warning(f"Unhandled message type: {msg_type}")
                        
        except (ConnectionError, socket.error):
            self.logger.info(f"Client {addr} disconnected")
        except Exception as e:
            self.logger.exception(f"Error handling client {addr}: {e}")
        finally:
            if current_token:
                self._cleanup_session(current_token)

    def _handle_register(self, conn, req_id, payload):
        username = payload.get("username")
        password = payload.get("password")
        display_name = payload.get("display_name", username)
        
        success, error_code = self.auth_service.register_user(username, password, display_name)
        if success:
            send_packet(conn, build_packet("REGISTER_OK", {"username": username}, request_id=req_id))
        else:
            send_packet(conn, build_error_packet(error_code, request_id=req_id))

    def _handle_login(self, conn, req_id, payload, addr):
        username = payload.get("username")
        password = payload.get("password")
        
        user = self.auth_service.authenticate(username, password)
        if user:
            with self.lock:
                # Handle duplicate login
                if username in self.user_to_token:
                    old_token = self.user_to_token[username]
                    self.logger.info(f"User {username} already logged in. Disconnecting old session.")
                    # In a real app, we might notify the old socket
                    self._cleanup_session(old_token)
                
                token = str(uuid.uuid4())
                self.active_sessions[token] = {
                    "user_id": user["user_id"],
                    "username": username,
                    "socket": conn,
                    "last_seen": datetime.now()
                }
                self.user_to_token[username] = token
            
            send_packet(conn, build_packet("LOGIN_OK", {
                "user_id": user["user_id"],
                "username": username,
                "display_name": user["display_name"]
            }, request_id=req_id, token=token))
            return token
        else:
            send_packet(conn, build_error_packet("INVALID_CREDENTIALS", request_id=req_id))
            return None

    def _handle_logout(self, conn, req_id, token):
        if token and token in self.active_sessions:
            self._cleanup_session(token)
            send_packet(conn, build_packet("LOGOUT_OK", request_id=req_id))
        else:
            send_packet(conn, build_error_packet("INVALID_TOKEN", request_id=req_id))

    def _cleanup_session(self, token):
        with self.lock:
            if token in self.active_sessions:
                username = self.active_sessions[token]["username"]
                del self.active_sessions[token]
                if self.user_to_token.get(username) == token:
                    del self.user_to_token[username]
                self.logger.info(f"Session cleaned up for user: {username}")

    def _handle_backend(self, conn, addr):
        self.logger.info(f"New backend connection from {addr}")
        # To be implemented in Phase 4
        conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NetCourier Gateway")
    parser.add_argument("--host", default=DEFAULT_GATEWAY_HOST)
    parser.add_argument("--client-port", type=int, default=DEFAULT_GATEWAY_CLIENT_PORT)
    parser.add_argument("--backend-port", type=int, default=DEFAULT_GATEWAY_BACKEND_PORT)
    parser.add_argument("--debug", action="store_true")
    
    args = parser.parse_args()
    
    gateway = Gateway(args.host, args.client_port, args.backend_port)
    gateway.start()
