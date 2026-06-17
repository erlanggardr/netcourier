import socket
import threading
import time
import argparse
from common.protocol import send_packet, receive_packet, build_packet
from common.constants import DEFAULT_GATEWAY_HOST, DEFAULT_GATEWAY_CLIENT_PORT

class ChatTestClient:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.token = None
        self.gw_sock = None
        self.room_sock = None
        self.room_location = None
        self.received_messages = 0

    def connect_and_login(self):
        try:
            self.gw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.gw_sock.connect((DEFAULT_GATEWAY_HOST, DEFAULT_GATEWAY_CLIENT_PORT))
            
            req = build_packet("LOGIN", {"username": self.username, "password": self.password})
            send_packet(self.gw_sock, req)
            header, _ = receive_packet(self.gw_sock)
            
            if header["type"] == "LOGIN_OK":
                self.token = header["token"]
                return True
                
            req_reg = build_packet("REGISTER", {"username": self.username, "password": self.password})
            send_packet(self.gw_sock, req_reg)
            receive_packet(self.gw_sock)
            
            send_packet(self.gw_sock, req)
            header, _ = receive_packet(self.gw_sock)
            if header["type"] == "LOGIN_OK":
                self.token = header["token"]
                return True
            return False
        except Exception:
            return False

    def join_room_gateway(self, room_name):
        try:
            req = build_packet("JOIN_ROOM", {"room_name": room_name}, token=self.token)
            send_packet(self.gw_sock, req)
            header, _ = receive_packet(self.gw_sock)
            
            if header["type"] == "ERROR" and header.get("payload", {}).get("code") == "ROOM_NOT_FOUND":
                req_create = build_packet("CREATE_ROOM", {"room_name": room_name, "description": "Stress Test Room"}, token=self.token)
                send_packet(self.gw_sock, req_create)
                header_c, _ = receive_packet(self.gw_sock)
                if header_c["type"] == "ROOM_ASSIGNED":
                    req_join = build_packet("JOIN_ROOM", {"room_name": room_name}, token=self.token)
                    send_packet(self.gw_sock, req_join)
                    header_j, _ = receive_packet(self.gw_sock)
                    if header_j["type"] == "ROOM_LOCATION":
                        self.room_location = header_j["payload"]
                        return True
                return False

            if header["type"] == "ROOM_LOCATION":
                self.room_location = header["payload"]
                return True
            return False
        except Exception:
            return False

    def join_room_backend(self):
        try:
            self.room_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.room_sock.connect((self.room_location["host"], self.room_location["port"]))
            
            req_auth = build_packet("AUTH_BACKEND", {"room_id": self.room_location["room_id"]}, token=self.token)
            send_packet(self.room_sock, req_auth)
            receive_packet(self.room_sock)
            
            req_join = build_packet("JOIN_ROOM_BACKEND", {"room_name": self.room_location["room_name"]}, token=self.token)
            send_packet(self.room_sock, req_join)
            self.room_sock.settimeout(0.5)
            try:
                while True:
                    receive_packet(self.room_sock)
            except socket.timeout:
                pass
            self.room_sock.settimeout(None)
            return True
        except Exception:
            return False

    def send_chat(self, msg):
        req = build_packet("ROOM_CHAT_SEND", {"room_name": self.room_location["room_name"], "message": msg}, token=self.token)
        send_packet(self.room_sock, req)

    def listen_loop(self, expected_count):
        self.room_sock.settimeout(5.0)
        try:
            while self.received_messages < expected_count:
                header, _ = receive_packet(self.room_sock)
                if header["type"] == "ROOM_CHAT_BROADCAST":
                    self.received_messages += 1
        except socket.timeout:
            pass
        except Exception:
            pass

    def close(self):
        try:
            if self.gw_sock: self.gw_sock.close()
            if self.room_sock: self.room_sock.close()
        except Exception:
            pass

def run_chat_stress_test(num_clients, messages_per_client):
    print(f"[*] Starting Chat Broadcast Stress Test...")
    print(f"[*] Simulating {num_clients} clients in 1 room, each sending {messages_per_client} messages.")
    
    room_name = f"Stress_Room_{int(time.time())}"
    expected_total_messages = num_clients * messages_per_client
    clients = []
    
    for i in range(num_clients):
        c = ChatTestClient(f"spam_user_{i}_{int(time.time())}", "pass123")
        is_login = c.connect_and_login()
        is_gw = is_login and c.join_room_gateway(room_name)
        is_be = is_gw and c.join_room_backend()
        if is_be:
            clients.append(c)
        else:
            print(f"[!] Client {i} failed: Login={is_login}, Gateway={is_gw}, Backend={is_be}")
        time.sleep(0.05)
    
    print(f"[+] All {len(clients)} clients connected to {room_name}.")
    
    # Start listeners
    threads = []
    for c in clients:
        t = threading.Thread(target=c.listen_loop, args=(expected_total_messages,))
        threads.append(t)
        t.start()
        
    print("[*] Broadcasting messages...")
    start_time = time.time()
    
    # Spam
    for i in range(messages_per_client):
        for c in clients:
            c.send_chat(f"Spam message {i} from {c.username}")
            
    print(f"[*] Finished sending {expected_total_messages} requests. Waiting for receives...")
    
    for t in threads:
        t.join()
        
    duration = time.time() - start_time
    total_received = sum(c.received_messages for c in clients)
    
    # 20 clients each receiving 100 broadcasted messages = 2000 events total to process
    expected_received_across_all = expected_total_messages * len(clients)
    
    print("\n--- Chat Broadcast Stress Test Results ---")
    print(f"Total Time: {duration:.2f} seconds")
    print(f"Messages Sent: {expected_total_messages}")
    print(f"Total Broadcasts Processed (Expected): {expected_received_across_all}")
    print(f"Total Broadcasts Processed (Actual): {total_received}")
    
    if expected_received_across_all > 0:
        success_rate = (total_received / expected_received_across_all) * 100
        print(f"Success Rate: {success_rate:.2f}%")
        
        # Calculate Throughput
        if duration > 0:
            print(f"Throughput: {total_received / duration:.2f} broadcasts/second")
    
    for c in clients:
        c.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test NetCourier Chat Broadcast Throughput")
    parser.add_argument("--clients", type=int, default=20, help="Number of concurrent users in room")
    parser.add_argument("--messages", type=int, default=5, help="Messages sent by each user")
    args = parser.parse_args()
    
    run_chat_stress_test(args.clients, args.messages)
