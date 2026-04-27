# main.py
# This is the MAIN file that runs the entire application.
# It opens the login screen first, then shows the dashboard.

import tkinter as tk
from tkinter import ttk, messagebox
import logging
from datetime import datetime

# Import our own files
from database import initialise_database
from auth import LoginWindow, get_current_user, end_session, has_permission

logging.basicConfig(
    filename='northshore.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# ─────────────────────────────────────────────────────────
# MAIN DASHBOARD WINDOW
# ─────────────────────────────────────────────────────────

class MainDashboard:
    """
    The main window that appears after login.
    Has a sidebar menu on the left and content area on the right.
    Menu options change depending on the user's role.
    """

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Northshore Logistics Ltd — Dashboard")
        self.root.geometry("1200x700")
        self.root.configure(bg='#1a1a2e')
        self.root.state('zoomed')  # Open maximised

        # Get the logged-in user's info
        self.user = get_current_user()

        # Build the window layout
        self.build_layout()
        self.show_home()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.mainloop()

    # ── LAYOUT ──────────────────────────────────────────

    def build_layout(self):
        """Split the window into sidebar (left) and content area (right)"""

        # LEFT SIDEBAR
        self.sidebar = tk.Frame(self.root, bg='#16213e', width=230)
        self.sidebar.pack(side='left', fill='y')
        self.sidebar.pack_propagate(False)

        # RIGHT CONTENT AREA
        self.content = tk.Frame(self.root, bg='#f0f2f5')
        self.content.pack(side='right', fill='both', expand=True)

        self.build_sidebar()

    def build_sidebar(self):
        """Build the left menu sidebar"""

        # Logo area
        logo_frame = tk.Frame(self.sidebar, bg='#0f3460', pady=20)
        logo_frame.pack(fill='x')

        tk.Label(logo_frame, text='🚛', font=('Arial', 30),
                 bg='#0f3460', fg='white').pack()
        tk.Label(logo_frame, text='NORTHSHORE', font=('Arial', 12, 'bold'),
                 bg='#0f3460', fg='white').pack()
        tk.Label(logo_frame, text='LOGISTICS', font=('Arial', 12, 'bold'),
                 bg='#0f3460', fg='#e94560').pack()

        # User info
        user_frame = tk.Frame(self.sidebar, bg='#16213e', pady=12)
        user_frame.pack(fill='x')

        tk.Label(user_frame,
                 text=f"👤 {self.user['full_name']}",
                 font=('Arial', 9, 'bold'),
                 bg='#16213e', fg='white').pack()

        role_colours = {
            'admin': '#e94560',
            'manager': '#f5a623',
            'warehouse_staff': '#7ed321',
            'driver': '#4a90e2'
        }
        role_col = role_colours.get(self.user['role'], 'white')

        tk.Label(user_frame,
                 text=self.user['role'].upper().replace('_', ' '),
                 font=('Arial', 8),
                 bg='#16213e', fg=role_col).pack()

        # Divider
        tk.Frame(self.sidebar, bg='#2a2a4a', height=1).pack(fill='x', pady=5)

        # ── MENU BUTTONS ──
        # Define all menu items: (label, icon, function, allowed_roles)
        menu_items = [
            ('Home',            '🏠', self.show_home,
             ['admin','manager','warehouse_staff','driver']),
            ('Shipments',       '📦', self.show_shipments,
             ['admin','manager','warehouse_staff']),
            ('Inventory',       '🏭', self.show_inventory,
             ['admin','manager','warehouse_staff']),
            ('Fleet & Drivers', '🚗', self.show_fleet,
             ['admin','manager']),
            ('Reports',         '📊', self.show_reports,
             ['admin','manager']),
            ('Security & Users','🔒', self.show_security,
             ['admin']),
        ]

        self.menu_buttons = []
        for label, icon, command, roles in menu_items:
            # Only show buttons the user's role can access
            if self.user['role'] in roles:
                btn = tk.Button(
                    self.sidebar,
                    text=f"  {icon}  {label}",
                    font=('Arial', 10),
                    bg='#16213e', fg='#a0a0b0',
                    relief='flat',
                    anchor='w',
                    padx=15,
                    cursor='hand2',
                    activebackground='#0f3460',
                    activeforeground='white',
                    command=command
                )
                btn.pack(fill='x', pady=1, ipady=10)
                self.menu_buttons.append(btn)

        # Divider
        tk.Frame(self.sidebar, bg='#2a2a4a', height=1).pack(fill='x', pady=10)

        # Logout button at the bottom
        tk.Button(
            self.sidebar,
            text='  🚪  Logout',
            font=('Arial', 10),
            bg='#16213e', fg='#e94560',
            relief='flat',
            anchor='w',
            padx=15,
            cursor='hand2',
            command=self.logout
        ).pack(fill='x', pady=1, ipady=10, side='bottom')

        # Time display at bottom
        self.time_label = tk.Label(
            self.sidebar,
            text='',
            font=('Arial', 8),
            bg='#16213e', fg='#555577'
        )
        self.time_label.pack(side='bottom', pady=5)
        self.update_clock()

    def update_clock(self):
        """Show live clock in the sidebar"""
        now = datetime.now().strftime('%d %b %Y  %H:%M:%S')
        self.time_label.config(text=now)
        self.root.after(1000, self.update_clock)

    def clear_content(self):
        """Remove everything from the content area before loading new screen"""
        for widget in self.content.winfo_children():
            widget.destroy()

    def page_header(self, title, subtitle=''):
        """Create a consistent header for every page"""
        header = tk.Frame(self.content, bg='#1a1a2e', pady=18)
        header.pack(fill='x')
        tk.Label(header, text=title,
                 font=('Arial', 18, 'bold'),
                 bg='#1a1a2e', fg='white').pack(side='left', padx=25)
        if subtitle:
            tk.Label(header, text=subtitle,
                     font=('Arial', 10),
                     bg='#1a1a2e', fg='#888888').pack(side='left')

    # ── PAGE LOADERS ────────────────────────────────────

    def show_home(self):
        """Show the home/dashboard page"""
        self.clear_content()
        self.page_header('🏠  Dashboard', 'Welcome to Northshore Logistics')

        # Stats bar
        stats_frame = tk.Frame(self.content, bg='#f0f2f5', pady=20)
        stats_frame.pack(fill='x', padx=25)

        import sqlite3
        conn = sqlite3.connect('northshore.db')
        c = conn.cursor()

        # Get live stats from database
        stats = [
            ('📦 Total Shipments', c.execute(
                "SELECT COUNT(*) FROM Shipments").fetchone()[0], '#e94560'),
            ('✅ Delivered',        c.execute(
                "SELECT COUNT(*) FROM Shipments WHERE status='delivered'").fetchone()[0], '#27ae60'),
            ('⏳ In Transit',       c.execute(
                "SELECT COUNT(*) FROM Shipments WHERE status='in_transit'").fetchone()[0], '#f39c12'),
            ('🚗 Vehicles',         c.execute(
                "SELECT COUNT(*) FROM Vehicles").fetchone()[0], '#2980b9'),
            ('👤 Drivers',          c.execute(
                "SELECT COUNT(*) FROM Drivers").fetchone()[0], '#8e44ad'),
            ('🏭 Warehouses',       c.execute(
                "SELECT COUNT(*) FROM Warehouses").fetchone()[0], '#16a085'),
        ]
        conn.close()

        for label, value, colour in stats:
            card = tk.Frame(stats_frame, bg='white',
                            relief='flat', padx=20, pady=15)
            card.pack(side='left', padx=8, ipadx=10)

            tk.Label(card, text=str(value),
                     font=('Arial', 28, 'bold'),
                     bg='white', fg=colour).pack()
            tk.Label(card, text=label,
                     font=('Arial', 9),
                     bg='white', fg='#666666').pack()

        # Recent activity
        activity_frame = tk.Frame(self.content, bg='white',
                                  relief='flat', padx=20, pady=15)
        activity_frame.pack(fill='both', expand=True, padx=25, pady=15)

        tk.Label(activity_frame,
                 text='📋  Recent Audit Activity',
                 font=('Arial', 12, 'bold'),
                 bg='white', fg='#1a1a2e').pack(anchor='w')

        # Table of recent audit logs
        cols = ('Timestamp', 'User', 'Action', 'Details')
        tree = ttk.Treeview(activity_frame, columns=cols,
                            show='headings', height=12)
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=200)

        conn2 = sqlite3.connect('northshore.db')
        c2 = conn2.cursor()
        c2.execute('''SELECT timestamp, username, action, details
                      FROM AuditLog ORDER BY log_id DESC LIMIT 20''')
        for row in c2.fetchall():
            tree.insert('', 'end', values=row)
        conn2.close()

        scroll = ttk.Scrollbar(activity_frame,
                               orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        tree.pack(fill='both', expand=True, pady=10)
        scroll.pack(side='right', fill='y')

    def show_shipments(self):
        self.clear_content()
        self.page_header('📦  Shipment Management',
                         'Add, update, and track shipments')
        from shipments import ShipmentsPage
        ShipmentsPage(self.content, self.user)

    def show_inventory(self):
        self.clear_content()
        self.page_header('🏭  Inventory Management',
                         'Track stock levels across warehouses')
        from inventory import InventoryPage
        InventoryPage(self.content, self.user)

    def show_fleet(self):
        self.clear_content()
        self.page_header('🚗  Fleet & Driver Management',
                         'Manage vehicles and drivers')
        from fleet import FleetPage
        FleetPage(self.content, self.user)

    def show_reports(self):
        self.clear_content()
        self.page_header('📊  Reports & Analytics',
                         'Operational summaries and insights')
        from reports import ReportsPage
        ReportsPage(self.content, self.user)

    def show_security(self):
        self.clear_content()
        self.page_header('🔒  Security & User Management',
                         'Manage users, roles, and audit logs')
        from security import SecurityPage
        SecurityPage(self.content, self.user)

    # ── LOGOUT ──────────────────────────────────────────

    def logout(self):
        if messagebox.askyesno("Logout", "Are you sure you want to logout?"):
            end_session()
            self.root.destroy()
            # Restart the login screen
            app = LoginWindow()

    def on_close(self):
        if messagebox.askyesno("Exit", "Are you sure you want to exit?"):
            end_session()
            self.root.destroy()


# ─────────────────────────────────────────────────────────
# APPLICATION ENTRY POINT
# This is where the program starts when you run main.py
# ─────────────────────────────────────────────────────────

def run_app():
    # Step 1: Make sure the database and tables exist
    initialise_database()

    # Step 2: Show the login window
    login = LoginWindow()

    # Step 3: After login window closes, check if someone logged in
    user = get_current_user()
    if user['username'] is not None:
        # Step 4: Open the main dashboard
        dashboard = MainDashboard()


if __name__ == '__main__':
    run_app()