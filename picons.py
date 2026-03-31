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
    PiconWeaver v2.0 - The Enigma2 Matrix
    Advanced Picon and Service management suite with FTP deployment.
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
{Colors.WARNING}                  Version 2.0 - The Enigma2 Matrix Edition                   {Colors.ENDC}
{Colors.BLUE}==============================================================================={Colors.ENDC}
        """
        print(banner)

    def print_menu(self):
        """Displays the main interactive menu with detailed helper text."""
        print(f"\n{Colors.CYAN}╭─────────────────── ACTION MENU ──────────────────────────────────────────╮{Colors.ENDC}")
        print(f"{Colors.CYAN}│{Colors.ENDC} {Colors.BOLD}[1] 📄 Export ALL Services (CSV){Colors.ENDC}    | Creates 'all_services.csv'          {Colors.CYAN}│{Colors.ENDC}")
        print(f"{Colors.CYAN}│{Colors.ENDC} {Colors.BOLD}[2] ✅ Export FOUND Picons (CSV){Colors.ENDC}    | Creates 'found_picons.csv'          {Colors.CYAN}│{Colors.ENDC}")
        print(f"{Colors.CYAN}│{Colors.ENDC} {Colors.BOLD}[3] ❌ Export MISSING Picons (CSV){Colors.ENDC}  | Creates 'missing_picons.csv'        {Colors.CYAN}│{Colors.ENDC}")
        print(f"{Colors.CYAN}│{Colors.ENDC} {Colors.BOLD}[4] 🗂️  Organize Picon Dirs{Colors.ENDC}         | Builds SAT/SRP and SAT/SNP tree     {Colors.CYAN}│{Colors.ENDC}")
        print(f"{Colors.CYAN}│{Colors.ENDC} {Colors.BOLD}[5] 🩹 Heal Missing Picons{Colors.ENDC}          | Scans external path to fill gaps    {Colors.CYAN}│{Colors.ENDC}")
        print(f"{Colors.CYAN}│{Colors.ENDC} {Colors.BOLD}[6] 📤 FTP Upload to STB{Colors.ENDC}            | Deploy organized picons directly    {Colors.CYAN}│{Colors.ENDC}")
        print(f"{Colors.CYAN}│{Colors.ENDC} {Colors.BOLD}[Q] 🚪 Quit Application{Colors.ENDC}             | Exit PiconWeaver                    {Colors.CYAN}│{Colors.ENDC}")
        print(f"{Colors.CYAN}╰──────────────────────────────────────────────────────────────────────────╯{Colors.ENDC}")
        print(f"{Colors.GREEN} 💡 TIP: CSV files are auto-refreshed after options 4 and 5.{Colors.ENDC}\n")

    def print_header(self, title):
        print(f"\n{Colors.BLUE}{Colors.BOLD}=== {title} ==={Colors.ENDC}")

    # ------------------------------------------
    # INITIALIZATION & SETUP
    # ------------------------------------------
    def setup_environment(self):
        """Prompts user for file paths with default fallbacks."""
        self.print_header("ENVIRONMENT SETUP")
        print(f"{Colors.WARNING}Press [ENTER] to accept the default values shown in brackets.{Colors.ENDC}\n")
        
        lamedb_in = input(f"📂 Path to lamedb [{Colors.GREEN}{self.lamedb_path}{Colors.ENDC}]: ").strip()
        self.lamedb_path = os.path.expanduser(lamedb_in) if lamedb_in else self.lamedb_path
        
        sat_in = input(f"🛰️  Path to satellites.xml [{Colors.GREEN}{self.satellites_path}{Colors.ENDC}]: ").strip()
        self.satellites_path = os.path.expanduser(sat_in) if sat_in else self.satellites_path
        
        picon_in = input(f"🖼️  Path to picons folder [{Colors.GREEN}{self.picon_dir}{Colors.ENDC}]: ").strip()
        self.picon_dir = os.path.expanduser(picon_in) if picon_in else self.picon_dir

        if not os.path.exists(self.lamedb_path) or not os.path.exists(self.satellites_path):
            print(f"\n{Colors.FAIL}⛔ CRITICAL ERROR: Source files not found. Please check paths.{Colors.ENDC}")
            sys.exit(1)

        if not os.path.exists(self.picon_dir):
            os.makedirs(self.picon_dir)
            print(f"✨ Created missing directory: {self.picon_dir}")

    @staticmethod
    def sanitize_snp(name):
        return re.sub(r'[^a-z0-9]', '', name.lower())

    def refresh_picon_index(self):
        self.picon_index.clear()
        if os.path.exists(self.picon_dir):
            for f in os.listdir(self.picon_dir):
                if f.lower().endswith('.png'):
                    self.picon_index[f.lower()] = f

    # ------------------------------------------
    # PARSING LOGIC
    # ------------------------------------------
    def parse_satellites(self):
        print(f"⏳ {Colors.CYAN}Parsing satellite data...{Colors.ENDC}")
        try:
            tree = ET.parse(self.satellites_path)
            root = tree.getroot()
            for sat in root.findall('sat'):
                name = sat.get('name')
                pos_int = int(sat.get('position'))
                direction = 'W' if pos_int < 0 else 'E'
                abs_pos = abs(pos_int) / 10.0
                pos_str = f"{abs_pos}{direction}"
                
                if pos_int >= 0:
                    ns_val = (pos_int << 16) & 0xFFFFFFFF
                else:
                    ns_val = ((3600 + pos_int) << 16) & 0xFFFFFFFF
                    
                namespace = format(ns_val, '08x').lower()
                info = {'name': name, 'pos': pos_str, 'pos_val': pos_int}
                self.sat_map[namespace] = info
                
                for tp in sat.findall('transponder'):
                    f = tp.get('frequency')[:5]
                    sr = tp.get('symbol_rate')
                    self.freq_map[(f, sr)] = info
        except Exception as e:
            print(f"{Colors.FAIL}Error parsing satellites.xml: {e}{Colors.ENDC}")

    def parse_lamedb(self):
        print(f"⏳ {Colors.CYAN}Indexing services matrix...{Colors.ENDC}")
        self.services.clear()
        tp_data = {}

        with open(self.lamedb_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        try:
            curr_tp_key = None
            for line in lines:
                line = line.strip()
                if line == "services": break
                if ":" in line and len(line.split(':')) == 3:
                    curr_tp_key = line.lower()
                elif line.startswith('s ') and curr_tp_key:
                    p = line.split(':')
                    tp_data[curr_tp_key] = (p[0][2:7], p[1])

            start_idx = lines.index("services\n") + 1
            idx = start_idx
            while idx < len(lines):
                line = lines[idx].strip()
                if not line or line == "end" or line == "/":
                    idx += 1
                    continue
                
                parts = line.split(':')
                if len(parts) == 6:
                    sid, ns, tsid, onid, stype = parts[0].upper(), parts[1].lower(), parts[2].upper(), parts[3].upper(), parts[4]
                    name = lines[idx+1].strip() if idx + 1 < len(lines) else "Unknown"
                    
                    sat_info = self.sat_map.get(ns)
                    if not sat_info:
                        tp_key = f"{ns}:{tsid.lower()}:{onid.lower()}"
                        sat_info = self.freq_map.get(tp_data.get(tp_key))
                    
                    if not sat_info:
                        sat_info = {'name': 'Unknown', 'pos': 'Unknown', 'pos_val': 9999}

                    clean_ns = ns.lstrip('0') if ns != '00000000' else '0'
                    sr_name = f"1_0_{int(stype):X}_{sid}_{tsid}_{onid}_{clean_ns.upper()}_0_0_0.png"
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
            print(f"✅ {Colors.GREEN}Successfully mapped {len(self.services)} services.{Colors.ENDC}")
            
        except Exception as e:
            print(f"{Colors.FAIL}Error parsing lamedb: {e}{Colors.ENDC}")

    # ------------------------------------------
    # FEATURE: FTP DEPLOYMENT
    # ------------------------------------------
    def ftp_upload(self):
        """Connects to STB via FTP and deploys organized picons."""
        self.print_header("FTP UPLOAD TO STB")
        print(f"{Colors.CYAN}Deploy picons directly to your Enigma2 receiver.{Colors.ENDC}")
        print(f"{Colors.WARNING}Defaults shown in brackets. Press [ENTER] to skip.{Colors.ENDC}\n")

        ip = input(f"🌐 STB IP Address [{Colors.GREEN}192.168.1.14{Colors.ENDC}]: ").strip() or "192.168.1.14"
        usr = input(f"👤 Username [{Colors.GREEN}root{Colors.ENDC}]: ").strip() or "root"
        pwd = input(f"🔑 Password [{Colors.GREEN}root{Colors.ENDC}]: ").strip() or "root"
        remote_path = input(f"📁 STB Destination [{Colors.GREEN}/media/hdd/picon{Colors.ENDC}]: ").strip() or "/media/hdd/picon"
        
        mode = input(f"🎯 Format (SRP or SNP) [{Colors.GREEN}SRP{Colors.ENDC}]: ").strip().upper() or "SRP"
        if mode not in ['SRP', 'SNP']: 
            print(f"{Colors.WARNING}Invalid mode. Defaulting to SRP.{Colors.ENDC}")
            mode = 'SRP'

        print(f"\n{Colors.CYAN}Available Satellite Folders:{Colors.ENDC}")
        available_sats = [d for d in os.listdir(self.picon_dir) if os.path.isdir(os.path.join(self.picon_dir, d)) and d not in ['SRP', 'SNP']]
        print(", ".join(available_sats) if available_sats else "None found. Did you run Option 4 first?")
        
        sats_input = input(f"🌍 Satellites (comma-separated or 'all') [{Colors.GREEN}all{Colors.ENDC}]: ").strip().lower() or "all"
        target_sats = available_sats if sats_input == 'all' else [s.strip() for s in sats_input.split(',')]

        # Gather payload
        payload = []
        for sat in target_sats:
            folder_path = os.path.join(self.picon_dir, sat, mode)
            if os.path.exists(folder_path):
                for f in os.listdir(folder_path):
                    if f.endswith('.png'):
                        payload.append(os.path.join(folder_path, f))

        if not payload:
            print(f"\n{Colors.FAIL}⛔ No valid .png files found for the selected criteria.{Colors.ENDC}")
            return

        total = len(payload)
        print(f"\n🚀 {Colors.BOLD}Connecting to {ip}...{Colors.ENDC}")
        
        try:
            ftp = ftplib.FTP(ip)
            ftp.login(usr, pwd)
            print(f"✅ {Colors.GREEN}Authenticated.{Colors.ENDC} Navigating to {remote_path}...")
            
            try:
                ftp.cwd(remote_path)
            except ftplib.error_perm:
                print(f"{Colors.WARNING}Path does not exist. Attempting to create {remote_path}...{Colors.ENDC}")
                ftp.mkd(remote_path)
                ftp.cwd(remote_path)

            print(f"📤 {Colors.CYAN}Starting transfer of {total} picons...{Colors.ENDC}\n")
            
            for i, file_path in enumerate(payload):
                filename = os.path.basename(file_path)
                with open(file_path, 'rb') as f:
                    ftp.storbinary(f'STOR {filename}', f)
                
                # Dynamic progress bar
                percent = int(((i + 1) / total) * 100)
                sys.stdout.write(f"\r{Colors.GREEN}[{'#' * (percent // 2)}{'.' * (50 - (percent // 2))}] {percent}% ({i+1}/{total}){Colors.ENDC}")
                sys.stdout.flush()

            ftp.quit()
            print(f"\n\n🎉 {Colors.BOLD}{Colors.GREEN}Upload Completed Successfully!{Colors.ENDC}")

        except Exception as e:
            print(f"\n\n{Colors.FAIL}💥 FTP Communication Error: {e}{Colors.ENDC}")
            print(f"{Colors.WARNING}Hint: Check IP, credentials, and ensure STB FTP service is running.{Colors.ENDC}")

    # ------------------------------------------
    # EXPORT & FILE OPERATIONS
    # ------------------------------------------
    def export_csv(self, mode):
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
                    
        print(f"  📝 Generated {Colors.GREEN}{out_name}{Colors.ENDC} [{count} records]")

    def auto_refresh_csvs(self):
        print(f"\n🔄 {Colors.CYAN}Auto-refreshing database reports...{Colors.ENDC}")
        self.refresh_picon_index() 
        self.export_csv('all')
        self.export_csv('found')
        self.export_csv('missing')

    def organize_picons(self):
        self.print_header("ORGANIZE PICONS")
        print("Building SAT/SRP and SAT/SNP directory trees...")
        
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
                
        print(f"\n{Colors.GREEN}✔ Organized {organized_count} services across satellites.{Colors.ENDC}")
        self.auto_refresh_csvs()

    def import_alternate_picons(self):
        self.print_header("HEAL MISSING PICONS")
        raw_path = input(f"🔍 Alternate Path [Press Tab to Autocomplete]: ").strip()
        if not raw_path: return
        
        alt_path = os.path.expanduser(raw_path)
        if not os.path.exists(alt_path):
            print(f"{Colors.FAIL}Error: Path '{alt_path}' not found.{Colors.ENDC}")
            return
            
        print(f"⏳ Indexing {alt_path}...")
        alt_index = {f.lower(): f for f in os.listdir(alt_path) if f.lower().endswith('.png')}
                
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
                        
        print(f"\n{Colors.GREEN}✔ Import complete! Added {import_count} new picons.{Colors.ENDC}")
        self.auto_refresh_csvs()

    # ------------------------------------------
    # MAIN EXECUTION LOOP
    # ------------------------------------------
    def run(self):
        self.print_banner()
        self.setup_environment()
        
        self.parse_satellites()
        self.refresh_picon_index()
        self.parse_lamedb()
        self.auto_refresh_csvs()

        while True:
            self.print_menu()
            choice = input(f"👉 Select an option: {Colors.CYAN}").strip().upper()
            print(f"{Colors.ENDC}", end="")
            
            if choice == '1': self.export_csv('all')
            elif choice == '2': self.export_csv('found')
            elif choice == '3': self.export_csv('missing')
            elif choice == '4': self.organize_picons()
            elif choice == '5': self.import_alternate_picons()
            elif choice == '6': self.ftp_upload()
            elif choice == 'Q':
                print(f"\n👋 {Colors.CYAN}Exiting PiconWeaver. May your signals be strong!{Colors.ENDC}")
                break
            else:
                print(f"{Colors.FAIL}Invalid selection. Try again.{Colors.ENDC}")

# ==========================================
# BOOTSTRAP
# ==========================================
if __name__ == "__main__":
    try:
        app = PiconWeaver()
        app.run()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.WARNING}⚠️ Process interrupted by user. Exiting gracefully...{Colors.ENDC}")
        sys.exit(0)
