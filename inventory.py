# inventory.py
# Manages stock levels, reorder alerts, and warehouse activity

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


class InventoryPage:

    def __init__(self, parent, user):
        self.parent = parent
        self.user   = user
        self.build()

    def build(self):
        notebook = ttk.Notebook(self.parent)
        notebook.pack(fill='both', expand=True, padx=20, pady=10)

        self.tab_stock    = tk.Frame(notebook, bg='#f0f2f5')
        self.tab_add      = tk.Frame(notebook, bg='#f0f2f5')
        self.tab_update   = tk.Frame(notebook, bg='#f0f2f5')
        self.tab_warehouse= tk.Frame(notebook, bg='#f0f2f5')

        notebook.add(self.tab_stock,     text='  📋 Stock Levels  ')
        notebook.add(self.tab_add,       text='  ➕ Add Item  ')
        notebook.add(self.tab_update,    text='  ✏️ Update Stock  ')
        notebook.add(self.tab_warehouse, text='  🏭 Warehouses  ')

        self.build_stock_tab()
        self.build_add_tab()
        self.build_update_tab()
        self.build_warehouse_tab()

    # ── TAB 1: STOCK LEVELS ─────────────────────────────

    def build_stock_tab(self):
        frame = self.tab_stock

        # Alert banner for low stock
        self.alert_frame = tk.Frame(frame, bg='#e74c3c', pady=6)
        self.alert_lbl   = tk.Label(self.alert_frame,
                                    text='', font=('Arial', 9, 'bold'),
                                    bg='#e74c3c', fg='white')
        self.alert_lbl.pack()

        btn_row = tk.Frame(frame, bg='#f0f2f5', pady=8)
        btn_row.pack(fill='x', padx=15)

        tk.Button(btn_row, text='🔄 Refresh',
                  command=self.load_stock,
                  bg='#27ae60', fg='white',
                  relief='flat', padx=12,
                  cursor='hand2').pack(side='left', ipady=5)

        tk.Label(btn_row, text='  Filter Warehouse:',
                 bg='#f0f2f5', font=('Arial', 10)).pack(side='left')

        self.wh_filter_var = tk.StringVar(value='All')
        self.wh_combo = ttk.Combobox(
            btn_row, textvariable=self.wh_filter_var,
            values=self.get_warehouse_names(),
            width=20, state='readonly')
        self.wh_combo.pack(side='left', padx=8)
        self.wh_combo.bind('<<ComboboxSelected>>',
                           lambda e: self.load_stock())

        cols = ('ID','Item Name','Warehouse',
                'Quantity','Reorder Level','Location','Last Updated')
        self.stock_tree = ttk.Treeview(frame, columns=cols,
                                       show='headings', height=20)

        widths = [50, 160, 130, 80, 100, 120, 140]
        for col, w in zip(cols, widths):
            self.stock_tree.heading(col, text=col)
            self.stock_tree.column(col, width=w)

        # Red row for items below reorder level
        self.stock_tree.tag_configure('low',  background='#fadbd8')
        self.stock_tree.tag_configure('ok',   background='#d5f5e3')

        scroll = ttk.Scrollbar(frame, orient='vertical',
                               command=self.stock_tree.yview)
        self.stock_tree.configure(yscrollcommand=scroll.set)
        self.stock_tree.pack(fill='both', expand=True,
                             padx=15, pady=5, side='left')
        scroll.pack(side='right', fill='y', pady=5)

        self.load_stock()

    def get_warehouse_names(self):
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT name FROM Warehouses")
        names = ['All'] + [r['name'] for r in c.fetchall()]
        conn.close()
        return names

    def load_stock(self):
        for row in self.stock_tree.get_children():
            self.stock_tree.delete(row)

        conn = get_connection()
        c = conn.cursor()

        wh_filter = self.wh_filter_var.get()
        if wh_filter == 'All':
            c.execute('''
                SELECT i.inventory_id, i.item_name,
                       COALESCE(w.name,'No Warehouse'),
                       i.quantity, i.reorder_level,
                       COALESCE(i.item_location,'N/A'),
                       i.last_updated
                FROM Inventory i
                LEFT JOIN Warehouses w ON i.warehouse_id=w.warehouse_id
                ORDER BY i.item_name
            ''')
        else:
            c.execute('''
                SELECT i.inventory_id, i.item_name,
                       COALESCE(w.name,'No Warehouse'),
                       i.quantity, i.reorder_level,
                       COALESCE(i.item_location,'N/A'),
                       i.last_updated
                FROM Inventory i
                LEFT JOIN Warehouses w ON i.warehouse_id=w.warehouse_id
                WHERE w.name = ?
                ORDER BY i.item_name
            ''', (wh_filter,))

        low_stock_items = []
        for row in c.fetchall():
            qty    = row[3]
            reorder= row[4]
            tag    = 'low' if qty <= reorder else 'ok'
            if qty <= reorder:
                low_stock_items.append(row[1])
            self.stock_tree.insert('', 'end', values=tuple(row), tags=(tag,))

        conn.close()

        # Show or hide low stock alert
        if low_stock_items:
            self.alert_lbl.config(
                text=f'⚠ LOW STOCK ALERT: {", ".join(low_stock_items[:5])} — reorder needed!')
            self.alert_frame.pack(fill='x', before=self.stock_tree)
        else:
            self.alert_frame.pack_forget()

    # ── TAB 2: ADD ITEM ─────────────────────────────────

    def build_add_tab(self):
        frame = self.tab_add
        card  = tk.Frame(frame, bg='white', padx=30, pady=20)
        card.pack(padx=20, pady=15, fill='both')

        tk.Label(card, text='Add New Inventory Item',
                 font=('Arial', 14, 'bold'),
                 bg='white', fg='#1a1a2e').grid(
                     row=0, column=0, columnspan=2,
                     pady=(0,15), sticky='w')

        fields = [
            ('Item Name *',       'item_name'),
            ('Quantity *',        'quantity'),
            ('Reorder Level',     'reorder_level'),
            ('Item Location',     'item_location'),
        ]

        self.inv_add_vars = {}
        for i, (lbl, vname) in enumerate(fields):
            tk.Label(card, text=lbl, font=('Arial', 10),
                     bg='white', anchor='e', width=16).grid(
                         row=i+1, column=0, padx=(0,10),
                         pady=8, sticky='e')
            var = tk.StringVar()
            self.inv_add_vars[vname] = var
            tk.Entry(card, textvariable=var, font=('Arial', 10),
                     width=35, relief='solid', bd=1).grid(
                         row=i+1, column=1, pady=8, sticky='w')

        # Warehouse dropdown
        tk.Label(card, text='Warehouse', font=('Arial', 10),
                 bg='white', anchor='e', width=16).grid(
                     row=5, column=0, padx=(0,10), pady=8, sticky='e')

        self.inv_wh_map = self.get_warehouses()
        self.inv_wh_var = tk.StringVar()
        ttk.Combobox(card, textvariable=self.inv_wh_var,
                     values=list(self.inv_wh_map.keys()),
                     width=33, state='readonly').grid(
                         row=5, column=1, pady=8, sticky='w')

        tk.Button(card, text='➕  Add Item',
                  command=self.add_item,
                  font=('Arial', 11, 'bold'),
                  bg='#e94560', fg='white',
                  relief='flat', padx=20,
                  cursor='hand2').grid(
                      row=6, column=0, columnspan=2,
                      pady=20, ipadx=10, ipady=8)

        self.inv_add_msg = tk.Label(card, text='',
                                    font=('Arial', 10),
                                    bg='white', fg='green')
        self.inv_add_msg.grid(row=7, column=0, columnspan=2)

    def get_warehouses(self):
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT warehouse_id, name FROM Warehouses")
        result = {r['name']: r['warehouse_id'] for r in c.fetchall()}
        conn.close()
        return result

    def add_item(self):
        name = self.inv_add_vars['item_name'].get().strip()
        qty  = self.inv_add_vars['quantity'].get().strip()

        if not name or not qty:
            self.inv_add_msg.config(
                text='⚠ Item name and quantity are required!', fg='red')
            return

        try:
            qty_int     = int(qty)
            reorder_int = int(
                self.inv_add_vars['reorder_level'].get() or 10)
        except ValueError:
            self.inv_add_msg.config(
                text='⚠ Quantity must be a whole number!', fg='red')
            return

        wh_name = self.inv_wh_var.get()
        wh_id   = self.inv_wh_map.get(wh_name)

        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute('''
                INSERT INTO Inventory
                (item_name, warehouse_id, quantity,
                 reorder_level, item_location)
                VALUES (?,?,?,?,?)
            ''', (name, wh_id, qty_int, reorder_int,
                  self.inv_add_vars['item_location'].get()))
            conn.commit()
            conn.close()

            log_audit(self.user['username'], 'ADD_INVENTORY',
                      'Inventory', f"Added item: {name} qty:{qty_int}")

            self.inv_add_msg.config(
                text=f'✅ {name} added successfully!', fg='green')
            for var in self.inv_add_vars.values():
                var.set('')
            self.load_stock()

        except Exception as e:
            self.inv_add_msg.config(text=f'Error: {e}', fg='red')

    # ── TAB 3: UPDATE STOCK ─────────────────────────────

    def build_update_tab(self):
        frame = self.tab_update
        card  = tk.Frame(frame, bg='white', padx=30, pady=20)
        card.pack(padx=20, pady=15, fill='both')

        tk.Label(card, text='Update Stock Quantity',
                 font=('Arial', 14, 'bold'),
                 bg='white', fg='#1a1a2e').grid(
                     row=0, column=0, columnspan=2,
                     pady=(0,15), sticky='w')

        tk.Label(card, text='Inventory ID *',
                 font=('Arial', 10), bg='white',
                 anchor='e', width=16).grid(
                     row=1, column=0, padx=(0,10), pady=8, sticky='e')

        self.upd_inv_id = tk.StringVar()
        tk.Entry(card, textvariable=self.upd_inv_id,
                 font=('Arial', 10), width=20,
                 relief='solid', bd=1).grid(
                     row=1, column=1, pady=8, sticky='w')

        # Operation type
        tk.Label(card, text='Operation',
                 font=('Arial', 10), bg='white',
                 anchor='e', width=16).grid(
                     row=2, column=0, padx=(0,10), pady=8, sticky='e')

        self.upd_operation = tk.StringVar(value='add')
        ops_frame = tk.Frame(card, bg='white')
        ops_frame.grid(row=2, column=1, sticky='w')
        for val, lbl in [('add','➕ Add Stock'),
                         ('remove','➖ Remove Stock'),
                         ('set','🔄 Set Exact Quantity')]:
            tk.Radiobutton(ops_frame, text=lbl,
                           variable=self.upd_operation,
                           value=val, bg='white',
                           font=('Arial', 10)).pack(
                               side='left', padx=8)

        tk.Label(card, text='Amount *',
                 font=('Arial', 10), bg='white',
                 anchor='e', width=16).grid(
                     row=3, column=0, padx=(0,10), pady=8, sticky='e')

        self.upd_amount = tk.StringVar()
        tk.Entry(card, textvariable=self.upd_amount,
                 font=('Arial', 10), width=20,
                 relief='solid', bd=1).grid(
                     row=3, column=1, pady=8, sticky='w')

        tk.Button(card, text='💾  Update Stock',
                  command=self.update_stock,
                  font=('Arial', 11, 'bold'),
                  bg='#27ae60', fg='white',
                  relief='flat', padx=20,
                  cursor='hand2').grid(
                      row=4, column=0, columnspan=2,
                      pady=20, ipadx=10, ipady=8)

        self.upd_inv_msg = tk.Label(card, text='',
                                    font=('Arial', 10),
                                    bg='white', fg='green')
        self.upd_inv_msg.grid(row=5, column=0, columnspan=2)

    def update_stock(self):
        inv_id = self.upd_inv_id.get().strip()
        amount = self.upd_amount.get().strip()
        op     = self.upd_operation.get()

        if not inv_id or not amount:
            self.upd_inv_msg.config(
                text='⚠ ID and amount required!', fg='red')
            return

        try:
            amount_int = int(amount)
        except ValueError:
            self.upd_inv_msg.config(
                text='⚠ Amount must be a whole number!', fg='red')
            return

        try:
            conn = get_connection()
            c = conn.cursor()

            if op == 'add':
                c.execute('''UPDATE Inventory
                             SET quantity = quantity + ?,
                                 last_updated = datetime('now')
                             WHERE inventory_id = ?''',
                          (amount_int, inv_id))
            elif op == 'remove':
                c.execute('''UPDATE Inventory
                             SET quantity = MAX(0, quantity - ?),
                                 last_updated = datetime('now')
                             WHERE inventory_id = ?''',
                          (amount_int, inv_id))
            elif op == 'set':
                c.execute('''UPDATE Inventory
                             SET quantity = ?,
                                 last_updated = datetime('now')
                             WHERE inventory_id = ?''',
                          (amount_int, inv_id))

            conn.commit()
            conn.close()

            log_audit(self.user['username'], 'UPDATE_STOCK',
                      'Inventory',
                      f"Stock update: ID={inv_id} op={op} amount={amount_int}")

            self.upd_inv_msg.config(
                text=f'✅ Stock updated for item #{inv_id}!', fg='green')
            self.load_stock()

        except Exception as e:
            self.upd_inv_msg.config(text=f'Error: {e}', fg='red')

    # ── TAB 4: WAREHOUSES ───────────────────────────────

    def build_warehouse_tab(self):
        frame = self.tab_warehouse

        # Add warehouse form
        top = tk.Frame(frame, bg='white', padx=25, pady=15)
        top.pack(fill='x', padx=20, pady=10)

        tk.Label(top, text='Add / View Warehouses',
                 font=('Arial', 13, 'bold'),
                 bg='white', fg='#1a1a2e').grid(
                     row=0, column=0, columnspan=2,
                     sticky='w', pady=(0,10))

        wh_fields = [
            ('Warehouse Name *', 'wh_name'),
            ('Location *',       'wh_location'),
            ('Capacity',         'wh_capacity'),
            ('Manager Name',     'wh_manager'),
            ('Phone',            'wh_phone'),
        ]

        self.wh_vars = {}
        for i, (lbl, vname) in enumerate(wh_fields):
            tk.Label(top, text=lbl, font=('Arial', 10),
                     bg='white', anchor='e', width=16).grid(
                         row=i+1, column=0, padx=(0,10),
                         pady=6, sticky='e')
            var = tk.StringVar()
            self.wh_vars[vname] = var
            tk.Entry(top, textvariable=var, font=('Arial', 10),
                     width=30, relief='solid', bd=1).grid(
                         row=i+1, column=1, pady=6, sticky='w')

        tk.Button(top, text='➕  Add Warehouse',
                  command=self.add_warehouse,
                  font=('Arial', 10, 'bold'),
                  bg='#2980b9', fg='white',
                  relief='flat', padx=15,
                  cursor='hand2').grid(
                      row=6, column=0, columnspan=2,
                      pady=12, ipady=6)

        self.wh_msg = tk.Label(top, text='', font=('Arial', 10),
                               bg='white', fg='green')
        self.wh_msg.grid(row=7, column=0, columnspan=2)

        # Warehouses list
        bottom = tk.Frame(frame, bg='#f0f2f5')
        bottom.pack(fill='both', expand=True, padx=20, pady=5)

        cols = ('ID','Name','Location','Capacity','Manager','Phone')
        self.wh_tree = ttk.Treeview(bottom, columns=cols,
                                    show='headings', height=8)
        for col in cols:
            self.wh_tree.heading(col, text=col)
            self.wh_tree.column(col, width=130)
        self.wh_tree.pack(fill='both', expand=True)
        self.load_warehouses()

    def add_warehouse(self):
        name     = self.wh_vars['wh_name'].get().strip()
        location = self.wh_vars['wh_location'].get().strip()

        if not name or not location:
            self.wh_msg.config(
                text='⚠ Name and location required!', fg='red')
            return

        try:
            capacity = int(self.wh_vars['wh_capacity'].get() or 0)
        except ValueError:
            capacity = 0

        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute('''
                INSERT INTO Warehouses
                (name, location, capacity, manager_name, phone)
                VALUES (?,?,?,?,?)
            ''', (name, location, capacity,
                  self.wh_vars['wh_manager'].get(),
                  self.wh_vars['wh_phone'].get()))
            conn.commit()
            conn.close()

            log_audit(self.user['username'], 'ADD_WAREHOUSE',
                      'Warehouses', f"Added warehouse: {name}")

            self.wh_msg.config(
                text=f'✅ Warehouse "{name}" added!', fg='green')
            for var in self.wh_vars.values():
                var.set('')
            self.load_warehouses()

        except Exception as e:
            self.wh_msg.config(text=f'Error: {e}', fg='red')

    def load_warehouses(self):
        for row in self.wh_tree.get_children():
            self.wh_tree.delete(row)
        conn = get_connection()
        c = conn.cursor()
        c.execute('''SELECT warehouse_id, name, location,
                            capacity, manager_name, phone
                     FROM Warehouses ORDER BY name''')
        for row in c.fetchall():
            self.wh_tree.insert('', 'end', values=tuple(row))
        conn.close()