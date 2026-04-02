import os
import re
import glob
import csv
import time
import sys
import difflib
import unicodedata  # FIX: Added for accurate UI emoji width calculation
from datetime import datetime

# ==========================================================================================
# 🛠️ TUNING & CALIBRATION (ADJUST THESE TO FIX YOUR UI BOXES)
# ==========================================================================================
class TUNE:
    UI_WIDTH    = 82    # Total box width
    ADJUST_TOP  = 0     # Fine-tune the top border (▜) alignment
    ADJUST_LINE = -1    # Fine-tune the side border (▐) alignment
    ADJUST_BTM  = 0     # Fine-tune the bottom border (▟) alignment

# ==========================================================================================
# 🛠️ CLASS: PATH COMMANDER (READLINE ENGINE)
# ==========================================================================================
try:
    import readline

    class PathCommander:
        """Handles deep-path autocompletion with support for ~ and relative paths."""
        def __init__(self):
            self.matches = []

        def complete(self, text, state):
            if state == 0:
                expanded_text = os.path.expanduser(text)
                if os.path.isdir(expanded_text) and text.endswith(os.sep):
                    search_dir = expanded_text
                    prefix = ""
                else:
                    search_dir = os.path.dirname(expanded_text) or "."
                    prefix = os.path.basename(expanded_text)

                try:
                    items = os.listdir(search_dir)
                    self.matches = []
                    for item in items:
                        if item.startswith(prefix):
                            dir_part = os.path.dirname(text)
                            display_path = os.path.join(dir_part, item)
                            full_path = os.path.join(search_dir, item)
                            if os.path.isdir(full_path):
                                self.matches.append(display_path + os.sep)
                            else:
                                self.matches.append(display_path)
                except:
                    self.matches = []
            try:
                return self.matches[state]
            except IndexError:
                return None

        @classmethod
        def initialize(cls):
            commander = cls()
            readline.set_completer(commander.complete)
            readline.set_completer_delims(' \t\n`@=#%^&()[]{}\\|;\'",<>?')
            if 'libedit' in readline.__doc__:
                readline.parse_and_bind("bind ^I rl_complete")
            else:
                readline.parse_and_bind("tab: complete")
            readline.parse_and_bind("set editing-mode emacs")

except ImportError:
    readline = None

# ==========================================================================================
# 🎨 CLASS: COLOR & UI ENGINE
# ==========================================================================================
class COLOR:
    G = '\033[38;5;82m'   # Neon Green
    Y = '\033[38;5;226m'  # Bright Yellow
    R = '\033[38;5;196m'  # Red
    B = '\033[38;5;27m'    # Deep Blue
    C = '\033[38;5;51m'   # Cyan
    M = '\033[38;5;201m'  # Hot Magenta
    W = '\033[0m'          # Reset
    GRAY = '\033[38;5;244m'
    D_GRAY = '\033[38;5;236m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class Logger:
    def __init__(self, filename="titan_session.log"):
        self.terminal = sys.stdout
        self.log_file = open(filename, "w", encoding="utf-8")
        self.ansi_cleaner = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_file.write(f"{'='*80}\n")
        self.log_file.write(f"TITAN ELITE SESSION START: {timestamp}\n")
        self.log_file.write(f"VERSION: 9.4 | ENGINE: STRICT TIER 1 SYNC\n")
        self.log_file.write(f"{'='*80}\n\n")

    def write(self, message):
        self.terminal.write(message)
        clean_msg = self.ansi_cleaner.sub('', message)
        self.log_file.write(clean_msg)
        self.log_file.flush()

    def flush(self):
        self.terminal.flush()

class UI:
    ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

    @classmethod
    def clean_len(cls, text):
        """Calculates visible terminal length of string excluding ANSI codes and accounting for Emojis."""
        clean = cls.ANSI_ESCAPE.sub('', text)
        width = 0
        for char in clean:
            if unicodedata.east_asian_width(char) in ('W', 'F'):
                width += 2  # Emojis take 2 columns
            else:
                width += 1
        return width

    @staticmethod
    def header():
        c, m = COLOR.C, COLOR.M
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"{m}█████████████████████████████████████████████████████████████████████████████████████")
        print(f"█{c}                                                                                 {m}  █")
        print(f"█{c}   ████████╗██╗████████╗ █████╗ ███╗   ██╗     ███████╗██╗     ██╗████████╗███████╗ {m}█")
        print(f"█{c}   ╚══██╔══╝██║╚══██╔══╝██╔══██╗████╗  ██║     ██╔════╝██║     ██║╚══██╔══╝██╔════╝ {m}█")
        print(f"█{c}      ██║   ██║   ██║   ███████║██╔██╗ ██║     █████╗  ██║     ██║   ██║   █████╗   {m}█")
        print(f"█{c}      ██║   ██║   ██║   ██╔══██║██║╚██╗██║     ██╔══╝  ██║     ██║   ██║   ██╔══╝   {m}█")
        print(f"█{c}      ██║   ██║   ██║   ██║  ██║██║ ╚████║     ███████╗███████╗██║   ██║   ███████╗ {m}█")
        print(f"█{c}      ╚═╝   ╚═╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═══╝     ╚══════╝╚══════╝╚═╝   ╚═╝   ╚══════╝ {m}█")
        print(f"█{m}" + f"--- {COLOR.W}{COLOR.BOLD}TITAN ELITE V9.4{COLOR.W} | {COLOR.GRAY}STRICT TIER 1 SYNC {m}---".center(TUNE.UI_WIDTH +34) + f"{m} █")
        print(f"█{c}                                                                                 {m}  █")
        print(f"█████████████████████████████████████████████████████████████████████████████████████{COLOR.W}\n")

    @staticmethod
    def box_top(title="", color=COLOR.C):
        title_text = f"┨ {title} ┠"
        # FIX: Correct math -> ▛▀▀ (3) + space (1) + title + space (1) + ▀*n + ▜ (1) = 6 overhead
        visible_len = UI.clean_len(title_text)
        padding_len = TUNE.UI_WIDTH - visible_len - 6 + TUNE.ADJUST_TOP
        print(f"{color}▛▀▀ {COLOR.W}{COLOR.BOLD}{title_text}{COLOR.W}{color} {'▀' * max(0, padding_len)}▜")

    @staticmethod
    def box_line(text, icon=" ", color=COLOR.C):
        # FIX: Correct math -> ▌ (1) + space (1) + icon + space (1) + text + space (1) + ▐ (1) = 6 overhead
        visible_text_len = UI.clean_len(text)
        visible_icon_len = UI.clean_len(icon)
        overhead = 6 + visible_icon_len
        padding_len = TUNE.UI_WIDTH - overhead - visible_text_len + TUNE.ADJUST_LINE
        padding = " " * max(0, padding_len)
        print(f"{color}▌ {COLOR.W}{icon} {text}{padding} {color}▐")

    @staticmethod
    def box_bottom(color=COLOR.C):
        # FIX: Correct math -> ▙ (1) + ▄*n + ▟ (1) = 2 overhead
        width = TUNE.UI_WIDTH - 2 + TUNE.ADJUST_BTM
        print(f"{color}▙{'▄' * max(0, width)}▟{COLOR.W}")

    @staticmethod
    def progress_bar(current, total, length=35):
        percent = (current / total) if total > 0 else 0
        filled = int(length * percent)
        bar = f"{COLOR.G}█" * filled + f"{COLOR.D_GRAY}█" * (length - filled)
        return f"{bar} {COLOR.W}{int(percent*100)}%"

# ==========================================================================================
# 🛰️ CLASS: ENIGMA DATABASE (PARSER & DATA)
# ==========================================================================================
class EnigmaDB:
    def __init__(self, file_path):
        self.file_path = os.path.abspath(os.path.expanduser(file_path))
        self.raw_lines = []
        self.data = {'tp': {}, 'srv': []}
        self.error = None

    def load(self):
        try:
            with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                self.raw_lines = f.readlines()
        except Exception as e:
            self.error = str(e)
            return False

        if not self.raw_lines or 'eDVB services /4/' not in self.raw_lines[0]:
            self.error = "Invalid lamedb format"
            return False

        try:
            t_start = self.raw_lines.index('transponders\n') + 1
            t_end = self.raw_lines.index('end\n', t_start)
            s_start = self.raw_lines.index('services\n', t_end) + 1
            s_end = self.raw_lines.index('end\n', s_start)
            self._parse_transponders(t_start, t_end)
            self._parse_services(s_start, s_end)
            return True
        except ValueError:
            self.error = "Structure markers not found"
            return False

    def _parse_transponders(self, start, end):
        i = start
        while i < end:
            line = self.raw_lines[i].strip()
            if not line or line == '/': i += 1; continue
            header = line.split(':')
            if len(header) >= 3:
                tp_key = (header[0].lower(), header[1].lower(), header[2].lower())
                if i + 1 < end:
                    data = self.raw_lines[i+1].strip().replace(':', ' ').split()
                    if data and data[0] == 's' and len(data) > 6:
                        try:
                            self.data['tp'][tp_key] = {
                                'freq': int(data[1]) // 1000,
                                'sr': int(data[2]) // 1000,
                                'pol': data[3],
                                'pos': int(data[5]),
                                'sys': 'DVB-S2' if len(data) > 7 and data[7] == '1' else 'DVB-S'
                            }
                        except: pass
                    i += 2
                else:
                    i += 1  # FIX: Prevent infinite loop if malformed transponder at end of block
            else: i += 1

    def _parse_services(self, start, end):
        i = start
        while i < end:
            line = self.raw_lines[i].strip()
            if not line or line == '/': i += 1; continue
            h = line.split(':')
            if len(h) >= 5:
                self.data['srv'].append({
                    'sid': h[0].lower().lstrip('0') or '0',
                    'tp_ref': (h[1].lower(), h[2].lower(), h[3].lower()),
                    'type': h[4],
                    'name_idx': i + 1,
                    'initial_name': self.raw_lines[i+1].strip()
                })
                i += 3
            else: i += 1

    def save(self):
        with open(self.file_path, 'w', encoding='utf-8', newline='\n') as f:
            f.writelines(self.raw_lines)

# ==========================================================================================
# 🌌 CLASS: TITAN CORE (PROCESSING ENGINE)
# ==========================================================================================
class TitanCore:
    def __init__(self, db):
        self.db = db
        self.pol_map = {'H': '0', 'V': '1', 'L': '2', 'R': '3'}
        self.stats = {
            'upd': 0, 'ver': 0, 'chk': 0, 't1': 0, 'dup': 0,
            'unm': [], 'audits': [], 'unmatched_reports': [], 'processed_csvs': 0, 'total_time': 0,
            'sat_data': {}
        }

    @staticmethod
    def get_orbital_position(filename):
        match = re.search(r'@(\d+\.?\d*)([WE])', filename)
        if not match: return 9999
        pos = float(match.group(1))
        direction = match.group(2)
        return int(pos * 10) * (1 if direction == 'E' else -1)

    def process_csv(self, csv_path):
        start_t = time.time()
        csv_pos = self.get_orbital_position(csv_path)
        sat_name = os.path.basename(csv_path)
        file_stats = {'upd': 0, 'ver': 0, 'chk': 0, 't1': 0, 'dup': 0, 'unm': [], 'audit': []}
        
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            rows = list(csv.DictReader(f))
            total_rows = len(rows)

        for idx, row in enumerate(rows):
            file_stats['chk'] += 1
            c_freq = int(row['Frequency'])
            c_pol = self.pol_map.get(row['Polarization'].upper(), '0')
            c_sid = hex(int(row['SID']))[2:].lower().lstrip('0') or '0'
            c_name = row['ServiceName'].strip()
            
            if hasattr(sys.stdout, 'terminal'):
                status = f"  {COLOR.Y}⟳{COLOR.W} Strict Sync: {idx+1}/{total_rows} | {c_name[:20]}..."
                sys.stdout.terminal.write(f"\r{status}\033[K")
                sys.stdout.terminal.flush()

            match = self._find_match(c_sid, c_freq, c_pol, csv_pos)

            if match:
                old_n = self.db.raw_lines[match['name_idx']].strip()
                
                # Preserve HD/SD if DB has it but CSV doesn't (Original Logic Kept)
                final_name = c_name
                quality_match = re.search(r'\(?(HD|SD|4K)\)?', old_n, re.IGNORECASE)
                if quality_match and not re.search(r'\(?(HD|SD|4K)\)?', c_name, re.IGNORECASE):
                    final_name = f"{c_name} ({quality_match.group(1).upper()})"

                if old_n != final_name and final_name:
                    self.db.raw_lines[match['name_idx']] = final_name + "\n"
                    file_stats['upd'] += 1
                    file_stats['t1'] += 1
                    print(f"\r  {COLOR.G}[UPDATE]{COLOR.W} T1 │ {COLOR.GRAY}{old_n[:22].ljust(22)} {COLOR.C}➔  {COLOR.G}{final_name.ljust(25)}")
                else:
                    file_stats['ver'] += 1
                
                file_stats['audit'].append({
                    'status': 'VERIFIED' if old_n == final_name else 'UPDATED',
                    'freq': c_freq, 'pol': row['Polarization'], 'sid': row['SID'],
                    'old_name': old_n, 'new_name': final_name
                })
            else:
                is_dup = any(s['sid'] == c_sid and self.db.data['tp'].get(s['tp_ref'], {}).get('pos') == csv_pos for s in self.db.data['srv'])
                
                if is_dup:
                    file_stats['dup'] += 1
                else:
                    file_stats['unm'].append(row)
                    print(f"\r  {COLOR.R}[MISSED]{COLOR.W}      │ {COLOR.R}{c_name[:22].ljust(22)} {COLOR.W}✖ {COLOR.GRAY}(SID:{c_sid.upper()} F:{c_freq} P:{c_pol})")
                    
                    file_stats['audit'].append({
                        'status': 'MISSED',
                        'freq': c_freq, 'pol': row['Polarization'], 'sid': row['SID'],
                        'old_name': 'N/A', 'new_name': c_name
                    })

        sys.stdout.write("\r" + " " * 85 + "\r")
        self._generate_audit(csv_path, file_stats)
        self._generate_unmatched_report(csv_path, file_stats)
        
        file_stats['elapsed'] = time.time() - start_t
        self.stats['sat_data'][sat_name] = {
            'upd': file_stats['upd'], 'ver': file_stats['ver'], 'chk': file_stats['chk'],
            'unm': len(file_stats['unm']), 'dup': file_stats['dup']
        }
        self._merge_stats(file_stats)
        return file_stats

    def _find_match(self, c_sid, c_freq, c_pol, csv_pos):
        """FIX: Strict 2-Step Tier 1 Match. Finds exact transponder first, then SID within it."""
        matched_tp_key = None
        
        # STEP 1: Find the precise transponder key by Position, Frequency, and Polarity
        for tp_key, tp in self.db.data['tp'].items():
            if tp['pos'] == csv_pos:
                dfreq = abs(tp['freq'] - c_freq)
                # FIX: Increased tolerance to 5MHz to catch common DB drifts (e.g. 11881 vs 11885)
                if dfreq <= 5 and tp['pol'] == c_pol:
                    matched_tp_key = tp_key
                    break  # Locked onto the correct transponder
                
        if not matched_tp_key:
            return None
            
        # STEP 2: Search for the SID strictly within that specific transponder
        for srv in self.db.data['srv']:
            if srv['sid'] == c_sid and srv['tp_ref'] == matched_tp_key:
                return srv
                
        return None

    def _generate_audit(self, csv_path, file_stats):
        pos_label = os.path.basename(csv_path).replace('.csv', '')
        audit_file = f"audit_{pos_label}.csv"
        
        if file_stats['audit']:
            with open(audit_file, 'w', encoding='utf-8', newline='') as f:
                dw = csv.DictWriter(f, fieldnames=['status', 'freq', 'pol', 'sid', 'old_name', 'new_name'])
                dw.writeheader()
                dw.writerows(file_stats['audit'])
            file_stats['audit_fn'] = audit_file

    def _generate_unmatched_report(self, csv_path, file_stats):
        if not file_stats['unm']: return
        
        pos_label = os.path.basename(csv_path).replace('.csv', '')
        report_fn = f"missed_services_{pos_label}.txt"
        
        with open(report_fn, "w", encoding="utf-8") as f:
            f.write(f"╔{'═'*78}╗\n")
            f.write(f"║ TITAN UNMATCHED SERVICE REPORT {' '.center(46)} ║\n")
            f.write(f"╠{'═'*78}╣\n")
            f.write(f"║ SOURCE FILE : {os.path.basename(csv_path).ljust(61)} ║\n")
            f.write(f"║ TIMESTAMP   : {datetime.now().strftime('%Y-%m-%d %H:%M:%S').ljust(61)} ║\n")
            f.write(f"╠{'═'*12}╦{'═'*10}╦{'═'*8}╦{'═'*10}╦{'═'*34}╣\n")
            f.write(f"║ FREQUENCY  ║ POL      ║ SID    ║ TYPE     ║ SERVICE NAME                   ║\n")
            f.write(f"╠{'═'*12}╬{'═'*10}╬{'═'*8}╬{'═'*10}╬{'═'*34}╣\n")
            
            for row in file_stats['unm']:
                freq = row.get('Frequency', '0').ljust(10)
                pol = row.get('Polarization', 'N/A').ljust(8)
                sid = row.get('SID', '0').ljust(6)
                stype = row.get('ServiceType', 'N/A').ljust(8)
                name = row.get('ServiceName', 'Unknown')[:32].ljust(32)
                f.write(f"║ {freq} ║ {pol} ║ {sid} ║ {stype} ║ {name} ║\n")
                
            f.write(f"╚{'═'*12}╩{'═'*10}╩{'═'*8}╩{'═'*10}╩{'═'*34}╝\n")
        file_stats['unm_report_fn'] = report_fn

    def _merge_stats(self, fs):
        for key in ['upd', 'ver', 'chk', 't1', 'dup']: self.stats[key] += fs[key]
        self.stats['unm'].extend(fs['unm'])
        self.stats['processed_csvs'] += 1
        self.stats['total_time'] += fs['elapsed']
        if 'audit_fn' in fs: self.stats['audits'].append(fs['audit_fn'])
        if 'unm_report_fn' in fs: self.stats['unmatched_reports'].append(fs['unm_report_fn'])

# ==========================================================================================
# 🚀 MAIN APPLICATION CONTROLLER
# ==========================================================================================
def main():
    if readline:
        PathCommander.initialize()

    UI.header()
    
    UI.box_top("ENVIRONMENT & INPUT CONFIGURATION", COLOR.M)
    UI.box_line(f"AUTO-COMPLETE: Press {COLOR.C}TAB{COLOR.W} to suggest file/folder paths.", "⌨", COLOR.M)
    UI.box_line(f"LOGGING      : Live session is recorded to {COLOR.C}titan_session.log{COLOR.W}", "📝", COLOR.M)
    UI.box_line(f"V9.4 ENGINE  : Strict Tier 1 Logic (Technical Matches Only).", "🛡", COLOR.M)
    UI.box_bottom(COLOR.M)

    while True:
        try:
            db_path = input(f"\n {COLOR.M}🛰  LAMEDB PATH{COLOR.W}: ").strip() or "./lamedb"
            db = EnigmaDB(db_path)
            if os.path.isdir(db.file_path):
                print(f" {COLOR.Y}⚠ DIRECTORY DETECTED!{COLOR.W} Please target the specific 'lamedb' file.")
                continue
            if not os.path.exists(db.file_path):
                print(f" {COLOR.R}✖ FILE NOT FOUND:{COLOR.W} {db.file_path}")
                continue
            if db.load(): break
            else: print(f" {COLOR.R}✖ LOAD ERROR:{COLOR.W} {db.error}")
        except (EOFError, KeyboardInterrupt): return

    sys.stdout = Logger()
    
    csv_files = sorted(glob.glob("channels/*.csv"), key=TitanCore.get_orbital_position)
    if not csv_files:
        UI.box_top("IO ERROR", COLOR.R)
        UI.box_line("No .csv maps found in the /channels directory.", "✖", COLOR.R)
        UI.box_bottom(COLOR.R)
        return

    UI.box_top("SATELLITE ORBITAL MAPS DISCOVERED", COLOR.B)
    for idx, f in enumerate(csv_files):
        p = TitanCore.get_orbital_position(f)
        p_str = f"{abs(p/10)}°W" if p < 0 else f"{p/10}°E"
        UI.box_line(f"[{COLOR.C}{str(idx).center(3)}{COLOR.W}] {COLOR.BOLD}{p_str.rjust(6)}{COLOR.W} │ {os.path.basename(f)[:52]}", "🛰", COLOR.B)
    UI.box_bottom(COLOR.B)
    
    print(f"\n  {COLOR.BOLD}[COMMANDS]{COLOR.W}  {COLOR.G}(B) Batch Sync All{COLOR.W}  │  {COLOR.G}(#) Single Satellite{COLOR.W}  │  {COLOR.R}(Q) Quit{COLOR.W}")
    
    try:
        choice = input(f"\n {COLOR.M} weaver@titan{COLOR.W}:~$ ").strip().upper()
    except (EOFError, KeyboardInterrupt): return
    
    if choice == 'Q': return
    to_proc = csv_files if choice == 'B' else [csv_files[int(choice)]] if choice.isdigit() and int(choice) < len(csv_files) else []
    if not to_proc: return

    titan = TitanCore(db)
    for f_path in to_proc:
        print(f"\n {COLOR.C}◈ {COLOR.BOLD}SYNCHRONIZING:{COLOR.W} {COLOR.UNDERLINE}{os.path.basename(f_path)}{COLOR.W}")
        titan.process_csv(f_path)

    # FINAL DEEP ANALYTICS REPORT
    UI.box_top("TITAN ELITE V9.4 - SESSION ANALYTICS", COLOR.G)
    UI.box_line(f"PROCESSING PERFORMANCE", "⚡", COLOR.G)
    UI.box_line(f"  ├─ Files Processed   : {titan.stats['processed_csvs']}", " ", COLOR.G)
    UI.box_line(f"  ├─ Total Runtime     : {titan.stats['total_time']:.4f} seconds", " ", COLOR.G)
    UI.box_line(f"  └─ Avg Speed         : {titan.stats['chk'] / max(1, titan.stats['total_time']):.1f} rows/sec", " ", COLOR.G)
    
    UI.box_line(f"DATABASE UPDATE METRICS (STRICT MODE)", "📊", COLOR.G)
    UI.box_line(f"  ├─ Total Scanned     : {titan.stats['chk']}", " ", COLOR.G)
    UI.box_line(f"  ├─ Verified Clean    : {COLOR.C}{titan.stats['ver']}{COLOR.W}", " ", COLOR.G)
    UI.box_line(f"  ├─ Successful Updates: {COLOR.G}{titan.stats['upd']}{COLOR.W}", " ", COLOR.G)
    UI.box_line(f"  │  └─ Tier 1 Strict  : {titan.stats['t1']}", " ", COLOR.G)
    UI.box_line(f"  ├─ Scanner Dups      : {COLOR.Y}{titan.stats['dup']}{COLOR.W} (Ignored)", " ", COLOR.G)
    UI.box_line(f"  └─ Hard Misses       : {COLOR.R}{len(titan.stats['unm'])}{COLOR.W}", " ", COLOR.G)

    UI.box_line(f"SATELLITE HEAT MAP", "🗺", COLOR.G)
    for sat, s_data in titan.stats['sat_data'].items():
        m_tag = f"{COLOR.G}U:{s_data['upd']}{COLOR.W} {COLOR.R}M:{s_data['unm']}{COLOR.W}"
        UI.box_line(f"  ├─ {sat[:30].ljust(30)} : [{m_tag}]", " ", COLOR.G)
    UI.box_line("  └─ Sync Confidence  : " + UI.progress_bar(titan.stats['upd'] + titan.stats['ver'], titan.stats['chk']), " ", COLOR.G)

    UI.box_line(f"DATA INTEGRITY & IO", "🛡", COLOR.G)
    if titan.stats['upd'] > 0:
        db.save()
        UI.box_line(f"  ├─ Database Status  : {COLOR.G}SAVED & COMMITTED{COLOR.W}", " ", COLOR.G)
        UI.box_line(f"  ├─ Full Audit CSVs  : {len(titan.stats['audits'])} generated", " ", COLOR.G)
        UI.box_line(f"  └─ Unmatched Reports: {len(titan.stats['unmatched_reports'])} generated", " ", COLOR.G)
    else:
        UI.box_line(f"  └─ Database Status  : NO CHANGES REQUIRED", " ", COLOR.G)
    
    UI.box_bottom(COLOR.G)
    print(f"\n {COLOR.G}🏆 TITAN SESSION CONCLUDED. LOGGED TO titan_session.log{COLOR.W}\n")

if __name__ == "__main__":
    main()
