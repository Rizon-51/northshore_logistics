# ── TAB 3: UPDATE DELIVERY — FIXED ─────────────────

    def build_update_tab(self):
        frame = self.tab_update

        card = tk.Frame(frame, bg='white', padx=30, pady=20)
        card.pack(padx=20, pady=15, fill='both')

        tk.Label(card, text='Update Delivery Information',
                 font=('Arial', 14, 'bold'),
                 bg='white', fg='#1a1a2e').grid(
                     row=0, column=0, columnspan=3,
                     pady=(0, 15), sticky='w')

        # ── Step 1: Enter ID and load ──
        tk.Label(card, text='Shipment ID *',
                 font=('Arial', 10, 'bold'),
                 bg='white', anchor='e', width=20).grid(
                     row=1, column=0, padx=(0, 10),
                     pady=8, sticky='e')

        self.upd_id_var = tk.StringVar()
        tk.Entry(card, textvariable=self.upd_id_var,
                 font=('Arial', 11), width=18,
                 relief='solid', bd=1).grid(
                     row=1, column=1, pady=8, sticky='w')

        tk.Button(card, text='🔍 Load',
                  command=self.load_shipment_for_update,
                  bg='#1a1a2e', fg='white',
                  font=('Arial', 10),
                  relief='flat', padx=12,
                  cursor='hand2').grid(
                      row=1, column=2, padx=10)

        # Current info display
        self.current_info_lbl = tk.Label(
            card, text='',
            font=('Arial', 9, 'italic'),
            bg='white', fg='#555555')
        self.current_info_lbl.grid(
            row=2, column=0, columnspan=3,
            sticky='w', pady=(0, 10))

        # Divider
        tk.Frame(card, bg='#eeeeee', height=1).grid(
            row=3, column=0, columnspan=3,
            sticky='ew', pady=10)

        tk.Label(card, text='── Update Fields Below ──',
                 font=('Arial', 9, 'italic'),
                 bg='white', fg='#999999').grid(
                     row=4, column=0, columnspan=3,
                     pady=(0, 10))

        # ── Status dropdown ──
        tk.Label(card, text='New Status',
                 font=('Arial', 10), bg='white',
                 anchor='e', width=20).grid(
                     row=5, column=0, padx=(0, 10),
                     pady=8, sticky='e')

        self.upd_status_var = tk.StringVar()
        self.upd_status_combo = tk.ttk.Combobox(
            card,
            textvariable=self.upd_status_var,
            values=['in_transit', 'delivered', 'delayed', 'returned'],
            width=30, state='readonly')
        self.upd_status_combo.grid(
            row=5, column=1, columnspan=2,
            pady=8, sticky='w')

        # ── Delivery date ──
        tk.Label(card, text='Delivery Date (YYYY-MM-DD)',
                 font=('Arial', 10), bg='white',
                 anchor='e', width=20).grid(
                     row=6, column=0, padx=(0, 10),
                     pady=8, sticky='e')

        self.upd_date_var = tk.StringVar()
        tk.Entry(card, textvariable=self.upd_date_var,
                 font=('Arial', 11), width=32,
                 relief='solid', bd=1).grid(
                     row=6, column=1, columnspan=2,
                     pady=8, sticky='w')

        # ── Route details ──
        tk.Label(card, text='Route Details',
                 font=('Arial', 10), bg='white',
                 anchor='e', width=20).grid(
                     row=7, column=0, padx=(0, 10),
                     pady=8, sticky='e')

        self.upd_route_var = tk.StringVar()
        tk.Entry(card, textvariable=self.upd_route_var,
                 font=('Arial', 11), width=32,
                 relief='solid', bd=1).grid(
                     row=7, column=1, columnspan=2,
                     pady=8, sticky='w')

        # ── Payment status ──
        tk.Label(card, text='Payment Status',
                 font=('Arial', 10), bg='white',
                 anchor='e', width=20).grid(
                     row=8, column=0, padx=(0, 10),
                     pady=8, sticky='e')

        self.upd_payment_var = tk.StringVar()
        tk.ttk.Combobox(
            card,
            textvariable=self.upd_payment_var,
            values=['unpaid', 'paid', 'partial'],
            width=30, state='readonly').grid(
                row=8, column=1, columnspan=2,
                pady=8, sticky='w')

        # ── Assign driver ──
        tk.Label(card, text='Assign Driver',
                 font=('Arial', 10), bg='white',
                 anchor='e', width=20).grid(
                     row=9, column=0, padx=(0, 10),
                     pady=8, sticky='e')

        self.driver_map = self.get_drivers()
        driver_names = ['-- No Change --'] + list(self.driver_map.keys())
        self.upd_driver_var = tk.StringVar(value='-- No Change --')
        tk.ttk.Combobox(
            card,
            textvariable=self.upd_driver_var,
            values=driver_names,
            width=30, state='readonly').grid(
                row=9, column=1, columnspan=2,
                pady=8, sticky='w')

        # ── Save button ──
        tk.Button(
            card,
            text='💾   Save Update',
            command=self.update_shipment,
            font=('Arial', 12, 'bold'),
            bg='#27ae60', fg='white',
            relief='flat', cursor='hand2'
        ).grid(row=10, column=0, columnspan=3,
               pady=20, ipadx=40, ipady=10)

        # ── Result message ──
        self.upd_result_lbl = tk.Label(
            card, text='',
            font=('Arial', 10, 'bold'),
            bg='white', fg='green')
        self.upd_result_lbl.grid(
            row=11, column=0, columnspan=3, pady=5)

    def load_shipment_for_update(self):
        """Load a shipment's current values into the update fields"""
        ship_id = self.upd_id_var.get().strip()

        if not ship_id:
            self.upd_result_lbl.config(
                text='⚠  Please enter a Shipment ID', fg='orange')
            return

        # Check it's a number
        if not ship_id.isdigit():
            self.upd_result_lbl.config(
                text='⚠  Shipment ID must be a number', fg='red')
            return

        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute('''
                SELECT s.*, COALESCE(d.full_name, '') as driver_name
                FROM Shipments s
                LEFT JOIN Drivers d ON s.driver_id = d.driver_id
                WHERE s.shipment_id = ?
            ''', (ship_id,))
            row = c.fetchone()
            conn.close()

            if row:
                # Fill in all the fields with current values
                self.upd_status_var.set(row['status'] or 'in_transit')
                self.upd_date_var.set(row['delivery_date'] or '')
                self.upd_route_var.set(row['route_details'] or '')
                self.upd_payment_var.set(row['payment_status'] or 'unpaid')

                # Set driver if one is assigned
                if row['driver_name']:
                    self.upd_driver_var.set(row['driver_name'])
                else:
                    self.upd_driver_var.set('-- No Change --')

                # Show current info summary
                self.current_info_lbl.config(
                    text=f"✅ Loaded: Order {row['order_number']}  |  "
                         f"From: {row['sender_name']}  →  "
                         f"To: {row['receiver_name']}  |  "
                         f"Current status: {row['status']}",
                    fg='#27ae60')
                self.upd_result_lbl.config(text='')

            else:
                self.current_info_lbl.config(
                    text=f'⚠  No shipment found with ID {ship_id}',
                    fg='red')
                self.upd_result_lbl.config(text='')

        except Exception as e:
            self.upd_result_lbl.config(
                text=f'Error loading: {e}', fg='red')

    def update_shipment(self):
        """Save the updated shipment info to the database"""
        ship_id = self.upd_id_var.get().strip()

        if not ship_id:
            self.upd_result_lbl.config(
                text='⚠  Please enter a Shipment ID and click Load first',
                fg='red')
            return

        if not ship_id.isdigit():
            self.upd_result_lbl.config(
                text='⚠  Shipment ID must be a number', fg='red')
            return

        # Get new values
        new_status  = self.upd_status_var.get()
        new_date    = self.upd_date_var.get().strip()
        new_route   = self.upd_route_var.get().strip()
        new_payment = self.upd_payment_var.get()

        # Validate status is set
        if not new_status:
            self.upd_result_lbl.config(
                text='⚠  Please select a status', fg='red')
            return

        # Get driver ID if one is selected
        driver_name = self.upd_driver_var.get()
        if driver_name and driver_name != '-- No Change --':
            driver_id = self.driver_map.get(driver_name)
        else:
            # Keep existing driver — don't overwrite
            try:
                conn = get_connection()
                c = conn.cursor()
                c.execute('SELECT driver_id FROM Shipments WHERE shipment_id=?',
                          (ship_id,))
                row = c.fetchone()
                conn.close()
                driver_id = row['driver_id'] if row else None
            except Exception:
                driver_id = None

        try:
            conn = get_connection()
            c = conn.cursor()

            c.execute('''
                UPDATE Shipments
                SET status        = ?,
                    delivery_date = ?,
                    route_details = ?,
                    payment_status= ?,
                    driver_id     = ?
                WHERE shipment_id = ?
            ''', (
                new_status,
                new_date    if new_date    else None,
                new_route   if new_route   else None,
                new_payment if new_payment else 'unpaid',
                driver_id,
                int(ship_id)
            ))

            # Check if a row was actually updated
            if c.rowcount == 0:
                conn.close()
                self.upd_result_lbl.config(
                    text=f'⚠  No shipment found with ID {ship_id}',
                    fg='red')
                return

            conn.commit()
            conn.close()

            # Log the update
            log_audit(
                self.user['username'],
                'UPDATE_SHIPMENT',
                'Shipments',
                f"Updated shipment ID {ship_id} → "
                f"status:{new_status} payment:{new_payment}"
            )

            self.upd_result_lbl.config(
                text=f'✅ Shipment #{ship_id} updated successfully!',
                fg='green')

            # Refresh the shipments list
            self.load_shipments()

        except Exception as e:
            self.upd_result_lbl.config(
                text=f'❌ Error saving: {e}', fg='red')
            logging.error(f"Update shipment error: {e}")