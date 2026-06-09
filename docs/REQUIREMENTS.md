# Requirements - NetCourier

## 1. Product Overview

**NetCourier** adalah aplikasi multi-chat room berbasis TCP socket dengan fitur file transfer andal. Sistem dibuat menggunakan Python dan menerapkan client-server architecture, application layer protocol, serialization, TCP socket programming, multithreading/concurrency, reconnect handling, timeout handling, server logging, pengujian performa, dan simulasi beban server.

NetCourier dirancang dengan arsitektur:

```txt
Client -> Gateway/Auth/Load Balancer -> Process Server S1/S2 -> Central Database
```

Client tetap terhubung ke Gateway untuk fitur global seperti login, online user, private message, dan room directory. Saat user join room, Gateway mengarahkan client ke Process Server yang menangani room tersebut.

---

## 2. Goals

### G-01: Memenuhi ketentuan final project Multi-Chat Rooms

Sistem harus mendukung:
- banyak room,
- satu room banyak client,
- create room,
- join room,
- leave room,
- broadcast message,
- private message,
- TCP socket,
- multithreading/select,
- serialization,
- authentication sederhana,
- online user list,
- room list,
- chat history,
- timestamp message,
- server logging.

### G-02: Menambahkan fitur bonus yang kuat

Sistem menambahkan:
- file transfer,
- chunked upload/download,
- checksum SHA-256,
- resume transfer,
- database message persistence,
- load balancing berbasis room affinity,
- latency measurement,
- throughput measurement,
- load testing.

### G-03: Menjaga scope tetap feasible

Fitur yang dibuat harus cukup kuat untuk demo, tetapi tidak boleh terlalu melebar ke voice/video/web UI kompleks.

---

## 3. User Roles

## 3.1 Guest

User belum login.

Hak akses:
- register,
- login.

Tidak boleh:
- join room,
- melihat room detail,
- mengirim chat,
- mengirim PM,
- upload/download file.

## 3.2 Authenticated User

User sudah login melalui Gateway.

Hak akses:
- melihat online user global,
- mengirim private message,
- melihat PM history,
- melihat room list,
- create room,
- join room,
- leave room,
- melihat room history,
- broadcast message dalam room,
- upload/download file dalam room.

## 3.3 Room Admin

User yang membuat room atau diberi role admin.

Hak akses tambahan:
- menghapus file room,
- menghapus pesan room secara soft delete,
- kick user dari room,
- melihat aktivitas room.

## 3.4 Server Operator

Pihak yang menjalankan sistem saat demo.

Hak akses:
- menjalankan Gateway,
- menjalankan Process Server S1/S2,
- memantau log,
- menjalankan load test,
- melihat metrics.

---

## 4. Functional Requirements

## 4.1 Authentication and Session

### FR-AUTH-01 Register

Sistem harus memungkinkan user membuat akun.

Input:
- username,
- password,
- display name.

Aturan:
- username unik,
- password minimal 6 karakter,
- password disimpan dalam bentuk hash,
- username tidak boleh mengandung karakter berbahaya.

Output:
- `REGISTER_OK` jika berhasil,
- `ERROR USERNAME_TAKEN` jika username sudah ada,
- `ERROR INVALID_INPUT` jika input tidak valid.

### FR-AUTH-02 Login

Sistem harus memungkinkan user login ke Gateway.

Input:
- username,
- password.

Aturan:
- user valid mendapat session token,
- duplicate login ditolak atau session lama diputus sesuai konfigurasi,
- token digunakan untuk request berikutnya.

Output:
- `LOGIN_OK` + token,
- `ERROR INVALID_CREDENTIALS`,
- `ERROR DUPLICATE_LOGIN`.

### FR-AUTH-03 Logout

User dapat logout dari Gateway.

Aturan:
- session dinonaktifkan,
- presence user menjadi offline,
- Gateway memberi tahu Process Server jika user masih aktif di room.

### FR-AUTH-04 Token Validation

Process Server harus memvalidasi token ke Gateway sebelum menerima client.

Flow:
1. Client connect ke Process Server dengan token.
2. Process Server mengirim `VALIDATE_TOKEN` ke Gateway.
3. Gateway membalas `TOKEN_VALID` atau `TOKEN_INVALID`.

---

## 4.2 Gateway and Load Balancing

### FR-GW-01 Backend Register

Setiap Process Server harus register ke Gateway.

Data:
- server_id,
- host,
- port,
- status.

### FR-GW-02 Backend Heartbeat

Process Server mengirim heartbeat periodik ke Gateway.

Data:
- server_id,
- active_rooms,
- active_clients,
- active_transfers,
- last_heartbeat_at.

### FR-GW-03 Room Directory

Gateway menyimpan mapping:

```txt
room_name -> server_id
```

Tujuan:
- user yang join room sama selalu diarahkan ke server yang sama.

### FR-GW-04 Room Affinity

Satu room hanya boleh aktif di satu Process Server.

Contoh:
- Room `FP-Jaringan` -> S1.
- Semua user yang join `FP-Jaringan` diarahkan ke S1.

### FR-GW-05 Load Balancing Algorithm

Gateway memilih server untuk room baru berdasarkan:
1. server status alive,
2. jumlah room paling sedikit,
3. jumlah client paling sedikit,
4. fallback round-robin jika skor sama.

### FR-GW-06 Waiting Room

Setelah login, user berada di area global/waiting room Gateway.

Di waiting room, user bisa:
- melihat online user,
- PM user lain,
- melihat room list,
- create room,
- join room.

---

## 4.3 Private Message Global

### FR-PM-01 Send PM

User dapat mengirim PM ke user lain dari waiting room maupun saat sedang berada di room.

Flow:
1. Client mengirim PM ke Gateway melalui koneksi Gateway.
2. Gateway validasi token.
3. Gateway menyimpan PM ke database.
4. Gateway mengirim PM ke recipient jika online.
5. Gateway mengirim status ke sender.

### FR-PM-02 Receive PM While In Room

User yang sedang berada di Process Server tetap harus dapat menerima PM karena koneksi Gateway tetap aktif.

### FR-PM-03 PM History

User dapat melihat history PM dengan user lain.

### FR-PM-04 Offline PM

Jika recipient offline:
- PM disimpan ke database,
- status `stored_offline`,
- PM dikirim saat recipient login.

---

## 4.4 Room Management

### FR-ROOM-01 Create Room

User dapat membuat room melalui Gateway.

Flow:
1. Client mengirim `CREATE_ROOM` ke Gateway.
2. Gateway memilih Process Server.
3. Gateway menyimpan room dan room_mapping.
4. Gateway mengembalikan lokasi Process Server.
5. Client connect ke Process Server tersebut.

### FR-ROOM-02 Join Room

User dapat join room yang sudah ada.

Flow:
1. Client mengirim `JOIN_ROOM` ke Gateway.
2. Gateway mencari room_mapping.
3. Gateway mengembalikan host/port Process Server.
4. Client connect ke Process Server.
5. Process Server validasi token ke Gateway.
6. User masuk ke room.

### FR-ROOM-03 Leave Room

User dapat keluar dari room.

Aturan:
- user tidak lagi menerima room broadcast,
- PM tetap aktif melalui Gateway,
- Process Server update membership.

### FR-ROOM-04 Room List

Gateway menyediakan daftar room.

Output:
- room_name,
- server_id,
- active user count,
- total file count,
- visibility.

### FR-ROOM-05 Online User List

Gateway menyediakan online user global. Process Server menyediakan online user per room.

---

## 4.5 Room Chat

### FR-CHAT-01 Broadcast Message

User dapat mengirim pesan ke semua user dalam room.

Flow:
1. Client mengirim pesan ke Process Server.
2. Process Server validasi user adalah member room.
3. Process Server simpan pesan ke database.
4. Process Server broadcast pesan ke user dalam room.

### FR-CHAT-02 Chat History

Saat join room, user menerima N pesan terakhir, default 50.

### FR-CHAT-03 Timestamp

Setiap pesan harus memiliki timestamp format:

```txt
YYYY-MM-DD HH:MM:SS
```

### FR-CHAT-04 System Message

System message dikirim saat:
- user join,
- user leave,
- file upload mulai,
- file upload sukses,
- file checksum gagal,
- user disconnect/reconnect.

---

## 4.6 File Transfer

### FR-FILE-01 File List

User dapat melihat file list pada room.

Field:
- file_id,
- filename,
- size,
- uploader,
- checksum,
- status,
- uploaded_at.

### FR-FILE-02 Upload File

User dapat upload file ke room.

Aturan:
- file dikirim per chunk,
- server mengirim ACK per chunk,
- checksum divalidasi setelah upload selesai,
- metadata disimpan di database,
- file fisik disimpan di folder storage Process Server.

### FR-FILE-03 Download File

User dapat download file dari room.

Aturan:
- server mengirim file per chunk,
- client menampilkan progress,
- client validasi checksum setelah download selesai.

### FR-FILE-04 Chunking

Default chunk size:
- 64 KB.

Chunk metadata:
- transfer_id,
- chunk_index,
- payload_size,
- total_chunks.

### FR-FILE-05 Resume Transfer

Transfer yang terputus dapat dilanjutkan.

Aturan:
- server menyimpan transfer state,
- client mengirim `RESUME_TRANSFER`,
- transfer dilanjutkan dari chunk terakhir yang sukses.

### FR-FILE-06 Checksum SHA-256

Checksum digunakan untuk upload dan download.

Jika checksum gagal:
- file ditandai `corrupted`,
- user mendapat error,
- log dicatat.

---

## 4.7 Logging and Metrics

### FR-LOG-01 Server Logging

Semua komponen mencatat:
- login/register,
- create/join/leave room,
- chat send,
- PM send,
- upload/download,
- checksum result,
- malformed packet,
- timeout,
- reconnect,
- load balancer decision,
- backend heartbeat.

### FR-METRIC-01 Latency Measurement

Client dapat menjalankan `/ping` ke Gateway dan Process Server.

### FR-METRIC-02 Throughput Measurement

Upload/download file harus mencatat:
- bytes transferred,
- duration,
- throughput.

### FR-METRIC-03 Load Test

Disediakan script simulasi:
- banyak client login,
- banyak client PM,
- banyak client join room,
- banyak pesan room,
- upload/download file paralel.

---

## 5. Non-Functional Requirements

## 5.1 Performance

- Minimal 5 client real saat demo.
- Target simulasi 30 client via load test.
- Chat latency lokal harus rendah.
- File 1 MB, 5 MB, dan 10 MB harus berhasil transfer.
- Server tidak crash saat 100 pesan dikirim cepat.

## 5.2 Reliability

- Server tidak crash saat client disconnect mendadak.
- Gateway tidak mengarahkan client ke backend yang mati.
- Process Server menolak token invalid.
- File transfer dapat resume.
- Malformed packet tidak membuat server berhenti.

## 5.3 Security

- Password di-hash.
- Token digunakan untuk request setelah login.
- Path traversal dicegah.
- File size dibatasi.
- Rate limit diterapkan untuk chat/PM.
- Packet divalidasi sebelum diproses.

## 5.4 Maintainability

- Kode modular.
- Protocol shared di folder `common/`.
- Handler per message type.
- Logging konsisten.
- Dokumentasi diperbarui setiap perubahan besar.

## 5.5 Usability

- UI Tkinter mudah digunakan dan tidak bergantung pada CLI/TUI.
- Ada menu/help dialog untuk daftar fitur dan cara penggunaan.
- Error message jelas melalui label status atau messagebox.
- Progress transfer tampil menggunakan progress bar.
- Tampilan waiting room dan room chat terlihat berbeda.
- Operasi socket tidak boleh mem-freeze GUI; gunakan worker thread dan UI event queue.

---

## 6. Out of Scope

Fitur berikut tidak wajib:
- voice chat,
- video call,
- screen sharing,
- web UI penuh,
- mobile app,
- CLI/TUI client sebagai UI utama,
- distributed file storage,
- automatic room migration,
- end-to-end encryption penuh,
- Nginx/HAProxy sebagai load balancer utama.

---

## 7. Success Criteria

Project dianggap berhasil jika:
1. User bisa register/login.
2. User bisa PM dari waiting room ke user yang sedang di room.
3. User bisa create/join/leave room.
4. User bisa broadcast message di room.
5. User bisa melihat chat history.
6. User bisa upload/download file.
7. File transfer menggunakan chunking.
8. Checksum berhasil divalidasi.
9. Resume transfer berhasil didemokan.
10. Gateway bisa mengarahkan room ke S1/S2.
11. Backend heartbeat berjalan.
12. Load test menghasilkan latency, throughput, success rate.
13. Server tetap stabil saat malformed packet dan disconnect.
