# reports.py
# Generates operational reports and summaries

import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import logging
from datetime import datetime
from auth import log_audit, get_current_user

logging.basicConfig(filename='northshore.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def get_connection():
    conn = sqlite3.connect('northshore.db')
    conn.row_factory = sqlite3.Row
    return conn


class ReportsPage:

    def __init__(self, parent, user):
        self.parent = parent
        self.user   = user
        self.build()

    def build(self):
        notebook = ttk.Notebook(self.parent)
        notebook.pack(fill='both', expand=True, padx=20, pady=10)

        self.tab_delivery  = tk.Frame(notebook, bg='#f0f2f5')
        self.tab_warehouse = tk.Frame(notebook, bg='#f0f2f5')
        self.tab_vehicle   = tk.Frame(notebook, bg='#f0f2f5')
        self.tab_export    = tk.Frame(notebook, bg='#f0f2f5')

        notebook.add(self.tab_delivery,  text='  📦 Delivery Report  ')
        notebook.add(self.tab_warehouse, text='  🏭 Warehouse Activity  ')
        notebook.add(self.tab_vehicle,   text='  🚗 Vehicle Utilisation  ')
        notebook.add(self.tab_export,    text='  💾 Export Report  ')

        self.build_delivery_tab()
        self.build_warehouse_tab()
        self.build_vehicle_tab()
        self.build_export_tab()

    # ── DELIVERY REPORT ─────────────────────────────────

    def build_delivery_tab(self):
        frame = self.tab_delivery

        # Summary cards
        summary = tk.Frame(frame, bg='#f0f2f5', pady=15)
        summary.pack(fill='x', padx=20)

        tk.Label(summary, text='Delivery Progress Report',
                 font=('Arial', 14, 'bold'),
                 bg='#f0f2f5', fg='#1a1a2e').pack(
                     anchor='w', pady=(0,10))

        conn = get_connection()
        c = conn.cursor()

        stats = [
            ('Total',       c.execute(
                "SELECT COUNT(*) FROM Shipments").fetchone()[0],           '#1a1a2e'),
            ('Delivered',   c.execute(
                "SELECT COUNT(*) FROM Shipments WHERE status='delivered'"
            ).fetchone()[0], '#27ae60'),
            ('In Transit',  c.execute(
                "SELECT COUNT(*) FROM Shipments WHERE status='in_transit'"
            ).fetchone()[0], '#f39c12'),
            ('Delayed',     c.execute(
                "SELECT COUNT(*) FROM Shipments WHERE status='delayed'"
            ).fetchone()[0], '#e74c3c'),
            ('Returned',    c.execute(
                "SELECT COUNT(*) FROM Shipments WHERE status='returned'"
            ).fetchone()[0], '#8e44ad'),
        ]
        conn.close()

        cards_row = tk.Frame(summary, bg='#f0f2f5')
        cards_row.pack(fill='x')

        for label, value, colour in stats:
            card = tk.Frame(cards_row, bg=colour,
                            padx=20, pady=12)
            card.pack(side='left', padx=6)
            tk.Label(card, text=str(value),
                     font=('Arial', 24, 'bold'),
                     bg=colour, fg='white').pack()
            tk.Label(card, text=label,
                     font=('Arial', 9),
                     bg=colour, fg='white').pack()

        # Delivery table
        table_frame = tk.Frame(frame, bg='white',
                               padx=15, pady=10)
        table_frame.pack(fill='both', expand=True,
                         padx=20, pady=10)

        tk.Label(table_frame, text='All Shipments Detail',
                 font=('Arial', 11, 'bold'),
                 bg='white').pack(anchor='w', pady=(0,8))

        cols = ('Shipment ID','Order No','Sender',
                'Receiver','Status','Driver','Date','Cost')
        tree = ttk.Treeview(table_frame, columns=cols,
                            show='headings', height=15)

        tree.tag_configure('delivered', background='#d5f5e3')
        tree.tag_configure('delayed',   background='#fadbd8')
        tree.tag_configure('returned',  background='#f9ebea')
        tree.tag_configure('in_transit',background='#d6eaf8')

        widths = [80, 100, 120, 120, 90, 120, 100, 80]
        for col, w in zip(cols, widths):
            tree.heading(col, text=col)
            tree.column(col, width=w)

        conn2 = get_connection()
        c2 = conn2.cursor()
        c2.execute('''
            SELECT s.shipment_id, s.order_number,
                   s.sender_name, s.receiver_name, s.status,
                   COALESCE(d.full_name,'Unassigned'),
                   COALESCE(s.delivery_date,'TBD'),
                   COALESCE(s.transport_cost,0)
            FROM Shipments s
            LEFT JOIN Drivers d ON s.driver_id=d.driver_id
            ORDER BY s.shipment_id DESC
        ''')
        for row in c2.fetchall():
            tree.insert('', 'end', values=tuple(row), tags=(row[4],))
        conn2.close()

        scroll = ttk.Scrollbar(table_frame, orient='vertical',
                               command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        tree.pack(fill='both', expand=True, side='left')
        scroll.pack(side='right', fill='y')

        log_audit(self.user['username'], 'VIEW_REPORT',
                  'Shipments', "Viewed delivery progress report")

    # ── WAREHOUSE ACTIVITY ──────────────────────────────

    def build_warehouse_tab(self):
        frame = self.tab_warehouse

        tk.Label(frame, text='Warehouse Activity Log',
                 font=('Arial', 14, 'bold'),
                 bg='#f0f2f5', fg='#1a1a2e').pack(
                     anchor='w', padx=20, pady=15)

        cols = ('Warehouse','Total Shipments','Delivered',
                'In Transit','Delayed','Total Inventory Items')
        tree = ttk.Treeview(frame, columns=cols,
                            show='headings', height=20)
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=150)

        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT warehouse_id, name FROM Warehouses")
        warehouses = c.fetchall()

        for wh in warehouses:
            wid  = wh['warehouse_id']
            name = wh['name']

            total = c.execute(
                "SELECT COUNT(*) FROM Shipments WHERE warehouse_id=?",
                (wid,)).fetchone()[0]
            delivered = c.execute(
                "SELECT COUNT(*) FROM Shipments WHERE warehouse_id=? AND status='delivered'",
                (wid,)).fetchone()[0]
            in_transit = c.execute(
                "SELECT COUNT(*) FROM Shipments WHERE warehouse_id=? AND status='in_transit'",
                (wid,)).fetchone()[0]
            delayed = c.execute(
                "SELECT COUNT(*) FROM Shipments WHERE warehouse_id=? AND status='delayed'",
                (wid,)).fetchone()[0]
            inv_items = c.execute(
                "SELECT COUNT(*) FROM Inventory WHERE warehouse_id=?",
                (wid,)).fetchone()[0]

            tree.insert('', 'end',
                        values=(name, total, delivered,
                                in_transit, delayed, inv_items))

        conn.close()
        tree.pack(fill='both', expand=True, padx=20, pady=5)

    # ── VEHICLE UTILISATION ─────────────────────────────

    def build_vehicle_tab(self):
        frame = self.tab_vehicle

        tk.Label(frame, text='Vehicle Utilisation Summary',
                 font=('Arial', 14, 'bold'),
                 bg='#f0f2f5', fg='#1a1a2e').pack(
                     anchor='w', padx=20, pady=15)

        cols = ('Vehicle ID','Registration','Type',
                'Capacity(kg)','Status','Assigned Shipments','Warehouse')
        tree = ttk.Treeview(frame, columns=cols,
                            show='headings', height=20)

        tree.tag_configure('available',   background='#d5f5e3')
        tree.tag_configure('in_use',      background='#fef9e7')
        tree.tag_configure('maintenance', background='#fadbd8')

        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=120)

        conn = get_connection()
        c = conn.cursor()
        c.execute('''
            SELECT v.vehicle_id, v.registration, v.vehicle_type,
                   v.capacity_kg, v.availability,
                   (SELECT COUNT(*) FROM Shipments s
                    WHERE s.vehicle_id = v.vehicle_id) as ship_count,
                   COALESCE(w.name,'Unassigned')
            FROM Vehicles v
            LEFT JOIN Warehouses w ON v.warehouse_id=w.warehouse_id
            ORDER BY v.registration
        ''')
        for row in c.fetchall():
            tree.insert('', 'end', values=tuple(row),
                        tags=(row[4],))
        conn.close()

        tree.pack(fill='both', expand=True, padx=20, pady=5)

    # ── EXPORT REPORT ───────────────────────────────────

    def build_export_tab(self):
        frame = self.tab_export

        card = tk.Frame(frame, bg='white', padx=30, pady=25)
        card.pack(padx=40, pady=30, fill='both')

        tk.Label(card, text='💾  Export Reports to File',
                 font=('Arial', 14, 'bold'),
                 bg='white', fg='#1a1a2e').pack(anchor='w')

        tk.Label(card,
                 text='Click a button below to export the chosen report as a .txt file.',
                 font=('Arial', 10),
                 bg='white', fg='#666666').pack(
                     anchor='w', pady=(5, 20))

        buttons = [
            ('📦 Export Shipments Report',
             '#e94560', self.export_shipments),
            ('🏭 Export Warehouse Activity',
             '#2980b9', self.export_warehouse),
            ('🚗 Export Vehicle Report',
             '#27ae60', self.export_vehicles),
            ('📋 Export Full Audit Log',
             '#8e44ad', self.export_audit),
        ]

        for label, colour, command in buttons:
            tk.Button(card, text=label,
                      command=command,
                      font=('Arial', 11),
                      bg=colour, fg='white',
                      relief='flat', cursor='hand2',
                      padx=20).pack(
                          fill='x', pady=6, ipady=10)

        self.export_msg = tk.Label(card, text='',
                                   font=('Arial', 10),
                                   bg='white', fg='green')
        self.export_msg.pack(pady=10)

    def export_shipments(self):
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute('''
                SELECT s.shipment_id, s.order_number,
                       s.sender_name, s.receiver_name, s.status,
                       COALESCE(d.full_name,'Unassigned'),
                       COALESCE(s.delivery_date,'TBD'),
                       COALESCE(s.transport_cost,0),
                       s.payment_status
                FROM Shipments s
                LEFT JOIN Drivers d ON s.driver_id=d.driver_id
                ORDER BY s.shipment_id DESC
            ''')
            rows = c.fetchall()
            conn.close()

            filename = f'shipments_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
            with open(filename, 'w') as f:
                f.write('NORTHSHORE LOGISTICS LTD\n')
                f.write('SHIPMENTS REPORT\n')
                f.write(f'Generated: {datetime.now()}\n')
                f.write('='*80 + '\n\n')
                f.write(f'{"ID":<6}{"Order No":<15}{"Sender":<20}'
                        f'{"Receiver":<20}{"Status":<12}'
                        f'{"Driver":<18}{"Date":<12}{"Cost":>8}\n')
                f.write('-'*80 + '\n')
                for row in rows:
                    f.write(f'{row[0]:<6}{row[1]:<15}{row[2]:<20}'
                            f'{row[3]:<20}{row[4]:<12}'
                            f'{row[5]:<18}{row[6]:<12}£{row[7]:>7.2f}\n')

            log_audit(self.user['username'], 'EXPORT_REPORT',
                      'Shipments', f"Exported to {filename}")
            self.export_msg.config(
                text=f'✅ Exported to {filename}', fg='green')

        except Exception as e:
            self.export_msg.config(text=f'Error: {e}', fg='red')

    def export_warehouse(self):
        try:
            filename = f'warehouse_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
            conn = get_connection()
            c = conn.cursor()
            c.execute("SELECT warehouse_id, name FROM Warehouses")
            warehouses = c.fetchall()

            with open(filename, 'w') as f:
                f.write('NORTHSHORE LOGISTICS LTD\n')
                f.write('WAREHOUSE ACTIVITY REPORT\n')
                f.write(f'Generated: {datetime.now()}\n')
                f.write('='*60 + '\n\n')

                for wh in warehouses:
                    wid  = wh['warehouse_id']
                    name = wh['name']
                    total = c.execute(
                        "SELECT COUNT(*) FROM Shipments WHERE warehouse_id=?",
                        (wid,)).fetchone()[0]
                    inv = c.execute(
                        "SELECT COUNT(*) FROM Inventory WHERE warehouse_id=?",
                        (wid,)).fetchone()[0]

                    f.write(f'Warehouse: {name}\n')
                    f.write(f'  Total Shipments : {total}\n')
                    f.write(f'  Inventory Items : {inv}\n\n')

            conn.close()
            log_audit(self.user['username'], 'EXPORT_REPORT',
                      'Warehouses', f"Exported to {filename}")
            self.export_msg.config(
                text=f'✅ Exported to {filename}', fg='green')

        except Exception as e:
            self.export_msg.config(text=f'Error: {e}', fg='red')

    def export_vehicles(self):
        try:
            filename = f'vehicles_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
            conn = get_connection()
            c = conn.cursor()
            c.execute('''
                SELECT v.registration, v.vehicle_type,
                       v.capacity_kg, v.availability,
                       COALESCE(w.name,'Unassigned')
                FROM Vehicles v
                LEFT JOIN Warehouses w ON v.warehouse_id=w.warehouse_id
            ''')
            rows = c.fetchall()
            conn.close()

            with open(filename, 'w') as f:
                f.write('NORTHSHORE LOGISTICS LTD\n')
                f.write('VEHICLE UTILISATION REPORT\n')
                f.write(f'Generated: {datetime.now()}\n')
                f.write('='*70 + '\n\n')
                f.write(f'{"Reg":<15}{"Type":<15}{"Capacity":<12}'
                        f'{"Status":<14}{"Warehouse"}\n')
                f.write('-'*70 + '\n')
                for row in rows:
                    f.write(f'{row[0]:<15}{row[1]:<15}{row[2]:<12}'
                            f'{row[3]:<14}{row[4]}\n')

            log_audit(self.user['username'], 'EXPORT_REPORT',
                      'Vehicles', f"Exported to {filename}")
            self.export_msg.config(
                text=f'✅ Exported to {filename}', fg='green')

        except Exception as e:
            self.export_msg.config(text=f'Error: {e}', fg='red')

    def export_audit(self):
        try:
            filename = f'audit_log_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
            conn = get_connection()
            c = conn.cursor()
            c.execute('''SELECT timestamp, username, action,
                                table_name, details
                         FROM AuditLog ORDER BY log_id DESC''')
            rows = c.fetchall()
            conn.close()

            with open(filename, 'w') as f:
                f.write('NORTHSHORE LOGISTICS LTD\n')
                f.write('FULL AUDIT LOG\n')
                f.write(f'Generated: {datetime.now()}\n')
                f.write('='*90 + '\n\n')
                for row in rows:
                    f.write(f'[{row[0]}] {row[1]:<15} '
                            f'{row[2]:<20} {row[3]:<15} {row[4]}\n')

            self.export_msg.config(
                text=f'✅ Exported to {filename}', fg='green')

        except Exception as e:
            self.export_msg.config(text=f'Error: {e}', fg='red')