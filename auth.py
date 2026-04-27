# auth.py - FIXED VERSION

import tkinter as tk
from tkinter import messagebox
import sqlite3
import hashlib
import logging
import secrets
from datetime import datetime

logging.basicConfig(
    filename='northshore.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# ─────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────

def get_connection():
    conn = sqlite3.connect('northshore.db')
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def log_audit(username, action, table_name, details):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO AuditLog (username, action, table_name, timestamp, details)
            VALUES (?, ?, ?, ?, ?)
        ''', (username, action, table_name,
              datetime.now().strftime('%Y-%m-%d %H:%M:%S'), details))
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"Audit log error: {e}")


def authenticate_user(username, password):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_id, username, password, role, full_name
            FROM Users
            WHERE username = ? AND is_active = 1
        ''', (username,))
        user = cursor.fetchone()
        conn.close()

        if user is None:
            logging.warning(f"Login failed - user not found: {username}")
            return None

        if user['password'] == hash_password(password):
            logging.info(f"Login success: {username}")
            log_audit(username, 'LOGIN', 'Users',
                      f"Logged in. Role: {user['role']}")
            return dict(user)
        else:
            logging.warning(f"Login failed - wrong password: {username}")
            log_audit(username, 'FAILED_LOGIN', 'Users',
                      "Wrong password")
            return None

    except Exception as e:
        logging.error(f"Auth error: {e}")
        return None


# ─────────────────────────────────────────
# SESSION
# ─────────────────────────────────────────

current_session = {
    'user_id'   : None,
    'username'  : None,
    'role'      : None,
    'full_name' : None,
    'token'     : None
}


def start_session(user_data):
    current_session['user_id']   = user_data['user_id']
    current_session['username']  = user_data['username']
    current_session['role']      = user_data['role']
    current_session['full_name'] = user_data['full_name']
    current_session['token']     = secrets.token_hex(16)


def end_session():
    username = current_session.get('username', 'Unknown')
    log_audit(username, 'LOGOUT', 'Users', "User logged out")
    for key in current_session:
        current_session[key] = None


def get_current_user():
    return current_session


def has_permission(allowed_roles):
    return current_session['role'] in allowed_roles


# ─────────────────────────────────────────
# LOGIN WINDOW — FIXED LAYOUT
# ─────────────────────────────────────────

class LoginWindow:

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Northshore Logistics Ltd — Login")

        # ── FIXED: larger window so button is always visible ──
        self.root.geometry("460x600")
        self.root.resizable(False, False)
        self.root.configure(bg='#1a1a2e')
        self.centre_window(460, 600)

        self.logged_in_user = None
        self.build_ui()

        # Press Enter to login
        self.root.bind('<Return>', lambda e: self.attempt_login())
        self.root.mainloop()

    def centre_window(self, w, h):
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x  = (sw // 2) - (w // 2)
        y  = (sh // 2) - (h // 2)
        self.root.geometry(f'{w}x{h}+{x}+{y}')

    def build_ui(self):
        """Build entire login UI in one method so nothing gets cut off"""

        # ── HEADER ──────────────────────────────────────
        header = tk.Frame(self.root, bg='#16213e', pady=20)
        header.pack(fill='x')

        tk.Label(header, text='🚛',
                 font=('Arial', 44),
                 bg='#16213e', fg='white').pack()

        tk.Label(header, text='NORTHSHORE LOGISTICS',
                 font=('Arial', 15, 'bold'),
                 bg='#16213e', fg='#e94560').pack()

        tk.Label(header, text='Centralised Management System',
                 font=('Arial', 9),
                 bg='#16213e', fg='#888888').pack(pady=(2, 0))

        # ── WHITE CARD ───────────────────────────────────
        card = tk.Frame(self.root, bg='white', padx=35, pady=25)
        card.pack(padx=30, pady=20, fill='x')

        tk.Label(card, text='Sign In',
                 font=('Arial', 16, 'bold'),
                 bg='white', fg='#1a1a2e').pack(anchor='w')

        tk.Label(card, text='Enter your credentials to continue',
                 font=('Arial', 9),
                 bg='white', fg='#999999').pack(
                     anchor='w', pady=(2, 15))

        # Username
        tk.Label(card, text='Username',
                 font=('Arial', 10, 'bold'),
                 bg='white', fg='#333333').pack(anchor='w')

        self.username_var = tk.StringVar()
        self.username_entry = tk.Entry(
            card,
            textvariable=self.username_var,
            font=('Arial', 11),
            relief='solid', bd=1,
            bg='#f5f5f5', fg='#333333')
        self.username_entry.pack(fill='x', ipady=8, pady=(4, 12))
        self.username_entry.focus()

        # Password
        tk.Label(card, text='Password',
                 font=('Arial', 10, 'bold'),
                 bg='white', fg='#333333').pack(anchor='w')

        self.password_var = tk.StringVar()
        self.password_entry = tk.Entry(
            card,
            textvariable=self.password_var,
            show='*',
            font=('Arial', 11),
            relief='solid', bd=1,
            bg='#f5f5f5', fg='#333333')
        self.password_entry.pack(fill='x', ipady=8, pady=(4, 6))

        # Show/hide password
        self.show_pw = tk.BooleanVar(value=False)
        tk.Checkbutton(
            card,
            text='Show password',
            variable=self.show_pw,
            command=self.toggle_password,
            bg='white', fg='#666666',
            font=('Arial', 9),
            activebackground='white'
        ).pack(anchor='w', pady=(0, 15))

        # ── LOGIN BUTTON — always visible ────────────────
        self.login_btn = tk.Button(
            card,
            text='🔐   LOGIN',
            command=self.attempt_login,
            font=('Arial', 12, 'bold'),
            bg='#e94560',
            fg='white',
            relief='flat',
            cursor='hand2',
            activebackground='#c73652',
            activeforeground='white'
        )
        self.login_btn.pack(fill='x', ipady=12, pady=(0, 10))

        # Status message
        self.status_lbl = tk.Label(
            card, text='',
            font=('Arial', 9),
            bg='white', fg='#e94560')
        self.status_lbl.pack()

        # ── FOOTER ──────────────────────────────────────
        footer = tk.Frame(self.root, bg='#1a1a2e', pady=8)
        footer.pack(fill='x', side='bottom')

        tk.Label(footer,
                 text='Default login:  admin  /  Admin123!',
                 font=('Arial', 8),
                 bg='#1a1a2e', fg='#e94560').pack()

        tk.Label(footer,
                 text='© 2026 Northshore Logistics Ltd',
                 font=('Arial', 8),
                 bg='#1a1a2e', fg='#444466').pack()

    def toggle_password(self):
        self.password_entry.config(
            show='' if self.show_pw.get() else '*')

    def attempt_login(self):
        username = self.username_var.get().strip()
        password = self.password_var.get().strip()

        if not username:
            self.status_lbl.config(text='⚠  Please enter your username')
            self.username_entry.focus()
            return

        if not password:
            self.status_lbl.config(text='⚠  Please enter your password')
            self.password_entry.focus()
            return

        # Disable button while checking
        self.login_btn.config(state='disabled', text='Checking...')
        self.root.update()

        user_data = authenticate_user(username, password)

        if user_data:
            start_session(user_data)
            self.status_lbl.config(
                text=f"✅ Welcome, {user_data['full_name']}!",
                fg='green')
            self.root.update()
            self.root.after(700, self.root.destroy)
        else:
            self.status_lbl.config(
                text='❌ Incorrect username or password', fg='#e94560')
            self.login_btn.config(state='normal', text='🔐   LOGIN')
            self.password_var.set('')
            self.password_entry.focus()


# ─────────────────────────────────────────
# USER MANAGEMENT FUNCTIONS
# ─────────────────────────────────────────

def add_user(username, password, role, full_name, email=''):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO Users (username, password, role, full_name, email)
            VALUES (?, ?, ?, ?, ?)
        ''', (username, hash_password(password), role, full_name, email))
        conn.commit()
        conn.close()
        log_audit(current_session['username'], 'CREATE_USER', 'Users',
                  f"Created: {username} | Role: {role}")
        return True, "User created successfully!"
    except sqlite3.IntegrityError:
        return False, "Username already exists."
    except Exception as e:
        return False, str(e)


def get_all_users():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_id, username, role, full_name,
                   email, created_at, is_active
            FROM Users ORDER BY created_at DESC
        ''')
        users = [dict(u) for u in cursor.fetchall()]
        conn.close()
        return users
    except Exception as e:
        logging.error(f"Error fetching users: {e}")
        return []


def deactivate_user(user_id):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE Users SET is_active = 0 WHERE user_id = ?',
            (user_id,))
        conn.commit()
        conn.close()
        log_audit(current_session['username'], 'DEACTIVATE_USER',
                  'Users', f"Deactivated user ID {user_id}")
        return True, "User deactivated successfully"
    except Exception as e:
        return False, str(e)


if __name__ == '__main__':
    from database import initialise_database
    initialise_database()
    LoginWindow()