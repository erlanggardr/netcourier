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
from gateway.presence_service import PresenceService
from gateway.pm_service import PMService
from gateway.backend_service import BackendService
from gateway.load_balancer import LoadBalancer
from gateway.room_directory import RoomDirectoryService

class Gateway:
    def __init__(self, host, client_port, backend_port):
        self.host = host
        self.client_port = client_port
        self.backend_port = backend_port
        
        self.logger = setup_logging("gateway")
        self.auth_service = AuthService()
        self.presence_service = PresenceService()
        self.pm_service = PMService()
        
        self.backend_service = BackendService()
        self.load_balancer = LoadBalancer(self.backend_service)
        self.room_directory = RoomDirectoryService(self.load_balancer, self.backend_service)
        
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
        self.backend_service.stop()

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
                        
                        user_id = self.active_sessions[token]["user_id"]
                        username = self.active_sessions[token]["username"]
                        
                        if msg_type == "LIST_ONLINE_USERS":
                            self._handle_list_online_users(conn, req_id)
                        elif msg_type == "PRIVATE_MESSAGE_SEND":
                            self._handle_private_message_send(conn, req_id, json_payload, user_id, username)
                        elif msg_type == "PM_HISTORY_REQUEST":
                            self._handle_pm_history_request(conn, req_id, json_payload, user_id)
                        elif msg_type == "LIST_ROOMS":
                            self._handle_list_rooms(conn, req_id)
                        elif msg_type == "CREATE_ROOM":
                            self._handle_create_room(conn, req_id, json_payload, user_id)
                        elif msg_type == "JOIN_ROOM":
                            self._handle_join_room(conn, req_id, json_payload)
                        else:
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
                self.presence_service.update_presence(user["user_id"], username, "online", active_room="waiting")
            
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
                session_info = self.active_sessions[token]
                username = session_info["username"]
                user_id = session_info["user_id"]
                del self.active_sessions[token]
                if self.user_to_token.get(username) == token:
                    del self.user_to_token[username]
                self.presence_service.update_presence(user_id, username, "offline")
                self.logger.info(f"Session cleaned up for user: {username}")

    def _handle_list_online_users(self, conn, req_id):
        users = self.presence_service.get_online_users()
        send_packet(conn, build_packet("ONLINE_USERS_RESPONSE", {"users": users}, request_id=req_id))

    def _handle_private_message_send(self, conn, req_id, payload, sender_id, sender_username):
        recipient_username = payload.get("recipient_username")
        content = payload.get("content")
        
        recipient_id = self.pm_service.get_user_id_by_username(recipient_username)
        if not recipient_id:
            send_packet(conn, build_error_packet("USER_NOT_FOUND", request_id=req_id))
            return

        # Check if recipient is online
        recipient_token = self.user_to_token.get(recipient_username)
        if recipient_token and recipient_token in self.active_sessions:
            # Recipient is online
            status = "delivered"
            self.pm_service.store_pm(sender_id, sender_username, recipient_id, recipient_username, content, status)
            
            # Send PM_STATUS to sender
            send_packet(conn, build_packet("PRIVATE_MESSAGE_STATUS", {
                "recipient_username": recipient_username,
                "status": "delivered"
            }, request_id=req_id))
            
            # Send PM_RECEIVED to recipient
            recipient_conn = self.active_sessions[recipient_token]["socket"]
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            try:
                send_packet(recipient_conn, build_packet("PRIVATE_MESSAGE_RECEIVED", {
                    "sender_username": sender_username,
                    "content": content,
                    "timestamp": now_str
                }))
            except Exception as e:
                self.logger.error(f"Failed to deliver PM to {recipient_username}: {e}")
                # Fallback to stored_offline if delivery fails?
        else:
            # Recipient is offline
            status = "stored_offline"
            self.pm_service.store_pm(sender_id, sender_username, recipient_id, recipient_username, content, status)
            
            # Send PM_STATUS to sender
            send_packet(conn, build_packet("PRIVATE_MESSAGE_STATUS", {
                "recipient_username": recipient_username,
                "status": "stored_offline"
            }, request_id=req_id))

    def _handle_pm_history_request(self, conn, req_id, payload, user_id):
        other_username = payload.get("other_username")
        other_user_id = self.pm_service.get_user_id_by_username(other_username)
        
        if not other_user_id:
            send_packet(conn, build_error_packet("USER_NOT_FOUND", request_id=req_id))
            return
            
        history = self.pm_service.get_pm_history(user_id, other_user_id)
        send_packet(conn, build_packet("PM_HISTORY_RESPONSE", {
            "other_username": other_username,
            "messages": history
        }, request_id=req_id))

    def _handle_list_rooms(self, conn, req_id):
        rooms = self.room_directory.get_room_list()
        send_packet(conn, build_packet("ROOM_LIST_RESPONSE", {"rooms": rooms}, request_id=req_id))

    def _handle_create_room(self, conn, req_id, payload, user_id):
        room_name = payload.get("room_name")
        description = payload.get("description", "")
        
        success, error_code, data = self.room_directory.create_room(room_name, description, user_id)
        if success:
            send_packet(conn, build_packet("ROOM_ASSIGNED", data, request_id=req_id))
        else:
            send_packet(conn, build_error_packet(error_code, request_id=req_id))

    def _handle_join_room(self, conn, req_id, payload):
        room_name = payload.get("room_name")
        
        success, error_code, data = self.room_directory.join_room(room_name)
        if success:
            send_packet(conn, build_packet("ROOM_LOCATION", data, request_id=req_id))
        else:
            send_packet(conn, build_error_packet(error_code, request_id=req_id))

    def _handle_backend(self, conn, addr):
        self.logger.info(f"New backend connection from {addr}")
        current_server_id = None
        try:
            with conn:
                while self.running:
                    header, binary_payload = receive_packet(conn)
                    msg_type = header.get("type")
                    req_id = header.get("request_id")
                    payload = header.get("payload", {})
                    
                    if msg_type == "REGISTER_BACKEND":
                        server_id = payload.get("server_id")
                        host = payload.get("host")
                        port = payload.get("port")
                        self.backend_service.register_backend(server_id, host, port, conn)
                        current_server_id = server_id
                        send_packet(conn, build_packet("BACKEND_REGISTERED", request_id=req_id))
                        
                    elif msg_type == "HEARTBEAT":
                        server_id = payload.get("server_id")
                        stats = payload.get("stats", {})
                        self.backend_service.update_heartbeat(server_id, stats)
                        send_packet(conn, build_packet("HEARTBEAT_ACK", request_id=req_id))
                        
                    elif msg_type == "VALIDATE_TOKEN":
                        token = payload.get("token")
                        with self.lock:
                            if token in self.active_sessions:
                                session = self.active_sessions[token]
                                send_packet(conn, build_packet("TOKEN_VALID", {
                                    "user_id": session["user_id"],
                                    "username": session["username"]
                                }, request_id=req_id))
                            else:
                                send_packet(conn, build_packet("TOKEN_INVALID", request_id=req_id))
                    
                    elif msg_type == "USER_ROOM_STATUS_UPDATE":
                        # Used by Process Server to notify user joined/left a room
                        user_id = payload.get("user_id")
                        username = payload.get("username")
                        status = payload.get("status") # 'in_room' or 'waiting'
                        server_id = payload.get("server_id")
                        active_room = payload.get("room_name")
                        self.presence_service.update_presence(user_id, username, status, server_id, active_room)
                        send_packet(conn, build_packet("SYSTEM_EVENT_ACK", request_id=req_id))

        except (ConnectionError, socket.error):
            if current_server_id:
                self.logger.warning(f"Backend {current_server_id} disconnected unexpectedly.")
        except Exception as e:
            self.logger.exception(f"Error handling backend {addr}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NetCourier Gateway")
    parser.add_argument("--host", default=DEFAULT_GATEWAY_HOST)
    parser.add_argument("--client-port", type=int, default=DEFAULT_GATEWAY_CLIENT_PORT)
    parser.add_argument("--backend-port", type=int, default=DEFAULT_GATEWAY_BACKEND_PORT)
    parser.add_argument("--debug", action="store_true")
    
    args = parser.parse_args()
    
    gateway = Gateway(args.host, args.client_port, args.backend_port)
    gateway.start()
