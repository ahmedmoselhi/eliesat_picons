import os
import sys
import glob
import subprocess
import time
import json
import re
import csv
import logging
import random
from datetime import datetime
from collections import defaultdict
from wcwidth import wcswidth

# ======================================================================================
# 0. MUTE EXTERNAL LIBRARY DEBUG SPAM
# ======================================================================================
# Deep-translator, urllib3, and google-genai can output excessive debug information.
# We suppress all logs below ERROR level to keep the Terminal UI clean and prevent
# text from overwriting our drawn boxes.
logging.basicConfig(level=logging.ERROR)
logging.getLogger('urllib3').setLevel(logging.ERROR)
logging.disable(logging.INFO)
logging.disable(logging.DEBUG)

# ======================================================================================
# 1. READLINE & TAB-COMPLETION
# ======================================================================================
# We attempt to import readline to allow the user to use the TAB key when typing
# file paths in our custom input blocks. This works seamlessly on Unix systems.
try:
    import readline
    class HorizonPathCompleter:
        def complete(self, text, state):
            # Expand tilde (~) to the user's home directory
            if text.startswith('~'): text = os.path.expanduser(text)
            matches = glob.glob(text + '*')
            try:
                match = matches[state]
                # If the match is a directory, append a slash to continue navigation
                if os.path.isdir(match): return match + "/"
                return match
            except IndexError: return None
            
    readline.set_completer(HorizonPathCompleter().complete)
    readline.set_completer_delims(' \t\n=')
    
    # macOS specifically uses libedit instead of GNU readline, requiring a different bind command
    if 'libedit' in readline.__doc__: 
        readline.parse_and_bind("bind ^I rl_complete")
    else: 
        readline.parse_and_bind("tab: complete")
        
    # Bind UP and DOWN arrows to history search
    readline.parse_and_bind(r'"\033[A": history-search-backward')
    readline.parse_and_bind(r'"\033[B": history-search-forward')
except ImportError: 
    # Windows typically doesn't have readline installed by default, so we pass gracefully
    pass

# ======================================================================================
# 1.5 NATIVE TERMINAL INPUT HANDLER (KEYBOARD + MOUSE)
# ======================================================================================
class NativeTerminalReader:
    """Handles raw terminal input across OS platforms for interactive TUI.
    This bypasses standard buffered input to capture single keystrokes and mouse events."""
    def __init__(self):
        self.is_windows = os.name == 'nt'
        
    def get_char(self):
        """Reads a single character from the terminal stream without requiring the Enter key."""
        if self.is_windows:
            import msvcrt
            return msvcrt.getch().decode('utf-8', 'ignore')
        else:
            import tty, termios
            fd = sys.stdin.fileno()
            # Save the old terminal settings to restore them after grabbing the character
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(sys.stdin.fileno())
                ch = sys.stdin.read(1)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            return ch

    def get_event(self):
        """Reads a character or ANSI escape sequence (mouse clicks/arrows) and maps them to unified string commands."""
        c = self.get_char()
        if c == '\x1b':  # ESC sequence initiator
            c2 = self.get_char()
            if c2 == '[':
                c3 = self.get_char()
                if c3 == '<':  # SGR Mouse tracking sequence (\x1b[<b;x;yM)
                    seq = ""
                    # Read the rest of the mouse sequence until we hit the terminator (M or m)
                    while True:
                        char = self.get_char()
                        seq += char
                        if char in ('M', 'm'): break
                    parts = seq[:-1].split(';')
                    if len(parts) == 3 and seq.endswith('M'): # M = press, m = release
                        btn, x, y = int(parts[0]), int(parts[1]), int(parts[2])
                        # button 0 = left click, 64 = scroll up, 65 = scroll down
                        return ('mouse_click' if btn == 0 else f'mouse_scroll_{btn}', x, y)
                    return ('mouse_release', 0, 0)
                # Map standard ANSI arrow keys
                elif c3 == 'A': return ('up', 0, 0)
                elif c3 == 'B': return ('down', 0, 0)
                elif c3 == 'C': return ('right', 0, 0)
                elif c3 == 'D': return ('left', 0, 0)
            return ('esc', 0, 0)
        # Map single standard keystrokes to descriptive event strings
        elif c == '\x03': raise KeyboardInterrupt # Handle Ctrl+C gracefully
        elif c in ('\r', '\n'): return ('enter', 0, 0)
        elif c == 'q': return ('quit', 0, 0)
        elif c == ' ': return ('space', 0, 0)
        elif c == 'a': return ('add', 0, 0)
        elif c == 'r': return ('remove', 0, 0) # Trigger to delete/remove items
        elif c == 's': return ('sort', 0, 0)
        elif c == 'f': return ('search', 0, 0)
        elif c == 'c': return ('clear', 0, 0)
        elif c == 'n': return ('next', 0, 0)
        elif c == 'p': return ('prev', 0, 0)
        return (c, 0, 0)

term_reader = NativeTerminalReader()

class InputMode:
    """Safe context switcher for entering text queries while in a TUI session."""
    def __enter__(self):
        # Disable Mouse Tracking so it doesn't interfere with typing
        sys.stdout.write('\033[?1000l\033[?1006l')
        sys.stdout.flush()
        self.original_stdout = sys.stdout
        sys.stdout = sys.__stdout__
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self.original_stdout
        # Re-enable Mouse Tracking
        sys.stdout.write('\033[?1000h\033[?1006h')
        sys.stdout.flush()

# ======================================================================================
# 2. UI ENGINE (FULLY PARAMETERIZED & RTL-READY)
# ======================================================================================
class ObsidianUI:
    """
    ====================================================================================
    UI DRAWING ENGINE - PARAMETERIZATION & TUNING GUIDE
    ====================================================================================
    This engine dynamically calculates inner spacing to ensure perfect alignment.
    It takes terminal width, border characters, and ANSI color codes to construct boxes.
    """
    def __init__(self, width=120):
        # Master Configuration
        self.config = {
            "width": width,
            "padding_x": 3,
            "align": "left"
        }
        
        # Visual Theme Palette (ANSI Escape Codes)
        self.theme = {
            "border_v": "█", "border_h_top": "▀", "border_h_bot": "▄", "border_h_mid": "─",
            "c_main": "\033[96m",     # Cyan
            "c_accent": "\033[95m",   # Magenta
            "c_warn": "\033[93m",     # Gold
            "c_ok": "\033[92m",       # Green
            "c_err": "\033[91m",      # Red
            "c_bold": "\033[1m",      # Bold
            "c_inv": "\033[7m",       # Invert (Highlight)
            "c_rst": "\033[0m",       # Reset
            "icon_log": "📜", "icon_hint": "💡", "icon_exec": "🖥️", "icon_warn": "⚠️", 
            "icon_sat": "📡", "icon_stat": "📊", "icon_edit": "🛠️", "icon_sort": "🔃",
            "icon_net": "🌐", "icon_save": "💾", "icon_cat": "📂", "icon_time": "⏱️",
            "icon_trans": "🔄", "icon_batch": "📦", "icon_mouse": "🖱️"
        }
        self.W = self.config["width"]

    def _get_visual_len(self, text):
        """Calculates the visual length of a string by stripping ANSI codes and measuring character width."""
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        plain_text = ansi_escape.sub('', text)
        return wcswidth(plain_text)

    def fix_rtl(self, text):
        """
        Processes Arabic text for correct terminal rendering while PRESERVING ANSI sequences.
        Without this, Arabic characters render backwards in most standard terminals.
        """
        if not any("\u0600" <= c <= "\u06FF" for c in text): return text
        try:
            import arabic_reshaper
            from bidi.algorithm import get_display
            
            # Regex to safely isolate ANSI escape codes so they aren't mangled by the reshaper
            ansi_escape = re.compile(r'(\033\[[0-9;]*[a-zA-Z])')
            parts = ansi_escape.split(text)
            
            result = ""
            for part in parts:
                if ansi_escape.match(part):
                    result += part
                else:
                    # Apply reshape and bidi ONLY to raw text content
                    reshaped = arabic_reshaper.reshape(part)
                    result += get_display(reshaped)
            return result
        except: 
            return text

    def draw_master_header(self):
        """Clears the screen and draws the primary application title."""
        os.system('cls' if os.name == 'nt' else 'clear')
        t = self.theme
        print(f"{t['c_accent']}{t['border_v']}{t['border_h_top'] * (self.W-2)}{t['border_v']}{t['c_rst']}")
        # VERSION UPDATED TO 14.0
        title = "O B S I D I A N    H O R I Z O N    v 1 4 . 0"
        sub = "MULTI-SATELLITE BATCH PROCESSING | INTERACTIVE TUI EDITOR"
        t_pad = (self.W - 2 - len(title)) // 2
        s_pad = (self.W - 2 - len(sub)) // 2
        print(f"{t['c_accent']}{t['border_v']}{t['c_rst']}{' ' * t_pad}{t['c_bold']}{title}{t['c_rst']}{' ' * (self.W - 2 - t_pad - len(title))}{t['c_accent']}{t['border_v']}{t['c_rst']}")
        print(f"{t['c_accent']}{t['border_v']}{t['c_rst']}{' ' * s_pad}{sub}{' ' * (self.W - 2 - s_pad - len(sub))}{t['c_accent']}{t['border_v']}{t['c_rst']}")
        print(f"{t['c_accent']}{t['border_v']}{t['border_h_bot'] * (self.W-2)}{t['border_v']}{t['c_rst']}")

    def draw_solid_box(self, title, rows, color=None, icon=None, manual_offset=0):
        """Draws a bordered container to display informational lists or logs."""
        t = self.theme
        c = color if color else t['c_main']
        icn = icon if icon else t['icon_log']
        pad = " " * self.config["padding_x"]
        inner_w = self.W - 2 - (self.config["padding_x"] * 2)
        
        print(f"\n{c}{t['border_v']}{t['border_h_top'] * (self.W-2)}{t['border_v']}{t['c_rst']}")
        
        # Calculate centering for the header row
        raw_header = f"{icn} {title} {icn}"
        visual_header_w = self._get_visual_len(raw_header)
        h_space = ((inner_w - visual_header_w) // 2) + manual_offset
        header_content = f"{t['c_bold']}{raw_header}{t['c_rst']}"
        left_filler = " " * h_space
        right_filler = " " * (inner_w - h_space - visual_header_w)
        
        print(f"{c}{t['border_v']}{t['c_rst']}{pad}{left_filler}{header_content}{right_filler}{pad}{c}{t['border_v']}{t['c_rst']}")
        print(f"{c}{t['border_v']}{t['border_h_mid'] * (self.W-2)}{t['border_v']}{t['c_rst']}")
        
        # Print each row, padding it to fit the box width
        for row in rows:
            row_fixed = self.fix_rtl(row)
            v_len = self._get_visual_len(row_fixed)
            padding = max(0, inner_w - v_len)
            print(f"{c}{t['border_v']}{t['c_rst']}{pad}{row_fixed}{' ' * padding}{pad}{c}{t['border_v']}{t['c_rst']}")
            
        print(f"{c}{t['border_v']}{t['border_h_bot'] * (self.W-2)}{t['border_v']}{t['c_rst']}")

    def draw_input_block(self, label, helper_text="", color=None, label_offset=0):
        """Draws a standardized input prompt box that captures user typed string input."""
        import textwrap
        t = self.theme
        c = color if color else t['c_warn']
        
        # Top Header calculation
        label_vis_len = self._get_visual_len(label)
        remaining_border = self.W - label_vis_len - 5 + label_offset
        print(f"\n{c}{t['border_v']}{t['border_h_top']} {t['c_bold']}{label}{t['c_rst']} "
              f"{c}{t['border_h_top'] * max(0, remaining_border)}{t['border_v']}{t['c_rst']}")

        # Helper/Hint Section (Wraps long text automatically)
        if helper_text:
            prefix = f" {t['icon_hint']} {t['c_accent']}HINT:{t['c_rst']} "
            prefix_len = self._get_visual_len(prefix)
            wrap_width = (self.W - 2) - prefix_len - 1
            wrapped_lines = textwrap.wrap(helper_text, width=wrap_width)

            for i, line in enumerate(wrapped_lines):
                current_prefix = prefix if i == 0 else " " * prefix_len
                v_len = self._get_visual_len(line)
                h_padding = (self.W - 2) - prefix_len - v_len
                print(f"{c}{t['border_v']}{t['c_rst']}{current_prefix}{line}"
                      f"{' ' * h_padding}{c}{t['border_v']}{t['c_rst']}")
            print(f"{c}{t['border_v']}{t['border_h_mid'] * (self.W-2)}{t['border_v']}{t['c_rst']}")

        prompt_prefix = f" {t['icon_exec']}   {t['c_bold']}USER_EXEC >{t['c_rst']} "
        print(f"{c}{t['border_v']}{t['c_rst']}{prompt_prefix}", end="", flush=True)

        # Disconnect logger momentarily so typing feels native
        original_stdout = sys.stdout
        sys.stdout = sys.__stdout__
        try:
            val = input().strip()
        except KeyboardInterrupt:
            # Ensuring graceful terminal state restoration on Ctrl+C during typing
            sys.stdout.write('\033[?1000l\033[?1006l')
            sys.stdout.flush()
            print(f"\n\n{t['c_err']} OPERATION CANCELLED BY USER (CTRL+C) {t['c_rst']}")
            sys.exit(0)
        finally:
            sys.stdout = original_stdout

        print(f"{c}{t['border_v']}{t['border_h_bot'] * (self.W-2)}{t['border_v']}{t['c_rst']}")
        return val

    def draw_category_selector(self, cat_counts, selected_cats, order, col_width=30, label_offset=0):
        """Draws the main category inclusion/exclusion interface."""
        t = self.theme
        c = t['c_main']
        
        print(f"\n{c}{t['border_v']}{t['border_h_top'] * (self.W-2)}{t['border_v']}{t['c_rst']}")
        
        title = "📂 CATEGORY FILTER MODULE & BOUQUET BUILDER"
        title_v_len = self._get_visual_len(title)
        inner_w = self.W - 2
        h_space = ((inner_w - title_v_len) // 2) + label_offset
        r_filler = " " * (inner_w - h_space - title_v_len)
        print(f"{c}{t['border_v']}{t['c_rst']}{' ' * h_space}{t['c_bold']}{title}{t['c_rst']}{r_filler}{c}{t['border_v']}{t['c_rst']}")
        print(f"{c}{t['border_v']}{t['border_h_mid'] * (self.W-2)}{t['border_v']}{t['c_rst']}")
        
        helper = "Toggle/Edit categories. Press [ENTER] to process final translation."
        h_prefix = f" {t['icon_hint']} "
        h_prefix_len = self._get_visual_len(h_prefix)
        h_v_len = self._get_visual_len(helper)
        h_padding = inner_w - h_prefix_len - h_v_len
        print(f"{c}{t['border_v']}{t['c_rst']}{h_prefix}{helper}{' ' * max(0, h_padding)}{c}{t['border_v']}{t['c_rst']}")
        print(f"{c}{t['border_v']}{t['border_h_mid'] * (self.W-2)}{t['border_v']}{t['c_rst']}")
        
        # Render each category found in the dictionary
        display_list = [cat for cat in order if cat in cat_counts]
        for i, cat in enumerate(display_list, 1):
            count = cat_counts[cat]
            if cat in selected_cats:
                status = f"{t['c_ok']}✅ INCLUDED ({count}){t['c_rst']}"
            else:
                status = f"{t['c_err']}❌ IGNORED{t['c_rst']}"
            
            idx_str = f" {str(i).rjust(2)}. "
            cat_fixed = self.fix_rtl(cat)
            cat_v_len = self._get_visual_len(cat_fixed)
            cat_col_padding = " " * max(1, (col_width - cat_v_len))
            
            row_content = f"{idx_str}{cat_fixed}{cat_col_padding}{status}"
            row_v_len = self._get_visual_len(row_content)
            final_padding = " " * max(0, (inner_w - row_v_len))
            
            print(f"{c}{t['border_v']}{t['c_rst']}{row_content}{final_padding}{c}{t['border_v']}{t['c_rst']}")
            
        print(f"{c}{t['border_v']}{t['border_h_bot'] * (self.W-2)}{t['border_v']}{t['c_rst']}")
        return display_list

UI = ObsidianUI()
UI.draw_master_header()

# Gather Initial Variables
DB_PATH = UI.draw_input_block("DATABASE SOURCE", "Provide the full path to your lamedb file.You can use TAB to autocomplete file names in your current directory.") or "lamedb"
WRITE_MODE = UI.draw_input_block("WRITE MODE", "Decide if you want to overwrite your source file ('y') or create a safe copy named 'lamedb.translated' ('n').").lower() == "y"
ENABLE_TRANSLATION = UI.draw_input_block("ENABLE TRANSLATION", "Enable AI and Dictionary translation procedures? ('y' to enable, 'n' to bypass translation and only sort/build bouquets).").lower() == "y"

def fetch_api_key():
    """Attempts to retrieve the Google GenAI API key from file, or asks the user via TUI."""
    key_file = "api_key.txt"
    if os.path.exists(key_file):
        try:
            with open(key_file, "r", encoding="utf-8") as f:
                k = f.read().strip()
                if len(k) >= 30: return k
        except Exception as e:
            UI.draw_solid_box("SYSTEM ERROR", [f"Could not read {key_file}: {str(e)}"], color=UI.theme['c_err'])

    k = UI.draw_input_block(
        "GEMINI API KEY", 
        "API Key not found or invalid in api_key.txt. Enter your Google AI Studio API Key. "
        "Leave empty to use local dictionary mode only."
    ).strip()

    if k:
        try:
            with open(key_file, "w", encoding="utf-8") as f:
                f.write(k)
            UI.draw_solid_box("SUCCESS", ["API Key saved to api_key.txt"], color=UI.theme['c_ok'])
        except Exception as e:
            UI.draw_solid_box("STORAGE ERROR", [f"Failed to save key: {str(e)}"], color=UI.theme['c_err'])
    return k

# ======================================================================================
# 3. LIVE LOGGER (LOGGER TAB FIX & RTL SUPPORT)
# ======================================================================================
class LiveLogger:
    """Intercepts sys.stdout to save a plain-text log file of the session,
    while simultaneously pushing visually corrected (RTL/ANSI) text to the terminal screen."""
    def __init__(self, filename="session_execution.log"):
        self.filename = filename
        self.logfile = open(filename, "w", encoding="utf-8")
        self.terminal = sys.stdout
        self.tab_fix_pattern = re.compile(r'\t|\x08|\r') 

    def write(self, message):
        fixed_msg = UI.fix_rtl(message)
        # Strip ANSI codes for the plain text log file
        clean_msg = re.sub(r'\033\[[0-9;]*[a-zA-Z]', '', message)
        clean_msg = self.tab_fix_pattern.sub('    ', clean_msg)
        self.terminal.write(fixed_msg)
        self.logfile.write(clean_msg)
        self.logfile.flush()

    def flush(self): 
        self.terminal.flush()
        self.logfile.flush()

current_logger = LiveLogger()
sys.stdout = current_logger

# ======================================================================================
# 4. NEURAL MODULE INITIALIZATION
# ======================================================================================
def initialize_quantum_env():
    """Validates and automatically installs missing required python packages using pip."""
    print(f"\n{UI.theme['c_main']}{UI.theme['icon_net']} [SYSTEM] Synchronizing Translation & Bidi Modules...{UI.theme['c_rst']}")
    for pkg in ["deep-translator", "arabic-reshaper", "python-bidi", "tabulate", "google-genai"]:
        try: 
            if pkg == "deep-translator": import deep_translator
            elif pkg == "google-genai": import google.genai
            else: __import__(pkg.replace("-", "_"))
        except ImportError: 
            print(f"{UI.theme['c_warn']}[!] Missing {pkg}. Installing via pip...{UI.theme['c_rst']}")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "--break-system-packages"])

initialize_quantum_env()

from deep_translator import GoogleTranslator
from tabulate import tabulate
from google import genai
from google.genai import types
from google.genai.errors import APIError

# ======================================================================================
# 5. CORE LOGIC ENGINE (BATCH PROCESSING, TUI & STATE PERSISTENCE)
# ======================================================================================
class HorizonCore:
    def __init__(self, api_key=None, enable_translation=True):
        self.ui = UI
        self.t = UI.theme
        self.stats = defaultdict(int)
        self.mapping_export = []
        self.used_corrections = set()
        self.neural_enabled = True
        self.enable_translation = enable_translation
        self.BATCH_SIZE = 40  
        self.api_key = api_key
        
        # MULTI-MODEL FALLBACK ENGINE
        # The script iterates through these if rate limits (429) are hit.
        self.models_available = [
            "gemini-3.6-flash",
            "gemini-3.5-flash",
            "gemini-3.5-flash-lite",
            "gemini-3.1-flash-lite",
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            "gemini-3-flash",
            "gemini-2.5-pro"
        ]
        self.active_model_idx = 0
        
        if not self.enable_translation or not self.api_key:
            self.neural_enabled = False
        else:
            try:
                from google import genai
                self.gemini_client = genai.Client(api_key=self.api_key)
                self._init_gemini_model()
            except Exception as e:
                self.neural_enabled = False
                print(f"{self.t['c_err']}AI Initialization failed: {e}{self.t['c_rst']}")

        self.translator = GoogleTranslator(source='en', target='ar')
        # Bypass translation if these words exist to preserve technical channel names
        self.BYPASS_WORDS = ["SID", "DATA", "SERVICE", "TEST", "OTA", "PROMO", "SPARE", "RESERVED"]
        self.corrections = self._load_json_corrections()
        self.sat_mapping = self._load_sat_mapping()
        
        # EXTANDED CATEGORIES - Base groupings for bouquet creation
        self.CATEGORY_ORDER = [
            "إسلامي",
            "مسيحي",
            "القنوات المصرية",
            "افلام ومسلسلات",
            "رياضة",
            "اخبار",
            "موسيقى",
            "وثائقيات",
            "أطفال",
            "مطبخ",
            "عام",
        ]
        # Pattern mapping to auto-assign categories based on the raw channel name
        self.CATEGORY_MAP = {
            "quran": "ISLAMIC", "islam": "ISLAMIC", "majd": "ISLAMIC", "azhari": "ISLAMIC", "kareem": "ISLAMIC",
            "aghapy": "CHRISTIAN", "sat 7": "CHRISTIAN", "nour sat": "CHRISTIAN",
            "egypt": "EGYPTIAN", "masr": "EGYPTIAN", "cairo": "EGYPTIAN", "nile": "EGYPTIAN", "ertu": "EGYPTIAN", "مصرية": "EGYPTIAN",
            "cinema": "MOVIES & SERIES", "movie": "MOVIES & SERIES", "film": "MOVIES & SERIES", "aflam": "MOVIES & SERIES",
            "drama": "MOVIES & SERIES", "series": "MOVIES & SERIES",
            "sport": "SPORTS", "sports": "SPORTS", "bein": "SPORTS", "kass": "SPORTS", "ssc": "SPORTS", "koora": "SPORTS",
            "news": "NEWS", "al arabiya": "NEWS", "bbc": "NEWS", "cnn": "NEWS", "akhbar": "NEWS", "hadath": "NEWS", "aljazeera": "NEWS",
            "music": "MUSIC & RADIO", "fm": "MUSIC & RADIO", "radio": "MUSIC & RADIO", "iza'at": "MUSIC & RADIO",
            "doc": "DOCUMENTARY", "nat geo": "DOCUMENTARY", "discovery": "DOCUMENTARY", "history": "DOCUMENTARY", "وثائقية": "DOCUMENTARY",
            "kids": "KIDS", "spacetoon": "KIDS",
            "food": "COOKING", "cook": "COOKING", "sofra": "COOKING", "chef": "COOKING", "fatafeat": "COOKING", "طبخ": "COOKING"
        }

    def _init_gemini_model(self):
        """Initializes or swaps the target Gemini model."""
        self.target_model = self.models_available[self.active_model_idx]
        print(f"\n{self.t['c_ok']}{self.t['icon_exec']} [AI SUBSYSTEM] Targeting Model Instance: {self.target_model}{self.t['c_rst']}")

    def _load_json_corrections(self):
        """Loads manual user overrides from a local corrections.json file to bypass AI translation."""
        path = "corrections.json"
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    print(f"{self.t['c_ok']}{self.t['icon_save']} [STORAGE] Loaded {len(data)} entries from corrections.json.{self.t['c_rst']}")
                    return {" ".join(str(k).split()).lower(): " ".join(str(v).split()) for k, v in data.items()}
            except: pass
        return {}

    def _load_sat_mapping(self):
        """Loads a mapping CSV to translate raw orbital degrees into human readable satellite names."""
        mapping = {}
        path = "mapping.csv"
        if os.path.exists(path):
            try:
                with open(path, mode='r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    for row in reader:
                        if len(row) >= 2:
                            name, position = row[0].strip(), row[1].strip().upper()
                            mapping[position] = name
            except Exception as e:
                print(f"{self.t['c_warn']}[!] Mapping Error: {e}{self.t['c_rst']}")
        return mapping

    def load_sat_config(self, mask):
        """Loads persisted states (custom sorting, overrides) specific to the selected satellite."""
        config_file = "sat_configs.json"
        if os.path.exists(config_file):
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get(mask, {})
            except: pass
        return {}

    def save_sat_config(self, mask, selected_cats, all_services):
        """Saves current state (sorting, category changes) so it persists on future runs."""
        config_file = "sat_configs.json"
        data = {}
        if os.path.exists(config_file):
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except: pass
        
        sat_data = {
            "selected_cats": list(selected_cats),
            "cat_overrides": {s['sid']: s['cat'] for s in all_services if s['cat'] != self.get_arabic_category_name(self.get_category(s['clean']))},
            "custom_orders": {s['sid']: s['order'] for s in all_services}
        }
        data[mask] = sat_data
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def _repair_json(self, raw_text):
        """Failsafe to parse JSON objects even if the LLM output contains trailing markdown or garbage data."""
        try:
            start = raw_text.find('{')
            end = raw_text.rfind('}')
            if start == -1: return None
            json_str = raw_text[start:end+1]
            while json_str.count('{') > json_str.count('}'): json_str += "}"
            return json.loads(json_str)
        except:
            pairs = re.findall(r'"([^"]+)":\s*"([^"]+)"', raw_text)
            return {k: v for k, v in pairs} if pairs else None

    def get_category(self, name):
        """Determines the English category of a channel based on regex mapping rules."""
        low_name = name.lower()
        for kw, cat in self.CATEGORY_MAP.items():
            if kw in low_name: return cat
        return "GENERAL"

    def get_arabic_category_name(self, eng_cat):
        """Translates internal English category tags into the final Arabic bouquet strings."""
        mapping = {
            "ISLAMIC": "إسلامي",
            "CHRISTIAN": "مسيحي",
            "EGYPTIAN": "القنوات المصرية",
            "MOVIES & SERIES": "افلام ومسلسلات",
            "SPORTS": "رياضة",
            "NEWS": "اخبار",
            "MUSIC & RADIO": "موسيقى",
            "DOCUMENTARY": "وثائقيات",
            "KIDS": "أطفال",
            "COOKING": "مطبخ",
            "GENERAL": "عام",
        }
        return mapping.get(eng_cat, "عام")

    def _clean_tags(self, name):
        """Strips resolutions and technical flags (HD, FHD, 4K) from channel names to improve AI translation accuracy."""
        tags = []
        pattern = re.compile(r'\s*([\(\[]?\s*\b(HD|SD|4K|UHD|FHD|TEST|PROMO|SERVICE|DATA|OTA)\b\s*[\)\]]?)\s*', re.I)
        def tag_extractor(match): tags.append(match.group(1).strip()); return ' '
        clean = pattern.sub(tag_extractor, name).strip()
        return clean, tags

    def batch_translate_gemini(self, names_to_translate):
        """Sends a batched payload of channels to the Gemini API for fast, context-aware Arabic translation."""
        if not self.api_key or not names_to_translate: return {}, 0
        prompt = (
            "Act as a professional DVB satellite channel translator. "
            "Translate the following service names into natural Arabic. "
            "Return ONLY a JSON object where keys are original names and values are Arabic translations.\n\n"
            f"Names: {json.dumps(names_to_translate)}"
        )
        max_retries = 8
        base_delay = 5 
        for attempt in range(max_retries):
            try:
                start_t = time.time()
                response = self.gemini_client.models.generate_content(
                    model=self.target_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                    )
                )
                lat = round(time.time() - start_t, 2)
                raw_response = response.text.strip()
                data = self._repair_json(raw_response)
                if data: return data, lat
            except APIError as e:
                # Handle Rate Limits (429) by hot-swapping to a lower-tier Gemini model dynamically
                if getattr(e, 'code', None) == 429 or "429" in str(e) or "quota" in str(e).lower():
                    self.active_model_idx = (self.active_model_idx + 1) % len(self.models_available)
                    self._init_gemini_model()
                    print(f"{self.t['c_warn']}[!] Quota Exceeded. Hot-swapping to: {self.target_model}{self.t['c_rst']}")
                    time.sleep(base_delay + random.uniform(1, 3))
                    continue
                else:
                    print(f"{self.t['c_err']}[GEMINI_API_ERROR] Attempt {attempt+1} failed: {str(e)}{self.t['c_rst']}")
                    time.sleep(5)
                    continue
            except Exception as e:
                print(f"{self.t['c_err']}[GEMINI_ERROR] Attempt {attempt+1} failed: {str(e)}{self.t['c_rst']}")
                time.sleep(5)
                continue
        return {}, 0

    def get_satellites(self, lines):
        """Parses Enigma2 lamedb lines to identify all satellite positions embedded in the database."""
        masks = defaultdict(lambda: {"pos": 0, "human": "", "full_name": ""}); cur_ns = None
        for line in lines:
            line = line.strip()
            if ":" in line and line.count(":") == 2 and not any(line.startswith(x) for x in ["s", "/", "e"]): 
                cur_ns = line.split(":")[0].lower()
            if line.startswith("s ") and cur_ns:
                p = line[2:].split(":")
                if len(p) >= 5:
                    orb = int(p[4]); m = cur_ns[:4]
                    if m not in masks:
                        deg = abs(orb) / 10.0
                        lookup_key = f"{deg:.1f}{'W' if orb < 0 else 'E'}"
                        fallback_str = f"{deg}°{'W' if orb < 0 else 'E'}"
                        full_name = self.sat_mapping.get(lookup_key, fallback_str)
                        masks[m] = {"pos": orb, "human": lookup_key, "full_name": full_name}
        return sorted([{"mask": k, "name": v["human"], "full_name": v["full_name"], "val": v["pos"]} for k, v in masks.items()], key=lambda x: x['val'])

    def format_bouquet_reference(self, sid_line, fallback_type=1):
        """Converts raw Lamedb SIDs into the Enigma2 specific `#SERVICE 1:0...` bouquet format."""
        parts = sid_line.split(':')
        if len(parts) >= 5:
            try:
                s_hex = f"{int(parts[0], 16):X}"
                ns_hex = f"{int(parts[1], 16):X}"
                ts_hex = f"{int(parts[2], 16):X}"
                on_hex = f"{int(parts[3], 16):X}"
                t_hex = f"{int(parts[4], 10):X}" 
                return f"1:0:{t_hex}:{s_hex}:{ts_hex}:{on_hex}:{ns_hex}:0:0:0"
            except ValueError: pass
        s_hex = f"{int(parts[0], 16):X}" if len(parts) > 0 and parts[0] else "0"
        ns_hex = f"{int(parts[1], 16):X}" if len(parts) > 1 and parts[1] else "0"
        return f"1:0:{fallback_type:X}:{s_hex}:0:0:{ns_hex}:0:0:0"

    def _tui_add_from_general(self, category_name, target_list, general_pool):
        """SUB-TUI: Navigates the global general pool to stage and add elements to active category."""
        page_size = 15
        current_page = 0
        selected_idx = 0
        staged_for_add = set() # Stores SIDs to prevent index shifting issues
        search_query = ""
        
        while True:
            # Apply search filter
            filtered_pool = [s for s in general_pool if not search_query or search_query.lower() in s['raw'].lower() or search_query.lower() in s.get('tx', '').lower()]
            
            # Ensure selected_idx stays in bounds after search filtering
            if filtered_pool:
                selected_idx = min(selected_idx, len(filtered_pool) - 1)
            else:
                selected_idx = 0
                
            total_pages = (len(filtered_pool) + page_size - 1) // page_size if filtered_pool else 1
            current_page = max(0, min(current_page, total_pages - 1))
            start = current_page * page_size
            end = start + page_size
            page_items = filtered_pool[start:end]
            
            os.system('cls' if os.name == 'nt' else 'clear')
            print("\n")
            
            self.ui.draw_solid_box(f"GLOBAL ADD TO {category_name} (Pg {current_page+1}/{total_pages})", [
                f"{self.t['icon_mouse']} {self.t['c_accent']}MOUSE: Scroll to navigate.{self.t['c_rst']}",
                f"⌨️  {self.t['c_warn']}KEYS: [Up/Down] Navigate | [Space] Toggle Select | [Enter] Confirm Add | [Q/Esc] Cancel{self.t['c_rst']}",
                self.t['border_h_mid'] * (self.ui.W - 6)
            ], color=self.t['c_ok'], icon=self.t['icon_cat'])
            
            list_base_y = 9
            for i, s in enumerate(page_items):
                abs_idx = start + i
                pointer = "►" if abs_idx == selected_idx else " "
                sid = s['sid']
                if sid in staged_for_add:
                    row_color = self.t['c_ok'] + self.t['c_inv'] 
                    chk = "[X]"
                elif abs_idx == selected_idx:
                    row_color = self.t['c_inv'] 
                    chk = "[ ]"
                else:
                    row_color = self.t['c_rst']
                    chk = "[ ]"
                print(f"   {pointer} {row_color} {chk} {str(abs_idx+1).rjust(3)}. {s['raw'][:40].ljust(40)} | SID: {sid.split(':')[0]} {self.t['c_rst']}")
            
            # Interactive Footer UI
            footer_text = f"   [< PREV ]    [ NEXT >]    [ SEARCH ]    [ CLEAR ]    Query: '{search_query}'"
            print(f"\n{self.t['c_main']}{footer_text}{self.t['c_rst']}")
            footer_y = list_base_y + len(page_items) + 1
            
            print(f"\n{self.t['c_main']}{self.t['border_v']} Waiting for Event...{self.t['c_rst']}")
            event, mx, my = term_reader.get_event()
            
            # Mouse click mapping for footer boundaries
            if event == 'mouse_click' and my == footer_y:
                if 3 <= mx <= 12: event = 'prev'
                elif 16 <= mx <= 25: event = 'next'
                elif 29 <= mx <= 39: event = 'search'
                elif 43 <= mx <= 52: event = 'clear'
            
            # Key/Event Routing
            if event in ('quit', 'esc', 'q'): 
                break
            elif event == 'enter':
                current_max_order = max([s['order'] for s in target_list]) if target_list else 0
                items_to_add = [s for s in general_pool if s['sid'] in staged_for_add]
                for item in items_to_add:
                    general_pool.remove(item)
                    item['cat'] = category_name
                    current_max_order += 1
                    item['order'] = current_max_order
                    target_list.append(item)
                break
            elif event in ('up', 'left', 'prev'):
                if event == 'up':
                    selected_idx = max(0, selected_idx - 1)
                    if selected_idx < start: current_page -= 1
                else:
                    current_page = max(0, current_page - 1)
                    selected_idx = current_page * page_size
            elif event in ('down', 'right', 'next'):
                if event == 'down':
                    selected_idx = min(len(filtered_pool) - 1, selected_idx + 1)
                    if selected_idx >= end: current_page += 1
                else:
                    current_page = min(total_pages - 1, current_page + 1)
                    selected_idx = current_page * page_size
            elif event == 'space':
                if filtered_pool and selected_idx < len(filtered_pool):
                    sid = filtered_pool[selected_idx]['sid']
                    if sid in staged_for_add: staged_for_add.remove(sid)
                    else: staged_for_add.add(sid)
            elif event == 'search':
                with InputMode():
                    search_query = input("\nSearch Query: ").strip()
                current_page = 0
                selected_idx = 0
            elif event == 'clear':
                search_query = ""
                current_page = 0
                selected_idx = 0
            elif event == 'mouse_scroll_64': 
                current_page = max(0, current_page - 1); selected_idx = current_page * page_size
            elif event == 'mouse_scroll_65': 
                current_page = min(total_pages - 1, current_page + 1); selected_idx = current_page * page_size

    def manage_category_contents(self, category_name, all_services):
        """Primary TUI for sorting, modifying, and viewing specific categories."""
        target_list = sorted([s for s in all_services if s['cat'] == category_name], key=lambda x: x['order'])
        general_pool = [s for s in all_services if s['cat'] == "عام" and category_name != "عام"]
        
        page_size = 15
        current_page = 0
        selected_idx = 0
        staged_for_move = set() # Multi-select SIDs
        search_query = ""
        
        # Engage Mouse Tracking codes
        sys.stdout.write('\033[?1000h\033[?1006h')
        sys.stdout.flush()

        try:
            while True:
                # Apply filter to view
                filtered_list = [s for s in target_list if not search_query or search_query.lower() in s['raw'].lower() or search_query.lower() in s.get('tx', '').lower()]
                
                # Dynamic out-of-bounds protection for index after filtering/removing
                if filtered_list:
                    selected_idx = min(selected_idx, len(filtered_list) - 1)
                else:
                    selected_idx = 0
                    
                total_pages = (len(filtered_list) + page_size - 1) // page_size if filtered_list else 1
                current_page = max(0, min(current_page, total_pages - 1))
                start = current_page * page_size
                end = start + page_size
                page_items = filtered_list[start:end]
                
                os.system('cls' if os.name == 'nt' else 'clear')
                print("\n")
                
                self.ui.draw_solid_box(f"INTERACTIVE TUI: {category_name} (Pg {current_page+1}/{total_pages})", [
                    f"{self.t['icon_mouse']} {self.t['c_accent']}MOUSE: Click to Select. Use Footer buttons for Nav/Search.{self.t['c_rst']}",
                    f"⌨️  {self.t['c_warn']}KEYS: [Up/Down] Navigate | [Space] Toggle Multi-Select | [Enter] Move Selected Here{self.t['c_rst']}",
                    f"⌨️  {self.t['c_warn']}      [A] Add from Global | [R]emove | [S]ort | [Q/Esc] Back{self.t['c_rst']}",
                    self.t['border_h_mid'] * (self.ui.W - 6)
                ], color=self.t['c_main'], icon=self.t['icon_edit'])
                
                list_base_y = 10
                for i, s in enumerate(page_items):
                    abs_idx = start + i
                    pointer = "►" if abs_idx == selected_idx else " "
                    sid = s['sid']
                    
                    if sid in staged_for_move:
                        row_color = self.t['c_warn'] + self.t['c_inv'] 
                        chk = "[X]"
                    elif abs_idx == selected_idx:
                        row_color = self.t['c_inv'] 
                        chk = "[ ]"
                    else:
                        row_color = self.t['c_rst']
                        chk = "[ ]"
                        
                    print(f"   {pointer} {row_color} {chk} {str(abs_idx+1).rjust(3)}. {s['raw'][:40].ljust(40)} | SID: {sid.split(':')[0]} {self.t['c_rst']}")
                
                # Interactive Footer UI
                footer_text = f"   [< PREV ]    [ NEXT >]    [ SEARCH ]    [ CLEAR ]    Query: '{search_query}'"
                print(f"\n{self.t['c_main']}{footer_text}{self.t['c_rst']}")
                footer_y = list_base_y + len(page_items) + 1
                
                print(f"\n{self.t['c_main']}{self.t['border_v']} Waiting for Event...{self.t['c_rst']}")
                event, mx, my = term_reader.get_event()
                
                # Footer Mouse mappings
                if event == 'mouse_click' and my == footer_y:
                    if 3 <= mx <= 12: event = 'prev'
                    elif 16 <= mx <= 25: event = 'next'
                    elif 29 <= mx <= 39: event = 'search'
                    elif 43 <= mx <= 52: event = 'clear'
                
                # Input Routing
                if event in ('quit', 'esc', 'q'): 
                    break
                elif event in ('up', 'left', 'prev'):
                    if event == 'up':
                        selected_idx = max(0, selected_idx - 1)
                        if selected_idx < start: current_page -= 1
                    else:
                        current_page = max(0, current_page - 1)
                        selected_idx = current_page * page_size
                elif event in ('down', 'right', 'next'):
                    if event == 'down':
                        selected_idx = min(len(filtered_list) - 1, selected_idx + 1)
                        if selected_idx >= end: current_page += 1
                    else:
                        current_page = min(total_pages - 1, current_page + 1)
                        selected_idx = current_page * page_size
                elif event == 'space':
                    if filtered_list and selected_idx < len(filtered_list):
                        sid = filtered_list[selected_idx]['sid']
                        if sid in staged_for_move: staged_for_move.remove(sid)
                        else: staged_for_move.add(sid)
                elif event == 'enter':
                    if staged_for_move and filtered_list:
                        target_sid = filtered_list[selected_idx]['sid']
                        items_to_move = [s for s in target_list if s['sid'] in staged_for_move]
                        target_list = [s for s in target_list if s['sid'] not in staged_for_move]
                        
                        target_pos_new = next((i for i, s in enumerate(target_list) if s['sid'] == target_sid), len(target_list))
                        
                        for item in reversed(items_to_move):
                            target_list.insert(target_pos_new, item)
                            
                        for idx_re, s in enumerate(target_list): s['order'] = idx_re
                        staged_for_move.clear()
                elif event == 'remove':
                    # Removes item from category and drops it back into "عام" (Global)
                    if staged_for_move:
                        items_to_remove = [s for s in target_list if s['sid'] in staged_for_move]
                        for item in items_to_remove:
                            target_list.remove(item)
                            item['cat'] = "عام"
                            item['order'] = 9999
                            general_pool.append(item)
                        staged_for_move.clear()
                    elif filtered_list and selected_idx < len(filtered_list):
                        item = filtered_list[selected_idx]
                        target_list.remove(item)
                        item['cat'] = "عام"
                        item['order'] = 9999
                        general_pool.append(item)
                    
                    # Reorder remaining to close integer gaps
                    for idx_re, s in enumerate(target_list): s['order'] = idx_re
                elif event == 'add':
                    self._tui_add_from_general(category_name, target_list, general_pool)
                    for idx_re, s in enumerate(target_list): s['order'] = idx_re
                    search_query = ""
                elif event == 'search':
                    with InputMode(): 
                        search_query = input("\nSearch Query: ").strip()
                    current_page = 0
                    selected_idx = 0
                elif event == 'clear':
                    search_query = ""
                    current_page = 0
                    selected_idx = 0
                elif event == 'mouse_click':
                    clicked_rel_y = my - list_base_y
                    if 0 <= clicked_rel_y < len(page_items):
                        clicked_abs_idx = start + clicked_rel_y
                        selected_idx = clicked_abs_idx
                elif event == 'mouse_scroll_64': 
                    current_page = max(0, current_page - 1)
                    selected_idx = current_page * page_size
                elif event == 'mouse_scroll_65': 
                    current_page = min(total_pages - 1, current_page + 1)
                    selected_idx = current_page * page_size
                elif event == 'sort':
                    target_list.sort(key=lambda x: x['raw'].lower())
                    for idx_re, s in enumerate(target_list): s['order'] = idx_re
                    selected_idx = 0
                    current_page = 0
        finally:
            # ALWAYS terminate mouse tracking cleanly on exit
            sys.stdout.write('\033[?1000l\033[?1006l')
            sys.stdout.flush()

    def run(self, path, ovr):
        """Main execution sequence linking Parsing -> Editor -> Translation -> Saving."""
        if not os.path.exists(path): 
            print(f"{self.t['c_err']}ERROR: Database not found at {path}{self.t['c_rst']}")
            return
        
        with open(path, "r", encoding="utf-8", errors="ignore") as f: lines = f.readlines()
        sats = self.get_satellites(lines)
        
        rows = [f"{str(i).rjust(2)}: {s['full_name'].ljust(35)} | MASK: {s['mask'].upper()}xxxx" for i, s in enumerate(sats, 1)]
        UI.draw_solid_box("ORBITAL COORDINATOR", rows, color=self.t['c_accent'], icon=self.t['icon_sat'])
        idx_in = UI.draw_input_block("SATELLITE SELECTION", "Select numbers comma-separated (e.g. 1, 3, 4) to process individually, or press [ENTER] to process everything as one unified bouquet.")
        
        target_sats = []
        if idx_in.strip():
            parts = idx_in.split(',')
            for p in parts:
                p = p.strip()
                if p.isdigit() and 0 < int(p) <= len(sats):
                    target_sats.append(sats[int(p)-1])
                    
        if not target_sats:
            target_sats.append({"mask": "", "full_name": "Obsidian Unified Bouquet"})

        # Block parsing to preserve headers/footers for accurate saving later
        header_block, services_block, footer_block = [], [], []
        mode, idx = "header", 0
        while idx < len(lines):
            line = lines[idx]
            if line.strip() == "services" and mode == "header": mode = "services"; idx += 1; continue
            if line.strip() == "end" and mode == "services": mode = "footer"; idx += 1; continue
            if mode == "header": header_block.append(line); idx += 1
            elif mode == "footer": footer_block.append(line); idx += 1
            elif mode == "services":
                # Only parse lines conforming to standard Enigma2 SID formatting
                if ":" in line and line.count(":") >= 4:
                    sid, raw, pid = line.strip(), lines[idx+1].strip(), lines[idx+2].strip()
                    c_name, tags = self._clean_tags(raw)
                    services_block.append({'sid': sid, 'raw': raw, 'pid': pid, 'ns': sid.split(":")[1].lower(), 
                                         'clean': c_name, 'tags': tags, 'cat': self.get_arabic_category_name(self.get_category(c_name)), 'order': 9999})
                    idx += 3
                else: idx += 1

        generated_bouquets = []

        # Core Loop: Process each selected satellite individually
        for current_sat in target_sats:
            target_mask = current_sat.get('mask', '')
            selected_sat_name = current_sat.get('full_name', 'Obsidian Bouquet')
            sat_config_key = target_mask if target_mask else "ALL_SATS"

            all_services = [s for s in services_block if not target_mask or s['ns'].startswith(target_mask)]
            
            if not all_services:
                print(f"\n{self.t['c_warn']}Skipping {selected_sat_name} - No services found.{self.t['c_rst']}")
                continue

            UI.draw_solid_box(f"ORBITAL POSITION: {selected_sat_name}", 
                              [f"Services in scope: {len(all_services)}", f"Target Mask: {target_mask or 'ALL'}"], 
                              color=self.t['c_main'], icon=self.t['icon_sat'])

            # SATELLITE PERSISTENT STATE LOADING
            sat_config = self.load_sat_config(sat_config_key)
            cat_overrides = sat_config.get("cat_overrides", {})
            custom_orders = sat_config.get("custom_orders", {})
            
            for s in all_services:
                if s['sid'] in cat_overrides: s['cat'] = cat_overrides[s['sid']]
                if s['sid'] in custom_orders: s['order'] = custom_orders[s['sid']]
                    
            # DEFAULT ALPHABETICAL PRE-SORTING (applied if no custom orders exist)
            if not custom_orders:
                for cat in self.CATEGORY_ORDER:
                    cat_list = sorted([s for s in all_services if s['cat'] == cat], key=lambda x: x['raw'].lower())
                    for i, s in enumerate(cat_list):
                        s['order'] = i

            if "selected_cats" in sat_config:
                selected_cats = set(sat_config["selected_cats"])
            else:
                selected_cats = {self.get_arabic_category_name(c) for c in ["ISLAMIC", "CHRISTIAN", "EGYPTIAN", "MOVIES & SERIES", "SPORTS", "NEWS", "MUSIC & RADIO", "GENERAL"]}
            
            while True:
                cat_counts = defaultdict(int)
                for s in all_services: cat_counts[s['cat']] += 1
                display_list = UI.draw_category_selector(cat_counts, selected_cats, self.CATEGORY_ORDER)
                choice = UI.draw_input_block(f"CATEGORY MODIFIER [{selected_sat_name}]", "Toggle categories for translation or enter Interactive Mode. Press [ENTER] to start batch processing.")
                if choice == "": break
                if choice.upper() == "ALL": selected_cats = set(cat_counts.keys()); continue
                if choice.upper() == "NONE": selected_cats = set(); continue
                if choice.isdigit():
                    c_idx = int(choice) - 1
                    if 0 <= c_idx < len(display_list):
                        t_cat = display_list[c_idx]
                        action = UI.draw_input_block(f"ACTION: {t_cat}", "[T]oggle inclusion or [E]nter Interactive Mouse/Keyboard Editor?").lower()
                        if action == 'e': self.manage_category_contents(t_cat, all_services)
                        else:
                            if t_cat in selected_cats: selected_cats.remove(t_cat)
                            else: selected_cats.add(t_cat)

            # SAVE SATELLITE CONFIG BEFORE BATCH TRANSLATION
            self.save_sat_config(sat_config_key, selected_cats, all_services)

            neural_candidates = []
            for s in all_services:
                self.stats["total"] += 1
                if s['cat'] not in selected_cats: continue
                
                # Prevent re-translating if overlap occurs
                if 'tx' in s and s.get('method'):
                    continue

                raw_low = " ".join(s['raw'].split()).lower()
                
                # Skip translation entirely if the translation procedure is disabled
                if not self.enable_translation:
                    s['tx'], s['method'] = s['raw'], "BYPASSED"
                    self.stats["method_bypass"] += 1
                # Use Local Dictionary Override
                elif raw_low in self.corrections:
                    s['tx'], s['method'] = self.corrections[raw_low], "DICTIONARY"
                    self.stats["method_dict"] += 1
                    self.used_corrections.add(raw_low)
                # Skip translation if bypass trigger words are present
                elif s['cat'] not in selected_cats or any(bw in s['raw'].upper() for bw in self.BYPASS_WORDS):
                    s['tx'], s['method'] = s['raw'], "BYPASSED"
                    self.stats["method_bypass"] += 1
                else:
                    # Stage for AI Batch translation
                    neural_candidates.append(s)

            if self.neural_enabled and neural_candidates:
                total_batches = (len(neural_candidates) + self.BATCH_SIZE - 1) // self.BATCH_SIZE
                
                throttle_rows = [
                    f"RATE LIMIT: {self.t['c_accent']}Cascading Engine Active{self.t['c_rst']}",
                    f"ESTIMATION: Processing {len(neural_candidates)} items across {total_batches} batches."
                ]
                UI.draw_solid_box(f"CONGESTION CONTROL ACTIVE [{selected_sat_name}]", throttle_rows, color=self.t['c_warn'], icon=self.t['icon_hint'])

                for b_idx in range(0, len(neural_candidates), self.BATCH_SIZE):
                    batch_num = (b_idx // self.BATCH_SIZE) + 1
                    batch = neural_candidates[b_idx : b_idx + self.BATCH_SIZE]
                    
                    batch_header = f"BATCH {batch_num}/{total_batches} | GEMINI TRANSLATION STREAM"
                    batch_logs = []
                    
                    translations, lat = self.batch_translate_gemini([s['clean'] for s in batch])
                    
                    # Apply translated data back to objects
                    for s in batch:
                        res = translations.get(s['clean'], s['clean'])
                        if s['tags']: s['tx'] = f"{res} {' '.join(s['tags'])}".strip()
                        else: s['tx'] = res
                            
                        s['method'] = "GEMINI_NEURAL"
                        self.stats["method_deep"] += 1
                        status_line = f" {self.t['icon_trans']} {s['raw'].ljust(35)} -> {s['tx']}"
                        batch_logs.append(status_line)
                    
                    batch_logs.append(f" {self.t['border_h_mid'] * (UI.W-6)}")
                    batch_logs.append(f" {self.t['icon_time']} Latency: {lat}s | {self.t['icon_batch']} Processed: {len(batch)} items")
                    UI.draw_solid_box(batch_header, batch_logs, color=self.t['c_accent'], icon=self.t['icon_net'])

            # Generate individual bouquet specific to this orbital position
            clean_title = re.sub(r'[^a-zA-Z0-9\s.-]', '', selected_sat_name)
            if not clean_title.strip(): clean_title = f"Bouquet_{target_mask}"
            bq_name = f"userbouquet.{clean_title}.tv"
            generated_bouquets.append(bq_name)

            with open(bq_name, "w", encoding="utf-8") as bq:
                bq.write(f"#NAME •••••| {selected_sat_name} |•••••\n")
                marker_idx = 800
                for cat in self.CATEGORY_ORDER:
                    cat_services = sorted([s for s in all_services if s['cat'] == cat], key=lambda x: x['order'])
                    if not cat_services: continue
                    # Draw Bouquet Group Category Headers
                    bq.write(f"#SERVICE 1:64:{marker_idx}:0:0:0:0:0:0:0::::| {cat} |::\n#DESCRIPTION | {cat} |\n")
                    marker_idx += 1
                    for s in cat_services:
                        tx_name = s.get('tx', s['raw'])
                        ref = self.format_bouquet_reference(s['sid'])
                        bq.write(f"#SERVICE {ref}::{tx_name}\n#DESCRIPTION {tx_name}\n")

        # ---------------------------------------------------------
        # ALL ITERATIONS COMPLETE - SAVE GLOBAL FILES
        # ---------------------------------------------------------

        # Compile Mapping Log (Avoid Duplicates if overlap happened)
        seen_sids = set()
        for s in services_block:
            tx = s.get('tx', s['raw'])
            if 'method' in s and s['sid'] not in seen_sids:
                self.mapping_export.append([s['sid'].split(":")[0], s['raw'], tx, s['method']])
                seen_sids.add(s['sid'])

        # Write translated Lamedb
        out_db = path if ovr else path + ".translated"
        with open(out_db, "w", encoding="utf-8") as f:
            f.writelines(header_block); f.write("services\n")
            for s in services_block:
                tx = s.get('tx', s['raw'])
                f.write(f"{s['sid']}\n{tx}\n{s['pid']}\n")
            f.write("end\n"); f.writelines(footer_block)

        # Write statistical outputs for user review
        with open("translation_mapping.txt", "w", encoding="utf-8") as fm:
            fm.write(tabulate(self.mapping_export, headers=["HEX_SID", "ORIGINAL", "TRANSLATED", "METHOD"], tablefmt="fancy_grid"))

        # Dictionary Usage Report 
        unused_corrections = set(self.corrections.keys()) - self.used_corrections
        with open("dictionary_usage_report.txt", "w", encoding="utf-8") as rep:
            rep.write("=== DICTIONARY CORRECTIONS USAGE REPORT ===\n\n")
            rep.write(f"Total Entries in corrections.json: {len(self.corrections)}\n")
            rep.write(f"Used Entries: {len(self.used_corrections)}\n")
            rep.write(f"Unused Entries: {len(unused_corrections)}\n\n")
            rep.write("--- USED ENTRIES ---\n")
            for k in sorted(self.used_corrections):
                rep.write(f"'{k}' -> '{self.corrections[k]}'\n")
            rep.write("\n--- UNUSED ENTRIES (Review these for typos/mismatches) ---\n")
            for k in sorted(unused_corrections):
                rep.write(f"'{k}' -> '{self.corrections[k]}'\n")

        # Dynamic Summary Rendering
        bq_list_strs = [f"BOUQUET GENERATED:       {os.path.abspath(bq)}" for bq in generated_bouquets]

        summary_rows = [
            f"TIMESTAMP:              {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"TOTAL SERVICES SCANNED:  {self.stats['total']}",
            f"──────────────────────────────────────────────────────────",
            f"DICTIONARY MATCHES:      {self.stats['method_dict']}",
            f"GEMINI AI TRANSLATIONS:  {self.stats['method_deep']}",
            f"BYPASSED/TECHNICAL:      {self.stats['method_bypass']}",
            f"──────────────────────────────────────────────────────────",
            f"DATABASE OUTPUT:         {os.path.abspath(out_db)}"
        ]
        summary_rows.extend(bq_list_strs)
        summary_rows.extend([
            f"SESSION LOG:             {current_logger.filename}",
            f"JSON MAPPING LOG:        translation_mapping.txt",
            f"DICTIONARY USAGE LOG:    dictionary_usage_report.txt",
            f"SATELLITE STATE CONFIG:  {os.path.abspath('sat_configs.json')}"
        ])

        UI.draw_solid_box("EXTREME MISSION SUMMARY", summary_rows, color=self.t['c_ok'], icon=self.t['icon_stat'])

if __name__ == "__main__":
    try:
        # 1. Fetch the API key conditionally based on the toggle switch
        CURRENT_API_KEY = fetch_api_key() if ENABLE_TRANSLATION else None
        
        # 2. Pass the key and the state flag to the engine constructor
        engine = HorizonCore(api_key=CURRENT_API_KEY, enable_translation=ENABLE_TRANSLATION)
        
        # 3. Execute main logic
        engine.run(DB_PATH, WRITE_MODE)
        
    except KeyboardInterrupt:
        # Gracefully handle Ctrl+C interrupts across all states while ensuring the TUI resets cleanly
        sys.stdout.write('\033[?1000l\033[?1006l')
        sys.stdout.flush()
        print(f"\n\n{UI.theme['c_err']} [!] OPERATION CANCELLED BY USER (CTRL+C) {UI.theme['c_rst']}\n")
        sys.exit(0)
    except Exception as e:
        # Failsafe: Reset terminal mouse tracking codes on crash to prevent broken terminal states
        sys.stdout.write('\033[?1000l\033[?1006l')
        sys.stdout.flush()
        print(f"\n{UI.theme['c_err']}CRITICAL ENGINE FAILURE: {str(e)}{UI.theme['c_rst']}")
