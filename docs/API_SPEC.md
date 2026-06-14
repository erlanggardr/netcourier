# API / Protocol Specification - NetCourier

NetCourier does not use a REST API as its primary communication method. The system utilizes a **custom application layer protocol** over **TCP sockets**.

This document defines the packet format, message types, request/response structures, and error codes.

---

## 1. Transport Protocol

- Protocol: TCP
- Serialization: JSON
- Binary payload: Used for file chunks
- Framing: Length-prefixed packets

---

## 2. Packet Framing

Since TCP is a stream-oriented protocol, every packet must have framing to delimit message boundaries.

Format:

```txt
[4 bytes header_length][JSON_HEADER][BINARY_PAYLOAD optional]
```

- `header_length`: 4-byte big-endian unsigned integer.
- `JSON_HEADER`: UTF-8 encoded JSON string.
- `BINARY_PAYLOAD`: Optional raw bytes for file chunks.

If there is no binary payload:
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

Fields:

| Field | Type | Required | Description |
|---|---|---:|---|
| type | string | yes | Message type |
| request_id | string | yes | Request ID for tracing |
| token | string/null | no | Session token |
| timestamp | string | yes | Transmission timestamp |
| payload_size | int | yes | Binary payload size in bytes |
| payload | object | yes | Request metadata payload |

---

## 4. Gateway Client-Facing Message Types

Clients communicate with the Gateway for authentication, Private Messages (PM), online user directories, and room directories.

| Type | Direction | Description |
|---|---|---|
| REGISTER | Client -> Gateway | Register a new user |
| REGISTER_OK | Gateway -> Client | Successful registration |
| LOGIN | Client -> Gateway | Log in user |
| LOGIN_OK | Gateway -> Client | Successful login |
| LOGOUT | Client -> Gateway | Log out user |
| LOGOUT_OK | Gateway -> Client | Successful logout |
| LIST_ONLINE_USERS | Client -> Gateway | Request list of online users |
| ONLINE_USERS_RESPONSE | Gateway -> Client | Response containing online users |
| PRIVATE_MESSAGE_SEND | Client -> Gateway | Send a private message (PM) |
| PRIVATE_MESSAGE_RECEIVED | Gateway -> Client | PM received notification |
| PRIVATE_MESSAGE_STATUS | Gateway -> Client | Status of sent PM |
| PM_HISTORY_REQUEST | Client -> Gateway | Request PM history |
| PM_HISTORY_RESPONSE | Gateway -> Client | Response containing PM history |
| LIST_ROOMS | Client -> Gateway | Request list of rooms |
| ROOM_LIST_RESPONSE | Gateway -> Client | Response containing room list |
| CREATE_ROOM | Client -> Gateway | Create a new chat room |
| ROOM_ASSIGNED | Gateway -> Client | Room created and Process Server assigned |
| JOIN_ROOM | Client -> Gateway | Request to join a chat room |
| ROOM_LOCATION | Gateway -> Client | Location of assigned Process Server |
| PING | Client -> Gateway | Latency check |
| PONG | Gateway -> Client | Response to ping |
| ERROR | Gateway -> Client | Error response |

---

## 5. Gateway Backend-Control Message Types

Process Servers communicate with the Gateway for registration, heartbeats, and token validation.

| Type | Direction | Description |
|---|---|---|
| REGISTER_BACKEND | Server -> Gateway | Register a backend server |
| BACKEND_REGISTERED | Gateway -> Server | Successful registration |
| HEARTBEAT | Server -> Gateway | Update server status / load metrics |
| HEARTBEAT_ACK | Gateway -> Server | Heartbeat acknowledgment |
| VALIDATE_TOKEN | Server -> Gateway | Validate client session token |
| TOKEN_VALID | Gateway -> Server | Session token is valid |
| TOKEN_INVALID | Gateway -> Server | Session token is invalid |
| USER_ROOM_STATUS_UPDATE | Server -> Gateway | Update user state (in_room / waiting) |
| ROOM_STATS_UPDATE | Server -> Gateway | Update count of active users/transfers |
| BACKEND_SHUTDOWN | Server -> Gateway | Server is shutting down |

---

## 6. Client to Process Server Message Types

Clients communicate with the Process Server for room chat, reactions, status updates, and file transfers.

| Type | Direction | Description |
|---|---|---|
| AUTH_BACKEND | Client -> Server | Authenticate with Process Server using session token |
| AUTH_BACKEND_OK | Server -> Client | Authentication successful |
| JOIN_ROOM_BACKEND | Client -> Server | Join a chat room on the backend |
| JOIN_ROOM_OK | Server -> Client | Successfully joined the room |
| LEAVE_ROOM | Client -> Server | Leave a chat room |
| LEAVE_ROOM_OK | Server -> Client | Successfully left the room |
| ROOM_CHAT_SEND | Client -> Server | Send a message to the chat room |
| ROOM_CHAT_BROADCAST | Server -> Client | Broadcasted chat message to room members |
| ROOM_HISTORY_REQUEST | Client -> Server | Request room chat history |
| ROOM_HISTORY_RESPONSE | Server -> Client | Response containing room history |
| FILE_LIST_REQUEST | Client -> Server | Request list of files uploaded in room |
| FILE_LIST_RESPONSE | Server -> Client | Response containing file list |
| UPLOAD_INIT | Client -> Server | Initialize file upload |
| UPLOAD_READY | Server -> Client | Server is ready for upload |
| UPLOAD_CHUNK | Client -> Server | Send upload chunk (with binary payload) |
| CHUNK_ACK | Server -> Client | Acknowledge chunk reception |
| UPLOAD_FINISH | Client -> Server | Finish file upload |
| UPLOAD_SUCCESS | Server -> Client | Upload verified (checksum matched) |
| DOWNLOAD_REQUEST | Client -> Server | Request file download |
| DOWNLOAD_READY | Server -> Client | Server is ready to send file chunks |
| DOWNLOAD_CHUNK | Server -> Client | Send download chunk (with binary payload) |
| DOWNLOAD_FINISH | Server -> Client | Download finished successfully |
| RESUME_TRANSFER | Client -> Server | Request to resume upload/download |
| TRANSFER_STATUS | Server -> Client | Current transfer status |
| SYSTEM_EVENT | Server -> Client | System event notification |
| PING | Client -> Server | Latency check |
| PONG | Server -> Client | Response to ping |
| ERROR | Server -> Client | Error response |

---

## 7. Packet Examples

### 7.1 REGISTER

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

### 7.2 LOGIN

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

### 7.3 PRIVATE_MESSAGE_SEND

Request:

```json
{
  "type": "PRIVATE_MESSAGE_SEND",
  "request_id": "REQ-0100",
  "token": "session-token-value",
  "timestamp": "2026-06-09 20:02:00",
  "payload_size": 0,
  "payload": {
    "to_username": "budi",
    "message": "Bro, check the file in the room later."
  }
}
```

Recipient receives:

```json
{
  "type": "PRIVATE_MESSAGE_RECEIVED",
  "request_id": "EVT-0200",
  "token": null,
  "timestamp": "2026-06-09 20:02:00",
  "payload_size": 0,
  "payload": {
    "from_username": "erlangga",
    "message": "Bro, check the file in the room later.",
    "status": "delivered"
  }
}
```

---

### 7.4 CREATE_ROOM

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

### 7.5 JOIN_ROOM

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

### 7.6 AUTH_BACKEND

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

### 7.7 ROOM_CHAT_SEND

```json
{
  "type": "ROOM_CHAT_SEND",
  "request_id": "REQ-0500",
  "token": "session-token-value",
  "timestamp": "2026-06-09 20:06:00",
  "payload_size": 0,
  "payload": {
    "room_id": 10,
    "message": "Hello everyone, I'm uploading the report."
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
    "message": "Hello everyone, I'm uploading the report."
  }
}
```

---

### 7.8 UPLOAD_INIT

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

### 7.9 UPLOAD_CHUNK

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
| INVALID_PACKET | Packet format is invalid |
| INVALID_JSON | JSON payload is malformed |
| MISSING_FIELD | Required fields are missing |
| INVALID_TOKEN | Session token is invalid |
| EXPIRED_TOKEN | Session token has expired |
| INVALID_CREDENTIALS | Username or password is incorrect |
| DUPLICATE_LOGIN | User is already logged in |
| USERNAME_TAKEN | Username is already taken |
| USER_NOT_FOUND | User not found |
| ROOM_NOT_FOUND | Chat room not found |
| ROOM_ALREADY_EXISTS | Chat room already exists |
| NOT_IN_ROOM | User has not joined the room |
| RATE_LIMIT_EXCEEDED | Rate limit has been exceeded |
| FILE_TOO_LARGE | File size exceeds the maximum limit |
| FILE_NOT_FOUND | File not found |
| CHECKSUM_FAILED | Checksum verification failed |
| TRANSFER_TIMEOUT | File transfer session timed out |
| BACKEND_DOWN | Backend process server is offline |
| INTERNAL_ERROR | Internal server error |

---

## 10. Protocol Rules

1. All request packets must have a `type` field.
2. All request packets except for `REGISTER` and `LOGIN` must include a valid session `token`.
3. All network communications must follow the length-prefixed packet framing format.
4. Binary payloads must only be used for transferring file chunks.
5. Servers must reject any packets with incomplete or missing mandatory fields.
6. Servers must handle exceptions gracefully and not crash when receiving malformed packets.
7. Every response packet must include the matching `request_id` of the request it is responding to.
8. Server-initiated event packets should use a `request_id` prefixed with `EVT-`.
9. File chunks must correspond to a valid `transfer_id` and correct `chunk_index`.
10. An acknowledgment (ACK) must be sent back to the sender for every successfully written upload chunk.
