# Tasks - NetCourier

Gunakan checklist ini sebagai roadmap implementasi.

---

## Phase 0 - Project Setup

- [x] Buat struktur folder project.
- [x] Buat `common/protocol.py`.
- [x] Buat `common/constants.py`.
- [x] Buat `common/errors.py`.
- [x] Setup logging dasar.
- [x] Setup database connection.
- [x] Buat migration/DDL database awal.
- [x] Buat config `.env.example`.

---

## Phase 1 - Protocol Core

- [x] Implement length-prefixed packet framing.
- [x] Implement JSON header encode/decode.
- [x] Implement binary payload support.
- [x] Implement request_id generator.
- [x] Implement error packet builder.
- [x] Test send/receive packet tanpa binary.
- [x] Test send/receive packet dengan binary payload.

---

## Phase 2A - Web Client UI & HTTP-to-TCP Bridge

- [x] Buat `client/main.py` sebagai entry point server Web UI & API.
- [x] Buat `src/netcourier/web/api/main.py` untuk mengelola REST API dan session bridge.
- [x] Buat antarmuka Login/Register menggunakan HTML/CSS/JS.
- [x] Buat antarmuka Waiting Room dan Room Chat di browser.
- [x] Implementasi event queue & long-polling `/api/events` untuk real-time update.
- [x] Pastikan perutean REST dan file transfer berfungsi secara non-blocking.

## Phase 2 - Gateway Basic

- [x] Buat Gateway TCP server client-facing port 9000.
- [x] Buat threading handler untuk client.
- [x] Implement `REGISTER`.
- [x] Implement password hashing.
- [x] Implement `LOGIN`.
- [x] Implement session token.
- [x] Implement `LOGOUT`.
- [x] Implement duplicate login handling.
- [x] Implement `PING/PONG`.
- [x] Simpan log Gateway.

---

## Phase 3 - PM and Presence

- [x] Implement `user_presence`.
- [x] Implement online users request and Web UI list update.
- [x] Implement `PRIVATE_MESSAGE_SEND`.
- [x] Implement PM delivery ke online user.
- [x] Implement PM stored_offline.
- [x] Implement `PM_HISTORY_REQUEST`.
- [x] Test PM waiting-to-waiting.
- [x] Test PM waiting-to-in-room.
- [x] Test PM offline recipient.

---

## Phase 4 - Backend Registry and Load Balancing

- [x] Buat Gateway backend-control port 9001.
- [x] Implement `REGISTER_BACKEND`.
- [x] Implement `HEARTBEAT`.
- [x] Simpan backend status.
- [x] Implement backend down detection.
- [x] Implement load balancing score.
- [x] Implement room_mapping.
- [x] Implement `CREATE_ROOM`.
- [x] Implement `JOIN_ROOM` returning server location.
- [x] Test room affinity S1/S2.

---

## Phase 5 - Process Server Basic

- [x] Buat Process Server TCP server.
- [x] Implement backend register ke Gateway.
- [x] Implement heartbeat ke Gateway.
- [x] Implement `AUTH_BACKEND`.
- [x] Implement token validation ke Gateway.
- [x] Implement join room backend.
- [x] Implement leave room.
- [x] Update user presence saat join/leave room.

---

## Phase 6 - Room Chat

- [x] Implement `ROOM_CHAT_SEND`.
- [x] Simpan room message ke database.
- [x] Broadcast room chat ke semua member.
- [x] Implement system message join/leave.
- [x] Implement `ROOM_HISTORY_REQUEST`.
- [x] Test user di room berbeda tidak menerima pesan.
- [x] Test chat history saat join.

---

## Phase 7 - File Transfer

- [x] Implement `FILE_LIST_REQUEST`.
- [x] Implement `UPLOAD_INIT`.
- [x] Implement transfer session.
- [x] Implement `UPLOAD_CHUNK`.
- [x] Implement `CHUNK_ACK`.
- [x] Implement `UPLOAD_FINISH`.
- [x] Implement checksum server.
- [x] Implement `DOWNLOAD_REQUEST`.
- [x] Implement `DOWNLOAD_CHUNK`.
- [x] Implement checksum client.
- [x] Implement progress upload/download.
- [x] Test upload/download 1 MB, 5 MB, 10 MB.

---

## Phase 8 - Resume Transfer

- [x] Simpan transfer state.
- [x] Implement interrupted transfer.
- [x] Implement `RESUME_TRANSFER`.
- [x] Resume download dari chunk terakhir.
- [x] Resume upload dari chunk terakhir.
- [x] Test disconnect saat download.
- [x] Test disconnect saat upload.
- [x] Validasi checksum setelah resume.
- [x] Optimasi kecepatan transfer (1MB chunk + DB Batching).

---

## Phase 9 - Reliability and Security

- [x] Implement malformed packet handling.
- [x] Implement rate limiting chat.
- [x] Implement rate limiting PM.
- [x] Implement file size limit (1GB).
- [x] Implement filename sanitizer.
- [x] Pause/Cancel transfer di Web UI.
- [x] Implement timeout client.
- [x] Implement timeout transfer.
- [x] Implement token expiry optional.
- [x] Test malformed packet.
- [x] Test path traversal filename.

---

## Phase 10 - Testing and Reporting

- [x] Buat `tests/load_test.py`.
- [x] Buat `tests/throughput_test.py`.
- [x] Buat `tests/malformed_packet_test.py` (Refer to `tests/test_phase9.py`).
- [x] Buat `tests/reconnect_test.py`.
- [x] Catat hasil latency Gateway.
- [x] Catat hasil latency Process Server.
- [x] Catat hasil throughput upload/download.
- [x] Catat hasil load test 5, 10, 30 client.
- [x] Screenshot/log hasil demo.
- [x] Update laporan final project (See `FINAL_REPORT.md`).

---

## Optional Bonus

- [ ] TLS/SSL socket.
- [ ] Emoji/reaction.
- [ ] Admin kick user.
- [ ] Admin delete file.
- [ ] Transfer queue.
- [ ] Web dashboard monitoring sederhana.
- [x] Docker compose untuk Gateway + S1 + S2 + DB.

