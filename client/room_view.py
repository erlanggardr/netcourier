import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from client.widgets import StatusBar, UserList, MessageList, FileList, TransferProgress

class RoomView(ttk.Frame):
    def __init__(self, parent, app, room_name="General", **kwargs):
        super().__init__(parent, **kwargs)
        self.app = app
        self.room_name = room_name
        
        self.setup_ui()
        self.request_history()

    def request_history(self):
        if self.app.room_conn:
            self.app.room_conn.send_request("ROOM_HISTORY_REQUEST", {
                "room_name": self.room_name,
                "limit": 50
            })

    def setup_ui(self):
        # Top toolbar
        self.toolbar = ttk.Frame(self)
        self.toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        ttk.Label(self.toolbar, text=f"Room: {self.room_name}", font=("Arial", 14, "bold")).pack(side=tk.LEFT)
        
        self.leave_btn = ttk.Button(self.toolbar, text="Leave Room", command=self.on_leave)
        self.leave_btn.pack(side=tk.RIGHT)

        # Main content area
        self.main_paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left side - Chat and Input
        self.chat_frame = ttk.Frame(self.main_paned)
        self.main_paned.add(self.chat_frame, weight=3)
        
        self.message_list = MessageList(self.chat_frame)
        self.message_list.pack(fill=tk.BOTH, expand=True)
        
        self.input_frame = ttk.Frame(self.chat_frame)
        self.input_frame.pack(fill=tk.X, pady=5)
        
        self.message_entry = ttk.Entry(self.input_frame)
        self.message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.message_entry.bind("<Return>", lambda e: self.on_send_message())
        
        self.send_btn = ttk.Button(self.input_frame, text="Send", command=self.on_send_message)
        self.send_btn.pack(side=tk.RIGHT, padx=5)

        # Right side - Members and Files
        self.sidebar_paned = ttk.PanedWindow(self.main_paned, orient=tk.VERTICAL)
        self.main_paned.add(self.sidebar_paned, weight=1)
        
        self.user_list = UserList(self.sidebar_paned, title="Room Members")
        self.sidebar_paned.add(self.user_list, weight=1)
        
        self.files_frame = ttk.Frame(self.sidebar_paned)
        self.sidebar_paned.add(self.files_frame, weight=1)
        
        self.file_list = FileList(self.files_frame)
        self.file_list.pack(fill=tk.BOTH, expand=True)
        
        self.file_btn_frame = ttk.Frame(self.files_frame)
        self.file_btn_frame.pack(fill=tk.X)
        
        self.upload_btn = ttk.Button(self.file_btn_frame, text="Upload", command=self.on_upload)
        self.upload_btn.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.download_btn = ttk.Button(self.file_btn_frame, text="Download", command=self.on_download)
        self.download_btn.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Bottom - Progress and Status
        self.bottom_frame = ttk.Frame(self)
        self.bottom_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.transfer_progress = TransferProgress(self.bottom_frame)
        self.transfer_progress.pack(fill=tk.X, padx=5, pady=2)
        
        self.status_bar = StatusBar(self.bottom_frame)
        self.status_bar.pack(fill=tk.X)
        self.status_bar.set_user(self.app.current_user)
        self.status_bar.set_status(f"Connected to Process Server (Room: {self.room_name})")

        # Initial data simulation
        self.simulate_data()

    def on_send_message(self):
        message = self.message_entry.get()
        if not message:
            return

        self.app.logger.info(f"Sending message: {message}")
        if self.app.room_conn:
            self.app.room_conn.send_request("ROOM_CHAT_SEND", {
                "room_name": self.room_name,
                "message": message
            })
            self.message_entry.delete(0, tk.END)

    def on_room_message(self, payload):
        sender = payload.get("sender_username")
        content = payload.get("message")
        timestamp = payload.get("timestamp")
        if not timestamp:
            import datetime
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        else:
            timestamp = timestamp.split(" ")[1] if " " in timestamp else timestamp

        align = "self" if sender == self.app.current_user else "other"
        self.message_list.add_message(sender, content, timestamp, align)

    def on_room_system_event(self, payload):
        event_type = payload.get("event_type")
        message = payload.get("message")
        import datetime
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.message_list.add_message(None, message, ts, "system")

        # If member list changed, update it
        if "members" in payload:
            self.user_list.update_users(payload["members"])

    def on_room_history_response(self, payload):
        messages = payload.get("messages", [])
        # Clear existing messages just in case
        self.message_list.clear()

        for msg in messages:
            sender = msg.get("sender_username")
            content = msg.get("message")
            timestamp = msg.get("timestamp")
            if timestamp and " " in timestamp:
                timestamp = timestamp.split(" ")[1]

            if msg.get("message_type") == "system":
                self.message_list.add_message(None, content, timestamp, "system")
            else:
                align = "self" if sender == self.app.current_user else "other"
                self.message_list.add_message(sender, content, timestamp, align)

    def on_upload(self):
        file_path = filedialog.askopenfilename()
        if file_path:
            self.app.logger.info(f"Uploading file: {file_path}")
            # Real app: start upload thread, update progress bar
            import os
            filename = os.path.basename(file_path)
            self.transfer_progress.update_progress(filename, 50, 100, "1.2 MB/s")

    def on_download(self):
        selected_file = self.file_list.get_selected_file()
        if not selected_file:
            messagebox.showwarning("Warning", "Please select a file to download")
            return
        
        filename = selected_file[0]
        save_path = filedialog.asksaveasfilename(initialfile=filename)
        if save_path:
            self.app.logger.info(f"Downloading file: {filename} to {save_path}")
            # Real app: start download thread, update progress bar
            self.transfer_progress.update_progress(filename, 30, 100, "2.5 MB/s")

    def on_leave(self):
        self.app.logger.info(f"Leaving room: {self.room_name}")
        self.app.leave_room_backend()

    def simulate_data(self):
        self.user_list.update_users(["user1", "user2", "admin"])
        self.file_list.update_files([
            {"filename": "project_spec.pdf", "size": "1.2 MB", "owner": "admin"},
            {"filename": "diagram.png", "size": "450 KB", "owner": "user2"}
        ])
        self.message_list.add_message(None, f"Joined room: {self.room_name}", "10:00:00")
        self.message_list.add_message("admin", "Welcome to the general room!", "10:01:00")
