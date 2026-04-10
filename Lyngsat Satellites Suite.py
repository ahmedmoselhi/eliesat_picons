#!/usr/bin/env python3
"""
LyngSat Satellite Master - Version 9.0 | OMNI-GRID ZENITH (FULL RESTORATION)
-------------------------------------------------------------------------------
RESTORATION MANIFEST:
- [UI] Restored v7.0 Full ASCII Border Logic & Cyber-Grid Banner.
- [UI] Restored Zenith Iconography (📡, 🛰️, 💎, 🔓, 🔒, 📦).
- [LOGS] Restored Detailed Service Extraction (Real-time SID/Name/Encryption).
- [LOGS] Restored Deep-Scan Telemetry (SR, FEC, Modulation per Mux).
- [LOGS] Restored System Telemetry Block (OS/Arch/Time).
- [CORE] Band-Splitting v2: Surgical C-Band (3400-4200) & Ku-Band (10700-12750).
- [CORE] Orbital Offset: +0.1° increment for C-Band namespaces.
- [EXPORT] Enigma2 lamedb v4 + CSV Provider-tagged Routing.
- [MEMORY] Persistent URL/Position Ledger (url.txt) with Control Center.
"""

import os
import sys
import platform
import re
import csv
import time
import signal
import unicodedata
from datetime import datetime
from typing import Optional, Dict, List, Tuple
from curl_cffi import requests
from bs4 import BeautifulSoup

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
        print(f"\n{c}╔══════════════════════════════════════════════════╗{r}")
        print(f"{c}║  ⚡ CRITICAL ERROR: MISSING CORE MODULES         ║{r}")
        print(f"{c}╟──────────────────────────────────────────────────╢{r}")
        for m in missing:
            print(f"{c}║{r}  • {m:<45} {c}║{r}")
        print(f"{c}║{r}  FIX: {sys.executable} -m pip install {' '.join(missing):<14} {c}║{r}")
        print(f"{c}╚══════════════════════════════════════════════════╝{r}\n")
        sys.exit(1)

check_dependencies()

# ==============================================================================
# [ 🎨 ZENITH COLOR PALETTE ]
# ==============================================================================
class ColorTheme:
    GOLD    = "\033[38;5;220m"
    SKY     = "\033[38;5;117m"
    LIME    = "\033[38;5;121m"
    CRIMSON = "\033[38;5;196m"
    VIOLET  = "\033[38;5;141m"
    TEAL    = "\033[38;5;51m"
    NEON_P  = "\033[38;5;201m" 
    NEON_G  = "\033[38;5;82m"  
    NEON_B  = "\033[38;5;27m"  
    CYAN    = "\033[38;5;45m"
    ORANGE  = "\033[38;5;208m"
    WHITE   = "\033[38;5;255m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    ENDC    = "\033[0m"

# ==============================================================================
# [ 🖼️ MASTER UI RENDERER (FULL DECOR) ]
# ==============================================================================
class UIRenderer:
    def __init__(self, color: ColorTheme):
        self.color = color
        self.w = 95

    def print_banner(self) -> None:
        c = self.color
        banner_art = [
            r"   __ __ __ __ __    ___   ___   ___  ____ ___  ____ ___   _  _ ",
            r"  / / \ \ \ \ \ \ \  / _ \ | _ ) / __||_  _|/ _ \ | _ \ / _ \ | \| |",
            r" / /   \ \ \ \ \ \ \| (_) || _ \ \__ \ _| || (_) ||   /| (_) || .  |",
            r"/_/     \_\_\_\_\_\_\\___/ |___/ |___/|___|\___/ |_|_\ \___/ |_|\_|",
            r"      [ L Y N G S A T   S A T E L L I T E   M A S T E R   v9.0 ]    "
        ]
        print(f"{c.NEON_B}╔{'═' * (self.w-2)}╗{c.ENDC}")
        for line in banner_art:
            print(f"{c.NEON_B}║{c.ENDC}{c.CYAN}{c.BOLD}{line:^{self.w-2}}{c.ENDC}{c.NEON_B}║{c.ENDC}")
        
        info = f" ZENITH FULL-RESTORE • {datetime.now().strftime('%d %b %Y')} • OMNI-GRID ENGINE "
        print(f"{c.NEON_B}╠{'═' * (self.w-2)}╣{c.ENDC}")
        print(f"{c.NEON_B}║{c.ENDC}{c.GOLD}{info:^{self.w-2}}{c.ENDC}{c.NEON_B}║{c.ENDC}")
        print(f"{c.NEON_B}╚{'═' * (self.w-2)}╝{c.ENDC}")

    def draw_telemetry(self):
        c = self.color
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        stats = f"SYSTEM: {platform.system()} | PY: {platform.python_version()} | NODE: {platform.node()} | {now}"
        print(f" {c.DIM}╔{'═' * (self.w-12)}╗{c.ENDC}")
        print(f" {c.DIM}║{c.ENDC} {c.LIME}📊 TELEMETRY:{c.ENDC} {c.SKY}{stats:<{self.w-27}}{c.ENDC} {c.DIM}║{c.ENDC}")
        print(f" {c.DIM}╚{'═' * (self.w-12)}╝{c.ENDC}")

    def draw_section(self, title: str, icon: str = "📡"):
        c = self.color
        bar = "═" * (self.w - len(title) - 12)
        print(f"\n{c.NEON_B}╠═╡ {c.BOLD}{c.WHITE}{icon} {title}{c.ENDC} {c.NEON_B}{bar}╾{c.ENDC}")

# ==============================================================================
# [ 🛰️ OMNI-SCAN ENGINE ]
# ==============================================================================
class SatelliteScanner:
    URL_FILE = "url.txt"

    def __init__(self):
        self.color = ColorTheme()
        self.ui = UIRenderer(self.color)
        self.running = True
        self._reset_stats()
        signal.signal(signal.SIGINT, self._handle_exit)

    def _reset_stats(self):
        self.stats = {"total": 0, "muxes": 0, "tv": 0, "radio": 0, "fta": 0, "encrypted": 0}

    def _handle_exit(self, sig, frame):
        self.running = False
        print(f"\n{self.color.CRIMSON}🛑 [EMERGENCY KILL] Shutdown protocol engaged...{self.color.ENDC}")

    def clean(self, text: str) -> str:
        return " ".join(text.replace('\xa0', ' ').split()).strip() if text else ""

    def _save_url(self, url: str, pos: str):
        entries = {}
        if os.path.exists(self.URL_FILE):
            with open(self.URL_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    if ',' in line:
                        u, p = line.strip().split(',', 1)
                        entries[u] = p
        entries[url] = pos
        with open(self.URL_FILE, 'w', encoding='utf-8') as f:
            for u, p in entries.items(): f.write(f"{u},{p}\n")

    def _load_urls(self) -> List[tuple]:
        if not os.path.exists(self.URL_FILE): return []
        with open(self.URL_FILE, 'r', encoding='utf-8') as f:
            return [line.strip().split(',', 1) for line in f if ',' in line]

    def parse_satellite(self, url: str, stored_pos: Optional[str] = None):
        try:
            self._reset_stats()
            self.ui.draw_section("UPLINK SYNCHRONIZATION", "🛰️")
            self.log_proc("LINK", f"Acquiring: {url}", self.color.GOLD)
            
            res = requests.get(url, impersonate="chrome", timeout=25)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            sat_name, pos_val, pos_dir = "Unknown-Sat", 0.0, "E"
            title_node = soup.title.string if soup.title else ""
            m = re.search(r'(.*?)\s+at\s+(\d+\.?\d*)\s?°?\s*([EW])', title_node, re.I)
            if m:
                sat_name, pos_val, pos_dir = m.group(1).strip().replace('/', '-'), float(m.group(2)), m.group(3).upper()
            elif stored_pos:
                m_stored = re.search(r'(\d+\.?\d*)\s*([EW])', stored_pos, re.I)
                if m_stored: pos_val, pos_dir = float(m_stored.group(1)), m_stored.group(2).upper()
            
            self._save_url(url, f"{pos_val}{pos_dir}")
            self.ui.draw_section(f"DATA STREAM: {sat_name} [{pos_val}{pos_dir}]", "💎")

            mux_queue, seen = [], set()
            for row in soup.find_all('tr'):
                if not self.running: break
                freq_td = row.find('td', style=lambda s: s and "linear-gradient" in s) or row.find('td', bgcolor=re.compile(r'(#ffffcc|#ffcc99)', re.I))
                if freq_td and freq_td.find('a'):
                    f_link = freq_td.find('a')
                    f_text = self.clean(f_link.get_text())
                    f_m = re.search(r'(\d{4,5})\s*([HVLR])', f_text)
                    if f_m:
                        freq, pol = f_m.group(1), f_m.group(2).upper()
                        freq_val = int(freq)
                        band = "C-Band" if 3400 <= freq_val <= 4200 else "KU-Band" if 10700 <= freq_val <= 12750 else None
                        if not band: continue
                        
                        m_url = f_link['href']
                        if not m_url.startswith('http'): 
                            m_url = f"https://www.lyngsat.com{m_url}" if m_url.startswith('/') else f"https://www.lyngsat.com/muxes/{m_url}"
                        
                        sr_td = freq_td.find_next_sibling('td')
                        sr, fec, sys = "0", "Auto", "DVB-S"
                        if sr_td:
                            c = " ".join([self.clean(p) for p in sr_td.get_text("|", strip=True).split("|")])
                            sys_m, fec_m, sr_m = re.search(r'(DVB-S[2X]?|DSS|ISDB)', c, re.I), re.search(r'(\d/\d)', c), re.search(r'\b(\d{3,5})\b', c.replace(freq, ""))
                            sys = sys_m.group(1) if sys_m else "DVB-S"
                            fec = fec_m.group(1) if fec_m else "Auto"
                            sr = sr_m.group(1) if sr_m else "0"

                        if f"{freq}{pol}{sr}" not in seen:
                            seen.add(f"{freq}{pol}{sr}")
                            mux_queue.append({"f": freq, "p": pol, "sr": sr, "fec": fec, "sys": sys, "url": m_url, "band": band})

            c_data, ku_data = [], []
            for i, mux in enumerate(mux_queue, 1):
                if not self.running: break
                p_pct = int((i/len(mux_queue))*20)
                p_bar = f"{self.color.NEON_B}╟{self.color.NEON_G}{'█' * p_pct}{self.color.DIM}{'░' * (20-p_pct)}{self.color.NEON_B}╢{self.color.ENDC}"
                telemetry = f"{mux['f']}{mux['p']} ┃ {mux['sys']} ┃ SR:{mux['sr']} ┃ FEC:{mux['fec']}"
                self.log_proc(f"SCAN {i:02}/{len(mux_queue):02}", f"{p_bar} {self.color.SKY}{telemetry}{self.color.ENDC}", self.color.TEAL)
                
                try:
                    m_res = requests.get(mux['url'], impersonate="chrome", timeout=15)
                    m_soup = BeautifulSoup(m_res.text, 'html.parser')
                    
                    onid, tid = 0, 0
                    ot_m = re.search(r'ONID-TID:.*?>(\d+)-(\d+)', m_res.text, re.I | re.DOTALL)
                    if ot_m: onid, tid = int(ot_m.group(1)), int(ot_m.group(2))
                    
                    table = m_soup.find('table', class_='mux-table') or m_soup.find('table', border="0", cellspacing="0", cellpadding="0")
                    if not table: continue
                    mux_sid_registry = set()

                    for m_row in table.find_all('tr'):
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
                            prov = "Unknown"
                            p_link = m_row.find('a', href=re.compile(r'/packages/', re.I))
                            if p_link: prov = self.clean(p_link.get_text())
                            
                            enc = "FTA"
                            if any(x in str(m_row).lower() for x in ['#ffb6c1', 'pink', 'crypt', 'nagra', 'videoguard', 'irdeto']):
                                enc = "Encrypted"
                                self.stats["encrypted"] += 1
                                lock_icon = f"{self.color.CRIMSON}🔒{self.color.ENDC}"
                            else:
                                self.stats["fta"] += 1
                                lock_icon = f"{self.color.NEON_G}🔓{self.color.ENDC}"

                            # FULL RESTORATION: Detailed Extraction Logs
                            type_icon = f"{self.color.NEON_P}📺{self.color.ENDC}" if ch_type == "1" else f"{self.color.SKY}📻{self.color.ENDC}"
                            svc_msg = f"{type_icon} {self.color.GOLD}{sid_text:<5}{self.color.ENDC} ┃ {self.color.WHITE}{name[:28]:<28}{self.color.ENDC} ┃ {lock_icon} {self.color.DIM}{enc:<9}{self.color.ENDC}"
                            self.log_proc("SERVICE", svc_msg, self.color.VIOLET)

                            self.stats["total"] += 1
                            if ch_type == "1": self.stats["tv"] += 1
                            else: self.stats["radio"] += 1

                            entry = [mux['f'], mux['p'], mux['sr'], mux['fec'], mux['sys'], sid_text, name, ch_type, enc, prov, onid, tid]
                            (c_data if mux['band'] == "C-Band" else ku_data).append(entry)
                            mux_sid_registry.add(sid_text)
                except Exception as e:
                    self.log_proc("WARN", f"Mux Logic Fail: {e}", self.color.CRIMSON)

            if c_data: self._save_all(f"{sat_name} (C-Band)", pos_val + 0.1, pos_dir, c_data)
            if ku_data: self._save_all(f"{sat_name} (KU-Band)", pos_val, pos_dir, ku_data)
            self._print_stats()

        except Exception as e:
            self.log_proc("FATAL", f"Global Exception: {e}", self.color.CRIMSON)

    def _save_all(self, label: str, pos_val: float, pos_dir: str, data: List[List[str]]):
        folder = "channels"
        if not os.path.exists(folder): os.makedirs(folder)
        base_name = f"{label}@{pos_val}{pos_dir}"
        
        # CSV Export
        csv_path = os.path.join(folder, f"{base_name}.csv")
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Freq", "Pol", "SR", "FEC", "Sys", "SID", "Name", "Type", "Enc", "Prov", "ONID", "TID"])
            writer.writerows(data)
        
        # Enigma2 lamedb v4 Export
        db_path = os.path.join(folder, f"{base_name}_lamedb")
        p_int = int(pos_val * 10)
        e2_pos, dvb_pos = (3600 - p_int, -p_int) if pos_dir == 'W' else (p_int, p_int)
        
        tps, svcs = {}, []
        for r in data:
            ns_hex = f"{(e2_pos << 16) | (int(r[0]) & 0xFFFF):08x}"
            tk = f"{ns_hex}:{int(r[11]):04x}:{int(r[10]):04x}"
            if tk not in tps:
                pol_i = {"H":0,"V":1,"L":2,"R":3}.get(r[1], 0)
                sys_i = 1 if "S2" in r[4] else 0
                tps[tk] = f"\ts {int(r[0])*1000}:{int(r[2])*1000}:{pol_i}:0:{dvb_pos}:2:0:{sys_i}:0:2:2"
            svcs.append((f"{int(r[5]):04x}:{tk}:{1 if r[7]=='1' else 2}:0:0", r[6], f"p:{r[9]}"))

        with open(db_path, 'w', encoding='utf-8') as f:
            f.write("eDVB services /4/\ntransponders\n")
            for k, v in tps.items(): f.write(f"{k}\n{v}\n/\n")
            f.write("end\nservices\n")
            for s1, s2, s3 in svcs: f.write(f"{s1}\n{s2}\n{s3}\n")
            f.write("end\n")
        self.log_proc("EXPORT", f"Committed: {base_name}", self.color.GOLD)

    def _print_stats(self):
        c = self.color
        self.ui.draw_section("MISSION TELEMETRY ARCHIVE", "📦")
        w = 50
        print(f"   {c.CYAN}╔{'═' * (w-2)}╗{c.ENDC}")
        def r(l, v, cl): print(f"   {c.CYAN}║{c.ENDC}{cl} {l:<32} {v:>13} {c.ENDC}{c.CYAN}║{c.ENDC}")
        r("TOTAL SERVICES MAPPED", self.stats['total'], c.SKY)
        r("TELEVISION NODES", self.stats['tv'], c.NEON_P)
        r("RADIO NODES", self.stats['radio'], c.NEON_B)
        r("FTA CLEARANCE", self.stats['fta'], c.NEON_G)
        r("ENCRYPTED LOCKS", self.stats['encrypted'], c.CRIMSON)
        print(f"   {c.CYAN}╚{'═' * (w-2)}╝{c.ENDC}")

    def log_proc(self, tag: str, msg: str, color: str):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"{self.color.DIM}{ts}{self.color.ENDC} {self.color.BOLD}{color}[{tag}]{self.color.ENDC:<18} {msg}")

    def run(self):
        os.system('clear' if os.name == 'posix' else 'cls')
        self.ui.print_banner()
        self.ui.draw_telemetry()
        
        stored = self._load_urls()
        targets = []
        
        if stored:
            print(f"\n {self.color.GOLD}📂 DETECTED ARCHIVE LEFTOVERS:{self.color.ENDC}")
            for i, (u, p) in enumerate(stored, 1):
                print(f"   {self.color.DIM}{i:02}.{self.color.ENDC} {self.color.SKY}{p:<8}{self.color.ENDC} ╾─╼ {u}")
            
            print(f"\n {self.color.NEON_P}▶{self.color.ENDC} {self.color.BOLD}ZENITH COMMAND CENTER:{self.color.ENDC}")
            print(f"   {self.color.DIM}[1]{self.color.ENDC} {self.color.BOLD}AUTO-BATCH{self.color.ENDC}   - Run all saved targets.")
            print(f"   {self.color.DIM}[2]{self.color.ENDC} {self.color.BOLD}SELECT-MODE{self.color.ENDC}  - Input indices (e.g., 1,3,4).")
            print(f"   {self.color.DIM}[3]{self.color.ENDC} {self.color.BOLD}MANUAL-LINK{self.color.ENDC}  - Enter new URLs.")
            
            choice = input(f"\n   {self.color.CYAN}╠═ Selection:{self.color.ENDC} ").strip()
            if choice == "1": targets = stored
            elif choice == "2":
                ids = input(f"   {self.color.CYAN}╚═ Indices:{self.color.ENDC} ").strip().split(',')
                try: targets = [stored[int(i)-1] for i in ids]
                except: choice = "3"
            else: choice = "3"
        else: choice = "3"

        if choice == "3":
            print(f"\n {self.color.NEON_P}▶{self.color.ENDC} {self.color.BOLD}UPLINK INJECTION (Empty line to start):{self.color.ENDC}")
            while True:
                u = input(f"   {self.color.CYAN}╠═ URL:{self.color.ENDC} ").strip()
                if not u: break
                targets.append((u, None))

        for u, p in targets:
            if not self.running: break
            self.parse_satellite(u, p)

if __name__ == "__main__":
    SatelliteScanner().run()
