# -*- coding: utf-8 -*-
import os
import re
import json
from datetime import datetime
from urllib.request import Request, urlopen

from Screens.Screen import Screen
from Components.Label import Label
from Components.ScrollLabel import ScrollLabel
from Components.ActionMap import ActionMap



from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.ScrollLabel import ScrollLabel
from enigma import eTimer
import os, re, base64, time, subprocess, json

try:
    from urllib.request import urlopen, Request
except:
    from urllib2 import urlopen, Request

# ---------------- CONFIG ----------------
OSCAM_URL = "http://127.0.0.1:8888/reader.html"
NCAM_URL = "http://127.0.0.1:8181/reader.html"
USER = "admin"
PASS = "password"
CONFIG_BASE = "/etc/tuxbox/config"
BG = "/usr/lib/enigma2/python/Plugins/Extensions/ElieSatPanelGrid/assets/background/panel_bg.jpg"

# ---------------- UTILS ----------------
def run_cmd(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL).decode().strip()
    except:
        return "Unavailable"

def safe_read(file):
    try:
        with open(file) as f:
            return f.read().strip()
    except:
        return "Unknown"

def get_network_info():
    interfaces = ["eth0", "eth1", "wlan0", "ra0"]
    for iface in interfaces:
        base = "/sys/class/net/%s" % iface
        if not os.path.exists(base):
            continue
        mac = safe_read(base + "/address").upper()
        if mac == "00:00:00:00:00:00":
            continue
        state = safe_read(base + "/operstate")
        connected = "Connected" if state == "up" else "Disconnected"
        speed_file = base + "/speed"
        if os.path.exists(speed_file):
            sp = safe_read(speed_file)
            speed = "%s Mb/s" % sp if sp.isdigit() else "Unknown"
        else:
            speed = "Wireless"
        return iface, connected, mac, speed
    return "N/A", "Disconnected", "Unavailable", "Unknown"

def human_speed(bytes_per_sec):
    if bytes_per_sec > 1024*1024:
        return "%.1f MB/s" % (bytes_per_sec/(1024*1024))
    elif bytes_per_sec > 1024:
        return "%.1f KB/s" % (bytes_per_sec/1024)
    else:
        return "%d B/s" % bytes_per_sec

# ============================================================
# MAIN INFOBOX SCREEN
# ============================================================
class Infobox(Screen):
    skin = f"""
<screen name="infobox" position="center,center" size="1920,1080">
<ePixmap position="0,0" size="1920,1080" pixmap="{BG}" zPosition="-10"/>
<eLabel position="0,0" size="1920,130" backgroundColor="#000000" zPosition="10"/>
<eLabel text="● Welcome to ElieSatPanel – Enjoy the best plugins, addons and tools for your E2 box." position="350,20" size="1400,60" font="Bold;32" halign="left" valign="center" foregroundColor="#E6BE3A" backgroundColor="#000000" transparent="0" zPosition="11"/>
<eLabel position="90,110" size="1740,780" backgroundColor="#000000" transparent="0" zPosition="-1"/>
<widget name="list" position="120,140" size="1680,720" font="Console;30" foregroundColor="#E6BE3A" transparent="1" zPosition="5"/>
<eLabel position="0,1020" size="480,40" text="System Monitor" font="Bold;30" halign="center" foregroundColor="#E6BE3A" backgroundColor="#000000" transparent="0"/>
<eLabel position="480,1020" size="480,40" text="IPTV" font="Bold;30" halign="center" foregroundColor="#E6BE3A" backgroundColor="#000000" transparent="0"/>
<eLabel position="960,1020" size="480,40" text="NCam" font="Bold;30" halign="center" foregroundColor="#E6BE3A" backgroundColor="#000000" transparent="0"/>
<eLabel position="1440,1020" size="480,40" text="OSCam" font="Bold;30" halign="center" foregroundColor="#E6BE3A" backgroundColor="#000000" transparent="0"/>
<eLabel position="0,1075" size="480,5" backgroundColor="red" transparent="0" zPosition="10"/>
<eLabel position="480,1075" size="480,5" backgroundColor="green" transparent="0" zPosition="10"/>
<eLabel position="960,1075" size="480,5" backgroundColor="yellow" transparent="0" zPosition="10"/>
<eLabel position="1440,1075" size="480,5" backgroundColor="blue" transparent="0" zPosition="10"/>
</screen>
"""

    def __init__(self, session):
        Screen.__init__(self, session)
        self["list"] = ScrollLabel("")

        self.prev_rx = 0
        self.prev_tx = 0
        self.prev_time = time.time()

        self["actions"] = ActionMap(
            ["OkCancelActions", "DirectionActions", "ColorActions"],
            {
                "cancel": self.close,
                "up": self["list"].pageUp,
                "down": self["list"].pageDown,
                "red": self.openSystemMonitor,
                "green": self.openIPTV,
                "yellow": self.openNCam,
                "blue": self.showOscam
            }
        )

        self.timer = eTimer()
        self.timer.callback.append(self.update_info)
        self.timer.start(1000, True)

        self.update_info()

    def update_info(self):
        lst = []

        lst.append("○ Time & Network")
        lst.append("-" * 35)
        lst.append("• Date & Time : %s" % time.strftime("%Y-%m-%d %H:%M:%S"))
        tz = safe_read("/etc/timezone") if os.path.exists("/etc/timezone") else run_cmd("date +'%Z %z'")
        lst.append("• Time Zone   : %s" % tz)
        local_ip = run_cmd("ip addr show | awk '/inet / && !/127/ {split($2,a,\"/\");print a[1];exit}'")
        lst.append("• Local IP    : %s" % local_ip)
        try:
            pub_ip = urlopen("https://api.ipify.org", timeout=2).read().decode().strip()
        except:
            pub_ip = "Unavailable"
        lst.append("• Public IP   : %s" % pub_ip)
        ping = "Connected" if run_cmd("ping -c2 -w3 8.8.8.8 >/dev/null && echo ok") == "ok" else "Disconnected"
        lst.append("• Internet    : %s" % ping)
        lst.append("")

        lst.append("○ Geolocation")
        lst.append("-" * 35)
        if pub_ip != "Unavailable":
            try:
                info = json.loads(urlopen(f"https://ipinfo.io/{pub_ip}/json", timeout=2).read().decode())
                country = info.get("country", "Unknown")
                region = info.get("region", "Unknown")
                city = info.get("city", "Unknown")
                loc = info.get("loc", "0,0")
                lat, lon = loc.split(",")
                isp = info.get("org", "Unknown")
            except:
                country = region = city = lat = lon = isp = "Unknown"
            lst.append("• Continent : %s" % self.getContinent(country))
            lst.append("• Country   : %s" % country)
            lst.append("• State     : %s" % region)
            lst.append("• City      : %s" % city)
            lst.append("• Latitude  : %s" % lat)
            lst.append("• Longitude : %s" % lon)
            lst.append("• ISP       : %s" % isp)
        lst.append("")

        lst.append("○ System Info")
        lst.append("-" * 35)
        iface, link, mac, speed = get_network_info()
        lst.append("• MAC Address : %s" % mac)
        lst.append("• Link Speed  : %s" % speed)
        rx_file = f"/sys/class/net/{iface}/statistics/rx_bytes"
        tx_file = f"/sys/class/net/{iface}/statistics/tx_bytes"
        try:
            rx = int(safe_read(rx_file))
            tx = int(safe_read(tx_file))
        except:
            rx = tx = 0
        now = time.time()
        dt = max(now - self.prev_time, 1)
        rx_speed = (rx - self.prev_rx)/dt
        tx_speed = (tx - self.prev_tx)/dt
        self.prev_rx = rx
        self.prev_tx = tx
        self.prev_time = now
        lst.append("• RX Speed    : %s" % human_speed(rx_speed))
        lst.append("• TX Speed    : %s" % human_speed(tx_speed))
        lst.append("")

        self["list"].setText("\n".join(lst))

    def getContinent(self, cc):
        mapping = {
            "Asia": ["LB", "AE", "SA", "QA", "KW", "JO", "IQ"],
            "Europe": ["FR", "DE", "IT", "ES", "NL", "GB"],
            "Africa": ["DZ", "EG", "MA", "TN"],
            "North America": ["US", "CA", "MX"]
        }
        for k in mapping:
            if cc in mapping[k]:
                return k
        return "Unknown"

    # ---------------- BUTTON ACTIONS ----------------
    def openSystemMonitor(self): self.session.open(SystemMonitorScreen)
    def openIPTV(self): self.session.open(IptvScreen)
    def openNCam(self): self.session.open(NCamReadersScreen)
    def showOscam(self): self.session.open(OSCamReadersScreen)

# ============================================================
# SYSTEM MONITOR SCREEN
# ============================================================
class SystemMonitorScreen(Screen):
    skin = f"""
<screen name="SystemMonitor" position="center,center" size="1920,1080">
<ePixmap position="0,0" size="1920,1080" pixmap="{BG}" zPosition="-10"/>
<eLabel position="0,0" size="1920,130" backgroundColor="#000000" zPosition="10"/>
<eLabel text="● System monitor" position="350,20" size="1400,60" font="Bold;32" halign="left" valign="center" foregroundColor="#E6BE3A" backgroundColor="#000000" transparent="0" zPosition="11"/>
<eLabel position="90,110" size="1740,780" backgroundColor="#000000" transparent="0" zPosition="-1"/>
<widget name="list" position="120,140" size="1680,720" font="Console;30" foregroundColor="#E6BE3A" transparent="1" zPosition="5"/>

<eLabel position="0,1020" size="480,40" text="System Monitor" font="Bold;30" halign="center" foregroundColor="#E6BE3A" backgroundColor="#000000"/>
<eLabel position="480,1020" size="480,40" text="IPTV" font="Bold;30" halign="center" foregroundColor="#E6BE3A" backgroundColor="#000000"/>
<eLabel position="960,1020" size="480,40" text="NCam" font="Bold;30" halign="center" foregroundColor="#E6BE3A" backgroundColor="#000000"/>
<eLabel position="1440,1020" size="480,40" text="OSCam" font="Bold;30" halign="center" foregroundColor="#E6BE3A" backgroundColor="#000000"/>

<eLabel position="0,1075" size="480,5" backgroundColor="red" zPosition="10"/>
<eLabel position="480,1075" size="480,5" backgroundColor="green" zPosition="10"/>
<eLabel position="960,1075" size="480,5" backgroundColor="yellow" zPosition="10"/>
<eLabel position="1440,1075" size="480,5" backgroundColor="blue" zPosition="10"/>
</screen>
"""

    def __init__(self, session):
        Screen.__init__(self, session)

        self["list"] = ScrollLabel(self.build_text())

        self["actions"] = ActionMap(
            ["OkCancelActions", "DirectionActions", "ColorActions"],
            {
                "cancel": self.close,
                "up": self["list"].pageUp,
                "down": self["list"].pageDown,
                "red": self.openSystemMonitor,
                "green": self.openIPTV,
                "yellow": self.openNCam,
                "blue": self.showOscam
            },
            -1
        )

    # ============================================================
    # UNIVERSAL IMAGE DETECTION
    # ============================================================
    def get_image_info(self):
        try:
            # OpenATV / OE-A
            if os.path.exists("/etc/image-version"):
                name = run_cmd("grep '^distro=' /etc/image-version | cut -d= -f2")
                ver = run_cmd("grep '^version=' /etc/image-version | cut -d= -f2")
                if name:
                    return f"{name} {ver}"

            # OpenPLi
            if os.path.exists("/etc/issue"):
                issue = safe_read("/etc/issue").split("\\n")[0]
                if issue:
                    return issue

            # OpenBlackHole
            if os.path.exists("/etc/bhversion"):
                return f"OpenBlackHole {safe_read('/etc/bhversion')}"

            # fallback using opkg
            opkg = run_cmd("opkg status | grep -i image | head -1")
            if opkg:
                return opkg

        except:
            pass

        return "Unknown Image"

    # ============================================================
    # BUILD SYSTEM TEXT
    # ============================================================
    def build_text(self):

        image = self.get_image_info()
        py = run_cmd("python3 -V | awk '{print $2}'")
        arch = run_cmd("uname -m")
        ker = run_cmd("uname -r")
        model = safe_read("/proc/stb/info/model")
        uptime = run_cmd("uptime -p")
        load = run_cmd("awk '{print $1}' /proc/loadavg")
        temp = run_cmd("cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null | awk '{printf \"%.1fC\",$1/1000}'")
        ram = run_cmd("free -h | awk '/Mem:/ {print $3\" / \"$2}'")
        flash = run_cmd("df -h / | awk 'NR==2 {print $3\" / \"$2}'")

        text = []

        text.append("○ System")
        text.append("-" * 35)
        text.append("• Image Name & Version : %s" % image)
        text.append("• Python              : %s" % py)
        text.append("• Architecture        : %s" % arch)
        text.append("• Kernel              : %s" % ker)
        text.append("")

        text.append("○ Hardware")
        text.append("-" * 35)
        text.append("• Model     : %s" % model)
        text.append("• Uptime    : %s" % uptime)
        text.append("• CPU Temp  : %s" % temp)
        text.append("• CPU Load  : %s" % load)
        text.append("")

        text.append("○ Resources")
        text.append("-" * 35)
        text.append("• RAM Usage   : %s" % ram)
        text.append("• Flash Usage : %s" % flash)

        return "\n".join(text)

    # ============================================================
    # BUTTON ACTIONS
    # ============================================================

    def openSystemMonitor(self):
        self.session.open(SystemMonitorScreen)

    def openIPTV(self):
        self.session.open(IptvScreen)

    def openNCam(self):
        self.session.open(NCamReadersScreen)

    def showOscam(self):
        self.session.open(OSCamReadersScreen)

# ============================================================
# OSCAM READERS SCREEN
# ============================================================
CONFIG_BASE = "/etc/tuxbox/config"

class OSCamReadersScreen(Screen):

    skin = """
<screen name="OscamReadersScreen" position="center,center" size="1920,1080">
<ePixmap position="0,0" size="1920,1080" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/ElieSatPanelGrid/assets/background/panel_bg.jpg" zPosition="-10"/>
<eLabel position="0,0" size="1920,130" backgroundColor="#000000" zPosition="10"/>
<eLabel text="● Oscam readers monitor" position="350,20" size="1400,60" font="Bold;32" halign="left" valign="center" foregroundColor="#E6BE3A" backgroundColor="#000000" transparent="0" zPosition="11"/>
<eLabel position="90,120" size="1740,780" backgroundColor="#000000" zPosition="-1"/>
<eLabel text=" Label                │ADDRESS                    │PORT      │PROTOCOL      │STATUS" position="100,150" size="1720,40" font="Console;30" foregroundColor="#E6BE3A" backgroundColor="#000000" zPosition="6"/>
<eLabel text="────────────────────────────────────────────────────────────────────────────────────" position="100,185" size="1720,40" font="Console;30" foregroundColor="#E6BE3A" backgroundColor="#000000" zPosition="6"/>
<widget name="list" position="100,225" size="1720,625" font="Console;30" foregroundColor="#E6BE3A" transparent="1" zPosition="5" scrollbarMode="showOnDemand"/>
<widget name="error" position="0,225" size="1920,625" font="Bold;44" halign="center" valign="center" foregroundColor="#FF0000" transparent="1" zPosition="7"/>
<eLabel position="0,1015" size="1920,50" backgroundColor="#000000" zPosition="9"/>
<eLabel position="0,1020" size="480,40" text="System Monitor" font="Bold;30" halign="center" foregroundColor="#E6BE3A" backgroundColor="#000000" transparent="0" zPosition="11"/>
<eLabel position="480,1020" size="480,40" text="IPTV" font="Bold;30" halign="center" foregroundColor="#E6BE3A" backgroundColor="#000000" transparent="0" zPosition="11"/>
<eLabel position="960,1020" size="480,40" text="NCam" font="Bold;30" halign="center" foregroundColor="#E6BE3A" backgroundColor="#000000" transparent="0" zPosition="11"/>
<eLabel position="1440,1020" size="480,40" text="OSCam" font="Bold;30" halign="center" foregroundColor="#E6BE3A" backgroundColor="#000000" transparent="0" zPosition="11"/>
<eLabel position="0,1075" size="480,5" backgroundColor="red" zPosition="12"/>
<eLabel position="480,1075" size="480,5" backgroundColor="green" zPosition="12"/>
<eLabel position="960,1075" size="480,5" backgroundColor="yellow" zPosition="12"/>
<eLabel position="1440,1075" size="480,5" backgroundColor="blue" zPosition="12"/>
<widget name="title" position="0,950" size="1920,50" font="Bold;28" halign="center" foregroundColor="#E6BE3A" transparent="1" zPosition="11"/>
</screen>
"""

    def __init__(self, session):
        Screen.__init__(self, session)

        self["title"] = Label("OSCam Readers Status")
        self["list"] = ScrollLabel("")
        self["error"] = Label("")

        self["actions"] = ActionMap(
            ["OkCancelActions", "DirectionActions"],
            {
                "cancel": self.close,
                "up": self["list"].pageUp,
                "down": self["list"].pageDown,
            },
        )

        self.reload()

    def getConfigPath(self):

        try:
            for pid in os.listdir("/proc"):
                if not pid.isdigit():
                    continue

                cmdline_path = os.path.join("/proc", pid, "cmdline")
                if not os.path.exists(cmdline_path):
                    continue

                cmdline = open(cmdline_path, "rb").read().decode("utf-8", "ignore")

                if "oscam" in cmdline.lower():
                    parts = cmdline.split("\x00")

                    for i, part in enumerate(parts):
                        if part == "-c" and i + 1 < len(parts):
                            config_dir = parts[i + 1]
                            candidate = os.path.join(config_dir, "oscam.server")
                            if os.path.exists(candidate):
                                return candidate
        except:
            pass

        if not os.path.exists(CONFIG_BASE):
            return None

        root_candidate = os.path.join(CONFIG_BASE, "oscam.server")
        if os.path.exists(root_candidate):
            return root_candidate

        for root, dirs, files in os.walk(CONFIG_BASE):
            if "oscam.server" in files:
                return os.path.join(root, "oscam.server")

        return None

    def fit(self, text, width):
        text = str(text)
        if len(text) > width:
            return text[:width - 1] + "…"
        return text.ljust(width)

    def colorStatus(self, status, proto):
        s = status.lower()
        if proto == "emu":
            return "\\c0000FF00CardOK\\c00E6BE3A"
        if s == "connected":
            return "\\c0000FF00connected\\c00E6BE3A"
        if s == "off":
            return "\\c00FF0000Off\\c00E6BE3A"
        return status

    def fetchWebif(self):
        try:
            auth = base64.b64encode(("%s:%s" % (USER, PASS)).encode()).decode()
            req = Request(OSCAM_URL)
            req.add_header("Authorization", "Basic %s" % auth)
            return urlopen(req, timeout=5).read().decode("utf-8", "ignore")
        except:
            pass
        try:
            req = Request(OSCAM_URL)
            return urlopen(req, timeout=5).read().decode("utf-8", "ignore")
        except:
            return ""

    def parseServer(self):

        readers = []
        config_path = self.getConfigPath()
        if not config_path:
            return readers

        reader = ""
        host = "-"
        port = "-"
        proto = "-"
        status = "ON"

        def push():
            if reader:
                readers.append({
                    "label": reader,
                    "host": host,
                    "port": port,
                    "proto": proto.lower(),
                    "status": status
                })

        for raw in open(config_path):
            line = raw.strip()
            if line.startswith("[reader]"):
                push()
                reader, host, port, proto, status = "", "-", "-", "-", "ON"
            elif line.startswith("label"):
                reader = line.split("=",1)[1].strip()
            elif line.startswith("protocol"):
                proto = line.split("=",1)[1].strip()
            elif line.startswith("device"):
                parts = line.split("=",1)[1].split(",")
                host = parts[0].strip()
                if len(parts) > 1:
                    port = parts[1].strip()
            elif line.startswith("enable"):
                if line.split("=")[1].strip() == "0":
                    status = "OFF"

        push()
        return readers

    def detectStatus(self, html, reader):

        proto = reader["proto"]

        if reader["status"] == "OFF":
            state = "Unreachable"
            priority = 3
        elif not html:
            state = "Unknown"
            priority = 4
        else:
            block = re.search(r">" + re.escape(reader["label"]) + r"<.*?</tr>", html, re.I | re.S)
            if not block:
                state = "Unknown"
                priority = 4
            else:
                info = block.group(0).lower()
                if "cardok" in info:
                    state = "CardOK"
                    priority = 1
                elif "connected" in info:
                    state = "Connected"
                    priority = 2
                elif "online" in info:
                    state = "Off"
                    priority = 3
                elif "offline" in info or "error" in info or "disconnected" in info:
                    state = "Unreachable"
                    priority = 4
                else:
                    state = "Unknown"
                    priority = 4

        if proto in ("cccam", "newcamd", "mgcamd"):
            priority += 10

        return state, priority

    def reload(self):

        readers = self.parseServer()
        html = self.fetchWebif()

        if not html:
            self["list"].setText("")
            self["error"].setText("OSCam WebIF Unreachable")
            return
        else:
            self["error"].setText("")

        rows = []

        W_READER = 22
        W_ADDRESS = 27
        W_PORT = 10
        W_PROTOCOL = 14

        for r in readers:
            status, prio = self.detectStatus(html, r)
            colored_status = self.colorStatus(status, r["proto"])

            line = "{}│{}│{}│{}│{}".format(
                self.fit(r["label"], W_READER),
                self.fit(r["host"], W_ADDRESS),
                self.fit(r["port"], W_PORT),
                self.fit(r["proto"], W_PROTOCOL),
                colored_status
            )

            rows.append((status.lower(), line))

        # Only change: CardOK → Connected → Off → rest
        sort_order = {"cardok": 1, "connected": 2, "off": 3}
        rows.sort(key=lambda x: sort_order.get(x[0], 4))

        lines = [""]
        lines.extend(row for _, row in rows)

        self["list"].setText("\n".join(lines))


class NCamReadersScreen(Screen):
    skin = """
<screen name="NCamReadersScreen" position="center,center" size="1920,1080">
<ePixmap position="0,0" size="1920,1080" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/ElieSatPanelGrid/assets/background/panel_bg.jpg" zPosition="-10"/>
<eLabel position="0,0" size="1920,130" backgroundColor="#000000" zPosition="10"/>
<eLabel text="● Ncam readers monitor" position="350,20" size="1400,60" font="Bold;32" halign="left" valign="center" foregroundColor="#E6BE3A" backgroundColor="#000000" transparent="0" zPosition="11"/>
<eLabel position="90,120" size="1740,780" backgroundColor="#000000" zPosition="-1"/>
<eLabel text=" Label                │ADDRESS                    │PORT      │PROTOCOL      │STATUS" position="100,150" size="1720,40" font="Console;30" foregroundColor="#E6BE3A" backgroundColor="#000000" zPosition="6"/>
<eLabel text="────────────────────────────────────────────────────────────────────────────────────" position="100,185" size="1720,40" font="Console;30" foregroundColor="#E6BE3A" backgroundColor="#000000" zPosition="6"/>
<widget name="list" position="100,225" size="1720,625" font="Console;30" foregroundColor="#E6BE3A" transparent="1" zPosition="5" scrollbarMode="showOnDemand"/>
<widget name="error" position="0,225" size="1920,625" font="Bold;44" halign="center" valign="center" foregroundColor="#FF0000" transparent="1" zPosition="7"/>
<widget name="title" position="0,950" size="1920,50" font="Bold;28" halign="center" foregroundColor="#E6BE3A" transparent="1"/>
<eLabel position="0,1020" size="480,40" text="System Monitor" font="Bold;30" halign="center" foregroundColor="#E6BE3A" backgroundColor="#000000" transparent="0"/>
<eLabel position="480,1020" size="480,40" text="IPTV" font="Bold;30" halign="center" foregroundColor="#E6BE3A" backgroundColor="#000000" transparent="0"/>
<eLabel position="960,1020" size="480,40" text="NCam" font="Bold;30" halign="center" foregroundColor="#E6BE3A" backgroundColor="#000000" transparent="0"/>
<eLabel position="1440,1020" size="480,40" text="OSCam" font="Bold;30" halign="center" foregroundColor="#E6BE3A" backgroundColor="#000000" transparent="0"/>
<eLabel position="0,1075" size="480,5" backgroundColor="red" zPosition="12"/>
<eLabel position="480,1075" size="480,5" backgroundColor="green" zPosition="12"/>
<eLabel position="960,1075" size="480,5" backgroundColor="yellow" zPosition="12"/>
<eLabel position="1440,1075" size="480,5" backgroundColor="blue" zPosition="12"/>
</screen>
"""

    NCAM_URL = "http://127.0.0.1:8181/reader.html"

    def __init__(self, session):
        Screen.__init__(self, session)
        self["title"] = Label("NCam Readers Status")
        self["list"] = ScrollLabel("")
        self["error"] = Label("")

        self["actions"] = ActionMap(
            ["OkCancelActions","DirectionActions"],
            {
                "cancel": self.close,
                "up": self["list"].pageUp,
                "down": self["list"].pageDown,
            }
        )

        self.reload()

    # ----------------------- CONFIG PATH -----------------------
    def getConfigPath(self):
        try:
            for pid in os.listdir("/proc"):
                if not pid.isdigit():
                    continue
                cmdline_path = os.path.join("/proc", pid, "cmdline")
                if not os.path.exists(cmdline_path):
                    continue
                cmdline = open(cmdline_path,"rb").read().decode("utf-8","ignore")
                if "ncam" in cmdline.lower():
                    parts = cmdline.split("\x00")
                    for i, part in enumerate(parts):
                        if part == "-c" and i + 1 < len(parts):
                            config_dir = parts[i+1]
                            candidate = os.path.join(config_dir,"ncam.server")
                            if os.path.exists(candidate):
                                return candidate
        except:
            pass

        root_candidate = os.path.join(CONFIG_BASE,"ncam.server")
        if os.path.exists(root_candidate):
            return root_candidate

        for root, dirs, files in os.walk(CONFIG_BASE):
            if "ncam.server" in files:
                return os.path.join(root,"ncam.server")
        return None

    def fit(self, text, width):
        text = str(text)
        if len(text) > width:
            return text[:width-1]+"…"
        return text.ljust(width)

    def colorStatus(self, status, proto):
        s = status.lower()
        if s == "cardok":
            return "\\c0000FF00CardOK\\c00E6BE3A"
        if s == "connected":
            return "\\c0000FF00connected\\c00E6BE3A"
        if s == "off":
            return "\\c00FF0000Off\\c00E6BE3A"
        return status

    def fetchWebif(self):
        try:
            req = Request(self.NCAM_URL)
            return urlopen(req, timeout=5).read().decode("utf-8","ignore")
        except:
            return ""

    def parseServer(self):
        readers = []
        config_path = self.getConfigPath()
        if not config_path:
            return readers

        reader = ""
        host = "-"
        port = "-"
        proto = "-"
        status = "ON"

        def push():
            if reader:
                readers.append({
                    "label": reader,
                    "host": host,
                    "port": port,
                    "proto": proto.lower(),
                    "status": status
                })

        for raw in open(config_path):
            line = raw.strip()
            if line.startswith("[reader]"):
                push()
                reader, host, port, proto, status = "", "-", "-", "-", "ON"
            elif line.startswith("label"):
                reader = line.split("=",1)[1].strip()
            elif line.startswith("protocol"):
                proto = line.split("=",1)[1].strip()
            elif line.startswith("device"):
                parts = line.split("=",1)[1].split(",")
                host = parts[0].strip()
                if len(parts) > 1:
                    port = parts[1].strip()
            elif line.startswith("enable"):
                if line.split("=")[1].strip() == "0":
                    status = "OFF"
        push()
        return readers

    def detectStatus(self, html, reader):
        proto = reader["proto"]
        if reader["status"] == "OFF":
            return "Off", 3
        if not html:
            return "Unknown", 4

        block = re.search(r">"+re.escape(reader["label"])+r"<.*?</tr>", html, re.I|re.S)
        if not block:
            return "Unknown", 4

        info = block.group(0).lower()

        if proto == "emu" or "cardok" in info:
            state = "CardOK"
            priority = 1
        elif "connected" in info:
            state = "connected"
            priority = 2
        elif "offline" in info or "error" in info or "disconnected" in info:
            state = "Unreachable"
            priority = 4
        elif "online" in info:
            state = "Off"
            priority = 3
        else:
            state = "Unknown"
            priority = 4

        return state, priority

    def reload(self):
        readers = self.parseServer()
        html = self.fetchWebif()

        if not html:
            self["list"].setText("")
            self["error"].setText("NCam WebIF Unreachable")
            return
        else:
            self["error"].setText("")

        rows = []

        W_READER = 22
        W_ADDRESS = 27
        W_PORT = 10
        W_PROTOCOL = 14

        for r in readers:
            status, prio = self.detectStatus(html, r)
            colored_status = self.colorStatus(status, r["proto"])

            line = "{}│{}│{}│{}│{}".format(
                self.fit(r["label"], W_READER),
                self.fit(r["host"], W_ADDRESS),
                self.fit(r["port"], W_PORT),
                self.fit(r["proto"], W_PROTOCOL),
                colored_status
            )

            rows.append((prio, line))

        # Sort by priority: CardOK → connected → Off → others
        rows.sort(key=lambda x: x[0])
        lines = [""] + [row for _, row in rows]
        self["list"].setText("\n".join(lines))


class IptvScreen(Screen):

    skin = """
<screen name="IptvScreen" position="center,center" size="1920,1080">
<ePixmap position="0,0" size="1920,1080" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/ElieSatPanelGrid/assets/background/panel_bg.jpg" zPosition="-10"/>
<eLabel position="0,0" size="1920,130" backgroundColor="#000000" zPosition="10"/>
<eLabel text="● IPTV servers monitor" position="350,20" size="1400,60" font="Bold;32" halign="left" valign="center" foregroundColor="#E6BE3A" backgroundColor="#000000" zPosition="11"/>
<eLabel position="90,120" size="1740,780" backgroundColor="#000000" zPosition="-1"/>
<eLabel text=" SERVER                     │PLUGIN              │EXPIRES     │ACT  │MAX  │STATUS"
position="100,150" size="1720,40" font="Console;30" foregroundColor="#E6BE3A" backgroundColor="#000000"/>
<eLabel text="────────────────────────────────────────────────────────────────────────────"
position="100,185" size="1720,40" font="Console;30" foregroundColor="#E6BE3A"/>
<widget name="list" position="100,225" size="1720,625" font="Console;30"
foregroundColor="#E6BE3A" transparent="1" scrollbarMode="showOnDemand"/>
<widget name="error" position="0,225" size="1920,625" font="Bold;44"
halign="center" valign="center" foregroundColor="#FF0000" transparent="1"/>
<widget name="title" position="0,950" size="1920,50"
font="Bold;28" halign="center" foregroundColor="#E6BE3A" transparent="1"/>
<eLabel position="0,1020" size="480,40" text="System Monitor" font="Bold;30" halign="center" foregroundColor="#E6BE3A" backgroundColor="#000000" transparent="0"/>
<eLabel position="480,1020" size="480,40" text="IPTV" font="Bold;30" halign="center" foregroundColor="#E6BE3A" backgroundColor="#000000" transparent="0"/>
<eLabel position="960,1020" size="480,40" text="NCam" font="Bold;30" halign="center" foregroundColor="#E6BE3A" backgroundColor="#000000" transparent="0"/>
<eLabel position="1440,1020" size="480,40" text="OSCam" font="Bold;30" halign="center" foregroundColor="#E6BE3A" backgroundColor="#000000" transparent="0"/>
<eLabel position="0,1075" size="480,5" backgroundColor="red" zPosition="12"/>
<eLabel position="480,1075" size="480,5" backgroundColor="green" zPosition="12"/>
<eLabel position="960,1075" size="480,5" backgroundColor="yellow" zPosition="12"/>
<eLabel position="1440,1075" size="480,5" backgroundColor="blue" zPosition="12"/>
</screen>
"""

    BASE_DIR = "/etc/enigma2"

    def __init__(self, session):
        Screen.__init__(self, session)

        self["title"] = Label("IPTV Servers Status")
        self["list"] = ScrollLabel("")
        self["error"] = Label("")

        self["actions"] = ActionMap(
            ["OkCancelActions","DirectionActions"],
            {
                "cancel": self.close,
                "up": self["list"].pageUp,
                "down": self["list"].pageDown,
            }
        )

        self.reload()

    def fit(self, text, width):
        text = str(text)
        if len(text) > width:
            return text[:width-1] + "…"
        return text.ljust(width)

    def queryApi(self, host, user, password):
        url = "http://{}/player_api.php?username={}&password={}".format(host, user, password)
        try:
            req = Request(url, headers={"User-Agent":"XStreamity-Monitor"})
            data = urlopen(req, timeout=5).read().decode("utf-8","ignore")
            return json.loads(data)
        except:
            return None

    def parsePlaylists(self):
        rows = []
        for root, dirs, files in os.walk(self.BASE_DIR):
            if "playlists.txt" not in files:
                continue

            playlist = os.path.join(root,"playlists.txt")
            plugin = "default"
            if root != self.BASE_DIR:
                plugin = os.path.basename(root)

            try:
                lines = open(playlist).read().splitlines()
            except:
                continue

            for line in lines:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                user = re.search(r'username=([^&]+)', line)
                password = re.search(r'password=([^&]+)', line)
                host = re.search(r'://([^/]+)', line)

                if not user or not password or not host:
                    continue

                user = user.group(1)
                password = password.group(1)
                host = host.group(1)

                api = self.queryApi(host,user,password)

                status = "Unknown"
                expires = "-"
                active = "0"
                maxc = "0"

                if api:
                    info = api.get("user_info",{})
                    status = info.get("status","Unknown")
                    active = str(info.get("active_cons","0"))
                    maxc = str(info.get("max_connections","0"))
                    exp = info.get("exp_date")
                    if exp:
                        try:
                            expires = datetime.fromtimestamp(int(exp)).strftime("%d-%m-%Y")
                        except:
                            pass
                else:
                    status = "No Reply"

                rows.append({
                    "host":host,
                    "plugin":plugin,
                    "expires":expires,
                    "active":active,
                    "max":maxc,
                    "status":status
                })

        return rows

    def colorStatus(self, status):
        s = status.lower()
        if s == "active":
            return "\\c0000FF00Active\\c00E6BE3A"
        if s == "no reply":
            return "\\c00FF0000No Reply\\c00E6BE3A"
        return status

    def buildTable(self, rows):
        # column widths, PLUGIN increased
        W_HOST = 28
        W_PLUGIN = 20   # widened
        W_EXP = 12
        W_ACTIVE = 5
        W_MAX = 5

        formatted = []

        for r in rows:
            status = self.colorStatus(r["status"])
            host = self.fit(r["host"], W_HOST)
            plugin = self.fit(r["plugin"], W_PLUGIN)
            exp = self.fit(r["expires"], W_EXP)
            active = self.fit(r["active"], W_ACTIVE)
            maxc = self.fit(r["max"], W_MAX)

            line = "{}│{}│{}│{}│{}│{}".format(
                host,
                plugin,
                exp,
                active,
                maxc,
                status
            )

            priority = 3
            if r["status"] == "Active":
                priority = 1
            elif r["status"] == "No Reply":
                priority = 2

            formatted.append((priority,line))

        formatted.sort(key=lambda x: x[0])
        return "\n".join([row for _,row in formatted])

    def reload(self):
        rows = self.parsePlaylists()
        if not rows:
            self["list"].setText("")
            self["error"].setText("No IPTV playlists found")
            return

        self["error"].setText("")
        table = self.buildTable(rows)
        self["list"].setText("\n" + table)
