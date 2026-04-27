# shipments.py
# Handles all shipment operations:
# adding, updating, tracking, incidents, financial info, reports

import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import logging
from datetime import datetime
from auth import log_audit, get_current_user, has_permission

logging.basicConfig(filename='northshore.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def get_connection():
    conn = sqlite3.connect('northshore.db')
    conn.row_factory = sqlite3.Row
    return conn


class ShipmentsPage:
    """Full shipment management screen"""

    def __init__(self, parent, user):
        self.parent = parent
        self.user   = user
        self.build()

    def build(self):
        # Tab control — like tabs in a web browser
        notebook = ttk.Notebook(self.parent)
        notebook.pack(fill='both', expand=True, padx=20, pady=10)

        # Create each tab
        self.tab_list     = tk.Frame(notebook, bg='#f0f2f5')
        self.tab_add      = tk.Frame(notebook, bg='#f0f2f5')
        self.tab_update   = tk.Frame(notebook, bg='#f0f2f5')
        self.tab_incident = tk.Frame(notebook, bg='#f0f2f5')
        self.tab_finance  = tk.Frame(notebook, bg='#f0f2f5')

        notebook.add(self.tab_list,     text='  📋 All Shipments  ')
        notebook.add(self.tab_add,      text='  ➕ Add Shipment  ')
        notebook.add(self.tab_update,   text='  ✏️ Update Delivery  ')
        notebook.add(self.tab_incident, text='  ⚠️ Incidents  ')
        notebook.add(self.tab_finance,  text='  💰 Financials  ')

        self.build_list_tab()
        self.build_add_tab()
        self.build_update_tab()
        self.build_incident_tab()
        self.build_finance_tab()

    # ── TAB 1: LIST ALL SHIPMENTS ──────────────────────

    def build_list_tab(self):
        frame = self.tab_list

        # Search bar
        search_frame = tk.Frame(frame, bg='#f0f2f5', pady=10)
        search_frame.pack(fill='x', padx=15)

        tk.Label(search_frame, text='Search:',
                 bg='#f0f2f5', font=('Arial', 10)).pack(side='left')

        self.search_var = tk.StringVar()
        tk.Entry(search_frame, textvariable=self.search_var,
                 font=('Arial', 10), width=30).pack(side='left', padx=8)

        tk.Button(search_frame, text='🔍 Search',
                  command=self.search_shipments,
                  bg='#1a1a2e', fg='white',
                  relief='flat', padx=10).pack(side='left')

        tk.Button(search_frame, text='🔄 Refresh',
                  command=self.load_shipments,
                  bg='#27ae60', fg='white',
                  relief='flat', padx=10).pack(side='left', padx=5)

        # Filter by status
        tk.Label(search_frame, text='  Filter:',
                 bg='#f0f2f5', font=('Arial', 10)).pack(side='left')

        self.filter_var = tk.StringVar(value='all')
        for val, lbl in [('all','All'),('in_transit','In Transit'),
                         ('delivered','Delivered'),('delayed','Delayed'),
                         ('returned','Returned')]:
            tk.Radiobutton(search_frame, text=lbl, variable=self.filter_var,
                           value=val, bg='#f0f2f5',
                           command=self.load_shipments).pack(side='left', padx=3)

        # Shipments table
        cols = ('ID','Order No','Sender','Receiver',
                'Status','Driver','Delivery Date','Cost')
        self.ship_tree = ttk.Treeview(frame, columns=cols,
                                      show='headings', height=18)

        widths = [50, 100, 130, 130, 90, 110, 110, 80]
        for col, w in zip(cols, widths):
            self.ship_tree.heading(col, text=col)
            self.ship_tree.column(col, width=w)

        # Colour rows by status
        self.ship_tree.tag_configure('delivered', background='#d5f5e3')
        self.ship_tree.tag_configure('delayed',   background='#fdebd0')
        self.ship_tree.tag_configure('returned',  background='#fadbd8')
        self.ship_tree.tag_configure('in_transit',background='#d6eaf8')

        scroll = ttk.Scrollbar(frame, orient='vertical',
                               command=self.ship_tree.yview)
        self.ship_tree.configure(yscrollcommand=scroll.set)
        self.ship_tree.pack(fill='both', expand=True,
                            padx=15, pady=5, side='left')
        scroll.pack(side='right', fill='y', pady=5)

        self.load_shipments()

    def load_shipments(self):
        """Load shipments from database into the table"""
        for row in self.ship_tree.get_children():
            self.ship_tree.delete(row)

        conn = get_connection()
        c = conn.cursor()

        status_filter = self.filter_var.get()
        if status_filter == 'all':
            c.execute('''
                SELECT s.shipment_id, s.order_number, s.sender_name,
                       s.receiver_name, s.status,
                       COALESCE(d.full_name,'Unassigned'),
                       COALESCE(s.delivery_date,'TBD'),
                       COALESCE(s.transport_cost,0)
                FROM Shipments s
                LEFT JOIN Drivers d ON s.driver_id = d.driver_id
                ORDER BY s.shipment_id DESC
            ''')
        else:
            c.execute('''
                SELECT s.shipment_id, s.order_number, s.sender_name,
                       s.receiver_name, s.status,
                       COALESCE(d.full_name,'Unassigned'),
                       COALESCE(s.delivery_date,'TBD'),
                       COALESCE(s.transport_cost,0)
                FROM Shipments s
                LEFT JOIN Drivers d ON s.driver_id = d.driver_id
                WHERE s.status = ?
                ORDER BY s.shipment_id DESC
            ''', (status_filter,))

        for row in c.fetchall():
            tag = row[4]  # status column
            self.ship_tree.insert('', 'end', values=tuple(row), tags=(tag,))

        conn.close()

    def search_shipments(self):
        """Search shipments by order number or name"""
        term = self.search_var.get().strip()
        if not term:
            self.load_shipments()
            return

        for row in self.ship_tree.get_children():
            self.ship_tree.delete(row)

        conn = get_connection()
        c = conn.cursor()
        like = f'%{term}%'
        c.execute('''
            SELECT s.shipment_id, s.order_number, s.sender_name,
                   s.receiver_name, s.status,
                   COALESCE(d.full_name,'Unassigned'),
                   COALESCE(s.delivery_date,'TBD'),
                   COALESCE(s.transport_cost,0)
            FROM Shipments s
            LEFT JOIN Drivers d ON s.driver_id = d.driver_id
            WHERE s.order_number LIKE ?
               OR s.sender_name  LIKE ?
               OR s.receiver_name LIKE ?
        ''', (like, like, like))

        for row in c.fetchall():
            self.ship_tree.insert('', 'end', values=tuple(row),
                                  tags=(row[4],))
        conn.close()

    # ── TAB 2: ADD NEW SHIPMENT ─────────────────────────

    def build_add_tab(self):
        frame = self.tab_add

        canvas = tk.Canvas(frame, bg='#f0f2f5')
        scrollbar = ttk.Scrollbar(frame, orient='vertical',
                                  command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg='#f0f2f5')

        scroll_frame.bind('<Configure>',
            lambda e: canvas.configure(
                scrollregion=canvas.bbox('all')))

        canvas.create_window((0, 0), window=scroll_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # White card
        card = tk.Frame(scroll_frame, bg='white', padx=30, pady=20)
        card.pack(padx=20, pady=15, fill='both')

        tk.Label(card, text='Add New Shipment Record',
                 font=('Arial', 14, 'bold'),
                 bg='white', fg='#1a1a2e').grid(
                     row=0, column=0, columnspan=2,
                     pady=(0,15), sticky='w')

        # Field definitions: (label, variable_name, row)
        fields = [
            ('Order Number *',     'order_number',     1),
            ('Sender Name *',      'sender_name',      2),
            ('Sender Address',     'sender_address',   3),
            ('Receiver Name *',    'receiver_name',    4),
            ('Receiver Address',   'receiver_address', 5),
            ('Item Description',   'item_description', 6),
            ('Weight (kg)',        'weight_kg',        7),
            ('Transport Cost (£)', 'transport_cost',   8),
            ('Route Details',      'route_details',    9),
        ]

        self.add_vars = {}
        for label, var_name, row in fields:
            tk.Label(card, text=label, font=('Arial', 10),
                     bg='white', fg='#333333',
                     anchor='e', width=18).grid(
                         row=row, column=0, padx=(0,10),
                         pady=6, sticky='e')

            var = tk.StringVar()
            self.add_vars[var_name] = var
            tk.Entry(card, textvariable=var, font=('Arial', 10),
                     width=35, relief='solid', bd=1).grid(
                         row=row, column=1, pady=6, sticky='w')

        # Status dropdown
        tk.Label(card, text='Status *', font=('Arial', 10),
                 bg='white', anchor='e', width=18).grid(
                     row=10, column=0, padx=(0,10), pady=6, sticky='e')

        self.add_status_var = tk.StringVar(value='in_transit')
        ttk.Combobox(card, textvariable=self.add_status_var,
                     values=['in_transit','delivered',
                             'delayed','returned'],
                     width=33, state='readonly').grid(
                         row=10, column=1, pady=6, sticky='w')

        # Payment status dropdown
        tk.Label(card, text='Payment Status', font=('Arial', 10),
                 bg='white', anchor='e', width=18).grid(
                     row=11, column=0, padx=(0,10), pady=6, sticky='e')

        self.add_payment_var = tk.StringVar(value='unpaid')
        ttk.Combobox(card, textvariable=self.add_payment_var,
                     values=['unpaid','paid','partial'],
                     width=33, state='readonly').grid(
                         row=11, column=1, pady=6, sticky='w')

        # Warehouse dropdown
        tk.Label(card, text='Warehouse', font=('Arial', 10),
                 bg='white', anchor='e', width=18).grid(
                     row=12, column=0, padx=(0,10), pady=6, sticky='e')

        self.warehouse_map = self.get_warehouses()
        self.add_warehouse_var = tk.StringVar()
        ttk.Combobox(card, textvariable=self.add_warehouse_var,
                     values=list(self.warehouse_map.keys()),
                     width=33, state='readonly').grid(
                         row=12, column=1, pady=6, sticky='w')

        # Submit button
        tk.Button(card, text='➕  Add Shipment',
                  command=self.add_shipment,
                  font=('Arial', 11, 'bold'),
                  bg='#e94560', fg='white',
                  relief='flat', padx=20,
                  cursor='hand2').grid(
                      row=13, column=0, columnspan=2,
                      pady=20, ipadx=10, ipady=8)

        self.add_status_lbl = tk.Label(card, text='',
                                       font=('Arial', 10),
                                       bg='white', fg='green')
        self.add_status_lbl.grid(row=14, column=0,
                                 columnspan=2, pady=5)

    def get_warehouses(self):
        """Return dict of {warehouse_name: warehouse_id}"""
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT warehouse_id, name FROM Warehouses")
        result = {row['name']: row['warehouse_id'] for row in c.fetchall()}
        conn.close()
        return result

    def get_drivers(self):
        """Return dict of {driver_name: driver_id}"""
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT driver_id, full_name FROM Drivers")
        result = {row['full_name']: row['driver_id'] for row in c.fetchall()}
        conn.close()
        return result

    def add_shipment(self):
        """Save a new shipment to the database"""
        # Get all values
        order_no  = self.add_vars['order_number'].get().strip()
        sender    = self.add_vars['sender_name'].get().strip()
        receiver  = self.add_vars['receiver_name'].get().strip()

        # Basic validation
        if not order_no or not sender or not receiver:
            self.add_status_lbl.config(
                text='⚠ Order number, sender and receiver are required!',
                fg='red')
            return

        try:
            cost   = float(self.add_vars['transport_cost'].get() or 0)
            weight = float(self.add_vars['weight_kg'].get() or 0)
        except ValueError:
            self.add_status_lbl.config(
                text='⚠ Cost and weight must be numbers!', fg='red')
            return

        wh_name = self.add_warehouse_var.get()
        wh_id   = self.warehouse_map.get(wh_name)

        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute('''
                INSERT INTO Shipments
                (order_number, sender_name, sender_address,
                 receiver_name, receiver_address, item_description,
                 weight_kg, status, warehouse_id, route_details,
                 transport_cost, payment_status)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            ''', (
                order_no,
                sender,
                self.add_vars['sender_address'].get(),
                receiver,
                self.add_vars['receiver_address'].get(),
                self.add_vars['item_description'].get(),
                weight,
                self.add_status_var.get(),
                wh_id,
                self.add_vars['route_details'].get(),
                cost,
                self.add_payment_var.get()
            ))
            conn.commit()
            conn.close()

            log_audit(self.user['username'], 'ADD_SHIPMENT',
                      'Shipments', f"Added shipment: {order_no}")

            self.add_status_lbl.config(
                text=f'✅ Shipment {order_no} added successfully!',
                fg='green')

            # Clear all fields
            for var in self.add_vars.values():
                var.set('')
            self.load_shipments()

        except sqlite3.IntegrityError:
            self.add_status_lbl.config(
                text='⚠ Order number already exists!', fg='red')
        except Exception as e:
            self.add_status_lbl.config(text=f'Error: {e}', fg='red')

    # ── TAB 3: UPDATE DELIVERY ──────────────────────────

    def build_update_tab(self):
        frame = self.tab_update

        card = tk.Frame(frame, bg='white', padx=30, pady=20)
        card.pack(padx=20, pady=15, fill='both')

        tk.Label(card, text='Update Delivery Information',
                 font=('Arial', 14, 'bold'),
                 bg='white', fg='#1a1a2e').grid(
                     row=0, column=0, columnspan=2,
                     pady=(0,15), sticky='w')

        # Shipment ID to update
        tk.Label(card, text='Shipment ID *',
                 font=('Arial', 10), bg='white',
                 anchor='e', width=18).grid(
                     row=1, column=0, padx=(0,10), pady=8, sticky='e')

        self.upd_id_var = tk.StringVar()
        tk.Entry(card, textvariable=self.upd_id_var,
                 font=('Arial', 10), width=20,
                 relief='solid', bd=1).grid(
                     row=1, column=1, pady=8, sticky='w')

        tk.Button(card, text='🔍 Load Shipment',
                  command=self.load_shipment_for_update,
                  bg='#1a1a2e', fg='white',
                  relief='flat', padx=10).grid(
                      row=1, column=2, padx=10)

        # Update fields
        update_fields = [
            ('New Status',      'upd_status'),
            ('Delivery Date\n(YYYY-MM-DD)', 'upd_date'),
            ('Route Details',   'upd_route'),
            ('Payment Status',  'upd_payment'),
        ]

        self.upd_vars = {}
        for i, (label, var_name) in enumerate(update_fields):
            tk.Label(card, text=label, font=('Arial', 10),
                     bg='white', anchor='e', width=18).grid(
                         row=i+2, column=0, padx=(0,10),
                         pady=8, sticky='e')
            var = tk.StringVar()
            self.upd_vars[var_name] = var

            if 'status' in var_name.lower() or 'payment' in var_name.lower():
                values = (['in_transit','delivered','delayed','returned']
                          if 'status' == var_name.lower()[-6:]
                          else ['unpaid','paid','partial'])
                ttk.Combobox(card, textvariable=var,
                             values=values, width=33,
                             state='readonly').grid(
                                 row=i+2, column=1, pady=8, sticky='w')
            else:
                tk.Entry(card, textvariable=var,
                         font=('Arial', 10), width=35,
                         relief='solid', bd=1).grid(
                             row=i+2, column=1, pady=8, sticky='w')

        # Assign driver
        tk.Label(card, text='Assign Driver',
                 font=('Arial', 10), bg='white',
                 anchor='e', width=18).grid(
                     row=6, column=0, padx=(0,10), pady=8, sticky='e')

        self.driver_map = self.get_drivers()
        self.upd_driver_var = tk.StringVar()
        ttk.Combobox(card, textvariable=self.upd_driver_var,
                     values=list(self.driver_map.keys()),
                     width=33, state='readonly').grid(
                         row=6, column=1, pady=8, sticky='w')

        tk.Button(card, text='💾  Save Update',
                  command=self.update_shipment,
                  font=('Arial', 11, 'bold'),
                  bg='#27ae60', fg='white',
                  relief='flat', padx=20,
                  cursor='hand2').grid(
                      row=7, column=0, columnspan=2,
                      pady=20, ipadx=10, ipady=8)

        self.upd_status_lbl = tk.Label(card, text='',
                                       font=('Arial', 10),
                                       bg='white', fg='green')
        self.upd_status_lbl.grid(row=8, column=0,
                                 columnspan=2, pady=5)

    def load_shipment_for_update(self):
        """Load a shipment's current data into the update fields"""
        ship_id = self.upd_id_var.get().strip()
        if not ship_id:
            messagebox.showwarning('Input needed',
                                   'Please enter a Shipment ID')
            return
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute('SELECT * FROM Shipments WHERE shipment_id=?',
                      (ship_id,))
            row = c.fetchone()
            conn.close()

            if row:
                self.upd_vars['upd_status'].set(row['status'] or '')
                self.upd_vars['upd_date'].set(row['delivery_date'] or '')
                self.upd_vars['upd_route'].set(row['route_details'] or '')
                self.upd_vars['upd_payment'].set(row['payment_status'] or '')
                self.upd_status_lbl.config(
                    text=f'✅ Loaded shipment #{ship_id}', fg='green')
            else:
                self.upd_status_lbl.config(
                    text='⚠ Shipment not found', fg='red')
        except Exception as e:
            self.upd_status_lbl.config(text=f'Error: {e}', fg='red')

    def update_shipment(self):
        """Save updated shipment info to the database"""
        ship_id = self.upd_id_var.get().strip()
        if not ship_id:
            self.upd_status_lbl.config(
                text='⚠ Please enter a Shipment ID first', fg='red')
            return

        driver_name = self.upd_driver_var.get()
        driver_id   = self.driver_map.get(driver_name)

        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute('''
                UPDATE Shipments
                SET status=?, delivery_date=?, route_details=?,
                    payment_status=?, driver_id=?
                WHERE shipment_id=?
            ''', (
                self.upd_vars['upd_status'].get(),
                self.upd_vars['upd_date'].get(),
                self.upd_vars['upd_route'].get(),
                self.upd_vars['upd_payment'].get(),
                driver_id,
                ship_id
            ))
            conn.commit()
            conn.close()

            log_audit(self.user['username'], 'UPDATE_SHIPMENT',
                      'Shipments',
                      f"Updated shipment ID: {ship_id}")

            self.upd_status_lbl.config(
                text=f'✅ Shipment #{ship_id} updated!', fg='green')
            self.load_shipments()

        except Exception as e:
            self.upd_status_lbl.config(text=f'Error: {e}', fg='red')

    # ── TAB 4: INCIDENTS ────────────────────────────────

    def build_incident_tab(self):
        frame = self.tab_incident

        # Top: log new incident
        top = tk.Frame(frame, bg='white', padx=25, pady=15)
        top.pack(fill='x', padx=20, pady=10)

        tk.Label(top, text='Log New Incident',
                 font=('Arial', 13, 'bold'),
                 bg='white', fg='#1a1a2e').grid(
                     row=0, column=0, columnspan=2,
                     sticky='w', pady=(0,10))

        labels_vars = [
            ('Shipment ID *', 'inc_ship_id'),
            ('Description *', 'inc_desc'),
        ]

        self.inc_vars = {}
        for i, (lbl, vname) in enumerate(labels_vars):
            tk.Label(top, text=lbl, font=('Arial', 10),
                     bg='white', anchor='e', width=16).grid(
                         row=i+1, column=0, padx=(0,10),
                         pady=6, sticky='e')
            var = tk.StringVar()
            self.inc_vars[vname] = var
            tk.Entry(top, textvariable=var, font=('Arial', 10),
                     width=40, relief='solid', bd=1).grid(
                         row=i+1, column=1, pady=6, sticky='w')

        tk.Label(top, text='Incident Type *',
                 font=('Arial', 10), bg='white',
                 anchor='e', width=16).grid(
                     row=3, column=0, padx=(0,10), pady=6, sticky='e')

        self.inc_type_var = tk.StringVar(value='delay')
        ttk.Combobox(top, textvariable=self.inc_type_var,
                     values=['delay','route_change',
                             'damaged','failed_delivery'],
                     width=38, state='readonly').grid(
                         row=3, column=1, pady=6, sticky='w')

        tk.Button(top, text='⚠️  Log Incident',
                  command=self.log_incident,
                  font=('Arial', 10, 'bold'),
                  bg='#e67e22', fg='white',
                  relief='flat', padx=15, cursor='hand2').grid(
                      row=4, column=0, columnspan=2,
                      pady=15, ipady=6)

        self.inc_msg = tk.Label(top, text='', font=('Arial', 10),
                                bg='white', fg='green')
        self.inc_msg.grid(row=5, column=0, columnspan=2)

        # Bottom: list of incidents
        bottom = tk.Frame(frame, bg='#f0f2f5')
        bottom.pack(fill='both', expand=True, padx=20)

        tk.Label(bottom, text='All Incidents',
                 font=('Arial', 11, 'bold'),
                 bg='#f0f2f5').pack(anchor='w', pady=5)

        cols = ('Inc ID','Shipment ID','Type','Description',
                'Reported At','Resolved')
        self.inc_tree = ttk.Treeview(bottom, columns=cols,
                                     show='headings', height=10)
        for col in cols:
            self.inc_tree.heading(col, text=col)
            self.inc_tree.column(col, width=120)

        self.inc_tree.pack(fill='both', expand=True)
        self.load_incidents()

    def log_incident(self):
        ship_id = self.inc_vars['inc_ship_id'].get().strip()
        desc    = self.inc_vars['inc_desc'].get().strip()

        if not ship_id or not desc:
            self.inc_msg.config(text='⚠ All fields required!', fg='red')
            return

        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute('''
                INSERT INTO Incidents
                (shipment_id, incident_type, description)
                VALUES (?,?,?)
            ''', (ship_id, self.inc_type_var.get(), desc))
            conn.commit()
            conn.close()

            log_audit(self.user['username'], 'LOG_INCIDENT',
                      'Incidents',
                      f"Incident logged for shipment: {ship_id}")

            self.inc_msg.config(
                text='✅ Incident logged successfully!', fg='green')
            self.inc_vars['inc_ship_id'].set('')
            self.inc_vars['inc_desc'].set('')
            self.load_incidents()

        except Exception as e:
            self.inc_msg.config(text=f'Error: {e}', fg='red')

    def load_incidents(self):
        for row in self.inc_tree.get_children():
            self.inc_tree.delete(row)
        conn = get_connection()
        c = conn.cursor()
        c.execute('''SELECT incident_id, shipment_id, incident_type,
                            description, reported_at, resolved
                     FROM Incidents ORDER BY incident_id DESC''')
        for row in c.fetchall():
            self.inc_tree.insert('', 'end', values=tuple(row))
        conn.close()

    # ── TAB 5: FINANCIALS ───────────────────────────────

    def build_finance_tab(self):
        frame = self.tab_finance

        card = tk.Frame(frame, bg='white', padx=25, pady=15)
        card.pack(padx=20, pady=10, fill='both')

        tk.Label(card, text='Financial Summary',
                 font=('Arial', 14, 'bold'),
                 bg='white', fg='#1a1a2e').pack(anchor='w')

        # Summary stats
        conn = get_connection()
        c = conn.cursor()

        total_rev = c.execute(
            "SELECT COALESCE(SUM(transport_cost),0) FROM Shipments"
        ).fetchone()[0]

        paid = c.execute(
            "SELECT COALESCE(SUM(transport_cost),0) FROM Shipments WHERE payment_status='paid'"
        ).fetchone()[0]

        unpaid = c.execute(
            "SELECT COALESCE(SUM(transport_cost),0) FROM Shipments WHERE payment_status='unpaid'"
        ).fetchone()[0]
        conn.close()

        stats_row = tk.Frame(card, bg='white')
        stats_row.pack(fill='x', pady=15)

        for label, value, colour in [
            ('Total Revenue', f'£{total_rev:,.2f}', '#27ae60'),
            ('Paid',          f'£{paid:,.2f}',      '#2980b9'),
            ('Unpaid',        f'£{unpaid:,.2f}',    '#e74c3c'),
        ]:
            stat = tk.Frame(stats_row, bg=colour,
                            padx=25, pady=15)
            stat.pack(side='left', padx=10)
            tk.Label(stat, text=value,
                     font=('Arial', 22, 'bold'),
                     bg=colour, fg='white').pack()
            tk.Label(stat, text=label,
                     font=('Arial', 10),
                     bg=colour, fg='white').pack()

        # Payment status breakdown table
        tk.Label(card, text='Shipment Payment Details',
                 font=('Arial', 11, 'bold'),
                 bg='white', fg='#1a1a2e').pack(
                     anchor='w', pady=(15, 5))

        cols = ('Shipment ID','Order No','Cost (£)','Payment Status')
        tree = ttk.Treeview(card, columns=cols,
                            show='headings', height=15)
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=180)

        tree.tag_configure('paid',    background='#d5f5e3')
        tree.tag_configure('unpaid',  background='#fadbd8')
        tree.tag_configure('partial', background='#fef9e7')

        conn2 = get_connection()
        c2 = conn2.cursor()
        c2.execute('''SELECT shipment_id, order_number,
                             transport_cost, payment_status
                      FROM Shipments ORDER BY shipment_id DESC''')
        for row in c2.fetchall():
            tree.insert('', 'end', values=tuple(row),
                        tags=(row[3],))
        conn2.close()

        tree.pack(fill='both', expand=True)