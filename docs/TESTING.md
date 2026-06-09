# Testing Guide - NetCourier

Dokumen ini menjelaskan pengujian manual, pengujian protokol, reliability test, performance test, dan load test.

---

## 1. Testing Goals

Pengujian harus membuktikan:
1. fitur wajib Multi-Chat Rooms berjalan,
2. file transfer bonus berjalan,
3. Gateway/Auth/Load Balancer berjalan,
4. PM global berjalan dari waiting room ke user yang sedang di room,
5. server stabil saat banyak client,
6. malformed packet tidak menyebabkan crash,
7. latency dan throughput dapat diukur.

---

## 2. Manual Functional Test

## 2.1 Authentication

- [ ] User bisa register.
- [ ] Username duplikat ditolak.
- [ ] User bisa login.
- [ ] Password salah ditolak.
- [ ] Duplicate login ditangani.
- [ ] User bisa logout.
- [ ] Token invalid ditolak Process Server.

Expected:
- Gateway log mencatat register/login/logout.
- User masuk `user_presence`.

---

## 2.2 Waiting Room

- [ ] Setelah login, user masuk waiting mode.
- [ ] User bisa melihat Online Users table.
- [ ] User bisa melihat Rooms table.
- [ ] User bisa mengirim PM tanpa join room.
- [ ] User bisa menerima PM tanpa join room.

---

## 2.3 Private Message

Scenario A: waiting to waiting
- [ ] User A dan B login.
- [ ] User A memilih Budi pada panel Online Users, mengetik pesan PM, lalu menekan tombol Send PM.
- [ ] User B menerima PM.
- [ ] PM tersimpan di database.

Scenario B: waiting to in-room
- [ ] User B join room.
- [ ] User A tetap di waiting.
- [ ] User A memilih B pada panel Online Users, mengetik pesan PM, lalu menekan tombol Send PM.
- [ ] User B menerima PM walaupun sedang di room.

Scenario C: offline recipient
- [ ] User B logout.
- [ ] User A memilih B pada panel Online Users, mengetik pesan PM, lalu menekan tombol Send PM.
- [ ] PM status `stored_offline`.
- [ ] User B login lagi.
- [ ] User B dapat membaca unread PM.

---

## 2.4 Room Management

- [ ] User bisa create room.
- [ ] Gateway assign room ke S1/S2.
- [ ] Room mapping tersimpan.
- [ ] User lain bisa join room yang sama.
- [ ] User dalam room yang sama diarahkan ke server yang sama.
- [ ] User bisa leave room.
- [ ] User tetap bisa PM setelah leave.

---

## 2.5 Room Chat

- [ ] User dalam room bisa kirim broadcast chat.
- [ ] Semua member room menerima pesan.
- [ ] User di room lain tidak menerima pesan.
- [ ] Pesan punya timestamp.
- [ ] Chat history tampil saat join.
- [ ] System event tampil saat join/leave.

---

## 2.6 File Transfer

Upload:
- [ ] User bisa upload file 1 MB.
- [ ] User bisa upload file 5 MB.
- [ ] Chunk ACK diterima.
- [ ] Progress upload tampil.
- [ ] Checksum valid.
- [ ] File muncul di `/files`.
- [ ] System event file uploaded muncul.

Download:
- [ ] User lain bisa download file.
- [ ] Progress download tampil.
- [ ] Checksum hasil download valid.
- [ ] File tersimpan di folder downloads.

Resume:
- [ ] Download diputus di tengah jalan.
- [ ] Client reconnect.
- [ ] Client resume transfer.
- [ ] Transfer lanjut dari chunk terakhir.
- [ ] Checksum akhir valid.

---

## 3. Protocol Test

## 3.1 Valid Packet Test

- [ ] REGISTER valid.
- [ ] LOGIN valid.
- [ ] PRIVATE_MESSAGE_SEND valid.
- [ ] CREATE_ROOM valid.
- [ ] JOIN_ROOM valid.
- [ ] ROOM_CHAT_SEND valid.
- [ ] UPLOAD_INIT valid.
- [ ] UPLOAD_CHUNK valid.
- [ ] DOWNLOAD_REQUEST valid.

## 3.2 Malformed Packet Test

Kirim packet:
- [ ] JSON invalid.
- [ ] Missing `type`.
- [ ] Missing `payload`.
- [ ] Token invalid.
- [ ] Unknown message type.
- [ ] Negative file size.
- [ ] Invalid chunk index.
- [ ] Payload size tidak sesuai.
- [ ] Username kosong.
- [ ] Room name kosong.

Expected:
- Server membalas `ERROR`.
- Server tidak crash.
- Error dicatat di log.

---

## 4. Reliability Test

## 4.1 Client Disconnect

- [ ] Client disconnect dari Gateway.
- [ ] Presence menjadi offline.
- [ ] Session menjadi inactive.
- [ ] Server tetap berjalan.

## 4.2 Room Disconnect

- [ ] Client disconnect dari Process Server.
- [ ] Membership inactive.
- [ ] Transfer aktif menjadi interrupted.
- [ ] Client bisa reconnect.

## 4.3 Backend Down

- [ ] Matikan S1.
- [ ] Gateway berhenti menerima heartbeat S1.
- [ ] Gateway mark S1 down.
- [ ] Room baru tidak diarahkan ke S1.
- [ ] S2 tetap bisa menerima room baru.

## 4.4 Database Error Simulation

- [ ] Simulasikan query gagal.
- [ ] Server mengembalikan `ERROR INTERNAL_ERROR`.
- [ ] Server tidak crash.

---

## 5. Performance Test

## 5.1 Latency Test

Command:
```txt
/ping
/ping-room
```

Measure:
- Gateway RTT,
- Process Server RTT.

Table template:

| Target | Clients | Avg Latency | Min | Max | Status |
|---|---:|---:|---:|---:|---|
| Gateway | 1 | ... ms | ... | ... | OK |
| Gateway | 10 | ... ms | ... | ... | OK |
| S1 | 1 | ... ms | ... | ... | OK |
| S1 | 10 | ... ms | ... | ... | OK |

---

## 5.2 Throughput Test

File sizes:
- 1 MB,
- 5 MB,
- 10 MB,
- optional 50 MB.

Table template:

| File Size | Upload Time | Download Time | Upload Throughput | Download Throughput | Checksum |
|---:|---:|---:|---:|---:|---|
| 1 MB | ... | ... | ... MB/s | ... MB/s | Valid |
| 5 MB | ... | ... | ... MB/s | ... MB/s | Valid |
| 10 MB | ... | ... | ... MB/s | ... MB/s | Valid |

---

## 6. Load Test

Command example:

```bash
python tests/load_test.py --clients 30 --rooms 5 --messages 100 --pm 50 --file-size 1048576
```

Metrics:
- total clients,
- successful login,
- failed login,
- total room messages,
- total PM,
- average latency,
- max latency,
- file throughput,
- error rate,
- server CPU/memory optional.

Table template:

| Clients | Rooms | Messages | PM | Uploads | Avg Latency | Error Rate | Status |
|---:|---:|---:|---:|---:|---:|---:|---|
| 5 | 1 | 100 | 20 | 2 | ... ms | ...% | OK |
| 10 | 2 | 300 | 50 | 5 | ... ms | ...% | OK |
| 30 | 5 | 1000 | 100 | 10 | ... ms | ...% | OK |

---

## 7. Demo Checklist

Saat demo, lakukan:

1. Jalankan Gateway.
2. Jalankan Process Server S1.
3. Jalankan Process Server S2.
4. Jalankan 3 client.
5. Register/login.
6. Tampilkan online user.
7. User A PM User B.
8. User B join room.
9. User A dari waiting room PM User B yang sedang di room.
10. Create room dan tunjukkan server assignment.
11. Join room dari beberapa client.
12. Broadcast room chat.
13. Tampilkan chat history.
14. Upload file dengan progress.
15. Download file dengan checksum.
16. Putuskan koneksi download dan resume.
17. Tampilkan log server.
18. Jalankan load test singkat.
19. Jelaskan arsitektur dan protokol.

---

## 8. Acceptance Criteria Global

- [ ] Semua fitur wajib multi-chat room berjalan.
- [ ] PM global berjalan dari waiting ke in-room.
- [ ] Room affinity berjalan.
- [ ] File transfer chunking berjalan.
- [ ] Checksum valid.
- [ ] Resume transfer berhasil.
- [ ] Gateway heartbeat backend berjalan.
- [ ] Load balancing bisa didemokan.
- [ ] Malformed packet aman.
- [ ] Load test menghasilkan data laporan.

---

## Tkinter UI Test

- [ ] Aplikasi client dapat dibuka dengan `python client/main.py`.
- [ ] Login/register dapat dilakukan melalui form Tkinter.
- [ ] Waiting Room menampilkan online user list, room list, PM panel, dan status bar.
- [ ] User dapat membuat room melalui form Create Room.
- [ ] User dapat join room melalui tombol Join Room.
- [ ] Room window/panel menampilkan chat history, room members, file list, dan transfer panel.
- [ ] PM tetap masuk saat user sedang berada di room.
- [ ] Upload file menggunakan file picker.
- [ ] Progress upload/download tampil menggunakan progress bar.
- [ ] GUI tidak freeze saat load test ringan, upload/download, atau menerima banyak pesan.
- [ ] Socket worker thread tidak mengubah widget langsung; update UI dilakukan lewat queue dan `root.after`.
