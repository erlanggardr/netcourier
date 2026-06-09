# AI Context - NetCourier

Kamu adalah AI coding assistant untuk project **NetCourier**.

Tujuanmu adalah membantu mengembangkan project sesuai dokumentasi, bukan mengubah scope sembarangan.

---

## 1. Must Read First

Sebelum coding, baca dokumen ini secara berurutan:

1. `README.md`
2. `docs/REQUIREMENTS.md`
3. `docs/FEATURE_SPEC.md`
4. `docs/ARCHITECTURE.md`
5. `docs/API_SPEC.md`
6. `docs/DATABASE.md`
7. `docs/TESTING.md`
8. `TASKS.md`

---

## 2. Project Summary

NetCourier adalah aplikasi **Multi-Chat Room berbasis TCP Socket** dengan fitur **Reliable File Transfer**.

Arsitektur:
```txt
Client -> Gateway/Auth/Load Balancer -> Process Server S1/S2 -> Central Database
```

Gateway:
- auth,
- session,
- PM global,
- online user,
- room directory,
- load balancing,
- room affinity.

Process Server:
- room chat,
- room history,
- file upload/download,
- chunking,
- checksum,
- resume transfer.

Client:
- menggunakan Tkinter desktop GUI sebagai UI utama,
- menjaga koneksi Gateway untuk PM,
- menjaga koneksi Process Server untuk room chat/file transfer,
- memakai worker thread dan UI event queue agar Tkinter tidak freeze.

---

## 3. Non-Negotiable Rules

1. Jangan mengganti TCP socket dengan HTTP/REST sebagai komunikasi utama.
2. Jangan membuat CLI/TUI sebagai UI utama; UI client wajib Tkinter desktop GUI.
3. Jangan membuat Nginx sebagai load balancer utama.
4. Gateway harus room-aware.
5. PM harus lewat Gateway.
6. Room chat harus lewat Process Server.
7. File transfer harus lewat Process Server.
8. User dalam room yang sama harus berada di Process Server yang sama.
9. Client harus tetap bisa menerima PM saat sedang di room.
10. Jangan simpan password plain text.
11. Jangan simpan file besar di database.
12. Jangan hardcode secret/token.
13. Jangan menghapus fitur lama tanpa alasan.
14. Jangan update widget Tkinter langsung dari socket/worker thread; gunakan queue dan `root.after`.
15. Jangan membuat fitur di luar requirement tanpa update docs dan TASKS.

---

## 4. Coding Rules

1. Gunakan Python.
2. Gunakan `socket` untuk networking.
3. Gunakan `threading` atau `select` untuk concurrency.
4. Gunakan JSON untuk serialization.
5. Gunakan length-prefixed framing untuk TCP packet.
6. Simpan protocol common di `common/protocol.py`.
7. Setiap message type sebaiknya punya handler.
8. Pisahkan Gateway, Process Server, Client, dan Common module.
9. Gunakan logging.
10. Tambahkan error handling untuk malformed packet.

---

## 5. Suggested Implementation Order

1. `common/protocol.py`: encode/decode packet.
2. Gateway basic TCP server.
3. Client connect Gateway.
4. Register/login/session.
5. PM global.
6. Backend register/heartbeat.
7. Room directory/load balancing.
8. Process Server auth backend.
9. Room join/chat/history.
10. File transfer init/chunk/finish.
11. Checksum.
12. Resume transfer.
13. Load test.
14. Documentation update.

---

## 6. Architecture Constraints

Gateway must not:
- process file chunks,
- store room chat in memory only,
- randomly route user to backend without room affinity.

Process Server must not:
- authenticate password directly,
- create session token,
- handle global PM,
- accept client without token validation.

Client must:
- maintain Gateway connection after login,
- open Process Server connection after join room,
- route PM action from Tkinter UI to Gateway,
- route room chat, upload, and download actions from Tkinter UI to Process Server.

---

## 7. When Generating Code

Always consider:
- What component is this file for?
- Does this feature belong to Gateway or Process Server?
- Does the packet follow `docs/API_SPEC.md`?
- Does it update database according to `docs/DATABASE.md`?
- Does it satisfy `docs/TESTING.md`?

---

## 8. Conflict Resolution

If docs conflict:
1. `docs/REQUIREMENTS.md` has highest priority for product behavior.
2. `docs/ARCHITECTURE.md` has highest priority for component responsibility.
3. `docs/API_SPEC.md` has highest priority for packet format.
4. `docs/DATABASE.md` has highest priority for data structure.
5. `TASKS.md` has highest priority for current implementation phase.

If still ambiguous, do not guess silently. State assumption clearly.


---

## 7. Tkinter Rules

1. File entry point client adalah `client/main.py`.
2. UI utama harus dibuat dengan `tkinter` dan `ttk`.
3. Gunakan `filedialog` untuk upload file.
4. Gunakan `messagebox` hanya untuk error/confirmation penting; status biasa tampil di status bar.
5. Gunakan `queue.Queue` untuk semua event dari socket thread ke UI.
6. Gunakan `root.after(...)` untuk polling UI queue.
7. Jangan menggunakan CLI prompt, curses, textual, rich TUI, atau command loop sebagai UI utama.
