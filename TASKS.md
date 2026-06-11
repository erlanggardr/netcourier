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

## Phase 2A - Tkinter Client Shell

- [x] Buat `client/main.py` sebagai entry point Tkinter.
- [x] Buat `client/app.py` untuk class utama aplikasi.
- [x] Buat Login/Register view.
- [x] Buat Waiting Room view.
- [x] Buat Room Chat view.
- [x] Buat reusable widgets untuk status bar, message list, user list, room list, file list, dan transfer progress.
- [x] Implement UI event queue menggunakan `queue.Queue`.
- [x] Implement `root.after(...)` untuk polling event queue.
- [x] Pastikan GUI tidak freeze saat koneksi Gateway berjalan.

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
- [x] Implement online users request and Tkinter table update.
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

- [ ] Buat Process Server TCP server.
- [ ] Implement backend register ke Gateway.
- [ ] Implement heartbeat ke Gateway.
- [ ] Implement `AUTH_BACKEND`.
- [ ] Implement token validation ke Gateway.
- [ ] Implement join room backend.
- [ ] Implement leave room.
- [ ] Update user presence saat join/leave room.

---

## Phase 6 - Room Chat

- [ ] Implement `ROOM_CHAT_SEND`.
- [ ] Simpan room message ke database.
- [ ] Broadcast room chat ke semua member.
- [ ] Implement system message join/leave.
- [ ] Implement `ROOM_HISTORY_REQUEST`.
- [ ] Test user di room berbeda tidak menerima pesan.
- [ ] Test chat history saat join.

---

## Phase 7 - File Transfer

- [ ] Implement `FILE_LIST_REQUEST`.
- [ ] Implement `UPLOAD_INIT`.
- [ ] Implement transfer session.
- [ ] Implement `UPLOAD_CHUNK`.
- [ ] Implement `CHUNK_ACK`.
- [ ] Implement `UPLOAD_FINISH`.
- [ ] Implement checksum server.
- [ ] Implement `DOWNLOAD_REQUEST`.
- [ ] Implement `DOWNLOAD_CHUNK`.
- [ ] Implement checksum client.
- [ ] Implement progress upload/download.
- [ ] Test upload/download 1 MB, 5 MB, 10 MB.

---

## Phase 8 - Resume Transfer

- [ ] Simpan transfer state.
- [ ] Implement interrupted transfer.
- [ ] Implement `RESUME_TRANSFER`.
- [ ] Resume download dari chunk terakhir.
- [ ] Resume upload dari chunk terakhir.
- [ ] Test disconnect saat download.
- [ ] Test disconnect saat upload.
- [ ] Validasi checksum setelah resume.

---

## Phase 9 - Reliability and Security

- [ ] Implement malformed packet handling.
- [ ] Implement rate limiting chat.
- [ ] Implement rate limiting PM.
- [ ] Implement file size limit.
- [ ] Implement filename sanitizer.
- [ ] Implement timeout client.
- [ ] Implement timeout transfer.
- [ ] Implement token expiry optional.
- [ ] Test malformed packet.
- [ ] Test path traversal filename.

---

## Phase 10 - Testing and Reporting

- [ ] Buat `tests/load_test.py`.
- [ ] Buat `tests/throughput_test.py`.
- [ ] Buat `tests/malformed_packet_test.py`.
- [ ] Buat `tests/reconnect_test.py`.
- [ ] Catat hasil latency Gateway.
- [ ] Catat hasil latency Process Server.
- [ ] Catat hasil throughput upload/download.
- [ ] Catat hasil load test 5, 10, 30 client.
- [ ] Screenshot/log hasil demo.
- [ ] Update README.
- [ ] Update laporan final project.
- [ ] Buat video demo singkat.

---

## Optional Bonus

- [ ] TLS/SSL socket.
- [ ] Emoji/reaction.
- [ ] Admin kick user.
- [ ] Admin delete file.
- [ ] Transfer queue.
- [ ] Web dashboard monitoring sederhana.
- [ ] Docker compose untuk Gateway + S1 + S2 + DB.
