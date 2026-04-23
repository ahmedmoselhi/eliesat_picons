import os
import csv
import xml.etree.ElementTree as ET
import shutil
import re
import readline
import glob
import sys
import ftplib
import math
import threading
import concurrent.futures
from time import sleep

# ==========================================
# PYQT6 IMPORTS (GUI Support)
# ==========================================
try:
    from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                                 QHBoxLayout, QTabWidget, QPushButton, QLabel, 
                                 QLineEdit, QFileDialog, QTextEdit, QProgressBar, 
                                 QComboBox, QTableWidget, QTableWidgetItem, QHeaderView, 
                                 QMessageBox, QGroupBox, QAbstractItemView)
    from PyQt6.QtCore import Qt, pyqtSignal, QObject, QTimer
    from PyQt6.QtGui import QColor, QTextCursor, QFont, QImage, QImageReader
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False

# ==========================================
# TERMINAL UI & COLORS ENHANCEMENTS
# ==========================================
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# ==========================================
# AUTOCOMPLETE SETUP
# ==========================================
def path_completer(text, state):
    """Standard readline completer for file/directory paths."""
    line = readline.get_line_buffer().split()
    expanded_text = os.path.expanduser(text)
    return (glob.glob(expanded_text + '*') + [None])[state]

readline.set_completer_delims(' \t\n;')
readline.parse_and_bind("tab: complete")
readline.set_completer(path_completer)

# ==========================================
# CORE APPLICATION CLASS (CLI & Logic)
# ==========================================
class PiconWeaver:
    """
    PiconWeaver v6.0 - The Enigma2 Matrix Edition (PyQt6)
    Advanced Picon and Service management suite with FTP deployment.
    Fixed: GUI Recursion Loop & QTextCursor Type Errors.
    Fixed: SRP Hex Padding (8A4 style).
    Fixed: FTP Upload bottlenecks (Now uses Multithreaded Turbo Mode).
    Enhanced: Pre-Organization local cleanup.
    Enhanced: Automatic CSV generation on startup & Refresh.
    Enhanced: Far West to Far East Satellite Ordering.
    New: Dedicated Heal Tab & Unused Picons Management Tab.
    New: Batch Picon Substitution.
    New: Picon Resizer Tab.
    """

    def __init__(self):
        # Configuration Variables
        self.lamedb_path = 'lamedb'
        self.satellites_path = 'satellites.xml'
        self.picon_dir = 'picons'
        
        # Internal Data Stores
        self.sat_map = {}       
        self.freq_map = {}      
        self.picon_index = {}   
        self.services = []      

    # ------------------------------------------
    # UI & DECORATION METHODS
    # ------------------------------------------
    def print_banner(self):
        """Displays the vibrant ASCII application banner."""
        os.system('cls' if os.name == 'nt' else 'clear')
        banner = f"""{Colors.CYAN}{Colors.BOLD}
 ▓█████▄ ▄▄▄       ██▀███   ██ ▄█▀    ██▓███   ██▓ ▄████▄   ▒█████   ███▄    █ 
 ▒██▀ ██▌▒████▄    ▓██ ▒ ██▒ ██▄█▒   ▓██░  ██▒▓██▒▒██▀ ▀█  ▒██▒  ██▒ ██ ▀█   █ 
 ░██   █▌▒██  ▀█▄  ▓██ ░▄█ ▒▓███▄░   ▓██░ ██▓▒▒██▒▒▓█    ▄ ▒██░  ██▒▓██  ▀█ ██▒
 ░▓█▄   ▌░██▄▄▄▄██ ▒██▀▀█▄  ▓██ █▄   ▒██▄█▓▒ ▒░██░▒▓▓▄ ▄██▒▒██   ██░▓██▒  ▐▌██▒
 ░▒████▓  ▓█   ▓██▒░██▓ ▒██▒▒██▒ █▄  ▒██▒ ░  ░░██░▒ ▓███▀ ░░ ████▓▒░▒██░   ▓██░
  ▒▒▓  ▒  ▒▒   ▓▒█░░ ▒▓ ░▒▓░▒ ▒▒ ▓▒  ▒▓▒░ ░  ░░▓  ░ ░▒ ▒  ░░ ▒░▒░▒░ ░ ▒░   ▒ ▒ 
  ░ ▒  ▒   ▒   ▒▒ ░  ░▒ ░ ▒░░ ░▒ ▒░  ░▒ ░      ▒ ░  ░  ▒     ░ ▒ ▒░ ░ ░░   ░ ▒░
  ░ ░  ░   ░   ▒     ░░   ░ ░ ░░ ░   ░░        ▒ ░░          ░ ░ ░ ▒     ░   ░ ░ 
    ░          ░  ░   ░     ░  ░               ░  ░ ░            ░ ░           ░ 
  ░                                           ░                                
{Colors.ENDC}{Colors.BLUE}==============================================================================={Colors.ENDC}
{Colors.WARNING}               Version 6.0 - The Enigma2 Matrix Edition (PyQt6)              {Colors.ENDC}
{Colors.BLUE}==============================================================================={Colors.ENDC}
        """
        print(banner)

    def print_menu(self):
        """Displays the main interactive menu with detailed helper text."""
        print(f"\n{Colors.CYAN}╭─────────────────── ACTION MENU ───────────────────────────────────────────────────╮{Colors.ENDC}")
        print(f"{Colors.CYAN}│{Colors.ENDC} {Colors.BOLD}[1] 📄 Export ALL Services (CSV){Colors.ENDC}        | Generates a full list of all channels   {Colors.CYAN}│{Colors.ENDC}")
        print(f"{Colors.CYAN}│{Colors.ENDC} {Colors.BOLD}[2] ✅ Export FOUND Picons (CSV){Colors.ENDC}        | Lists channels that have a picon file   {Colors.CYAN}│{Colors.ENDC}")
        print(f"{Colors.CYAN}│{Colors.ENDC} {Colors.BOLD}[3] ❌ Export MISSING Picons (CSV){Colors.ENDC}      | Identifies gaps in your picon library   {Colors.CYAN}│{Colors.ENDC}")
        print(f"{Colors.CYAN}│{Colors.ENDC} {Colors.BOLD}[4] 🗂️  Organize Picon Dirs{Colors.ENDC}              | Wipes/rebuilds local folders (Selective){Colors.CYAN}│{Colors.ENDC}")
        print(f"{Colors.CYAN}│{Colors.ENDC} {Colors.BOLD}[5] 🩹 Heal Missing Picons{Colors.ENDC}              | Imports picons from another folder      {Colors.CYAN}│{Colors.ENDC}")
        print(f"{Colors.CYAN}│{Colors.ENDC} {Colors.BOLD}[6] 📤 FTP Upload to STB{Colors.ENDC}                | Purges STB folder and uploads picons    {Colors.CYAN}│{Colors.ENDC}")
        print(f"{Colors.CYAN}│{Colors.ENDC} {Colors.BOLD}[7] 🗑️  Manage Unused Picons{Colors.ENDC}            | Find and delete orphaned picon files    {Colors.CYAN}│{Colors.ENDC}")
        print(f"{Colors.CYAN}│{Colors.ENDC} {Colors.BOLD}[Q] 🚪 Quit Application{Colors.ENDC}                 | Closes the program                      {Colors.CYAN}│{Colors.ENDC}")
        print(f"{Colors.CYAN}╰───────────────────────────────────────────────────────────────────────────────────╯{Colors.ENDC}")
        print(f"{Colors.GREEN} 💡 INFO: Changes to your picon library trigger an auto-refresh of all CSVs.{Colors.ENDC}\n")

    def print_header(self, title):
        print(f"\n{Colors.BLUE}{Colors.BOLD}=== {title} ==={Colors.ENDC}")

    # ------------------------------------------
    # INITIALIZATION & SETUP
    # ------------------------------------------
    def setup_environment(self):
        """Prompts user for file paths with detailed fallback descriptions."""
        self.print_header("ENVIRONMENT SETUP")
        print(f"{Colors.CYAN}Initial configuration is required. The script needs to know where your")
        print(f"system files are located to map picons to service references.{Colors.ENDC}")
        print(f"{Colors.WARNING}Press [ENTER] to accept defaults.{Colors.ENDC}\n")
        
        lamedb_in = input(f"📂 Path to lamedb (Service List) [{Colors.GREEN}{self.lamedb_path}{Colors.ENDC}]: ").strip()
        self.lamedb_path = os.path.expanduser(lamedb_in) if lamedb_in else self.lamedb_path
        
        sat_in = input(f"🛰️  Path to satellites.xml (Satellite Info) [{Colors.GREEN}{self.satellites_path}{Colors.ENDC}]: ").strip()
        self.satellites_path = os.path.expanduser(sat_in) if sat_in else self.satellites_path
        
        picon_in = input(f"🖼️  Primary Picons Folder (Source) [{Colors.GREEN}{self.picon_dir}{Colors.ENDC}]: ").strip()
        self.picon_dir = os.path.expanduser(picon_in) if picon_in else self.picon_dir

        if not os.path.exists(self.lamedb_path) or not os.path.exists(self.satellites_path):
            print(f"\n{Colors.FAIL}⛔ ERROR: Unable to locate lamedb or satellites.xml.{Colors.ENDC}")
            print(f"{Colors.WARNING}Make sure these files are in the same folder as the script or provide full paths.{Colors.ENDC}")
            sys.exit(1)

        if not os.path.exists(self.picon_dir):
            os.makedirs(self.picon_dir)
            print(f"✨ Created missing source directory: {self.picon_dir}")

    @staticmethod
    def sanitize_snp(name):
        """Standardizes channel names for SNP (Service Name Picon) format."""
        return re.sub(r'[^a-z0-9]', '', name.lower())

    def refresh_picon_index(self):
        """Scans the local directory to build an index of available picons."""
        self.picon_index.clear()
        if os.path.exists(self.picon_dir):
            for f in os.listdir(self.picon_dir):
                if f.lower().endswith('.png'):
                    self.picon_index[f.lower()] = f

    def get_sorted_sats(self):
        """Returns a list of unique satellite strings sorted from Far West to Far East."""
        sats = set()
        for s in self.services:
            if s['pos_str'] != 'Unknown':
                sats.add((s['pos_val'], s['pos_str']))
        # Sort by pos_val (West is negative, East is positive)
        return [x[1] for x in sorted(list(sats), key=lambda item: item[0])]

    def sort_sats_list_west_to_east(self, sat_strs):
        """Sorts an arbitrary list of satellite string names (e.g. '30.0W') from West to East."""
        def sat_to_val(s):
            if s == 'Unknown': return 9999
            try:
                val = float(s[:-1])
                if s.endswith('W'): return -val
                return val
            except: return 9999
        return sorted(sat_strs, key=sat_to_val)

    # ------------------------------------------
    # PARSING LOGIC
    # ------------------------------------------
    def parse_satellites(self):
        """Reads satellites.xml to build a coordinate-to-namespace mapping."""
        print(f"⏳ {Colors.CYAN}Step 1/2: Parsing orbital data from {self.satellites_path}...{Colors.ENDC}")
        try:
            tree = ET.parse(self.satellites_path)
            root = tree.getroot()
            for sat in root.findall('sat'):
                name = sat.get('name')
                pos_int = int(sat.get('position'))
                direction = 'W' if pos_int < 0 else 'E'
                abs_pos = abs(pos_int) / 10.0
                pos_str = f"{abs_pos}{direction}"
                
                # Namespace calculation logic (compatible with Enigma2)
                if pos_int >= 0:
                    ns_val = (pos_int << 16) & 0xFFFFFFFF
                else:
                    ns_val = ((3600 + pos_int) << 16) & 0xFFFFFFFF
                    
                namespace = format(ns_val, '08x').lower()
                info = {'name': name, 'pos': pos_str, 'pos_val': pos_int}
                self.sat_map[namespace] = info
                
                # Transponder-based fallback lookup
                for tp in sat.findall('transponder'):
                    f = tp.get('frequency')[:5]
                    sr = tp.get('symbol_rate')
                    self.freq_map[(f, sr)] = info
            print(f"✅ Loaded {len(self.sat_map)} orbital positions.")
        except Exception as e:
            print(f"{Colors.FAIL}Error parsing satellites.xml: {e}{Colors.ENDC}")

    def parse_lamedb(self):
        """
        Indexes all services found in lamedb. 
        Note: Enigma2 service references use Hex without leading zeros.
        Example: 08A4 -> 8A4
        """
        print(f"⏳ {Colors.CYAN}Step 2/2: Mapping services from {self.lamedb_path}...{Colors.ENDC}")
        self.services.clear()
        tp_data = {}

        if not os.path.exists(self.lamedb_path):
            print(f"{Colors.FAIL}Error: lamedb file not found at {self.lamedb_path}{Colors.ENDC}")
            return

        with open(self.lamedb_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        try:
            # First pass: Link transponders to orbital positions
            curr_tp_key = None
            for line in lines:
                line = line.strip()
                if line == "services": break
                if ":" in line and len(line.split(':')) == 3:
                    curr_tp_key = line.lower()
                elif line.startswith('s ') and curr_tp_key:
                    p = line.split(':')
                    tp_data[curr_tp_key] = (p[0][2:7], p[1])

            # Second pass: Parse specific service names and IDs
            start_idx = lines.index("services\n") + 1
            idx = start_idx
            while idx < len(lines):
                line = lines[idx].strip()
                if not line or line == "end" or line == "/":
                    idx += 1
                    continue
                
                parts = line.split(':')
                if len(parts) == 6:
                    # Convert to uppercase hex and strip leading zeros (Required for correct SRP)
                    sid = format(int(parts[0], 16), 'X')
                    ns = parts[1].lower()
                    tsid = format(int(parts[2], 16), 'X')
                    onid = format(int(parts[3], 16), 'X')
                    stype = format(int(parts[4]), 'X')
                    
                    name = lines[idx+1].strip() if idx + 1 < len(lines) else "Unknown"
                    
                    sat_info = self.sat_map.get(ns)
                    if not sat_info:
                        tp_key = f"{ns}:{parts[2].lower()}:{parts[3].lower()}"
                        sat_info = self.freq_map.get(tp_data.get(tp_key))
                    
                    if not sat_info:
                        sat_info = {'name': 'Unknown', 'pos': 'Unknown', 'pos_val': 9999}

                    clean_ns = format(int(ns, 16), 'X')
                    sr_name = f"1_0_{stype}_{sid}_{tsid}_{onid}_{clean_ns}_0_0_0.png"
                    sn_name = self.sanitize_snp(name) + ".png"

                    self.services.append({
                        'name': name,
                        'sr_full': sr_name,
                        'sn_full': sn_name,
                        'pos_str': sat_info['pos'],
                        'sat_name': sat_info['name'],
                        'pos_val': sat_info['pos_val'],
                        'lookup_sr': sr_name.lower(),
                        'lookup_sn': sn_name.lower()
                    })
                    idx += 3
                else:
                    idx += 1
                    
            self.services.sort(key=lambda x: (x['pos_val'], x['name']))
            print(f"✅ Indexed {len(self.services)} active services.")
            
        except Exception as e:
            print(f"{Colors.FAIL}Critical error during lamedb mapping: {e}{Colors.ENDC}")

    # ------------------------------------------
    # FEATURE: UNUSED PICONS MANAGER
    # ------------------------------------------
    def get_unused_picons(self):
        """Identifies files in the root picon dir that are not linked to any active service."""
        used_keys = set()
        for s in self.services:
            used_keys.add(s['lookup_sr'])
            used_keys.add(s['lookup_sn'])
        
        unused = []
        for k, f in self.picon_index.items():
            if k not in used_keys:
                unused.append(f)
        return sorted(unused)

    def delete_unused_picon(self, filename):
        """Safely deletes an unused picon file and removes it from the index."""
        path = os.path.join(self.picon_dir, filename)
        if os.path.exists(path):
            try:
                os.remove(path)
                if filename.lower() in self.picon_index:
                    del self.picon_index[filename.lower()]
                return True
            except:
                pass
        return False

    def manage_unused_picons_cli(self):
        """CLI Interface for unused picon management."""
        self.print_header("MANAGE UNUSED PICONS")
        unused = self.get_unused_picons()
        if not unused:
            print(f"{Colors.GREEN}No unused or orphaned picons found in the main directory.{Colors.ENDC}")
            return
        
        print(f"{Colors.WARNING}Found {len(unused)} unused picon files eating up space.{Colors.ENDC}")
        action = input(f"Do you want to delete ALL of them? (y/n): {Colors.CYAN}").strip().lower()
        print(f"{Colors.ENDC}", end="")
        if action == 'y':
            deleted = 0
            for f in unused:
                if self.delete_unused_picon(f): deleted += 1
            print(f"{Colors.GREEN}✔ Eradicated {deleted} unused picons.{Colors.ENDC}")
        else:
            print("Operation cancelled. Files preserved.")

    # ------------------------------------------
    # FEATURE: FTP DEPLOYMENT (CLI - Multi-Threaded)
    # ------------------------------------------
    def ftp_upload(self):
        """Connects to STB via FTP, purges destination folder, and deploys picons rapidly using threads."""
        self.print_header("FTP UPLOAD TO STB (TURBO MODE)")
        print(f"{Colors.CYAN}Deploy picons directly to your Set-Top Box.")
        print(f"WARNING: This will delete all .png files in the remote folder before uploading.{Colors.ENDC}")
        print(f"{Colors.WARNING}Enter details or press [ENTER] for defaults.{Colors.ENDC}\n")

        ip = input(f"🌐 STB IP Address [{Colors.GREEN}192.168.1.14{Colors.ENDC}]: ").strip() or "192.168.1.14"
        usr = input(f"👤 Username [{Colors.GREEN}root{Colors.ENDC}]: ").strip() or "root"
        pwd = input(f"🔑 Password [{Colors.GREEN}root{Colors.ENDC}]: ").strip() or "root"
        remote_path = input(f"📁 STB Destination Path [{Colors.GREEN}/media/hdd/picon{Colors.ENDC}]: ").strip() or "/media/hdd/picon"
        
        mode = input(f"🎯 Picon Type (SRP or SNP) [{Colors.GREEN}SRP{Colors.ENDC}]: ").strip().upper() or "SRP"
        if mode not in ['SRP', 'SNP']: 
            print(f"{Colors.WARNING}Input invalid. Using SRP mode.{Colors.ENDC}")
            mode = 'SRP'

        # Show current local inventory and order West to East
        available_sats = [d for d in os.listdir(self.picon_dir) if os.path.isdir(os.path.join(self.picon_dir, d)) and d not in ['SRP', 'SNP']]
        available_sats = self.sort_sats_list_west_to_east(available_sats)
        
        print(f"\n{Colors.BLUE}--- Local Satellite Folders Found ---{Colors.ENDC}")
        if available_sats:
            for s in available_sats:
                print(f" 🛰️  {s}")
        else:
            print(f" {Colors.FAIL}No organized folders found. Please run Option 4 first.{Colors.ENDC}")
            return

        sats_input = input(f"\n🌍 Select satellites (comma-separated or 'all') [{Colors.GREEN}all{Colors.ENDC}]: ").strip().lower() or "all"
        target_sats = available_sats if sats_input == 'all' else [s.strip() for s in sats_input.split(',')]

        # Gather file list for selected satellites
        payload = []
        for sat in target_sats:
            folder_path = os.path.join(self.picon_dir, sat, mode)
            if os.path.exists(folder_path):
                for f in os.listdir(folder_path):
                    if f.endswith('.png'):
                        payload.append(os.path.join(folder_path, f))

        if not payload:
            print(f"\n{Colors.FAIL}⛔ No picons found matching your selection in '{mode}' folders.{Colors.ENDC}")
            return

        total = len(payload)
        print(f"\n🚀 {Colors.BOLD}Establishing Initial Connection to {ip}...{Colors.ENDC}")
        
        try:
            ftp = ftplib.FTP(ip)
            ftp.set_pasv(True)
            ftp.login(usr, pwd)
            
            # Navigate or Create
            try:
                ftp.cwd(remote_path)
            except ftplib.error_perm:
                print(f"{Colors.WARNING}Folder '{remote_path}' not found. Attempting to create...{Colors.ENDC}")
                parts = remote_path.strip('/').split('/')
                curr = ""
                for p in parts:
                    curr += "/" + p
                    try: ftp.mkd(curr)
                    except: pass
                ftp.cwd(remote_path)

            # PURGE DESTINATION
            print(f"🧹 {Colors.FAIL}Cleaning remote folder...{Colors.ENDC}")
            try:
                files_on_stb = ftp.nlst()
                for filename in files_on_stb:
                    if filename.lower().endswith(".png"):
                        ftp.delete(filename)
                print(f"✅ {Colors.GREEN}Remote directory purged.{Colors.ENDC}")
            except:
                print(f"⚠️  Remote directory was empty or list failed.")
            ftp.quit()

            # MULTITHREADED UPLOAD
            print(f"📤 {Colors.CYAN}Deploying {total} picons using Multithreaded Turbo Mode...{Colors.ENDC}\n")
            
            completed = 0
            lock = threading.Lock()

            def upload_chunk(chunk):
                nonlocal completed
                try:
                    t_ftp = ftplib.FTP(ip)
                    t_ftp.set_pasv(True)
                    t_ftp.login(usr, pwd)
                    t_ftp.cwd(remote_path)
                    for file_path in chunk:
                        filename = os.path.basename(file_path)
                        with open(file_path, 'rb') as f:
                            t_ftp.storbinary(f'STOR {filename}', f, blocksize=65536)
                        
                        with lock:
                            completed += 1
                            percent = int((completed / total) * 100)
                            sys.stdout.write(f"\r{Colors.GREEN}[{'#' * (percent // 2)}{'.' * (50 - (percent // 2))}] {percent}% ({completed}/{total}){Colors.ENDC}")
                            sys.stdout.flush()
                    t_ftp.quit()
                except Exception as e:
                    print(f"\n💥 Worker Thread Error: {e}")

            threads_count = 4
            chunk_size = math.ceil(total / threads_count)
            chunks = [payload[i:i + chunk_size] for i in range(0, total, chunk_size)]
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=threads_count) as executor:
                executor.map(upload_chunk, chunks)

            print(f"\n\n🎉 {Colors.BOLD}{Colors.GREEN}Mission Accomplished! Picons deployed at Turbo Speed.{Colors.ENDC}")

        except Exception as e:
            print(f"\n\n{Colors.FAIL}💥 FTP Connection Failed: {e}{Colors.ENDC}")

    # ------------------------------------------
    # FEATURE: FTP DEPLOYMENT (GUI Variant - Multi-Threaded)
    # ------------------------------------------
    def ftp_upload_gui(self, ip, usr, pwd, remote_path, mode, sats_input, ui_callback=None):
        """GUI-driven threaded version of FTP upload to support Qt Progress Bars"""
        self.print_header("FTP UPLOAD TO STB (GUI DEPLOYMENT)")
        
        available_sats = [d for d in os.listdir(self.picon_dir) if os.path.isdir(os.path.join(self.picon_dir, d)) and d not in ['SRP', 'SNP']]
        available_sats = self.sort_sats_list_west_to_east(available_sats)
        
        target_sats = available_sats if sats_input == 'all' else [s.strip() for s in sats_input.split(',')]

        payload = []
        for sat in target_sats:
            folder_path = os.path.join(self.picon_dir, sat, mode)
            if os.path.exists(folder_path):
                for f in os.listdir(folder_path):
                    if f.endswith('.png'):
                        payload.append(os.path.join(folder_path, f))

        if not payload:
            print(f"\n{Colors.FAIL}⛔ No picons found for selected satellites in '{mode}' mode. Run Organization first.{Colors.ENDC}")
            return

        total = len(payload)
        print(f"🚀 {Colors.BOLD}Establishing Initial Connection to {ip}...{Colors.ENDC}")
        
        try:
            ftp = ftplib.FTP(ip)
            ftp.set_pasv(True)
            ftp.login(usr, pwd)
            
            try:
                ftp.cwd(remote_path)
            except ftplib.error_perm:
                print(f"{Colors.WARNING}Creating remote folder '{remote_path}'...{Colors.ENDC}")
                parts = remote_path.strip('/').split('/')
                curr = ""
                for p in parts:
                    curr += "/" + p
                    try: ftp.mkd(curr)
                    except: pass
                ftp.cwd(remote_path)

            print(f"🧹 {Colors.FAIL}Purging existing .png files from destination...{Colors.ENDC}")
            try:
                files_on_stb = ftp.nlst()
                for filename in files_on_stb:
                    if filename.lower().endswith(".png"):
                        ftp.delete(filename)
            except:
                pass
            ftp.quit()

            print(f"📤 {Colors.CYAN}Deploying {total} picons (Turbo Mode)...{Colors.ENDC}")
            
            completed = 0
            lock = threading.Lock()

            def upload_chunk_gui(chunk):
                nonlocal completed
                try:
                    t_ftp = ftplib.FTP(ip)
                    t_ftp.set_pasv(True)
                    t_ftp.login(usr, pwd)
                    t_ftp.cwd(remote_path)
                    for file_path in chunk:
                        filename = os.path.basename(file_path)
                        with open(file_path, 'rb') as f:
                            t_ftp.storbinary(f'STOR {filename}', f, blocksize=65536)
                        
                        with lock:
                            completed += 1
                            percent = int((completed / total) * 100)
                            if ui_callback:
                                ui_callback(percent, f"Turbo Upload: {completed}/{total} - {filename}")
                            else:
                                sys.stdout.write(f"\r{Colors.GREEN}[{'#' * (percent // 2)}{'.' * (50 - (percent // 2))}] {percent}%{Colors.ENDC}")
                                sys.stdout.flush()
                    t_ftp.quit()
                except Exception as e:
                    if ui_callback: ui_callback(int((completed/total)*100), f"Error in worker thread: {e}")
                    else: print(f"\n💥 Worker Thread Error: {e}")

            threads_count = 4
            chunk_size = math.ceil(total / threads_count)
            chunks = [payload[i:i + chunk_size] for i in range(0, total, chunk_size)]
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=threads_count) as executor:
                executor.map(upload_chunk_gui, chunks)

            print(f"\n🎉 {Colors.BOLD}{Colors.GREEN}Mission Accomplished! Picons deployed at Turbo Speed.{Colors.ENDC}")
        except Exception as e:
            print(f"\n💥 {Colors.FAIL}FTP Error: {e}{Colors.ENDC}")

    # ------------------------------------------
    # FEATURE: MANUAL ICON SUBSTITUTION 
    # ------------------------------------------
    def substitute_missing_picon(self, service_dict, replacement_path):
        """Copies an external image, applying expected SRP and SNP names directly to the core picon folder."""
        if service_dict['pos_str'] == "Unknown":
            print(f"{Colors.FAIL}Cannot substitute picons for an Unknown orbital position.{Colors.ENDC}")
            return False
            
        dst_sr = os.path.join(self.picon_dir, service_dict['sr_full'])
        dst_sn = os.path.join(self.picon_dir, service_dict['sn_full'])
        
        try:
            shutil.copy(replacement_path, dst_sr)
            shutil.copy(replacement_path, dst_sn)
            
            # Update internal index
            self.picon_index[service_dict['lookup_sr']] = service_dict['sr_full']
            self.picon_index[service_dict['lookup_sn']] = service_dict['sn_full']
            
            print(f"{Colors.GREEN}✔ Substituted picon for '{service_dict['name']}'{Colors.ENDC}")
            print(f"  {Colors.CYAN}Generated: {service_dict['sr_full']}{Colors.ENDC}")
            print(f"  {Colors.CYAN}Generated: {service_dict['sn_full']}{Colors.ENDC}")
            return True
        except Exception as e:
            print(f"{Colors.FAIL}Substitution Error: {e}{Colors.ENDC}")
            return False

    # ------------------------------------------
    # EXPORT & FILE OPERATIONS
    # ------------------------------------------
    def export_csv(self, mode):
        """Creates detailed CSV reports of your current service and picon status."""
        out_files = {'all': 'all_services.csv', 'found': 'found_picons.csv', 'missing': 'missing_picons.csv'}
        out_name = out_files.get(mode, 'export.csv')
        
        count = 0
        with open(out_name, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(['Channel Name', 'SRP Filename', 'SNP Filename', 'Position', 'Satellite', 'Status'])
            
            for s in self.services:
                p_file = self.picon_index.get(s['lookup_sr']) or self.picon_index.get(s['lookup_sn'])
                status = "Found" if p_file else "Missing"
                
                if (mode == 'all') or (mode == 'found' and p_file) or (mode == 'missing' and not p_file):
                    w.writerow([s['name'], s['sr_full'], s['sn_full'], s['pos_str'], s['sat_name'], status])
                    count += 1
                    
        print(f"  📝 Generated {Colors.GREEN}{out_name}{Colors.ENDC} [{count} entries]")

    def auto_refresh_csvs(self):
        """Helper to ensure CSVs always match the latest library state."""
        print(f"\n🔄 {Colors.CYAN}Syncing database reports with local library...{Colors.ENDC}")
        self.refresh_picon_index() 
        self.export_csv('all')
        self.export_csv('found')
        self.export_csv('missing')
        print(f"✅ Records are now up to date.")

    def organize_picons(self, target_sats_input="all"):
        """
        Organizes the flat picon folder into orbital position subfolders.
        Enhanced in v4.0: Accepts selective satellites to clean and reorganize.
        """
        self.print_header("ORGANIZE PICONS")
        print(f"{Colors.CYAN}Phase 1: Analyzing satellite clusters...{Colors.ENDC}")
        
        active_sats = set(s['pos_str'] for s in self.services if s['pos_str'] != "Unknown")
        
        if target_sats_input.strip().lower() != "all":
            requested = [s.strip() for s in target_sats_input.split(',')]
            active_sats = {s for s in active_sats if s in requested}
            if not active_sats:
                print(f"{Colors.FAIL}No matching satellites found for the input provided.{Colors.ENDC}")
                return

        print(f"{Colors.WARNING}Phase 2: Cleaning up existing directories to ensure data integrity...{Colors.ENDC}")
        for sat in active_sats:
            sat_root = os.path.join(self.picon_dir, sat)
            for sub in ["SRP", "SNP"]:
                target_path = os.path.join(sat_root, sub)
                if os.path.exists(target_path):
                    shutil.rmtree(target_path)
                    print(f" 🗑️  Purged: {sat}/{sub}")

        print(f"{Colors.CYAN}Phase 3: Building directory structure and copying files...{Colors.ENDC}")
        organized_count = 0
        for s in self.services:
            if s['pos_str'] == "Unknown" or s['pos_str'] not in active_sats: continue
            
            source_picon = self.picon_index.get(s['lookup_sr']) or self.picon_index.get(s['lookup_sn'])
            if source_picon:
                source_path = os.path.join(self.picon_dir, source_picon)
                sat_root = os.path.join(self.picon_dir, s['pos_str'])
                srp_dir = os.path.join(sat_root, "SRP")
                snp_dir = os.path.join(sat_root, "SNP")
                
                for d in [srp_dir, snp_dir]:
                    if not os.path.exists(d): os.makedirs(d)
                
                shutil.copy(source_path, os.path.join(srp_dir, s['sr_full']))
                shutil.copy(source_path, os.path.join(snp_dir, s['sn_full']))
                organized_count += 1
                
        print(f"\n{Colors.GREEN}✔ Done! Successfully organized {organized_count} picons across targeted positions.{Colors.ENDC}")
        self.auto_refresh_csvs()

    def import_alternate_picons(self, alt_path=None):
        """Allows merging picons from external packs into your local master library."""
        self.print_header("HEAL MISSING PICONS")
        if not alt_path:
            print(f"{Colors.CYAN}Point the script to a backup folder or new picon pack.")
            print(f"Missing picons will be identified and imported automatically.{Colors.ENDC}")
            raw_path = input(f"🔍 Path to external pack [TAB for completion]: ").strip()
            if not raw_path: return
            alt_path = os.path.expanduser(raw_path)
            
        if not os.path.exists(alt_path):
            print(f"{Colors.FAIL}Error: The path '{alt_path}' is unreachable.{Colors.ENDC}")
            return
            
        print(f"⏳ Indexing external files in {alt_path}...")
        alt_index = {f.lower(): f for f in os.listdir(alt_path) if f.lower().endswith('.png')}
        print(f"📦 Found {len(alt_index)} potential picons in source.")
                
        import_count = 0
        for s in self.services:
            if not self.picon_index.get(s['lookup_sr']) and not self.picon_index.get(s['lookup_sn']):
                found_alt = alt_index.get(s['lookup_sr']) or alt_index.get(s['lookup_sn'])
                if found_alt:
                    src = os.path.join(alt_path, found_alt)
                    dst = os.path.join(self.picon_dir, found_alt)
                    if not os.path.exists(dst):
                        shutil.copy(src, dst)
                        self.picon_index[found_alt.lower()] = found_alt
                        import_count += 1
                        
        print(f"\n{Colors.GREEN}✔ Success! {import_count} gaps healed in your primary library.{Colors.ENDC}")
        self.auto_refresh_csvs()

    # ------------------------------------------
    # MAIN EXECUTION LOOP (CLI Legacy Wrapper)
    # ------------------------------------------
    def run(self):
        """Main application lifecycle controller."""
        self.print_banner()
        self.setup_environment()
        
        self.print_header("INITIALIZING DATA MATRIX")
        self.parse_satellites()
        self.refresh_picon_index()
        self.parse_lamedb()
        self.auto_refresh_csvs()

        while True:
            self.print_menu()
            choice = input(f"👉 Enter your choice: {Colors.CYAN}").strip().upper()
            print(f"{Colors.ENDC}", end="")
            
            if choice == '1': self.export_csv('all')
            elif choice == '2': self.export_csv('found')
            elif choice == '3': self.export_csv('missing')
            elif choice == '4': 
                sats = input(f"🌍 Satellites to organize (comma-separated or 'all') [{Colors.GREEN}all{Colors.ENDC}]: ").strip() or "all"
                self.organize_picons(sats)
            elif choice == '5': self.import_alternate_picons()
            elif choice == '6': self.ftp_upload()
            elif choice == '7': self.manage_unused_picons_cli()
            elif choice == 'Q':
                print(f"\n👋 {Colors.CYAN}Exiting PiconWeaver. Signal Locked. Goodbye!{Colors.ENDC}")
                break
            else:
                print(f"{Colors.FAIL}Invalid input. Please choose a valid option or Q.{Colors.ENDC}")


# ==========================================
# PYQT6 GUI LAYER
# ==========================================
if PYQT6_AVAILABLE:
    MATRIX_QSS = """
    QMainWindow { background-color: #0D0D0D; }
    QWidget { color: #00FF41; font-family: 'Consolas', 'Courier New', monospace; font-size: 13px; }
    QTabWidget::pane { border: 1px solid #0088FF; background-color: #050505; }
    QTabBar::tab { background: #1A1A1A; border: 1px solid #0088FF; padding: 10px 20px; color: #0088FF; border-bottom: none; }
    QTabBar::tab:selected { background: #0088FF; color: #0D0D0D; font-weight: bold; }
    QTabBar::tab:hover { background: #0055AA; color: #FFF; }
    QPushButton { background-color: #1A1A1A; border: 1px solid #00FF41; color: #00FF41; padding: 8px; border-radius: 4px; }
    QPushButton:hover { background-color: #00FF41; color: #0D0D0D; font-weight: bold;}
    QPushButton:pressed { background-color: #00CC33; }
    QLineEdit, QComboBox { background-color: #000000; border: 1px solid #0088FF; color: #00FFFF; padding: 5px; }
    QTextEdit { background-color: #050505; border: 1px solid #00FF41; color: #00FF41; padding: 10px; }
    QGroupBox { border: 1px solid #0088FF; margin-top: 10px; font-weight: bold; padding: 15px 5px 5px 5px; color: #00FFFF;}
    QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
    QTableWidget { background-color: #050505; alternate-background-color: #111111; gridline-color: #0088FF; color: #00FFFF; selection-background-color: #0088FF; selection-color: #000; }
    QHeaderView::section { background-color: #1A1A1A; color: #00FF41; border: 1px solid #0088FF; padding: 5px; }
    QProgressBar { border: 1px solid #00FF41; text-align: center; color: #FFFFFF; font-weight: bold; background: #0D0D0D;}
    QProgressBar::chunk { background-color: #0088FF; }
    """

    class LogSignal(QObject):
        append = pyqtSignal(str)
        
    class ProgressSignal(QObject):
        update = pyqtSignal(int, str)

    class StreamRedirector:
        def __init__(self, signal):
            self.signal = signal
            # Retain access to the original terminal stdout as a fail-safe
            self.original_stdout = sys.__stdout__
            
        def write(self, text):
            if not text: return
            try:
                if '\r' in text:
                    text = text.split('\r')[-1]
                    self.signal.append.emit("OVERWRITE:" + text)
                else:
                    self.signal.append.emit(text)
            except Exception:
                self.original_stdout.write(text)
                
        def flush(self): pass

    def ansi_to_html(text):
        """Converts CLI ANSI Color Codes to GUI Rich Text HTML."""
        html = text.replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br>')
        html = html.replace('\033[95m', '<span style="color:#FF00FF;">') 
        html = html.replace('\033[94m', '<span style="color:#0088FF;">') 
        html = html.replace('\033[96m', '<span style="color:#00FFFF;">') 
        html = html.replace('\033[92m', '<span style="color:#00FF41;">') 
        html = html.replace('\033[93m', '<span style="color:#FFFF00;">') 
        html = html.replace('\033[91m', '<span style="color:#FF0000;">') 
        html = html.replace('\033[0m', '</span>') 
        html = html.replace('\033[1m', '<b>') 
        html = html.replace('\033[4m', '<u>') 
        return html

    class PiconWeaverGUI(QMainWindow):
        def __init__(self, core_app):
            super().__init__()
            self.core = core_app
            
            # Setup Thread-Safe Logging & Progress Signals
            self.log_signal = LogSignal()
            self.log_signal.append.connect(self.append_log)
            self.prog_sig = ProgressSignal()
            self.prog_sig.update.connect(self.update_ftp_progress)
            
            # Redirect stdout to GUI console
            sys.stdout = StreamRedirector(self.log_signal)
            
            self.initUI()
            self.core.print_banner()

            # v6.0 Initial Auto-Launch: Generate CSVs upon start if default paths exist
            QTimer.singleShot(500, self.auto_init)

        def auto_init(self):
            if os.path.exists(self.core.lamedb_path) and os.path.exists(self.core.satellites_path):
                self.init_matrix()

        def initUI(self):
            self.setWindowTitle("PiconWeaver v6.0 - The Enigma2 Matrix Edition")
            self.resize(1200, 900)
            self.setStyleSheet(MATRIX_QSS)

            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            main_layout = QVBoxLayout(central_widget)

            self.tabs = QTabWidget()
            main_layout.addWidget(self.tabs, stretch=2)

            # --- CONSOLE ---
            self.console = QTextEdit()
            self.console.setReadOnly(True)
            self.console.setFont(QFont("Consolas", 10))
            main_layout.addWidget(self.console, stretch=1)

            # Build Tabs
            self.build_setup_tab()
            self.build_operations_tab()
            self.build_heal_tab()
            self.build_substitution_tab()
            self.build_resize_tab()  # New in v6.0
            self.build_unused_tab()
            self.build_ftp_tab()

            # Variables for storing current states
            self.current_missing_services = []
            self.current_found_services = []

        def append_log(self, text):
            """Safely inserts text into the PyQt6 Console, avoiding strict QTextEdit wrapper bugs."""
            try:
                if text.startswith("OVERWRITE:"):
                    text = text.replace("OVERWRITE:", "")
                    cursor = self.console.textCursor()
                    cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
                    cursor.removeSelectedText()
                    self.console.insertHtml(ansi_to_html(text))
                else:
                    cursor = self.console.textCursor()
                    cursor.movePosition(QTextCursor.MoveOperation.End)
                    self.console.setTextCursor(cursor)
                    self.console.insertHtml(ansi_to_html(text))
                    
                    # Ensure scrollbar auto-scrolls to the bottom
                    scrollbar = self.console.verticalScrollBar()
                    scrollbar.setValue(scrollbar.maximum())
                    
                QApplication.processEvents()
            except Exception as e:
                # Direct fallback to standard output to prevent an infinite recursion crash loop
                sys.__stdout__.write(f"{text.replace('OVERWRITE:', '')}\n")
            
        def update_ftp_progress(self, val, msg):
            self.ftp_progress.setValue(val)
            print(f" {Colors.GREEN}► {msg}{Colors.ENDC}")

        # ---------- SHARED HELPER ----------
        def refresh_missing_and_csvs(self):
            """Forces a complete CSV refresh and updates all relevant GUI tables (v6.0 Feature)"""
            self.core.auto_refresh_csvs()
            self.populate_substitution_table()
            self.populate_unused_table()
            self.populate_resize_table()

        # ---------- TAB 1: SETUP ----------
        def build_setup_tab(self):
            tab = QWidget()
            layout = QVBoxLayout(tab)
            
            gb = QGroupBox("Environment Data Paths")
            form = QVBoxLayout()
            
            # Lamedb
            h1 = QHBoxLayout()
            h1.addWidget(QLabel("Lamedb Path:"))
            self.inp_lamedb = QLineEdit(self.core.lamedb_path)
            h1.addWidget(self.inp_lamedb)
            btn1 = QPushButton("Browse")
            btn1.clicked.connect(lambda: self.browse_file(self.inp_lamedb))
            h1.addWidget(btn1)
            form.addLayout(h1)

            # Satellites
            h2 = QHBoxLayout()
            h2.addWidget(QLabel("Satellites.xml:"))
            self.inp_sat = QLineEdit(self.core.satellites_path)
            h2.addWidget(self.inp_sat)
            btn2 = QPushButton("Browse")
            btn2.clicked.connect(lambda: self.browse_file(self.inp_sat))
            h2.addWidget(btn2)
            form.addLayout(h2)

            # Picons
            h3 = QHBoxLayout()
            h3.addWidget(QLabel("Picons Folder:"))
            self.inp_pic = QLineEdit(self.core.picon_dir)
            h3.addWidget(self.inp_pic)
            btn3 = QPushButton("Browse")
            btn3.clicked.connect(lambda: self.browse_folder(self.inp_pic))
            h3.addWidget(btn3)
            form.addLayout(h3)
            
            gb.setLayout(form)
            layout.addWidget(gb)

            btn_init = QPushButton("Initialize Data Matrix")
            btn_init.setFixedHeight(50)
            btn_init.clicked.connect(self.init_matrix)
            layout.addWidget(btn_init)
            layout.addStretch()
            self.tabs.addTab(tab, "⚙️ Setup & Init")

        def browse_file(self, line_edit):
            path, _ = QFileDialog.getOpenFileName(self, "Select File", os.path.expanduser("~"))
            if path: line_edit.setText(path)

        def browse_folder(self, line_edit):
            path = QFileDialog.getExistingDirectory(self, "Select Directory", os.path.expanduser("~"))
            if path: line_edit.setText(path)

        def init_matrix(self):
            self.core.lamedb_path = self.inp_lamedb.text()
            self.core.satellites_path = self.inp_sat.text()
            self.core.picon_dir = self.inp_pic.text()
            
            if not os.path.exists(self.core.picon_dir): os.makedirs(self.core.picon_dir)
            
            self.core.print_header("GUI MATRIX INITIALIZATION")
            self.core.parse_satellites()
            self.core.refresh_picon_index()
            self.core.parse_lamedb()
            self.core.auto_refresh_csvs()
            
            # Populate Satellite Filter Combo Boxes dynamically (Sorted West to East)
            unique_sats = self.core.get_sorted_sats()
            
            for combo in [self.filter_sat_combo, self.resize_sat_combo]:
                combo.blockSignals(True)
                combo.clear()
                combo.addItem("All Satellites")
                combo.addItems(unique_sats)
                combo.blockSignals(False)

            self.populate_substitution_table()
            self.populate_resize_table()
            self.populate_unused_table()

        # ---------- TAB 2: OPERATIONS ----------
        def build_operations_tab(self):
            tab = QWidget()
            layout = QVBoxLayout(tab)
            
            gb1 = QGroupBox("CSV Reporting")
            l1 = QHBoxLayout()
            b_all = QPushButton("📄 Export ALL")
            b_fnd = QPushButton("✅ Export FOUND")
            b_mis = QPushButton("❌ Export MISSING")
            b_all.clicked.connect(lambda: self.core.export_csv('all'))
            b_fnd.clicked.connect(lambda: self.core.export_csv('found'))
            b_mis.clicked.connect(lambda: self.core.export_csv('missing'))
            l1.addWidget(b_all); l1.addWidget(b_fnd); l1.addWidget(b_mis)
            gb1.setLayout(l1)
            layout.addWidget(gb1)

            gb2 = QGroupBox("Data Integrity & Organization")
            l2 = QVBoxLayout()
            
            # Selective Organization Layout
            h_org = QHBoxLayout()
            h_org.addWidget(QLabel("Target Sats (comma-separated or 'all'):"))
            self.inp_org_sats = QLineEdit("all")
            h_org.addWidget(self.inp_org_sats)
            
            b_org = QPushButton("🗂️ Wipe & Re-Organize Local Picons")
            b_org.clicked.connect(self.run_organize)
            h_org.addWidget(b_org)
            
            l2.addLayout(h_org)
            gb2.setLayout(l2)
            layout.addWidget(gb2)
            layout.addStretch()
            self.tabs.addTab(tab, "🛠️ Operations")

        def run_organize(self):
            if not self.core.services:
                print(f"{Colors.FAIL}Initialize Matrix First!{Colors.ENDC}")
                return
            self.core.organize_picons(self.inp_org_sats.text())

        # ---------- TAB 3: HEAL MISSING ----------
        def build_heal_tab(self):
            tab = QWidget()
            layout = QVBoxLayout(tab)
            
            gb = QGroupBox("Import Alternate Picons")
            form = QVBoxLayout()
            lbl = QLabel("Point the script to a backup folder or new picon pack. Missing picons will be identified and imported automatically.")
            form.addWidget(lbl)
            
            h1 = QHBoxLayout()
            h1.addWidget(QLabel("Alternate Path:"))
            self.inp_heal = QLineEdit()
            h1.addWidget(self.inp_heal)
            btn_browse = QPushButton("Browse")
            btn_browse.clicked.connect(lambda: self.browse_folder(self.inp_heal))
            h1.addWidget(btn_browse)
            form.addLayout(h1)
            
            btn_heal = QPushButton("🩹 Execute Heal Process")
            btn_heal.setFixedHeight(50)
            btn_heal.clicked.connect(self.run_heal_tab)
            form.addWidget(btn_heal)
            
            gb.setLayout(form)
            layout.addWidget(gb)
            layout.addStretch()
            
            self.tabs.addTab(tab, "🩹 Heal Missing")

        def run_heal_tab(self):
            if not self.core.services:
                print(f"{Colors.FAIL}Initialize Matrix First!{Colors.ENDC}")
                return
            path = self.inp_heal.text()
            if not path or not os.path.exists(path):
                print(f"{Colors.FAIL}Invalid path selected.{Colors.ENDC}")
                return
            self.core.import_alternate_picons(path)
            self.refresh_missing_and_csvs()

        # ---------- TAB 4: MANUAL SUBSTITUTION ----------
        def build_substitution_tab(self):
            tab = QWidget()
            layout = QVBoxLayout(tab)
            
            lbl = QLabel("List of services currently missing picons. Filter dynamically or select files to inject in batch.")
            layout.addWidget(lbl)

            # Filtering Controls 
            filter_layout = QHBoxLayout()
            
            self.filter_name_input = QLineEdit()
            self.filter_name_input.setPlaceholderText("Filter by Channel Name...")
            self.filter_name_input.textChanged.connect(self.populate_substitution_table)
            
            self.filter_sat_combo = QComboBox()
            self.filter_sat_combo.addItem("All Satellites")
            self.filter_sat_combo.currentIndexChanged.connect(self.populate_substitution_table)
            
            filter_layout.addWidget(QLabel("Name:"))
            filter_layout.addWidget(self.filter_name_input)
            filter_layout.addWidget(QLabel("Sat Position:"))
            filter_layout.addWidget(self.filter_sat_combo)
            layout.addLayout(filter_layout)

            self.sub_table = QTableWidget()
            self.sub_table.setColumnCount(4)
            self.sub_table.setHorizontalHeaderLabels(["Channel Name", "SRP Reference", "Satellite", "Action"])
            self.sub_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            self.sub_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
            self.sub_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
            self.sub_table.setAlternatingRowColors(True)
            # Enable Multiple Selection for Batch processing
            self.sub_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
            self.sub_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
            layout.addWidget(self.sub_table)
            
            btn_layout = QHBoxLayout()
            
            btn_batch = QPushButton("💉 Inject Selected (Batch)...")
            btn_batch.setStyleSheet("background-color: #0055AA; font-weight: bold; color: white;")
            btn_batch.clicked.connect(self.on_batch_substitute_clicked)
            btn_layout.addWidget(btn_batch)
            
            btn_refresh = QPushButton("🔄 Refresh Missing List & CSVs")
            btn_refresh.clicked.connect(self.refresh_missing_and_csvs)
            btn_layout.addWidget(btn_refresh)
            
            layout.addLayout(btn_layout)
            
            self.tabs.addTab(tab, "🖼️ Manual Substitution")

        def populate_substitution_table(self):
            if not self.core.services: return
            self.sub_table.setRowCount(0)
            
            name_filter = self.filter_name_input.text().lower()
            sat_filter = self.filter_sat_combo.currentText()
            
            self.current_missing_services = []
            for s in self.core.services:
                if not (self.core.picon_index.get(s['lookup_sr']) or self.core.picon_index.get(s['lookup_sn'])):
                    if name_filter and name_filter not in s['name'].lower():
                        continue
                    if sat_filter != "All Satellites" and s['pos_str'] != sat_filter:
                        continue
                    self.current_missing_services.append(s)

            self.sub_table.setRowCount(len(self.current_missing_services))
            
            for row, s in enumerate(self.current_missing_services):
                self.sub_table.setItem(row, 0, QTableWidgetItem(s['name']))
                self.sub_table.setItem(row, 1, QTableWidgetItem(s['sr_full']))
                self.sub_table.setItem(row, 2, QTableWidgetItem(s['sat_name']))
                
                btn = QPushButton("Inject...")
                btn.clicked.connect(lambda checked, svc=s: self.on_substitute_clicked(svc))
                self.sub_table.setCellWidget(row, 3, btn)

        def on_substitute_clicked(self, service_dict):
            file_path, _ = QFileDialog.getOpenFileName(self, f"Select Picon for {service_dict['name']}", self.core.picon_dir, "Images (*.png)")
            if file_path:
                success = self.core.substitute_missing_picon(service_dict, file_path)
                if success:
                    self.refresh_missing_and_csvs()

        def on_batch_substitute_clicked(self):
            selected_rows = sorted(list(set([item.row() for item in self.sub_table.selectedItems()])))
            if not selected_rows:
                print(f"{Colors.WARNING}Please select one or more rows from the table first.{Colors.ENDC}")
                return
            
            for row in selected_rows:
                svc = self.current_missing_services[row]
                file_path, _ = QFileDialog.getOpenFileName(self, f"Select Picon for {svc['name']} ({svc['pos_str']})", self.core.picon_dir, "Images (*.png)")
                if file_path:
                    self.core.substitute_missing_picon(svc, file_path)
                else:
                    print(f"{Colors.WARNING}Skipped substitution for '{svc['name']}'.{Colors.ENDC}")
            
            self.refresh_missing_and_csvs()

        # ---------- TAB 5: PICON RESIZER (NEW in v6.0) ----------
        def build_resize_tab(self):
            tab = QWidget()
            layout = QVBoxLayout(tab)
            
            lbl = QLabel("Scale your FOUND picons to match Enigma2 skin requirements (Standard: 220x132).")
            layout.addWidget(lbl)

            # Filtering Controls 
            filter_layout = QHBoxLayout()
            
            self.resize_name_input = QLineEdit()
            self.resize_name_input.setPlaceholderText("Filter by Channel Name...")
            self.resize_name_input.textChanged.connect(self.populate_resize_table)
            
            self.resize_sat_combo = QComboBox()
            self.resize_sat_combo.addItem("All Satellites")
            self.resize_sat_combo.currentIndexChanged.connect(self.populate_resize_table)
            
            filter_layout.addWidget(QLabel("Name:"))
            filter_layout.addWidget(self.resize_name_input)
            filter_layout.addWidget(QLabel("Sat Position:"))
            filter_layout.addWidget(self.resize_sat_combo)
            layout.addLayout(filter_layout)

            self.resize_table = QTableWidget()
            self.resize_table.setColumnCount(4)
            self.resize_table.setHorizontalHeaderLabels(["Channel Name", "SRP Reference", "Satellite", "Picon File"])
            self.resize_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            self.resize_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
            self.resize_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
            self.resize_table.setAlternatingRowColors(True)
            self.resize_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
            self.resize_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
            layout.addWidget(self.resize_table)
            
            controls_layout = QHBoxLayout()
            controls_layout.addWidget(QLabel("Target Width:"))
            self.inp_width = QLineEdit("220")
            self.inp_width.setFixedWidth(60)
            controls_layout.addWidget(self.inp_width)
            
            controls_layout.addWidget(QLabel("Target Height:"))
            self.inp_height = QLineEdit("132")
            self.inp_height.setFixedWidth(60)
            controls_layout.addWidget(self.inp_height)
            
            btn_resize_sel = QPushButton("📐 Resize Selected")
            btn_resize_sel.setStyleSheet("background-color: #0055AA; color: white;")
            btn_resize_sel.clicked.connect(self.resize_selected_picons)
            controls_layout.addWidget(btn_resize_sel)

            btn_resize_all = QPushButton("📐 Resize ALL Filtered")
            btn_resize_all.setStyleSheet("background-color: #550000; color: #FF0000; font-weight: bold;")
            btn_resize_all.clicked.connect(self.resize_all_filtered_picons)
            controls_layout.addWidget(btn_resize_all)
            
            layout.addLayout(controls_layout)
            
            self.tabs.addTab(tab, "📐 Picon Resizer")

        def populate_resize_table(self):
            if not self.core.services: return
            self.resize_table.setRowCount(0)
            
            name_filter = self.resize_name_input.text().lower()
            sat_filter = self.resize_sat_combo.currentText()
            
            self.current_found_services = []
            for s in self.core.services:
                p_file = self.core.picon_index.get(s['lookup_sr']) or self.core.picon_index.get(s['lookup_sn'])
                if p_file:
                    if name_filter and name_filter not in s['name'].lower():
                        continue
                    if sat_filter != "All Satellites" and s['pos_str'] != sat_filter:
                        continue
                    s['active_picon_file'] = p_file
                    self.current_found_services.append(s)

            self.resize_table.setRowCount(len(self.current_found_services))
            
            for row, s in enumerate(self.current_found_services):
                self.resize_table.setItem(row, 0, QTableWidgetItem(s['name']))
                self.resize_table.setItem(row, 1, QTableWidgetItem(s['sr_full']))
                self.resize_table.setItem(row, 2, QTableWidgetItem(s['sat_name']))
                self.resize_table.setItem(row, 3, QTableWidgetItem(s['active_picon_file']))

        def execute_resize(self, service_list, w, h):
            resized = 0
            for svc in service_list:
                filename = svc.get('active_picon_file')
                if not filename: continue
                
                filepath = os.path.join(self.core.picon_dir, filename)
                if not os.path.exists(filepath): continue
                
                img = QImage(filepath)
                if not img.isNull():
                    scaled_img = img.scaled(w, h, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    if scaled_img.save(filepath, "PNG"):
                        resized += 1
            print(f"{Colors.GREEN}✔ Successfully resized {resized} picons to {w}x{h}.{Colors.ENDC}")

        def resize_selected_picons(self):
            selected_rows = sorted(list(set([item.row() for item in self.resize_table.selectedItems()])))
            if not selected_rows: return
            
            try:
                w = int(self.inp_width.text())
                h = int(self.inp_height.text())
            except ValueError:
                print(f"{Colors.FAIL}Width and Height must be integers.{Colors.ENDC}")
                return

            to_resize = [self.current_found_services[r] for r in selected_rows]
            self.execute_resize(to_resize, w, h)

        def resize_all_filtered_picons(self):
            if not self.current_found_services: return
            
            try:
                w = int(self.inp_width.text())
                h = int(self.inp_height.text())
            except ValueError:
                print(f"{Colors.FAIL}Width and Height must be integers.{Colors.ENDC}")
                return

            reply = QMessageBox.question(self, "Confirm Bulk Resize", f"Resize ALL {len(self.current_found_services)} currently filtered picons to {w}x{h}?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.execute_resize(self.current_found_services, w, h)

        # ---------- TAB 6: UNUSED PICONS ----------
        def build_unused_tab(self):
            tab = QWidget()
            layout = QVBoxLayout(tab)
            
            lbl = QLabel("These picon files exist in your root folder but are NOT linked to any active service.")
            layout.addWidget(lbl)
            
            self.unused_table = QTableWidget()
            self.unused_table.setColumnCount(1)
            self.unused_table.setHorizontalHeaderLabels(["Orphaned Picon Filename"])
            self.unused_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            self.unused_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
            layout.addWidget(self.unused_table)
            
            btn_layout = QHBoxLayout()
            
            btn_scan = QPushButton("🔄 Scan Unused")
            btn_scan.clicked.connect(self.populate_unused_table)
            
            btn_del_sel = QPushButton("🗑️ Delete Selected")
            btn_del_sel.setStyleSheet("color: #FF0000; font-weight: bold;")
            btn_del_sel.clicked.connect(self.delete_selected_unused)
            
            btn_del_all = QPushButton("☢️ Delete ALL Unused")
            btn_del_all.setStyleSheet("background-color: #550000; color: #FF0000; font-weight: bold;")
            btn_del_all.clicked.connect(self.delete_all_unused)
            
            btn_layout.addWidget(btn_scan)
            btn_layout.addWidget(btn_del_sel)
            btn_layout.addWidget(btn_del_all)
            layout.addLayout(btn_layout)
            
            self.tabs.addTab(tab, "🧹 Unused Picons")

        def populate_unused_table(self):
            if not self.core.services: return
            unused = self.core.get_unused_picons()
            self.unused_table.setRowCount(len(unused))
            for row, filename in enumerate(unused):
                self.unused_table.setItem(row, 0, QTableWidgetItem(filename))

        def delete_selected_unused(self):
            selected_items = self.unused_table.selectedItems()
            if not selected_items: return
            
            reply = QMessageBox.question(self, "Confirm Deletion", f"Delete {len(selected_items)} selected picons?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                for item in selected_items:
                    filename = item.text()
                    self.core.delete_unused_picon(filename)
                self.populate_unused_table()

        def delete_all_unused(self):
            unused = self.core.get_unused_picons()
            if not unused: return
            
            reply = QMessageBox.question(self, "Confirm Delete ALL", f"Are you sure you want to completely erase ALL {len(unused)} orphaned picons?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                for f in unused:
                    self.core.delete_unused_picon(f)
                self.populate_unused_table()

        # ---------- TAB 7: FTP DEPLOYMENT ----------
        def build_ftp_tab(self):
            tab = QWidget()
            layout = QVBoxLayout(tab)
            
            gb = QGroupBox("FTP Credentials & Payload")
            form = QVBoxLayout()
            
            h1 = QHBoxLayout()
            h1.addWidget(QLabel("STB IP:")); self.inp_ip = QLineEdit("192.168.1.14"); h1.addWidget(self.inp_ip)
            h1.addWidget(QLabel("User:")); self.inp_usr = QLineEdit("root"); h1.addWidget(self.inp_usr)
            h1.addWidget(QLabel("Pass:")); self.inp_pwd = QLineEdit("root"); self.inp_pwd.setEchoMode(QLineEdit.EchoMode.Password); h1.addWidget(self.inp_pwd)
            form.addLayout(h1)

            h2 = QHBoxLayout()
            h2.addWidget(QLabel("STB Target Path:")); self.inp_rem = QLineEdit("/media/hdd/picon"); h2.addWidget(self.inp_rem)
            h2.addWidget(QLabel("Mode:")); self.cmb_mode = QComboBox(); self.cmb_mode.addItems(["SRP", "SNP"]); h2.addWidget(self.cmb_mode)
            form.addLayout(h2)

            h3 = QHBoxLayout()
            h3.addWidget(QLabel("Satellites (comma-separated or 'all'):"))
            self.inp_sats = QLineEdit("all")
            h3.addWidget(self.inp_sats)
            form.addLayout(h3)
            
            gb.setLayout(form)
            layout.addWidget(gb)

            self.ftp_progress = QProgressBar()
            self.ftp_progress.setValue(0)
            layout.addWidget(self.ftp_progress)

            btn_deploy = QPushButton("📤 PURGE DESTINATION & TURBO DEPLOY TO STB")
            btn_deploy.setFixedHeight(60)
            btn_deploy.setStyleSheet("font-size: 14px; font-weight: bold; background-color: #004400;")
            btn_deploy.clicked.connect(self.run_ftp)
            layout.addWidget(btn_deploy)
            layout.addStretch()
            
            self.tabs.addTab(tab, "📤 FTP Deployment")

        def run_ftp(self):
            if not self.core.services:
                print(f"{Colors.FAIL}Matrix not initialized.{Colors.ENDC}")
                return
            
            self.ftp_progress.setValue(0)
            
            def update_progress(val, msg):
                self.prog_sig.update.emit(val, msg)

            # Run the multithreaded FTP logic in a background thread so the GUI remains responsive
            t = threading.Thread(target=self.core.ftp_upload_gui, args=(
                self.inp_ip.text().strip(),
                self.inp_usr.text().strip(),
                self.inp_pwd.text().strip(),
                self.inp_rem.text().strip(),
                self.cmb_mode.currentText(),
                self.inp_sats.text().strip(),
                update_progress
            ))
            t.start()

# ==========================================
# BOOTSTRAP
# ==========================================
if __name__ == "__main__":
    if PYQT6_AVAILABLE:
        app = QApplication(sys.argv)
        core = PiconWeaver()
        gui = PiconWeaverGUI(core)
        gui.show()
        sys.exit(app.exec())
    else:
        # Fallback to CLI if PyQt6 is missing
        try:
            core = PiconWeaver()
            core.run()
        except KeyboardInterrupt:
            print(f"\n\n{Colors.WARNING}⚠️ Terminated by user. Closing connection...{Colors.ENDC}")
            sys.exit(0)
