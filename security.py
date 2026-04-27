# security.py
# Admin panel: manage users, view audit logs, role control

import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import logging
from auth import (log_audit, get_current_user,
                  add_user, get_all_users, deactivate_user,
                  hash_password)

logging.basicConfig(filename='northshore.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def get_connection():
    conn = sqlite3.connect('northshore.db')
    conn.row_factory = sqlite3.Row
    return conn


class SecurityPage:

    def __init__(self, parent, user):
        self.parent = parent
        self.user   = user
        self.build()

    def build(self):
        notebook = ttk.Notebook(self.parent)
        notebook.pack(fill='both', expand=True, padx=20, pady=10)

        self.tab_users    = tk.Frame(notebook, bg='#f0f2f5')
        self.tab_add_user = tk.Frame(notebook, bg='#f0f2f5')
        self.tab_audit    = tk.Frame(notebook, bg='#f0f2f5')

        notebook.add(self.tab_users,    text='  👥 All Users  ')
        notebook.add(self.tab_add_user, text='  ➕ Add User  ')
        notebook.add(self.tab_audit,    text='  📋 Audit Log  ')

        self.build_users_tab()
        self.build_add_user_tab()
        self.build_audit_tab()

    # ── TAB 1: ALL USERS ────────────────────────────────

    def build_users_tab(self):
        frame = self.tab_users

        btn_row = tk.Frame(frame, bg='#f0f2f5', pady=10)
        btn_row.pack(fill='x', padx=15)

        tk.Button(btn_row, text='🔄 Refresh Users',
                  command=self.load_users,
                  bg='#27ae60', fg='white',
                  relief='flat', padx=12,
                  cursor='hand2').pack(side='left', ipady=5)

        tk.Button(btn_row, text='🚫 Deactivate Selected',
                  command=self.deactivate_selected,
                  bg='#e74c3c', fg='white',
                  relief='flat', padx=12,
                  cursor='hand2').pack(side='left', padx=8, ipady=5)

        tk.Button(btn_row, text='🔑 Reset Password',
                  command=self.reset_password,
                  bg='#f39c12', fg='white',
                  relief='flat', padx=12,
                  cursor='hand2').pack(side='left', ipady=5)

        cols = ('ID','Username','Full Name','Role',
                'Email','Created At','Active')
        self.user_tree = ttk.Treeview(frame, columns=cols,
                                      show='headings', height=20)

        widths = [50, 120, 160, 130, 180, 140, 60]
        for col, w in zip(cols, widths):
            self.user_tree.heading(col, text=col)
            self.user_tree.column(col, width=w)

        self.user_tree.tag_configure('active',   background='#d5f5e3')
        self.user_tree.tag_configure('inactive', background='#fadbd8')

        scroll = ttk.Scrollbar(frame, orient='vertical',
                               command=self.user_tree.yview)
        self.user_tree.configure(yscrollcommand=scroll.set)
        self.user_tree.pack(fill='both', expand=True,
                            padx=15, pady=5, side='left')
        scroll.pack(side='right', fill='y', pady=5)

        self.load_users()

    def load_users(self):
        for row in self.user_tree.get_children():
            self.user_tree.delete(row)

        users = get_all_users()
        for u in users:
            tag = 'active' if u['is_active'] else 'inactive'
            active_str = 'Yes' if u['is_active'] else 'No'
            self.user_tree.insert('', 'end', values=(
                u['user_id'], u['username'], u['full_name'],
                u['role'], u.get('email',''),
                u['created_at'], active_str
            ), tags=(tag,))

    def deactivate_selected(self):
        selected = self.user_tree.selection()
        if not selected:
            messagebox.showwarning('Select User',
                                   'Please select a user first')
            return

        user_id  = self.user_tree.item(selected[0])['values'][0]
        username = self.user_tree.item(selected[0])['values'][1]

        if username == self.user['username']:
            messagebox.showerror('Error',
                                 "You cannot deactivate your own account!")
            return

        if messagebox.askyesno('Confirm',
                               f"Deactivate user '{username}'?"):
            success, msg = deactivate_user(user_id)
            if success:
                messagebox.showinfo('Success', msg)
                self.load_users()
            else:
                messagebox.showerror('Error', msg)

    def reset_password(self):
        selected = self.user_tree.selection()
        if not selected:
            messagebox.showwarning('Select User',
                                   'Please select a user first')
            return

        user_id  = self.user_tree.item(selected[0])['values'][0]
        username = self.user_tree.item(selected[0])['values'][1]

        # Simple popup to enter new password
        popup = tk.Toplevel()
        popup.title(f'Reset Password — {username}')
        popup.geometry('380x200')
        popup.configure(bg='white')
        popup.grab_set()

        tk.Label(popup, text=f'Set new password for {username}',
                 font=('Arial', 11, 'bold'),
                 bg='white').pack(pady=15)

        pw_var = tk.StringVar()
        tk.Entry(popup, textvariable=pw_var, show='*',
                 font=('Arial', 11), width=30,
                 relief='solid', bd=1).pack(pady=5)

        msg_lbl = tk.Label(popup, text='', bg='white',
                           font=('Arial', 10), fg='green')
        msg_lbl.pack()

        def do_reset():
            new_pw = pw_var.get().strip()
            if len(new_pw) < 6:
                msg_lbl.config(
                    text='⚠ Password must be at least 6 characters',
                    fg='red')
                return
            try:
                conn = get_connection()
                c = conn.cursor()
                c.execute('''UPDATE Users SET password=?
                             WHERE user_id=?''',
                          (hash_password(new_pw), user_id))
                conn.commit()
                conn.close()
                log_audit(self.user['username'], 'RESET_PASSWORD',
                          'Users',
                          f"Password reset for user: {username}")
                msg_lbl.config(
                    text='✅ Password reset successfully!', fg='green')
                popup.after(1500, popup.destroy)
            except Exception as e:
                msg_lbl.config(text=f'Error: {e}', fg='red')

        tk.Button(popup, text='🔑 Reset Password',
                  command=do_reset,
                  bg='#f39c12', fg='white',
                  font=('Arial', 10, 'bold'),
                  relief='flat', padx=15,
                  cursor='hand2').pack(pady=10, ipady=6)

    # ── TAB 2: ADD USER ─────────────────────────────────

    def build_add_user_tab(self):
        frame = self.tab_add_user
        card  = tk.Frame(frame, bg='white', padx=35, pady=25)
        card.pack(padx=40, pady=20, fill='both')

        tk.Label(card, text='Create New User Account',
                 font=('Arial', 14, 'bold'),
                 bg='white', fg='#1a1a2e').grid(
                     row=0, column=0, columnspan=2,
                     pady=(0,20), sticky='w')

        # Role descriptions
        desc_frame = tk.Frame(card, bg='#f0f2f5',
                              padx=15, pady=10)
        desc_frame.grid(row=1, column=0, columnspan=2,
                        sticky='ew', pady=(0,15))
        tk.Label(desc_frame,
                 text='Role Guide:  admin = full access  |  '
                      'manager = reports & fleet  |  '
                      'warehouse_staff = shipments & inventory  |  '
                      'driver = view only',
                 font=('Arial', 8), bg='#f0f2f5',
                 fg='#555555').pack()

        fields = [
            ('Username *',   'new_username'),
            ('Password *',   'new_password'),
            ('Full Name *',  'new_fullname'),
            ('Email',        'new_email'),
        ]

        self.new_user_vars = {}
        for i, (lbl, vname) in enumerate(fields):
            tk.Label(card, text=lbl, font=('Arial', 10),
                     bg='white', anchor='e', width=14).grid(
                         row=i+2, column=0, padx=(0,10),
                         pady=8, sticky='e')
            var = tk.StringVar()
            self.new_user_vars[vname] = var
            show = '*' if 'password' in vname else ''
            tk.Entry(card, textvariable=var,
                     font=('Arial', 10), width=35,
                     show=show, relief='solid', bd=1).grid(
                         row=i+2, column=1, pady=8, sticky='w')

        # Role selection
        tk.Label(card, text='Role *', font=('Arial', 10),
                 bg='white', anchor='e', width=14).grid(
                     row=6, column=0, padx=(0,10), pady=8, sticky='e')

        self.new_role_var = tk.StringVar(value='warehouse_staff')
        ttk.Combobox(card, textvariable=self.new_role_var,
                     values=['admin','manager',
                             'warehouse_staff','driver'],
                     width=33, state='readonly').grid(
                         row=6, column=1, pady=8, sticky='w')

        tk.Button(card, text='➕  Create User Account',
                  command=self.create_user,
                  font=('Arial', 11, 'bold'),
                  bg='#1a1a2e', fg='white',
                  relief='flat', padx=20,
                  cursor='hand2').grid(
                      row=7, column=0, columnspan=2,
                      pady=20, ipadx=10, ipady=10)

        self.new_user_msg = tk.Label(card, text='',
                                     font=('Arial', 10),
                                     bg='white', fg='green')
        self.new_user_msg.grid(row=8, column=0, columnspan=2)

    def create_user(self):
        username  = self.new_user_vars['new_username'].get().strip()
        password  = self.new_user_vars['new_password'].get().strip()
        full_name = self.new_user_vars['new_fullname'].get().strip()
        email     = self.new_user_vars['new_email'].get().strip()
        role      = self.new_role_var.get()

        if not username or not password or not full_name:
            self.new_user_msg.config(
                text='⚠ Username, password, and full name are required!',
                fg='red')
            return

        if len(password) < 6:
            self.new_user_msg.config(
                text='⚠ Password must be at least 6 characters!',
                fg='red')
            return

        success, msg = add_user(username, password,
                                role, full_name, email)
        if success:
            self.new_user_msg.config(text=f'✅ {msg}', fg='green')
            for var in self.new_user_vars.values():
                var.set('')
            self.load_users()
        else:
            self.new_user_msg.config(text=f'⚠ {msg}', fg='red')

    # ── TAB 3: AUDIT LOG ────────────────────────────────

    def build_audit_tab(self):
        frame = self.tab_audit

        btn_row = tk.Frame(frame, bg='#f0f2f5', pady=10)
        btn_row.pack(fill='x', padx=15)

        tk.Button(btn_row, text='🔄 Refresh',
                  command=self.load_audit_log,
                  bg='#27ae60', fg='white',
                  relief='flat', padx=12,
                  cursor='hand2').pack(side='left', ipady=5)

        # Filter by action type
        tk.Label(btn_row, text='  Filter Action:',
                 bg='#f0f2f5', font=('Arial', 10)).pack(side='left')

        self.audit_filter_var = tk.StringVar(value='ALL')
        ttk.Combobox(btn_row, textvariable=self.audit_filter_var,
                     values=['ALL','LOGIN','LOGOUT','FAILED_LOGIN',
                             'ADD_SHIPMENT','UPDATE_SHIPMENT',
                             'ADD_INVENTORY','UPDATE_STOCK',
                             'ADD_DRIVER','ADD_VEHICLE',
                             'CREATE_USER','DEACTIVATE_USER',
                             'EXPORT_REPORT','VIEW_REPORT'],
                     width=20, state='readonly').pack(
                         side='left', padx=8)
        self.audit_filter_var.trace('w',
            lambda *a: self.load_audit_log())

        cols = ('Log ID','Timestamp','Username',
                'Action','Table','Details')
        self.audit_tree = ttk.Treeview(frame, columns=cols,
                                       show='headings', height=22)

        widths = [60, 150, 110, 150, 100, 300]
        for col, w in zip(cols, widths):
            self.audit_tree.heading(col, text=col)
            self.audit_tree.column(col, width=w)

        # Highlight failed logins in red
        self.audit_tree.tag_configure(
            'failed', background='#fadbd8')
        self.audit_tree.tag_configure(
            'login',  background='#d5f5e3')

        scroll = ttk.Scrollbar(frame, orient='vertical',
                               command=self.audit_tree.yview)
        self.audit_tree.configure(yscrollcommand=scroll.set)
        self.audit_tree.pack(fill='both', expand=True,
                             padx=15, pady=5, side='left')
        scroll.pack(side='right', fill='y', pady=5)

        self.load_audit_log()

    def load_audit_log(self):
        for row in self.audit_tree.get_children():
            self.audit_tree.delete(row)

        action_filter = self.audit_filter_var.get()
        conn = get_connection()
        c = conn.cursor()

        if action_filter == 'ALL':
            c.execute('''SELECT log_id, timestamp, username,
                                action, table_name, details
                         FROM AuditLog ORDER BY log_id DESC LIMIT 500''')
        else:
            c.execute('''SELECT log_id, timestamp, username,
                                action, table_name, details
                         FROM AuditLog WHERE action=?
                         ORDER BY log_id DESC LIMIT 500''',
                      (action_filter,))

        for row in c.fetchall():
            action = row[3]
            tag = ('failed' if 'FAILED' in action
                   else 'login' if action in ('LOGIN','LOGOUT')
                   else '')
            self.audit_tree.insert('', 'end',
                                   values=tuple(row), tags=(tag,))
        conn.close()