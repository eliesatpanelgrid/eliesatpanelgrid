# -*- coding: utf-8 -*-
import os
import sys
import socket
from sys import version_info

# Enigma2 / GUI imports
from enigma import getDesktop
from Screens.Screen import Screen
from Components.Label import Label
from Components.ActionMap import ActionMap

# Plugin-specific imports
from Plugins.Extensions.ElieSatPanelGrid.__init__ import Version
from Plugins.Extensions.ElieSatPanelGrid.menus.Iptvadder import Iptvadder
from Plugins.Extensions.ElieSatPanelGrid.menus.Cccamadder import Cccamadder
from Plugins.Extensions.ElieSatPanelGrid.menus.News import News
from Plugins.Extensions.ElieSatPanelGrid.menus.Scripts import Scripts
from Plugins.Extensions.ElieSatPanelGrid.menus.Helpers import (
    get_local_ip,
    check_internet,
    get_image_name,
    get_python_version,
    get_storage_info,
    get_ram_info,
    is_device_unlocked
)

PY3 = version_info[0] == 3

# ---------------- Helper function to read plugin skin ----------------
def get_plugin_skin():
    screen_width = 1280
    try:
        screen_width = getDesktop(0).size().width()
    except Exception:
        pass

    # Use dynamic base path relative to plugin installation
    current_dir = os.path.dirname(os.path.abspath(__file__))
    plugin_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
    base_skin_path = os.path.join(plugin_root, "assets", "menus", "Free")

    # Fallback to standard absolute path
    if not os.path.exists(base_skin_path):
        base_skin_path = "/usr/lib/enigma2/python/Plugins/Extensions/ElieSatPanelGrid/menus/Free/"

    fhd_path = os.path.join(base_skin_path, "Free_fhd.xml")
    hd_path = os.path.join(base_skin_path, "Free_hd.xml")

    # Select skin based on screen resolution
    if screen_width >= 1920 and os.path.exists(fhd_path):
        skin_file = fhd_path
    elif os.path.exists(hd_path):
        skin_file = hd_path
    elif os.path.exists(fhd_path):
        skin_file = fhd_path
    else:
        print(f"[Free Screen Error] Skin files not found in '{base_skin_path}'")
        return """<screen name="Free" position="center,center" size="1280,720">
                    <eLabel text="Skin File Missing" position="center,center" size="400,50"
                    font="Regular;30" halign="center" valign="center"/>
                  </screen>"""

    try:
        with open(skin_file, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception as e:
        print(f"[Free Screen Error] Could not read skin file '{skin_file}':", e)
        return """<screen name="Free" position="center,center" size="1280,720">
                    <eLabel text="Skin Read Error" position="center,center" size="400,50"
                    font="Regular;30" halign="center" valign="center"/>
                  </screen>"""

# ---------------- Free Screen ----------------
class Free3(Screen):
    def __init__(self, session):
        self.session = session
        Screen.__init__(self, session)

        # Security & device unlock checks
        unlock_ok = is_device_unlocked()
        unlock_file_exists = os.path.exists("/etc/eliesat_unlocked.cfg")
        main_mac_exists = os.path.exists("/etc/eliesat_main_mac.cfg")

        if not unlock_ok or not unlock_file_exists or not main_mac_exists:
            self.close()
            return

        self.skin = get_plugin_skin()
        self.build_ui()
        self.setup_actions()

    # ---------------- UI Setup ----------------
    def build_ui(self):
        # Description & Pager widgets defined in XML
        self["description"] = Label("")
        self["pageinfo"] = Label("")
        self["pagelabel"] = Label("")

        # System Info Bar Widgets
        self["image_name"] = Label(f"Image: {get_image_name()}")
        self["local_ip"] = Label(f"IP: {get_local_ip()}")
        self["StorageInfo"] = Label(get_storage_info())
        self["RAMInfo"] = Label(get_ram_info())
        self["python_ver"] = Label(f"Python: {get_python_version()}")
        self["net_status"] = Label(f"Net: {check_internet()}")

        # Vertical Side Bars
        self["left_bar"] = Label("\n".join(list("Version " + Version)))
        self["right_bar"] = Label("\n".join(list("By ElieSat")))

        # Color Action Button Labels (Matched exactly to skin XML text)
        self["red"] = Label("Free Ipaudio")
        self["green"] = Label("Free Cccam")
        self["yellow"] = Label("Free XtreamCodes")
        self["blue"] = Label("Portals")

    # ---------------- Key Actions ----------------
    def setup_actions(self):
        self["setupActions"] = ActionMap(
            ["OkCancelActions", "ColorActions"],
            {
                "cancel": self.close,
                "red": self.openIptvadder,
                "green": self.openCccamadder,
                "yellow": self.openNews,
                "blue": self.openScripts,
            },
            -1,
        )

    # ---------------- Colored Buttons Navigation ----------------
    def openIptvadder(self):
        self._safe_open(Iptvadder, "Free Ipaudio")

    def openCccamadder(self):
        self._safe_open(Cccamadder, "Free Cccam")

    def openNews(self):
        self._safe_open(News, "Free XtreamCodes")

    def openScripts(self):
        self._safe_open(Scripts, "Portals")

    def _safe_open(self, screen, name):
        try:
            self.session.open(screen)
        except Exception as e:
            print(f"[Free Screen] {name} error:", e)
