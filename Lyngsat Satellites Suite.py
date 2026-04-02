#!/usr/bin/env python3
"""
LyngSat Satellite Master - Version 5.0 | HYPER-GRID OBSIDIAN
---------------------------------------------------------------
FEATURES:
- Ultra-Enhanced UI: Rounded box drawings, segmented telemetry blocks.
- Smart File Routing: Automated export to 'channels/' subdirectory.
- Surgical Strike Logic: Zero-leaks policy on sidebars and stream links.
- Performance: Preserves same-row SID validation and aggressive de-noising.
- Advanced Analytics: Real-time encryption/FTA telemetry dashboard.
- Dependency Guard: Failsafes for missing external libraries.
- Band Filtering: Limits scans to standard C-Band (3400-4200) and Ku-Band (10700-12750).
- Batch Processing: Multi-URL parsing engine with automated queuing.
- Smart Naming: Dynamic CSV output routing (Satellite@Position_Full_Services.csv).
"""

import os
import sys

# ==============================================================================
# [ 🛡️ DEPENDENCY GUARD ]
# ==============================================================================
def check_dependencies():
    missing = []
    try:
        import curl_cffi
    except ImportError:
        missing.append("curl_cffi")
    try:
        import bs4
    except ImportError:
        missing.append("beautifulsoup4")

    if missing:
        c = "\033[38;5;196m"
        r = "\033[0m"
        print(f"\n{c}╭──────────────────────────────────────────────────╮{r}")
        print(f"{c}│  ⚡ CRITICAL ERROR: MISSING DEPENDENCIES         │{r}")
        print(f"{c}│{r}  The following modules are missing:              {c}│{r}")
        for m in missing:
            print(f"{c}│{r}  • {m:<45} {c}│{r}")
        print(f"{c}│{r}  FIX: {sys.executable} -m pip install {' '.join(missing):<14} {c}│{r}")
        print(f"{c}╰──────────────────────────────────────────────────╯{r}\n")
        sys.exit(1)

check_dependencies()

import re
import csv
import time
import signal
import unicodedata
from datetime import datetime
from typing import Optional, Dict, List
from curl_cffi import requests
from bs4 import BeautifulSoup

# ==============================================================================
# [ 🎨 HYPER-GLOW COLOR THEME ]
# ==============================================================================
class ColorTheme:
    BASE    = "\033[38;5;250m"
    GOLD    = "\033[38;5;220m"
    SKY     = "\033[38;5;117m"
    LIME    = "\033[38;5;121m"
    CRIMSON = "\033[38;5;196m"
    VIOLET  = "\033[38;5;141m"
    TEAL    = "\033[38;5;51m"
    NEON_P  = "\033[38;5;201m" # Neon Pink
    NEON_G  = "\033[38;5;82m"  # Neon Green
    NEON_B  = "\033[38;5;27m"  # Deep Blue
    CYAN    = "\033[38;5;45m"
    ORANGE  = "\033[38;5;208m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    REVERSE = "\033[7m"
    ENDC    = "\033[0m"

# ==============================================================================
# [ 🖼️ MASTER UI RENDERER ]
# ==============================================================================
class UIRenderer:
    ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    DEFAULT_WIDTH = 90

    def __init__(self, color: ColorTheme):
        self.color = color
        self.terminal_width = self._get_terminal_width()

    def _get_terminal_width(self) -> int:
        try: return os.get_terminal_size().columns
        except: return self.DEFAULT_WIDTH

    @staticmethod
    def strip_ansi(text: str) -> str:
        return UIRenderer.ANSI_ESCAPE.sub('', text)

    @staticmethod
    def visible_width(text: str) -> int:
        stripped = UIRenderer.strip_ansi(text)
        width = 0
        for char in stripped:
            eaw = unicodedata.east_asian_width(char)
            if eaw in ('F', 'W'): width += 2
            elif unicodedata.category(char) in ('Mn', 'Me', 'Cf'): width += 0
            else: width += 1
        return width

    def print_banner(self) -> None:
        c = self.color
        w = self.terminal_width
        
        # Rounded Boxes Setup
        top = "╭" + "─" * (w - 2) + "╮"
        bot = "╰" + "─" * (w - 2) + "╯"
        
        print(f"{c.NEON_B}{top}{c.ENDC}")
        
        title = "  🛰️   L Y N G S A T   S A T E L L I T E   M A S T E R  "
        version = " [ v5.0 | OBSIDIAN-GRID ] "
        
        inner_space = w - 2
        gap = inner_space - self.visible_width(title) - self.visible_width(version)
        
        print(f"{c.NEON_B}│{c.ENDC}{c.NEON_P}{c.BOLD}{title}{c.ENDC}{' ' * max(0, gap)}{c.SKY}{version}{c.NEON_B}│{c.ENDC}")
        
        # Sub-header graphic line
        sub_line = "  " + "─" * (w - 6) + "  "
        print(f"{c.NEON_B}│{c.ENDC}{c.DIM}{sub_line}{c.ENDC}{c.NEON_B}│{c.ENDC}")
        
        desc = "  DEEP-SCAN SURGICAL ENGINE • NEON-TELEMETRY • BATCH CHANNEL-ROUTING v5  "
        print(f"{c.NEON_B}│{c.ENDC}{c.TEAL}{desc:^{inner_space}}{c.ENDC}{c.NEON_B}│{c.ENDC}")
        
        print(f"{c.NEON_B}{bot}{c.ENDC}")

    def draw_section_head(self, title: str):
        c = self.color
        w = self.terminal_width
        print(f"\n{c.NEON_B}├─ {c.BOLD}{c.GOLD}{title}{c.ENDC} {c.NEON_B}{'─' * (w - len(title) - 5)}╮{c.ENDC}")

    def draw_divider(self):
        print(f"{self.color.DIM}{'─' * self.terminal_width}{self.color.ENDC}")

# ==============================================================================
# [ 🛰️ SURGICAL SCANNER CORE ]
# ==============================================================================
class SatelliteScanner:
    def __init__(self):
        self.color = ColorTheme()
        self.ui = UIRenderer(self.color)
        self.running = True
        self._reset_stats()
        signal.signal(signal.SIGINT, self._handle_exit)

    def _reset_stats(self):
        self.stats = {
            "total": 0,
            "muxes": 0,
            "tv": 0, 
            "radio": 0, 
            "fta": 0, 
            "encrypted": 0,
            "tv_fta": 0,
            "tv_enc": 0,
            "radio_fta": 0,
            "radio_enc": 0
        }

    def _handle_exit(self, sig, frame):
        self.running = False
        print(f"\n{self.color.CRIMSON}🛑 [EMERGENCY KILL] System shutdown initiated...{self.color.ENDC}")

    def clean(self, text: str) -> str:
        if not text: return ""
        return " ".join(text.replace('\xa0', ' ').split()).strip()

    def _denoise_html(self, soup):
        """Aggressive path-lockdown and sidebar purging."""
        for a in soup.find_all('a', href=re.compile(r'/(stream|news|advert|lyngsat-logo|shop)/', re.I)):
            a.decompose()
        for junk in soup.find_all(['table', 'td', 'div'], bgcolor=re.compile(r'lemonchiffon|lightgreen|#ccffcc|#ffffcc', re.I)):
            junk.decompose()
        for tag in soup.find_all(string=re.compile(r'(News at LyngSat|LyngSat Stream)', re.I)):
            p = tag.find_parent(['table', 'div'])
            if p: p.decompose()

    def parse_satellite(self, url: str):
        try:
            self._reset_stats()
            self.ui.draw_section_head("INITIALIZING UPLINK")
            self.log_proc("LINK", f"Acquiring target: {url}", self.color.GOLD)
            
            res = requests.get(url, impersonate="chrome", timeout=25)
            soup = BeautifulSoup(res.text, 'html.parser')

            title_node = soup.title.string if soup.title else "Satellite"
            
            # Smart Naming Logic: Match "<Name> at <Position>" format
            name_pos_m = re.search(r'(.*?)\s+at\s+(\d+\.?\d*)\s?°?\s*([EW])', title_node, re.I)
            if name_pos_m:
                # Replace '/' with '-' to prevent OS directory traversal errors while maintaining style
                sat_name = name_pos_m.group(1).strip().replace('/', '-')
                pos_val = name_pos_m.group(2)
                pos_dir = name_pos_m.group(3).upper()
                pos_label = f"{sat_name}@{pos_val}{pos_dir}"
            else:
                # Fallback to pure position
                sat_m = re.search(r'(\d+\.?\d*)\s?°?\s*([EW])', title_node)
                pos_label = f"{sat_m.group(1)}{sat_m.group(2).upper()}" if sat_m else "Sat_Data"
            
            # PHASE 1: DISCOVERY
            mux_queue = []
            seen_tps = set()
            
            for row in soup.find_all('tr'):
                if not self.running: break
                freq_td = row.find('td', style=lambda s: s and "linear-gradient" in s) or row.find('td', bgcolor=re.compile(r'(#ffffcc|#ffcc99)', re.I))
                
                if freq_td:
                    f_link = freq_td.find('a')
                    if f_link and f_link.get('href'):
                        f_text = self.clean(f_link.get_text())
                        f_match = re.search(r'(\d{4,5})\s*([HVLR])', f_text)
                        
                        if f_match:
                            freq, pol = f_match.group(1), f_match.group(2).upper()
                            
                            # --- BAND FILTERING LOGIC ---
                            # C-band: 3400-4200
                            # Ku-band: 10700-12750
                            freq_val = int(freq)
                            if not ((3400 <= freq_val <= 4200) or (10700 <= freq_val <= 12750)):
                                continue
                            
                            mux_url = f_link['href']
                            if not mux_url.startswith('http'):
                                mux_url = f"https://www.lyngsat.com{mux_url}" if mux_url.startswith('/') else f"https://www.lyngsat.com/muxes/{mux_url}"
                            
                            sr_td = freq_td.find_next_sibling('td')
                            sr, fec, sys_type = "0", "Auto", "DVB-S"
                            if sr_td:
                                content = " ".join([self.clean(p) for p in sr_td.get_text("|", strip=True).split("|")])
                                sys_m = re.search(r'(DVB-S[2X]?|DSS|ISDB)', content, re.I)
                                fec_m = re.search(r'(\d/\d)', content)
                                sr_m = re.search(r'\b(\d{3,5})\b', content.replace(freq, ""))
                                sys_type = sys_m.group(1) if sys_m else "DVB-S"
                                fec = fec_m.group(1) if fec_m else "Auto"
                                sr = sr_m.group(1) if sr_m else "0"

                            key = f"{freq}{pol}{sr}"
                            if key not in seen_tps:
                                seen_tps.add(key)
                                mux_queue.append({"f": freq, "p": pol, "sr": sr, "fec": fec, "sys": sys_type, "url": mux_url})

            self.stats['muxes'] = len(mux_queue)
            self.ui.draw_section_head(f"TARGET ACQUIRED: {pos_label}")
            self.log_proc("DATA", f"Found {len(mux_queue)} transponders. Commencing Surgical Scan.", self.color.LIME)

            # PHASE 2: SURGICAL SCAN
            master_data = []
            total_tps = len(mux_queue)

            for idx, mux in enumerate(mux_queue, 1):
                if not self.running: break
                
                progress_pct = int((idx/total_tps)*20)
                p_bar = f"{self.color.NEON_B}│{self.color.NEON_G}{'█' * progress_pct}{self.color.DIM}{'░' * (20-progress_pct)}{self.color.NEON_B}│{self.color.ENDC}"
                
                meta_str = f"{mux['f']} {mux['p']} • SR:{mux['sr']} • {mux['sys']}"
                self.log_proc(f"SCAN {idx:02}/{total_tps:02}", f"{p_bar} {self.color.SKY}{meta_str}{self.color.ENDC}", self.color.TEAL)
                
                try:
                    m_res = requests.get(mux['url'], impersonate="chrome", timeout=15)
                    m_soup = BeautifulSoup(m_res.text, 'html.parser')
                    self._denoise_html(m_soup)
                    
                    data_table = m_soup.find('table', class_='mux-table')
                    if not data_table:
                        max_links = 0
                        for tbl in m_soup.find_all('table'):
                            valid_links = tbl.find_all('a', href=re.compile(r'/(tvchannels|radiochannels)/', re.I))
                            if len(valid_links) > max_links:
                                max_links = len(valid_links)
                                data_table = tbl

                    if not data_table: continue
                    mux_sid_registry = set()

                    for m_row in data_table.find_all('tr'):
                        tds = m_row.find_all('td')
                        if len(tds) < 3: continue

                        sid_text = self.clean(tds[0].get_text()).replace('*', '')
                        if sid_text.isdigit() and 1 <= len(sid_text) <= 6:
                            if sid_text == mux['f'] or sid_text == mux['sr']: continue
                            
                            ch_link = m_row.find('a', href=re.compile(r'/(tvchannels|radiochannels)/', re.I))
                            if not ch_link or "/stream/" in ch_link.get('href', ''): continue
                            if sid_text in mux_sid_registry: continue

                            name = self.clean(ch_link.get_text())
                            ch_type = "2" if "radio" in ch_link['href'].lower() else "1"
                            
                            enc = "FTA"
                            r_html = str(m_row).lower()
                            if any(x in r_html for x in ['background:#ffb6c1', 'bgcolor="pink"', 'crypt', 'nagravision', 'videoguard', 'irdeto']):
                                enc = "Encrypted"
                                self.stats["encrypted"] += 1
                                e_ico = f"{self.color.CRIMSON}🔒 CRYPT{self.color.ENDC}"
                            else:
                                self.stats["fta"] += 1
                                e_ico = f"{self.color.NEON_G}🔓 FTA  {self.color.ENDC}"

                            # Expanded Statistics Logic
                            self.stats["total"] += 1
                            if ch_type == "1": 
                                self.stats["tv"] += 1
                                if enc == "FTA": self.stats["tv_fta"] += 1
                                else: self.stats["tv_enc"] += 1
                                t_ico = f"{self.color.SKY}📺 TV   {self.color.ENDC}"
                            else: 
                                self.stats["radio"] += 1
                                if enc == "FTA": self.stats["radio_fta"] += 1
                                else: self.stats["radio_enc"] += 1
                                t_ico = f"{self.color.ORANGE}📻 RADIO{self.color.ENDC}"

                            master_data.append([
                                mux['f'], mux['p'], mux['sr'], mux['fec'], mux['sys'],
                                sid_text, name, ch_type, enc
                            ])
                            mux_sid_registry.add(sid_text)
                            
                            # Maximized Detailed Output for each Mux row
                            print(f"      {self.color.DIM}├─{self.color.ENDC} {self.color.CYAN}[MUX: {mux['f']} {mux['p']}]{self.color.ENDC} {self.color.VIOLET}[SID: {sid_text:>5}]{self.color.ENDC} [{t_ico}] [{e_ico}] ─ {self.color.BASE}{name}{self.color.ENDC}")
                                
                    time.sleep(0.05)
                except Exception as e:
                    self.log_proc("WARN", f"Mux Error: {e}", self.color.CRIMSON)

            # PHASE 3: FINALIZATION
            if master_data:
                self._save_csv(pos_label, master_data)
                self._print_stats()
            else:
                self.log_proc("FAIL", "Uplink returned empty dataset. Check source URL.", self.color.CRIMSON)

        except Exception as e:
            self.log_proc("FATAL", f"Core Exception: {e}", self.color.CRIMSON)

    def _print_stats(self):
        c = self.color
        self.ui.draw_section_head("FINAL TELEMETRY REPORT")
        
        box_w = 46
        line = "─" * (box_w - 2)
        print(f"   {c.CYAN}╭{line}╮{c.ENDC}")
        
        def row(label, val, color):
            inner = f" {label:<28} {val:>13} "
            print(f"   {c.CYAN}│{c.ENDC}{color}{inner}{c.ENDC}{c.CYAN}│{c.ENDC}")

        # Expanded Full Output Report Breakdown
        row("TOTAL MUXES SCANNED", self.stats['muxes'], c.GOLD)
        row("TOTAL SERVICES FOUND", self.stats['total'], c.SKY)
        print(f"   {c.CYAN}├{line}┤{c.ENDC}")
        row("TELEVISION (TV)", self.stats['tv'], c.NEON_P)
        row("  ├─ TV FTA", self.stats['tv_fta'], c.LIME)
        row("  ╰─ TV ENCRYPTED", self.stats['tv_enc'], c.CRIMSON)
        print(f"   {c.CYAN}├{line}┤{c.ENDC}")
        row("RADIO STATIONS", self.stats['radio'], c.NEON_B)
        row("  ├─ RADIO FTA", self.stats['radio_fta'], c.LIME)
        row("  ╰─ RADIO ENCRYPTED", self.stats['radio_enc'], c.CRIMSON)
        
        print(f"   {c.CYAN}╰{line}╯{c.ENDC}")
        print(f"\n   {c.NEON_G}{c.REVERSE}  MISSION SUCCESSFUL  {c.ENDC}\n")

    def _save_csv(self, label: str, data: List[List[str]]):
        # SUBFOLDER ROUTING
        folder = "channels"
        if not os.path.exists(folder):
            os.makedirs(folder)
            self.log_proc("FILE", f"Created directory: {folder}/", self.color.ORANGE)

        # Smart Naming updated syntax mapping
        filename = os.path.join(folder, f"{label}_Full_Services.csv")
        headers = ["Frequency", "Polarization", "SymbolRate", "FEC", "System", "SID", "ServiceName", "Type", "Encryption"]
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(data)
            
        self.log_proc("EXPORT", f"Database committed to {filename}", self.color.GOLD)

    def log_proc(self, tag: str, msg: str, color: str):
        ts = datetime.now().strftime("%H:%M:%S")
        tag_box = f"{self.color.BOLD}{color}[{tag}]{self.color.ENDC}"
        print(f"{self.color.DIM}{ts}{self.color.ENDC} {tag_box:<18} {msg}")

    def run(self):
        os.system('clear' if os.name == 'posix' else 'cls')
        self.ui.print_banner()
        print(f"\n {self.color.NEON_P}▶{self.color.ENDC} {self.color.BOLD}UPLINK TARGETS (Enter URLs one by one. Leave empty to start):{self.color.ENDC}")
        
        urls = []
        while True:
            url = input(f"   {self.color.CYAN}├─ URL:{self.color.ENDC} ").strip()
            if not url:
                break
            urls.append(url)
            
        if urls:
            self.log_proc("BATCH", f"Initiating batch scan for {len(urls)} targets.", self.color.NEON_G)
            for idx, u in enumerate(urls, 1):
                if not self.running: break
                if len(urls) > 1:
                    self.ui.draw_divider()
                    self.log_proc("QUEUE", f"Processing target {idx}/{len(urls)}", self.color.VIOLET)
                self.parse_satellite(u)
        else:
            self.log_proc("ABORT", "No URLs provided. System standby.", self.color.CRIMSON)

if __name__ == "__main__":
    app = SatelliteScanner()
    app.run()
