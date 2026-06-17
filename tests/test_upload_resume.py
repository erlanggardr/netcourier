import socket
import os
import time
import hashlib
from common.protocol import send_packet, receive_packet, build_packet
from common.constants import DEFAULT_GATEWAY_HOST, DEFAULT_GATEWAY_CLIENT_PORT

TEST_DIR = "tests/uploadbinarytest"

def get_checksum(file_path):
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()

class UploadResumeClient:
    def __init__(self, username):
        self.username = username
        self.password = "pass123"
        self.token = None
        self.gw_sock = None
        self.room_sock = None
        self.room_location = None

    def connect_and_auth(self):
        self.gw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.gw_sock.connect((DEFAULT_GATEWAY_HOST, DEFAULT_GATEWAY_CLIENT_PORT))
        
        req = build_packet("REGISTER", {"username": self.username, "password": self.password})
        send_packet(self.gw_sock, req)
        receive_packet(self.gw_sock)
        
        req = build_packet("LOGIN", {"username": self.username, "password": self.password})
        send_packet(self.gw_sock, req)
        h, _ = receive_packet(self.gw_sock)
        self.token = h["token"]
        
        req = build_packet("JOIN_ROOM", {"room_name": "Resume_Room"}, token=self.token)
        send_packet(self.gw_sock, req)
        h, _ = receive_packet(self.gw_sock)
        
        if h["type"] == "ERROR":
            req_c = build_packet("CREATE_ROOM", {"room_name": "Resume_Room", "description": "Res"}, token=self.token)
            send_packet(self.gw_sock, req_c)
            receive_packet(self.gw_sock)
            send_packet(self.gw_sock, req)
            h, _ = receive_packet(self.gw_sock)
            
        self.room_location = h["payload"]
        
    def connect_room(self):
        self.room_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.room_sock.connect((self.room_location["host"], self.room_location["port"]))
        req_auth = build_packet("AUTH_BACKEND", {"room_id": self.room_location["room_id"]}, token=self.token)
        send_packet(self.room_sock, req_auth)
        receive_packet(self.room_sock)
        req_join = build_packet("JOIN_ROOM_BACKEND", {"room_name": self.room_location["room_name"]}, token=self.token)
        send_packet(self.room_sock, req_join)
        receive_packet(self.room_sock)

def run_resume_test():
    print("[*] Starting Upload Resiliency Test (Disconnect & Resume)...")
    os.makedirs(TEST_DIR, exist_ok=True)
    test_file = os.path.join(TEST_DIR, "resume_test.bin")
    
    print("[*] Generating 10MB test file...")
    file_size = 10 * 1024 * 1024
    with open(test_file, "wb") as f:
        f.write(os.urandom(file_size))
        
    checksum = get_checksum(test_file)
    print(f"[*] Original SHA-256: {checksum}")
    
    c = UploadResumeClient(f"resume_user_{int(time.time())}")
    c.connect_and_auth()
    c.connect_room()
    
    # 1. INIT
    chunk_size = 1024 * 1024 # 1MB chunks
    total_chunks = (file_size + chunk_size - 1) // chunk_size
    req_init = build_packet("UPLOAD_INIT", {
        "room_id": c.room_location["room_id"],
        "filename": "resume_test.bin",
        "filesize": file_size,
        "chunk_size": chunk_size,
        "total_chunks": total_chunks,
        "checksum_sha256": checksum
    }, token=c.token)
    
    send_packet(c.room_sock, req_init)
    h, _ = receive_packet(c.room_sock)
    transfer_id = h["payload"]["transfer_id"]
    print(f"[+] Upload initialized. Transfer ID: {transfer_id}")
    
    # 2. Upload half
    print("[*] Uploading first half of the chunks...")
    with open(test_file, "rb") as f:
        for i in range(total_chunks // 2):
            data = f.read(chunk_size)
            req_c = build_packet("UPLOAD_CHUNK", {"transfer_id": transfer_id, "chunk_index": i, "chunk_size": len(data)}, token=c.token)
            send_packet(c.room_sock, req_c, data)
            receive_packet(c.room_sock)
            print(f"  - Chunk {i} sent successfully.")
            
    # 3. Simulate Disconnect
    print("\n[!] SIMULATING UNEXPECTED CONNECTION DROP...")
    c.room_sock.close()
    time.sleep(2)
    
    # 4. Resume
    print("[*] Reconnecting...")
    c.connect_room()
    
    print("[*] Requesting resume status...")
    req_resume = build_packet("RESUME_TRANSFER", {"transfer_id": transfer_id, "direction": "upload"}, token=c.token)
    send_packet(c.room_sock, req_resume)
    h, _ = receive_packet(c.room_sock)
    
    start_chunk = h["payload"].get("start_chunk", 0)
    print(f"[+] Server responded: resume upload starting from chunk index {start_chunk}")
    
    # 5. Send remaining chunks
    print("[*] Sending remaining chunks...")
    with open(test_file, "rb") as f:
        f.seek(start_chunk * chunk_size)
        for i in range(start_chunk, total_chunks):
            data = f.read(chunk_size)
            req_c = build_packet("UPLOAD_CHUNK", {"transfer_id": transfer_id, "chunk_index": i, "chunk_size": len(data)}, token=c.token)
            send_packet(c.room_sock, req_c, data)
            receive_packet(c.room_sock)
            print(f"  - Chunk {i} sent successfully.")
            
    # 6. Finish
    print("[*] Sending UPLOAD_FINISH signal...")
    req_f = build_packet("UPLOAD_FINISH", {"transfer_id": transfer_id}, token=c.token)
    send_packet(c.room_sock, req_f)
    h, _ = receive_packet(c.room_sock)
    
    if h["type"] == "UPLOAD_SUCCESS":
        print("\n[+] SUCCESS! Server assembled the file and checksum matched perfectly after the resumed transfer.")
    else:
        print(f"\n[-] FAILED! Server responded with error: {h}")
        
    c.gw_sock.close()
    c.room_sock.close()

if __name__ == "__main__":
    run_resume_test()
