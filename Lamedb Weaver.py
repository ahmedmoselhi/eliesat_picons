#!/usr/bin/env python3
import os
import re
import glob
import csv
import time
import sys
import difflib
import unicodedata
import json
from datetime import datetime

# ==========================================================================================
# 🛠️ TUNING & CALIBRATION
# ==========================================================================================
class TUNE:
    """Global UI and alignment parameters for the Titan terminal interface."""
    UI_WIDTH    = 82
    ADJUST_TOP  = -2
    ADJUST_LINE = -1
    ADJUST_BTM  = -2

# ==========================================================================================
# 🛠️ CLASS: PATH COMMANDER
# ==========================================================================================
try:
    import readline

    class PathCommander:
        """
        Handles deep-path autocompletion with support for ~ and relative paths.
        This provides a professional shell-like experience for selecting the lamedb file.
        """
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
    G = '\033[38;5;82m'
    Y = '\033[38;5;226m'
    R = '\033[38;5;196m'
    B = '\033[38;5;27m'
    C = '\033[38;5;51m'
    M = '\033[38;5;201m'
    W = '\033[0m'
    GRAY = '\033[38;5;244m'
    D_GRAY = '\033[38;5;236m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class Logger:
    """
    Custom logger that redirects stdout to both the terminal and a physical file.
    Includes the 'Logger Tab Fix' to ensure table alignment remains consistent in text logs.
    """
    def __init__(self, filename="titan_session.log"):
        self.terminal = sys.stdout
        self.log_file = open(filename, "w", encoding="utf-8")
        self.ansi_cleaner = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_file.write(f"{'='*80}\n")
        self.log_file.write(f"TITAN ELITE SESSION START: {timestamp}\n")
        self.log_file.write(f"VERSION: 10.3 | ENGINE: OPTIMIZED NAMESPACE PARSER\n")
        self.log_file.write(f"{'='*80}\n\n")

    def write(self, message):
        # Logger Tab Fix: Replace tabs with 4 spaces to maintain column alignment in .log files
        fixed_message = message.replace('\t', '    ')
        self.terminal.write(fixed_message)
        
        # Strip ANSI colors before writing to the physical log file
        clean_msg = self.ansi_cleaner.sub('', fixed_message)
        self.log_file.write(clean_msg)
        self.log_file.flush()

    def flush(self):
        self.terminal.flush()

class UI:
    ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

    @classmethod
    def clean_len(cls, text):
        clean = cls.ANSI_ESCAPE.sub('', text)
        width = 0
        for char in clean:
            if unicodedata.east_asian_width(char) in ('W', 'F'):
                width += 2
            else:
                width += 1
        return width

    @staticmethod
    def header():
        c, m = COLOR.C, COLOR.M
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"{m}███████████████████████████████████████████████████████████████████████████████████████")
        print(f"█{c}                                                                                     {m}   █")
        print(f"█{c}   ████████╗██╗████████╗ █████╗ ███╗   ██╗     ███████╗██╗     ██║████████╗███████╗ {m} █")
        print(f"█{c}   ╚══██╔══╝██║╚══██╔══╝██╔══██╗████╗  ██║     ██╔════╝██║     ██║╚══██╔══╝██╔════╝ {m} █")
        print(f"█{c}      ██║   ██║   ██║   ███████║██╔██╗ ██║     █████╗  ██║     ██║   ██║   █████╗   {m} █")
        print(f"█{c}      ██║   ██║   ██║   ██╔══██║██║╚██╗██║     ██╔══╝  ██║     ██║   ██║   ██╔══╝   {m} █")
        print(f"█{c}      ██║   ██║   ██║   ██║  ██║██║ ╚████║     ███████╗███████╗██║   ██║   ███████╗ {m} █")
        print(f"█{c}      ╚═╝   ╚═╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═══╝     ╚══════╝╚══════╝╚═╝   ╚═╝   ╚══════╝ {m} █")
        print(f"█{m}" + f"--- {COLOR.W}{COLOR.BOLD}TITAN ELITE V10.3{COLOR.W} | {COLOR.GRAY}OPTIMIZED NAMESPACE LOGIC {m}---".center(TUNE.UI_WIDTH +36) + f"{m} █")
        print(f"█{c}                                                                                     {m}   █")
        print(f"███████████████████████████████████████████████████████████████████████████████████████{COLOR.W}\n")

    @staticmethod
    def box_top(title="", color=COLOR.C):
        title_text = f"┨ {title} ┠"
        visible_len = UI.clean_len(title_text)
        padding_len = TUNE.UI_WIDTH - visible_len - 6 + TUNE.ADJUST_TOP
        print(f"{color}▛▀▀ {COLOR.W}{COLOR.BOLD}{title_text}{COLOR.W}{color} {'▀' * max(0, padding_len)}▜")

    @staticmethod
    def box_line(text, icon=" ", color=COLOR.C):
        visible_text_len = UI.clean_len(text)
        visible_icon_len = UI.clean_len(icon)
        overhead = 6 + visible_icon_len
        padding_len = TUNE.UI_WIDTH - overhead - visible_text_len + TUNE.ADJUST_LINE
        padding = " " * max(0, padding_len)
        print(f"{color}▌ {COLOR.W}{icon} {text}{padding} {color}▐")

    @staticmethod
    def box_bottom(color=COLOR.C):
        width = TUNE.UI_WIDTH - 2 + TUNE.ADJUST_BTM
        print(f"{color}▙{'▄' * max(0, width)}▟{COLOR.W}")

    @staticmethod
    def progress_bar(current, total, length=35):
        percent = (current / total) if total > 0 else 0
        filled = int(length * percent)
        bar = f"{COLOR.G}█" * filled + f"{COLOR.D_GRAY}█" * (length - filled)
        return f"{bar} {COLOR.W}{int(percent*100)}%"

# ==========================================================================================
# 🛰️ CLASS: ENIGMA DATABASE (PARSER)
# ==========================================================================================
class EnigmaDB:
    """
    Parser for Enigma2 lamedb format (Version 4).
    Separates Transponders and Services for relational matching.
    """
    def __init__(self, file_path):
        self.file_path = os.path.abspath(os.path.expanduser(file_path))
        self.raw_lines = []
        self.data = {'tp': {}, 'srv': []}
        self.error = None

    def load(self):
        try:
            if not os.path.exists(self.file_path):
                self.error = "File does not exist"
                return False
            with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                self.raw_lines = f.readlines()
        except Exception as e:
            self.error = str(e)
            return False

        if not self.raw_lines or 'eDVB services /4/' not in self.raw_lines[0]:
            self.error = "Invalid lamedb format (Expected Version 4)"
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
            self.error = "Structure markers (transponders/services/end) not found"
            return False

    def _parse_transponders(self, start, end):
        i = start
        while i < end:
            line = self.raw_lines[i].strip()
            if not line or line == '/': 
                i += 1
                continue
            header = line.split(':')
            if len(header) >= 3:
                tp_key = (header[0].lower(), header[1].lower(), header[2].lower())
                if i + 1 < end:
                    data = self.raw_lines[i+1].strip().replace(':', ' ').split()
                    if data and data[0] == 's' and len(data) > 5:
                        try:
                            freq = int(data[1])
                            sr = int(data[sr_idx := 2])
                            
                            raw_pol = data[3]
                            if raw_pol == '0': pol = 'H'
                            elif raw_pol == '1': pol = 'V'
                            else: pol = str(raw_pol).upper()
                            
                            pos = 0
                            if len(data) > 5:
                                try: pos = int(data[5])
                                except: pass
                            
                            sys_type = 'DVB-S'
                            if len(data) > 6:
                                if data[6] in ('1', '2'): sys_type = 'DVB-S2'
                            
                            self.data['tp'][tp_key] = {
                                'freq': freq, 'sr': sr, 'pol': pol,
                                'pos': pos, 'sys': sys_type
                            }
                        except: pass
                        i += 2
                    else: i += 1
                else: i += 1
            else: i += 1

    def _parse_services(self, start, end):
        i = start
        while i < end:
            line = self.raw_lines[i].strip()
            if not line or line == '/': 
                i += 1
                continue
            h = line.split(':')
            if len(h) >= 5:
                self.data['srv'].append({
                    'sid': h[0].lower().lstrip('0') or '0',
                    'tp_ref': (h[1].lower(), h[2].lower(), h[3].lower()),
                    'type': h[4],
                    'name_idx': i + 1,
                    'name': self.raw_lines[i+1].strip()
                })
                i += 3
            else: i += 1

    def save(self):
        with open(self.file_path, 'w', encoding='utf-8', newline='\n') as f:
            f.writelines(self.raw_lines)

# ==========================================================================================
# 🌌 CLASS: TITAN CORE (LOGIC)
# ==========================================================================================
class TitanCore:
    """
    Main processing engine for synchronizing service names.
    Uses 'Strict Namespace' matching to prevent cross-satellite SID collisions.
    """
    def __init__(self, target_db):
        self.target_db = target_db
        self.pol_map = {'H': '0', 'V': '1', 'L': '2', 'R': '3'}
        self.pol_reverse_map = {'0': 'H', '1': 'V', '2': 'L', '3': 'R'}
        self.stats = {
            'upd': 0, 'ver': 0, 'chk': 0, 't1': 0, 'dup': 0, 'skip': 0,
            'unm': [], 'audits': [], 'unmatched_reports': [], 'processed_csvs': 0, 'total_time': 0,
            'sat_data': {}
        }
        
        # Build Optimized Maps for O(1) matching
        self.target_sid_map = {}
        for srv in self.target_db.data['srv']:
            sid = srv['sid']
            if sid not in self.target_sid_map: self.target_sid_map[sid] = []
            self.target_sid_map[sid].append(srv)
            
        self.target_tp_by_pos = {}
        for tp_key, tp_data in self.target_db.data['tp'].items():
            e2_pos = self._get_e2_pos_from_namespace(tp_key[0])
            if e2_pos not in self.target_tp_by_pos: self.target_tp_by_pos[e2_pos] = []
            self.target_tp_by_pos[e2_pos].append((tp_key, tp_data))

    @staticmethod
    def get_orbital_position(filename):
        match = re.search(r'@(\d+\.?\d*)([WE])', filename)
        if not match: return 9999
        pos = float(match.group(1))
        direction = match.group(2)
        return int(pos * 10) * (1 if direction == 'E' else -1)

    def _get_e2_pos_from_namespace(self, namespace_hex):
        try: return int(namespace_hex, 16) >> 16
        except: return -1

    def process_source_lamedb(self, source_db, sat_name):
        start_t = time.time()
        csv_pos = self.get_orbital_position(sat_name)
        expected_e2_pos = (3600 + csv_pos) if csv_pos < 0 else csv_pos
        sat_name_clean = sat_name.replace('_lamedb', '')
        file_stats = {'upd': 0, 'ver': 0, 'chk': 0, 't1': 0, 'dup': 0, 'skip': 0, 'unm': [], 'audits': []}
        
        for source_srv in source_db.data['srv']:
            if source_srv['sid'] == '0': continue
            file_stats['chk'] += 1
            
            if hasattr(sys.stdout, 'terminal'):
                status = f"  {COLOR.Y}⟳{COLOR.W} Strict Sync: {file_stats['chk']:>4} │ {source_srv['name'][:20]}..."
                sys.stdout.terminal.write(f"\r{status}\033[K")
                sys.stdout.terminal.flush()

            match, match_type = self._find_match(source_srv, expected_e2_pos, source_db)

            if match:
                old_n = self.target_db.raw_lines[match['name_idx']].strip()
                new_name = source_srv['name']
                
                # Preserve quality tags (HD/SD/4K)
                quality_match = re.search(r'\(?(HD|SD|4K|UHD)\)?', old_n, re.IGNORECASE)
                if quality_match and not re.search(r'\(?(HD|SD|4K|UHD)\)?', new_name, re.IGNORECASE):
                    new_name = f"{new_name} ({quality_match.group(1).upper()})"

                if old_n != new_name:
                    self.target_db.raw_lines[match['name_idx']] = new_name + "\n"
                    file_stats['upd'] += 1
                    file_stats['t1'] += 1
                    print(f"\r  {COLOR.G}[UPDATE]{COLOR.W} {match_type} │ {COLOR.GRAY}{old_n[:22].ljust(22)} {COLOR.C}➔  {COLOR.G}{new_name[:25].ljust(25)}")
                else:
                    file_stats['ver'] += 1
                    print(f"\r  {COLOR.B}[VERIFIED]{COLOR.W} {match_type} │ {COLOR.GRAY}{old_n[:22].ljust(22)} {COLOR.C}== {COLOR.GRAY}{new_name[:25].ljust(25)}")
                    
                file_stats['audits'].append({
                    'status': 'VERIFIED' if old_n == new_name else 'UPDATED',
                    'freq': self.target_db.data['tp'].get(match['tp_ref'], {}).get('freq', 'N/A'),
                    'pol': self.target_db.data['tp'].get(match['tp_ref'], {}).get('pol', 'N/A'),
                    'sid': source_srv['sid'].upper(), 'old_name': old_n, 'new_name': new_name
                })
            else:
                source_tp = source_db.data['tp'].get(source_srv['sid'])
                file_stats['unm'].append({
                    'sid': source_srv['sid'].upper(), 'name': source_srv['name'],
                    'real_freq': 'N/A', 'real_pol': 'N/A'
                })
                file_stats['audits'].append({
                    'status': 'MISSED', 'sid': source_srv['sid'].upper(), 'new_name': source_srv['name']
                })

        self._generate_unmatched_report(sat_name_clean, file_stats)
        self._generate_audit_csv(sat_name_clean, file_stats)
        
        file_stats['elapsed'] = time.time() - start_t
        self.stats['sat_data'][sat_name_clean] = {
            'upd': file_stats['upd'], 'ver': file_stats['ver'], 'chk': file_stats['chk'],
            'unm': len(file_stats['unm']), 'dup': file_stats['dup']
        }
        self._merge_stats(file_stats)
        return file_stats

    def _find_match(self, source_srv, expected_e2_pos, source_db):
        source_tp = source_db.data['tp'].get(source_srv['tp_ref'])
        if not source_tp: return None, "NO_SOURCE_TP"
        
        source_freq = source_tp['freq']
        source_pol = str(source_tp['pol']).upper()
        
        # Step 1: Find matching TP in Target using Namespace Indexing
        matched_tp_key = None
        for tp_key, tp in self.target_tp_by_pos.get(expected_e2_pos, []):
            dfreq = abs(tp.get('freq', 0) - source_freq)
            if dfreq <= 5 and source_pol == str(tp.get('pol', '')).upper():
                matched_tp_key = tp_key
                break 
        
        if not matched_tp_key: return None, "NO_TARGET_TP"
            
        # Step 2: SID Match via Optimized Map
        for srv in self.target_sid_map.get(source_srv['sid'], []):
            if srv['tp_ref'] == matched_tp_key:
                return srv, "T1_MATCH"
                
        return None, "SID_NOT_FOUND"

    def _generate_unmatched_report(self, sat_name_clean, file_stats):
        if not file_stats['unm']: return
        report_fn = f"missed_{sat_name_clean}.txt"
        with open(report_fn, "w", encoding="utf-8") as f:
            f.write(f"╔{'═'*78}╗\n║ TITAN UNMATCHED SERVICE REPORT {' '.center(46)} ║\n╠{'═'*78}╣\n")
            f.write(f"║ TIMESTAMP   : {datetime.now().strftime('%Y-%m-%d %H:%M:%S').ljust(61)} ║\n")
            f.write(f"╠{'═'*12}╦{'═'*10}╦{'═'*8}╦{'═'*10}╦{'═'*34}╣\n")
            for m in file_stats['unm']:
                f.write(f"║ {str(m.get('real_freq')).ljust(10)} ║ {str(m.get('real_pol')).ljust(8)} ║ {m['sid'].ljust(6)} ║ {'TV'.ljust(8)} ║ {m['name'][:32].ljust(32)} ║\n")
            f.write(f"╚{'═'*12}╩{'═'*10}╩{'═'*8}╩{'═'*10}╩{'═'*34}╝\n")
        file_stats['unm_report_fn'] = report_fn

    def _generate_audit_csv(self, sat_name, file_stats):
        if not file_stats['audits']: return
        fn = f"audit_{sat_name}.csv"
        with open(fn, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['status', 'freq', 'pol', 'sid', 'old_name', 'new_name'])
            writer.writeheader()
            writer.writerows(file_stats['audits'])
        file_stats['audit_fn'] = fn

    def _merge_stats(self, fs):
        for key in ['upd', 'ver', 'chk', 't1', 'dup', 'skip']: self.stats[key] += fs.get(key, 0)
        self.stats['processed_csvs'] += 1
        self.stats['total_time'] += fs['elapsed']
        if 'unm_report_fn' in fs: self.stats['unmatched_reports'].append(fs['unm_report_fn'])
        if 'audit_fn' in fs: self.stats['audits'].append(fs['audit_fn'])

    def generate_json_summary_mapping(self):
        """Finalizes session and exports all metrics to titan_summary_mapping.json."""
        try:
            with open("titan_summary_mapping.json", "w", encoding="utf-8") as f:
                json.dump(self.stats, f, indent=4, default=str)
            return True
        except: return False

# ==========================================================================================
# 🚀 MAIN APPLICATION CONTROLLER
# ==========================================================================================
def main():
    if readline:
        PathCommander.initialize()

    UI.header()
    
    # [ DETAILED DESCRIPTIVE HELPER TEXT ]
    UI.box_top("TITAN OPERATIONAL GUIDE & CONFIGURATION", COLOR.M)
    UI.box_line(f"AUTO-COMPLETE : Press {COLOR.C}TAB{COLOR.W} to navigate path suggestions.", "⌨", COLOR.M)
    UI.box_line(f"STRICT SYNC   : Names match ONLY if Sat Position & Freq align.", "🛡", COLOR.M)
    UI.box_line(f"CHANNELS DIR  : Ensure source lamedb files are in './channels/'.", "📁", COLOR.M)
    UI.box_line(f"QUALITY TAGS  : (HD), (SD), and (4K) labels are preserved from target.", "💎", COLOR.M)
    UI.box_line(f"LOGGING       : Sessions are mirrored to {COLOR.C}titan_session.log{COLOR.W}", "📝", COLOR.M)
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

    sys.stdout = Logger() # Initialize Global Logger with Tab Fix
    
    source_files = sorted(glob.glob("channels/*_lamedb"), key=TitanCore.get_orbital_position)
    if not source_files:
        UI.box_top("IO ERROR", COLOR.R)
        UI.box_line("No *_lamedb files found in the /channels directory.", "✖", COLOR.R)
        UI.box_bottom(COLOR.R)
        return

    UI.box_top("SOURCE LAMEDB FILES DISCOVERED", COLOR.B)
    for idx, f in enumerate(source_files):
        p = TitanCore.get_orbital_position(f)
        p_str = f"{abs(p/10)}°W" if p < 0 else f"{p/10}°E"
        UI.box_line(f"[{COLOR.C}{str(idx).center(3)}{COLOR.W}] {COLOR.BOLD}{p_str.rjust(6)}{COLOR.W} │ {os.path.basename(f)[:52]}", "🛰", COLOR.B)
    UI.box_bottom(COLOR.B)
    
    print(f"\n  {COLOR.BOLD}[COMMANDS]{COLOR.W}  {COLOR.G}(B) Batch Sync All{COLOR.W}  │  {COLOR.G}(#) Single Source{COLOR.W}  │  {COLOR.R}(Q) Quit{COLOR.W}")
    
    try:
        choice = input(f"\n {COLOR.M} weaver@titan{COLOR.W}:~$ ").strip().upper()
    except (EOFError, KeyboardInterrupt): return
    
    if choice == 'Q': return
    to_proc = source_files if choice == 'B' else [source_files[int(choice)]] if choice.isdigit() and int(choice) < len(source_files) else []
    if not to_proc: return

    titan = TitanCore(db)
    for f_path in to_proc:
        print(f"\n {COLOR.C}◈ {COLOR.BOLD}SYNCHRONIZING:{COLOR.W} {COLOR.UNDERLINE}{os.path.basename(f_path)}{COLOR.W}")
        source_db = EnigmaDB(f_path)
        if not source_db.load(): continue
        titan.process_source_lamedb(source_db, os.path.basename(f_path))

    # FINAL REPORT
    UI.box_top("TITAN ELITE V10.3 - SESSION ANALYTICS", COLOR.G)
    UI.box_line(f"PROCESSING PERFORMANCE", "⚡", COLOR.G)
    UI.box_line(f"  ├─ Files Processed   : {titan.stats['processed_csvs']}", " ", COLOR.G)
    UI.box_line(f"  ├─ Total Runtime     : {titan.stats['total_time']:.4f} seconds", " ", COLOR.G)
    UI.box_line(f"  └─ Avg Speed         : {titan.stats['chk'] / max(1, titan.stats['total_time']):.1f} rows/sec", " ", COLOR.G)
    
    UI.box_line(f"DATABASE UPDATE METRICS (STRICT MODE)", "📊", COLOR.G)
    UI.box_line(f"  ├─ Total Scanned     : {titan.stats['chk']}", " ", COLOR.G)
    UI.box_line(f"  ├─ Verified          : {COLOR.C}{titan.stats['ver']}{COLOR.W}", " ", COLOR.G)
    UI.box_line(f"  ├─ Updates           : {COLOR.G}{titan.stats['upd']}{COLOR.W}", " ", COLOR.G)
    UI.box_line(f"  ├─ Hard Misses       : {COLOR.R}{len(titan.stats['unm'])}{COLOR.W}", " ", COLOR.G)
    UI.box_line(f"  └─ Duplicates Found  : {COLOR.Y}{titan.stats['dup']}{COLOR.W}", " ", COLOR.G)

    UI.box_line(f"SATELLITE HEAT MAP", "🗺", COLOR.G)
    for sat, s_data in titan.stats['sat_data'].items():
        m_tag = f"{COLOR.G}U:{s_data['upd']}{COLOR.W} {COLOR.R}M:{s_data['unm']}{COLOR.W}"
        UI.box_line(f"  ├─ {sat[:30].ljust(30)} : [{m_tag}]", " ", COLOR.G)
    UI.box_line("  └─ Sync Conf  : " + UI.progress_bar(titan.stats['upd'] + titan.stats['ver'], titan.stats['chk']), " ", COLOR.G)

    UI.box_line(f"DATA INTEGRITY & IO", "🛡", COLOR.G)
    if titan.stats['upd'] > 0:
        db.save()
        UI.box_line(f"  ├─ Target DB   : {COLOR.G}SAVED & COMMITTED{COLOR.W}", " ", COLOR.G)
    else:
        UI.box_line(f"  ├─ Target DB   : NO CHANGES REQUIRED", " ", COLOR.G)
    
    titan.generate_json_summary_mapping()
    UI.box_line(f"  └─ JSON Status : titan_summary_mapping.json created", " ", COLOR.G)
    UI.box_bottom(COLOR.G)
    print(f"\n {COLOR.G}🏆 TITAN SESSION CONCLUDED. LOGGED TO titan_session.log{COLOR.W}\n")

if __name__ == "__main__":
    main()
