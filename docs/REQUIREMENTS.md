# Requirements - NetCourier

## 1. Product Overview

**NetCourier** is a high-performance, distributed multi-chat room application built on custom TCP sockets with reliable chunked file transfer support. The system is implemented in Python and implements a distributed client-server architecture, custom application layer protocol, message serialization, socket programming, concurrency/multithreading, reconnect handling, timeout management, server auditing, performance measurement, and server load simulation.

NetCourier is designed with the following routing flow:

```txt
Client -> Gateway/Auth/Load Balancer -> Process Server S1/S2 -> Central Database
```

Clients maintain persistent connections to the Gateway for global features such as authentication, global presence, private messaging, and the room directory. When a user joins a room, the Gateway routes the client to the specific Process Server assigned to host that room.

---

## 2. Goals

### G-01: Meet Multi-Chat Rooms Final Project Specifications

The core system must support:
- Multiple concurrent chat rooms.
- Multiple client connections per room.
- Creating rooms.
- Joining rooms.
- Leaving rooms.
- Room chat broadcasting.
- Global private messaging (PM).
- Raw TCP socket communications.
- Multithreaded socket handling.
- JSON-based message serialization.
- Secure credential authentication.
- Online users directory.
- Room directory.
- Chat history persistence.
- Message timestamps.
- Detailed server audit logging.

### G-02: Provide Robust Core Features (Bonus Scope)

The system extends standard specs with:
- Integrated chunked file transfers.
- SHA-256 integrity checksum validations.
- Resumable transfer handshakes (upload/download resume).
- Database chat history persistence.
- Dynamic load balancing based on room affinity.
- Network latency metrics.
- Transfer throughput calculations.
- Concurrency load testing simulations.

### G-03: Keep Scope Feasible

The features must be robust enough for demonstration, but keeping away from voice/video protocols or unnecessary UI bloat.

---

## 3. User Roles

### 3.1 Guest (Unauthenticated)

A user who has not registered or logged in.

Privileges:
- User registration.
- User login.

Restrictions:
- Cannot join rooms.
- Cannot view room details.
- Cannot send room messages.
- Cannot send private messages.
- Cannot perform file transfers.

### 3.2 Authenticated User

A user successfully authenticated through the Gateway.

Privileges:
- View the global online users directory.
- Send private messages (PM).
- View private message histories.
- View active rooms directory.
- Create new rooms.
- Join chat rooms.
- Leave chat rooms.
- View room chat history logs.
- Broadcast messages inside joined rooms.
- Perform file transfers inside joined rooms.

### 3.3 Room Admin (Room Owner)

The user who created the room or holds administrative credentials.

Additional Privileges:
- Delete uploaded files in the room.
- Soft-delete room chat messages.
- Kick users from the room.
- View room activity logs.

### 3.4 Server Operator / Administrator

The administrator deploying the NetCourier system.

Privileges:
- Launch and configure the Gateway.
- Launch and configure Process Servers (S1/S2).
- Monitor system logs in real-time.
- Run load testing benchmark suites.
- Analyze performance metrics.

---

## 4. Functional Requirements

### 4.1 Authentication and Session

#### FR-AUTH-01 Register
The system must allow guests to create user accounts.
- **Input:** Username, password, display name.
- **Rules:**
  - Username must be unique.
  - Password must be at least 6 characters long.
  - Passwords must be hashed (PBKDF2 with salt) and never stored in plain text.
  - Usernames must not contain special or malicious characters.
- **Output:**
  - `REGISTER_OK` on success.
  - `ERROR USERNAME_TAKEN` if username is already registered.
  - `ERROR INVALID_INPUT` if validation fails.

#### FR-AUTH-02 Login
The system must allow users to log in through the Gateway.
- **Input:** Username, password.
- **Rules:**
  - Valid credentials yield a unique session token.
  - Duplicate login attempts are rejected or terminate previous sessions based on configuration.
  - The token must be included in subsequent communications for verification.
- **Output:**
  - `LOGIN_OK` + token on success.
  - `ERROR INVALID_CREDENTIALS` on mismatch.
  - `ERROR DUPLICATE_LOGIN` if already logged in.

#### FR-AUTH-03 Logout
Users can log out from the Gateway.
- **Rules:**
  - Session token is invalidated.
  - User presence state transitions to offline.
  - Gateway notifies the Process Server if the user is currently active inside a room.

#### FR-AUTH-04 Token Validation
Process Servers must validate user session tokens with the Gateway before accepting client connections.
- **Flow:**
  1. Client connects to the Process Server and sends its session token.
  2. The Process Server sends a `VALIDATE_TOKEN` query to the Gateway.
  3. The Gateway responds with `TOKEN_VALID` or `TOKEN_INVALID`.

---

### 4.2 Gateway and Load Balancing

#### FR-GW-01 Backend Register
Every Process Server must register with the Gateway upon starting.
- **Data:** `server_id`, `host`, `port`, `status`.

#### FR-GW-02 Backend Heartbeat
Process Servers must transmit periodic heartbeats to the Gateway.
- **Data:** `server_id`, `active_rooms`, `active_clients`, `active_transfers`, `last_heartbeat_at`.

#### FR-GW-03 Room Directory
The Gateway maintains a room mapping directory:
```txt
room_name -> server_id
```
- **Objective:** Users joining the same room are always routed to the same Process Server.

#### FR-GW-04 Room Affinity
A single room must strictly run on one Process Server.
- *Example:* Room `FP-Jaringan` -> S1. All users joining `FP-Jaringan` are routed to S1.

#### FR-GW-05 Load Balancing Algorithm
The Gateway selects the target server for a new room based on:
1. Server status must be `alive`.
2. Lowest count of `active_rooms`.
3. Lowest count of `active_clients`.
4. Fallback to round-robin on ties.

#### FR-GW-06 Waiting Room (Global Lobby)
Upon logging in, the user resides in the Gateway's global lobby / waiting room.
In this lobby, users can:
- View online users.
- Send PMs to other users.
- View active room lists.
- Create new rooms.
- Join chat rooms.

---

### 4.3 Global Private Messaging (PM)

#### FR-PM-01 Send PM
Users can send private messages (PM) to other users from either the lobby or from inside active chat rooms.
- **Flow:**
  1. Client sends a PM to the Gateway through its Gateway connection.
  2. Gateway validates the sender token.
  3. Gateway persists the PM in the database.
  4. Gateway forwards the PM to the recipient if online.
  5. Gateway returns delivery status to the sender.

#### FR-PM-02 Receive PM While In Room
Users active in a chat room on a Process Server must still receive incoming PMs because their Gateway socket connection remains active.

#### FR-PM-03 PM History
Users can query their private message history with other users.

#### FR-PM-04 Offline PM
If the recipient is offline:
- The PM is stored in the database.
- Message status is marked as `stored_offline`.
- PM is delivered immediately when the recipient logs in.

---

### 4.4 Room Management

#### FR-ROOM-01 Create Room
Users can create rooms through the Gateway.
- **Flow:**
  1. Client sends `CREATE_ROOM` to the Gateway.
  2. Gateway selects the target Process Server.
  3. Gateway stores the room entry and the `room_mapping` registry.
  4. Gateway returns the location of the Process Server.
  5. The client automatically connects to the designated Process Server.

#### FR-ROOM-02 Join Room
Users can join existing chat rooms.
- **Flow:**
  1. Client sends `JOIN_ROOM` to the Gateway.
  2. Gateway retrieves the server location from the `room_mapping`.
  3. Gateway returns the host/port of the Process Server.
  4. Client connects to the Process Server and authenticates.
  5. Process Server validates token against Gateway and loads history.

#### FR-ROOM-03 Leave Room
Users can leave rooms.
- **Rules:**
  - User ceases to receive room broadcasts.
  - PM remains active through the Gateway.
  - Process Server updates the membership status to inactive.

#### FR-ROOM-04 Room List
Gateway provides the directory of rooms.
- **Data:** `room_name`, `server_id`, `active_user_count`, `total_file_count`, `visibility`.

#### FR-ROOM-05 Online User List
The Gateway maintains a global online user presence list. Process Servers maintain the participant listing per room.

---

### 4.5 Room Chat

#### FR-CHAT-01 Broadcast Message
Users can broadcast chat messages to all users in the same room.
- **Flow:**
  1. Client sends a message packet to the Process Server.
  2. The Process Server validates that the sender is an active member of the room.
  3. The Process Server persists the message in the database.
  4. The Process Server broadcasts the message to all clients in the room.

#### FR-CHAT-02 Chat History
Upon joining a room, users automatically receive the last N historical messages (default: 50).

#### FR-CHAT-03 Message Timestamps
Every chat message must include a timestamp formatted as:
```txt
YYYY-MM-DD HH:MM:SS
```

#### FR-CHAT-04 System Messages
System notifications are broadcasted when:
- A user joins the room.
- A user leaves the room.
- A file upload initializes.
- A file upload completes successfully.
- A file checksum validation fails.
- A user disconnects or reconnects.

---

### 4.6 File Transfer

#### FR-FILE-01 File List
Users can query the list of uploaded files in the room.
- **Fields:** `file_id`, `filename`, `size`, `uploader`, `checksum`, `status`, `uploaded_at`.

#### FR-FILE-02 Upload File
Users can upload files to the room.
- **Rules:**
  - Files are uploaded in chunk segments.
  - The server returns a `CHUNK_ACK` for each written chunk.
  - SHA-256 checksum integrity is verified upon completion.
  - Metadata is stored in the database.
  - Physical files are saved in the storage directory of the Process Server node.

#### FR-FILE-03 Download File
Users can download files from the room.
- **Rules:**
  - Server transmits files chunk-by-chunk.
  - Client updates transfer progress indicators.
  - Client verifies SHA-256 checksum integrity upon download completion.

#### FR-FILE-04 Chunking
The default chunk size is **64 KB** for standard TCP packets.
*Note: The Web UI client dynamically scales chunk sizes from 1MB up to 16MB based on file size for localhost transfer speed optimization.*

#### FR-FILE-05 Resume Transfer
Interrupted file transfers can be resumed.
- **Rules:**
  - Process Server stores the transfer transaction state.
  - Client sends a `RESUME_TRANSFER` request.
  - Transfer resumes from the last successfully written chunk index.

#### FR-FILE-06 Checksum SHA-256
SHA-256 hashes validate upload and download integrity.
- **If checksum fails:**
  - File status is marked as `corrupted`.
  - Client is notified of the failure.
  - Audit log record is emitted.

---

### 4.7 Logging and Metrics

#### FR-LOG-01 Server Logging
All components must log operational events: login/registrations, room creations/joins/leaves, room chats, PM routing, uploads/downloads, checksum outcomes, malformed packets, timeouts, socket reconnections, load balancing decisions, and server heartbeats.

#### FR-METRIC-01 Latency Measurement
Clients can execute `/ping` commands to measure latency to the Gateway and Process Servers.

#### FR-METRIC-02 Throughput Measurement
Upload/download events must record bytes transferred, transfer duration, and calculated net throughput.

#### FR-METRIC-03 Load Test
A benchmarking utility script is provided to simulate: concurrent client logins, concurrent PM routing, concurrent room entries, high-frequency chat broadcasting, and parallel file transfers.

---

## 5. Non-Functional Requirements

### 5.1 Performance
- Minimum of 5 real concurrent clients during live demo.
- Target simulation of 30 clients via load test.
- Extremely low local chat latency.
- Successful transfer of 1MB, 5MB, 10MB, up to 1GB files.
- Server must remain stable under rapid message bursts.

### 5.2 Reliability
- Server must handle abrupt client socket disconnections gracefully.
- Gateway must exclude dead nodes from room load balancing.
- Process Servers must reject invalid tokens.
- File transfers must support resumption after disconnection.
- Malformed packets must not crash the server.

### 5.3 Security
- Passwords must be hashed using PBKDF2.
- Session tokens are mandatory for all queries except registration and login.
- Path traversal must be blocked during file reads/writes.
- Maximum file sizes must be enforced.
- Rate limits applied to chats and PMs.
- All packets must be validated before processing.

### 5.4 Maintainability
- Modular codebase structure.
- Common protocols shared in `common/` modules.
- Dedicated handler functions per message type.
- Consistent log formats.
- Documentation updated alongside design changes.

### 5.5 Usability
- Web UI easy to navigate and does not rely on CLI commands.
- Clear help dialog for features and command list.
- Friendly error messages and alerts.
- Live progress bars for file transfers.
- Visually distinct waiting room and room chat panels.
- Async HTTP calls (fetch) and API bridge event queue prevent UI freezes.

---

## 6. Out of Scope

The following features are not required:
- Voice and video chat.
- Screen sharing.
- Complex native mobile apps.
- Distributed/replicated file storage.
- Automatic live room migration.
- Full end-to-end encryption (E2EE).
- Nginx as the primary load balancer.

---

## 7. Success Criteria

The project is successful if:
1. Users can register and log in.
2. Users can PM globally from lobby to room.
3. Users can create, join, and leave rooms.
4. Users can send room messages.
5. Users receive historical chat messages.
6. Users can upload and download files.
7. File transfers utilize chunking.
8. Checksums match and verify successfully.
9. Resumable transfer is demonstrable.
10. Gateway balances loads and routes rooms between S1 and S2.
11. Backend heartbeat runs.
12. Load tests produce measurable performance logs.
13. Servers remain online under malformed packets and sudden disconnects.
