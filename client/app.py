import tkinter as tk
from tkinter import ttk, messagebox
import queue
import logging
import threading

from client.auth_view import AuthView
from client.waiting_view import WaitingView
from client.room_view import RoomView
from client.gateway_connection import GatewayConnection
from client.room_connection import RoomConnection

class NetCourierApp:
    def __init__(self, gateway_host, gateway_port):
        self.gateway_host = gateway_host
        self.gateway_port = gateway_port
        
        self.root = tk.Tk()
        self.root.title("NetCourier")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)
        
        self.queue = queue.Queue()
        self.logger = logging.getLogger("NetCourierApp")
        
        # Application state
        self.current_user = None
        self.token = None
        self.current_view = None
        
        # Networking
        self.gateway_conn = GatewayConnection(gateway_host, gateway_port, self)
        self.room_conn = None
        
        # Setup styles
        self._setup_styles()
        
        # Initialize views (will be lazy loaded or swapped)
        self.container = ttk.Frame(self.root)
        self.container.pack(fill=tk.BOTH, expand=True)
        
        # Start polling the queue
        self.root.after(100, self._process_queue)
        
        # Show initial view
        self.show_login_register()

    def _setup_styles(self):
        style = ttk.Style()
        # You can add custom styles here
        pass

    def _process_queue(self):
        """Poll the queue for UI updates from other threads."""
        try:
            while True:
                item = self.queue.get_nowait()
                if len(item) == 3:
                    callback, args, kwargs = item
                    try:
                        callback(*args, **kwargs)
                    except Exception as e:
                        self.logger.exception(f"Error executing callback from queue: {e}")
                self.queue.task_done()
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self._process_queue)

    def run_in_ui(self, callback, *args, **kwargs):
        """Schedule a callback to be run in the main UI thread."""
        self.queue.put((callback, args, kwargs))

    def show_login_register(self):
        self.logger.info("Switching to Login/Register view")
        self._clear_container()
        self.current_view = AuthView(self.container, self)
        self.current_view.pack(fill=tk.BOTH, expand=True)

    def show_waiting_room(self):
        self.logger.info("Switching to Waiting Room view")
        self._clear_container()
        self.current_view = WaitingView(self.container, self)
        self.current_view.pack(fill=tk.BOTH, expand=True)

    def show_room_chat(self, room_name="General", host=None, port=None):
        """Transition to a room. If host/port provided, connect to backend first."""
        if host and port:
            self.join_room_backend(host, port, room_name)
        else:
            self.logger.info(f"Switching to Room Chat view: {room_name}")
            self._clear_container()
            self.current_view = RoomView(self.container, self, room_name=room_name)
            self.current_view.pack(fill=tk.BOTH, expand=True)

    def join_room_backend(self, host, port, room_name):
        self.logger.info(f"Connecting to backend room {room_name} at {host}:{port}")
        
        if self.room_conn:
            self.room_conn.disconnect()
            
        self.room_conn = RoomConnection(host, port, self)
        if self.room_conn.connect():
            # 1. Auth with backend
            self.room_conn.send_request("AUTH_BACKEND", callback=lambda h: self._on_auth_backend_response(h, room_name))
        else:
            messagebox.showerror("Error", f"Could not connect to room server at {host}:{port}")

    def _on_auth_backend_response(self, header, room_name):
        if header["type"] == "AUTH_BACKEND_OK":
            # 2. Join room
            self.room_conn.send_request("JOIN_ROOM_BACKEND", {"room_name": room_name}, 
                                        callback=self._on_join_room_backend_response)
        else:
            messagebox.showerror("Auth Error", "Failed to authenticate with room server")

    def _on_join_room_backend_response(self, header):
        if header["type"] == "JOIN_ROOM_OK":
            room_name = header["payload"]["room_name"]
            self.room_conn.current_room = room_name
            self.show_room_chat(room_name)
        else:
            messagebox.showerror("Join Error", "Failed to join room on server")

    def leave_room_backend(self):
        if self.room_conn:
            self.room_conn.send_request("LEAVE_ROOM", callback=self._on_leave_room_response)

    def _on_leave_room_response(self, header):
        if self.room_conn:
            self.room_conn.disconnect()
            self.room_conn = None
        self.show_waiting_room()

    def on_room_disconnected(self):
        if self.room_conn:
            messagebox.showwarning("Room Connection Lost", "Disconnected from room server.")
            self.room_conn = None
            self.show_waiting_room()

    def on_room_message(self, payload):
        if isinstance(self.current_view, RoomView):
            self.current_view.on_room_message(payload)

    def on_room_system_event(self, payload):
        if isinstance(self.current_view, RoomView):
            self.current_view.on_room_system_event(payload)

    def _clear_container(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    def on_login_success(self, username, token):
        self.current_user = username
        self.token = token
        self.show_waiting_room()

    def run(self):
        self.root.mainloop()

    def cleanup(self):
        self.logger.info("Cleaning up application...")
        self.gateway_conn.disconnect()
        self.root.destroy()

    def on_gateway_disconnected(self):
        messagebox.showwarning("Connection Lost", "Connection to Gateway was lost.")
        self.show_login_register()

    def show_error(self, message):
        messagebox.showerror("Error", message)

    def on_pm_received(self, payload):
        # Forward to waiting view if active
        if isinstance(self.current_view, WaitingView):
            self.current_view.on_pm_received(payload)
        else:
            # Maybe show a notification?
            self.logger.info(f"PM received from {payload.get('from_username')}: {payload.get('message')}")
