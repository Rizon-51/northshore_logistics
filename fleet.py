# fleet.py
# Manages drivers and vehicles

import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import logging
from auth import log_audit, get_current_user

logging.basicConfig(filename='northshore.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def get_connection():
    conn = sqlite3.connect('northshore.db')
    conn.row_factory = sqlite3.Row
    return conn


class FleetPage:

    def __init__(self, parent, user):
        self.parent = parent
        self.user   = user
        self.build()

    def build(self):
        notebook = ttk.Notebook(self.parent)
        notebook.pack(fill='both', expand=True, padx=20, pady=10)

        self.tab_drivers  = tk.Frame(notebook, bg='#f0f2f5')
        self.tab_vehicles = tk.Frame(notebook, bg='#f0f2f5')

        notebook.add(self.tab_drivers,  text='  👤 Drivers  ')
        notebook.add(self.tab_vehicles, text='  🚗 Vehicles  ')

        self.build_drivers_tab()
        self.build_vehicles_tab()

    # ── DRIVERS TAB ─────────────────────────────────────

    def build_drivers_tab(self):
        frame = self.tab_drivers

        # Add driver form
        top = tk.Frame(frame, bg='white', padx=25, pady=15)
        top.pack(fill='x', padx=20, pady=10)

        tk.Label(top, text='Add New Driver',
                 font=('Arial', 13, 'bold'),
                 bg='white', fg='#1a1a2e').grid(
                     row=0, column=0, columnspan=2,
                     sticky='w', pady=(0,10))

        driver_fields = [
            ('Full Name *',      'drv_name'),
            ('Licence Number *', 'drv_licence'),
            ('Phone',            'drv_phone'),
        ]

        self.drv_vars = {}
        for i, (lbl, vname) in enumerate(driver_fields):
            tk.Label(top, text=lbl, font=('Arial', 10),
                     bg='white', anchor='e', width=16).grid(
                         row=i+1, column=0, padx=(0,10),
                         pady=6, sticky='e')
            var = tk.StringVar()
            self.drv_vars[vname] = var
            tk.Entry(top, textvariable=var, font=('Arial', 10),
                     width=30, relief='solid', bd=1).grid(
                         row=i+1, column=1, pady=6, sticky='w')

        # Shift dropdown
        tk.Label(top, text='Shift', font=('Arial', 10),
                 bg='white', anchor='e', width=16).grid(
                     row=4, column=0, padx=(0,10), pady=6, sticky='e')

        self.drv_shift_var = tk.StringVar(value='morning')
        ttk.Combobox(top, textvariable=self.drv_shift_var,
                     values=['morning','afternoon','night'],
                     width=28, state='readonly').grid(
                         row=4, column=1, pady=6, sticky='w')

        # Warehouse dropdown
        tk.Label(top, text='Assigned Warehouse',
                 font=('Arial', 10), bg='white',
                 anchor='e', width=16).grid(
                     row=5, column=0, padx=(0,10), pady=6, sticky='e')

        self.drv_wh_map = self.get_warehouses()
        self.drv_wh_var = tk.StringVar()
        ttk.Combobox(top, textvariable=self.drv_wh_var,
                     values=list(self.drv_wh_map.keys()),
                     width=28, state='readonly').grid(
                         row=5, column=1, pady=6, sticky='w')

        tk.Button(top, text='➕  Add Driver',
                  command=self.add_driver,
                  font=('Arial', 10, 'bold'),
                  bg='#8e44ad', fg='white',
                  relief='flat', padx=15,
                  cursor='hand2').grid(
                      row=6, column=0, columnspan=2,
                      pady=12, ipady=6)

        self.drv_msg = tk.Label(top, text='', font=('Arial', 10),
                                bg='white', fg='green')
        self.drv_msg.grid(row=7, column=0, columnspan=2)

        # Drivers list
        bottom = tk.Frame(frame, bg='#f0f2f5')
        bottom.pack(fill='both', expand=True, padx=20)

        tk.Label(bottom, text='All Drivers',
                 font=('Arial', 11, 'bold'),
                 bg='#f0f2f5').pack(anchor='w', pady=5)

        cols = ('ID','Full Name','Licence','Phone',
                'Shift','Warehouse','Status')
        self.drv_tree = ttk.Treeview(bottom, columns=cols,
                                     show='headings', height=10)
        for col in cols:
            self.drv_tree.heading(col, text=col)
            self.drv_tree.column(col, width=110)

        scroll = ttk.Scrollbar(bottom, orient='vertical',
                               command=self.drv_tree.yview)
        self.drv_tree.configure(yscrollcommand=scroll.set)
        self.drv_tree.pack(fill='both', expand=True, side='left')
        scroll.pack(side='right', fill='y')

        self.load_drivers()

    def get_warehouses(self):
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT warehouse_id, name FROM Warehouses")
        result = {r['name']: r['warehouse_id'] for r in c.fetchall()}
        conn.close()
        return result

    def add_driver(self):
        name    = self.drv_vars['drv_name'].get().strip()
        licence = self.drv_vars['drv_licence'].get().strip()

        if not name or not licence:
            self.drv_msg.config(
                text='⚠ Name and licence required!', fg='red')
            return

        wh_name = self.drv_wh_var.get()
        wh_id   = self.drv_wh_map.get(wh_name)

        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute('''
                INSERT INTO Drivers
                (full_name, licence_number, phone, shift, warehouse_id)
                VALUES (?,?,?,?,?)
            ''', (name, licence,
                  self.drv_vars['drv_phone'].get(),
                  self.drv_shift_var.get(), wh_id))
            conn.commit()
            conn.close()

            log_audit(self.user['username'], 'ADD_DRIVER',
                      'Drivers', f"Added driver: {name}")

            self.drv_msg.config(
                text=f'✅ Driver "{name}" added!', fg='green')
            for var in self.drv_vars.values():
                var.set('')
            self.load_drivers()

        except sqlite3.IntegrityError:
            self.drv_msg.config(
                text='⚠ Licence number already exists!', fg='red')
        except Exception as e:
            self.drv_msg.config(text=f'Error: {e}', fg='red')

    def load_drivers(self):
        for row in self.drv_tree.get_children():
            self.drv_tree.delete(row)
        conn = get_connection()
        c = conn.cursor()
        c.execute('''
            SELECT d.driver_id, d.full_name, d.licence_number,
                   d.phone, d.shift,
                   COALESCE(w.name,'Unassigned'), d.status
            FROM Drivers d
            LEFT JOIN Warehouses w ON d.warehouse_id=w.warehouse_id
            ORDER BY d.full_name
        ''')
        for row in c.fetchall():
            self.drv_tree.insert('', 'end', values=tuple(row))
        conn.close()

    # ── VEHICLES TAB ────────────────────────────────────

    def build_vehicles_tab(self):
        frame = self.tab_vehicles

        # Add vehicle form
        top = tk.Frame(frame, bg='white', padx=25, pady=15)
        top.pack(fill='x', padx=20, pady=10)

        tk.Label(top, text='Add New Vehicle',
                 font=('Arial', 13, 'bold'),
                 bg='white', fg='#1a1a2e').grid(
                     row=0, column=0, columnspan=2,
                     sticky='w', pady=(0,10))

        veh_fields = [
            ('Registration *',   'veh_reg'),
            ('Vehicle Type',     'veh_type'),
            ('Capacity (kg)',    'veh_capacity'),
            ('Maintenance Due\n(YYYY-MM-DD)', 'veh_maintenance'),
        ]

        self.veh_vars = {}
        for i, (lbl, vname) in enumerate(veh_fields):
            tk.Label(top, text=lbl, font=('Arial', 10),
                     bg='white', anchor='e', width=18).grid(
                         row=i+1, column=0, padx=(0,10),
                         pady=6, sticky='e')
            var = tk.StringVar()
            self.veh_vars[vname] = var
            tk.Entry(top, textvariable=var, font=('Arial', 10),
                     width=30, relief='solid', bd=1).grid(
                         row=i+1, column=1, pady=6, sticky='w')

        # Availability dropdown
        tk.Label(top, text='Availability',
                 font=('Arial', 10), bg='white',
                 anchor='e', width=18).grid(
                     row=5, column=0, padx=(0,10), pady=6, sticky='e')

        self.veh_avail_var = tk.StringVar(value='available')
        ttk.Combobox(top, textvariable=self.veh_avail_var,
                     values=['available','in_use','maintenance'],
                     width=28, state='readonly').grid(
                         row=5, column=1, pady=6, sticky='w')

        # Warehouse dropdown
        tk.Label(top, text='Assigned Warehouse',
                 font=('Arial', 10), bg='white',
                 anchor='e', width=18).grid(
                     row=6, column=0, padx=(0,10), pady=6, sticky='e')

        self.veh_wh_map = self.get_warehouses()
        self.veh_wh_var = tk.StringVar()
        ttk.Combobox(top, textvariable=self.veh_wh_var,
                     values=list(self.veh_wh_map.keys()),
                     width=28, state='readonly').grid(
                         row=6, column=1, pady=6, sticky='w')

        tk.Button(top, text='➕  Add Vehicle',
                  command=self.add_vehicle,
                  font=('Arial', 10, 'bold'),
                  bg='#2980b9', fg='white',
                  relief='flat', padx=15,
                  cursor='hand2').grid(
                      row=7, column=0, columnspan=2,
                      pady=12, ipady=6)

        self.veh_msg = tk.Label(top, text='', font=('Arial', 10),
                                bg='white', fg='green')
        self.veh_msg.grid(row=8, column=0, columnspan=2)

        # Vehicles list
        bottom = tk.Frame(frame, bg='#f0f2f5')
        bottom.pack(fill='both', expand=True, padx=20)

        tk.Label(bottom, text='All Vehicles',
                 font=('Arial', 11, 'bold'),
                 bg='#f0f2f5').pack(anchor='w', pady=5)

        cols = ('ID','Registration','Type',
                'Capacity(kg)','Maintenance Due','Availability','Warehouse')
        self.veh_tree = ttk.Treeview(bottom, columns=cols,
                                     show='headings', height=10)

        self.veh_tree.tag_configure('available',   background='#d5f5e3')
        self.veh_tree.tag_configure('maintenance', background='#fadbd8')
        self.veh_tree.tag_configure('in_use',      background='#fef9e7')

        for col in cols:
            self.veh_tree.heading(col, text=col)
            self.veh_tree.column(col, width=120)

        self.veh_tree.pack(fill='both', expand=True)
        self.load_vehicles()

    def add_vehicle(self):
        reg = self.veh_vars['veh_reg'].get().strip()
        if not reg:
            self.veh_msg.config(
                text='⚠ Registration required!', fg='red')
            return

        try:
            capacity = float(self.veh_vars['veh_capacity'].get() or 0)
        except ValueError:
            capacity = 0

        wh_name = self.veh_wh_var.get()
        wh_id   = self.veh_wh_map.get(wh_name)

        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute('''
                INSERT INTO Vehicles
                (registration, vehicle_type, capacity_kg,
                 maintenance_due, availability, warehouse_id)
                VALUES (?,?,?,?,?,?)
            ''', (reg,
                  self.veh_vars['veh_type'].get(),
                  capacity,
                  self.veh_vars['veh_maintenance'].get(),
                  self.veh_avail_var.get(),
                  wh_id))
            conn.commit()
            conn.close()

            log_audit(self.user['username'], 'ADD_VEHICLE',
                      'Vehicles', f"Added vehicle: {reg}")

            self.veh_msg.config(
                text=f'✅ Vehicle "{reg}" added!', fg='green')
            for var in self.veh_vars.values():
                var.set('')
            self.load_vehicles()

        except sqlite3.IntegrityError:
            self.veh_msg.config(
                text='⚠ Registration already exists!', fg='red')
        except Exception as e:
            self.veh_msg.config(text=f'Error: {e}', fg='red')

    def load_vehicles(self):
        for row in self.veh_tree.get_children():
            self.veh_tree.delete(row)
        conn = get_connection()
        c = conn.cursor()
        c.execute('''
            SELECT v.vehicle_id, v.registration, v.vehicle_type,
                   v.capacity_kg, v.maintenance_due,
                   v.availability,
                   COALESCE(w.name,'Unassigned')
            FROM Vehicles v
            LEFT JOIN Warehouses w ON v.warehouse_id=w.warehouse_id
            ORDER BY v.registration
        ''')
        for row in c.fetchall():
            tag = row[5]
            self.veh_tree.insert('', 'end', values=tuple(row), tags=(tag,))
        conn.close()