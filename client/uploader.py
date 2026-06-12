import threading
import os
import hashlib
import json
import struct
from common.protocol import build_packet, send_packet

class Uploader(threading.Thread):
    def __init__(self, app, file_path, room_name, room_id):
        super().__init__(daemon=True)
        self.app = app
        self.file_path = file_path
        self.room_name = room_name
        self.room_id = room_id
        self.filename = os.path.basename(file_path)
        self.filesize = os.path.getsize(file_path)
        self.chunk_size = 65536
        self.total_chunks = (self.filesize + self.chunk_size - 1) // self.chunk_size
        self.transfer_id = None
        self.checksum = None
        
    def run(self):
        # Calculate checksum
        sha256 = hashlib.sha256()
        with open(self.file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        self.checksum = sha256.hexdigest()
        
        # Send UPLOAD_INIT
        self.app.room_conn.send_request("UPLOAD_INIT", {
            "room_id": self.room_id,
            "room_name": self.room_name,
            "filename": self.filename,
            "filesize": self.filesize,
            "chunk_size": self.chunk_size,
            "total_chunks": self.total_chunks,
            "checksum_sha256": self.checksum
        }, callback=self.on_upload_ready)
        
    def on_upload_ready(self, header):
        if header.get("type") == "ERROR":
            self.app.run_in_ui(self.app.show_error, header.get("payload", {}).get("message", "Upload failed"))
            return
            
        payload = header.get("payload", {})
        self.transfer_id = payload.get("transfer_id")
        start_chunk = payload.get("start_chunk", 0)
        
        threading.Thread(target=self.upload_chunks, args=(start_chunk,), daemon=True).start()
        
    def upload_chunks(self, start_chunk):
        with open(self.file_path, "rb") as f:
            f.seek(start_chunk * self.chunk_size)
            for i in range(start_chunk, self.total_chunks):
                chunk_data = f.read(self.chunk_size)
                
                packet = build_packet("UPLOAD_CHUNK", {
                    "transfer_id": self.transfer_id,
                    "chunk_index": i
                }, token=self.app.token)
                
                packet["payload_size"] = len(chunk_data)
                header_json = json.dumps(packet).encode('utf-8')
                
                try:
                    self.app.room_conn.sock.sendall(struct.pack(">I", len(header_json)) + header_json + chunk_data)
                    # Update UI progress
                    progress = int(((i + 1) / self.total_chunks) * 100)
                    self.app.run_in_ui(self.app.room_view.transfer_progress.update_progress, self.filename, progress, 100, "Uploading...")
                except Exception as e:
                    self.app.logger.error(f"Error uploading chunk {i}: {e}")
                    return
                
        # Send UPLOAD_FINISH
        self.app.room_conn.send_request("UPLOAD_FINISH", {
            "transfer_id": self.transfer_id
        }, callback=self.on_upload_success)
        
    def on_upload_success(self, header):
        if header.get("type") == "ERROR":
            self.app.run_in_ui(self.app.show_error, header.get("payload", {}).get("message", "Upload failed"))
            return
        self.app.run_in_ui(self.app.room_view.transfer_progress.update_progress, self.filename, 100, 100, "Success")
        self.app.run_in_ui(self.app.room_view.request_file_list)
