import socket
import threading
import time
import argparse
from collections import Counter
from netcourier.common.protocol import send_packet, receive_packet, build_packet
from netcourier.common.constants import DEFAULT_GATEWAY_HOST, DEFAULT_GATEWAY_CLIENT_PORT

class TestClient:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.token = None
        self.sock = None
        self.assigned_server = None

    def connect_and_login(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((DEFAULT_GATEWAY_HOST, DEFAULT_GATEWAY_CLIENT_PORT))
            
            # 1. Try Login
            req = build_packet("LOGIN", {"username": self.username, "password": self.password})
            send_packet(self.sock, req)
            header, _ = receive_packet(self.sock)
            
            if header["type"] == "LOGIN_OK":
                self.token = header["token"]
                return True
            
            # 2. Try Register if login failed
            req_reg = build_packet("REGISTER", {"username": self.username, "password": self.password})
            send_packet(self.sock, req_reg)
            header, _ = receive_packet(self.sock)
            
            if header["type"] == "REGISTER_OK":
                # Now login again
                send_packet(self.sock, req)
                header, _ = receive_packet(self.sock)
                if header["type"] == "LOGIN_OK":
                    self.token = header["token"]
                    return True
                    
            return False
        except Exception as e:
            print(f"[!] Connection error for {self.username}: {e}")
            return False

    def create_room(self, room_name):
        try:
            req = build_packet("CREATE_ROOM", {"room_name": room_name, "description": "Load Test Room"}, token=self.token)
            send_packet(self.sock, req)
            header, _ = receive_packet(self.sock)
            if header["type"] == "ROOM_ASSIGNED":
                self.assigned_server = header["payload"]["server_id"]
                return True
            return False
        except Exception:
            return False
        
    def join_room(self, room_name):
        try:
            req = build_packet("JOIN_ROOM", {"room_name": room_name}, token=self.token)
            send_packet(self.sock, req)
            header, _ = receive_packet(self.sock)
            if header["type"] == "ROOM_LOCATION":
                return header["payload"]["server_id"]
            return None
        except Exception:
            return None

    def close(self):
        if self.sock:
            try:
                self.sock.close()
            except:
                pass

def client_worker(client_id, stats, lock):
    username = f"lb_user_{client_id}_{int(time.time())}"
    c = TestClient(username, "pass123")
    if not c.connect_and_login():
        return
        
    room_name = f"lb_room_{client_id}_{int(time.time())}"
    
    # 1. Create Room (triggers load balancer selection)
    if c.create_room(room_name):
        with lock:
            stats["created"] += 1
            stats["servers"][c.assigned_server] += 1
    else:
        with lock:
            stats["failed_create"] += 1
        
    # 2. Join Room to increase active clients on that server (affects load balancer score)
    assigned = c.join_room(room_name)
    if assigned:
        with lock:
            stats["joined"] += 1
    
    # Keep connection alive so the load score reflects the active client
    time.sleep(15)
    c.close()

def run_lb_test(num_clients):
    print(f"[*] Starting Load Balancer Test with {num_clients} concurrent clients...")
    
    stats = {
        "created": 0,
        "failed_create": 0,
        "joined": 0,
        "servers": Counter()
    }
    lock = threading.Lock()
    
    threads = []
    start_time = time.time()
    
    for i in range(num_clients):
        t = threading.Thread(target=client_worker, args=(i, stats, lock))
        threads.append(t)
        t.start()
        time.sleep(0.05) # Small stagger to prevent socket flood issues
        if i == num_clients // 2:
            print("[*] Waiting 6 seconds for server heartbeat to update load...")
            time.sleep(6.0)
        
    for t in threads:
        t.join()
        
    duration = time.time() - start_time
        
    print("\n--- Load Balancer Test Results ---")
    print(f"Total Time: {duration:.2f} seconds")
    print(f"Total Clients Attempted: {num_clients}")
    print(f"Rooms Created Successfully: {stats['created']}")
    print(f"Rooms Failed to Create: {stats['failed_create']}")
    print(f"Rooms Joined Successfully: {stats['joined']}")
    
    if stats["created"] > 0:
        print("\nServer Distribution (Load Balance Check):")
        for server_id, count in stats["servers"].items():
            percentage = (count / stats["created"]) * 100
            print(f"  - {server_id}: {count} rooms assigned ({percentage:.2f}%)")
    else:
        print("\n[!] No rooms were created. Ensure Gateway and Process Servers are running.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test NetCourier Load Balancer Distribution")
    parser.add_argument("--clients", type=int, default=50, help="Number of concurrent clients to simulate")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Gateway Host IP")
    parser.add_argument("--port", type=int, default=9000, help="Gateway Client Port")
    args = parser.parse_args()

    # Update global variables so TestClient uses them
    global DEFAULT_GATEWAY_HOST, DEFAULT_GATEWAY_CLIENT_PORT
    DEFAULT_GATEWAY_HOST = args.host
    DEFAULT_GATEWAY_CLIENT_PORT = args.port

    run_lb_test(args.clients)
