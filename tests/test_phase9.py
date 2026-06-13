import socket
import json
import struct
import time
from common.constants import DEFAULT_GATEWAY_HOST, DEFAULT_GATEWAY_CLIENT_PORT

def test_malformed_header():
    print("[*] Testing malformed header...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((DEFAULT_GATEWAY_HOST, DEFAULT_GATEWAY_CLIENT_PORT))
        
        # Send huge header length
        sock.sendall(struct.pack(">I", 1000000))
        
        # Should be disconnected or receive error
        data = sock.recv(1024)
        print(f"[+] Received: {data}")
    except Exception as e:
        print(f"[+] Error (expected): {e}")
    finally:
        sock.close()

def test_invalid_json():
    print("\n[*] Testing invalid JSON...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((DEFAULT_GATEWAY_HOST, DEFAULT_GATEWAY_CLIENT_PORT))
        
        header_raw = b"{invalid_json"
        sock.sendall(struct.pack(">I", len(header_raw)) + header_raw)
        
        data = sock.recv(1024)
        print(f"[+] Received: {data}")
    except Exception as e:
        print(f"[+] Error: {e}")
    finally:
        sock.close()

def test_large_payload():
    print("\n[*] Testing large payload...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((DEFAULT_GATEWAY_HOST, DEFAULT_GATEWAY_CLIENT_PORT))
        
        header = {
            "type": "PING",
            "request_id": "test-1",
            "payload_size": 30000000 # 30MB, exceeds 20MB limit
        }
        header_json = json.dumps(header).encode('utf-8')
        sock.sendall(struct.pack(">I", len(header_json)) + header_json)
        
        data = sock.recv(1024)
        print(f"[+] Received: {data}")
    except Exception as e:
        print(f"[+] Error: {e}")
    finally:
        sock.close()

if __name__ == "__main__":
    # Note: These tests require the Gateway to be running
    try:
        test_malformed_header()
        test_invalid_json()
        test_large_payload()
    except ConnectionRefusedError:
        print("[!] Gateway not running. Please start it first.")
