import sys
import os
import threading
import tkinter as tk
from tkinter import messagebox
from PIL import Image
import customtkinter as ctk

# ============================================================
# Import backend modules 
# ============================================================

# Import modul main_aci dan main_legacy 
try:
    from aci import main_aci
except ImportError:
    main_aci = None  # fallback jika tidak ada

try:
    from legacy import main_legacy
except ImportError:
    main_legacy = None # fallback jika tidak ada

#--------------------------------------------
# Import fungsi-fungsi main_legacy ke GUI #
#--------------------------------------------

# Import Save Credentials Tools
try:
    from legacy.creds.credential_manager import (
        save_credentials as legacy_save_credentials,
        load_credentials as legacy_load_credentials,
        list_profiles as legacy_list_profiles,
    )
except ImportError:
    legacy_save_credentials = None
    legacy_load_credentials = None
    legacy_list_profiles = None


# Import create and save inventory
try:
    from legacy.inventory.inventory import (
        create_inventory as legacy_create_inventory,        # versi CLI (masih bisa dipakai di terminal)
        show_inventory as legacy_show_inventory,
        create_inventory_gui as legacy_create_inventory_gui,  # versi GUI baru
    )
except ImportError:
    legacy_create_inventory = None
    legacy_show_inventory = None
    legacy_create_inventory_gui = None



# Import backup config
try:
    from legacy.backup_config.backup import run_backup as legacy_run_backup
except ImportError:
    legacy_run_backup = None


# Import fungsi ACI
try:
    from aci.healthcheck.checklist_aci import main_healthcheck_aci
except ImportError:
    main_healthcheck_aci = None

# Notes:
# - Fungsi ACI (snapshot, compare, dll) belum  dihubungkan


# ============================================================
# Konfigurasi global 
# ============================================================


ctk.set_appearance_mode("system")          # Pilihan: "dark", "light", "system"
ctk.set_default_color_theme("dark-blue")      # Pilihan: "blue", "green", "dark-blue"


class NetworkToolsApp(ctk.CTk):
    # Class utama aplikasi GUI 

    def __init__(self):
        super().__init__()

        # Pengaturan window dasar
        self.title("MANTOOLS v.1.0 - GUI ")
        self.iconbitmap("assets/logo_mantools.ico")
        self.geometry("1000x600")
        self.minsize(900, 500)

        # Simpan state menu aktif 
        self.active_menu = tk.StringVar(value="dashboard")

        # Layout grid utama: kolom 0 = sidebar, kolom 1 = konten
        self.grid_columnconfigure(0, weight=0)   # Sidebar
        self.grid_columnconfigure(1, weight=1)   # Konten utama
        self.grid_rowconfigure(0, weight=1)

        # Buat sidebar dan main frame
        self._create_sidebar()
        self._create_main_frame()

        # Untuk Tampilkan tampilan awal (dashboard)
        self.show_dashboard()



    def _run_in_thread(self, target, *args, **kwargs):
        # Helper untuk menjalankan fungsi blocking di thread terpisah
        # supaya GUI tidak freeze saat menjalankan tools.
        t = threading.Thread(target=target, args=args, kwargs=kwargs, daemon=True)
        t.start()

    # ========================================================
    # Sidebar / Navigasi
    # ========================================================

    def _create_sidebar(self):
        #  sidebar kiri untuk navigasi menu utama (Dashboard, Legacy, ACI).
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        # Logo 
        from PIL import Image
        logo = ctk.CTkImage(Image.open("assets/mastersystem.png"), size=(200,100))  # sesuaikan ukuran
        ctk.CTkLabel(
            self.sidebar,
            image=logo,
            text="",     
        ).pack(pady=(16,24))

        # Judul 
        title_label = ctk.CTkLabel(
            self.sidebar,
            text="MANTOOLS\nMSI Punya Bosque ",
            font=ctk.CTkFont(size=17, weight="bold"),
            justify="center"
        )
        title_label.pack(pady=(16, 24))

        # Tombol navigasi utama
        btn_dashboard = ctk.CTkButton(
            self.sidebar,
            text="Dashboard",
            command=self.show_dashboard,
        )
        btn_dashboard.pack(fill="x", padx=12, pady=4)

        btn_legacy = ctk.CTkButton(
            self.sidebar,
            text="Legacy Tools",
            command=self.show_legacy_tools,
        )
        btn_legacy.pack(fill="x", padx=12, pady=4)

        btn_aci = ctk.CTkButton(
            self.sidebar,
            text="ACI Tools",
            command=self.show_aci_tools,
        )
        btn_aci.pack(fill="x", padx=12, pady=4)

        btn_iosxr_tools = ctk.CTkButton(
            self.sidebar,
            text="IOS-XR Tools",
            command=self.show_iosxr_tools,
        )
        btn_iosxr_tools.pack(fill="x", padx=12, pady=4)
        
        btn_about= ctk.CTkButton(
            self.sidebar,
            text="About",
            command=self.show_about,
        )
        btn_about.pack(fill="x", padx=12, pady=4)        
        
        
        # footer apps
        footer_label = ctk.CTkLabel(
            self.sidebar,
            text="v1.0\n Mantools ",
            font=ctk.CTkFont(size=11),
            justify="center",
        )
        footer_label.pack(side="bottom", pady=8)

    # ========================================================
    # Main content frame
    # ========================================================

    def _create_main_frame(self):
        #  main frame di kanan tempat tampilan konten halaman.
        self.main_frame = ctk.CTkFrame(self, corner_radius=0)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)

    def _clear_main_frame(self):
        # Untuk Menghapus semua widget yang ada di main_frame saat mengganti halaman.
        for widget in self.main_frame.winfo_children():
            widget.destroy()

    # ========================================================
    # Halaman Dashboard
    # ========================================================

    def show_about(self):
        # Menampilkan halaman About
        self.active_menu.set("About")
        self._clear_main_frame()

        container = ctk.CTkFrame(self.main_frame)
        container.grid(row=0, column=0, sticky="nsew", padx=24, pady=24)
        container.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            container,
            text="About This Apllication",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        title.grid(row=0, column=0, sticky="w", pady=(0, 12))

        desc = ctk.CTkLabel(
            container,
            text=(
                "Mantools Developer Team: \n"
                "- \n"
                "- \n"
                "- \n"
                "All Right Reserved to PT. Mastersystem Infotama Tbk.\n"
            ),
            justify="left",
        )
        desc.grid(row=1, column=0, sticky="w")

    def show_dashboard(self):
        # Menampilkan halaman Dashboard awal.
        self.active_menu.set("dashboard")
        self._clear_main_frame()

        container = ctk.CTkFrame(self.main_frame)
        container.grid(row=0, column=0, sticky="nsew", padx=24, pady=24)
        container.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            container,
            text="Welcome to MANTOOLS Network Automation",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        title.grid(row=0, column=0, sticky="w", pady=(0, 12))

        desc = ctk.CTkLabel(
            container,
            text=(
                "Gunakan menu di sidebar untuk memilih jenis tools:\n"
                "- Legacy Tools: inventory, backup config, dsb.\n"
                "- ACI Tools: snapshot, health-check, compare snapshot.\n\n"
            ),
            justify="left",
        )
        desc.grid(row=1, column=0, sticky="w")

        quick_frame = ctk.CTkFrame(container)
        quick_frame.grid(row=2, column=0, sticky="ew", pady=(16, 0))
        quick_frame.grid_columnconfigure((0, 1), weight=1)

        btn_q_legacy = ctk.CTkButton(
            quick_frame,
            text="Add Customer Name",
            command=self.show_customer_input_form,
        )
        btn_q_legacy.grid(row=0, column=0, padx=4, pady=4, sticky="ew")

        btn_q_aci = ctk.CTkButton(
            quick_frame,
            text="Create/Update Inventory Legacy",
            command=self.show_legacy_inventory_page,
        )
        btn_q_aci.grid(row=0, column=1, padx=4, pady=4, sticky="ew")

    # ========================================================
    # Customer Input Form (GUI)
    # ========================================================

    def show_customer_input_form(self):
        # Form simple untuk input Customer Name
        self._clear_main_frame()

        from legacy.customer_context import get_customer_name, set_customer_name

        container = ctk.CTkFrame(self.main_frame)
        container.grid(row=0, column=0, sticky="nsew", padx=24, pady=24)
        container.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            container,
            text="Set Customer Name",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        title.grid(row=0, column=0, sticky="w", pady=(0, 12))

        current = get_customer_name()
        ctk.CTkLabel(
            container,
            text=f"Current Customer: {current}",
        ).grid(row=1, column=0, sticky="w", pady=(0, 12))

        # Input field
        self.customer_entry = ctk.CTkEntry(container, placeholder_text="Enter new customer name")
        self.customer_entry.grid(row=2, column=0, sticky="ew", pady=8)

        def save_customer():
            name = self.customer_entry.get().strip()
            if not name:
                messagebox.showerror("Error", "Customer name tidak boleh kosong.")
                return
            
            set_customer_name(name)
            messagebox.showinfo("Saved", f"Customer name saved: {name}")

        ctk.CTkButton(
            container,
            text="Save Customer Name",
            command=save_customer
        ).grid(row=3, column=0, sticky="ew", pady=8)



    # ========================================================
    # Legacy Tools - Create / Update Inventory (GUI Form)
    # ========================================================

    def show_legacy_inventory_page(self):
        """
        Halaman GUI untuk membuat / update inventory.
        - Menggunakan credentials dari credential_manager (profile 'default').
        - IP list diinput via Textbox (satu IP per baris).
        """
        if legacy_create_inventory_gui is None:
            messagebox.showerror(
                "Module Not Found",
                "Fungsi 'create_inventory_gui' tidak bisa diimport.\n"
                "Cek modul legacy.inventory.inventory.",
            )
            return

        if legacy_load_credentials is None:
            messagebox.showerror(
                "Module Not Found",
                "Fungsi 'load_credentials' tidak bisa diimport.\n"
                "Cek modul legacy.creds.credential_manager.",
            )
            return

        # Ambil credential default
        username, password = legacy_load_credentials()
        if not username or not password:
            messagebox.showwarning(
                "Credentials Required",
                "Belum ada credentials yang disimpan.\n"
                "Silakan isi dan simpan credentials dulu di menu 'Save Credentials'.",
            )
            return

        # Bersihkan main_frame 
        self._clear_main_frame()

        container = ctk.CTkFrame(self.main_frame)
        container.grid(row=0, column=0, sticky="nsew", padx=24, pady=24)
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(3, weight=1)

        title = ctk.CTkLabel(
            container,
            text="Create / Update Device Inventory",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title.grid(row=0, column=0, sticky="w", pady=(0, 8))

        # Info credentials yang dipakai
        cred_label = ctk.CTkLabel(
            container,
            text=f"Using credentials profile 'default' → {username}",
            font=ctk.CTkFont(size=11),
        )
        cred_label.grid(row=1, column=0, sticky="w", pady=(0, 8))

        # Label IP list
        ip_label = ctk.CTkLabel(
            container,
            text="Device IP list (satu IP per baris):",
        )
        ip_label.grid(row=2, column=0, sticky="w")

        # Textbox IP
        ip_textbox = ctk.CTkTextbox(container, height=150)
        ip_textbox.grid(row=3, column=0, sticky="nsew", pady=(4, 8))

        # Area untuk summary hasil
        result_label = ctk.CTkLabel(
            container,
            text="Result:",
            anchor="w",
        )
        result_label.grid(row=4, column=0, sticky="w", pady=(8, 0))

        result_text = ctk.CTkTextbox(container, height=80)
        result_text.grid(row=5, column=0, sticky="nsew", pady=(4, 8))

        # --- Fungsi internal untuk menjalankan inventory di thread terpisah ---
        def run_inventory_job():
            raw_text = ip_textbox.get("1.0", "end")
            ip_list = [line.strip() for line in raw_text.splitlines() if line.strip()]

            if not ip_list:
                messagebox.showerror("Error", "IP list tidak boleh kosong.")
                return

            # Bersihkan hasil lama
            result_text.delete("1.0", "end")
            result_text.insert("end", "Running inventory...\n")

            def job():
                try:
                    results = legacy_create_inventory_gui(
                        ip_list,
                        username,
                        password,
                        save_creds=False,      # EDITABLE AREA: bisa diubah jadi True kalau mau overwrite credentials 
                        profile_name="default" # EDITABLE AREA
                    )
                except Exception as e:
                    # Update GUI harus lewat main thread → pakai .after
                    self.after(0, lambda: messagebox.showerror("Error", f"Gagal menjalankan inventory:\n{e}"))
                    return

                # Fungsi untuk update result_text di main thread
                def update_result():
                    result_text.delete("1.0", "end")

                    result_text.insert("end", "=== Inventory Result ===\n\n")

                    if results["added"]:
                        result_text.insert("end", "Added:\n")
                        for item in results["added"]:
                            result_text.insert(
                                "end",
                                f"  - {item['hostname']} ({item['ip']}, {item['os']})\n"
                            )
                        result_text.insert("end", "\n")

                    if results["updated"]:
                        result_text.insert("end", "Updated:\n")
                        for item in results["updated"]:
                            result_text.insert(
                                "end",
                                f"  - {item['hostname']} ({item['ip']}, {item['os']})\n"
                            )
                        result_text.insert("end", "\n")

                    if results["failed"]:
                        result_text.insert("end", "Failed:\n")
                        for item in results["failed"]:
                            result_text.insert(
                                "end",
                                f"  - {item['ip']} → {item['reason']}\n"
                            )
                        result_text.insert("end", "\n")

                    result_text.insert("end", "Done.\n")

                self.after(0, update_result)

            # Jalankan di thread supaya GUI tidak freeze
            self._run_in_thread(job)

        # Tombol Run
        run_button = ctk.CTkButton(
            container,
            text="Run Inventory",
            command=run_inventory_job,
        )
        run_button.grid(row=6, column=0, sticky="ew", pady=(4, 4))

        # Tombol Back
        back_button = ctk.CTkButton(
            container,
            text="Back to Legacy Menu",
            command=self.show_legacy_tools,
        )
        back_button.grid(row=7, column=0, sticky="ew", pady=(4, 0))


    # ========================================================
    # Halaman Legacy Tools (Menampilkan Button Legacy Tools)
    # ========================================================

    def show_legacy_tools(self):
        # Menampilkan halaman menu Legacy Tools.
        # Setting tombol-tombol untuk panggil fungsi backend Legacy.
        self.active_menu.set("legacy")
        self._clear_main_frame()

        container = ctk.CTkFrame(self.main_frame)
        container.grid(row=0, column=0, sticky="nsew", padx=24, pady=24)
        container.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            container,
            text="Legacy Network Tools",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title.grid(row=0, column=0, sticky="w", pady=(0, 12))

        subtitle = ctk.CTkLabel(
            container,
            text="Pilih menu yang ingin dijalankan:",
            justify="left",
        )
        subtitle.grid(row=1, column=0, sticky="w", pady=(0, 12))

        btn_frame = ctk.CTkFrame(container)
        btn_frame.grid(row=2, column=0, sticky="ew")
        btn_frame.grid_columnconfigure(0, weight=1)

        # --------------------------------------------------------
        # Tambah / kurangi tombol Legacy Tools
        # --------------------------------------------------------

        # Tombol Save Credentials 
        ctk.CTkButton(
            btn_frame,
            text="Save Credentials",
            command=self.show_legacy_credentials_page,
        ).grid(row=1, column=0, sticky="ew", pady=4)


        # Tombol Create / Update Inventory
        ctk.CTkButton(
            btn_frame,
            text="Create / Update Inventory",
            command=self.show_legacy_inventory_page,
        ).grid(row=2, column=0, sticky="ew", pady=4)

        # Tombol Backup Device Config
        ctk.CTkButton(
            btn_frame,
            text="Backup Device Config",
            command=self._handle_legacy_backup,
        ).grid(row=3, column=0, sticky="ew", pady=4)

        # Tombol Show Inventory List
        ctk.CTkButton(
            btn_frame,
            text="Show Inventory List",
            command=self._handle_legacy_show_inventory,
        ).grid(row=4, column=0, sticky="ew", pady=4)

        info = ctk.CTkLabel(
            container,
            text=(),
            justify="left",
            font=ctk.CTkFont(size=11),
        )
        info.grid(row=3, column=0, sticky="w", pady=(16, 0))

    # ==============================================================================
    # Legacy Handlers (untuk integrasi antara tombol dan pemanggilan tools)
    # ==============================================================================

    # ========================================================
    # Legacy Tools - Save Credentials (GUI Form)
    # ========================================================

    def show_legacy_credentials_page(self):
        """
        Halaman form untuk menyimpan credentials ke credential_manager.
        Interaksi full via GUI, tanpa terminal.
        """
        if legacy_save_credentials is None:
            messagebox.showerror(
                "Module Not Found",
                "Fungsi 'save_credentials' tidak bisa diimport.\n"
                "Cek modul legacy.creds.credential_manager.",
            )
            return

        # Bersihkan tampilan utama 
        self._clear_main_frame()

        container = ctk.CTkFrame(self.main_frame)
        container.grid(row=0, column=0, sticky="nsew", padx=24, pady=24)
        container.grid_columnconfigure(0, weight=1)

        # Judul
        title = ctk.CTkLabel(
            container,
            text="Save Credentials (Legacy Tools)",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title.grid(row=0, column=0, sticky="w", pady=(0, 12))

        # EDITABLE AREA: default profile name
        default_profile = "default"

        # Label + Entry Profile Name
        ctk.CTkLabel(
            container,
            text="Profile Name:",
        ).grid(row=1, column=0, sticky="w")

        profile_entry = ctk.CTkEntry(container)
        profile_entry.insert(0, default_profile)
        profile_entry.grid(row=2, column=0, sticky="ew", pady=(0, 8))

        # Label + Entry Username
        ctk.CTkLabel(
            container,
            text="Username:",
        ).grid(row=3, column=0, sticky="w")

        username_entry = ctk.CTkEntry(container)
        username_entry.grid(row=4, column=0, sticky="ew", pady=(0, 8))

        # Label + Entry Password (masked)
        ctk.CTkLabel(
            container,
            text="Password:",
        ).grid(row=5, column=0, sticky="w")

        password_entry = ctk.CTkEntry(container, show="*")
        password_entry.grid(row=6, column=0, sticky="ew", pady=(0, 12))

        # --- Fungsi internal untuk menyimpan credentials ---
        def on_save_clicked():
            profile_name = profile_entry.get().strip()
            username = username_entry.get().strip()
            password = password_entry.get().strip()

            if not profile_name:
                messagebox.showerror("Error", "Profile name tidak boleh kosong.")
                return
            if not username:
                messagebox.showerror("Error", "Username tidak boleh kosong.")
                return
            if not password:
                messagebox.showerror("Error", "Password tidak boleh kosong.")
                return

            try:
                # Panggil backend  untuk simpan ke file terenkripsi
                legacy_save_credentials(profile_name, username, password)
                messagebox.showinfo(
                    "Success",
                    f"Credentials untuk profile '{profile_name}' berhasil disimpan.",
                )
            except Exception as e:
                messagebox.showerror(
                    "Error",
                    f"Gagal menyimpan credentials:\n{e}"
                )

        # Tombol Save
        save_button = ctk.CTkButton(
            container,
            text="Save Credentials",
            command=on_save_clicked,
        )
        save_button.grid(row=7, column=0, sticky="ew", pady=(4, 4))

        # Tombol Back ke Legacy Menu
        back_button = ctk.CTkButton(
            container,
            text="Back to Legacy Menu",
            command=self.show_legacy_tools,
        )
        back_button.grid(row=8, column=0, sticky="ew", pady=(4, 0))

        self._run_in_thread(_run)

    def _handle_legacy_inventory(self):
        # Handler tombol "Create / Update Inventory".
        # Memanggil fungsi create_inventory() dari legacy.inventory.inventory.
        if legacy_create_inventory is None:
            messagebox.showerror(
                "Module Not Found",
                "Fungsi 'create_inventory' tidak bisa diimport.\n"
                "Cek modul legacy.inventory.inventory.",
            )
            return

        def _run():
            try:
                legacy_create_inventory()
            except Exception as e:
                messagebox.showerror("Error", f"Error saat Create/Update Inventory:\n{e}")

        self._run_in_thread(_run)

    def _handle_legacy_backup(self):
        # Handler tombol "Backup Device Config".
        # Memanggil fungsi run_backup() dari legacy.backup_config.backup.
        if legacy_run_backup is None:
            messagebox.showerror(
                "Module Not Found",
                "Fungsi 'run_backup' tidak bisa diimport.\n"
                "Cek modul legacy.backup_config.backup.",
            )
            return

        def _run():
            try:
                legacy_run_backup()
            except Exception as e:
                messagebox.showerror("Error", f"Error saat Backup Config:\n{e}")

        self._run_in_thread(_run)

    def _handle_legacy_show_inventory(self):
        # Handler tombol "Show Inventory List".
        # Memanggil fungsi show_inventory() dari legacy.inventory.inventory.
        if legacy_show_inventory is None:
            messagebox.showerror(
                "Module Not Found",
                "Fungsi 'show_inventory' tidak bisa diimport.\n"
                "Cek modul legacy.inventory.inventory.",
            )
            return

        def _run():
            try:
                legacy_show_inventory()
            except Exception as e:
                messagebox.showerror("Error", f"Error saat Show Inventory:\n{e}")

        self._run_in_thread(_run)

    # ========================================================
    # Halaman ACI Tools (Menampilkan Button ACI Tools)
    # ========================================================

    def show_aci_tools(self):
        # Menampilkan halaman menu ACI Tools.
        self.active_menu.set("aci")
        self._clear_main_frame()

        container = ctk.CTkFrame(self.main_frame)
        container.grid(row=0, column=0, sticky="nsew", padx=24, pady=24)
        container.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            container,
            text="ACI Tools",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title.grid(row=0, column=0, sticky="w", pady=(0, 12))

        subtitle = ctk.CTkLabel(
            container,
            text="Pilih menu ACI Tools yang ingin dijalankan:",
            justify="left",
        )
        subtitle.grid(row=1, column=0, sticky="w", pady=(0, 12))

        btn_frame = ctk.CTkFrame(container)
        btn_frame.grid(row=2, column=0, sticky="ew")
        btn_frame.grid_columnconfigure(0, weight=1)

        # ----------------------------------------------------
        #  Tambah / kurangi tombol ACI Tools
        # ----------------------------------------------------
        
        # Tombol untuk menjalankan ACI Health Check langsung
        ctk.CTkButton(
            btn_frame,
            text="Run ACI Health Check",
            command=self._handle_aci_healthcheck,
        ).grid(row=1, column=0, sticky="ew", pady=4)

        # Tombol (Snapshot, Compare, dll) masih Oncheck integrasi penuh ke GUI
        ctk.CTkButton(
            btn_frame,
            text="Take Snapshot (TODO: Integrasi GUI)",
            command=self._handle_aci_snapshot_todo,
        ).grid(row=2, column=0, sticky="ew", pady=4)

        ctk.CTkButton(
            btn_frame,
            text="Compare Snapshots (TODO: Integrasi GUI)",
            command=self._handle_aci_compare_todo,
        ).grid(row=3, column=0, sticky="ew", pady=4)

        info = ctk.CTkLabel(
            container,
            text=(),
            justify="left",
            font=ctk.CTkFont(size=11),
        )
        info.grid(row=3, column=0, sticky="w", pady=(16, 0))

    # ========================================================
    # ACI Handlers
    # ========================================================

    def _handle_aci_healthcheck(self):
        # Handler tombol "Run ACI Health Check".
        # Memanggil main_healthcheck_aci() dari aci.healthcheck.checklist_aci.
        # Catatan: fungsi ini masih memakai input CLI (APIC, user, dll). Pelu Integrasi
        if main_healthcheck_aci is None:
            messagebox.showerror(
                "Module Not Found",
                "Fungsi 'main_healthcheck_aci' tidak bisa diimport.\n"
                "Cek modul aci.healthcheck.checklist_aci.",
            )
            return

        def _run():
            try:
                main_healthcheck_aci()
            except Exception as e:
                messagebox.showerror("Error", f"Error saat ACI Health Check:\n{e}")

        self._run_in_thread(_run)

    def _handle_aci_snapshot_todo(self):
        # Handler placeholder untuk "Take Snapshot" ACI.
        # TODO: Integrasi dengan fungsi snapshot setelah input APIC, kredensial, dll.
        messagebox.showinfo(
            "TODO",
        )

    def _handle_aci_compare_todo(self):
        # Handler placeholder untuk "Compare Snapshots".
        # TODO: Integrasi dengan fungsi compare snapshot setelah flow pemilihan file.
        messagebox.showinfo(
            "TODO",
        )

    # ========================================================
    # Halaman IOS-XR Tools 
    # ========================================================

    def show_iosxr_tools(self):
        # Menampilkan halaman menu IOS-XR Tools.
        self.active_menu.set("IOS-XR")
        self._clear_main_frame()

        container = ctk.CTkFrame(self.main_frame)
        container.grid(row=0, column=0, sticky="nsew", padx=24, pady=24)
        container.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            container,
            text="IOS-XR Tools",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title.grid(row=0, column=0, sticky="w", pady=(0, 12))

        subtitle = ctk.CTkLabel(
            container,
            text="Pilih IOS-XR Tools yang ingin dijalankan:",
            justify="left",
        )
        subtitle.grid(row=1, column=0, sticky="w", pady=(0, 12))

        btn_frame = ctk.CTkFrame(container)
        btn_frame.grid(row=2, column=0, sticky="ew")
        btn_frame.grid_columnconfigure(0, weight=1)

        # ----------------------------------------------------
        #  Tambah / kurangi tombol IOS-XR Tools
        # ----------------------------------------------------
        
        ctk.CTkButton(
            btn_frame,
            text="Atlas (TODO: Integrasi GUI)",
            command=self._handle_aci_snapshot_todo,
        ).grid(row=1, column=0, sticky="ew", pady=4)

        ctk.CTkButton(
            btn_frame,
            text="CRCell (TODO: Integrasi GUI)",
            command=self._handle_aci_snapshot_todo,
        ).grid(row=2, column=0, sticky="ew", pady=4)

        ctk.CTkButton(
            btn_frame,
            text="Snipe (TODO: Integrasi GUI)",
            command=self._handle_aci_compare_todo,
        ).grid(row=3, column=0, sticky="ew", pady=4)

        ctk.CTkButton(
            btn_frame,
            text="Xray (TODO: Integrasi GUI)",
            command=self._handle_aci_compare_todo,
        ).grid(row=4, column=0, sticky="ew", pady=4)


        info = ctk.CTkLabel(
            container,
            text=(),
            justify="left",
            font=ctk.CTkFont(size=11),
        )
        info.grid(row=3, column=0, sticky="w", pady=(16, 0))
        
        
        
# ============================================================
# Entry point run GUI
# ============================================================

def main():
    #  main untuk aplikasi GUI.
    app = NetworkToolsApp()
    app.mainloop()


if __name__ == "__main__":
    main()
