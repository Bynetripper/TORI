#!/usr/bin/env python3
"""
TORII - Anonymity Routing & Proxy Manager
Minimal, centered dark-mode UI.
Optimized for Raspberry Pi OS / Debian.
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
        if subprocess.run(['which', 'pkexec'], capture_output=True).returncode == 0:
            cmd = ['pkexec'] + cmd
        else:
            cmd = ['sudo'] + cmd
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
        return False, None

# ----------------------------------------------------------------------------
# IP Checker
# ----------------------------------------------------------------------------
def check_ip_async(callback, use_socks=False):
    def worker():
        urls = ["https://ipinfo.io/json", "https://api.ipify.org?format=json"]
        for url in urls:
            if use_socks:
                cmd = ['curl', '-s', '--socks5-hostname', '127.0.0.1:9050', '--max-time', '10', url]
            else:
                cmd = ['curl', '-s', '--max-time', '10', url]
            try:
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                if res.returncode == 0 and res.stdout:
                    data = json.loads(res.stdout)
                    if "ip" in data:
                        callback(data); return
                    if "origin" in data:
                        callback({"ip": data["origin"]}); return
            except Exception:
                pass
        callback(None)
    threading.Thread(target=worker, daemon=True).start()

# ----------------------------------------------------------------------------
# Glowy button
# ----------------------------------------------------------------------------
class GlowButton(tk.Canvas):
    def __init__(self, parent, text="BUTTON", command=None, width=360, height=66, bg=None, font=None):
        self._bg = bg or "#05070a"
        super().__init__(parent, width=width, height=height, bg=self._bg, highlightthickness=0, cursor="hand2")
        self.text = text; self.command = command; self.width = width; self.height = height
        self.hover = False; self.pressed = False
        self.font = font or ("Courier", 10, "bold")
        self.bind("<Enter>", lambda e: self._set_hover(True))
        self.bind("<Leave>", lambda e: self._set_hover(False))
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self._draw()

    def set_text(self, text):
        self.text = text; self._draw()

    def _set_hover(self, value):
        if self.hover != value: self.hover = value; self._draw()

    def _on_press(self, event): self.pressed = True; self._draw()

    def _on_release(self, event):
        if not self.pressed: return
        self.pressed = False; self._draw()
        if 0 <= event.x <= self.width and 0 <= event.y <= self.height:
            if self.command: self.command()

    def _round_rect(self, x1, y1, x2, y2, radius, **kwargs):
        radius = max(1, min(radius, abs(x2 - x1) // 2, abs(y2 - y1) // 2))
        points = [x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius, x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2, x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1]
        return self.create_polygon(points, smooth=True, **kwargs)

    def _draw(self):
        self.delete("all")
        w, h, pad = self.width, self.height, 16
        glow_normal = ["#2a0005", "#4a000a", "#6a000f", "#8a0014"]
        glow_hover = ["#4a000a", "#7a0010", "#aa0018", "#dd0022"]
        colors = glow_hover if self.hover else glow_normal
        for off, color in zip((12, 9, 6, 3), colors):
            self._round_rect(off, off, w - off, h - off, 20, fill=self._bg, outline=color)
        x1, y1 = pad, pad; x2, y2 = w - pad, h - pad
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
class ToriiApp:
    def __init__(self, root):
        self.root = root
        self.root.title("TORII")
        self.root.geometry("550x480")
        self.root.minsize(450, 400)
        self.root.configure(bg=BG)
        
        self.zombie_active = False
        self.transparent_mode = True # Default to transparent
        self.vpn_active = False
        self.settings_window = None
        
        self.font_title = self._fixed_font(18, True)
        self.font_small = self._fixed_font(9)
        self.font_button = self._fixed_font(10, True)
        
        self._style()
        self._build_ui()
        
        self.root.after(500, self.check_vpn_status)
        self.root.after(1000, self.check_ip)

    def _fixed_font(self, size=10, bold=False):
        families = ["DejaVu Sans Mono", "Monospace", "Courier New", "Courier"]
        family = "Courier"
        try:
            import tkinter.font as tkfont
            available = tkfont.families()
            for f in families:
                if f in available: family = f; break
        except Exception: pass
        weight = "bold" if bold else "normal"
        return (family, size, weight)

    def _style(self):
        style = ttk.Style(self.root)
        try: style.theme_use("clam")
        except Exception: pass
        style.configure(".", background=BG, foreground=FG, bordercolor=BORDER, fieldbackground=PANEL, font=self.font_small)
        style.configure("TFrame", background=BG)

    def _build_ui(self):
        # Header (Centered Title, Settings on Right)
        header = tk.Frame(self.root, bg=BG)
        header.pack(fill="x", pady=20)
        tk.Label(header, text="[ T O R I I ]", bg=BG, fg=RETRO_GREEN, font=self.font_title).pack()
        
        self.settings_btn = tk.Button(header, text="[ SETTINGS ]", bg=BG, fg=HAZARD_YELLOW, font=self.font_button, relief="flat", command=self.open_settings, cursor="hand2", activebackground=BG, activeforeground=RETRO_GREEN)
        self.settings_btn.place(relx=1.0, rely=0.5, anchor="e", x=-20)

        # Main Content Container (Centered)
        container = tk.Frame(self.root, bg=BG)
        container.pack(fill="both", expand=True, padx=40)

        # IP Panel
        ip_frame = self._create_panel(container)
        ip_frame.pack(fill="x", pady=10)
        tk.Label(ip_frame, text="CURRENT EXIT IP", bg=PANEL, fg=HAZARD_YELLOW, font=self.font_button, anchor="center").pack(fill="x", padx=10, pady=(10, 5))
        self.ip_value = tk.Label(ip_frame, text="--- CHECKING ---", bg=PANEL, fg=RETRO_GREEN, font=self._fixed_font(14, True), anchor="center")
        self.ip_value.pack(fill="x", padx=10)
        self.loc_value = tk.Label(ip_frame, text="Location: ---", bg=PANEL, fg=MUTED, font=self.font_small, anchor="center")
        self.loc_value.pack(fill="x", padx=10)
        
        # Fixed Verify Button (Wider to fit text properly)
        GlowButton(ip_frame, text="VERIFY IP NOW", command=self.check_ip, width=240, height=40, bg=PANEL, font=self.font_button).pack(pady=(0, 15))

        # Status Label (Centered)
        self.status_label = tk.Label(container, text="Status: OFFLINE", bg=BG, fg=BLOOD_RED, font=self._fixed_font(12, True))
        self.status_label.pack(pady=10)

        # Main Enable Button (Centered)
        self.toggle_btn = GlowButton(container, text="ENABLE TORII MODE", command=self.toggle_tori_mode, width=320, height=58, bg=BG, font=self._fixed_font(14, True))
        self.toggle_btn.pack(pady=20)

    # -------------------------------------------------------------------------
    # Settings Window
    # -------------------------------------------------------------------------
    def open_settings(self):
        if self.settings_window and self.settings_window.winfo_exists():
            self.settings_window.focus(); return
            
        self.settings_window = tk.Toplevel(self.root)
        self.settings_window.title("TORII Settings")
        self.settings_window.geometry("400x520")
        self.settings_window.configure(bg=BG)
        self.settings_window.transient(self.root)
        
        tk.Label(self.settings_window, text="⚙ SETTINGS & CONTROLS", bg=BG, fg=ACCENT, font=self.font_title).pack(pady=15)
        
        settings_frame = tk.Frame(self.settings_window, bg=BG)
        settings_frame.pack(fill="both", expand=True, padx=20)
        
        # Routing Mode
        mode_frame = self._create_panel(settings_frame)
        mode_frame.pack(fill="x", pady=10)
        tk.Label(mode_frame, text="ROUTING MODE", bg=PANEL, fg=HAZARD_YELLOW, font=self.font_button, anchor="center").pack(fill="x", padx=10, pady=(10, 5))
        self.mode_var = tk.IntVar(value=1) # Default to Transparent (1)
        radio_style = {"bg": PANEL, "fg": FG, "selectcolor": "#111827", "font": self.font_small, "activebackground": PANEL, "activeforeground": FG}
        tk.Radiobutton(mode_frame, text="SOCKS5 (App-level proxy)", variable=self.mode_var, value=0, **radio_style).pack(anchor="center", pady=2)
        tk.Radiobutton(mode_frame, text="Transparent (System-wide)", variable=self.mode_var, value=1, **radio_style).pack(anchor="center", pady=(2, 10))

        # Exit Node Exclusions
        exclude_frame = self._create_panel(settings_frame)
        exclude_frame.pack(fill="x", pady=10)
        tk.Label(exclude_frame, text="AVOID EXIT NODES", bg=PANEL, fg=HAZARD_YELLOW, font=self.font_button, anchor="center").pack(fill="x", padx=10, pady=(10, 5))
        
        self.avoid_usa_var = tk.BooleanVar(value=False)
        self.avoid_eu_var = tk.BooleanVar(value=False)
        chk_style = {"bg": PANEL, "fg": FG, "selectcolor": "#111827", "font": self.font_small, "activebackground": PANEL, "activeforeground": FG}
        tk.Checkbutton(exclude_frame, text="Avoid USA End Nodes", variable=self.avoid_usa_var, **chk_style).pack(anchor="center", pady=2)
        tk.Checkbutton(exclude_frame, text="Avoid Europe End Nodes", variable=self.avoid_eu_var, **chk_style).pack(anchor="center", pady=(2, 10))

        # Node Status
        node_frame = self._create_panel(settings_frame)
        node_frame.pack(fill="x", pady=10)
        tk.Label(node_frame, text="NODE STATUS", bg=PANEL, fg=HAZARD_YELLOW, font=self.font_button, anchor="center").pack(fill="x", padx=10, pady=(10, 5))
        self.node_count_lbl = tk.Label(node_frame, text="Active Circuits: Checking...", bg=PANEL, fg=FG, font=self.font_small, anchor="center")
        self.node_count_lbl.pack(fill="x", padx=10)
        tk.Button(node_frame, text="Refresh Status", bg="#111827", fg=RETRO_GREEN, font=self.font_button, relief="flat", command=self.update_node_count).pack(pady=10)

        # Action Buttons
        tk.Button(settings_frame, text="[ DISCONNECT TORII ]", bg="#1a050a", fg=BLOOD_RED, font=self.font_button, relief="solid", borderwidth=1, highlightbackground=BLOOD_RED, activebackground="#2a0005", activeforeground="#ffffff", cursor="hand2", command=self.disconnect).pack(fill="x", pady=8)
        tk.Button(settings_frame, text="[ PANIC: RESET NETWORK ]", bg="#1a050a", fg=HAZARD_YELLOW, font=self.font_button, relief="solid", borderwidth=1, highlightbackground=HAZARD_YELLOW, activebackground="#2a1a00", activeforeground="#ffffff", cursor="hand2", command=self.reset_network).pack(fill="x", pady=8)
        tk.Button(settings_frame, text="[ INSTALL DEPENDENCIES ]", bg="#111827", fg=HAZARD_YELLOW, font=self.font_button, relief="flat", command=self.install_dependencies).pack(fill="x", pady=10)

    def update_node_count(self):
        if self.zombie_active:
            self.node_count_lbl.config(text="Active Circuits: 3 (Guard, Middle, Exit)", fg=RETRO_GREEN)
        else:
            self.node_count_lbl.config(text="Active Circuits: 0 (Tor Offline)", fg=MUTED)

    def disconnect(self):
        if not self.zombie_active:
            messagebox.showinfo("Info", "Torii Mode is already offline.")
            return
        if messagebox.askyesno("Disconnect", "Disable Torii Mode and flush proxy settings?"):
            self.toggle_tori_mode()

    def install_dependencies(self):
        if not is_root():
            messagebox.showwarning("Root Required", "Please run with sudo to install dependencies.")
            return
        if subprocess.run(['which', 'apt'], capture_output=True).returncode != 0:
            messagebox.showwarning("Unsupported OS", "Automatic installation is only supported on Debian/Raspberry Pi OS (apt).")
            return
        self.status_label.config(text="Status: INSTALLING...", fg=HAZARD_YELLOW)
        def worker():
            cmd = "apt update && apt install -y tor curl iptables python3-tk network-manager"
            try:
                res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=180)
                if res.returncode == 0:
                    self.root.after(0, lambda: messagebox.showinfo("Success", "Dependencies installed successfully!"))
                    self.root.after(0, lambda: self.status_label.config(text="Status: READY", fg=RETRO_GREEN))
                else:
                    self.root.after(0, lambda: messagebox.showerror("Error", "Installation failed."))
                    self.root.after(0, lambda: self.status_label.config(text="Status: INSTALL FAILED", fg=BLOOD_RED))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
        threading.Thread(target=worker, daemon=True).start()

    # -------------------------------------------------------------------------
    # Core Logic
    # -------------------------------------------------------------------------
    def _create_panel(self, parent): return tk.Frame(parent, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)

    def check_vpn_status(self):
        active, name = VPNDetector.is_vpn_active()
        self.vpn_active = active
        if active:
            self.status_label.config(text=f"Status: OFFLINE [VPN: {name}]", fg=HAZARD_YELLOW)
        else:
            self.status_label.config(text="Status: OFFLINE", fg=BLOOD_RED)

    def check_ip(self):
        self.ip_value.config(text="...QUERYING...", fg=MUTED)
        self.loc_value.config(text="Location: ...")
        use_socks = self.zombie_active and not self.transparent_mode
        def callback(data):
            if data:
                ip = data.get("ip", "?"); city = data.get("city", ""); reg = data.get("region", ""); ctry = data.get("country", ""); org = data.get("org", "")
                loc = ", ".join(x for x in [city, reg, ctry] if x) or "unknown"
                self.root.after(0, lambda: self.ip_value.config(text=ip))
                self.root.after(0, lambda: self.loc_value.config(text=f"Location: {loc}"))
                if "tor" in org.lower() or "tor" in ip.lower(): self.root.after(0, lambda: self.ip_value.config(fg=RETRO_GREEN))
                else: self.root.after(0, lambda: self.ip_value.config(fg="#ff4500"))
            else:
                self.root.after(0, lambda: self.ip_value.config(text="[ CHECK FAILED ]", fg=BLOOD_RED))
        check_ip_async(callback, use_socks=use_socks)

    def configure_torrc(self):
        torrc_path = "/etc/tor/torrc"
        try:
            with open(torrc_path, 'r') as f: content = f.read()
            
            # Clean old Torii additions
            lines = content.split('\n')
            new_lines = []
            skip = False
            for line in lines:
                if line.startswith("# Torii Mode Additions"): skip = True
                if not skip: new_lines.append(line)
                if skip and line.strip() == "" and len(new_lines) > 0 and new_lines[-1].strip() == "": skip = False
            content = '\n'.join(new_lines)
            
            additions = ["# Torii Mode Additions"]
            if "TransPort" not in content: additions.append("TransPort 9040")
            if "DNSPort" not in content: additions.append("DNSPort 5353")
            if "AutomapHostsOnResolve" not in content: additions.append("AutomapHostsOnResolve 1")
            
            # Apply Exit Node Exclusions
            exclude_nodes = []
            if self.avoid_usa_var.get():
                exclude_nodes.append("{us}")
            if self.avoid_eu_var.get():
                # Major European countries
                eu_nodes = "{de,fr,nl,gb,es,it,se,ch,at,be,dk,fi,ie,no,pl,pt}"
                exclude_nodes.append(eu_nodes)
                
            if exclude_nodes:
                additions.append(f"ExcludeNodes {','.join(exclude_nodes)}")
                additions.append("StrictNodes 0") # Allow fallback if excluded nodes are the only ones available
                
            content += "\n" + "\n".join(additions) + "\n"
            
            temp_path = "/tmp/torrc.new"
            with open(temp_path, 'w') as f: f.write(content)
            run_cmd(['cp', temp_path, torrc_path], root=True)
            os.remove(temp_path)
        except Exception as e:
            print(f"Failed to configure torrc: {e}")

    def apply_transparent_proxy(self):
        script = """#!/bin/bash
iptables -F && iptables -t nat -F && iptables -X
iptables -P INPUT DROP && iptables -P FORWARD DROP && iptables -P OUTPUT DROP
iptables -A INPUT -i lo -j ACCEPT && iptables -A OUTPUT -o lo -j ACCEPT
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
iptables -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
TOR_UID=$(id -u debian-tor 2>/dev/null || id -u _tor 2>/dev/null || id -u tor 2>/dev/null)
[ -n "$TOR_UID" ] && iptables -t nat -A OUTPUT -m owner --uid-owner $TOR_UID -j RETURN
iptables -t nat -A OUTPUT -p udp --dport 53 -j REDIRECT --to-ports 5353
iptables -t nat -A OUTPUT -p tcp --dport 53 -j REDIRECT --to-ports 5353
iptables -t nat -A OUTPUT -p tcp -j REDIRECT --to-ports 9040
[ -n "$TOR_UID" ] && iptables -A OUTPUT -m owner --uid-owner $TOR_UID -j ACCEPT
iptables -A OUTPUT -p tcp --dport 9040 -j ACCEPT && iptables -A OUTPUT -p tcp --dport 9050 -j ACCEPT
"""
        temp_script = "/tmp/torii_iptables.sh"
        with open(temp_script, 'w') as f: f.write(script)
        os.chmod(temp_script, 0o755)
        run_cmd(['bash', temp_script], root=True)
        os.remove(temp_script)

    def remove_transparent_proxy(self):
        script = "#!/bin/bash\niptables -F && iptables -t nat -F && iptables -X\niptables -P INPUT ACCEPT && iptables -P FORWARD ACCEPT && iptables -P OUTPUT ACCEPT\n"
        temp_script = "/tmp/torii_flush.sh"
        with open(temp_script, 'w') as f: f.write(script)
        os.chmod(temp_script, 0o755)
        run_cmd(['bash', temp_script], root=True)
        os.remove(temp_script)

    def set_system_proxy(self, enable):
        try:
            if enable:
                subprocess.run(['gsettings', 'set', 'org.gnome.system.proxy', 'mode', 'manual'], capture_output=True, timeout=5)
                subprocess.run(['gsettings', 'set', 'org.gnome.system.proxy.socks', 'host', '127.0.0.1'], capture_output=True, timeout=5)
                subprocess.run(['gsettings', 'set', 'org.gnome.system.proxy.socks', 'port', '9050'], capture_output=True, timeout=5)
            else:
                subprocess.run(['gsettings', 'set', 'org.gnome.system.proxy', 'mode', 'none'], capture_output=True, timeout=5)
        except Exception: pass

    def toggle_tori_mode(self):
        if not is_root():
            messagebox.showwarning("Root Required", "Torii Mode requires root privileges.\nPlease run: sudo python3 torii.py")
            return

        if not self.zombie_active:
            self.toggle_btn.set_text("DISABLE TORII MODE")
            self.zombie_active = True
            self.transparent_mode = (self.mode_var.get() == 1)
            self.status_label.config(text="... Status: Connecting...", fg=HAZARD_YELLOW)
            
            self.configure_torrc() # Applies Avoid USA/EU rules before starting
            run_cmd(['systemctl', 'start', 'tor'], root=True)
            self.check_vpn_status()
            
            if self.transparent_mode:
                self.root.after(4000, self._enable_transparent)
            else:
                self.root.after(3000, self._enable_socks)
        else:
            self.toggle_btn.set_text("ENABLE TORII MODE")
            self.zombie_active = False
            if self.transparent_mode: self.remove_transparent_proxy()
            else: self.set_system_proxy(False)
            run_cmd(['systemctl', 'stop', 'tor'], root=True)
            self.status_label.config(text="Status: OFFLINE", fg=BLOOD_RED)
            self.root.after(500, self.check_ip)

    def _enable_socks(self):
        self.set_system_proxy(True)
        vpn_status = " [VPN DETECTED]" if self.vpn_active else ""
        self.status_label.config(text=f"Status: TOR ACTIVE - SOCKS5{vpn_status}", fg=RETRO_GREEN)
        self.check_ip()

    def _enable_transparent(self):
        self.apply_transparent_proxy()
        vpn_status = " [VPN DETECTED]" if self.vpn_active else ""
        self.status_label.config(text=f"Status: TOR ACTIVE - TRANSPARENT{vpn_status}", fg=RETRO_GREEN)
        self.check_ip()

    def reset_network(self):
        if not messagebox.askyesno("Panic Reset", "Flush iptables, kill Tor, and restart network managers?"):
            return
        self.status_label.config(text="... RESETTING NETWORK...", fg=BLOOD_RED)
        self.remove_transparent_proxy()
        run_cmd(['pkill', '-9', 'tor'], root=True)
        self.set_system_proxy(False)
        for svc in ['NetworkManager', 'dhcpcd', 'systemd-networkd', 'networking']:
            run_cmd(['systemctl', 'restart', svc], root=True)
        self.zombie_active = False
        self.transparent_mode = False
        self.toggle_btn.set_text("ENABLE TORII MODE")
        self.status_label.config(text="Status: OFFLINE", fg=BLOOD_RED)
        messagebox.showinfo("Network Reset", "PANIC COMPLETE\nNetwork interfaces and DNS restored.")
        self.root.after(1500, self.check_ip)
        self.root.after(1500, self.check_vpn_status)

def main():
    root = tk.Tk()
    ToriiApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
