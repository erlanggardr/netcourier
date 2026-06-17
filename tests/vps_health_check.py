import argparse
import sys
import time
from .client_sim import TestClient

def run_health_check(host, port):
    print(f"[*] Memulai Health Check ke VPS: {host}:{port}")
    
    username = f"vps_tester_{int(time.time())}"
    password = "secure_password"
    
    print(f"[*] 1. Mencoba koneksi dan login (Username: {username})...")
    client = TestClient(username, password, host=host, port=port)
    if not client.connect_and_login():
        print("[-] GAGAL: Tidak dapat terhubung atau login ke Gateway.")
        sys.exit(1)
    print("[+] BERHASIL: Koneksi & Login sukses.")
    
    print("\n[*] 2. Mencoba membuat Room baru...")
    room_name = f"VPS_Room_{int(time.time())}"
    if not client.create_room(room_name):
        print("[-] GAGAL: Tidak dapat membuat Room.")
        client.close()
        sys.exit(1)
    print(f"[+] BERHASIL: Room '{room_name}' berhasil dibuat dan dialokasikan oleh Load Balancer ke {client.assigned_server}.")
    
    print("\n[*] 3. Mencoba bergabung ke dalam Room...")
    assigned = client.join_room_backend()
    if not assigned:
        print("[-] GAGAL: Tidak dapat bergabung ke Room.")
        client.close()
        sys.exit(1)
    print(f"[+] BERHASIL: Bergabung ke Room di backend {assigned}.")
    
    print("\n[*] 4. Mencoba mengirim dan menerima pesan obrolan...")
    # Flush queue
    while not client.event_queue.empty():
        client.event_queue.get()
        
    client.send_chat("Halo VPS, ini pesan pengujian otomatis!")
    
    # Tunggu balasan (echo broadcast)
    chat_success = False
    timeout = 3
    start = time.time()
    while time.time() - start < timeout:
        if not client.event_queue.empty():
            ev = client.event_queue.get()
            if ev.get("type") == "CHAT_MESSAGE":
                print(f"[+] BERHASIL: Pesan diterima dari {ev.get('sender')}: {ev.get('message')}")
                chat_success = True
                break
        time.sleep(0.1)
        
    if not chat_success:
        print("[-] GAGAL: Pesan obrolan tidak diterima kembali (Broadcast mati atau timeout).")
        client.close()
        sys.exit(1)
        
    print("\n[*] 5. Mencoba menginisialisasi Upload File...")
    # Mencoba inisialisasi file berukuran kecil
    file_info = {
        "filename": "test_vps.txt",
        "filesize": 1024,
        "hash": "dummyhash123",
        "description": "File uji coba"
    }
    client.start_upload(file_info)
    
    # Menunggu UPLOAD_READY dari server
    upload_success = False
    start = time.time()
    while time.time() - start < timeout:
        if not client.event_queue.empty():
            ev = client.event_queue.get()
            if ev.get("type") == "UPLOAD_READY":
                print(f"[+] BERHASIL: Server merespons UPLOAD_READY. Transfer ID: {ev.get('transfer_id')}")
                upload_success = True
                break
        time.sleep(0.1)
        
    if not upload_success:
        print("[-] GAGAL: Inisialisasi upload gagal atau timeout.")
        client.close()
        sys.exit(1)

    print("\n[=== KESIMPULAN ===]")
    print(f"[+] SELAMAT! Semua fungsionalitas utama di VPS ({host}) berjalan dengan normal dan responsif.")
    
    client.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VPS Health Check for NetCourier")
    parser.add_argument("--host", type=str, required=True, help="IP atau Domain VPS Anda")
    parser.add_argument("--port", type=int, default=9000, help="Port Gateway (Default: 9000)")
    
    args = parser.parse_args()
    
    try:
        run_health_check(args.host, args.port)
    except KeyboardInterrupt:
        print("\n[*] Dihentikan oleh pengguna.")
    except Exception as e:
        print(f"\n[-] Terjadi kesalahan tidak terduga: {e}")
