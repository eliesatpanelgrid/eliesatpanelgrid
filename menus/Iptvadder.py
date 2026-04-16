# -*- coding: utf-8 -*-
import os
import re
from enigma import eTimer, getDesktop

from Plugins.Extensions.ElieSatPanelGrid.menus.Helpers import (
    get_local_ip,
    check_internet,
    get_image_name,
    get_python_version,
    get_storage_info,
    get_ram_info,
)

from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.config import ConfigText, ConfigSelection, getConfigListEntry
from Components.ConfigList import ConfigListScreen
from Plugins.Extensions.ElieSatPanelGrid.__init__ import Version
from Plugins.Extensions.ElieSatPanelGrid.menus.Infobox import IptvScreen


class Iptvadder(Screen, ConfigListScreen):

    width, height = getDesktop(0).size().width(), getDesktop(0).size().height()

    skin_file = (
        "/usr/lib/enigma2/python/Plugins/Extensions/ElieSatPanelGrid/assets/skin/iptvadder_fhd.xml"
        if width >= 1920
        else "/usr/lib/enigma2/python/Plugins/Extensions/ElieSatPanelGrid/assets/skin/iptvadder_hd.xml"
    )

    try:
        with open(skin_file, "r") as f:
            skin = f.read()
    except:
        skin = "<screen></screen>"

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        self.setTitle(_("Subscription Editor"))

        self.restore_mode = 0
        self.blue_mode = 0

        # TIMER (5 sec window)
        self.blue_timer = eTimer()
        self.blue_timer.callback.append(self._blue_timeout)

        self.label = ConfigSelection(
            default="custom",
            choices=[
                ("custom", "custom"),
                ("serverx1", "serverx1"),
                ("serverx2", "serverx2"),
                ("serverx3", "serverx3"),
                ("serverx4", "serverx4"),
                ("jepro1", "server jepro1"),
                ("ultra", "server ultra"),
                ("strong8k1", "server strong 8k1"),
                ("strong8k2", "server strong 8k2"),
                ("neo4k1", "server neo4k1"),
                ("neo4k2", "server neo4k2"),
                ("neo4k3", "server neo4k3"),
                ("neo4k4", "server neo4k4"),
            ],
        )

        self.url = ConfigText(default="http://url.com")
        self.port = ConfigText(default="80")
        self.username = ConfigText(default="user")
        self.password = ConfigText(default="pass")

        self.label.addNotifier(self.label_changed, initial_call=False)

        self.clist = [
            getConfigListEntry("Label:", self.label),
            getConfigListEntry("URL:", self.url),
            getConfigListEntry("Port:", self.port),
            getConfigListEntry("Username:", self.username),
            getConfigListEntry("Password:", self.password),
        ]

        ConfigListScreen.__init__(self, self.clist, session=session)
        self["config"].l.setList(self.clist)

        self["left_bar"] = Label("\n".join(list("Version " + Version)))
        self["right_bar"] = Label("\n".join(list("By ElieSat")))

        self["image_name"] = Label("Image: " + get_image_name())
        self["local_ip"] = Label("IP: " + get_local_ip())
        self["StorageInfo"] = Label(get_storage_info())
        self["RAMInfo"] = Label(get_ram_info())
        self["python_ver"] = Label("Python: " + get_python_version())
        self["net_status"] = Label("Net: " + check_internet())

        self["red"] = Label(_("Check Path"))
        self["green"] = Label(_("Show / Restore Accounts"))
        self["yellow"] = Label(_("Send and Backup"))
        self["blue"] = Label(_("Clear Playlists"))

        self["panel_path"] = Label("")
        self["playlists"] = Label(self.get_playlists_dirs())

        self.panel_dir = self.find_panel_dir()
        self.load_saved_subscription()

        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions"],
            {
                "red": self.show_isubscription_path,
                "green": self.restore_reader,
                "yellow": self.send_backup,
                "blue": self.clear_playlists,
                "cancel": self.close,
            },
            -1,
        )

    # ---------------- TIMER ----------------
    def _blue_timeout(self):
        self.blue_mode = 0
        self["panel_path"].setText("")

    def get_playlists_dirs(self):
        plugins = []
        for root, _, files in os.walk("/etc/enigma2"):
            if "playlists.txt" in files:
                folder = os.path.basename(root)
                name = folder.replace("_", " ").replace("-", " ").strip().title()
                if name and name not in plugins:
                    plugins.append(name)

        return "Available plugins playlists:\n(" + ", ".join(plugins) + ")" if plugins else "Available plugins playlists:\n(<not found>)"

    def get_all_playlists_files(self):
        files = []
        for root, _, fs in os.walk("/etc/enigma2"):
            if "playlists.txt" in fs:
                files.append(os.path.join(root, "playlists.txt"))
        return files

    def extract_base_url(self, line):
        m = re.match(r'(http[s]?://[^/]+)', line)
        return m.group(1) if m else None

    # ---------------- BLUE BUTTON UPDATED ----------------
    def clear_playlists(self):
        if not self.panel_dir:
            return

        subfile = os.path.join(self.panel_dir, "isubscription.txt")

        # 🔵 FIRST CLICK
        if self.blue_mode == 0:

            # clear ONLY playlists files in /etc/enigma2
            for fpath in self.get_all_playlists_files():
                try:
                    open(fpath, "w").close()
                except:
                    pass

            self["panel_path"].setText(
                "Playlists cleared.\nPress BLUE again within 5 seconds to clear subscription"
            )

            self.blue_mode = 1
            self.blue_timer.start(5000, True)
            return

        # 🔵 SECOND CLICK (within 5 sec)
        try:
            self.blue_timer.stop()

            # clear ONLY subscription file
            if os.path.exists(subfile):
                open(subfile, "w").close()

            self["panel_path"].setText("Subscription file cleared")

        except:
            self["panel_path"].setText("Error clearing subscription")

        self.blue_mode = 0

    # ---------------- REST OF YOUR ORIGINAL CODE (UNCHANGED) ----------------

    def load_saved_subscription(self):
        if not self.panel_dir:
            return

        subfile = os.path.join(self.panel_dir, "isubscription.txt")
        if not os.path.exists(subfile):
            return

        try:
            with open(subfile, "r") as f:
                lines = f.read().splitlines()

            if len(lines) < 2:
                return

            self.label.setValue(lines[0].strip())
            active = lines[-1].strip()

            m = re.match(
                r'(http[s]?://[^:/]+)(?::(\d+))?/get\.php\?username=([^&]+)&password=([^&]+)',
                active,
            )

            if m:
                self.url.setValue(m.group(1))
                self.port.setValue(m.group(2) or "")
                self.username.setValue(m.group(3))
                self.password.setValue(m.group(4))

            self.refresh_config()
        except:
            pass

    def label_changed(self, config_element):
        mapping = {
            "custom": ("http://url.com", "user", "pass"),
            "serverx1": ("http://cafott.com", None, None),
            "serverx2": ("http://vipxtv.net", None, None),
            "serverx3": ("http://servx.pro", None, None),
            "serverx4": ("http://hxb8j.otvipserv.com", None, None),
            "jepro1": ("http://a345d.info", None, None),
            "ultra": ("http://ultra.gotop.me", None, None),
            "strong8k1": ("https://fine61764.wd.business-cloud-8k.ru", None, None),
            "strong8k2": ("https://cf.cdn-90.me", None, None),
            "neo4k1": ("http://april80089.wd.business-cloud-neo.ru", None, None),
            "neo4k2": ("http://cf.business-cloud-neo.ru", None, None),
            "neo4k3": ("http://pro.business-cloud-neo.ru", None, None),
            "neo4k4": ("http://tv.business-cloud-neo.ru", None, None),
        }

        key = config_element.value
        if key in mapping:
            url, user, pwd = mapping[key]
            self.url.setValue(url)
            if key == "custom":
                self.username.setValue(user)
                self.password.setValue(pwd)

        self.refresh_config()

    def refresh_config(self):
        self.clist = [
            getConfigListEntry("Label:", self.label),
            getConfigListEntry("URL:", self.url),
            getConfigListEntry("Port:", self.port),
            getConfigListEntry("Username:", self.username),
            getConfigListEntry("Password:", self.password),
        ]
        self["config"].l.setList(self.clist)
        self["config"].setCurrentIndex(0)

    def find_panel_dir(self):
        search_roots = ["/media/hdd", "/media/mmc"]

        try:
            search_roots += [
                os.path.join("/media", d)
                for d in os.listdir("/media")
                if d.startswith("usb")
            ]
        except:
            pass

        for root in search_roots:
            path = os.path.join(root, "ElieSatPanel", "panel_dir.cfg")
            if os.path.exists(path):
                folder = os.path.dirname(path)
                subfile = os.path.join(folder, "isubscription.txt")
                if not os.path.exists(subfile):
                    open(subfile, "w").close()
                return folder
        return None

    def show_isubscription_path(self):
        self.session.open(IptvScreen)

    def restore_reader(self):
        if not self.panel_dir:
            return

        subfile = os.path.join(self.panel_dir, "isubscription.txt")

        if not os.path.exists(subfile):
            self["panel_path"].setText("No file found")
            return

        try:
            with open(subfile, "r") as f:
                lines = [l.strip() for l in f.readlines() if l.strip()]

            if len(lines) < 2:
                self["panel_path"].setText("No accounts saved")
                return

            accounts = lines[1:]

            if self.restore_mode == 0:
                self["panel_path"].setText(
                    "Saved Account:\n\n" + "\n".join(accounts)
                )
                self.restore_mode = 1
                return

            for fpath in self.get_all_playlists_files():
                try:
                    with open(fpath, "r") as f:
                        existing = [l.strip() for l in f.readlines() if l.strip()]
                except:
                    existing = []

                merged = list(dict.fromkeys(existing + accounts))

                with open(fpath, "w") as f:
                    f.write("\n".join(merged) + "\n")

            self["panel_path"].setText("Accounts restored to playlists")
            self.restore_mode = 0

        except:
            self["panel_path"].setText("Error reading file")

    def send_backup(self):
        if not self.panel_dir:
            return

        if self.port.value.strip():
            new_line = "%s:%s/get.php?username=%s&password=%s&type=m3u_plus&output=ts" % (
                self.url.value,
                self.port.value,
                self.username.value,
                self.password.value,
            )
        else:
            new_line = "%s/get.php?username=%s&password=%s&type=m3u_plus&output=ts" % (
                self.url.value,
                self.username.value,
                self.password.value,
            )

        new_base = self.extract_base_url(new_line)

        subfile = os.path.join(self.panel_dir, "isubscription.txt")

        lines = []
        if os.path.exists(subfile):
            try:
                with open(subfile, "r") as f:
                    lines = f.read().splitlines()
            except:
                pass

        label_line = self.label.value

        filtered = []
        for l in lines[1:]:
            base = self.extract_base_url(l)
            if base != new_base:
                filtered.append(l)

        lines = [label_line] + filtered + [new_line]

        with open(subfile, "w") as f:
            f.write("\n".join(lines) + "\n")

        for fpath in self.get_all_playlists_files():
            try:
                with open(fpath, "w") as f:
                    f.write("\n".join(lines[1:]))
            except:
                pass

        self["panel_path"].setText("UPDATED:\n%s" % new_line)
