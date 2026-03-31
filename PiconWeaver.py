import os
import csv
import xml.etree.ElementTree as ET
import shutil
import re
import readline
import glob
import sys
import ftplib
from time import sleep

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
# CORE APPLICATION CLASS
# ==========================================
class PiconWeaver:
    """
    PiconWeaver v2.2 - The Enigma2 Matrix
    Advanced Picon and Service management suite with FTP deployment.
    Fixed: SRP Hex Padding (8A4 style).
    Enhanced: Pre-Organization local cleanup.
    Enhanced: Detailed telemetry and helper texts.
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
{Colors.WARNING}                  Version 2.2 - The Enigma2 Matrix Edition                   {Colors.ENDC}
{Colors.BLUE}==============================================================================={Colors.ENDC}
        """
        print(banner)

    def print_menu(self):
        """Displays the main interactive menu with detailed helper text."""
        print(f"\n{Colors.CYAN}╭─────────────────── ACTION MENU ───────────────────────────────────────────────────╮{Colors.ENDC}")
        print(f"{Colors.CYAN}│{Colors.ENDC} {Colors.BOLD}[1] 📄 Export ALL Services (CSV){Colors.ENDC}        | Generates a full list of all channels   {Colors.CYAN}│{Colors.ENDC}")
        print(f"{Colors.CYAN}│{Colors.ENDC} {Colors.BOLD}[2] ✅ Export FOUND Picons (CSV){Colors.ENDC}        | Lists channels that have a picon file   {Colors.CYAN}│{Colors.ENDC}")
        print(f"{Colors.CYAN}│{Colors.ENDC} {Colors.BOLD}[3] ❌ Export MISSING Picons (CSV){Colors.ENDC}      | Identifies gaps in your picon library   {Colors.CYAN}│{Colors.ENDC}")
        print(f"{Colors.CYAN}│{Colors.ENDC} {Colors.BOLD}[4] 🗂️  Organize Picon Dirs{Colors.ENDC}              | Wipes and rebuilds SAT/SRP/SNP folders  {Colors.CYAN}│{Colors.ENDC}")
        print(f"{Colors.CYAN}│{Colors.ENDC} {Colors.BOLD}[5] 🩹 Heal Missing Picons{Colors.ENDC}              | Imports picons from another folder      {Colors.CYAN}│{Colors.ENDC}")
        print(f"{Colors.CYAN}│{Colors.ENDC} {Colors.BOLD}[6] 📤 FTP Upload to STB{Colors.ENDC}                | Purges STB folder and uploads picons    {Colors.CYAN}│{Colors.ENDC}")
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
    # FEATURE: FTP DEPLOYMENT
    # ------------------------------------------
    def ftp_upload(self):
        """Connects to STB via FTP, purges destination folder, and deploys picons."""
        self.print_header("FTP UPLOAD TO STB")
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

        # Show current local inventory
        available_sats = [d for d in os.listdir(self.picon_dir) if os.path.isdir(os.path.join(self.picon_dir, d)) and d not in ['SRP', 'SNP']]
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
        print(f"\n🚀 {Colors.BOLD}Establishing FTP connection to {ip}...{Colors.ENDC}")
        
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

            # UPLOAD
            print(f"📤 {Colors.CYAN}Deploying {total} picons...{Colors.ENDC}\n")
            for i, file_path in enumerate(payload):
                filename = os.path.basename(file_path)
                with open(file_path, 'rb') as f:
                    ftp.storbinary(f'STOR {filename}', f)
                
                # Progress Telemetry
                percent = int(((i + 1) / total) * 100)
                sys.stdout.write(f"\r{Colors.GREEN}[{'#' * (percent // 2)}{'.' * (50 - (percent // 2))}] {percent}% ({i+1}/{total}){Colors.ENDC}")
                sys.stdout.flush()

            ftp.quit()
            print(f"\n\n🎉 {Colors.BOLD}{Colors.GREEN}Mission Accomplished! Picons deployed.{Colors.ENDC}")

        except Exception as e:
            print(f"\n\n{Colors.FAIL}💥 FTP Connection Failed: {e}{Colors.ENDC}")

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

    def organize_picons(self):
        """
        Organizes the flat picon folder into orbital position subfolders.
        Enhanced: Performs a full cleanup of target folders before copying.
        """
        self.print_header("ORGANIZE PICONS")
        print(f"{Colors.CYAN}Phase 1: Analyzing satellite clusters...{Colors.ENDC}")
        
        # Identify active satellites for this lamedb
        active_sats = set(s['pos_str'] for s in self.services if s['pos_str'] != "Unknown")
        
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
            if s['pos_str'] == "Unknown": continue
            
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
                
        print(f"\n{Colors.GREEN}✔ Done! Successfully organized {organized_count} picons across orbital positions.{Colors.ENDC}")
        self.auto_refresh_csvs()

    def import_alternate_picons(self):
        """Allows merging picons from external packs into your local master library."""
        self.print_header("HEAL MISSING PICONS")
        print(f"{Colors.CYAN}Point the script to a backup folder or new picon pack.")
        print(f"Missing picons will be identified and imported automatically.{Colors.ENDC}")
        raw_path = input(f"🔍 Path to external pack [TAB for completion]: ").strip()
        if not raw_path: return
        
        alt_path = os.path.expanduser(raw_path)
        if not os.path.exists(alt_path):
            print(f"{Colors.FAIL}Error: The path '{alt_path}' is unreachable.{Colors.ENDC}")
            return
            
        print(f"⏳ Indexing external files...")
        alt_index = {f.lower(): f for f in os.listdir(alt_path) if f.lower().endswith('.png')}
        print(f"📦 Found {len(alt_index)} potential picons in source.")
                
        import_count = 0
        for s in self.services:
            # Only import if we don't already have it
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
    # MAIN EXECUTION LOOP
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
            elif choice == '4': self.organize_picons()
            elif choice == '5': self.import_alternate_picons()
            elif choice == '6': self.ftp_upload()
            elif choice == 'Q':
                print(f"\n👋 {Colors.CYAN}Exiting PiconWeaver. Signal Locked. Goodbye!{Colors.ENDC}")
                break
            else:
                print(f"{Colors.FAIL}Invalid input. Please choose a number from 1 to 6 or Q.{Colors.ENDC}")

# ==========================================
# BOOTSTRAP
# ==========================================
if __name__ == "__main__":
    try:
        app = PiconWeaver()
        app.run()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.WARNING}⚠️ Terminated by user. Closing connection...{Colors.ENDC}")
        sys.exit(0)
