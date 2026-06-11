import tkinter as tk
from tkinter import ttk

class StatusBar(ttk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.status_label = ttk.Label(self, text="Disconnected", relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.user_label = ttk.Label(self, text="Not logged in", relief=tk.SUNKEN, anchor=tk.W, width=20)
        self.user_label.pack(side=tk.RIGHT)

    def set_status(self, text):
        self.status_label.config(text=text)

    def set_user(self, username):
        self.user_label.config(text=f"User: {username}")

class MessageList(ttk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.text_area = tk.Text(self, state=tk.DISABLED, wrap=tk.WORD)
        self.scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.text_area.yview)
        self.text_area.configure(yscrollcommand=self.scrollbar.set)
        
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Configure tags for different message types
        self.text_area.tag_configure("system", foreground="gray", font=("Arial", 10, "italic"))
        self.text_area.tag_configure("self", foreground="blue", font=("Arial", 10, "bold"))
        self.text_area.tag_configure("other", foreground="black", font=("Arial", 10, "bold"))
        self.text_area.tag_configure("private", foreground="purple", font=("Arial", 10, "italic"))

    def add_message(self, sender, message, timestamp, msg_type="other"):
        self.text_area.config(state=tk.NORMAL)
        if sender:
            self.text_area.insert(tk.END, f"[{timestamp}] ", "system")
            tag = msg_type if msg_type in ["self", "other", "private"] else "other"
            self.text_area.insert(tk.END, f"{sender}: ", tag)
            self.text_area.insert(tk.END, f"{message}\n")
        else:
            self.text_area.insert(tk.END, f"[{timestamp}] {message}\n", "system")
        
        self.text_area.see(tk.END)
        self.text_area.config(state=tk.DISABLED)

    def clear(self):
        self.text_area.config(state=tk.NORMAL)
        self.text_area.delete(1.0, tk.END)
        self.text_area.config(state=tk.DISABLED)

class UserList(ttk.Frame):
    def __init__(self, parent, title="Online Users", **kwargs):
        super().__init__(parent, **kwargs)
        ttk.Label(self, text=title, font=("Arial", 10, "bold")).pack(pady=2)
        
        self.tree = ttk.Treeview(self, columns=("username",), show="headings", selectmode="browse")
        self.tree.heading("username", text="Username")
        self.tree.column("username", width=150)
        
        self.scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.scrollbar.set)
        
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def bind_select(self, callback):
        def on_select(event):
            callback()
        self.tree.bind("<<TreeviewSelect>>", on_select)

    def update_users(self, users):
        self.tree.delete(*self.tree.get_children())
        for user in users:
            self.tree.insert("", tk.END, values=(user,))

    def get_selected_user(self):
        selected = self.tree.selection()
        if selected:
            return self.tree.item(selected[0])["values"][0]
        return None

class RoomList(ttk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        ttk.Label(self, text="Available Rooms", font=("Arial", 10, "bold")).pack(pady=2)
        
        self.tree = ttk.Treeview(self, columns=("name", "members"), show="headings", selectmode="browse")
        self.tree.heading("name", text="Room Name")
        self.tree.heading("members", text="Members")
        self.tree.column("name", width=150)
        self.tree.column("members", width=70, anchor=tk.CENTER)
        
        self.scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.scrollbar.set)
        
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def update_rooms(self, rooms):
        """rooms is a list of dicts with 'name' and 'members' count."""
        self.tree.delete(*self.tree.get_children())
        for room in rooms:
            self.tree.insert("", tk.END, values=(room['name'], room['members']))

    def get_selected_room(self):
        selected = self.tree.selection()
        if selected:
            return self.tree.item(selected[0])["values"][0]
        return None

class FileList(ttk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        ttk.Label(self, text="Room Files", font=("Arial", 10, "bold")).pack(pady=2)
        
        self.tree = ttk.Treeview(self, columns=("filename", "size", "owner"), show="headings", selectmode="browse")
        self.tree.heading("filename", text="Filename")
        self.tree.heading("size", text="Size")
        self.tree.heading("owner", text="Owner")
        self.tree.column("filename", width=200)
        self.tree.column("size", width=80)
        self.tree.column("owner", width=100)
        
        self.scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.scrollbar.set)
        
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def update_files(self, files):
        """files is a list of dicts with 'filename', 'size', 'owner'."""
        self.tree.delete(*self.tree.get_children())
        for file in files:
            self.tree.insert("", tk.END, values=(file['filename'], file['size'], file['owner']))

    def get_selected_file(self):
        selected = self.tree.selection()
        if selected:
            return self.tree.item(selected[0])["values"]
        return None

class TransferProgress(ttk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.label = ttk.Label(self, text="Idle")
        self.label.pack(side=tk.TOP, anchor=tk.W)
        
        self.progress = ttk.Progressbar(self, orient=tk.HORIZONTAL, length=200, mode='determinate')
        self.progress.pack(side=tk.TOP, fill=tk.X, expand=True, pady=2)

    def update_progress(self, filename, current, total, speed=""):
        percentage = (current / total) * 100 if total > 0 else 0
        self.progress['value'] = percentage
        status = f"Transferring {filename}: {percentage:.1f}% ({current}/{total} bytes)"
        if speed:
            status += f" - {speed}"
        self.label.config(text=status)

    def set_idle(self, message="Idle"):
        self.progress['value'] = 0
        self.label.config(text=message)
