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

        # Initial data simulation
        self.simulate_data()

    def on_refresh(self):
        self.app.logger.info("Refreshing user and room lists")
        # In real app, send LIST_ONLINE_USERS and LIST_ROOMS requests
        self.simulate_data()

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
        # Real app: send PRIVATE_MESSAGE_SEND to Gateway
        import datetime
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.pm_display.add_message(self.app.current_user, message, ts, "self")
        self.pm_entry.delete(0, tk.END)

    def simulate_data(self):
        self.user_list.update_users(["user1", "user2", "admin", "guest"])
        self.room_list.update_rooms([
            {"name": "General", "members": 5},
            {"name": "Python", "members": 12},
            {"name": "Networking", "members": 3}
        ])
