import tkinter as tk
from tkinter import ttk, messagebox
from client.widgets import StatusBar, UserList, RoomList, MessageList

class WaitingView(ttk.Frame):
    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, **kwargs)
        self.app = app
        
        self.setup_ui()

    def setup_ui(self):
        # Top toolbar
        self.toolbar = ttk.Frame(self)
        self.toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        ttk.Label(self.toolbar, text="Waiting Room", font=("Arial", 14, "bold")).pack(side=tk.LEFT)
        
        self.logout_btn = ttk.Button(self.toolbar, text="Logout", command=self.app.show_login_register)
        self.logout_btn.pack(side=tk.RIGHT)
        
        self.refresh_btn = ttk.Button(self.toolbar, text="Refresh", command=self.on_refresh)
        self.refresh_btn.pack(side=tk.RIGHT, padx=5)

        # Main content area
        self.main_paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left sidebar - Online Users
        self.user_list = UserList(self.main_paned)
        self.main_paned.add(self.user_list, weight=1)
        self.user_list.bind_select(self.on_user_selected)
        
        # Center - Room List and Private Chat
        self.center_frame = ttk.Frame(self.main_paned)
        self.main_paned.add(self.center_frame, weight=3)
        
        self.room_list = RoomList(self.center_frame)
        self.room_list.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        self.join_btn = ttk.Button(self.center_frame, text="Join Selected Room", command=self.on_join_room)
        self.join_btn.pack(fill=tk.X)
        
        self.create_room_frame = ttk.LabelFrame(self.center_frame, text="Create New Room")
        self.create_room_frame.pack(fill=tk.X, pady=5)
        
        self.room_name_entry = ttk.Entry(self.create_room_frame)
        self.room_name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        
        self.create_btn = ttk.Button(self.create_room_frame, text="Create", command=self.on_create_room)
        self.create_btn.pack(side=tk.RIGHT, padx=5, pady=5)

        # Right sidebar - Private Chat (Optional, but useful)
        self.pm_frame = ttk.LabelFrame(self.main_paned, text="Global Private Messages")
        self.main_paned.add(self.pm_frame, weight=2)
        
        self.pm_display = MessageList(self.pm_frame)
        self.pm_display.pack(fill=tk.BOTH, expand=True)
        
        self.pm_input_frame = ttk.Frame(self.pm_frame)
        self.pm_input_frame.pack(fill=tk.X)
        
        self.pm_entry = ttk.Entry(self.pm_input_frame)
        self.pm_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        self.pm_entry.bind("<Return>", lambda e: self.on_send_pm())
        
        self.send_pm_btn = ttk.Button(self.pm_input_frame, text="Send PM", command=self.on_send_pm)
        self.send_pm_btn.pack(side=tk.RIGHT)

        # Status bar
        self.status_bar = StatusBar(self)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_bar.set_user(self.app.current_user)
        self.status_bar.set_status("Connected to Gateway")

        # Initial data fetch
        self.on_refresh()

    def on_refresh(self):
        self.app.logger.info("Refreshing user and room lists")
        self.app.gateway_conn.send_request("LIST_ONLINE_USERS", callback=self._on_online_users_response)
        # LIST_ROOMS is Phase 4, but we can send it or just ignore it for now
        # self.app.gateway_conn.send_request("LIST_ROOMS", callback=self._on_list_rooms_response)

    def _on_online_users_response(self, header):
        if header["type"] == "ONLINE_USERS_RESPONSE":
            users = header["payload"].get("users", [])
            # users is a list of dicts with 'username' and 'status'
            user_names = [u["username"] for u in users]
            self.user_list.update_users(user_names)
        elif header["type"] == "ERROR":
            messagebox.showerror("Error", f"Failed to get online users: {header['payload'].get('message')}")

    def on_user_selected(self):
        selected_user = self.user_list.get_selected_user()
        if selected_user:
            self.app.logger.info(f"Selected user: {selected_user}, requesting PM history")
            self.pm_display.text_area.config(state=tk.NORMAL)
            self.pm_display.text_area.delete(1.0, tk.END)
            self.pm_display.text_area.config(state=tk.DISABLED)
            
            self.app.gateway_conn.send_request("PM_HISTORY_REQUEST", {
                "other_username": selected_user
            }, callback=self._on_pm_history_response)

    def _on_pm_history_response(self, header):
        if header["type"] == "PM_HISTORY_RESPONSE":
            messages = header["payload"].get("messages", [])
            other_username = header["payload"].get("other_username")
            
            # Check if this user is still selected
            if self.user_list.get_selected_user() != other_username:
                return
                
            self.pm_display.text_area.config(state=tk.NORMAL)
            self.pm_display.text_area.delete(1.0, tk.END)
            self.pm_display.text_area.config(state=tk.DISABLED)
            
            for msg in messages:
                sender = msg["sender_username"]
                content = msg["content"]
                timestamp = msg["created_at"].split(" ")[1] if " " in msg["created_at"] else msg["created_at"]
                
                align = "self" if sender == self.app.current_user else "other"
                self.pm_display.add_message(sender, content, timestamp, align)
        elif header["type"] == "ERROR":
            messagebox.showerror("Error", f"Failed to get PM history: {header['payload'].get('message')}")

    def on_join_room(self):
        room_name = self.room_list.get_selected_room()
        if not room_name:
            messagebox.showwarning("Warning", "Please select a room to join")
            return
        
        self.app.logger.info(f"Joining room: {room_name}")
        # Real app: send JOIN_ROOM to Gateway, get server location, then switch view
        self.app.show_room_chat()

    def on_create_room(self):
        room_name = self.room_name_entry.get()
        if not room_name:
            messagebox.showwarning("Warning", "Please enter a room name")
            return
        
        self.app.logger.info(f"Creating room: {room_name}")
        # Real app: send CREATE_ROOM to Gateway
        messagebox.showinfo("Success", f"Room '{room_name}' created!")
        self.room_name_entry.delete(0, tk.END)
        self.on_refresh()

    def on_send_pm(self):
        recipient = self.user_list.get_selected_user()
        message = self.pm_entry.get()
        if not recipient:
            messagebox.showwarning("Warning", "Please select a user to send a private message")
            return
        if not message:
            return
        
        self.app.logger.info(f"Sending PM to {recipient}: {message}")
        
        # Display our own message locally first
        import datetime
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.pm_display.add_message(self.app.current_user, message, ts, "self")
        self.pm_entry.delete(0, tk.END)
        
        # Send to Gateway
        self.app.gateway_conn.send_request("PRIVATE_MESSAGE_SEND", {
            "recipient_username": recipient,
            "content": message
        }, callback=self._on_pm_status)

    def _on_pm_status(self, header):
        if header["type"] == "PRIVATE_MESSAGE_STATUS":
            status = header["payload"].get("status")
            recipient = header["payload"].get("recipient_username")
            # We already displayed it, maybe update status?
            pass
        elif header["type"] == "ERROR":
            messagebox.showerror("PM Error", header["payload"].get("message", "Unknown error"))

    def on_pm_received(self, payload):
        sender = payload.get("sender_username")
        content = payload.get("content")
        timestamp = payload.get("timestamp")
        if not timestamp:
            import datetime
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        else:
            # Parse timestamp if needed, but just using it is fine
            timestamp = timestamp.split(" ")[1] if " " in timestamp else timestamp
            
        self.pm_display.add_message(sender, content, timestamp, "other")
