import tkinter as tk
from tkinter import ttk, messagebox
import queue
import logging
import threading

from client.auth_view import AuthView
from client.waiting_view import WaitingView
from client.room_view import RoomView
from client.gateway_connection import GatewayConnection

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

    def show_room_chat(self, room_name="General"):
        self.logger.info(f"Switching to Room Chat view: {room_name}")
        self._clear_container()
        self.current_view = RoomView(self.container, self, room_name=room_name)
        self.current_view.pack(fill=tk.BOTH, expand=True)

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
