# UI/UX Specification - NetCourier Web Client

NetCourier utilizes a modern **Web Client GUI** (HTML/CSS/JS) as its primary user interface. The client **must not be CLI/TUI-based**. Command-line interfaces (CLI) are reserved strictly for launching the Gateway, Process Servers, and running load testing tools.

The UI must be clean, stable, easy to demonstrate, and explicitly visualize core network concepts: active Gateway connections, Process Server connectivity, global PM routing, room chat, chunked file transfer progress, and live latency status.

---

## 1. UI Modes

The client interface is split into two primary areas:

1. **Gateway Lobby / Waiting Area**
   - User is logged in but has not entered a specific chat room.
   - Global PM routing is active.
   - Global online users directory is active.
   - Active rooms listing directory is active.
   - Creating and joining rooms are available.

2. **Room View Area**
   - User is actively inside a specific chat room.
   - Room chat broadcasting is active.
   - Room participant listing is active.
   - Room files listing is active.
   - Chunked file uploads and downloads are active.
   - Global PM routing remains active via the background Gateway connection.

The layout features a Single Page Application (SPA) dashboard design:

```txt
+--------------------------------------------------------------+
| NetCourier                                      user: erlangga |
+----------------------+---------------------------------------+
| Sidebar / Navigation | Main Content                          |
| - Gateway            | - Waiting Room / Room Chat            |
| - Rooms              | - Private Message                     |
| - Files              | - Transfer Progress                   |
+----------------------+---------------------------------------+
| Status: Gateway connected | Room: FP-Jaringan @ S1 | 12 ms   |
+--------------------------------------------------------------+
```

---

## 2. Window Structure

### 2.1 Authentication Window

Components:
- App title: NetCourier.
- Gateway host input.
- Gateway port input.
- Login form:
  - Username input.
  - Password input.
  - Login trigger button.
- Registration form:
  - Username input.
  - Display name input.
  - Password input.
  - Register trigger button.
- Status labels to show errors or success notifications.

Rules:
- Password fields must use character masking.
- Login/Register buttons are disabled while network requests are in progress.
- Authentication errors are displayed in status labels or modal alert dialogues.
- Upon successful authentication, the main client dashboard is loaded.

---

## 3. Main Window Layout

The Main Window loads immediately after a successful login.

Layout:

```txt
+--------------------------------------------------------------------------------+
| NetCourier - erlangga                                           [Logout] [Help] |
+-------------------------+------------------------------------------------------+
| Global Panel            | Room Panel                                           |
|                         |                                                      |
| Online Users            | Room Header: FP-Jaringan @ S1                        |
| [search user]           | [Leave Room] [Refresh History] [Ping Room]           |
| - budi      in_room     |                                                      |
| - nadia     waiting     | Chat History                                         |
|                         | ---------------------------------------------------- |
| Private Message         | [20:20] budi: Hello                                  |
| To: [budi         v]    | [20:21] erlangga: I am uploading the report          |
| Message: [          ]   |                                                      |
| [Send PM] [History]     | Message: [                              ] [Send]     |
|                         |                                                      |
| Rooms                   | Files                                                |
| [Create Room input]     | ID | Filename    | Size   | Uploader | Status        |
| [Create]                | 1  | laporan.pdf | 2.4 MB | erlangga | available     |
| Room table              | [Upload] [Download Selected] [Resume]               |
+-------------------------+------------------------------------------------------+
| Transfer Progress: laporan.pdf [########------] 67% | 780 KB/s | ETA 2s        |
| Status: Gateway connected | Room Server S1 connected | Last error: -                  |
+--------------------------------------------------------------------------------+
```

---

## 4. Authentication Flow UX

### 4.1 Registration

User workflow:
1. The user opens the local client app launcher.
2. The user inputs the Gateway Host IP and Port.
3. The user inputs their desired username, display name, and password.
4. The user clicks the **Register** button.
5. The client transmits a `REGISTER` packet to the Gateway.
6. On success, the UI displays: `Register success. Please login.`

Error Handling:
- Username empty -> `Username is required.`
- Username already taken -> `Username already taken.`
- Password too short -> `Password is too short.`
- Gateway connection failed -> `Cannot connect to Gateway.`

### 4.2 Login

User workflow:
1. The user inputs their username and password.
2. The user clicks the **Login** button.
3. The client transmits a `LOGIN` packet to the Gateway.
4. On success, the Auth view is replaced by the Main Dashboard.
5. The status bar displays `Gateway connected`.

Error Handling:
- Incorrect credentials -> `Invalid username or password.`
- Duplicate login -> `User already logged in.`
- Connection timeout -> `Login timeout. Please try again.`

---

## 5. Lobby/Waiting Area UX

The lobby is the global landing area after logging in.

Components:
- Online Users table.
- Private Message routing panel.
- Active Rooms directory list.
- Create Room input form.
- Join Room trigger buttons.
- PM History panel.

### 5.1 Online Users Table

Columns:
- Username.
- Display name.
- Status (`waiting`, `in_room`, `offline`).
- Active room name.
- Process Server ID.

Actions:
- Double-clicking a user entry automatically selects them as the target for a Private Message.
- The refresh action issues a `ONLINE_USERS_REQUEST` update.

### 5.2 Private Message Panel

Components:
- Recipient dropdown/input.
- Message text entry area.
- Send PM trigger button.
- PM History loading button.
- Conversation thread display.

Message display format:
```txt
[PM from budi | 20:15:01] Bro, I downloaded the file.
[PM to budi | delivered] Awesome, thanks.
[PM to nadia | stored_offline] User offline. Message saved.
```

Rules:
- Incoming PMs must display in real-time even if the user is currently inside a chat room.
- Private message formats must be visually distinct from room chat broadcasts.
- PM history logs are retrieved from the Gateway/Central Database.

### 5.3 Room List Table

Columns:
- Room name.
- Hosting Server ID.
- Active user count.
- Total files uploaded.
- Visibility (public/private).

Actions:
- **Create Room:** Requests a new room allocation from the Gateway.
- **Join Room:** Gateway returns the Process Server details, and the client connects.
- Upon joining, the Room Panel interface is activated.

---

## 6. Room Area UX

The Room Panel is activated after a user joins a chat room.

Components:
- Room header (displaying room name, host server, latency).
- Chat message history log.
- Text input box and Send button.
- Room participant listing.
- Files listing database table.
- Upload file control.
- Download selected file control.
- Resume transfer control.
- Live file transfer progress bar.

### 6.1 Room Chat History

Format:
```txt
[ROOM FP-Jaringan | 20:20:01] budi: Hello everyone
[ROOM FP-Jaringan | 20:20:05] erlangga: I am uploading the report
[SYSTEM | 20:20:06] erlangga started uploading laporan.pdf
```

Rules:
- Room chat strictly displays messages broadcasted within the currently active room.
- Chat messages are sent to the assigned Process Server, bypassing the Gateway.
- Last 50 messages are automatically retrieved upon entering the room.
- Chat display logs are read-only.
- Input fields clear instantly upon successful transmission.

### 6.2 Room Members List

Columns:
- Username.
- Member role (admin/member).
- Presence status.

Actions:
- Selecting a member allows sending a PM to them directly.

### 6.3 File List Table

Columns:
- File ID.
- Filename.
- Size.
- Uploader.
- Integrity status (available/corrupted).
- Upload date/time.

Actions:
- **Upload:** Opens the local browser file dialog.
- **Download:** Downloads the selected file.
- **Resume:** Resumes an interrupted transfer.
- **Refresh:** Requests the latest file listing from the Process Server.

---

## 7. File Transfer UX

### 7.1 Uploading Files

User workflow:
1. The user clicks the **Upload** button.
2. The browser opens a file dialogue.
3. The user selects a file.
4. The UI displays file metadata: name, size, chunk size, total chunks, and SHA-256 hash.
5. The user confirms the upload.
6. The upload process executes in background threads.
7. The progress bar updates dynamically via the event queue.
8. Upon completion, the client displays a success/failure checksum message.

Progress bar formatting:
```txt
Uploading laporan.pdf to Server S1
67% | 1.60 MB / 2.40 MB | 780 KB/s | ETA 2s
```

### 7.2 Downloading Files

User workflow:
1. The user selects a file entry from the File List.
2. The user clicks the **Download** button.
3. The browser prompts for a download folder or uses the default `downloads/` directory.
4. The download executes in background threads.
5. The progress bar updates dynamically.
6. Upon completion, the client validates the file checksum and saves it.

### 7.3 Resume Transfer

If a transfer is interrupted:
- The transaction entry appears in the Transfer Panel marked as `interrupted`.
- The user can click the **Resume** button.
- The client sends a `RESUME_TRANSFER` handshake.
- The progress bar resumes loading from the last written chunk index.

---

## 8. Status Bar

The status bar must be persistently visible at the bottom of the client window.

Status bar details:
- Gateway connection status (connected/disconnected).
- Process Server status (connected/disconnected, Server ID, Host IP).
- Current active room name.
- Live network latency (RTT).
- Last error message preview.

Example:
```txt
Gateway: connected | Room: FP-Jaringan @ S1 | Latency: 12 ms | Status: Ready
```

---

## 9. Error Notifications

Standard warnings appear in the status bar. Critical errors are displayed using modal alert boxes.

Example messages:
- `Invalid username or password.`
- `Room not found.`
- `Server S1 is offline. Please try again later.`
- `File size exceeds the 100 MB limit.`
- `Checksum verification failed. File marked corrupted.`
- `Invalid packet structure received.`

Rules:
- Never display raw JSON packets in user-facing error dialogues.
- Detailed technical exception traces must be written to log files.
- The UI must remain responsive and active after errors.

---

## 10. Concurrent Web Sessions and UI Updates

The browser Web UI interacts asynchronously with the Web API server via fetch requests. Real-time events are dispatched from backend TCP sockets to the Web API server, then forwarded to the browser client using an HTTP Long-polling `/api/events` mechanism.

Required Javascript Polling Pattern:

```javascript
async function pollEvents() {
    try {
        const response = await fetch(`/api/events?session_id=${sessionId}`);
        const data = await response.json();
        for (const event of data.events) {
            handleEvent(event);
        }
    } catch (e) {
        console.error("Polling error", e);
    }
    setTimeout(pollEvents, 500);
}
```

Web API Threads:
- The HTTP ThreadPool serves concurrent incoming requests from the browser.
- Background receiver threads read TCP socket streams and queue events in the thread-safe `WebSession.events`.

Rules:
- The web client (JavaScript) must not block the UI during file transfers.
- Upload and download progress is updated dynamically using standard web progress elements.

---

## 11. Web Client & API Bridge Files

```txt
client/
├── main.py                 # Entry point / Web Server launcher
├── gateway_connection.py   # Gateway TCP socket handler
└── room_connection.py      # Process Server TCP socket handler
web_ui/
├── index.html              # Single Page Application HTML markup
└── app.js                  # UI event handlers, upload queue, DOM updates
web_api/
└── server.py               # Web API HTTP translation server
```

---

## 12. Help Guidelines Dialog

Help guidelines must be accessible through a dedicated **Help** menu or button in the Web UI.

Information included:
- Instructions to register and log in.
- Steps to send global Private Messages.
- Steps to create and join rooms.
- Instructions to chat inside a room.
- Instructions to upload and download files.
- Visual definitions of status bar symbols.

---

## 13. UX Rules

1. The primary client UI must be a browser-based Web UI.
2. Do not use CLI/TUI interfaces as the primary user client.
3. Private message formats must be visually distinct from room chat broadcasts.
4. System notifications must be visually distinct from user messages.
5. File transfers must display a live progress bar.
6. Users must be able to receive PMs while active inside a chat room.
7. The lobby/waiting area and room chat area must be visually distinct.
8. Buttons triggering network requests should be disabled while processing is underway.
9. The browser GUI must never freeze during transfers or message surges.
10. All UI updates from the background networking threads must be routed to the browser via long-polling `/api/events` requests.
