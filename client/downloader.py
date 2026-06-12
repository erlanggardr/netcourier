import threading
import os
import hashlib
import json
import struct
from common.protocol import build_packet, send_packet

class Downloader:
    def __init__(self, app, file_id, filename, save_path):
        self.app = app
        self.file_id = file_id
        self.filename = filename
        self.save_path = save_path
        self.transfer_id = None
        self.total_chunks = 0
        self.chunk_size = 0
        self.checksum_sha256 = None
        self.file_obj = None
        self.received_chunks = 0

    def start(self):
        # Open file
        try:
            self.file_obj = open(self.save_path, "wb")
        except Exception as e:
            self.app.show_error(f"Failed to open file for writing: {e}")
            return

        self.app.room_conn.send_request("DOWNLOAD_REQUEST", {
            "file_id": self.file_id
        }, callback=self.on_download_ready)

    def on_download_ready(self, header):
        if header.get("type") == "ERROR":
            self.file_obj.close()
            self.app.run_in_ui(self.app.show_error, header.get("payload", {}).get("message", "Download failed"))
            return

        payload = header.get("payload", {})
        self.transfer_id = payload.get("transfer_id")
        self.total_chunks = payload.get("total_chunks")
        self.chunk_size = payload.get("chunk_size")
        self.checksum_sha256 = payload.get("checksum_sha256")
        
        self.app.logger.info(f"Download ready: {self.filename}, chunks: {self.total_chunks}")
        self.app.run_in_ui(self.app.room_view.transfer_progress.update_progress, self.filename, 0, 100, "Starting...")

    def handle_chunk(self, chunk_index, chunk_data):
        if not self.file_obj:
            return

        self.file_obj.seek(chunk_index * self.chunk_size)
        self.file_obj.write(chunk_data)
        self.received_chunks += 1
        
        progress = int((self.received_chunks / self.total_chunks) * 100)
        self.app.run_in_ui(self.app.room_view.transfer_progress.update_progress, self.filename, progress, 100, "Downloading...")

        if self.received_chunks == self.total_chunks:
            self.finish_download()

    def finish_download(self):
        self.file_obj.close()
        self.file_obj = None
        
        # Verify checksum
        sha256 = hashlib.sha256()
        with open(self.save_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        calc_checksum = sha256.hexdigest()
        
        if calc_checksum == self.checksum_sha256:
            self.app.logger.info(f"Download finished successfully: {self.filename}")
            self.app.run_in_ui(self.app.room_view.transfer_progress.update_progress, self.filename, 100, 100, "Success")
        else:
            self.app.logger.error(f"Checksum mismatch for {self.filename}")
            self.app.run_in_ui(self.app.show_error, "Checksum failed!")
            self.app.run_in_ui(self.app.room_view.transfer_progress.update_progress, self.filename, 100, 100, "Checksum Error")
