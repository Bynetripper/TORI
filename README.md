
1. **VPN Detection** – Scans for active VPN interfaces (`tun0`, `wg0`, `ppp0`, etc.) and known VPN processes to confirm whether a VPN tunnel is already established before Tor is layered on top.

2. **Tor Activation** – Starts the local Tor service and ensures the SOCKS5 proxy is listening on `127.0.0.1:9050`.

3. **Routing Mode Selection** – Applies one of two routing strategies:
   - **SOCKS5 Proxy Mode** – Configures the system proxy (and compatible browsers) to route traffic through Tor's local SOCKS5 port. Ideal for browser-only anonymity via FoxyProxy or TORI's built-in browser launcher.
   - **Transparent Tor Mode** – Rewrites `iptables` rules to redirect all TCP and DNS traffic through Tor's `TransPort` and `DNSPort`, enforcing system-wide Tor routing without per-app configuration.

4. **IP Verification** – Queries external IP intelligence services to display your current public IP, geolocation, and ISP/organization, confirming whether traffic is exiting through a Tor relay or your real address.

5. **Browser Launching** – Spawns isolated browser profiles (Firefox, Chrome/Chromium, or Tor Browser) pre-configured to route through Tor's SOCKS5 proxy with remote DNS resolution enabled.

6. **Panic / Reset** – Instantly flushes all Tor firewall rules, kills the Tor process, removes proxy settings, restarts NetworkManager, and restores default networking.

---

## Features

- **Minimal Dark / ASCII GUI** – Clean, distraction-free interface built with Tkinter. No web frameworks, no heavy dependencies, no bloat.
- **Active VPN Detection** – Automatically identifies whether a VPN tunnel is live before layering Tor, helping enforce a VPN → Tor chain.
- **Real-Time IP / Location / ISP Check** – Displays your public-facing IP address, approximate geolocation, and hosting organization so you can verify routing at a glance.
- **Dual Tor Routing Modes**
  - **SOCKS5 Proxy Mode** – Application-level routing through `127.0.0.1:9050`. Best for browser-only anonymity.
  - **Transparent Tor Mode** – System-wide traffic redirection using `iptables`, Tor `TransPort`, and Tor `DNSPort`. No per-app proxy setup required.
- **One-Click Browser Launcher** – Opens Firefox, Chrome/Chromium, or Tor Browser in isolated profiles pre-configured for Tor SOCKS5 with remote DNS.
- **FoxyProxy-Compatible** – Works seamlessly with FoxyProxy Standard for granular, per-site proxy rules inside Firefox.
- **Network Panic / Reset Button** – One click to flush Tor rules, stop Tor, clear proxy settings, and restore normal networking.
- **Built-In About / Info Panel** – Expandable dropdown containing usage instructions, SOCKS5 + FoxyProxy setup guidance, and a privacy disclaimer.
- **Multi-Level Privacy Support** – Designed to work on top of an active VPN, creating a `You → VPN → Tor → Destination` chain.

---

## Requirements

### Core

```bash
python3          # Python 3.x runtime
python3-tk       # Tkinter GUI framework
tor              # Tor daemon for SOCKS5 and transparent routing
curl             # IP verification and HTTP checks
