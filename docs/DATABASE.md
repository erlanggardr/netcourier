# Database Design - NetCourier

This document designs the NetCourier database for the following architecture:

```txt
Gateway/Auth/Load Balancer + Process Server S1/S2 + Central Database
```

The central database stores authentication data, rooms, chat histories, PM histories, file metadata, transfer states, logs, and metrics. Physical files are stored in the local file storage of the respective Process Server.

---

## 1. ERD

```mermaid
erDiagram
    USERS ||--o{ SESSIONS : has
    USERS ||--o{ USER_PRESENCE : has
    USERS ||--o{ ROOMS : creates
    USERS ||--o{ ROOM_MEMBERS : joins
    USERS ||--o{ ROOM_MESSAGES : sends
    USERS ||--o{ PRIVATE_MESSAGES : sends
    USERS ||--o{ PRIVATE_MESSAGES : receives
    USERS ||--o{ FILES : uploads
    USERS ||--o{ FILE_TRANSFERS : performs
    USERS ||--o{ SERVER_LOGS : triggers

    BACKEND_SERVERS ||--o{ ROOM_MAPPING : hosts
    BACKEND_SERVERS ||--o{ ROOMS : processes
    BACKEND_SERVERS ||--o{ USER_PRESENCE : contains
    BACKEND_SERVERS ||--o{ SERVER_LOGS : emits

    ROOMS ||--|| ROOM_MAPPING : mapped_by
    ROOMS ||--o{ ROOM_MEMBERS : contains
    ROOMS ||--o{ ROOM_MESSAGES : has
    ROOMS ||--o{ FILES : stores
    ROOMS ||--o{ FILE_TRANSFERS : has

    FILES ||--o{ FILE_TRANSFERS : transferred_as
    FILE_TRANSFERS ||--o{ TRANSFER_CHUNKS : consists_of
    FILE_TRANSFERS ||--o{ PERFORMANCE_METRICS : measured_by

    USERS {
        int user_id PK
        string username UK
        string password_hash
        string display_name
        string status
        datetime created_at
        datetime last_login_at
    }

    SESSIONS {
        int session_id PK
        int user_id FK
        string token_hash UK
        boolean is_active
        string client_ip
        datetime connected_at
        datetime last_seen_at
        datetime disconnected_at
    }

    BACKEND_SERVERS {
        string server_id PK
        string host
        int port
        string status
        int active_rooms
        int active_clients
        int active_transfers
        datetime last_heartbeat_at
    }

    USER_PRESENCE {
        int presence_id PK
        int user_id FK
        string username
        string status
        string server_id FK
        string active_room
        datetime last_seen_at
    }

    ROOMS {
        int room_id PK
        string room_name UK
        int created_by FK
        string server_id FK
        string description
        string visibility
        datetime created_at
        boolean is_active
    }

    ROOM_MAPPING {
        int mapping_id PK
        int room_id FK
        string room_name UK
        string server_id FK
        datetime assigned_at
        boolean is_active
    }

    ROOM_MEMBERS {
        int member_id PK
        int room_id FK
        int user_id FK
        string username
        string role
        datetime joined_at
        datetime left_at
        boolean is_active
    }

    ROOM_MESSAGES {
        int message_id PK
        int room_id FK
        string server_id FK
        int sender_id FK
        string sender_username
        string message_type
        text content
        datetime created_at
        boolean is_deleted
    }

    PRIVATE_MESSAGES {
        int private_message_id PK
        int sender_id FK
        string sender_username
        int recipient_id FK
        string recipient_username
        text content
        string status
        datetime created_at
        datetime delivered_at
        datetime read_at
    }

    FILES {
        int file_id PK
        int room_id FK
        string server_id FK
        int uploader_id FK
        string original_filename
        string stored_filename
        string stored_path
        int size_bytes
        string checksum_sha256
        int chunk_size
        int total_chunks
        string status
        datetime uploaded_at
    }

    FILE_TRANSFERS {
        int transfer_id PK
        int file_id FK
        int room_id FK
        string server_id FK
        int user_id FK
        string direction
        string status
        int total_chunks
        int completed_chunks
        int bytes_transferred
        string resume_token
        datetime started_at
        datetime ended_at
        datetime last_activity_at
    }

    TRANSFER_CHUNKS {
        int chunk_id PK
        int transfer_id FK
        int chunk_index
        int size_bytes
        string status
        datetime processed_at
    }

    SERVER_LOGS {
        int log_id PK
        string server_id FK
        int user_id FK
        int room_id FK
        string event_type
        text message
        string ip_address
        datetime created_at
    }

    PERFORMANCE_METRICS {
        int metric_id PK
        int transfer_id FK
        int user_id FK
        int room_id FK
        string server_id FK
        string metric_type
        float value
        string unit
        datetime measured_at
    }
```

---

## 2. Table Definitions

### 2.1 users

Stores user account information.

| Column | Type | Constraint | Description |
|---|---|---|---|
| user_id | INTEGER | PK, Auto-increment | Unique identifier for the user |
| username | VARCHAR(50) | UNIQUE, NOT NULL | Username used for logging in |
| password_hash | TEXT | NOT NULL | Hashed password |
| display_name | VARCHAR(100) | NOT NULL | User's display profile name |
| status | VARCHAR(20) | NOT NULL | Status of the user account (active/banned) |
| created_at | DATETIME | NOT NULL | Date and time of registration |
| last_login_at | DATETIME | NULL | Timestamp of the last successful login |

Rules:
- Username must be unique.
- Passwords must not be stored in plain text.

---

### 2.2 sessions

Stores login sessions on the Gateway.

| Column | Type | Constraint | Description |
|---|---|---|---|
| session_id | INTEGER | PK, Auto-increment | Unique session ID |
| user_id | INTEGER | FK users.user_id | Associated user ID |
| token_hash | TEXT | UNIQUE, NOT NULL | SHA-256 hash of the session token |
| is_active | BOOLEAN | NOT NULL | Session status flag (active/inactive) |
| client_ip | VARCHAR(50) | NULL | Client IP address |
| connected_at | DATETIME | NOT NULL | Session connection / login timestamp |
| last_seen_at | DATETIME | NOT NULL | Last activity timestamp |
| disconnected_at | DATETIME | NULL | Session disconnection / logout timestamp |

Rules:
- The actual plain token must not be stored in the database; save only its hash.
- Inactive sessions must not be accepted for authentication.

---

### 2.3 backend_servers

Stores the list of active/inactive Process Servers.

| Column | Type | Constraint | Description |
|---|---|---|---|
| server_id | VARCHAR(20) | PK | Server ID (e.g., S1/S2) |
| host | VARCHAR(100) | NOT NULL | Host name or IP address |
| port | INTEGER | NOT NULL | Client-facing TCP port |
| status | VARCHAR(20) | NOT NULL | Server status (alive/down) |
| active_rooms | INTEGER | NOT NULL | Number of active chat rooms assigned |
| active_clients | INTEGER | NOT NULL | Number of active connected clients |
| active_transfers | INTEGER | NOT NULL | Number of active concurrent transfers |
| last_heartbeat_at | DATETIME | NULL | Timestamp of the last received heartbeat |

---

### 2.4 user_presence

Stores global user presence status.

| Column | Type | Constraint | Description |
|---|---|---|---|
| presence_id | INTEGER | PK, Auto-increment | Unique presence ID |
| user_id | INTEGER | FK users.user_id, UNIQUE | Associated user ID |
| username | VARCHAR(50) | NOT NULL | Denormalized username copy |
| status | VARCHAR(20) | NOT NULL | Presence status (waiting/in_room/offline) |
| server_id | VARCHAR(20) | FK backend_servers.server_id, NULL | Active Server ID (if user is in a room) |
| active_room | VARCHAR(100) | NULL | Name of the active room the user is in |
| last_seen_at | DATETIME | NOT NULL | Last seen timestamp |

---

### 2.5 rooms

Stores chat room details.

| Column | Type | Constraint | Description |
|---|---|---|---|
| room_id | INTEGER | PK, Auto-increment | Unique room ID |
| room_name | VARCHAR(100) | UNIQUE, NOT NULL | Chat room name |
| created_by | INTEGER | FK users.user_id | Room creator ID |
| server_id | VARCHAR(20) | FK backend_servers.server_id | Process Server hosting the room |
| description | TEXT | NULL | Description of the room |
| visibility | VARCHAR(20) | NOT NULL | Room visibility (public/private) |
| created_at | DATETIME | NOT NULL | Room creation timestamp |
| is_active | BOOLEAN | NOT NULL | Room active status flag |

---

### 2.6 room_mapping

Maps rooms to their designated Process Servers for room affinity.

| Column | Type | Constraint | Description |
|---|---|---|---|
| mapping_id | INTEGER | PK, Auto-increment | Unique mapping ID |
| room_id | INTEGER | FK rooms.room_id, UNIQUE | Room ID |
| room_name | VARCHAR(100) | UNIQUE, NOT NULL | Chat room name |
| server_id | VARCHAR(20) | FK backend_servers.server_id | Process Server assigned |
| assigned_at | DATETIME | NOT NULL | Assignment timestamp |
| is_active | BOOLEAN | NOT NULL | Mapping active status flag |

Rules:
- A room must have exactly one active server mapping.

---

### 2.7 room_members

Stores room membership details.

| Column | Type | Constraint | Description |
|---|---|---|---|
| member_id | INTEGER | PK, Auto-increment | Unique member ID |
| room_id | INTEGER | FK rooms.room_id | Room ID |
| user_id | INTEGER | FK users.user_id | User ID |
| username | VARCHAR(50) | NOT NULL | Denormalized username copy |
| role | VARCHAR(20) | NOT NULL | Room role (admin/member) |
| joined_at | DATETIME | NOT NULL | Join timestamp |
| left_at | DATETIME | NULL | Leave timestamp |
| is_active | BOOLEAN | NOT NULL | Active membership status flag |

---

### 2.8 room_messages

Stores room chat message history.

| Column | Type | Constraint | Description |
|---|---|---|---|
| message_id | INTEGER | PK, Auto-increment | Unique message ID |
| room_id | INTEGER | FK rooms.room_id | Room ID |
| server_id | VARCHAR(20) | FK backend_servers.server_id | Process Server that routed the message |
| sender_id | INTEGER | FK users.user_id, NULL | Sender User ID |
| sender_username | VARCHAR(50) | NULL | Sender username copy |
| message_type | VARCHAR(20) | NOT NULL | Message type (text/system/file_event) |
| content | TEXT | NOT NULL | Message text or event payload |
| created_at | DATETIME | NOT NULL | Message timestamp |
| is_deleted | BOOLEAN | NOT NULL | Soft delete status flag |

Rules:
- `sender_id` can be NULL for system generated messages.
- Messages must not be permanently deleted; use soft delete instead.

---

### 2.9 private_messages

Stores global private messages (PM).

| Column | Type | Constraint | Description |
|---|---|---|---|
| private_message_id | INTEGER | PK, Auto-increment | Unique private message ID |
| sender_id | INTEGER | FK users.user_id | Sender User ID |
| sender_username | VARCHAR(50) | NOT NULL | Sender username |
| recipient_id | INTEGER | FK users.user_id | Recipient User ID |
| recipient_username | VARCHAR(50) | NOT NULL | Recipient username |
| content | TEXT | NOT NULL | Private message text |
| status | VARCHAR(20) | NOT NULL | Message status (sent/delivered/stored_offline/read/failed) |
| created_at | DATETIME | NOT NULL | Time the private message was sent |
| delivered_at | DATETIME | NULL | Time the private message was delivered |
| read_at | DATETIME | NULL | Time the private message was read |

Rules:
- PMs are coordinated and stored by the Gateway.
- PMs can be received by users whether they are in the lobby (waiting) or active inside a room.

---

### 2.10 files

Stores metadata of uploaded files.

| Column | Type | Constraint | Description |
|---|---|---|---|
| file_id | INTEGER | PK, Auto-increment | Unique file ID |
| room_id | INTEGER | FK rooms.room_id | Room ID |
| server_id | VARCHAR(20) | FK backend_servers.server_id | Server storing the physical file |
| uploader_id | INTEGER | FK users.user_id | Uploader user ID |
| original_filename | VARCHAR(255) | NOT NULL | Original filename |
| stored_filename | VARCHAR(255) | NOT NULL | Sanitized filename stored on disk |
| stored_path | TEXT | NOT NULL | File path on disk |
| size_bytes | INTEGER | NOT NULL | File size in bytes |
| checksum_sha256 | TEXT | NOT NULL | SHA-256 checksum hash |
| chunk_size | INTEGER | NOT NULL | Size of each file chunk |
| total_chunks | INTEGER | NOT NULL | Total number of chunks |
| status | VARCHAR(20) | NOT NULL | File status (uploading/available/corrupted/deleted) |
| uploaded_at | DATETIME | NOT NULL | Upload timestamp |

---

### 2.11 file_transfers

Stores state metrics for file uploads and downloads.

| Column | Type | Constraint | Description |
|---|---|---|---|
| transfer_id | INTEGER | PK, Auto-increment | Unique transfer session ID |
| file_id | INTEGER | FK files.file_id, NULL | Associated file ID |
| room_id | INTEGER | FK rooms.room_id | Room ID |
| server_id | VARCHAR(20) | FK backend_servers.server_id | Process Server handling the transfer |
| user_id | INTEGER | FK users.user_id | User ID performing the transfer |
| direction | VARCHAR(20) | NOT NULL | Transfer direction (upload/download) |
| status | VARCHAR(20) | NOT NULL | Transfer status (pending/in_progress/completed/interrupted/failed) |
| total_chunks | INTEGER | NOT NULL | Total number of chunks |
| completed_chunks | INTEGER | NOT NULL | Completed chunks count |
| bytes_transferred | INTEGER | NOT NULL | Bytes transferred |
| resume_token | TEXT | UNIQUE, NULL | Resume token for verifying sessions |
| started_at | DATETIME | NOT NULL | Started timestamp |
| ended_at | DATETIME | NULL | Ended timestamp |
| last_activity_at | DATETIME | NOT NULL | Last activity timestamp |

---

### 2.12 transfer_chunks

Stores the receipt/transmission status of individual file chunks.

| Column | Type | Constraint | Description |
|---|---|---|---|
| chunk_id | INTEGER | PK, Auto-increment | Unique chunk ID |
| transfer_id | INTEGER | FK file_transfers.transfer_id | Transfer ID |
| chunk_index | INTEGER | NOT NULL | Chunk index (0-based) |
| size_bytes | INTEGER | NOT NULL | Chunk size in bytes |
| status | VARCHAR(20) | NOT NULL | Chunk status (pending/received/sent/failed) |
| processed_at | DATETIME | NULL | Processed timestamp |

Constraints:
- UNIQUE(transfer_id, chunk_index)

---

### 2.13 server_logs

Stores audit logs.

| Column | Type | Constraint | Description |
|---|---|---|---|
| log_id | INTEGER | PK, Auto-increment | Unique log ID |
| server_id | VARCHAR(20) | FK backend_servers.server_id, NULL | Server |
| user_id | INTEGER | FK users.user_id, NULL | Associated user ID |
| room_id | INTEGER | FK rooms.room_id, NULL | Associated room ID |
| event_type | VARCHAR(50) | NOT NULL | Event type category |
| message | TEXT | NOT NULL | Log message description |
| ip_address | VARCHAR(50) | NULL | Client IP address |
| created_at | DATETIME | NOT NULL | Log generation timestamp |

---

### 2.14 performance_metrics

Stores performance evaluation metrics.

| Column | Type | Constraint | Description |
|---|---|---|---|
| metric_id | INTEGER | PK, Auto-increment | Unique metric ID |
| transfer_id | INTEGER | FK file_transfers.transfer_id, NULL | Associated transfer ID |
| user_id | INTEGER | FK users.user_id, NULL | Associated user ID |
| room_id | INTEGER | FK rooms.room_id, NULL | Associated room ID |
| server_id | VARCHAR(20) | FK backend_servers.server_id, NULL | Associated Process Server ID |
| metric_type | VARCHAR(50) | NOT NULL | Metric category (latency/throughput/error_rate) |
| value | REAL | NOT NULL | Measured metric value |
| unit | VARCHAR(20) | NOT NULL | Measurement unit (ms/KBps/MBps/percent) |
| measured_at | DATETIME | NOT NULL | Measurement timestamp |

---

## 3. SQLite-Compatible DDL

```sql
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at DATETIME NOT NULL,
    last_login_at DATETIME
);

CREATE TABLE sessions (
    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    client_ip VARCHAR(50),
    connected_at DATETIME NOT NULL,
    last_seen_at DATETIME NOT NULL,
    disconnected_at DATETIME,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE backend_servers (
    server_id VARCHAR(20) PRIMARY KEY,
    host VARCHAR(100) NOT NULL,
    port INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'alive',
    active_rooms INTEGER NOT NULL DEFAULT 0,
    active_clients INTEGER NOT NULL DEFAULT 0,
    active_transfers INTEGER NOT NULL DEFAULT 0,
    last_heartbeat_at DATETIME
);

CREATE TABLE user_presence (
    presence_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    username VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'offline',
    server_id VARCHAR(20),
    active_room VARCHAR(100),
    last_seen_at DATETIME NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (server_id) REFERENCES backend_servers(server_id)
);

CREATE TABLE rooms (
    room_id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_name VARCHAR(100) NOT NULL UNIQUE,
    created_by INTEGER NOT NULL,
    server_id VARCHAR(20) NOT NULL,
    description TEXT,
    visibility VARCHAR(20) NOT NULL DEFAULT 'public',
    created_at DATETIME NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    FOREIGN KEY (created_by) REFERENCES users(user_id),
    FOREIGN KEY (server_id) REFERENCES backend_servers(server_id)
);

CREATE TABLE room_mapping (
    mapping_id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id INTEGER NOT NULL UNIQUE,
    room_name VARCHAR(100) NOT NULL UNIQUE,
    server_id VARCHAR(20) NOT NULL,
    assigned_at DATETIME NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    FOREIGN KEY (room_id) REFERENCES rooms(room_id),
    FOREIGN KEY (server_id) REFERENCES backend_servers(server_id)
);

CREATE TABLE room_members (
    member_id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    username VARCHAR(50) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'member',
    joined_at DATETIME NOT NULL,
    left_at DATETIME,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    FOREIGN KEY (room_id) REFERENCES rooms(room_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE room_messages (
    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id INTEGER NOT NULL,
    server_id VARCHAR(20) NOT NULL,
    sender_id INTEGER,
    sender_username VARCHAR(50),
    message_type VARCHAR(20) NOT NULL DEFAULT 'text',
    content TEXT NOT NULL,
    created_at DATETIME NOT NULL,
    is_deleted BOOLEAN NOT NULL DEFAULT 0,
    FOREIGN KEY (room_id) REFERENCES rooms(room_id),
    FOREIGN KEY (server_id) REFERENCES backend_servers(server_id),
    FOREIGN KEY (sender_id) REFERENCES users(user_id)
);

CREATE TABLE private_messages (
    private_message_id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id INTEGER NOT NULL,
    sender_username VARCHAR(50) NOT NULL,
    recipient_id INTEGER NOT NULL,
    recipient_username VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'sent',
    created_at DATETIME NOT NULL,
    delivered_at DATETIME,
    read_at DATETIME,
    FOREIGN KEY (sender_id) REFERENCES users(user_id),
    FOREIGN KEY (recipient_id) REFERENCES users(user_id)
);

CREATE TABLE files (
    file_id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id INTEGER NOT NULL,
    server_id VARCHAR(20) NOT NULL,
    uploader_id INTEGER NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    stored_filename VARCHAR(255) NOT NULL,
    stored_path TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    checksum_sha256 TEXT NOT NULL,
    chunk_size INTEGER NOT NULL,
    total_chunks INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'uploading',
    uploaded_at DATETIME NOT NULL,
    FOREIGN KEY (room_id) REFERENCES rooms(room_id),
    FOREIGN KEY (server_id) REFERENCES backend_servers(server_id),
    FOREIGN KEY (uploader_id) REFERENCES users(user_id)
);

CREATE TABLE file_transfers (
    transfer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER,
    room_id INTEGER NOT NULL,
    server_id VARCHAR(20) NOT NULL,
    user_id INTEGER NOT NULL,
    direction VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    total_chunks INTEGER NOT NULL,
    completed_chunks INTEGER NOT NULL DEFAULT 0,
    bytes_transferred INTEGER NOT NULL DEFAULT 0,
    resume_token TEXT UNIQUE,
    started_at DATETIME NOT NULL,
    ended_at DATETIME,
    last_activity_at DATETIME NOT NULL,
    FOREIGN KEY (file_id) REFERENCES files(file_id),
    FOREIGN KEY (room_id) REFERENCES rooms(room_id),
    FOREIGN KEY (server_id) REFERENCES backend_servers(server_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE transfer_chunks (
    chunk_id INTEGER PRIMARY KEY AUTOINCREMENT,
    transfer_id INTEGER NOT NULL,
    chunk_index INTEGER NOT NULL,
    size_bytes INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    processed_at DATETIME,
    FOREIGN KEY (transfer_id) REFERENCES file_transfers(transfer_id),
    UNIQUE (transfer_id, chunk_index)
);

CREATE TABLE server_logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    server_id VARCHAR(20),
    user_id INTEGER,
    room_id INTEGER,
    event_type VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    ip_address VARCHAR(50),
    created_at DATETIME NOT NULL,
    FOREIGN KEY (server_id) REFERENCES backend_servers(server_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (room_id) REFERENCES rooms(room_id)
);

CREATE TABLE performance_metrics (
    metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
    transfer_id INTEGER,
    user_id INTEGER,
    room_id INTEGER,
    server_id VARCHAR(20),
    metric_type VARCHAR(50) NOT NULL,
    value REAL NOT NULL,
    unit VARCHAR(20) NOT NULL,
    measured_at DATETIME NOT NULL,
    FOREIGN KEY (transfer_id) REFERENCES file_transfers(transfer_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (room_id) REFERENCES rooms(room_id),
    FOREIGN KEY (server_id) REFERENCES backend_servers(server_id)
);
```

---

## 4. Recommended Indexes

```sql
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_user_presence_status ON user_presence(status);
CREATE INDEX idx_rooms_server_id ON rooms(server_id);
CREATE INDEX idx_room_members_room_id ON room_members(room_id);
CREATE INDEX idx_room_messages_room_id_created_at ON room_messages(room_id, created_at);
CREATE INDEX idx_private_messages_pair ON private_messages(sender_id, recipient_id, created_at);
CREATE INDEX idx_files_room_id ON files(room_id);
CREATE INDEX idx_file_transfers_user_id ON file_transfers(user_id);
CREATE INDEX idx_transfer_chunks_transfer_id ON transfer_chunks(transfer_id);
CREATE INDEX idx_server_logs_created_at ON server_logs(created_at);
CREATE INDEX idx_metrics_type ON performance_metrics(metric_type);
```

---

## 5. Data Ownership Rules

| Data | Writer | Reader |
|---|---|---|
| users | Gateway | Gateway |
| sessions | Gateway | Gateway, Process Server via validation |
| backend_servers | Gateway / Process Server heartbeat | Gateway |
| room_mapping | Gateway | Gateway |
| user_presence | Gateway + Process Server status update | Gateway |
| private_messages | Gateway | Gateway |
| rooms | Gateway | Gateway, Process Server |
| room_members | Process Server | Process Server |
| room_messages | Process Server | Process Server |
| files | Process Server | Process Server |
| file_transfers | Process Server | Process Server |
| server_logs | Gateway and Process Server | Operator / reports |
| performance_metrics | Gateway / Process Server / test script | Reports |

---

## 6. Important Database Rules

1. Passwords must be hashed.
2. Session tokens should be stored as hashes.
3. PM history is global and stored by the Gateway.
4. Room history is stored by the Process Server.
5. A room must have exactly one active server mapping.
6. File physical content is not stored in the database.
7. File metadata must include a checksum.
8. Transfer states must support resume.
9. Use soft deletes for messages and files if possible.
10. Log important events for demo and report audits.
