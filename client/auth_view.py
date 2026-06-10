import tkinter as tk
from tkinter import ttk, messagebox

class AuthView(ttk.Frame):
    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, **kwargs)
        self.app = app
        
        self.setup_ui()

    def setup_ui(self):
        # Center frame
        center_frame = ttk.Frame(self)
        center_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
        ttk.Label(center_frame, text="NetCourier", font=("Arial", 24, "bold")).grid(row=0, column=0, columnspan=2, pady=20)
        
        ttk.Label(center_frame, text="Username:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.username_entry = ttk.Entry(center_frame, width=30)
        self.username_entry.grid(row=1, column=1, pady=5, padx=5)
        
        ttk.Label(center_frame, text="Password:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.password_entry = ttk.Entry(center_frame, show="*", width=30)
        self.password_entry.grid(row=2, column=1, pady=5, padx=5)
        
        btn_frame = ttk.Frame(center_frame)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=20)
        
        self.login_btn = ttk.Button(btn_frame, text="Login", command=self.on_login)
        self.login_btn.pack(side=tk.LEFT, padx=5)
        
        self.register_btn = ttk.Button(btn_frame, text="Register", command=self.on_register)
        self.register_btn.pack(side=tk.LEFT, padx=5)

    def on_login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        if not username or not password:
            messagebox.showerror("Error", "Please enter both username and password")
            return
        
        self.app.logger.info(f"Attempting login for user: {username}")
        # In a real implementation, this would start a background thread to talk to Gateway
        # For now, we simulate success
        self.app.on_login_success(username, "dummy_token")

    def on_register(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        if not username or not password:
            messagebox.showerror("Error", "Please enter both username and password")
            return
        
        self.app.logger.info(f"Attempting registration for user: {username}")
        # Simulate registration success
        messagebox.showinfo("Success", "Registration successful! You can now login.")
