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

- [ ] Guests can register accounts.
- [ ] Duplicate usernames are rejected.
- [ ] Registered users can log in.
- [ ] Incorrect credentials/passwords are rejected.
- [ ] Duplicate login attempts are handled (disconnects previous or rejects new session).
- [ ] Users can successfully log out.
- [ ] Request packets containing invalid tokens are rejected by Process Servers.

Expected behavior:
- Gateway server logs record all registration, login, and logout events.
- Active user presence statuses update in the database.

---

### 2.2 Global Lobby (Waiting Room)

- [ ] Upon logging in, users enter lobby/waiting mode.
- [ ] Users can view the Online Users list table.
- [ ] Users can view the Rooms directory list.
- [ ] Users can send private messages without joining a room.
- [ ] Users can receive private messages without joining a room.

---

### 2.3 Private Message (PM) Routing

*   **Scenario A: Lobby-to-Lobby PM**
    - [ ] Users A and B log in and remain in the lobby.
    - [ ] User A selects User B in the Online Users panel, writes a message, and clicks Send PM.
    - [ ] User B receives the private message.
    - [ ] PM is recorded in the database.

*   **Scenario B: Lobby-to-Room PM**
    - [ ] User B joins a chat room.
    - [ ] User A remains in the lobby.
    - [ ] User A selects User B in the Online Users panel, writes a message, and clicks Send PM.
    - [ ] User B receives the private message inside the chat room.

*   **Scenario C: Offline PM Storing**
    - [ ] User B logs out.
    - [ ] User A writes and sends a PM to User B.
    - [ ] PM delivery status is marked as `stored_offline`.
    - [ ] User B logs back in.
    - [ ] User B retrieves and displays the unread offline message.

---

### 2.4 Room Management

- [ ] Users can create chat rooms.
- [ ] The Gateway load balances and assigns the room mapping to S1 or S2.
- [ ] Room mapping details are saved in the database.
- [ ] Other users can view and join the created room.
- [ ] All users joining the same room are routed to the same Process Server IP/port.
- [ ] Users can leave rooms.
- [ ] Users continue to receive and send PMs after leaving a room.

---

### 2.5 Room Chat Broadcasting

- [ ] Room members can broadcast chat messages.
- [ ] All active room members receive the broadcast in real-time.
- [ ] Users in different rooms do not receive the broadcast.
- [ ] Chat messages display correct timestamps.
- [ ] Historical room chats are loaded upon entry.
- [ ] System events display when users join or leave the room.

---

### 2.6 File Transfer

*   **Upload:**
    - [ ] Users can upload a 1 MB file.
    - [ ] Users can upload a 5 MB file.
    - [ ] Chunk acknowledgments (ACKs) are received by the client.
    - [ ] The upload progress bar updates correctly.
    - [ ] SHA-256 integrity checksum validates successfully.
    - [ ] The uploaded file appears in the room's file listing.
    - [ ] A system file uploaded announcement is broadcasted.

*   **Download:**
    - [ ] Other room members can download the uploaded file.
    - [ ] The download progress bar updates correctly.
    - [ ] The downloaded file's SHA-256 checksum matches the original.
    - [ ] The downloaded file is written correctly in the local download directory.

*   **Resumable Transfer:**
    - [ ] The file transfer is intentionally interrupted mid-way.
    - [ ] The client reconnects to the Process Server.
    - [ ] The client issues a resume transfer request.
    - [ ] The transfer resumes from the last successfully written chunk index.
    - [ ] The completed file SHA-256 checksum validates successfully.

---

## 3. Protocol Validation Tests

### 3.1 Valid Packet Formatting

Verify the server accepts valid formatted requests:
- [ ] REGISTER
- [ ] LOGIN
- [ ] PRIVATE_MESSAGE_SEND
- [ ] CREATE_ROOM
- [ ] JOIN_ROOM
- [ ] ROOM_CHAT_SEND
- [ ] UPLOAD_INIT
- [ ] UPLOAD_CHUNK
- [ ] DOWNLOAD_REQUEST

### 3.2 Malformed Packet Robustness

Transmit incorrect packets to verify error handling:
- [ ] Malformed JSON syntax.
- [ ] Missing mandatory `type` field.
- [ ] Missing mandatory `payload` field.
- [ ] Invalid or expired session tokens.
- [ ] Unknown message types.
- [ ] Negative file size values.
- [ ] Invalid chunk index values.
- [ ] Mismatched payload size indicators.
- [ ] Empty username strings.
- [ ] Empty room name strings.

Expected results:
- Server returns an `ERROR` response with appropriate error codes.
- Server processes continue running normally without crashes or hangs.
- Error exceptions are recorded in the audit logs.

---

## 4. Reliability Tests

### 4.1 Client Abrupt Disconnection

- [ ] Client disconnects abruptly from the Gateway.
- [ ] Presence status updates to offline.
- [ ] Session is marked inactive.
- [ ] Gateway server continues running normally.

### 4.2 Room Abrupt Disconnection

- [ ] Client disconnects abruptly from the Process Server.
- [ ] Room membership updates to inactive.
- [ ] Active file transfer states are marked interrupted.
- [ ] Client can reconnect and resume.

### 4.3 Process Server Outage (Failover)

- [ ] Terminate Process Server S1.
- [ ] Gateway ceases to receive heartbeat packets from S1.
- [ ] Gateway marks S1 status as `down` in the database.
- [ ] New rooms are not routed to S1.
- [ ] Process Server S2 remains fully active and receives new room allocations.

### 4.4 Database Query Failures

- [ ] Simulate database transaction/query failures.
- [ ] Server returns `ERROR INTERNAL_ERROR` to the client.
- [ ] Server processes continue running normally (no crashes).

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
| Gateway | 1 | ... ms | ... | ... | Pass |
| Gateway | 10 | ... ms | ... | ... | Pass |
| S1 Server | 1 | ... ms | ... | ... | Pass |
| S1 Server | 10 | ... ms | ... | ... | Pass |

---

### 5.2 Throughput Benchmarks

Transfer files of sizes: 1 MB, 5 MB, 10 MB, and 50 MB.

Table template:

| File Size | Upload Time | Download Time | Upload Throughput | Download Throughput | Checksum |
|---:|---:|---:|---:|---:|---|
| 1 MB | ... s | ... s | ... MB/s | ... MB/s | Valid |
| 5 MB | ... s | ... s | ... MB/s | ... MB/s | Valid |
| 10 MB | ... s | ... s | ... MB/s | ... MB/s | Valid |

---

## 6. Concurrency Load Testing

Run the load testing script simulating concurrent users:

```bash
python tests/load_test.py --clients 30 --rooms 5 --messages 100 --pm 50 --file-size 1048576
```

Table template:

| Clients | Rooms | Messages | PMs | Uploads | Avg Latency | Error Rate | Status |
|---:|---:|---:|---:|---:|---:|---:|---|
| 5 | 1 | 100 | 20 | 2 | ... ms | ...% | Pass |
| 10 | 2 | 300 | 50 | 5 | ... ms | ...% | Pass |
| 30 | 5 | 1000 | 100 | 10 | ... ms | ...% | Pass |

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

- [ ] All core multi-chat room features function correctly.
- [ ] Global PM routing functions from lobby to room.
- [ ] Room affinity enforces server assignments.
- [ ] File transfers segment data via chunking.
- [ ] Cryptographic checksums are verified successfully.
- [ ] Resumable transfer handshakes succeed.
- [ ] Gateway heartbeat monitoring functions correctly.
- [ ] Load balancing distributes rooms correctly.
- [ ] Malformed packets do not crash server processes.
- [ ] Concurrency load tests output performance reports.

---

## 9. Web UI Tests

- [ ] Client application starts via `python client/main.py` and opens in the browser.
- [ ] Login and registration succeed through the Web UI forms.
- [ ] Lobby displays online user lists, room list, PM panels, and the status bar.
- [ ] Users can create chat rooms via the web form.
- [ ] Users can join rooms using the UI buttons.
- [ ] Room view displays chat logs, participant lists, files, and transfer panels.
- [ ] PM notifications are received inside room views (via `/api/events`).
- [ ] Files can be selected and uploaded using browser file dialogues.
- [ ] Upload/download progress indicators update dynamically.
- [ ] Browser GUI does not freeze during transfers or message surges.
- [ ] Asynchronous API bridge queries run without race conditions.
