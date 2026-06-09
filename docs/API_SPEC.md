# API / Protocol Specification - NetCourier

NetCourier tidak menggunakan REST API sebagai komunikasi utama. Sistem menggunakan **custom application layer protocol** di atas **TCP socket**.

Dokumen ini mendefinisikan format packet, message type, request/response, dan error code.

---

## 1. Transport Protocol

- Protocol: TCP
- Serialization: JSON
- Binary payload: digunakan untuk file chunk
- Framing: length-prefixed packet

---

## 2. Packet Framing

Karena TCP adalah stream, setiap packet harus memiliki framing.

Format:

```txt
[4 bytes header_length][JSON_HEADER][BINARY_PAYLOAD optional]
```

- `header_length`: unsigned integer 4 byte big-endian.
- `JSON_HEADER`: string JSON UTF-8.
- `BINARY_PAYLOAD`: bytes opsional untuk file chunk.

Jika tidak ada binary payload:
- `payload_size = 0`.

---

## 3. General Header Format

```json
{
  "type": "MESSAGE_TYPE",
  "request_id": "REQ-0001",
  "token": "SESSION_TOKEN_OR_NULL",
  "timestamp": "2026-06-09 20:00:00",
  "payload_size": 0,
  "payload": {}
}
```

Field:

| Field | Type | Required | Description |
|---|---|---:|---|
| type | string | yes | Message type |
| request_id | string | yes | ID request untuk tracing |
| token | string/null | no | Session token |
| timestamp | string | yes | Waktu pengiriman |
| payload_size | int | yes | Ukuran binary payload |
| payload | object | yes | Metadata request |

---

## 4. Gateway Client-Facing Message Types

Client berkomunikasi dengan Gateway untuk auth, PM, online user, room directory.

| Type | Direction | Description |
|---|---|---|
| REGISTER | Client -> Gateway | Register user |
| REGISTER_OK | Gateway -> Client | Register sukses |
| LOGIN | Client -> Gateway | Login |
| LOGIN_OK | Gateway -> Client | Login sukses |
| LOGOUT | Client -> Gateway | Logout |
| LOGOUT_OK | Gateway -> Client | Logout sukses |
| LIST_ONLINE_USERS | Client -> Gateway | Daftar user online |
| ONLINE_USERS_RESPONSE | Gateway -> Client | Response user online |
| PRIVATE_MESSAGE_SEND | Client -> Gateway | Kirim PM |
| PRIVATE_MESSAGE_RECEIVED | Gateway -> Client | PM diterima |
| PRIVATE_MESSAGE_STATUS | Gateway -> Client | Status PM |
| PM_HISTORY_REQUEST | Client -> Gateway | Request history PM |
| PM_HISTORY_RESPONSE | Gateway -> Client | Response history PM |
| LIST_ROOMS | Client -> Gateway | Daftar room |
| ROOM_LIST_RESPONSE | Gateway -> Client | Response daftar room |
| CREATE_ROOM | Client -> Gateway | Buat room |
| ROOM_ASSIGNED | Gateway -> Client | Room dibuat dan server dipilih |
| JOIN_ROOM | Client -> Gateway | Request join room |
| ROOM_LOCATION | Gateway -> Client | Lokasi Process Server |
| PING | Client -> Gateway | Latency check |
| PONG | Gateway -> Client | Response ping |
| ERROR | Gateway -> Client | Error response |

---

## 5. Gateway Backend-Control Message Types

Process Server berkomunikasi dengan Gateway untuk register, heartbeat, token validation.

| Type | Direction | Description |
|---|---|---|
| REGISTER_BACKEND | Server -> Gateway | Mendaftarkan backend |
| BACKEND_REGISTERED | Gateway -> Server | Register sukses |
| HEARTBEAT | Server -> Gateway | Update status server |
| HEARTBEAT_ACK | Gateway -> Server | ACK heartbeat |
| VALIDATE_TOKEN | Server -> Gateway | Validasi token client |
| TOKEN_VALID | Gateway -> Server | Token valid |
| TOKEN_INVALID | Gateway -> Server | Token invalid |
| USER_ROOM_STATUS_UPDATE | Server -> Gateway | Update user in_room/waiting |
| ROOM_STATS_UPDATE | Server -> Gateway | Update jumlah user/transfer |
| BACKEND_SHUTDOWN | Server -> Gateway | Server akan shutdown |

---

## 6. Client Process Server Message Types

Client berkomunikasi dengan Process Server untuk room chat dan file transfer.

| Type | Direction | Description |
|---|---|---|
| AUTH_BACKEND | Client -> Server | Auth ke Process Server pakai token |
| AUTH_BACKEND_OK | Server -> Client | Auth sukses |
| JOIN_ROOM_BACKEND | Client -> Server | Join room di backend |
| JOIN_ROOM_OK | Server -> Client | Join sukses |
| LEAVE_ROOM | Client -> Server | Leave room |
| LEAVE_ROOM_OK | Server -> Client | Leave sukses |
| ROOM_CHAT_SEND | Client -> Server | Kirim chat room |
| ROOM_CHAT_BROADCAST | Server -> Client | Broadcast room |
| ROOM_HISTORY_REQUEST | Client -> Server | Minta history room |
| ROOM_HISTORY_RESPONSE | Server -> Client | Response history room |
| FILE_LIST_REQUEST | Client -> Server | Minta file list |
| FILE_LIST_RESPONSE | Server -> Client | Response file list |
| UPLOAD_INIT | Client -> Server | Mulai upload |
| UPLOAD_READY | Server -> Client | Server siap upload |
| UPLOAD_CHUNK | Client -> Server | Kirim chunk upload |
| CHUNK_ACK | Server -> Client | ACK chunk |
| UPLOAD_FINISH | Client -> Server | Upload selesai |
| UPLOAD_SUCCESS | Server -> Client | Upload valid |
| DOWNLOAD_REQUEST | Client -> Server | Request download |
| DOWNLOAD_READY | Server -> Client | Server siap download |
| DOWNLOAD_CHUNK | Server -> Client | Kirim chunk download |
| DOWNLOAD_FINISH | Server -> Client | Download selesai |
| RESUME_TRANSFER | Client -> Server | Resume upload/download |
| TRANSFER_STATUS | Server -> Client | Status transfer |
| SYSTEM_EVENT | Server -> Client | Notifikasi sistem |
| PING | Client -> Server | Latency check |
| PONG | Server -> Client | Response ping |
| ERROR | Server -> Client | Error response |

---

## 7. Packet Examples

## 7.1 REGISTER

Request:

```json
{
  "type": "REGISTER",
  "request_id": "REQ-0001",
  "token": null,
  "timestamp": "2026-06-09 20:00:00",
  "payload_size": 0,
  "payload": {
    "username": "erlangga",
    "password": "password123",
    "display_name": "Erlangga"
  }
}
```

Response:

```json
{
  "type": "REGISTER_OK",
  "request_id": "REQ-0001",
  "token": null,
  "timestamp": "2026-06-09 20:00:01",
  "payload_size": 0,
  "payload": {
    "user_id": 1,
    "username": "erlangga"
  }
}
```

---

## 7.2 LOGIN

Request:

```json
{
  "type": "LOGIN",
  "request_id": "REQ-0002",
  "token": null,
  "timestamp": "2026-06-09 20:01:00",
  "payload_size": 0,
  "payload": {
    "username": "erlangga",
    "password": "password123"
  }
}
```

Response:

```json
{
  "type": "LOGIN_OK",
  "request_id": "REQ-0002",
  "token": "session-token-value",
  "timestamp": "2026-06-09 20:01:01",
  "payload_size": 0,
  "payload": {
    "user_id": 1,
    "username": "erlangga",
    "display_name": "Erlangga"
  }
}
```

---

## 7.3 PRIVATE_MESSAGE_SEND

```json
{
  "type": "PRIVATE_MESSAGE_SEND",
  "request_id": "REQ-0100",
  "token": "session-token-value",
  "timestamp": "2026-06-09 20:02:00",
  "payload_size": 0,
  "payload": {
    "to_username": "budi",
    "message": "Bro, cek file di room nanti ya."
  }
}
```

Recipient receive:

```json
{
  "type": "PRIVATE_MESSAGE_RECEIVED",
  "request_id": "EVT-0200",
  "token": null,
  "timestamp": "2026-06-09 20:02:00",
  "payload_size": 0,
  "payload": {
    "from_username": "erlangga",
    "message": "Bro, cek file di room nanti ya.",
    "status": "delivered"
  }
}
```

---

## 7.4 CREATE_ROOM

```json
{
  "type": "CREATE_ROOM",
  "request_id": "REQ-0200",
  "token": "session-token-value",
  "timestamp": "2026-06-09 20:03:00",
  "payload_size": 0,
  "payload": {
    "room_name": "FP-Jaringan",
    "description": "Room final project",
    "visibility": "public"
  }
}
```

Response:

```json
{
  "type": "ROOM_ASSIGNED",
  "request_id": "REQ-0200",
  "token": null,
  "timestamp": "2026-06-09 20:03:01",
  "payload_size": 0,
  "payload": {
    "room_id": 10,
    "room_name": "FP-Jaringan",
    "server_id": "S1",
    "host": "127.0.0.1",
    "port": 9101
  }
}
```

---

## 7.5 JOIN_ROOM

```json
{
  "type": "JOIN_ROOM",
  "request_id": "REQ-0300",
  "token": "session-token-value",
  "timestamp": "2026-06-09 20:04:00",
  "payload_size": 0,
  "payload": {
    "room_name": "FP-Jaringan"
  }
}
```

Response:

```json
{
  "type": "ROOM_LOCATION",
  "request_id": "REQ-0300",
  "token": null,
  "timestamp": "2026-06-09 20:04:01",
  "payload_size": 0,
  "payload": {
    "room_id": 10,
    "room_name": "FP-Jaringan",
    "server_id": "S1",
    "host": "127.0.0.1",
    "port": 9101
  }
}
```

---

## 7.6 AUTH_BACKEND

```json
{
  "type": "AUTH_BACKEND",
  "request_id": "REQ-0400",
  "token": "session-token-value",
  "timestamp": "2026-06-09 20:05:00",
  "payload_size": 0,
  "payload": {
    "room_name": "FP-Jaringan"
  }
}
```

Response:

```json
{
  "type": "AUTH_BACKEND_OK",
  "request_id": "REQ-0400",
  "token": null,
  "timestamp": "2026-06-09 20:05:01",
  "payload_size": 0,
  "payload": {
    "user_id": 1,
    "username": "erlangga",
    "room_name": "FP-Jaringan"
  }
}
```

---

## 7.7 ROOM_CHAT_SEND

```json
{
  "type": "ROOM_CHAT_SEND",
  "request_id": "REQ-0500",
  "token": "session-token-value",
  "timestamp": "2026-06-09 20:06:00",
  "payload_size": 0,
  "payload": {
    "room_id": 10,
    "message": "Halo semua, aku upload laporan ya."
  }
}
```

Broadcast:

```json
{
  "type": "ROOM_CHAT_BROADCAST",
  "request_id": "EVT-0501",
  "token": null,
  "timestamp": "2026-06-09 20:06:00",
  "payload_size": 0,
  "payload": {
    "room_id": 10,
    "sender_username": "erlangga",
    "message": "Halo semua, aku upload laporan ya."
  }
}
```

---

## 7.8 UPLOAD_INIT

```json
{
  "type": "UPLOAD_INIT",
  "request_id": "REQ-0600",
  "token": "session-token-value",
  "timestamp": "2026-06-09 20:07:00",
  "payload_size": 0,
  "payload": {
    "room_id": 10,
    "filename": "laporan.pdf",
    "filesize": 2457600,
    "chunk_size": 65536,
    "total_chunks": 38,
    "checksum_sha256": "9f2a8c..."
  }
}
```

Response:

```json
{
  "type": "UPLOAD_READY",
  "request_id": "REQ-0600",
  "token": null,
  "timestamp": "2026-06-09 20:07:01",
  "payload_size": 0,
  "payload": {
    "transfer_id": 1001,
    "start_chunk": 0
  }
}
```

---

## 7.9 UPLOAD_CHUNK

Header:

```json
{
  "type": "UPLOAD_CHUNK",
  "request_id": "REQ-0601",
  "token": "session-token-value",
  "timestamp": "2026-06-09 20:07:02",
  "payload_size": 65536,
  "payload": {
    "transfer_id": 1001,
    "chunk_index": 5
  }
}
```

Binary payload:
```txt
<65536 bytes>
```

ACK:

```json
{
  "type": "CHUNK_ACK",
  "request_id": "REQ-0601",
  "token": null,
  "timestamp": "2026-06-09 20:07:02",
  "payload_size": 0,
  "payload": {
    "transfer_id": 1001,
    "chunk_index": 5,
    "status": "received"
  }
}
```

---

## 8. Error Format

```json
{
  "type": "ERROR",
  "request_id": "REQ-XXXX",
  "token": null,
  "timestamp": "2026-06-09 20:00:00",
  "payload_size": 0,
  "payload": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message"
  }
}
```

---

## 9. Error Codes

| Code | Meaning |
|---|---|
| INVALID_PACKET | Packet tidak sesuai format |
| INVALID_JSON | JSON rusak |
| MISSING_FIELD | Field wajib kosong |
| INVALID_TOKEN | Token invalid |
| EXPIRED_TOKEN | Token expired |
| INVALID_CREDENTIALS | Username/password salah |
| DUPLICATE_LOGIN | User sudah login |
| USERNAME_TAKEN | Username sudah dipakai |
| USER_NOT_FOUND | User tidak ditemukan |
| ROOM_NOT_FOUND | Room tidak ditemukan |
| ROOM_ALREADY_EXISTS | Room sudah ada |
| NOT_IN_ROOM | User belum join room |
| RATE_LIMIT_EXCEEDED | Terlalu banyak request |
| FILE_TOO_LARGE | File melebihi batas |
| FILE_NOT_FOUND | File tidak ditemukan |
| CHECKSUM_FAILED | Checksum tidak cocok |
| TRANSFER_TIMEOUT | Transfer timeout |
| BACKEND_DOWN | Backend server down |
| INTERNAL_ERROR | Error internal server |

---

## 10. Protocol Rules

1. Semua request harus punya `type`.
2. Semua request selain register/login harus punya token.
3. Semua packet harus melalui length-prefixed framing.
4. Binary payload hanya boleh dipakai untuk file chunk.
5. Server harus menolak packet dengan field tidak lengkap.
6. Server tidak boleh crash saat menerima malformed packet.
7. Setiap response harus menyertakan `request_id` yang sama jika response untuk request tertentu.
8. Event server boleh memakai `request_id` dengan prefix `EVT-`.
9. File chunk harus dikirim sesuai `transfer_id` dan `chunk_index`.
10. ACK wajib dikirim untuk setiap upload chunk.
