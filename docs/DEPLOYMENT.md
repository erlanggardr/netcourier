# Deployment Guide - NetCourier

Dokumen ini menjelaskan cara menjalankan NetCourier di localhost, LAN, dan VPS.

---

## 1. Deployment Modes

## 1.1 Localhost Demo

Semua proses berjalan di satu laptop dengan port berbeda.

```txt
Gateway: 127.0.0.1:9000
Gateway backend-control: 127.0.0.1:9001
Server S1: 127.0.0.1:9101
Server S2: 127.0.0.1:9102
Database: SQLite local / PostgreSQL local
```

Cocok untuk:
- development,
- demo aman,
- testing awal.

---

## 1.2 LAN Demo

Gateway dan Process Server berjalan di satu laptop. Client lain connect lewat IP LAN.

```txt
Gateway: 192.168.1.10:9000
S1: 192.168.1.10:9101
S2: 192.168.1.10:9102
```

Cocok untuk:
- demo multi-client dari beberapa laptop,
- simulasi jaringan lokal.

---

## 1.3 VPS Demo

Gateway dan Process Server berjalan di VPS.

```txt
Gateway: <VPS_IP>:9000
S1: <VPS_IP>:9101
S2: <VPS_IP>:9102
```

Cocok untuk:
- bonus deployment,
- demo online.

---

## 2. Running Locally

Terminal 1:

```bash
python gateway/main.py --host 0.0.0.0 --client-port 9000 --backend-port 9001
```

Terminal 2:

```bash
python server/server.py --server-id S1 --host 0.0.0.0 --port 9101 --gateway-host 127.0.0.1 --gateway-port 9001
```

Terminal 3:

```bash
python server/server.py --server-id S2 --host 0.0.0.0 --port 9102 --gateway-host 127.0.0.1 --gateway-port 9001
```

Terminal 4:

```bash
python client/client.py --gateway-host 127.0.0.1 --gateway-port 9000
```

---

## 3. Running on LAN

Cari IP laptop server:

```bash
ipconfig
```

atau Linux:

```bash
ip addr
```

Client connect ke:

```bash
python client/client.py --gateway-host 192.168.1.10 --gateway-port 9000
```

Pastikan firewall mengizinkan:
- 9000/tcp,
- 9101/tcp,
- 9102/tcp.

---

## 4. Running on VPS Ubuntu

Install dependency:

```bash
sudo apt update
sudo apt install python3 python3-pip tmux ufw
```

Buka port:

```bash
sudo ufw allow 9000/tcp
sudo ufw allow 9101/tcp
sudo ufw allow 9102/tcp
sudo ufw enable
```

Jalankan dengan tmux:

```bash
tmux new -s gateway
python3 gateway/main.py --host 0.0.0.0 --client-port 9000 --backend-port 9001
```

```bash
tmux new -s s1
python3 server/server.py --server-id S1 --host 0.0.0.0 --port 9101 --gateway-host 127.0.0.1 --gateway-port 9001
```

```bash
tmux new -s s2
python3 server/server.py --server-id S2 --host 0.0.0.0 --port 9102 --gateway-host 127.0.0.1 --gateway-port 9001
```

Client:

```bash
python3 client/client.py --gateway-host <VPS_IP> --gateway-port 9000
```

---

## 5. Environment Variables

Gunakan `.env` atau config file.

```txt
GATEWAY_HOST=0.0.0.0
GATEWAY_CLIENT_PORT=9000
GATEWAY_BACKEND_PORT=9001
DATABASE_URL=sqlite:///data/netcourier.db
MAX_FILE_SIZE_MB=100
CHUNK_SIZE=65536
HEARTBEAT_INTERVAL=5
HEARTBEAT_TIMEOUT=15
```

Jangan commit `.env`.

---

## 6. Storage Layout

```txt
storage/
├── S1/
│   └── rooms/
│       └── fp-jaringan/
└── S2/
    └── rooms/
        └── kelompok-a/
```

---

## 7. Deployment Recommendation

Untuk final project:
1. Demo utama: localhost atau LAN.
2. Bonus: VPS jika fitur sudah stabil.
3. Jangan memprioritaskan VPS sebelum fitur utama selesai.

---

## 8. Nginx Note

Nginx tidak dipakai sebagai load balancer utama karena NetCourier membutuhkan room-aware routing.

Load balancing utama dibuat di Gateway Python agar paham:
- room name,
- room mapping,
- server load,
- room affinity.

Nginx boleh digunakan sebagai optional public TCP proxy, tetapi bukan inti project.

---

## 9. Deployment Checklist

- [ ] Gateway running.
- [ ] S1 running.
- [ ] S2 running.
- [ ] Backend heartbeat diterima Gateway.
- [ ] Client bisa login.
- [ ] Client bisa create room.
- [ ] Room diarahkan ke S1/S2.
- [ ] Client bisa PM.
- [ ] Client bisa chat room.
- [ ] Upload/download file berhasil.
- [ ] Firewall port terbuka.
- [ ] Log tersimpan.
