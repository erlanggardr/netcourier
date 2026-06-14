# NetCourier

**NetCourier** adalah aplikasi **Multi-Chat Room berbasis TCP Socket** dengan fitur unggulan **Reliable File Transfer**. Project ini dibuat untuk final project Pemrograman Jaringan.

NetCourier memenuhi kategori **Aplikasi Multi-Chat Rooms** dengan fitur wajib:
- authentication sederhana,
- banyak room,
- satu room banyak client,
- create room,
- join room,
- leave room,
- broadcast message,
- private message,
- online user list,
- room list,
- chat history,
- timestamp message,
- server logging,
- TCP socket,
- multithreading/select,
- serialization.

Fitur pembeda NetCourier:
- private message global melalui Gateway,
- room chat dan file transfer melalui Process Server,
- file transfer dengan chunking,
- checksum SHA-256,
- progress upload/download,
- resume transfer,
- load balancing berbasis room affinity,
- latency dan throughput measurement,
- load testing.

---

## 1. Konsep Singkat

NetCourier memisahkan komunikasi menjadi dua jenis:

1. **Global communication**
   - Ditangani oleh Gateway.
   - Berisi login, register, online user list, private message, PM history, room directory, dan load balancing.

2. **Room communication**
   - Ditangani oleh Process Server.
   - Berisi room chat, broadcast message, room history, file upload, file download, chunking, checksum, dan resume transfer.

Client dapat tetap menerima private message walaupun sedang berada di dalam room, karena client menjaga koneksi ke Gateway selama aplikasi berjalan.

UI utama NetCourier menggunakan **Web-based UI** (Single Page HTML/JS) yang dihubungkan ke server TCP via **HTTP & JSON API Bridge** di `web_api/server.py`. Pengguna mengakses aplikasi dengan membuka browser ke server HTTP lokal.

---

## 2. Arsitektur Ringkas

```txt
Web Client (Browser)
   |
   | HTTP REST / JSON API & SSE / Long-Polling
   v
Web API Server / HTTP Bridge (client/main.py)
   |
   +--- TCP Socket A: login, PM, online user, room directory ---> Gateway
   |
   +--- TCP Socket B: room chat, file transfer -----------------> Process Server (S1/S2)
```

---

## 3. Komponen Utama

| Komponen | Tugas |
|---|---|
| Web Client (Browser) | Web UI user, login, PM, join room, room chat, upload/download file |
| Web API / HTTP Bridge | Jembatan penerjemah request HTTP/JSON ke koneksi TCP socket Gateway & Process Server |
| Gateway | Auth, session, PM global, online user, room directory, load balancing |
| Process Server | Room chat, broadcast, file transfer, chunking, checksum, resume |
| Central Database | Users, sessions, rooms, chat history, PM history, file metadata, logs |
| File Storage | Menyimpan file fisik per server/room |

---

## 4. Tech Stack

| Bagian | Teknologi |
|---|---|
| Bahasa | Python |
| Networking | `socket` |
| Concurrency | `threading` atau `select` |
| Serialization | JSON |
| Packet framing | Length-prefixed TCP frame |
| Database | PostgreSQL direkomendasikan, SQLite boleh untuk demo lokal |
| Password hashing | `hashlib.pbkdf2_hmac` atau `bcrypt` jika tersedia |
| Checksum file | SHA-256 |
| Logging | Python `logging` |
| UI | Web-based HTML/CSS/JS (SPA) |
| UI modules | Vanilla HTML/CSS/JS, Web API Server HTTP, long-polling /api/events |

---

## 5. Struktur Folder Rekomendasi

```txt
netcourier/
├── gateway/
│   ├── main.py
│   ├── auth_service.py
│   ├── pm_service.py
│   ├── room_directory.py
│   ├── load_balancer.py
│   └── presence_service.py
│
├── server/
│   ├── server.py
│   ├── client_handler.py
│   ├── room_service.py
│   ├── chat_service.py
│   ├── file_transfer_service.py
│   ├── transfer_state.py
│   └── storage_service.py
│
├── client/
│   ├── main.py (Web API & UI Server launcher)
│   ├── gateway_connection.py (Gateway socket helper)
│   └── room_connection.py (Room server socket helper)
├── web_ui/
│   ├── index.html
│   └── app.js
├── web_api/
│   └── server.py (Custom HTTP Server / TCP Bridge)
│
├── common/
│   ├── protocol.py
│   ├── packet.py
│   ├── constants.py
│   ├── errors.py
│   └── utils.py
│
├── data/
│   └── netcourier.db
│
├── storage/
│   ├── S1/
│   └── S2/
│
├── tests/
│   ├── load_test.py
│   ├── malformed_packet_test.py
│   ├── reconnect_test.py
│   └── throughput_test.py
│
├── docs/
│   ├── REQUIREMENTS.md
│   ├── FEATURE_SPEC.md
│   ├── ARCHITECTURE.md
│   ├── API_SPEC.md
│   ├── DATABASE.md
│   ├── UI_UX.md
│   ├── TESTING.md
│   ├── SECURITY.md
│   ├── DEPLOYMENT.md
│   └── GLOSSARY.md
│
├── ai/
│   └── AI_CONTEXT.md
│
├── TASKS.md
├── CHANGELOG.md
└── README.md
```

---

## 6. Cara Menjalankan Versi Demo Lokal

### Terminal 1: Gateway

```bash
python gateway/main.py --host 0.0.0.0 --client-port 9000 --backend-port 9001
```

### Terminal 2: Process Server S1

```bash
python server/main.py --server-id S1 --host 0.0.0.0 --port 9101 --gateway-host 127.0.0.1 --gateway-port 9001
```

### Terminal 3: Process Server S2

```bash
python server/main.py --server-id S2 --host 0.0.0.0 --port 9102 --gateway-host 127.0.0.1 --gateway-port 9001
```

### Terminal 4 dst: Client (Web Server)

```bash
python client/main.py --gateway-host 127.0.0.1 --gateway-port 9000 --port 8080
```
Akses Web UI di browser Anda melalui tautan `http://localhost:8080`.

---

## 7. Prioritas Implementasi

1. TCP protocol dan packet framing.
2. Gateway: register, login, session token.
3. Gateway: online user dan PM global.
4. Gateway: backend registry dan heartbeat.
5. Gateway: room directory dan room affinity.
6. Process Server: room chat.
7. Process Server: file transfer.
8. Reliable transfer: chunking, checksum, resume.
9. Web UI integration and HTTP-to-TCP API bridge.
10. Testing: latency, throughput, load test.
11. Dokumentasi dan video demo.

---

## 8. Dokumentasi Penting

Baca berurutan:
1. `ai/AI_CONTEXT.md`
2. `docs/REQUIREMENTS.md`
3. `docs/FEATURE_SPEC.md`
4. `docs/ARCHITECTURE.md`
5. `docs/API_SPEC.md`
6. `docs/DATABASE.md`
7. `docs/TESTING.md`
8. `TASKS.md`
