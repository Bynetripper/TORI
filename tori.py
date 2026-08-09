#!/usr/bin/env python3
"""
TORI - Anonymity Routing & Proxy Manager
Minimal dark-mode/ASCII UI.
Requires: python3-tk
"""

import os
import sys
import json
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from urllib.request import urlopen, Request

# ----------------------------------------------------------------------------
# Theme
# ----------------------------------------------------------------------------

BG = "#05070a"
PANEL = "#0d1117"
BORDER = "#1f2937"
FG = "#e5e7eb"
MUTED = "#94a3b8"
ACCENT = "#22d3ee"
RETRO_GREEN = "#39ff14"
RETRO_CYAN = "#00fff9"
HAZARD_YELLOW = "#ffcc00"
BLOOD_RED = "#ff0033"


# ----------------------------------------------------------------------------
# Utilities
# ----------------------------------------------------------------------------

def is_root():
    return hasattr(os, "geteuid") and os.geteuid() == 0


def run_cmd(cmd, root=False):
    if root and not is_root():
        cmd = ['pkexec'] + cmd
    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    except Exception as e:
        print(f"Command failed: {e}")


# ----------------------------------------------------------------------------
# VPN Detector
# ----------------------------------------------------------------------------

class VPNDetector:
    VPN_INTERFACES = ['tun0', 'tun1', 'wg0', 'wg1', 'ppp0', 'vtun0']
    VPN_KEYWORDS = ['openvpn', 'wireguard', 'nordvpn', 'expressvpn', 'protonvpn']

    @staticmethod
    def is_vpn_active():
        for iface in VPNDetector.VPN_INTERFACES:
            if os.path.exists(f'/sys/class/net/{iface}'):
                return True, iface

        try:
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True, timeout=5)
            for line in result.stdout.split('\n'):
                for kw in VPNDetector.VPN_KEYWORDS:
                    if kw in line.lower() and 'grep' not in line.lower():
                        return True, kw
        except Exception:
            pass

        try:
            result = subprocess.run(['ip', 'route'], capture_output=True, text=True, timeout=5)
            for line in result.stdout.split('\n'):
                if 'tun' in line or 'wg' in line:
                    return True, 'route'
        except Exception:
            pass

        return False, None

    @staticmethod
    def get_vpn_interface():
        active, name = VPNDetector.is_vpn_active()
        if active and name in VPNDetector.VPN_INTERFACES:
            return name
        return None


# ----------------------------------------------------------------------------
# IP Checker
# ----------------------------------------------------------------------------

def check_ip_async(callback, use_socks=False):
    def worker():
        urls = ["https://ipinfo.io/json", "https://api.ipify.org?format=json"]

        for url in urls:
            if use_socks:
                cmd = [
                    'curl',
                    '-s',
                    '--socks5-hostname',
                    '127.0.0.1:9050',
                    '--max-time',
                    '10',
                    url
                ]
            else:
                cmd = [
                    'curl',
                    '-s',
                    '--max-time',
                    '10',
                    url
                ]

            try:
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                if res.returncode == 0 and res.stdout:
                    data = json.loads(res.stdout)
                    if "ip" in data:
                        callback(data)
                        return
                    if "origin" in data:
                        callback({"ip": data["origin"]})
                        return
            except Exception:
                pass

        # If using Tor SOCKS5, do not fall back to direct urllib.
        if use_socks:
            callback(None)
            return

        try:
            req = Request("https://api.ipify.org?format=json", headers={"User-Agent": "Tori/1.0"})
            with urlopen(req, timeout=10) as r:
                data = json.loads(r.read().decode())
                callback(data)
                return
        except Exception:
            callback(None)

    threading.Thread(target=worker, daemon=True).start()


# ----------------------------------------------------------------------------
# Browser Launcher
# ----------------------------------------------------------------------------

class BrowserLauncher:
    SOCKS_HOST = "127.0.0.1"
    SOCKS_PORT = "9050"

    @staticmethod
    def launch_firefox_tor():
        profile_dir = "/tmp/tori_firefox_profile"
        os.makedirs(profile_dir, exist_ok=True)

        user_js = f"""
user_pref("network.proxy.type", 1);
user_pref("network.proxy.socks", "{BrowserLauncher.SOCKS_HOST}");
user_pref("network.proxy.socks_port", {BrowserLauncher.SOCKS_PORT});
user_pref("network.proxy.socks_remote_dns", true);
user_pref("network.proxy.socks_version", 5);
user_pref("network.proxy.no_proxies_on", "localhost, 127.0.0.1");
user_pref("network.proxy.share_proxy_settings", true);
user_pref("privacy.donottrackheader.enabled", true);
user_pref("privacy.resistFingerprinting", true);
"""
        with open(os.path.join(profile_dir, 'user.js'), 'w') as f:
            f.write(user_js)

        try:
            subprocess.Popen(
                ['firefox', '--new-instance', '--profile', profile_dir, 'about:blank'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return True
        except FileNotFoundError:
            try:
                subprocess.Popen(
                    ['firefox-esr', '--new-instance', '--profile', profile_dir, 'about:blank'],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                return True
            except FileNotFoundError:
                return False

    @staticmethod
    def launch_chrome_tor():
        chrome_paths = ['google-chrome', 'chromium', 'chromium-browser']
        proxy_flag = f"--proxy-server=socks5://{BrowserLauncher.SOCKS_HOST}:{BrowserLauncher.SOCKS_PORT}"

        for chrome in chrome_paths:
            try:
                subprocess.Popen(
                    [
                        chrome,
                        proxy_flag,
                        '--host-resolver-rules=MAP * ~NOTFOUND , EXCLUDE 127.0.0.1',
                        '--no-first-run',
                        '--no-default-browser-check',
                        'about:blank'
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                return True
            except FileNotFoundError:
                continue
        return False

    @staticmethod
    def launch_tor_browser():
        tor_browser_paths = [
            os.path.expanduser("~/tor-browser/Browser/start-tor-browser"),
            "/usr/bin/torbrowser-launcher",
            "torbrowser-launcher"
        ]
        for path in tor_browser_paths:
            try:
                subprocess.Popen([path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True
            except (FileNotFoundError, PermissionError):
                continue
        return False


# ----------------------------------------------------------------------------
# Glowy button
# ----------------------------------------------------------------------------

class GlowButton(tk.Canvas):
    def __init__(self, parent, text="BUTTON", command=None, width=360, height=66, bg=None, font=None):
        self._bg = bg or "#05070a"
        super().__init__(parent, width=width, height=height, bg=self._bg, highlightthickness=0, cursor="hand2")

        self.text = text
        self.command = command
        self.width = width
        self.height = height
        self.hover = False
        self.pressed = False
        self.font = font or ("Courier", 10, "bold")

        self.bind("<Enter>", lambda e: self._set_hover(True))
        self.bind("<Leave>", lambda e: self._set_hover(False))
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self._draw()

    def set_text(self, text):
        self.text = text
        self._draw()

    def _set_hover(self, value):
        if self.hover != value:
            self.hover = value
            self._draw()

    def _on_press(self, event):
        self.pressed = True
        self._draw()

    def _on_release(self, event):
        if not self.pressed:
            return
        self.pressed = False
        self._draw()
        if 0 <= event.x <= self.width and 0 <= event.y <= self.height:
            if self.command:
                self.command()

    def _round_rect(self, x1, y1, x2, y2, radius, **kwargs):
        radius = max(1, min(radius, abs(x2 - x1) // 2, abs(y2 - y1) // 2))
        points = [
            x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
            x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
            x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1,
        ]
        return self.create_polygon(points, smooth=True, **kwargs)

    def _draw(self):
        self.delete("all")
        w, h, pad = self.width, self.height, 16
        glow_normal = ["#2a0005", "#4a000a", "#6a000f", "#8a0014"]
        glow_hover = ["#4a000a", "#7a0010", "#aa0018", "#dd0022"]
        colors = glow_hover if self.hover else glow_normal

        for off, color in zip((12, 9, 6, 3), colors):
            self._round_rect(off, off, w - off, h - off, 20, fill=self._bg, outline=color)

        x1, y1 = pad, pad
        x2, y2 = w - pad, h - pad
        border = "#ff4d6d" if self.hover else "#ff0033"
        fill = "#1a050a" if not self.pressed else "#0d0205"

        self._round_rect(x1, y1, x2, y2, 16, fill=fill, outline=border, width=2)
        inner = "#5c0011" if self.hover else "#3d000b"
        self._round_rect(x1 + 4, y1 + 4, x2 - 4, y2 - 4, 12, fill=fill, outline=inner)

        text_color = "#ffffff" if self.hover else "#ffccd5"
        y = h // 2 + (1 if self.pressed else 0)
        self.create_text(w // 2, y, text=self.text, fill=text_color, font=self.font)


# ----------------------------------------------------------------------------
# Main app
# ----------------------------------------------------------------------------

class ToriApp:
    def __init__(self, root):
        self.root = root
        self.root.title("TORI")
        self.root.geometry("680x860")
        self.root.minsize(560, 700)
        self.root.configure(bg=BG)

        self.zombie_active = False
        self.transparent_mode = False
        self.vpn_active = False

        self.canvas = None
        self.scroll_frame = None
        self.scroll_window_id = None
        self.about_frame = None
        self.about_text = None
        self.vpn_frame = None
        self.about_visible = False

        self.font_title = self._fixed_font(16, True)
        self.font_small = self._fixed_font(9)
        self.font_button = self._fixed_font(10, True)
        self.font_hazard = self._fixed_font(16, True)

        self._style()
        self._build_ui()

        self.root.after(500, self.check_vpn_status)
        self.root.after(1000, self.check_ip)

    def _fixed_font(self, size=10, bold=False):
        try:
            import tkinter.font as tkfont
            family = tkfont.nametofont("TkFixedFont").actual()["family"].strip()
            if not family:
                family = "Courier"
        except Exception:
            family = "Courier"
        weight = "bold" if bold else "normal"
        return (family, size, weight)

    def _style(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure(
            ".",
            background=BG,
            foreground=FG,
            bordercolor=BORDER,
            fieldbackground=PANEL,
            troughcolor=PANEL,
            font=self.font_small
        )
        style.configure("TFrame", background=BG)
        style.configure(
            "Vertical.TScrollbar",
            background="#111827",
            troughcolor=BG,
            bordercolor=BG,
            arrowcolor=ACCENT
        )

    def _build_ui(self):
        header = tk.Frame(self.root, bg=BG)
        header.pack(fill="x", padx=18, pady=(18, 8))

        tk.Label(
            header,
            text="[ T O R I ]",
            bg=BG,
            fg=RETRO_GREEN,
            font=self.font_title
        ).pack(side="left")

        tk.Label(
            header,
            text=":: ANONYMITY ROUTING ::",
            bg=BG,
            fg=MUTED,
            font=self.font_small
        ).pack(side="left", padx=(14, 0), pady=(10, 0))

        self.about_btn = tk.Button(
            header,
            text="[ ABOUT / INFO ]",
            bg=BG,
            fg=ACCENT,
            font=self.font_button,
            relief="flat",
            command=self.toggle_about,
            cursor="hand2",
            activebackground=BG,
            activeforeground=RETRO_CYAN
        )
        self.about_btn.pack(side="right", pady=(10, 0))

        self.hazard_canvas = tk.Canvas(self.root, height=90, bg=BG, highlightthickness=0)
        self.hazard_canvas.pack(fill="x", padx=18, pady=(0, 10))
        self.hazard_canvas.bind("<Configure>", self._draw_hazard)

        container = tk.Frame(self.root, bg=BG)
        container.pack(fill="both", expand=True, padx=18, pady=(0, 18))

        self.canvas = tk.Canvas(container, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        self.scroll_frame = tk.Frame(self.canvas, bg=BG)

        self.scroll_window_id = self.canvas.create_window(
            (0, 0),
            window=self.scroll_frame,
            anchor="nw"
        )

        self.scroll_frame.bind("<Configure>", self._on_scroll_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._bind_mousewheel()

        # About dropdown is inside the scrollable frame.
        self.about_frame = tk.Frame(
            self.scroll_frame,
            bg=PANEL,
            highlightbackground=ACCENT,
            highlightthickness=1
        )

        self.about_text = tk.Text(
            self.about_frame,
            bg=PANEL,
            fg=FG,
            font=self.font_small,
            relief="flat",
            wrap="word",
            height=52,
            padx=10,
            pady=10,
            highlightthickness=0,
            borderwidth=0,
            insertbackground=FG
        )
        self.about_text.pack(fill="x", expand=True)
        self.about_text.tag_config("heading", foreground=HAZARD_YELLOW, font=self.font_button)
        self.about_text.tag_config("subhead", foreground=RETRO_CYAN, font=self._fixed_font(9, True))
        self._populate_about_text()

        # VPN
        self.vpn_frame = self._create_panel(self.scroll_frame)
        self.vpn_frame.pack(fill="x", pady=6)

        self.vpn_label = tk.Label(
            self.vpn_frame,
            text="VPN: Checking...",
            bg=PANEL,
            fg=HAZARD_YELLOW,
            font=self.font_button,
            anchor="w"
        )
        self.vpn_label.pack(side="left", padx=10, pady=10)

        btn_vpn = tk.Button(
            self.vpn_frame,
            text="REFRESH",
            bg="#111827",
            fg=RETRO_GREEN,
            font=self.font_button,
            relief="flat",
            command=self.check_vpn_status
        )
        btn_vpn.pack(side="right", padx=10, pady=10)

        # IP
        ip_frame = self._create_panel(self.scroll_frame)
        ip_frame.pack(fill="x", pady=6)

        tk.Label(
            ip_frame,
            text="CURRENT IP / LOCATION",
            bg=PANEL,
            fg=HAZARD_YELLOW,
            font=self.font_button,
            anchor="w"
        ).pack(fill="x", padx=10, pady=(10, 5))

        self.ip_value = tk.Label(
            ip_frame,
            text="IP:  --- checking ---",
            bg=PANEL,
            fg=RETRO_GREEN,
            font=self._fixed_font(12, True),
            anchor="w"
        )
        self.ip_value.pack(fill="x", padx=10)

        self.loc_value = tk.Label(
            ip_frame,
            text="Location: ---",
            bg=PANEL,
            fg=MUTED,
            font=self.font_small,
            anchor="w"
        )
        self.loc_value.pack(fill="x", padx=10)

        self.isp_value = tk.Label(
            ip_frame,
            text="ISP / Org: ---",
            bg=PANEL,
            fg=MUTED,
            font=self.font_small,
            anchor="w"
        )
        self.isp_value.pack(fill="x", padx=10, pady=(0, 10))

        self.btn_check_ip = GlowButton(
            ip_frame,
            text="VERIFY IP NOW",
            command=self.check_ip,
            width=220,
            height=42,
            bg=PANEL,
            font=self.font_button
        )
        self.btn_check_ip.pack(pady=(0, 15))

        # Status
        self.status_label = tk.Label(
            self.scroll_frame,
            text="Status: OFFLINE",
            bg=BG,
            fg=BLOOD_RED,
            font=self._fixed_font(12, True)
        )
        self.status_label.pack(pady=10)

        # Mode
        mode_frame = self._create_panel(self.scroll_frame)
        mode_frame.pack(fill="x", pady=6)

        tk.Label(
            mode_frame,
            text="ROUTING MODE",
            bg=PANEL,
            fg=HAZARD_YELLOW,
            font=self.font_button,
            anchor="w"
        ).pack(fill="x", padx=10, pady=(10, 5))

        self.mode_var = tk.IntVar(value=0)
        radio_style = {
            "bg": PANEL,
            "fg": FG,
            "selectcolor": "#111827",
            "font": self.font_small,
            "activebackground": PANEL,
            "activeforeground": FG
        }

        tk.Radiobutton(
            mode_frame,
            text="SOCKS5 (App-level proxy)",
            variable=self.mode_var,
            value=0,
            **radio_style
        ).pack(anchor="w", padx=20, pady=2)

        tk.Radiobutton(
            mode_frame,
            text="Transparent (TOR Network)",
            variable=self.mode_var,
            value=1,
            **radio_style
        ).pack(anchor="w", padx=20, pady=(2, 10))

        # Browsers
        browser_frame = self._create_panel(self.scroll_frame)
        browser_frame.pack(fill="x", pady=6)

        tk.Label(
            browser_frame,
            text="LAUNCH BROWSER (TOR PROXY)",
            bg=PANEL,
            fg=HAZARD_YELLOW,
            font=self.font_button,
            anchor="w"
        ).pack(fill="x", padx=10, pady=(10, 5))

        brow_btns = tk.Frame(browser_frame, bg=PANEL)
        brow_btns.pack(fill="x", padx=10, pady=(0, 10))

        self._create_ascii_button(
            brow_btns,
            "Firefox",
            "#ff9500",
            lambda: self.launch_browser('firefox')
        ).pack(side="left", expand=True, fill="x", padx=(0, 5))

        self._create_ascii_button(
            brow_btns,
            "Chrome",
            "#4285f4",
            lambda: self.launch_browser('chrome')
        ).pack(side="left", expand=True, fill="x", padx=5)

        self._create_ascii_button(
            brow_btns,
            "Tor Browser",
            "#7d4698",
            lambda: self.launch_browser('tor')
        ).pack(side="left", expand=True, fill="x", padx=(5, 0))

        # Env
        self._create_ascii_button(
            self.scroll_frame,
            "SET PROXY ENV VARS",
            RETRO_GREEN,
            self.set_proxy_env
        ).pack(fill="x", pady=6)

        # Toggle
        self.toggle_btn = GlowButton(
            self.scroll_frame,
            text="ENABLE TORI MODE",
            command=self.toggle_tori_mode,
            width=420,
            height=62,
            bg=BG,
            font=self._fixed_font(14, True)
        )
        self.toggle_btn.pack(pady=15)

        # Granular controls
        gran_frame = tk.Frame(self.scroll_frame, bg=BG)
        gran_frame.pack(fill="x", pady=6)

        self._create_ascii_button(
            gran_frame,
            "Disable SOCKS5",
            HAZARD_YELLOW,
            self.turn_off_socks
        ).pack(side="left", expand=True, fill="x", padx=(0, 5))

        self._create_ascii_button(
            gran_frame,
            "Disable Trans",
            HAZARD_YELLOW,
            self.turn_off_transparent
        ).pack(side="left", expand=True, fill="x", padx=5)

        self._create_ascii_button(
            gran_frame,
            "Stop Tor",
            HAZARD_YELLOW,
            self.turn_off_tor
        ).pack(side="left", expand=True, fill="x", padx=(5, 0))

        # Reset
        self._create_ascii_button(
            self.scroll_frame,
            "RESET NETWORK",
            BLOOD_RED,
            self.reset_network
        ).pack(fill="x", pady=15)

    def _populate_about_text(self):
        self.about_text.config(state="normal")
        self.about_text.delete("1.0", "end")

        self.about_text.insert("end", "[ DISCLAIMER ]\n", "heading")
        self.about_text.insert("end", "Tori provides anonymity routing but does not make you invincible.\n")
        self.about_text.insert("end", "Misconfiguration, browser fingerprinting, or user error can leak identity.\n")
        self.about_text.insert("end", "Use responsibly and in accordance with local laws.\n\n")

        self.about_text.insert("end", "[ HOW IT WORKS ]\n", "heading")
        self.about_text.insert("end", "> VPN: ", "subhead")
        self.about_text.insert("end", "Encrypts traffic to a remote server. Hides your IP from your ISP,\n")
        self.about_text.insert("end", "  but the VPN provider can see your traffic and real IP.\n")

        self.about_text.insert("end", "> TOR: ", "subhead")
        self.about_text.insert("end", "Routes traffic through 3 volunteer nodes. Hides your IP from the\n")
        self.about_text.insert("end", "  destination, but the exit node can see unencrypted traffic.\n")

        self.about_text.insert("end", "> MULTI-LEVEL (VPN + TOR): ", "subhead")
        self.about_text.insert("end", "Combines both. 'TOR over VPN' (VPN -> TOR) hides Tor usage\n")
        self.about_text.insert("end", "  from your ISP and prevents malicious exit nodes from seeing your real IP.\n\n")

        self.about_text.insert("end", "[ SOCKS5 MODE ]\n", "heading")
        self.about_text.insert("end", "SOCKS5 is app-level routing. Tori starts Tor and exposes a local\n")
        self.about_text.insert("end", "SOCKS5 proxy at 127.0.0.1:9050. Only apps configured to use it\n")
        self.about_text.insert("end", "will go through Tor. This is ideal for browser-only routing.\n\n")

        self.about_text.insert("end", "[ FOXYPROXY SETUP ]\n", "heading")
        self.about_text.insert("end", "1. Install FoxyProxy Standard in your browser.\n")
        self.about_text.insert("end", "2. Add a new proxy profile.\n")
        self.about_text.insert("end", "3. Type: SOCKS5\n")
        self.about_text.insert("end", "4. Host: 127.0.0.1\n")
        self.about_text.insert("end", "5. Port: 9050\n")
        self.about_text.insert("end", "6. Enable Proxy DNS / Remote DNS.\n")
        self.about_text.insert("end", "7. Save and select the Tori proxy profile.\n")
        self.about_text.insert("end", "8. Test at https://check.torproject.org\n\n")

        self.about_text.insert("end", "[ MINIMAL USAGE ]\n", "heading")
        self.about_text.insert("end", "1. Connect to your VPN first.\n")
        self.about_text.insert("end", "2. Enable Tori mode using SOCKS5 routing.\n")
        self.about_text.insert("end", "3. Enable FoxyProxy with 127.0.0.1:9050.\n")
        self.about_text.insert("end", "4. Browse only through the proxied browser.\n")

        self.about_text.config(state="disabled")

    def toggle_about(self):
        if self.about_visible:
            self.about_frame.pack_forget()
            self.about_btn.config(text="[ ABOUT / INFO ]")
            self.about_visible = False
        else:
            self.about_frame.pack(fill="x", pady=6, before=self.vpn_frame)
            self.about_btn.config(text="[ HIDE INFO ]")
            self.about_visible = True
            self.canvas.yview_moveto(0.0)

        self.scroll_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_scroll_frame_configure(self, event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event=None):
        if event.width > 1:
            self.canvas.itemconfig(self.scroll_window_id, width=event.width)

    def _bind_mousewheel(self):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)

    def _on_mousewheel(self, event):
        if event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")
        elif getattr(event, "delta", 0):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _create_panel(self, parent):
        return tk.Frame(parent, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)

    def _create_ascii_button(self, parent, text, color, command):
        return tk.Button(
            parent,
            text=text,
            bg="#0b0c10",
            fg=color,
            font=self.font_button,
            relief="solid",
            borderwidth=1,
            highlightbackground=color,
            activebackground="#1f2833",
            activeforeground=color,
            cursor="hand2",
            command=command
        )

    def _draw_hazard(self, event=None):
        c = self.hazard_canvas
        c.delete("all")
        w = c.winfo_width()
        h = c.winfo_height()
        if w < 10:
            return

        stripe = 20
        for i in range(-h, w + h, stripe * 2):
            c.create_polygon([i, 0, i + stripe, 0, i + stripe + 8, 8, i + 8, 8], fill=HAZARD_YELLOW, outline="")
            c.create_polygon([i, h - 8, i + stripe, h - 8, i + stripe + 8, h, i + 8, h], fill=HAZARD_YELLOW, outline="")

        c.create_rectangle(0, 8, w, h - 8, fill="#05070a", outline="")

        title = "T O R I   M O D E"
        for off in range(4, 0, -1):
            c.create_text(w//2, h//2 - 5 + off, text=title, fill=f"#{60 - off*10:02x}0000", font=self.font_hazard)
        c.create_text(w//2, h//2 - 5, text=title, fill="#ffffff", font=self.font_hazard)

        sub = "ANONYMITY PROTOCOL ACTIVE"
        c.create_text(w//2, h//2 + 20, text=sub, fill=HAZARD_YELLOW, font=self.font_small)

    def check_vpn_status(self):
        active, name = VPNDetector.is_vpn_active()
        self.vpn_active = active
        if active:
            self.vpn_label.config(text=f"VPN: ACTIVE ({name})", fg=RETRO_GREEN)
        else:
            self.vpn_label.config(text="VPN: INACTIVE", fg="#ff4500")

    def check_ip(self):
        self.ip_value.config(text="IP:  ...querying...", fg=MUTED)
        self.loc_value.config(text="Location: ...")
        self.isp_value.config(text="ISP / Org: ...")

        use_socks = self.zombie_active and not self.transparent_mode

        def callback(data):
            if data:
                ip = data.get("ip", "?")
                city = data.get("city", "")
                reg = data.get("region", "")
                ctry = data.get("country", "")
                org = data.get("org", "")
                loc = ", ".join(x for x in [city, reg, ctry] if x) or "unknown"

                self.root.after(0, lambda: self.ip_value.config(text=f"IP:  {ip}"))
                self.root.after(0, lambda: self.loc_value.config(text=f"Location: {loc}"))
                self.root.after(0, lambda: self.isp_value.config(text=f"ISP / Org: {org or 'unknown'}"))

                if "tor" in org.lower() or "tor" in ip.lower():
                    self.root.after(0, lambda: self.ip_value.config(fg=RETRO_GREEN))
                else:
                    self.root.after(0, lambda: self.ip_value.config(fg="#ff4500"))
            else:
                self.root.after(0, lambda: self.ip_value.config(text="IP:  [check failed]", fg=BLOOD_RED))

        check_ip_async(callback, use_socks=use_socks)

    def configure_torrc(self):
        torrc_path = "/etc/tor/torrc"
        try:
            with open(torrc_path, 'r') as f:
                content = f.read()

            additions = []
            if "TransPort" not in content:
                additions.append("TransPort 9040")
            if "DNSPort" not in content:
                additions.append("DNSPort 5353")
            if "AutomapHostsOnResolve" not in content:
                additions.append("AutomapHostsOnResolve 1")

            if additions:
                content += "\n# Tori Mode Additions\n" + "\n".join(additions) + "\n"

            temp_path = "/tmp/torrc.new"
            with open(temp_path, 'w') as f:
                f.write(content)

            run_cmd(['cp', temp_path, torrc_path], root=True)
            os.remove(temp_path)
        except Exception as e:
            print(f"Failed to configure torrc: {e}")

    def apply_transparent_proxy(self):
        vpn_iface = VPNDetector.get_vpn_interface()
        script = f"""#!/bin/bash
iptables -F
iptables -t nat -F
iptables -X
iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT DROP

iptables -A INPUT -i lo -j ACCEPT
iptables -A OUTPUT -o lo -j ACCEPT
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
iptables -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

TOR_UID=$(id -u debian-tor 2>/dev/null || id -u _tor 2>/dev/null)

if [ -n "$TOR_UID" ]; then
    iptables -t nat -A OUTPUT -m owner --uid-owner $TOR_UID -j RETURN
fi

iptables -t nat -A OUTPUT -p udp --dport 53 -j REDIRECT --to-ports 5353
iptables -t nat -A OUTPUT -p tcp --dport 53 -j REDIRECT --to-ports 5353
iptables -t nat -A OUTPUT -p tcp -j REDIRECT --to-ports 9040

if [ -n "$TOR_UID" ]; then
    iptables -A OUTPUT -m owner --uid-owner $TOR_UID -j ACCEPT
fi

iptables -A OUTPUT -p tcp --dport 9040 -j ACCEPT
iptables -A OUTPUT -p tcp --dport 9050 -j ACCEPT
iptables -A OUTPUT -p udp --dport 5353 -j ACCEPT

{"iptables -A OUTPUT -o " + vpn_iface + " -j ACCEPT" if vpn_iface else "# No VPN detected"}
"""
        temp_script = "/tmp/tori_iptables.sh"
        with open(temp_script, 'w') as f:
            f.write(script)
        os.chmod(temp_script, 0o755)
        run_cmd(['bash', temp_script], root=True)
        os.remove(temp_script)

    def remove_transparent_proxy(self):
        script = """#!/bin/bash
iptables -F
iptables -t nat -F
iptables -X
iptables -P INPUT ACCEPT
iptables -P FORWARD ACCEPT
iptables -P OUTPUT ACCEPT
systemctl restart systemd-resolved 2>/dev/null || true
"""
        temp_script = "/tmp/tori_flush.sh"
        with open(temp_script, 'w') as f:
            f.write(script)
        os.chmod(temp_script, 0o755)
        run_cmd(['bash', temp_script], root=True)
        os.remove(temp_script)

    def set_system_proxy(self, enable):
        if enable:
            run_cmd(['gsettings', 'set', 'org.gnome.system.proxy', 'mode', 'manual'])
            run_cmd(['gsettings', 'set', 'org.gnome.system.proxy.socks', 'host', '127.0.0.1'])
            run_cmd(['gsettings', 'set', 'org.gnome.system.proxy.socks', 'port', '9050'])
        else:
            run_cmd(['gsettings', 'set', 'org.gnome.system.proxy', 'mode', 'none'])

    def set_proxy_env(self):
        messagebox.showinfo(
            "Proxy Environment Variables",
            "Run this in your terminal to set proxy env vars:\n\n"
            "export http_proxy=\"socks5h://127.0.0.1:9050\"\n"
            "export https_proxy=\"socks5h://127.0.0.1:9050\"\n"
            "export ALL_PROXY=\"socks5h://127.0.0.1:9050\"\n\n"
            "Or add to ~/.bashrc for persistence."
        )

    def launch_browser(self, browser_type):
        if not self.zombie_active:
            messagebox.showwarning("Tori Mode Inactive", "Enable Tori Mode first to use Tor proxy.")
            return

        if browser_type == 'firefox':
            success = BrowserLauncher.launch_firefox_tor()
            name = "Firefox"
        elif browser_type == 'chrome':
            success = BrowserLauncher.launch_chrome_tor()
            name = "Chrome/Chromium"
        elif browser_type == 'tor':
            success = BrowserLauncher.launch_tor_browser()
            name = "Tor Browser"
        else:
            return

        if success:
            messagebox.showinfo(
                "Browser Launched",
                f"{name} launched with Tor SOCKS5 proxy (127.0.0.1:9050).\nRemote DNS resolution enabled."
            )
        else:
            messagebox.showwarning(
                "Browser Not Found",
                f"{name} not found. Install it or use the proxy manually."
            )

    def toggle_tori_mode(self):
        if not is_root():
            messagebox.showwarning(
                "Root Required",
                "Tori Mode requires root privileges to manage Tor and iptables.\n\n"
                "Please run: sudo python3 Tori.py"
            )
            return

        if not self.zombie_active:
            self.toggle_btn.set_text("DISABLE TORI MODE")
            self.zombie_active = True
            self.transparent_mode = (self.mode_var.get() == 1)
            self.status_label.config(text="... Status: BOARDING WINDOWS...", fg=HAZARD_YELLOW)

            self.configure_torrc()
            run_cmd(['systemctl', 'start', 'tor'], root=True)
            self.check_vpn_status()

            if self.transparent_mode:
                self.root.after(4000, self._enable_transparent)
            else:
                self.root.after(3000, self._enable_socks)
        else:
            self.toggle_btn.set_text("ENABLE TORI MODE")
            self.zombie_active = False

            if self.transparent_mode:
                self.remove_transparent_proxy()
            else:
                self.set_system_proxy(False)

            run_cmd(['systemctl', 'stop', 'tor'], root=True)
            self.status_label.config(text="Status: OFFLINE", fg=BLOOD_RED)
            self.root.after(500, self.check_ip)

    def _enable_socks(self):
        self.set_system_proxy(True)
        vpn_status = " [VPN DETECTED]" if self.vpn_active else ""
        self.status_label.config(text=f"Status: TOR ACTIVE - SOCKS5 PROXY ON{vpn_status}", fg=RETRO_GREEN)
        self.check_ip()

    def _enable_transparent(self):
        self.apply_transparent_proxy()
        vpn_status = " [VPN DETECTED]" if self.vpn_active else ""
        self.status_label.config(text=f"Status: TOR ACTIVE - TRANSPARENT PROXY ON{vpn_status}", fg=RETRO_GREEN)
        self.check_ip()

    def turn_off_socks(self):
        self.set_system_proxy(False)
        messagebox.showinfo(
            "SOCKS5",
            "System-wide SOCKS5 proxy disabled.\nTor daemon is still running."
        )

    def turn_off_transparent(self):
        self.remove_transparent_proxy()
        messagebox.showinfo(
            "Transparent Proxy",
            "Transparent proxy disabled (iptables flushed).\nTor daemon is still running."
        )

    def turn_off_tor(self):
        run_cmd(['systemctl', 'stop', 'tor'], root=True)
        messagebox.showinfo(
            "Tor",
            "Tor daemon stopped.\nProxy settings remain unchanged."
        )

    def reset_network(self):
        self.status_label.config(text="... RESETTING NETWORK...", fg=BLOOD_RED)
        self.remove_transparent_proxy()
        run_cmd(['pkill', '-9', 'tor'], root=True)
        self.set_system_proxy(False)
        run_cmd(['systemctl', 'restart', 'NetworkManager'], root=True)

        self.zombie_active = False
        self.transparent_mode = False
        self.toggle_btn.set_text("ENABLE TORI MODE")

        messagebox.showinfo(
            "Network Reset",
            "PANIC COMPLETE\nNetwork interfaces and DNS restored."
        )

        self.root.after(1500, self.check_ip)
        self.root.after(1500, self.check_vpn_status)


def main():
    root = tk.Tk()
    ToriApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()