<img width="549" height="503" alt="image" src="https://github.com/user-attachments/assets/9803b6b6-5c42-4ad6-8f01-c433712d869b" />
<img width="398" height="544" alt="image" src="https://github.com/user-attachments/assets/dfef5831-619f-40f7-94c9-4f1a53555e2d" />


# ⛩ TORII - Anonymity Routing & Proxy Manager

**TORII** is a minimalist, dark-themed Python GUI tool designed to manage Tor routing and proxy configurations. Built with simplicity and security in mind, it provides a clean interface to toggle between SOCKS5 and Transparent proxy modes, manage exit node exclusions, and monitor your network status.

Optimized for **Debian** and **Raspberry Pi OS**.

---

## ✨ Features

- **Dual Routing Modes**: Seamlessly switch between **SOCKS5** (App-level) and **Transparent** (System-wide via iptables) proxy modes.
- **Exit Node Control**: Built-in checkboxes to easily **Avoid USA** or **Avoid Europe** exit nodes by dynamically configuring `/etc/tor/torrc`.
- **Minimalist UI**: Ultra-clean, centered dark-mode interface with glowing interactive buttons. No clutter, just the essentials.
- **Tor Control Port Integration**: Instantly request new circuits and monitor active Tor circuits without restarting the daemon.
- **VPN Detection**: Automatically detects active VPN interfaces (OpenVPN, WireGuard, etc.) to prevent routing conflicts.
- **Panic Reset**: One-click network reset to flush iptables, kill Tor, and restore default DNS/network settings.
- **Dependency Installer**: Built-in tool to automatically install required system packages (`tor`, `curl`, `iptables`, etc.).

---

## 📋 Prerequisites

Before running TORII, ensure you have the following installed on your system:

- **Python 3.7+**
- **python3-tk** (Tkinter)
- **Tor** (`tor`)
- **curl**
- **iptables**

---

## 🚀 Installation & Setup

### 1. Install System Dependencies
If you are on a Debian-based system (Ubuntu, Raspberry Pi OS, Kali, etc.), you can install all required dependencies using the built-in installer in the Settings menu, or via the terminal:

```bash
sudo apt update
sudo apt install -y tor curl iptables python3-tk network-manager

