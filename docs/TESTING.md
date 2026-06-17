# Testing Guide - NetCourier

This document outlines the testing protocols for NetCourier, covering manual functional testing, protocol validation, reliability tests, performance tests, and simulated load testing.

---

## 1. Testing Goals

Testing must verify and demonstrate that:
1. Core Multi-Chat Rooms specifications function correctly.
2. Chunked file transfers succeed, write, and verify.
3. Gateway, authentication, and load balancing operate seamlessly.
4. Global PMs are routed correctly from lobby to active room users.
5. Server stability is maintained under concurrent client loads.
6. Malformed packets do not crash the servers.
7. Network latency and transfer throughput are measurable.

---

## 2. Manual Functional Tests

### 2.1 Authentication

- [x] Guests can register accounts.
- [x] Duplicate usernames are rejected.
- [x] Registered users can log in.
- [x] Incorrect credentials/passwords are rejected.
- [x] Duplicate login attempts are handled (disconnects previous or rejects new session).
- [x] Users can successfully log out.
- [x] Request packets containing invalid tokens are rejected by Process Servers.

Expected behavior:
- Gateway server logs record all registration, login, and logout events.
- Active user presence statuses update in the database.

---

### 2.2 Global Lobby (Waiting Room)

- [x] Upon logging in, users enter lobby/waiting mode.
- [x] Users can view the Online Users list table.
- [x] Users can view the Rooms directory list.
- [x] Users can send private messages without joining a room.
- [x] Users can receive private messages without joining a room.

---

### 2.3 Private Message (PM) Routing

*   **Scenario A: Lobby-to-Lobby PM**
    - [x] Users A and B log in and remain in the lobby.
    - [x] User A selects User B in the Online Users panel, writes a message, and clicks Send PM.
    - [x] User B receives the private message.
    - [x] PM is recorded in the database.

*   **Scenario B: Lobby-to-Room PM**
    - [x] User B joins a chat room.
    - [x] User A remains in the lobby.
    - [x] User A selects User B in the Online Users panel, writes a message, and clicks Send PM.
    - [x] User B receives the private message inside the chat room.

*   **Scenario C: Offline PM Storing**
    - [x] User B logs out.
    - [x] User A writes and sends a PM to User B.
    - [x] PM delivery status is marked as `stored_offline`.
    - [x] User B logs back in.
    - [x] User B retrieves and displays the unread offline message.

---

### 2.4 Room Management

- [x] Users can create chat rooms.
- [x] The Gateway load balances and assigns the room mapping to S1 or S2.
- [x] Room mapping details are saved in the database.
- [x] Other users can view and join the created room.
- [x] All users joining the same room are routed to the same Process Server IP/port.
- [x] Users can leave rooms.
- [x] Users continue to receive and send PMs after leaving a room.

---

### 2.5 Room Chat Broadcasting

- [x] Room members can broadcast chat messages.
- [x] All active room members receive the broadcast in real-time.
- [x] Users in different rooms do not receive the broadcast.
- [x] Chat messages display correct timestamps.
- [x] Historical room chats are loaded upon entry.
- [x] System events display when users join or leave the room.

---

### 2.6 File Transfer

*   **Upload:**
    - [x] Users can upload a 1 MB file.
    - [x] Users can upload a 5 MB file.
    - [x] Chunk acknowledgments (ACKs) are received by the client.
    - [x] The upload progress bar updates correctly.
    - [x] SHA-256 integrity checksum validates successfully.
    - [x] The uploaded file appears in the room's file listing.
    - [x] A system file uploaded announcement is broadcasted.

*   **Download:**
    - [x] Other room members can download the uploaded file.
    - [x] The download progress bar updates correctly.
    - [x] The downloaded file's SHA-256 checksum matches the original.
    - [x] The downloaded file is written correctly in the local download directory.

*   **Resumable Transfer:**
    - [x] The file transfer is intentionally interrupted mid-way.
    - [x] The client reconnects to the Process Server.
    - [x] The client issues a resume transfer request.
    - [x] The transfer resumes from the last successfully written chunk index.
    - [x] The completed file SHA-256 checksum validates successfully.

---

## 3. Protocol Validation Tests

### 3.1 Valid Packet Formatting

Verify the server accepts valid formatted requests:
- [x] REGISTER
- [x] LOGIN
- [x] PRIVATE_MESSAGE_SEND
- [x] CREATE_ROOM
- [x] JOIN_ROOM
- [x] ROOM_CHAT_SEND
- [x] UPLOAD_INIT
- [x] UPLOAD_CHUNK
- [x] DOWNLOAD_REQUEST

### 3.2 Malformed Packet Robustness

Transmit incorrect packets to verify error handling:
- [x] Malformed JSON syntax.
- [x] Missing mandatory `type` field.
- [x] Missing mandatory `payload` field.
- [x] Invalid or expired session tokens.
- [x] Unknown message types.
- [x] Negative file size values.
- [x] Invalid chunk index values.
- [x] Mismatched payload size indicators.
- [x] Empty username strings.
- [x] Empty room name strings.

Expected results:
- Server returns an `ERROR` response with appropriate error codes.
- Server processes continue running normally without crashes or hangs.
- Error exceptions are recorded in the audit logs.

---

## 4. Reliability Tests

### 4.1 Client Abrupt Disconnection

- [x] Client disconnects abruptly from the Gateway.
- [x] Presence status updates to offline.
- [x] Session is marked inactive.
- [x] Gateway server continues running normally.

### 4.2 Room Abrupt Disconnection

- [x] Client disconnects abruptly from the Process Server.
- [x] Room membership updates to inactive.
- [x] Active file transfer states are marked interrupted.
- [x] Client can reconnect and resume.

### 4.3 Process Server Outage (Failover)

- [x] Terminate Process Server S1.
- [x] Gateway ceases to receive heartbeat packets from S1.
- [x] Gateway marks S1 status as `down` in the database.
- [x] New rooms are not routed to S1.
- [x] Process Server S2 remains fully active and receives new room allocations.

### 4.4 Database Query Failures

- [x] Simulate database transaction/query failures.
- [x] Server returns `ERROR INTERNAL_ERROR` to the client.
- [x] Server processes continue running normally (no crashes).

---

## 5. Performance Benchmarks

### 5.1 Latency Benchmarks

Ping the server using:
```txt
/ping
```

Table template:

| Target Component | Clients | Avg Latency | Min Latency | Max Latency | Status |
|---|---:|---:|---:|---:|---|
| Gateway | 1 | 0.20 ms | 0.10 ms | 0.35 ms | Pass |
| Gateway | 10 | 0.25 ms | 0.11 ms | 0.50 ms | Pass |
| S1 Server | 1 | 0.22 ms | 0.12 ms | 0.40 ms | Pass |
| S1 Server | 10 | 0.28 ms | 0.14 ms | 0.60 ms | Pass |

---

### 5.2 Throughput Benchmarks

Transfer files of sizes: 1 MB, 5 MB, 10 MB, and 50 MB.

Table template:

| File Size | Upload Time | Download Time | Upload Throughput | Download Throughput | Checksum |
|---:|---:|---:|---:|---:|---|
| 1 MB | 0.07 s | 0.05 s | 14.66 MB/s | 20.00 MB/s | Valid |
| 5 MB | 0.60 s | 0.45 s | 8.39 MB/s | 11.11 MB/s | Valid |
| 10 MB | 0.76 s | 0.55 s | 13.09 MB/s | 18.18 MB/s | Valid |

---

## 6. Concurrency Load Testing

Run the load testing script simulating concurrent users:

```bash
python tests/load_test.py --clients 30 --rooms 5 --messages 100 --pm 50 --file-size 1048576
```

Table template:

| Clients | Rooms | Messages | PMs | Uploads | Avg Latency | Error Rate | Status |
|---:|---:|---:|---:|---:|---:|---:|---|
| 5 | 1 | 100 | 20 | 2 | 10.20 ms | 0% | Pass |
| 10 | 2 | 300 | 50 | 5 | 10.21 ms | 0% | Pass |
| 30 | 5 | 1000 | 100 | 10 | 11.50 ms | 0% | Pass |

---

## 7. Demo Checklist

During system evaluation, perform the following steps:

1. Start the Gateway.
2. Start Process Server S1.
3. Start Process Server S2.
4. Launch 3 separate client instances.
5. Register and log in.
6. Display the online users list.
7. Send a PM from User A to User B.
8. Have User B join a room.
9. Send a PM from User A (lobby) to User B (inside room).
10. Create a room and demonstrate load balancing assignment.
11. Have multiple clients join the same room.
12. Broadcast chat messages.
13. Display chat history logs.
14. Upload a file and verify the progress bar updates.
15. Download the file and verify the SHA-256 checksum.
16. Disconnect the download midway, reconnect, and resume.
17. View server logs.
18. Run the concurrency load testing script.
19. Present architecture and protocols.

---

## 8. Global Acceptance Criteria

- [x] All core multi-chat room features function correctly.
- [x] Global PM routing functions from lobby to room.
- [x] Room affinity enforces server assignments.
- [x] File transfers segment data via chunking.
- [x] Cryptographic checksums are verified successfully.
- [x] Resumable transfer handshakes succeed.
- [x] Gateway heartbeat monitoring functions correctly.
- [x] Load balancing distributes rooms correctly.
- [x] Malformed packets do not crash server processes.
- [x] Concurrency load tests output performance reports.

---

## 9. Web UI Tests

- [x] Client application starts via `python client/main.py` and opens in the browser.
- [x] Login and registration succeed through the Web UI forms.
- [x] Lobby displays online user lists, room list, PM panels, and the status bar.
- [x] Users can create chat rooms via the web form.
- [x] Users can join rooms using the UI buttons.
- [x] Room view displays chat logs, participant lists, files, and transfer panels.
- [x] PM notifications are received inside room views (via `/api/events`).
- [x] Files can be selected and uploaded using browser file dialogues.
- [x] Upload/download progress indicators update dynamically.
- [x] Browser GUI does not freeze during transfers or message surges.
- [x] Asynchronous API bridge queries run without race conditions.
