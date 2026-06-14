# Security Specification - NetCourier

This document specifies the baseline security architecture, rules, and configurations for NetCourier.

---

## 1. Security Goals

1. Prevent unauthorized access (enforce authentication before usage).
2. Avoid storing passwords in plain text.
3. Validate session tokens for all data plane requests.
4. Ensure malformed packets do not crash servers.
5. Prevent path traversal attacks during file upload and download processes.
6. Apply rate limits to prevent chat spam and resource depletion.
7. Validate file integrity using cryptographic checksums.

---

## 2. Authentication Security

### 2.1 Password Hashing

Passwords must never be stored in plain text.

Recommendation:
- Use `bcrypt` if available on the deployment system.
- Otherwise, fall back to `hashlib.pbkdf2_hmac`.

Baseline requirement:
```txt
password_hash = PBKDF2(password, salt, iterations=100000)
```

Stored user records must contain:
- `salt`
- `hash`
- `algorithm`

---

### 2.2 Session Tokens

Upon successful user authentication, the Gateway generates a cryptographically secure random session token.

Rules:
- Tokens must be at least 32 bytes of secure random data.
- The token is transmitted to the client immediately after login.
- The database stores only the SHA-256 hash of the token, never the plain token.
- Tokens are set to inactive in the database upon user logout.
- Any request presenting an invalid or expired token is rejected.

---

### 2.3 Duplicate Login

Baseline project rules:
- A username is restricted to a single active session at any given time.
- Secondary login attempts are rejected with `ERROR DUPLICATE_LOGIN`.

Alternative approach:
- A second login attempt terminates the previous active session session.

---

## 3. Authorization Rules

| Action | Required Role |
|---|---|
| Register | Guest |
| Login | Guest |
| Private Message (PM) | Authenticated |
| List rooms | Authenticated |
| Create room | Authenticated |
| Join room | Authenticated |
| Room chat | Room member |
| Upload / Download file | Room member |
| Delete file | Room admin / owner |
| Kick user | Room admin / owner |

---

## 4. Packet Validation

Every incoming packet must be validated for structure and constraints:

- Ensure `type` is populated.
- Ensure `request_id` is present.
- Ensure `payload` is present.
- Verify all required fields for the message type are populated.
- Validate session tokens where required.
- Validate that `payload_size` matches the received binary payload.
- Ensure the message type is known.
- Verify data types of payload variables.

If a packet is invalid:
- Respond with `ERROR INVALID_PACKET`.
- Log the validation exception.
- Maintain server uptime (do not crash).

---

## 5. Rate Limiting

Apply baseline limits to protect resources:

| Action | Limit |
|---|---|
| Chat room broadcasting | Max 5 messages / 3 seconds |
| Private messaging (PM) | Max 5 messages / 3 seconds |
| Failed login attempts | Max 5 attempts / minute |
| Active file transfers | Max 2 concurrent transfers per user |
| File size limit | Max 100 MB for demo (configurable) |

If a limit is exceeded:
- Return `ERROR RATE_LIMIT_EXCEEDED`.

---

## 6. File Security

### 6.1 Filename Sanitization

Filenames must be sanitized to block directory traversal. Filenames must not contain:
- `../`
- `..\\`
- Absolute path markers (e.g., `/` or `C:\`)
- Null bytes
- Control characters

Use server-generated stored filenames formatted as:

```txt
<timestamp>_<random_string>_<safe_original_filename>
```

### 6.2 Storage Directory Restrictions

Physical files must be saved under the designated storage folder:

```txt
storage/<server_id>/rooms/<room_name>/
```

Process Servers must restrict all disk writes within this specific folder structure.

### 6.3 File Size Limits

Default limit:
```txt
MAX_FILE_SIZE = 100 MB (Note: can be scaled up dynamically based on config settings)
```

### 6.4 Checksum Validation

All file transfers must enforce SHA-256 validation.

If a checksum mismatch is detected:
- The file's status is marked as `corrupted` in the database.
- File downloads are blocked until the file is fixed or re-uploaded.
- An audit log is recorded.

---

## 7. Gateway Security

The Gateway must:
- Validate credentials securely.
- Track active sessions.
- Perform token validations requested by Process Servers.
- Reject/ignore large file payloads (prevent gateway resource depletion).
- Refuse client-determined server assignments (Gateway determines routing).
- Only route users to Process Servers with an `alive` status.

---

## 8. Process Server Security

Process Servers must:
- Terminate connections presenting invalid session tokens.
- Restrict chat broadcasts and file actions to verified room members.
- Deny file uploads from users not currently active in the room context.
- Sanitize and block hazardous file path syntax.
- Verify chunk indices and offsets during file writes.
- Terminate file transfer transactions that time out.

---

## 9. Logging Security Guidelines

Never write the following data to logs:
- User passwords.
- Plain-text session tokens.
- Binary data block segments.

Authorized logging elements:
- Usernames.
- Message event types.
- Target room names.
- File metadata (names, sizes, hashes).
- Source IP addresses.
- System error codes.

---

## 10. Public Hosting Safety Rules

If deploying on a public VPS:
1. Do not run Python processes under the root user context.
2. Expose only the mandatory ports (e.g., 9000, 9101, 9102).
3. Enable and configure the system firewall (e.g., UFW).
4. Enforce strict maximum file size constraints.
5. Disable verbose debug logging in production environments.
6. Never commit credentials or secrets to version control.
7. Externalize configuration via `.env` files.
8. Enforce TLS wrapping if time permits.

---

## 11. Security Acceptance Criteria

- [ ] User passwords are hashed securely.
- [ ] Requests with invalid session tokens are rejected.
- [ ] Guests cannot join rooms or broadcast chats.
- [ ] Users cannot write or read chats/files in rooms they are not members of.
- [ ] Path traversal strings (e.g., `../../etc/passwd`) are blocked and rejected.
- [ ] Files with mismatched SHA-256 checksums are marked corrupted.
- [ ] Malformed JSON packets do not cause servers to crash.
- [ ] Message rate limiting blocks spam.
