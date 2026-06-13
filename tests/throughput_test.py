import socket
import time
import os
import hashlib
import argparse
import json
import struct
from common.protocol import send_packet, receive_packet, build_packet
from common.constants import DEFAULT_GATEWAY_HOST, DEFAULT_GATEWAY_CLIENT_PORT

class ThroughputClient:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.token = None
        self.gate_sock = None
        self.room_sock = None
        self.room_id = None
        self.room_name = None

    def receive_until(self, sock, expected_type):
        while True:
            header, payload = receive_packet(sock)
            if header["type"] == expected_type:
                return header, payload
            if header["type"] == "ERROR":
                return header, payload
            # Ignore or log others (like SYSTEM_EVENT)
            # print(f"[*] Skipping {header['type']} while waiting for {expected_type}")

    def connect_and_login(self):
        self.gate_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.gate_sock.connect((DEFAULT_GATEWAY_HOST, DEFAULT_GATEWAY_CLIENT_PORT))
        
        # Register if needed, then login
        send_packet(self.gate_sock, build_packet("REGISTER", {"username": self.username, "password": self.password}))
        receive_packet(self.gate_sock)
        
        send_packet(self.gate_sock, build_packet("LOGIN", {"username": self.username, "password": self.password}))
        header, _ = self.receive_until(self.gate_sock, "LOGIN_OK")
        if header["type"] == "LOGIN_OK":
            self.token = header["token"]
            return True
        return False

    def create_and_join_room(self, name):
        self.room_name = name
        send_packet(self.gate_sock, build_packet("CREATE_ROOM", {"room_name": name}, token=self.token))
        header, _ = receive_packet(self.gate_sock)
        if header["type"] == "ERROR": # Maybe exists
            send_packet(self.gate_sock, build_packet("JOIN_ROOM", {"room_name": name}, token=self.token))
            header, _ = receive_packet(self.gate_sock)
            
        if header["type"] in ["ROOM_ASSIGNED", "ROOM_LOCATION"]:
            payload = header["payload"]
            self.room_id = payload.get("room_id")
            host = payload["host"]
            port = payload["port"]
            
            # Connect to Room Server
            self.room_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.room_sock.connect((host, port))
            
            send_packet(self.room_sock, build_packet("AUTH_BACKEND", token=self.token))
            self.receive_until(self.room_sock, "AUTH_BACKEND_OK")
            
            send_packet(self.room_sock, build_packet("JOIN_ROOM_BACKEND", {"room_name": name}, token=self.token))
            self.receive_until(self.room_sock, "JOIN_ROOM_OK")
            return True
        return False

    def upload_file(self, file_path):
        filename = os.path.basename(file_path)
        filesize = os.path.getsize(file_path)
        chunk_size = 65536
        total_chunks = (filesize + chunk_size - 1) // chunk_size
        
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        checksum = sha256.hexdigest()
        
        start_time = time.time()
        
        send_packet(self.room_sock, build_packet("UPLOAD_INIT", {
            "room_id": self.room_id,
            "room_name": self.room_name,
            "filename": filename,
            "filesize": filesize,
            "chunk_size": chunk_size,
            "total_chunks": total_chunks,
            "checksum_sha256": checksum
        }, token=self.token))
        
        header, _ = self.receive_until(self.room_sock, "UPLOAD_READY")
        if header["type"] == "ERROR":
            print(f"[!] UPLOAD_INIT failed: {header['payload'].get('message')}")
            return 0, 0
            
        transfer_id = header["payload"]["transfer_id"]
        
        with open(file_path, "rb") as f:
            for i in range(total_chunks):
                chunk_data = f.read(chunk_size)
                packet = build_packet("UPLOAD_CHUNK", {"transfer_id": transfer_id, "chunk_index": i}, token=self.token)
                packet["payload_size"] = len(chunk_data)
                header_json = json.dumps(packet).encode('utf-8')
                self.room_sock.sendall(struct.pack(">I", len(header_json)) + header_json + chunk_data)
                self.receive_until(self.room_sock, "CHUNK_ACK")
                
        send_packet(self.room_sock, build_packet("UPLOAD_FINISH", {"transfer_id": transfer_id}, token=self.token))
        self.receive_until(self.room_sock, "UPLOAD_SUCCESS")
        
        duration = time.time() - start_time
        return filesize, duration

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--size-mb", type=int, default=5)
    args = parser.parse_args()
    
    file_path = f"test_{args.size_mb}mb.bin"
    if not os.path.exists(file_path):
        print(f"[*] Creating {args.size_mb}MB test file...")
        with open(file_path, "wb") as f:
            f.write(os.urandom(args.size_mb * 1024 * 1024))
            
    client = ThroughputClient("bench_user", "bench_pass")
    if not client.connect_and_login():
        print("[!] Login failed")
        return
        
    if not client.create_and_join_room("BenchRoom"):
        print("[!] Room join failed")
        return
        
    print(f"[*] Starting upload of {file_path}...")
    size, duration = client.upload_file(file_path)
    
    print("\n--- Throughput Test Results ---")
    print(f"File Size:  {size / (1024*1024):.2f} MB")
    print(f"Time Taken: {duration:.2f} s")
    print(f"Throughput: {(size / duration) / (1024*1024):.2f} MB/s")

if __name__ == "__main__":
    main()
