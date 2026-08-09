from Plugins.Extensions.ElieSatPanelGrid.menus.Cccamadder.Softcamfile import Softcamfile
from Plugins.Extensions.ElieSatPanelGrid.menus.Cccamadder.Logfile import Logfile

# -*- coding: utf-8 -*-

import os
import re
import base64
import subprocess
from datetime import datetime
from urllib.request import Request, urlopen
from enigma import getDesktop

from Screens.Screen import Screen
from Components.Label import Label
from Components.MenuList import MenuList
from Components.ActionMap import ActionMap
from Screens.MessageBox import MessageBox

from Plugins.Extensions.ElieSatPanelGrid.__init__ import Version

CONFIG_BASE = "/etc/tuxbox/config"


def decrypt_payload(incoming_data, key=None):
    try:
        cleaned_data = incoming_data.strip()
        decoded_bytes = base64.b64decode(cleaned_data)
        decoded_text = decoded_bytes.decode('utf-8')
        if all(c.isspace() or (32 <= ord(c) <= 126) for c in decoded_text[:50]):
            return decoded_text
    except Exception:
        pass
    return incoming_data


class Showstatus(Screen):

    width, height = getDesktop(0).size().width(), getDesktop(0).size().height()
    skin_file = (
        "/usr/lib/enigma2/python/Plugins/Extensions/ElieSatPanelGrid/menus/Cccamadder/Showstatus_fhd.xml"
        if width >= 1920
        else "/usr/lib/enigma2/python/Plugins/Extensions/ElieSatPanelGrid/menus/Cccamadder/Showstatus_hd.xml"
    )
    try:
        with open(skin_file, "r") as f:
            skin = f.read()
    except Exception as e:
        print(f"[ElieSatPanel] Failed to load skin: {e}")
        skin = "<screen></screen>"

    def __init__(self, session):
        Screen.__init__(self, session)

        self["title"] = Label(_("Readers Status"))
        self["list"] = MenuList([])
        self["error"] = Label("")
        self["exp_date"] = Label("")

        self.list_data = []

        self["left_bar"] = Label("\n".join(list("Version " + Version)))
        self["right_bar"] = Label("\n".join(list("By ElieSat")))
        self["red"] = Label(_("Delete Reader"))
        self["yellow"] = Label(_("Show Softcam File"))
        self["blue"] = Label(_("Show Log File"))
        self["green"] = Label(_("Toggle Status"))

        self["actions"] = ActionMap(
            ["OkCancelActions", "DirectionActions", "ColorActions"],
            {
                "cancel": self.close,
                "ok": self.showDetails,
                "up": self.up,
                "down": self.down,
                "red": self.deleteReaderPrompt,
                "green": self.toggleReaderStatus,
                "yellow": self.openSoftcamFile,
                "blue": self.openLogFile,
            },
        )

        self["list"].onSelectionChanged.append(self.updateExpDate)

        self.reload()

    def up(self):
        self["list"].selectPrevious()

    def down(self):
        self["list"].selectNext()

    def openSoftcamFile(self):
        self.session.open(Softcamfile)

    def openLogFile(self):
        self.session.open(Logfile)

    def getEmuDetails(self):
        emu_type = "oscam"
        cfg_dir = CONFIG_BASE
        cfg_file = None

        try:
            for pid in os.listdir("/proc"):
                if not pid.isdigit():
                    continue

                cmd = os.path.join("/proc", pid, "cmdline")
                if not os.path.exists(cmd):
                    continue

                data = open(cmd, "rb").read().decode("utf-8", "ignore").lower()

                if "ncam" in data:
                    emu_type = "ncam"
                elif "oscam" in data:
                    emu_type = "oscam"
                else:
                    continue

                parts = data.split("\x00")
                for i, p in enumerate(parts):
                    if p == "-c" and i + 1 < len(parts):
                        cfg_dir = parts[i + 1]
                        break
                break
        except Exception:
            pass

        target_server = f"{emu_type}.server"
        possible_cfg = os.path.join(cfg_dir, target_server)
        if os.path.exists(possible_cfg):
            cfg_file = possible_cfg
        else:
            for alt_emu in [emu_type, "oscam", "ncam"]:
                chk = os.path.join(CONFIG_BASE, f"{alt_emu}.server")
                if os.path.exists(chk):
                    cfg_file = chk
                    emu_type = alt_emu
                    cfg_dir = CONFIG_BASE
                    break

        port = "8181" if emu_type == "ncam" else "8888"
        user = "admin"
        pwd = "password"

        conf_file = os.path.join(cfg_dir, f"{emu_type}.conf")
        if not os.path.exists(conf_file):
            conf_file = os.path.join(CONFIG_BASE, f"{emu_type}.conf")

        if os.path.exists(conf_file):
            try:
                in_webif = False
                with open(conf_file, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("[") and line.endswith("]"):
                            in_webif = (line.lower() == "[webif]")
                            continue
                        if in_webif and "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip().lower()
                            v = v.strip()
                            if k in ("httpport", "port"):
                                port_match = re.search(r"\d+", v)
                                if port_match:
                                    port = port_match.group(0)
                            elif k in ("httpuser", "user"):
                                user = v
                            elif k in ("httppwd", "httppassword", "pwd"):
                                pwd = v
            except Exception:
                pass

        webif_url = f"http://127.0.0.1:{port}/reader.html"
        return emu_type, cfg_file, webif_url, user, pwd

    def getConfigPath(self):
        _, cfg_file, _, _, _ = self.getEmuDetails()
        return cfg_file

    def fit(self, text, width):
        text = str(text)
        if len(text) > width:
            return text[:width - 1] + "…"
        return text.ljust(width)

    def makeRow(self, label, host, port, proto, status):
        return (
            f"{self.fit(label, 24)} │ "
            f"{self.fit(host, 25)} │ "
            f"{self.fit(port, 8)} │ "
            f"{self.fit(proto, 12)} │ "
            f"{status}"
        )

    def fetchExpiryData(self):
        expiry_map = {}

        try:
            url_file1 = "https://www.dropbox.com/scl/fi/ve2w5xkrqsxhaienq8tf2/server-eagle?rlkey=g915654fu7rqoizbror90itdt&st=898xqyye&dl=1"
            req1 = Request(url_file1, headers={'User-Agent': 'Mozilla/5.0'})
            raw_payload1 = urlopen(req1, timeout=8).read().decode('utf-8', 'ignore')
            content1 = decrypt_payload(raw_payload1)

            current_user = None
            current_exp = None

            for line in content1.splitlines():
                line = line.strip()
                if not line or line.startswith("#") or line.startswith(";"):
                    continue

                if line.startswith("["):
                    if current_user and current_exp:
                        expiry_map[current_user] = current_exp
                    current_user = None
                    current_exp = None
                    continue

                if "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip().lower()
                    val = val.strip()
                    if key == "user":
                        current_user = val
                    elif key == "expdate":
                        current_exp = val

            if current_user and current_exp:
                expiry_map[current_user] = current_exp

        except Exception as e:
            print(f"[ElieSatPanel] Dropbox expiration fetch error: {e}")

        try:
            url_file2 = "https://raw.githubusercontent.com/omarsat7788/SERVER_EAGLE_SAT/refs/heads/users_expdate/users_expdate.txt"
            req2 = Request(url_file2, headers={'User-Agent': 'Mozilla/5.0'})
            raw_payload2 = urlopen(req2, timeout=8).read().decode('utf-8', 'ignore')
            content2 = decrypt_payload(raw_payload2)

            for line in content2.splitlines():
                line = line.strip()
                if not line or line.startswith("#") or line.startswith(";"):
                    continue

                if "user:" in line.lower() and "expdate:" in line.lower():
                    try:
                        parts_user = line.split("user:", 1)[1]
                        user_segment = parts_user.split("expdate:", 1)[0].strip()
                        date_segment = parts_user.split("expdate:", 1)[1].strip()

                        if user_segment and date_segment:
                            expiry_map[user_segment] = date_segment
                    except Exception as line_err:
                        print(f"[ElieSatPanel] Error parsing GitHub expiry line: {line_err}")

        except Exception as e:
            print(f"[ElieSatPanel] GitHub expiration fetch error: {e}")

        return expiry_map

    def fetchWebif(self, webif_url, user, pwd):
        try:
            auth = base64.b64encode(f"{user}:{pwd}".encode()).decode()
            req = Request(webif_url)
            req.add_header("Authorization", f"Basic {auth}")
            return urlopen(req, timeout=5).read().decode("utf-8", "ignore")
        except Exception:
            try:
                return urlopen(webif_url, timeout=5).read().decode("utf-8", "ignore")
            except Exception:
                return ""

    def parseServer(self, cfg_path):
        readers = []
        if not cfg_path or not os.path.exists(cfg_path):
            return readers

        r, h, p, pr, st = "", "-", "-", "-", "ON"
        u, pw = "-", "-"

        def push():
            if r:
                readers.append({
                    "label": r,
                    "host": h,
                    "port": p,
                    "proto": pr.lower(),
                    "status": st,
                    "user": u,
                    "pass": pw,
                })

        for line in open(cfg_path):
            line = line.strip()

            if line.startswith("[reader]"):
                push()
                r, h, p, pr, st = "", "-", "-", "-", "ON"
                u, pw = "-", "-"

            elif line.startswith("label"):
                r = line.split("=", 1)[1].strip()

            elif line.startswith("protocol"):
                pr = line.split("=", 1)[1].strip()

            elif line.startswith("device"):
                parts = line.split("=", 1)[1].split(",")
                h = parts[0].strip()
                if len(parts) > 1:
                    p = parts[1].strip()

            elif line.startswith("account") or line.startswith("user"):
                u = line.split("=", 1)[1].strip()

            elif line.startswith("password"):
                pw = line.split("=", 1)[1].strip()

            elif line.startswith("enable"):
                if line.split("=")[1].strip() == "0":
                    st = "OFF"

        push()
        return readers

    def detectStatus(self, html, r):
        if not html:
            return "Unknown", 4

        b = re.search(
            r">" + re.escape(r["label"]) + r"<.*?</tr>",
            html,
            re.I | re.S
        )

        if not b:
            return "Unknown", 4

        i = b.group(0).lower()

        if "cardok" in i:
            return "CardOK", 1

        if "connected" in i:
            return "Connected", 2

        if "offline" in i or "error" in i or "needinit" in i:
            return "Unreachable", 4

        return "Unknown", 4

    def reload(self):
        emu_type, cfg_file, webif_url, user, pwd = self.getEmuDetails()
        readers = self.parseServer(cfg_file)
        html = self.fetchWebif(webif_url, user, pwd)
        expiry_data = self.fetchExpiryData()

        self["title"].setText(_(f"Readers Status ({emu_type.upper()})"))
        self["error"].setText("")
        rows = []

        for r in readers:
            username = r.get("user", "-")
            exp_date_str = "N/A"
            days_left_str = "N/A"

            if username in expiry_data:
                exp_date_str = expiry_data[username]
                try:
                    clean_date_str = exp_date_str.replace("-", ".")
                    year_part, month_part, day_part = clean_date_str.split(".")
                    clean_date_str = "%s.%02d.%02d" % (year_part, int(month_part), int(day_part))

                    exp_date = datetime.strptime(clean_date_str, "%Y.%m.%d")
                    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                    delta_days = (exp_date - today).days
                    days_left_str = str(delta_days) if delta_days >= 0 else "Expired"
                except Exception as parse_err:
                    print(f"[ElieSatPanel] Expiration calculation failed: {parse_err}")

            r["exp_date"] = exp_date_str
            r["days_left"] = days_left_str

            if r["status"] == "OFF":
                status = "Disabled"
                prio = 3
            else:
                if not html:
                    status = "Unknown"
                    prio = 4
                else:
                    status, prio = self.detectStatus(html, r)

            line = self.makeRow(
                r["label"],
                r["host"],
                r["port"],
                r["proto"],
                status
            )

            rows.append((prio, line, r))

        rows.sort(key=lambda x: x[0])

        self.list_data = rows
        self["list"].setList([x[1] for x in rows])
        self.updateExpDate()

    def getSelectedReader(self):
        idx = self["list"].getSelectionIndex()

        if idx < 0 or idx >= len(self.list_data):
            return None

        return self.list_data[idx][2]

    def updateExpDate(self):
        r = self.getSelectedReader()
        if r:
            exp = r.get("exp_date", "N/A")
            days = r.get("days_left", "N/A")
            self["exp_date"].setText(f"Expiration Date: {exp} │ Days Left: {days}")
        else:
            self["exp_date"].setText("")

    def showDetails(self):
        r = self.getSelectedReader()

        if not r:
            return

        msg = (
            "Reader: {}\n"
            "Host: {}\n"
            "Port: {}\n"
            "Protocol: {}\n"
            "User: {}\n"
            "Pass: {}\n"
            "Expiration: {}\n"
            "Days Left: {}\n"
        ).format(
            r["label"],
            r["host"],
            r["port"],
            r["proto"],
            r["user"],
            r["pass"],
            r.get("exp_date", "N/A"),
            r.get("days_left", "N/A"),
        )

        self.session.open(
            MessageBox,
            msg,
            MessageBox.TYPE_INFO
        )

    def toggleReaderStatus(self):
        r = self.getSelectedReader()
        cfg_path = self.getConfigPath()

        if not r or not cfg_path or not os.path.exists(cfg_path):
            self.session.open(MessageBox, _("Configuration file not found!"), MessageBox.TYPE_ERROR)
            return

        try:
            with open(cfg_path, "r") as f:
                content = f.read()

            blocks = content.split("[reader]")
            new_blocks = [blocks[0]]

            target_enable = "1" if r["status"] == "OFF" else "0"

            for block in blocks[1:]:
                match = re.search(r"^\s*label\s*=\s*" + re.escape(r["label"]) + r"\b", block, re.IGNORECASE | re.MULTILINE)

                if match:
                    enable_match = re.search(r"^\s*enable\s*=\s*.*$", block, re.IGNORECASE | re.MULTILINE)
                    if enable_match:
                        block = re.sub(r"^\s*enable\s*=\s*.*$", f"enable = {target_enable}", block, flags=re.IGNORECASE | re.MULTILINE)
                    else:
                        block = f"\nenable = {target_enable}\n" + block

                new_blocks.append("[reader]" + block)

            new_content = "".join(new_blocks)

            with open(cfg_path, "w") as f:
                f.write(new_content)

            self.restartSoftcam()

        except Exception as e:
            self.session.open(
                MessageBox,
                _("Failed to edit configuration:\n{}").format(str(e)),
                MessageBox.TYPE_ERROR
            )

    def restartSoftcam(self):
        try:
            init_atv = "/etc/init.d/softcam"
            init_pli = "/usr/script/softcam.sh"

            use_systemd = False
            use_atv = False
            use_pli = False

            if os.path.exists(init_atv):
                use_atv = True
            elif os.path.exists(init_pli):
                use_pli = True
            else:
                use_systemd = True

            subprocess.call("killall -15 oscam ncam CCcam 2>/dev/null", shell=True)
            subprocess.call("sleep 2", shell=True)

            if use_atv:
                subprocess.call("/etc/init.d/softcam stop", shell=True)
            elif use_pli:
                subprocess.call("/usr/script/softcam.sh stop", shell=True)
            elif use_systemd:
                subprocess.call("systemctl stop softcam 2>/dev/null", shell=True)

            subprocess.call("sleep 2", shell=True)

            if use_atv:
                subprocess.call("/etc/init.d/softcam start", shell=True)
            elif use_pli:
                subprocess.call("/usr/script/softcam.sh start", shell=True)
            elif use_systemd:
                subprocess.call("systemctl start softcam 2>/dev/null", shell=True)

            subprocess.call("sleep 2", shell=True)

            self.reload()

            self.session.open(
                MessageBox,
                _("Softcam restarted and status updated successfully!"),
                MessageBox.TYPE_INFO,
                timeout=3
            )

        except Exception as e:
            self.session.open(
                MessageBox,
                _("Softcam restart failed:\n") + str(e),
                MessageBox.TYPE_ERROR,
                timeout=5
            )

    def deleteReaderPrompt(self):
        r = self.getSelectedReader()
        if not r:
            return

        self.session.openWithCallback(
            self.deleteReaderConfirmed,
            MessageBox,
            _("Are you sure you want to delete the reader:\n{}?").format(r["label"]),
            MessageBox.TYPE_YESNO
        )

    def deleteReaderConfirmed(self, answer):
        if not answer:
            return

        r = self.getSelectedReader()
        cfg_path = self.getConfigPath()

        if not r or not cfg_path or not os.path.exists(cfg_path):
            self.session.open(MessageBox, _("Configuration file not found!"), MessageBox.TYPE_ERROR)
            return

        try:
            with open(cfg_path, "r") as f:
                content = f.read()

            blocks = content.split("[reader]")
            new_blocks = [blocks[0]]

            for block in blocks[1:]:
                match = re.search(r"^\s*label\s*=\s*" + re.escape(r["label"]) + r"\b", block, re.IGNORECASE | re.MULTILINE)
                if match:
                    continue

                new_blocks.append("[reader]" + block)

            new_content = "".join(new_blocks)

            with open(cfg_path, "w") as f:
                f.write(new_content)

            self.reload()

        except Exception as e:
            self.session.open(
                MessageBox,
                _("Failed to edit server configuration:\n{}").format(str(e)),
                MessageBox.TYPE_ERROR
            )
