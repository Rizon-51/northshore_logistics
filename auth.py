# auth.py
# This file handles everything related to login and user authentication
# Authentication means "checking who you are before letting you in"

import tkinter as tk  # For building the GUI (windows, buttons etc.)
from tkinter import messagebox  # For showing popup messages
import sqlite3  # For talking to the database
import hashlib  # For checking encrypted passwords
import logging  # For recording login activity
import secrets  # For generating secure session tokens
from datetime import datetime  # For recording timestamps


# ──────────────────────────────────────────────
# HELPER FUNCTIONS (tools used by the login system)
# ──────────────────────────────────────────────

def get_connection():
    """Open a connection to the database"""
    conn = sqlite3.connect('northshore.db')
    conn.row_factory = sqlite3.Row  # Lets us access columns by name e.g. row['username']
    return conn


def hash_password(password):
    """
    Encrypt a password using SHA-256.
    SHA-256 turns any text into a fixed string of letters/numbers.
    Example: 'Admin123!' becomes 'a3f1c9...' — impossible to reverse.
    """
    return hashlib.sha256(password.encode()).hexdigest()


def log_audit(username, action, table_name, details):
    """
    Record every important action into the AuditLog table.
    This is required by the brief for security monitoring.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
                       INSERT INTO AuditLog (username, action, table_name, timestamp, details)
                       VALUES (?, ?, ?, ?, ?)
                       ''', (username, action, table_name, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), details))
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"Audit log error: {e}")


def authenticate_user(username, password):
    """
    Check if the username and password are correct.
    Returns the user's data if correct, or None if wrong.

    How it works:
    1. We take the password the user typed
    2. We encrypt it (hash it)
    3. We compare that encrypted version with what's stored in the database
    4. If they match → login success!
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Look for a user with this username who is active (not deleted)
        cursor.execute('''
                       SELECT user_id, username, password, role, full_name
                       FROM Users
                       WHERE username = ?
                         AND is_active = 1
                       ''', (username,))

        user = cursor.fetchone()  # fetchone() gets the first matching row
        conn.close()

        if user is None:
            # No user found with that username
            logging.warning(f"Failed login attempt - username not found: {username}")
            return None

        # Compare the hashed version of what they typed with what's in the database
        if user['password'] == hash_password(password):
            # ✅ Password matches! Login successful
            logging.info(f"Successful login: {username} | Role: {user['role']}")
            log_audit(username, 'LOGIN', 'Users', f"User logged in successfully. Role: {user['role']}")
            return dict(user)  # Return user info as a dictionary
        else:
            # ❌ Wrong password
            logging.warning(f"Failed login - wrong password for username: {username}")
            log_audit(username, 'FAILED_LOGIN', 'Users', "Incorrect password entered")
            return None

    except Exception as e:
        logging.error(f"Authentication error: {e}")
        return None


# ──────────────────────────────────────────────
# SESSION MANAGEMENT
# A "session" remembers who is logged in while the app is running
# ──────────────────────────────────────────────

# This dictionary stores the current logged-in user's info
# It's like a temporary name badge while you're working
current_session = {
    'user_id': None,
    'username': None,
    'role': None,
    'full_name': None,
    'token': None  # A unique security code for this session
}


def start_session(user_data):
    """
    Save the logged-in user's details into the session.
    Also generates a unique security token for this session.
    """
    current_session['user_id'] = user_data['user_id']
    current_session['username'] = user_data['username']
    current_session['role'] = user_data['role']
    current_session['full_name'] = user_data['full_name']
    current_session['token'] = secrets.token_hex(16)  # Random 32-character token


def end_session():
    """
    Clear the session when user logs out.
    Like handing back your name badge when you leave.
    """
    username = current_session.get('username', 'Unknown')
    log_audit(username, 'LOGOUT', 'Users', "User logged out")
    for key in current_session:
        current_session[key] = None


def get_current_user():
    """Return the currently logged-in user's info"""
    return current_session


def has_permission(allowed_roles):
    """
    Check if the current user has permission to do something.

    Example usage:
        has_permission(['admin', 'manager']) → True or False

    This is Role-Based Access Control (RBAC) — required by the brief.
    """
    return current_session['role'] in allowed_roles


# ──────────────────────────────────────────────
# LOGIN WINDOW (The GUI Screen)
# ──────────────────────────────────────────────

class LoginWindow:
    """
    This class builds the Login Screen window.
    A 'class' is like a blueprint — it defines how the window looks and works.
    """

    def __init__(self):
        """
        __init__ runs automatically when we create a LoginWindow.
        This is where we build all the visual elements.
        """

        # ── Create the main window ──
        self.root = tk.Tk()  # Create the window
        self.root.title("Northshore Logistics Ltd — Login")  # Window title
        self.root.geometry("480x560")  # Width x Height in pixels
        self.root.resizable(False, False)  # Prevent resizing
        self.root.configure(bg='#1a1a2e')  # Dark blue background

        # Centre the window on the screen
        self.centre_window(480, 560)

        # Store the result of login (will be set to user data if successful)
        self.logged_in_user = None

        # ── Build all the visual parts ──
        self.build_header()
        self.build_login_form()
        self.build_footer()

        # ── Keyboard shortcut: press Enter to login ──
        self.root.bind('<Return>', lambda event: self.attempt_login())

        # ── Start the window ──
        self.root.mainloop()

    def centre_window(self, width, height):
        """Position the window in the middle of the screen"""
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def build_header(self):
        """Build the top section with the company logo/title"""

        # Outer frame for the header area
        header_frame = tk.Frame(self.root, bg='#16213e', pady=25)
        header_frame.pack(fill='x')

        # Company icon (using text emoji as a simple icon)
        tk.Label(
            header_frame,
            text='🚛',
            font=('Arial', 48),
            bg='#16213e',
            fg='white'
        ).pack()

        # Company name
        tk.Label(
            header_frame,
            text='NORTHSHORE LOGISTICS',
            font=('Arial', 16, 'bold'),
            bg='#16213e',
            fg='#e94560'  # Red accent colour
        ).pack()

        # Subtitle
        tk.Label(
            header_frame,
            text='Centralised Management System',
            font=('Arial', 10),
            bg='#16213e',
            fg='#a0a0a0'  # Grey colour
        ).pack(pady=(2, 0))

    def build_login_form(self):
        """Build the login form with username and password fields"""

        # White card in the middle
        card = tk.Frame(
            self.root,
            bg='#ffffff',
            padx=40,
            pady=30,
            relief='flat'
        )
        card.pack(padx=40, pady=25, fill='both')

        # ── Title on the card ──
        tk.Label(
            card,
            text='Sign In',
            font=('Arial', 18, 'bold'),
            bg='white',
            fg='#1a1a2e'
        ).pack(anchor='w')

        tk.Label(
            card,
            text='Enter your credentials to continue',
            font=('Arial', 9),
            bg='white',
            fg='#888888'
        ).pack(anchor='w', pady=(2, 20))

        # ── Username Field ──
        tk.Label(
            card,
            text='Username',
            font=('Arial', 10, 'bold'),
            bg='white',
            fg='#333333'
        ).pack(anchor='w')

        # The box where user types their username
        self.username_var = tk.StringVar()  # Variable that holds what's typed
        username_entry = tk.Entry(
            card,
            textvariable=self.username_var,
            font=('Arial', 11),
            relief='solid',
            bd=1,
            fg='#333333',
            bg='#f5f5f5'
        )
        username_entry.pack(fill='x', pady=(4, 16), ipady=8)
        username_entry.focus()  # Cursor starts here automatically

        # ── Password Field ──
        tk.Label(
            card,
            text='Password',
            font=('Arial', 10, 'bold'),
            bg='white',
            fg='#333333'
        ).pack(anchor='w')

        # Password entry - show='*' means characters appear as stars
        self.password_var = tk.StringVar()
        self.password_entry = tk.Entry(
            card,
            textvariable=self.password_var,
            show='*',  # Hide password characters
            font=('Arial', 11),
            relief='solid',
            bd=1,
            fg='#333333',
            bg='#f5f5f5'
        )
        self.password_entry.pack(fill='x', pady=(4, 8), ipady=8)

        # ── Show/Hide Password Toggle ──
        self.show_pw = tk.BooleanVar(value=False)
        tk.Checkbutton(
            card,
            text='Show password',
            variable=self.show_pw,
            command=self.toggle_password,
            bg='white',
            fg='#555555',
            font=('Arial', 9),
            activebackground='white'
        ).pack(anchor='w', pady=(0, 20))

        # ── Login Button ──
        self.login_btn = tk.Button(
            card,
            text='LOGIN  →',
            command=self.attempt_login,
            font=('Arial', 12, 'bold'),
            bg='#e94560',  # Red button
            fg='white',
            relief='flat',
            cursor='hand2',  # Cursor changes to a hand when hovering
            activebackground='#c73652',
            activeforeground='white'
        )
        self.login_btn.pack(fill='x', ipady=10)

        # ── Status message (shows errors) ──
        self.status_label = tk.Label(
            card,
            text='',
            font=('Arial', 9),
            bg='white',
            fg='#e94560'
        )
        self.status_label.pack(pady=(12, 0))

        # ── Role information ──
        tk.Label(
            card,
            text='Roles: admin | manager | warehouse_staff | driver',
            font=('Arial', 8),
            bg='white',
            fg='#aaaaaa'
        ).pack(pady=(8, 0))

    def build_footer(self):
        """Build the bottom bar"""
        footer = tk.Frame(self.root, bg='#1a1a2e', pady=10)
        footer.pack(fill='x', side='bottom')

        tk.Label(
            footer,
            text='© 2026 Northshore Logistics Ltd  |  CPS4004 Assessment',
            font=('Arial', 8),
            bg='#1a1a2e',
            fg='#555555'
        ).pack()

    def toggle_password(self):
        """Show or hide the password when checkbox is ticked"""
        if self.show_pw.get():
            self.password_entry.config(show='')  # Show plain text
        else:
            self.password_entry.config(show='*')  # Hide with stars

    def attempt_login(self):
        """
        This runs when the user clicks LOGIN.
        Steps:
        1. Get what was typed in the fields
        2. Check they're not empty
        3. Call authenticate_user() to check the database
        4. If correct → open the main app
        5. If wrong   → show error message
        """

        # Get the typed values and remove any accidental spaces
        username = self.username_var.get().strip()
        password = self.password_var.get().strip()

        # ── Validation: make sure fields are not empty ──
        if not username:
            self.show_status("⚠ Please enter your username")
            return

        if not password:
            self.show_status("⚠ Please enter your password")
            return

        # ── Disable button while checking (prevents double clicks) ──
        self.login_btn.config(state='disabled', text='Checking...')
        self.root.update()  # Refresh the window to show the change

        # ── Try to authenticate ──
        user_data = authenticate_user(username, password)

        if user_data:
            # ✅ Login successful!
            start_session(user_data)  # Save user to session

            # Show a brief welcome message
            self.show_status(f"✅ Welcome, {user_data['full_name']}!")
            self.root.update()
            self.root.after(800, self.open_main_app)  # Wait 0.8 seconds then open app

        else:
            # ❌ Login failed
            self.show_status("❌ Incorrect username or password")
            self.login_btn.config(state='normal', text='LOGIN  →')  # Re-enable button
            self.password_var.set('')  # Clear the password field
            self.password_entry.focus()  # Move cursor back to password field

    def show_status(self, message):
        """Update the status message shown below the login button"""
        self.status_label.config(text=message)
        self.root.update()

    def open_main_app(self):
        """Close the login window and open the main dashboard"""
        self.root.destroy()  # Close the login window
        # We will import and open the main dashboard here in the next step
        # For now, let's show a confirmation
        import tkinter as tk
        from tkinter import messagebox
        user = get_current_user()
        messagebox.showinfo(
            "Login Successful",
            f"Welcome {user['full_name']}!\n\nRole: {user['role'].upper()}\n\nMain dashboard coming next!"
        )


# ──────────────────────────────────────────────
# USER MANAGEMENT FUNCTIONS
# (Used by admin to add new users)
# ──────────────────────────────────────────────

def add_user(username, password, role, full_name, email=''):
    """
    Add a new user to the database.
    Only admins can do this (checked in the main app).
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        hashed_pw = hash_password(password)

        cursor.execute('''
                       INSERT INTO Users (username, password, role, full_name, email)
                       VALUES (?, ?, ?, ?, ?)
                       ''', (username, hashed_pw, role, full_name, email))

        conn.commit()
        conn.close()

        # Record this action in the audit log
        log_audit(
            current_session['username'],
            'CREATE_USER',
            'Users',
            f"New user created: {username} | Role: {role}"
        )
        logging.info(f"New user created: {username} | Role: {role}")
        return True, "User created successfully!"

    except sqlite3.IntegrityError:
        return False, "Username already exists. Please choose a different username."
    except Exception as e:
        logging.error(f"Error creating user: {e}")
        return False, f"Error: {str(e)}"


def get_all_users():
    """Get a list of all users — for the admin panel"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
                       SELECT user_id, username, role, full_name, email, created_at, is_active
                       FROM Users
                       ORDER BY created_at DESC
                       ''')
        users = cursor.fetchall()
        conn.close()
        return [dict(u) for u in users]
    except Exception as e:
        logging.error(f"Error fetching users: {e}")
        return []


def deactivate_user(user_id):
    """
    Deactivate a user (they can't login anymore).
    We don't delete users — we just mark them as inactive.
    This is better for audit trails.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
                       UPDATE Users
                       SET is_active = 0
                       WHERE user_id = ?
                       ''', (user_id,))
        conn.commit()
        conn.close()

        log_audit(
            current_session['username'],
            'DEACTIVATE_USER',
            'Users',
            f"User ID {user_id} deactivated"
        )
        return True, "User deactivated successfully"
    except Exception as e:
        return False, str(e)


# ──────────────────────────────────────────────
# RUN THE LOGIN WINDOW
# ──────────────────────────────────────────────

if __name__ == '__main__':
    # First make sure the database exists
    from database import initialise_database

    initialise_database()

    # Then open the login window
    app = LoginWindow()