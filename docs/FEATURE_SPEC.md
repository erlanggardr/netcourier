# Feature Specification - NetCourier

This document describes the detailed behavior, specifications, and workflows of each NetCourier feature.

---

## 1. Feature: User Registration

### Actor
Guest user.

### Description
A guest user creates a new account credentials through the Gateway Server.

### Normal Flow
1. The guest opens the NetCourier Web UI in a browser.
2. The guest fills out the registration form: username, password, and display name.
3. The guest clicks the **Register** button.
4. The client sends a `REGISTER` packet to the Gateway.
5. The Gateway validates the input format.
6. The Gateway hashes the password using PBKDF2 with salt.
7. The Gateway stores the new user record in the database.
8. The Gateway returns a `REGISTER_OK` packet to the client.

### Error Flow
- Username is already taken -> Returns `ERROR USERNAME_TAKEN`.
- Password is too short -> Returns `ERROR INVALID_PASSWORD`.
- Username contains forbidden/dangerous characters -> Returns `ERROR INVALID_USERNAME`.

### Acceptance Criteria
- A new user record is successfully inserted into the database.
- Passwords must not be stored in plain text (must use PBKDF2).
- Duplicate usernames must be rejected with appropriate error packets.

---

## 2. Feature: User Login

### Actor
Registered user.

### Description
A user logs in through the Gateway to obtain a session token.

### Normal Flow
1. The user fills out the login credentials in the Web UI and clicks the **Login** button.
2. The client sends a `LOGIN` packet to the Gateway.
3. The Gateway verifies the username and validates the password against the stored PBKDF2 hash.
4. The Gateway checks for duplicate active login sessions.
5. The Gateway generates a unique session token.
6. The Gateway persists the session record in the database.
7. The Gateway updates the user's presence state to online/waiting.
8. The Gateway returns a `LOGIN_OK` packet with session details.

### Error Flow
- Incorrect username or password -> Returns `ERROR INVALID_CREDENTIALS`.
- User is already logged in elsewhere -> Returns `ERROR DUPLICATE_LOGIN`.
- Database transaction fails -> Returns `ERROR INTERNAL_ERROR`.

### Output Payload
- `token`
- `user_id`
- `username`
- `display_name`

---

## 3. Feature: Waiting Room / Global Lobby

### Actor
Authenticated user.

### Description
Upon logging in, the user enters the global lobby/waiting room coordinated by the Gateway. The lobby is not a typical chat room but a global dashboard facilitating PM routing, global online user directory, room directories, room creation, and room joining.

### Available UI Actions
- View online users in the **Online Users** panel.
- Send Private Messages (PMs) through the **Private Message** panel.
- Open private message history by clicking the **History** button.
- View active rooms in the **Rooms** list panel.
- Create new rooms using the **Create Room** form.
- Join an existing room by clicking the **Join** button.
- Log out using the **Logout** button.
- Open help instructions from the **Help** menu.

### Acceptance Criteria
- Users can send private messages without joining a chat room.
- Users can receive private messages before they join any room.
- Users can view a real-time list of active chat rooms from the Gateway.

---

## 3.1 Feature: Web UI & HTTP-to-TCP API Bridge

### Actor
Authenticated user and Guest.

### Description
NetCourier utilizes a Single Page Application (SPA) Web UI built on vanilla HTML/CSS/JS connected to the backend via an HTTP-to-TCP API Bridge (`src/netcourier/web/api/main.py`). The entire application interface is managed in the browser. The Web UI provides login/registration forms, a lobby/waiting room dashboard, online user listings, private messaging panels, room listings, room chat panels, file listings, upload/download controls, transfer progress indicators, and status bars.

### Normal Flow
1. The user runs the client launcher (`PYTHONPATH=src python -m netcourier.client.main`) which starts the local HTTP Web Server.
2. The user navigates to `http://localhost:8080` in their web browser.
3. The user logs in or registers via the Web UI forms.
4. Upon authentication, the browser stores the session token and redirects the user to the Lobby/Waiting Room view.
5. The user can send private messages, view online users, and create or join rooms.
6. Upon joining a room, the Web UI displays the Room Chat panel while the API bridge maintains the Gateway TCP socket connection in the background.
7. Asynchronous events received by the background TCP sockets are queued in server memory and polled by the browser client via long-polling `/api/events` requests.

### Acceptance Criteria
- All user-facing features are fully accessible through the browser Web UI.
- The Web UI remains highly responsive and non-blocking during chat, PM routing, uploads, or downloads.
- All TCP socket communications are protected by thread-safe synchronization locks (`threading.Lock`), and events are serialized through the `WebSession.events` queue.
- File uploads and downloads are fully supported directly from the web interface.
- Upload and download progress indicators update in real-time on a web-based progress bar.

---

## 4. Feature: Global Private Messaging (PM)

### Actor
Authenticated user.

### Description
Users can send private messages (PM) to other users through the Gateway, regardless of whether the sender or recipient is in the lobby or inside a Process Server chat room.

### Normal Flow
1. The sender selects a target user in the Online Users panel or inputs the target username in the Private Message panel.
2. The sender types the message and clicks the **Send PM** button.
3. The client sends a `PRIVATE_MESSAGE_SEND` packet to the Gateway.
4. The Gateway validates the sender's token.
5. The Gateway verifies the recipient exists.
6. The Gateway saves the PM to the database.
7. If the recipient is currently online, the Gateway forwards `PRIVATE_MESSAGE_RECEIVED` to the recipient's Gateway socket.
8. The Gateway returns a `delivered` status notification to the sender.
9. If the recipient is offline, the Gateway stores the message with a status of `stored_offline`.

### Important Design Rule
Clients inside a chat room maintain their active TCP connections to the Gateway. Thus, private messages can be sent between lobby users and active room users.

### Error Flow
- Recipient user not found -> Returns `ERROR USER_NOT_FOUND`.
- Empty message payload -> Returns `ERROR EMPTY_MESSAGE`.
- Sender rate limit exceeded -> Returns `ERROR RATE_LIMIT_EXCEEDED`.

### Acceptance Criteria
- Private messages can be sent between lobby users and active room users successfully.
- Private messages can be sent between users connected to different Process Servers successfully.
- PM history records are successfully saved and loaded.
- Offline PMs are retrieved immediately after logging in.

---

## 5. Feature: Online User List

### Actor
Authenticated user.

### Description
The Gateway maintains and broadcasts a global list of online users.

### Output format
```txt
username | status | active_room | server_id
erlangga | waiting | -           | -
budi     | in_room | FP-Jaringan | S1
nadia    | in_room | Kelompok-A  | S2
```

### Status Values
- `waiting` (online in lobby)
- `in_room` (active in a chat room)
- `offline` (not logged in)

### Acceptance Criteria
- Newly logged-in users appear online.
- Logged-out users are immediately removed or marked offline.
- Users joining a room dynamically transition to the `in_room` status.

---

## 6. Feature: Create Room

### Actor
Authenticated user.

### Description
A user creates a new chat room. The Gateway load balances the room to the least loaded Process Server.

### Normal Flow
1. The user inputs a room name `FP-Jaringan` and description, then clicks the **Create Room** button.
2. The client sends a `CREATE_ROOM` packet to the Gateway.
3. The Gateway validates the room name format.
4. The Gateway selects the alive Process Server with the lowest load score.
5. The Gateway stores the room entry and the `room_mapping` registry.
6. The Gateway returns a `ROOM_ASSIGNED` packet containing host, port, and server details.
7. The client automatically connects to the designated Process Server.
8. The Process Server validates the client's token against the Gateway.
9. The Process Server initializes the room context, and the client joins.

### Load Balancing Rule
Priority of server selection:
1. Server status must be `alive`.
2. Lowest count of `active_rooms`.
3. Lowest count of `active_clients`.
4. Fallback to round-robin on ties.

### Acceptance Criteria
- The new room is recorded in the database.
- The room-to-server mapping is stored.
- The room creator becomes the room administrator (admin).
- The client is successfully routed to the assigned Process Server.

---

## 7. Feature: Join Room

### Actor
Authenticated user.

### Description
A user joins an existing chat room.

### Normal Flow
1. The user selects a room from the Rooms list and clicks the **Join** button.
2. The client sends a `JOIN_ROOM` packet to the Gateway.
3. The Gateway retrieves the server location from the `room_mapping`.
4. The Gateway returns a `ROOM_LOCATION` packet.
5. The client establishes a TCP socket connection to the designated Process Server.
6. The client sends an `AUTH_BACKEND` packet to the Process Server.
7. The Process Server validates the session token against the Gateway.
8. The Process Server registers the user as active in the room context.
9. The Process Server loads and transmits the last 50 room chat messages.
10. The Process Server broadcasts a user join event to all other room members.

### Acceptance Criteria
- All users joining the same room are routed to the same Process Server.
- Users receive historical room messages upon entry.
- Existing room members receive real-time join notifications.

---

## 8. Feature: Leave Room

### Actor
Room member.

### Description
A user exits a chat room but remains logged in to the global Gateway.

### Normal Flow
1. The user clicks the **Leave Room** button.
2. The client sends a `LEAVE_ROOM` packet to the Process Server.
3. The Process Server updates the user's membership to inactive.
4. The Process Server broadcasts a user departure notification.
5. The client terminates the Process Server socket connection and returns to lobby mode.
6. The Gateway updates the user's presence state back to `waiting`.

### Acceptance Criteria
- Users stop receiving room broadcasts immediately after leaving.
- Users can still send and receive PMs through the Gateway.

---

## 9. Feature: Broadcast Room Chat

### Actor
Room member.

### Description
A user sends a message to all active participants inside the chat room.

### Normal Flow
1. The user types a message and clicks the **Send** button.
2. The client sends a `ROOM_CHAT_SEND` packet to the Process Server.
3. The Process Server validates that the sender is an active member of the room.
4. The Process Server persists the message in the database.
5. The Process Server broadcasts a `ROOM_CHAT_BROADCAST` packet to all clients inside the room.
6. The sender receives an acknowledgment (ACK).

### Error Flow
- User has not joined the room -> Returns `ERROR NOT_IN_ROOM`.
- Empty message payload -> Returns `ERROR EMPTY_MESSAGE`.
- Sender rate limit exceeded -> Returns `ERROR RATE_LIMIT_EXCEEDED`.

### Acceptance Criteria
- Messages are only received by users inside the same room.
- Messages are saved in room history database.
- Messages contain accurate creation timestamps.

---

## 10. Feature: Room Chat History

### Actor
Room member.

### Description
Users can retrieve historical chat messages from the room.

### Normal Flow
1. The user clicks the **Refresh History** button, or the history loads automatically upon joining.
2. The client sends a `ROOM_HISTORY_REQUEST` packet.
3. The Process Server queries the database for the room.
4. The Process Server returns the last 50 chat messages.

### Acceptance Criteria
- New members automatically receive history logs when joining.
- Members can manually request history updates.
- System events and file upload announcements are included in history logs.

---

## 11. Feature: File List

### Actor
Room member.

### Description
Users can view files uploaded in the active chat room.

### Normal Flow
1. The user opens the **Files** panel or clicks the **Refresh Files** button.
2. The client sends a `FILE_LIST_REQUEST` packet.
3. The Process Server queries file metadata from the database.
4. The client receives the file listing.

### Output format
```txt
ID | Filename    | Size   | Uploader | Status    | Uploaded At
12 | laporan.pdf | 2.4 MB | erlangga | available | 2026-06-09 20:00
```

---

## 12. Feature: Upload File

### Actor
Room member.

### Description
Users upload files to the room through the Process Server.

### Normal Flow
1. The user clicks **Upload File** and selects a file (e.g., `laporan.pdf`) using the file picker.
2. The client calculates the file size, total chunk count, and SHA-256 checksum.
3. The client sends an `UPLOAD_INIT` packet.
4. The Process Server initializes a transfer session.
5. The Process Server responds with an `UPLOAD_READY` packet containing the transfer ID.
6. The client uploads chunks sequentially (or concurrently up to 4 parallel workers).
7. The Process Server acknowledges chunk completion with a `CHUNK_ACK`.
8. The client displays the transfer progress bar.
9. The client sends an `UPLOAD_FINISH` packet.
10. The Process Server computes the SHA-256 checksum of the completed file on disk.
11. If the computed checksum matches, the file status is marked as `available`.
12. The Process Server broadcasts a system event announcing the new file.

### Error Flow
- File size exceeds limit -> Returns `ERROR FILE_TOO_LARGE`.
- Invalid file path -> Client-side error.
- Checksum verification failed -> Returns `ERROR CHECKSUM_FAILED`.
- Transfer session timed out -> Returns `ERROR TRANSFER_TIMEOUT`.

### Acceptance Criteria
- The uploaded file is stored in the Process Server's storage directory.
- File metadata is persisted in the database.
- Checksum is verified and correct.
- Other room members receive real-time notifications about the new file.

---

## 13. Feature: Download File

### Actor
Room member.

### Description
Users download uploaded files from the room.

### Normal Flow
1. The user selects a file in the file listing and clicks the **Download** button.
2. The client sends a `DOWNLOAD_REQUEST` packet.
3. The Process Server verifies the file is available.
4. The Process Server responds with a `DOWNLOAD_READY` packet.
5. The Process Server transmits file chunks sequentially.
6. The client writes bytes to the local target file.
7. The client updates the download progress bar.
8. Upon completion, the client computes the SHA-256 checksum.
9. The client validates the checksum against the original metadata hash.

### Acceptance Criteria
- The downloaded file matches the server copy bit-for-bit.
- Checksum verifies successfully.
- Progress bar functions correctly.

---

## 14. Feature: Resume Transfer

### Actor
Room member.

### Description
File uploads and downloads can be resumed after network disconnection.

### Normal Flow (Download/Upload Resume)
1. Client is downloading/uploading a file.
2. Network connection drops at chunk 40.
3. Client reconnects and authenticates with the Process Server.
4. Client sends a `RESUME_TRANSFER` request with the `transfer_id` and the last successfully written chunk index.
5. The server resumes sending/receiving from chunk 41.
6. The transfer completes and verifies successfully.

### Acceptance Criteria
- The file transfer resumes without re-transmitting already completed chunks.
- Resumed transaction states are logged in the database.
- Checksum remains valid after resume operations.

---

## 15. Feature: Backend Heartbeat

### Actor
Process Server.

### Description
Process Servers transmit periodic heartbeat packets to the Gateway.

### Payload Example
```json
{
  "server_id": "S1",
  "active_rooms": 3,
  "active_clients": 12,
  "active_transfers": 2
}
```

### Acceptance Criteria
- The Gateway monitors server status (online/offline).
- The Gateway excludes offline servers from room load balancing.

---

## 16. Feature: Load Test

### Actor
Server operator.

### Description
Test scripts simulate user loads.

### Scenario
- 30 concurrent clients logging in.
- 10 rooms created.
- 100 room chat messages sent.
- 50 PMs routed.
- 5 files (1MB each) uploaded and downloaded.
- 5 malformed/corrupted packets transmitted to test robustness.

### Output Reports
- Total success count
- Total failed count
- Average latency
- Max latency
- Network throughput
- Error rate percentages

---

## 17. Feature: Room Message Reactions (Emoji Reactions)

### Actor
Room member.

### Description
Users can add or remove emoji reactions (such as 👍, ❤️, 😂, etc.) on chat messages inside the room. Reactions are tracked per user per message and broadcast to all room members in real-time.

### Normal Flow
1. The user hovers over a chat message in the Web UI.
2. The user selects an emoji from the reaction menu overlay.
3. The client sends a `ROOM_MESSAGE_REACTION` packet with `message_id`, `emoji`, and `action = 'add'` or `'remove'`.
4. The Process Server processes the request, updates the `message_reactions` database, and broadcasts `ROOM_REACTION_BROADCAST` to all room members.
5. Receiving client UIs dynamically update the emoji counts and reaction tooltips.

### Acceptance Criteria
- Emoji reactions are correctly persisted or removed from the database.
- Reactions update dynamically without reloading the chat page.

---

## 18. Feature: Admin Kick User

### Actor
Room owner (admin).

### Description
The owner/creator of a chat room has administrative rights to kick other users from the room.

### Normal Flow
1. The admin clicks the **Kick** button next to a user's name (or in the member list) in the Web UI.
2. The client sends a `ROOM_KICK_USER` packet with the target `username`.
3. The Process Server verifies the sender is the room owner. If valid, the target is kicked from the room context (their presence resets to the lobby/waiting room), and the Gateway is notified.
4. The Process Server broadcasts a `SYSTEM_EVENT` stating that the user was kicked by the owner.
5. The target client receives the kick event and is automatically redirected back to the Lobby/Dashboard.

### Acceptance Criteria
- Only the original room creator/owner can kick members.
- Other members do not see the kick button, and unauthorized requests are rejected with a `PERMISSION_DENIED` error.
- Kicked members are evicted instantly and the active member list is updated.

---

## 19. Feature: Admin Delete File

### Actor
Room owner (admin).

### Description
The room owner can delete files uploaded within their room. Deletion is logical, secure, and clean.

### Normal Flow
1. The admin clicks the **Delete File** button on a file card in the room's Web UI chat area.
2. The client sends a `ROOM_DELETE_FILE` packet with the `file_id`.
3. The Process Server verifies owner permissions. If valid, the file status is updated to `'deleted'` in the `files` table and the message card is marked `is_deleted = 1` in the `room_messages` table.
4. The Process Server broadcasts a `ROOM_DELETE_FILE_BROADCAST` containing the `message_id` and `file_id` to room members and emits a system notification message.
5. All client browsers in the room detect the broadcast and remove the file card from their DOM instantly.
6. Download requests for deleted files are rejected with a `FILE_NOT_FOUND` error.

### Acceptance Criteria
- Only the owner can delete files.
- The file message card disappears instantly from all online clients in the room.
- Deleted files can no longer be downloaded.
