import sys
import os
import threading
import tkinter as tk
from tkinter import messagebox, filedialog
from PIL import Image
import customtkinter as ctk
from datetime import datetime
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


# Import snapshot (Take Snapshot + Healthcheck)
try:
    from legacy.lib.snapshot import take_snapshot as legacy_take_snapshot
except ImportError:
    legacy_take_snapshot = None


# Import compare snapshots
try:
    from legacy.lib.compare import compare_snapshots as legacy_compare_snapshots
except ImportError:
    legacy_compare_snapshots = None


# Import Mantools Online (collect_devices_data) - sama seperti di main_legacy
try:
    from legacy.lib.utils import collect_devices_data as legacy_collect_devices_data
except ImportError:
    legacy_collect_devices_data = None

# Import fungsi ACI
try:
    from aci.healthcheck.checklist_aci import main_healthcheck_aci
except ImportError:
    main_healthcheck_aci = None

# Notes:
# - Fungsi ACI (snapshot, compare, dll) belum  dihubungkan


# Import ATLAS GUI function
try:
    from sp_tools.Atlas_v1.Atlas_10 import run_atlas_gui
except Exception:
    run_atlas_gui = None


# Import CRCel GUI function
try:
    from sp_tools.CRCell_v1.CRC_Cell_15 import run_crc_gui
except ImportError:
    run_crc_gui = None

# Import Snipe GUI function
try:
    from sp_tools.Snipe_v1.snipe_R import run_snipe_gui
except ImportError:
    run_snipe_gui = None

# Import xray GUI function
try:
    from sp_tools.Xray_v1.xray_8 import run_xray_gui
except ImportError:
    run_xray_gui = None


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
        self.title("MANTOOLS MOBILE v.1.0 - GUI ")
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
        logo = ctk.CTkImage(Image.open("assets/mantools.png"), size=(120,120))  # sesuaikan ukuran
        ctk.CTkLabel(
            self.sidebar,
            image=logo,
            text="",     
        ).pack(pady=(16,20))

        # Judul 
        title_label = ctk.CTkLabel(
            self.sidebar,
            text="MANTOOLS MOBILE ",
            font=ctk.CTkFont(size=14, weight="bold"),
            justify="center"
        )
        title_label.pack(pady=(1,1))

        # Subjudul
        subtitle_label = ctk.CTkLabel(
            self.sidebar,
            text=" Advanced Network Automation Tools",
            font=ctk.CTkFont(size=12, weight="bold"),
            justify="center",
        )
        subtitle_label.pack(pady=(1,1))

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
            text="SP Tools",
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
            text="v1.0\n Mantools Mobile ",
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
            text="Powered By",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        title.grid(row=0, column=0, sticky="w", pady=(0, 12))

        # Add an image below the title.
        self._add_about_image(container, filename="mastersystem.png", size=(240,120), justify="center")
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
        desc.grid(row=2, column=0, sticky="w")

    def _add_about_image(self, container, filename: str = "mastersystem.png", size=(240, 120), justify: str = "center"):
        """
        Add an image to the About page below the title.

        Parameters:
        - container: the parent frame where the image will be placed.
        - filename: filename located inside the `assets/` folder (e.g. 'logo.png').
        - size: tuple (width, height) in pixels for the displayed image.
        - justify: one of 'left', 'center', 'right' to control placement.
        """
        # Resolve path inside the assets folder
        img_path = os.path.join("assets", filename)

        # Determine grid sticky based on justify
        sticky_map = {
            "left": "w",
            "center": "n",
            "right": "e",
        }
        sticky = sticky_map.get(justify, "n")

        if not os.path.exists(img_path):
            # Show a small notice if image not found
            ctk.CTkLabel(container, text=f"(Image not found: {img_path})", font=ctk.CTkFont(size=10)).grid(row=1, column=0, sticky=sticky, pady=(4, 12))
            return

        try:
            pil_img = Image.open(img_path)
            ctk_img = ctk.CTkImage(pil_img, size=size)

            lbl = ctk.CTkLabel(container, image=ctk_img, text="")
            lbl.grid(row=1, column=0, sticky=sticky, pady=(4, 12))

            # Keep a reference so Tk doesn't GC the image
            if not hasattr(self, "_about_images"):
                self._about_images = []
            self._about_images.append(ctk_img)

        except Exception as e:
            ctk.CTkLabel(container, text=f"(Error loading image: {e})", font=ctk.CTkFont(size=10)).grid(row=1, column=0, sticky=sticky, pady=(4, 12))

    def show_dashboard(self):
        # Menampilkan halaman Dashboard awal.
        self.active_menu.set("dashboard")
        self._clear_main_frame()

        container = ctk.CTkFrame(self.main_frame)
        container.grid(row=0, column=0, sticky="nsew", padx=24, pady=24)
        container.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            container,
            text="Welcome to MANTOOLS MOBILE Network Automation",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        title.grid(row=0, column=0, sticky="w", pady=(0, 12))

        desc = ctk.CTkLabel(
            container,
            text=(
                "Use Menu in sidebar to select  tools:\n"
                "- Legacy Tools: inventory, backup config, ect.\n"
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

        # Tombol Show Inventory List
        ctk.CTkButton(
            btn_frame,
            text="Show Inventory List",
            command=self._handle_legacy_show_inventory,
        ).grid(row=3, column=0, sticky="ew", pady=4)

        # Tombol Backup Device Config
        ctk.CTkButton(
            btn_frame,
            text="Backup Device Config",
            command=self._handle_legacy_backup,
        ).grid(row=2, column=0, sticky="ew", pady=4)


        ctk.CTkButton(
            btn_frame,
            text="Take Snapshot + Healthcheck",
            command=self._snapshot_handler_legacy,
        ).grid(row=4, column=0, sticky="ew", pady=4)

        ctk.CTkButton(
            btn_frame,
            text="Compare Snapshots",
            command=self._legacy_custom_tool2,
        ).grid(row=5, column=0, sticky="ew", pady=4)

        ctk.CTkButton(
            btn_frame,
            text="Collect MANTOOLS ONLINE File",
            command=self._legacy_custom_tool3,
        ).grid(row=6, column=0, sticky="ew", pady=4)

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
        # Display backup progress in GUI instead of terminal.
        if legacy_run_backup is None:
            messagebox.showerror(
                "Module Not Found",
                "Fungsi 'run_backup' tidak bisa diimport.\n"
                "Cek modul legacy.backup_config.backup.",
            )
            return

        self._clear_main_frame()

        container = ctk.CTkFrame(self.main_frame)
        container.grid(row=0, column=0, sticky="nsew", padx=24, pady=24)
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(1, weight=1)

        title = ctk.CTkLabel(
            container,
            text="Backup Device Config",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title.grid(row=0, column=0, sticky="w", pady=(0, 12))

        # Create a textbox to display backup progress
        backup_text = ctk.CTkTextbox(container, height=300)
        backup_text.grid(row=1, column=0, sticky="nsew", pady=(4, 8))

        def run_backup_job():
            # Disable button while running
            run_btn.configure(state="disabled")
            backup_text.delete("1.0", "end")
            backup_text.insert("end", "Starting backup process...\n")

            def job():
                try:
                    # Redirect stdout to capture backup output
                    import io
                    import sys
                    from contextlib import redirect_stdout

                    captured_output = io.StringIO()

                    with redirect_stdout(captured_output):
                        legacy_run_backup()

                    output = captured_output.getvalue()
                    
                    def update_display():
                        backup_text.delete("1.0", "end")
                        if output:
                            backup_text.insert("end", output)
                        else:
                            backup_text.insert("end", "Backup completed successfully.\n")
                        backup_text.insert("end", "\nBackup process finished. Check the backup folder for output.\n")
                        messagebox.showinfo(
                            "Done",
                            "Backup Device Config completed."
                        )

                    self.after(0, update_display)

                except Exception as e:
                    def show_error():
                        backup_text.delete("1.0", "end")
                        backup_text.insert("end", f"Backup failed:\n{e}\n")
                        messagebox.showerror("Error", f"Backup failed:\n{e}")

                    self.after(0, show_error)

                finally:
                    self.after(0, lambda: run_btn.configure(state="normal"))

            self._run_in_thread(job)

        run_btn = ctk.CTkButton(
            container,
            text="Run Backup",
            command=run_backup_job,
        )
        run_btn.grid(row=2, column=0, sticky="ew", pady=(4, 4))

        # Back button
        ctk.CTkButton(
            container,
            text="Back to Legacy Menu",
            command=self.show_legacy_tools,
        ).grid(row=3, column=0, sticky="ew", pady=(4, 0))

    def _handle_legacy_show_inventory(self):
        # Handler tombol "Show Inventory List".
        # Display inventory from CSV in GUI instead of terminal.
        self._clear_main_frame()

        container = ctk.CTkFrame(self.main_frame)
        container.grid(row=0, column=0, sticky="nsew", padx=24, pady=24)
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(1, weight=1)

        title = ctk.CTkLabel(
            container,
            text="Device Inventory List",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title.grid(row=0, column=0, sticky="w", pady=(0, 12))

        # Create a textbox to display inventory
        inventory_text = ctk.CTkTextbox(container, height=300)
        inventory_text.grid(row=1, column=0, sticky="nsew", pady=(4, 8))

        # Load and display inventory
        try:
            import csv
            from legacy.creds.credential_manager import load_key
            from cryptography.fernet import Fernet

            inventory_file = "inventory.csv"
            inventory_data = []

            try:
                with open(inventory_file, "r") as f:
                    reader = csv.reader(f, delimiter=";")
                    for row in reader:
                        if len(row) >= 5:
                            inventory_data.append(row)
            except FileNotFoundError:
                inventory_text.insert("end", "No inventory file found.\n")

            if inventory_data:
                # Display header
                header = f"{'Hostname':<20} {'IP':<18} {'OS Type':<12} {'Username':<15}\n"
                inventory_text.insert("end", header)
                inventory_text.insert("end", "-" * 70 + "\n")

                # Display each device
                for row in inventory_data:
                    hostname = row[0] if len(row) > 0 else ""
                    ip = row[1] if len(row) > 1 else ""
                    os_type = row[2] if len(row) > 2 else ""
                    username = row[3] if len(row) > 3 else ""

                    line = f"{hostname:<20} {ip:<18} {os_type:<12} {username:<15}\n"
                    inventory_text.insert("end", line)

                inventory_text.insert("end", "\n" + "=" * 70 + "\n")
                inventory_text.insert("end", f"Total devices: {len(inventory_data)}\n")
            else:
                inventory_text.insert("end", "Inventory is empty.\n")

        except Exception as e:
            inventory_text.insert("end", f"Error loading inventory:\n{e}\n")

        inventory_text.configure(state="disabled")

        # Back button
        ctk.CTkButton(
            container,
            text="Back to Legacy Menu",
            command=self.show_legacy_tools,
        ).grid(row=2, column=0, sticky="ew", pady=(4, 0))

    # ------------------------------------------------------------------
    # Editable placeholder handlers for the custom legacy buttons
    # ------------------------------------------------------------------
    def _snapshot_handler_legacy(self):
        # GUI integration for Take Snapshot + Healthcheck
        # This replaces the placeholder with a small form so the user
        # can provide an optional base directory and run the snapshot
        # from the GUI. The actual work runs in a background thread.

        if legacy_take_snapshot is None:
            messagebox.showerror(
                "Module Not Found",
                "Snapshot module not available.\nEnsure legacy.lib.snapshot is importable."
            )
            return

        # Clear and build a small page for snapshot
        self._clear_main_frame()

        container = ctk.CTkFrame(self.main_frame)
        container.grid(row=0, column=0, sticky="nsew", padx=24, pady=24)
        container.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            container,
            text="Take Snapshot + Healthcheck",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title.grid(row=0, column=0, sticky="w", pady=(0, 8))

        result_label = ctk.CTkLabel(container, text="Result:")
        result_label.grid(row=1, column=0, sticky="w", pady=(4, 0))

        result_text = ctk.CTkTextbox(container, height=140)
        result_text.grid(row=2, column=0, sticky="nsew", pady=(4, 8))

        def run_snapshot_job():
            # Always use default results path (no optional directory input)
            base_dir = None

            # disable button while running
            run_btn.configure(state="disabled")
            result_text.delete("1.0", "end")
            result_text.insert("end", "Running snapshot + healthcheck...\n")

            def job():
                try:
                    # Call the snapshot function (uses progress_callback to stream messages)
                    def progress_cb(msg: str):
                        # append messages to the textbox from the main thread
                        self.after(0, lambda: result_text.insert("end", msg + "\n"))

                    result = legacy_take_snapshot(base_dir, progress_callback=progress_cb)

                    if result is None:
                        # older behavior or unexpected; notify completion
                        self.after(0, lambda: result_text.insert("end", "Completed. Check the results/ folder for outputs.\n"))
                        self.after(0, lambda: messagebox.showinfo("Done", "Snapshot + Healthcheck finished. Check the results folder."))
                    else:
                        snapshot_path, health_path = result

                        def on_done():
                            result_text.insert("end", f"Snapshot file: {snapshot_path}\n")
                            result_text.insert("end", f"Health-check file: {health_path}\n")
                            messagebox.showinfo(
                                "Done",
                                "Snapshot + Healthcheck finished. Paths were added to the result box."
                            )

                        self.after(0, on_done)
                except Exception as e:
                    self.after(0, lambda: messagebox.showerror("Error", f"Snapshot failed:\n{e}"))
                finally:
                    self.after(0, lambda: run_btn.configure(state="normal"))

            # run the snapshot in a background thread
            self._run_in_thread(job)

        run_btn = ctk.CTkButton(
            container,
            text="Run Snapshot + Healthcheck",
            command=run_snapshot_job,
        )
        run_btn.grid(row=3, column=0, sticky="ew", pady=(4, 4))

        # Back button
        ctk.CTkButton(
            container,
            text="Back to Legacy Menu",
            command=self.show_legacy_tools,
        ).grid(row=4, column=0, sticky="ew", pady=(4, 0))

    def _legacy_custom_tool2(self):
        # GUI integration for Compare Snapshots
        # Allows user to select two snapshot files and compare them
        
        if legacy_compare_snapshots is None:
            messagebox.showerror(
                "Module Not Found",
                "Compare module not available.\nEnsure legacy.lib.compare is importable."
            )
            return

        # Clear and build page for snapshot comparison
        self._clear_main_frame()

        container = ctk.CTkFrame(self.main_frame)
        container.grid(row=0, column=0, sticky="nsew", padx=24, pady=24)
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(8, weight=1)

        title = ctk.CTkLabel(
            container,
            text="Compare Snapshots",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title.grid(row=0, column=0, sticky="w", pady=(0, 12))

        # EDITABLE: Default snapshot directory
        # Change this path if snapshot files are stored in a different location
        default_snapshot_dir = os.path.join("results", "legacy", "snapshot")
        
        # File selection info with directory hint
        info_label = ctk.CTkLabel(
            container,
            text=f"📁 Explorer will open: {default_snapshot_dir}/",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        info_label.grid(row=1, column=0, sticky="w", pady=(0, 4))
        
        note_label = ctk.CTkLabel(
            container,
            text="💡 Tip: Edit the directory path above if snapshot files are in a different location",
            font=ctk.CTkFont(size=9),
            text_color="gray"
        )
        note_label.grid(row=2, column=0, sticky="w", pady=(0, 12))

        # First snapshot file selection
        ctk.CTkLabel(
            container,
            text="First Snapshot File:",
        ).grid(row=3, column=0, sticky="w")

        file1_frame = ctk.CTkFrame(container)
        file1_frame.grid(row=4, column=0, sticky="ew", pady=(4, 8))
        file1_frame.grid_columnconfigure(0, weight=1)

        file1_entry = ctk.CTkEntry(file1_frame, placeholder_text="Select first snapshot JSON file")
        file1_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        def browse_file1():
            filename = tk.filedialog.askopenfilename(
                title="Select First Snapshot File",
                initialdir=default_snapshot_dir,
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            )
            if filename:
                file1_entry.delete(0, tk.END)
                file1_entry.insert(0, filename)

        browse_btn1 = ctk.CTkButton(
            file1_frame,
            text="Browse",
            command=browse_file1,
            width=100
        )
        browse_btn1.grid(row=0, column=1, sticky="ew")

        # Second snapshot file selection
        ctk.CTkLabel(
            container,
            text="Second Snapshot File:",
        ).grid(row=5, column=0, sticky="w", pady=(12, 0))

        file2_frame = ctk.CTkFrame(container)
        file2_frame.grid(row=6, column=0, sticky="ew", pady=(4, 12))
        file2_frame.grid_columnconfigure(0, weight=1)

        file2_entry = ctk.CTkEntry(file2_frame, placeholder_text="Select second snapshot JSON file")
        file2_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        def browse_file2():
            filename = tk.filedialog.askopenfilename(
                title="Select Second Snapshot File",
                initialdir=default_snapshot_dir,
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            )
            if filename:
                file2_entry.delete(0, tk.END)
                file2_entry.insert(0, filename)

        browse_btn2 = ctk.CTkButton(
            file2_frame,
            text="Browse",
            command=browse_file2,
            width=100
        )
        browse_btn2.grid(row=0, column=1, sticky="ew")

        # Result label
        result_label = ctk.CTkLabel(container, text="Comparison Result:")
        result_label.grid(row=7, column=0, sticky="w", pady=(12, 4))

        # Result textbox for comparison output
        result_text = ctk.CTkTextbox(container, height=200)
        result_text.grid(row=8, column=0, sticky="nsew", pady=(0, 8))

        def run_compare_job():
            file1 = file1_entry.get().strip()
            file2 = file2_entry.get().strip()

            if not file1 or not file2:
                messagebox.showerror("Error", "Both snapshot file paths must be provided.")
                return

            # Disable button while running
            run_btn.configure(state="disabled")
            result_text.delete("1.0", "end")
            result_text.insert("end", f"Comparing snapshots...\n")
            result_text.insert("end", f"File 1: {file1}\n")
            result_text.insert("end", f"File 2: {file2}\n")
            result_text.insert("end", "-" * 70 + "\n\n")

            def job():
                try:
                    # Load devices from inventory
                    from legacy.lib.utils import load_devices
                    devices = load_devices()
                    
                    # Call the compare function
                    comparison_result = legacy_compare_snapshots(devices, file1, file2)

                    def update_display():
                        result_text.delete("1.0", "end")
                        
                        if comparison_result is None:
                            result_text.insert("end", "✅ No changes detected between snapshots.\n")
                        elif isinstance(comparison_result, dict):
                            # Display structured comparison results by host
                            result_text.insert("end", "=== SNAPSHOT COMPARISON RESULTS ===\n\n")
                            
                            for host, host_data in comparison_result.items():
                                result_text.insert("end", f"\n{'=' * 70}\n")
                                result_text.insert("end", f"Device: {host}\n")
                                result_text.insert("end", f"{'=' * 70}\n\n")
                                
                                # Item Changes
                                item_changes = host_data.get("item_changes", {})
                                if item_changes:
                                    result_text.insert("end", "📝 ITEM CHANGES:\n")
                                    result_text.insert("end", "-" * 70 + "\n")
                                    
                                    for category, changes in item_changes.items():
                                        if changes:
                                            result_text.insert("end", f"\n{category.replace('_', ' ').title()}:\n")
                                            for change in changes:
                                                result_text.insert("end", f"  • {change.get('item', 'N/A')}\n")
                                                result_text.insert("end", f"    Type: {change.get('type', 'N/A')}\n")
                                                result_text.insert("end", f"    Before: {change.get('before', 'N/A')}\n")
                                                result_text.insert("end", f"    After: {change.get('after', 'N/A')}\n")
                                    result_text.insert("end", "\n")
                                
                                # Added Items
                                added_items = host_data.get("added_items", {})
                                if added_items:
                                    result_text.insert("end", "➕ ADDED ITEMS:\n")
                                    result_text.insert("end", "-" * 70 + "\n")
                                    
                                    for category, items in added_items.items():
                                        if items:
                                            result_text.insert("end", f"\n{category.replace('_', ' ').title()}:\n")
                                            for item in items:
                                                result_text.insert("end", f"  • {item.get('item', 'N/A')}\n")
                                                result_text.insert("end", f"    Details: {item.get('details', 'N/A')}\n")
                                    result_text.insert("end", "\n")
                                
                                # Removed Items
                                removed_items = host_data.get("removed_items", {})
                                if removed_items:
                                    result_text.insert("end", "➖ REMOVED ITEMS:\n")
                                    result_text.insert("end", "-" * 70 + "\n")
                                    
                                    for category, items in removed_items.items():
                                        if items:
                                            result_text.insert("end", f"\n{category.replace('_', ' ').title()}:\n")
                                            for item in items:
                                                result_text.insert("end", f"  • {item.get('item', 'N/A')}\n")
                                                result_text.insert("end", f"    Details: {item.get('details', 'N/A')}\n")
                                    result_text.insert("end", "\n")
                        else:
                            # If result is a string or other format, just display it
                            result_text.insert("end", f"{comparison_result}\n")
                        
                        messagebox.showinfo("Done", "Snapshot comparison completed.")

                    self.after(0, update_display)

                except FileNotFoundError as e:
                    def show_error():
                        result_text.delete("1.0", "end")
                        result_text.insert("end", f"File not found:\n{e}\n")
                        messagebox.showerror("Error", f"One or both snapshot files not found:\n{e}")
                    
                    self.after(0, show_error)

                except Exception as e:
                    def show_error():
                        result_text.delete("1.0", "end")
                        result_text.insert("end", f"Comparison failed:\n{e}\n")
                        messagebox.showerror("Error", f"Comparison failed:\n{e}")
                    
                    self.after(0, show_error)

                finally:
                    self.after(0, lambda: run_btn.configure(state="normal"))

            # Run comparison in background thread
            self._run_in_thread(job)

        run_btn = ctk.CTkButton(
            container,
            text="Compare Snapshots",
            command=run_compare_job,
        )
        run_btn.grid(row=9, column=0, sticky="ew", pady=(4, 4))

        # Back button
        ctk.CTkButton(
            container,
            text="Back to Legacy Menu",
            command=self.show_legacy_tools,
        ).grid(row=10, column=0, sticky="ew", pady=(4, 0))

    def _legacy_custom_tool3(self):
        
        #Collect MANTOOLS ONLINE File (Mantools Online)
        #----------------------------------------------
        # Pastikan fungsi backend tersedia
        if legacy_collect_devices_data is None:
            messagebox.showerror(
                "Module Not Found",
                "Fungsi collect_devices_data tidak tersedia.\n"
                "Pastikan legacy.lib.utils dapat di-import."
            )
            return

        # Bangun UI halaman Mantools Online
        self._clear_main_frame()

        container = ctk.CTkFrame(self.main_frame)
        container.grid(row=0, column=0, sticky="nsew", padx=24, pady=24)
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(1, weight=1)

        title = ctk.CTkLabel(
            container,
            text="Collect MANTOOLS ONLINE File",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title.grid(row=0, column=0, sticky="w", pady=(0, 12))

        info = ctk.CTkLabel(
            container,
            text=(
                "This will run the Legacy Mantools Online tool and collect data\n"
                "for all devices listed in inventory.csv. Output files will be\n"
                "saved under results/<customer>/legacy/mantools/<date>/."
            ),
            justify="left",
            font=ctk.CTkFont(size=11),
        )
        info.grid(row=1, column=0, sticky="w", pady=(0, 8))

        # Textbox untuk log / progres
        progress_text = ctk.CTkTextbox(container, height=320)
        progress_text.grid(row=2, column=0, sticky="nsew", pady=(4, 8))

        def run_collect_job():
            # Disable tombol selama job berjalan
            run_btn.configure(state="disabled")
            progress_text.configure(state="normal")
            progress_text.delete("1.0", "end")
            progress_text.insert("end", "Starting Mantools Online collect job...\n")

            def job():
                try:
                    # Tentukan lokasi output berdasarkan logika di collect_devices_data()
                    try:
                        from legacy.customer_context import get_customer_name
                        customer_name = get_customer_name()
                    except Exception:
                        customer_name = "default"

                    timestamp = datetime.now().strftime("%d%m%Y")
                    out_dir = os.path.join(
                        "results",
                        customer_name,
                        "legacy",
                        "mantools",
                        timestamp,
                    )

                    # Log rencana folder output sebelum eksekusi
                    def log_start():
                        progress_text.insert(
                            "end",
                            f"Output directory will be: {out_dir}\n"
                        )
                        progress_text.insert(
                            "end",
                            "Running legacy collect_devices_data()...\n\n"
                        )
                        progress_text.see("end")
                    self.after(0, log_start)

                    # Panggil backend CLI-style function (sama seperti main_legacy)
                    try:
                        # base_dir=None -> sama seperti main_legacy (pakai 'results' default)
                        legacy_collect_devices_data(None)
                    except Exception as e:
                        def on_error():
                            progress_text.insert(
                                "end",
                                f"ERROR while running Mantools Online:\n{e}\n"
                            )
                            progress_text.see("end")
                            messagebox.showerror(
                                "Collect Failed",
                                f"Collect Mantools Online failed:\n{e}"
                            )
                            run_btn.configure(state="normal")
                        self.after(0, on_error)
                        return

                    # Jika sukses
                    def on_finished():
                        progress_text.insert("end", "\nCollect job completed.\n")
                        progress_text.insert("end", f"Files saved to: {out_dir}\n")
                        progress_text.see("end")
                        progress_text.configure(state="disabled")
                        messagebox.showinfo(
                            "Collect Completed",
                            f"Collect Mantools Online completed.\n"
                            f"Files saved to:\n{out_dir}"
                        )
                        run_btn.configure(state="normal")
                    self.after(0, on_finished)

                except Exception as e:
                    # Fallback jika ada error tak terduga
                    def on_unexpected():
                        progress_text.insert(
                            "end",
                            f"Unexpected error while running job:\n{e}\n"
                        )
                        progress_text.see("end")
                        messagebox.showerror(
                            "Unexpected Error",
                            f"Unexpected error while running Mantools Online:\n{e}"
                        )
                        run_btn.configure(state="normal")
                    self.after(0, on_unexpected)

            # Jalankan di thread terpisah supaya GUI tidak freeze
            self._run_in_thread(job)

        # Tombol Run Collect
        run_btn = ctk.CTkButton(
            container,
            text="Run Collect",
            command=run_collect_job,
        )
        run_btn.grid(row=3, column=0, sticky="ew", pady=(4, 4))

        # Tombol Back
        ctk.CTkButton(
            container,
            text="Back to Legacy Menu",
            command=self.show_legacy_tools,
        ).grid(row=4, column=0, sticky="ew", pady=(4, 0))

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
        try:
            from aci.healthcheck.checklist_aci import ACIHealthChecker
        except Exception:
            messagebox.showerror(
                "Module Not Found",
                "Fungsi 'ACIHealthChecker' tidak bisa diimport.\n"
                "Cek modul aci.healthcheck.checklist_aci.",
            )
            return

        # Build UI for ACI Health Check parameters
        self._clear_main_frame()

        container = ctk.CTkFrame(self.main_frame)
        container.grid(row=0, column=0, sticky="nsew", padx=24, pady=24)
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(3, weight=1)

        title = ctk.CTkLabel(
            container,
            text="Run ACI Health Check",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title.grid(row=0, column=0, sticky="w", pady=(0, 12))

        # Create a temporary instance to read default values
        try:
            tmp = ACIHealthChecker()
            def_apic = tmp.DEFAULT_APIC_IP
            def_user = tmp.DEFAULT_USERNAME
            def_pass = tmp.DEFAULT_PASSWORD
            def_health = tmp.DEFAULT_HEALTH_THRESHOLD
            def_cpu = tmp.DEFAULT_CPU_MEM_THRESHOLD
            def_interface = tmp.DEFAULT_INTERFACE_ERROR_THRESHOLD
        except Exception:
            def_apic = ""
            def_user = ""
            def_pass = ""
            def_health = 90
            def_cpu = 75
            def_interface = 0

        # APIC IP
        ctk.CTkLabel(container, text="APIC IP:").grid(row=1, column=0, sticky="w")
        apic_entry = ctk.CTkEntry(container)
        apic_entry.insert(0, def_apic)
        apic_entry.grid(row=2, column=0, sticky="ew", pady=(4, 8))

        # Username
        ctk.CTkLabel(container, text="Username:").grid(row=3, column=0, sticky="w")
        user_entry = ctk.CTkEntry(container)
        user_entry.insert(0, def_user)
        user_entry.grid(row=4, column=0, sticky="ew", pady=(4, 8))

        # Password
        ctk.CTkLabel(container, text="Password:").grid(row=5, column=0, sticky="w")
        pass_entry = ctk.CTkEntry(container, show="*")
        pass_entry.insert(0, def_pass)
        pass_entry.grid(row=6, column=0, sticky="ew", pady=(4, 8))

        # Thresholds frame
        thr_frame = ctk.CTkFrame(container)
        thr_frame.grid(row=7, column=0, sticky="ew", pady=(8, 4))
        thr_frame.grid_columnconfigure((0,1,2), weight=1)

        ctk.CTkLabel(thr_frame, text="Health %").grid(row=0, column=0, sticky="w")
        health_entry = ctk.CTkEntry(thr_frame, width=60)
        health_entry.insert(0, str(def_health))
        health_entry.grid(row=1, column=0, sticky="ew", padx=4)

        ctk.CTkLabel(thr_frame, text="CPU/Mem %").grid(row=0, column=1, sticky="w")
        cpu_entry = ctk.CTkEntry(thr_frame, width=60)
        cpu_entry.insert(0, str(def_cpu))
        cpu_entry.grid(row=1, column=1, sticky="ew", padx=4)

        ctk.CTkLabel(thr_frame, text="Interface Err Threshold").grid(row=0, column=2, sticky="w")
        intf_entry = ctk.CTkEntry(thr_frame, width=60)
        intf_entry.insert(0, str(def_interface))
        intf_entry.grid(row=1, column=2, sticky="ew", padx=4)

        # Small helper note next to thresholds
        note_lbl = ctk.CTkLabel(container, text="Please Adjust thresholds before run", font=ctk.CTkFont(size=12), text_color="gray")
        note_lbl.grid(row=8, column=0, sticky="w", pady=(4, 4))

        # Output area with a vertical scrollbar and reduced height so Run button stays visible
        out_frame = ctk.CTkFrame(container)
        out_frame.grid(row=9, column=0, sticky="nsew", pady=(4, 8))
        out_frame.grid_columnconfigure(0, weight=1)
        out_frame.grid_rowconfigure(0, weight=1)

        output_text = ctk.CTkTextbox(out_frame, height=160)
        output_text.grid(row=0, column=0, sticky="nsew")

        # Add a vertical scrollbar bound to the textbox
        try:
            scrollbar = ctk.CTkScrollbar(out_frame, orientation="vertical", command=output_text.yview)
            scrollbar.grid(row=0, column=1, sticky="ns", padx=(6,0))
            output_text.configure(yscrollcommand=scrollbar.set)
        except Exception:
            # If customtkinter scrollbar is not available, fall back silently
            pass

        def run_job():
            run_btn.configure(state="disabled")
            output_text.configure(state="normal")
            output_text.delete("1.0", "end")
            output_text.insert("end", "Starting ACI Health Check...\n")

            def worker():
                try:
                    apic_ip = apic_entry.get().strip()
                    username = user_entry.get().strip()
                    password = pass_entry.get().strip()
                    try:
                        health_thr = int(health_entry.get().strip())
                    except Exception:
                        health_thr = def_health
                    try:
                        cpu_thr = int(cpu_entry.get().strip())
                    except Exception:
                        cpu_thr = def_cpu
                    try:
                        intf_thr = int(intf_entry.get().strip())
                    except Exception:
                        intf_thr = def_interface

                    checker = ACIHealthChecker()

                    # Capture console output
                    import io
                    from contextlib import redirect_stdout, redirect_stderr

                    # Live stream writer that appends to the GUI textbox via self.after
                    class GuiStream:
                        def __init__(self, textbox, app):
                            self.textbox = textbox
                            self.app = app

                        def write(self, s):
                            if not s:
                                return

                            def append(text=s):
                                try:
                                    self.textbox.configure(state="normal")
                                    self.textbox.insert("end", text)
                                    self.textbox.see("end")
                                    self.textbox.configure(state="disabled")
                                except Exception:
                                    pass

                            # Schedule append on the main thread
                            self.app.after(0, append)

                        def flush(self):
                            return

                    stream = GuiStream(output_text, self)

                    # Temporarily replace sys.exit to avoid terminating the whole app
                    orig_exit = sys.exit
                    def fake_exit(code=0):
                        raise RuntimeError(f"sys.exit({code}) called")
                    sys.exit = fake_exit

                    try:
                        with redirect_stdout(stream), redirect_stderr(stream):
                            # Call login via checker.apic_login to get cookies
                            cookies = checker.apic_login(apic_ip, username, password)
                            if not cookies:
                                raise RuntimeError("Login to APIC failed. Check credentials and connectivity.")

                            # Prepare components
                            api_client = checker.APIClient(apic_ip, cookies, checker.console)
                            data_processor = checker.DataProcessor()
                            report_generator = checker.ReportGenerator(
                                checker.console, health_thr, cpu_thr, intf_thr
                            )
                            data_saver = checker.DataSaver(checker.console)

                            # Run the same sequence as run_health_check
                            from rich.progress import Progress, SpinnerColumn, TextColumn
                            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
                                progress.add_task(description="Collecting APIC health data...", total=None)
                                apic_raw = api_client.fetch_apic_health()

                                progress.add_task(description="Collecting node information...", total=None)
                                top_raw = api_client.fetch_top_system()

                                progress.add_task(description="Checking for faults...", total=None)
                                faults_raw = api_client.fetch_faults()

                                progress.add_task(description="Collecting CPU/Memory data...", total=None)
                                cpu_raw, mem_raw = api_client.fetch_cpu_mem()

                                progress.add_task(description="Checking fabric health...", total=None)
                                fabric_raw = api_client.fetch_fabric_health()

                                progress.add_task(description="Checking FCS errors...", total=None)
                                fcs_raw = api_client.fetch_crc_errors()

                                progress.add_task(description="Checking CRC errors...", total=None)
                                crc_raw = api_client.fetch_crc_errors()

                                progress.add_task(description="Collecting drop errors...", total=None)
                                drop_raw = api_client.fetch_drop_errors()

                                progress.add_task(description="Collecting output errors...", total=None)
                                output_raw = api_client.fetch_output_errors()

                            # Process
                            apic_nodes = data_processor.process_apic_data(apic_raw) if apic_raw else []
                            leaf_spine_nodes = (
                                data_processor.process_leaf_spine(
                                    top_raw, cpu_raw if cpu_raw is not None else {}, mem_raw if mem_raw is not None else {}
                                ) if top_raw else []
                            )
                            faults = data_processor.process_faults(faults_raw, 20) if faults_raw else []
                            fabric_health = data_processor.process_fabric_health(fabric_raw) if fabric_raw else 0
                            fcs_errors = data_processor.process_fcs_errors(fcs_raw, intf_thr) if fcs_raw else []
                            crc_errors = data_processor.process_crc_errors(crc_raw, intf_thr) if crc_raw else []
                            drop_errors = data_processor.process_drop_errors({"imdata": drop_raw}, intf_thr) if drop_raw else []
                            output_errors = data_processor.process_output_errors({"imdata": output_raw}, intf_thr) if output_raw else []

                            # Generate report printing
                            report_generator.print_report(
                                apic_nodes, leaf_spine_nodes, faults, fabric_health, fcs_errors, crc_errors, drop_errors, output_errors
                            )

                            # Save
                            data_dict = {
                                "apic_nodes": apic_nodes,
                                "leaf_spine_nodes": leaf_spine_nodes,
                                "faults": faults,
                                "fcs_errors": fcs_errors,
                                "crc_errors": crc_errors,
                                "drop_errors": drop_errors,
                                "output_errors": output_errors,
                            }

                            # Use get_customer_name if available
                            try:
                                from legacy.customer_context import get_customer_name
                                customer_name = get_customer_name(default="")
                            except Exception:
                                customer_name = ""

                            data_saver.save_report_xlsx(data_dict, customer_name, base_dir=None)

                    finally:
                        sys.exit = orig_exit

                    def done_cb():
                        # Output already streamed into the textbox; ensure it's disabled and notify
                        output_text.configure(state="disabled")
                        messagebox.showinfo("Done", "ACI Health Check completed. See output box for details.")
                        run_btn.configure(state="normal")

                    self.after(0, done_cb)

                except Exception as e:
                    def err_cb():
                        output_text.delete("1.0", "end")
                        output_text.insert("end", f"Error: {e}\n")
                        output_text.configure(state="disabled")
                        messagebox.showerror("Error", f"ACI Health Check failed:\n{e}")
                        run_btn.configure(state="normal")

                    self.after(0, err_cb)

            self._run_in_thread(worker)

        run_btn = ctk.CTkButton(container, text="Run Health Check", command=run_job)
        run_btn.grid(row=10, column=0, sticky="ew", pady=(4, 4))

        # Back button
        ctk.CTkButton(container, text="Back to ACI Menu", command=self.show_aci_tools).grid(row=11, column=0, sticky="ew", pady=(4, 0))

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
    # Halaman SP Tools 
    # ========================================================


    def _sp_tool_atlas(self):
        # Clear halaman utama
        self._clear_main_frame()

        frame = ctk.CTkFrame(self.main_frame)
        frame.grid(row=0, column=0, sticky="nsew", padx=24, pady=24)
        frame.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(frame, text="ATLAS Tool", font=ctk.CTkFont(size=18, weight="bold"))
        title.grid(row=0, column=0, sticky="w", pady=(0, 12))

        # Input fields
        ip_entry = ctk.CTkEntry(frame, placeholder_text="Jumpserver IP")
        ip_entry.grid(row=1, column=0, sticky="ew", pady=4)

        user_entry = ctk.CTkEntry(frame, placeholder_text="Username")
        user_entry.grid(row=2, column=0, sticky="ew", pady=4)

        pass_entry = ctk.CTkEntry(frame, placeholder_text="Password", show="*")
        pass_entry.grid(row=3, column=0, sticky="ew", pady=4)

        port_entry = ctk.CTkEntry(frame, placeholder_text="Port (default 22)")
        port_entry.grid(row=4, column=0, sticky="ew", pady=4)

        dest_entry = ctk.CTkEntry(frame, placeholder_text="Destination Router (e.g. p-d2-bks)")
        dest_entry.grid(row=5, column=0, sticky="ew", pady=4)

        destip_entry = ctk.CTkEntry(frame, placeholder_text="Destination IPv4 (for traceroute)")
        destip_entry.grid(row=6, column=0, sticky="ew", pady=4)

        # Textbox output
        logbox = ctk.CTkTextbox(frame, height=280)
        logbox.grid(row=7, column=0, sticky="nsew", pady=8)

        # Run handler
        def run_job():
            if run_atlas_gui is None:
                messagebox.showerror("Error", "Atlas module not found or cannot be imported.")
                return

            ip = ip_entry.get().strip()
            username = user_entry.get().strip()
            password = pass_entry.get().strip()
            port = port_entry.get().strip() or "22"
            destination = dest_entry.get().strip()
            dest_ip = destip_entry.get().strip()

            if not ip or not username or not password or not destination or not dest_ip:
                messagebox.showwarning("Missing Input", "All fields must be filled!")
                return

            def job():
                try:
                    self.after(0, lambda: logbox.insert("end", "Running ATLAS...\n\n"))
                    traceroute_output = run_atlas_gui(
                        ip, username, password, port,
                        destination=destination,
                        destination_ip=dest_ip
                    )
                    self.after(0, lambda: logbox.insert("end", "\n=== ATLAS COMPLETED ===\n"))
                    self.after(0, lambda: logbox.insert("end", traceroute_output + "\n"))
                    self.after(0, lambda: logbox.see("end"))
                except Exception as e:
                    self.after(0, lambda: logbox.insert("end", f"\nERROR: {e}\n"))
                    self.after(0, lambda: logbox.see("end"))

            self._run_in_thread(job)

        # Run button
        ctk.CTkButton(frame, text="Run ATLAS", command=run_job).grid(row=8, column=0, sticky="ew", pady=6)

        # Back
        ctk.CTkButton(frame, text="Back", command=self.show_iosxr_tools).grid(row=9, column=0, sticky="ew", pady=4)
        
        
    def _show_sp_tool_page(self, tool_name, run_func):
        # page builder untuk SP Tools (CRCell, Snipe, Xray)
        if run_func is None:
            messagebox.showerror(
                "Module Not Found",
                f"Fungsi untuk {tool_name} tidak bisa diimport.\n"
                "Pastikan modul SP Tools tersedia di sp_tools."
            )
            return

        self.active_menu.set("IOS-XR")
        self._clear_main_frame()

        container = ctk.CTkFrame(self.main_frame)
        container.grid(row=0, column=0, sticky="nsew", padx=24, pady=24)
        container.grid_columnconfigure(0, weight=1)
        # baris log_box yang diberi weight supaya area log bisa menyesuaikan
        container.grid_rowconfigure(12, weight=1)

        # Judul
        title = ctk.CTkLabel(
            container,
            text=f"{tool_name} SP Tool",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title.grid(row=0, column=0, sticky="w", pady=(0, 8))

        subtitle = ctk.CTkLabel(
            container,
            text=(
                f"Masukkan parameter jumpserver dan destination untuk {tool_name}.\n"
                
            ),
            justify="left",
        )
        subtitle.grid(row=1, column=0, sticky="w", pady=(0, 12))

        # Jumpserver IP
        ctk.CTkLabel(container, text="Jumpserver IP:").grid(row=2, column=0, sticky="w")
        jump_ip_entry = ctk.CTkEntry(container)
        jump_ip_entry.grid(row=3, column=0, sticky="ew", pady=(0, 8))

        # Username
        ctk.CTkLabel(container, text="Username:").grid(row=4, column=0, sticky="w")
        username_entry = ctk.CTkEntry(container)
        username_entry.grid(row=5, column=0, sticky="ew", pady=(0, 8))

        # Password (masked)
        ctk.CTkLabel(container, text="Password:").grid(row=6, column=0, sticky="w")
        password_entry = ctk.CTkEntry(container, show="*")
        password_entry.grid(row=7, column=0, sticky="ew", pady=(0, 8))

        # Port
        ctk.CTkLabel(container, text="Port (default 22):").grid(row=8, column=0, sticky="w")
        port_entry = ctk.CTkEntry(container)
        port_entry.insert(0, "22")
        port_entry.grid(row=9, column=0, sticky="ew", pady=(0, 8))

        # Destination router / device
        ctk.CTkLabel(container, text="Destination (hostname/IP router):").grid(row=10, column=0, sticky="w")
        dest_entry = ctk.CTkEntry(container)
        dest_entry.grid(row=11, column=0, sticky="ew", pady=(0, 8))

        # Log output
        log_box = ctk.CTkTextbox(container, height=220)
        log_box.grid(row=12, column=0, sticky="nsew", pady=(8, 8))

        def run_clicked():
            jump_ip = jump_ip_entry.get().strip()
            username = username_entry.get().strip()
            password = password_entry.get()
            port = port_entry.get().strip() or "22"
            destination = dest_entry.get().strip()

            # Validasi basic – ini yang memunculkan popup "password belum diisi"
            if not jump_ip or not username or not password or not destination:
                messagebox.showwarning(
                    "Missing Input",
                    "Jumpserver IP, Username, Password, dan Destination harus diisi.",
                )
                return

            log_box.configure(state="normal")
            log_box.delete("1.0", "end")
            log_box.insert("end", f"Starting {tool_name} job...\n")
            log_box.see("end")

            def job():
                import io
                import sys
                from contextlib import redirect_stdout

                output = ""

                try:
                    captured_output = io.StringIO()

                    # Jalankan fungsi backend di dalam redirect_stdout
                    with redirect_stdout(captured_output):
                        result = run_func(
                            jump_ip,
                            username,
                            password,
                            port,
                            destination=destination,
                        )

                    # Ambil output dari stdout
                    output = captured_output.getvalue()

                    # Kalau wrapper mengembalikan string, pakai juga
                    if not output and isinstance(result, str):
                        output = result or ""

                except Exception as e:
                    err_msg = str(e)

                    def err_cb(msg=err_msg):
                        log_box.configure(state="normal")
                        log_box.delete("1.0", "end")
                        log_box.insert("end", f"Error:\n{msg}\n")
                        log_box.configure(state="disabled")
                        log_box.see("end")
                        messagebox.showerror(
                            "Error",
                            f"{tool_name} SP Tools failed:\n{msg}",
                        )
                        run_btn.configure(state="normal")

                    self.after(0, err_cb)
                    return

                def finished(text=output):
                    log_box.configure(state="normal")
                    log_box.delete("1.0", "end")
                    if text:
                        log_box.insert("end", text)
                    else:
                        log_box.insert("end", "\n(No output captured)\n")
                    log_box.configure(state="disabled")
                    log_box.see("end")
                    messagebox.showinfo(
                        f"{tool_name} Completed",
                        f"{tool_name} job finished.",
                    )
                    run_btn.configure(state="normal")

                self.after(0, finished)

            run_btn.configure(state="disabled")
            self._run_in_thread(job)

        run_btn = ctk.CTkButton(
            container,
            text=f"Run {tool_name}",
            command=run_clicked,
        )
        run_btn.grid(row=13, column=0, sticky="ew", pady=(4, 4))

        back_btn = ctk.CTkButton(
            container,
            text="Back to SP Tools Menu",
            command=self.show_iosxr_tools,
        )
        back_btn.grid(row=14, column=0, sticky="ew", pady=(4, 0))

    def show_sp_crcell_page(self):
        self._show_sp_tool_page("CRCell", run_crc_gui)

    def show_sp_snipe_page(self):
        self._show_sp_tool_page("Snipe", run_snipe_gui)

    def show_sp_xray_page(self):
        self._show_sp_tool_page("Xray", run_xray_gui)


    # ========================================================
    # Halaman SP Tools 
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
            text="SP Tools",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title.grid(row=0, column=0, sticky="w", pady=(0, 12))

        subtitle = ctk.CTkLabel(
            container,
            text="Pilih SP Tools yang ingin dijalankan:",
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
            text="Atlas ",
            command=self._sp_tool_atlas,
        ).grid(row=1, column=0, sticky="ew", pady=4)

        ctk.CTkButton(
            btn_frame,
            text="CRCell",
            command=self.show_sp_crcell_page,
        ).grid(row=2, column=0, sticky="ew", pady=4)

        ctk.CTkButton(
            btn_frame,
            text="Snipe",
            command=self.show_sp_snipe_page,
        ).grid(row=3, column=0, sticky="ew", pady=4)

        ctk.CTkButton(
            btn_frame,
            text="Xray",
            command=self.show_sp_xray_page,
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
