# -*- coding: utf-8 -*-
import os
import sys
from sys import version_info

from enigma import getDesktop
from Screens.Screen import Screen
from Components.Label import Label
from Components.ActionMap import ActionMap
from Components.MenuList import MenuList

from Plugins.Extensions.ElieSatPanelGrid.__init__ import Version
from Plugins.Extensions.ElieSatPanelGrid.menus.Helpers import (
    get_local_ip,
    check_internet,
    get_image_name,
    get_python_version,
    get_storage_info,
    get_ram_info,
    is_device_unlocked
)

# Safe imports for sub-screens
Free1 = None
Free2 = None
Free3 = None
Free4 = None

try:
    from Plugins.Extensions.ElieSatPanelGrid.menus.Free.Free1 import Free1
except Exception as e:
    print(f"[ElieSatPanel Error] Could not import Free1: {e}")

try:
    from Plugins.Extensions.ElieSatPanelGrid.menus.Free.Free2 import Free2
except Exception as e:
    print(f"[ElieSatPanel Error] Could not import Free2: {e}")

try:
    from Plugins.Extensions.ElieSatPanelGrid.menus.Free.Free3 import Free3
except Exception as e:
    print(f"[ElieSatPanel Error] Could not import Free3: {e}")

try:
    from Plugins.Extensions.ElieSatPanelGrid.menus.Free.Free4 import Free4
except Exception as e:
    print(f"[ElieSatPanel Error] Could not import Free4: {e}")


def get_plugin_skin():
    screen_width = 1280
    try:
        screen_width = getDesktop(0).size().width()
    except Exception:
        pass

    current_dir = os.path.dirname(os.path.abspath(__file__))
    plugin_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
    base_skin_path = os.path.join(plugin_root, "assets", "menus", "Free")

    if not os.path.exists(base_skin_path):
        base_skin_path = "/usr/lib/enigma2/python/Plugins/Extensions/ElieSatPanelGrid/menus/Free/"

    fhd_path = os.path.join(base_skin_path, "Free_fhd.xml")
    hd_path = os.path.join(base_skin_path, "Free_hd.xml")

    skin_file = fhd_path if screen_width >= 1920 and os.path.exists(fhd_path) else hd_path

    try:
        with open(skin_file, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception as e:
        print(f"[Free Screen Error] Could not read skin file '{skin_file}': {e}")
        return """<screen name="Free" position="0,0" size="1920,1080">
                    <widget name="menu_list" position="150,200" size="1100,600" scrollbarMode="showOnDemand"/>
                  </screen>"""


class Free(Screen):
    def __init__(self, session):
        self.session = session
        Screen.__init__(self, session)

        if not is_device_unlocked() or not os.path.exists("/etc/eliesat_unlocked.cfg"):
            print("[Free Screen Error] Security lock active or missing cfg file.")
            self.close()
            return

        self.skin = get_plugin_skin()
        self.build_ui()
        self.setup_actions()

    def build_ui(self):
        # Description text & static navigation text separated
        self["description"] = Label("")
        self["navigation_txt"] = Label("● Use UP/DOWN keys to select an option, or press OK / Colored buttons.")
        self["pagelabel"] = Label("● Free Services")

        # System Information
        self["image_name"] = Label(f"Image: {get_image_name()}")
        self["local_ip"] = Label(f"IP: {get_local_ip()}")
        self["StorageInfo"] = Label(get_storage_info())
        self["RAMInfo"] = Label(get_ram_info())
        self["python_ver"] = Label(f"Python: {get_python_version()}")
        self["net_status"] = Label(f"Net: {check_internet()}")

        # Vertical Side Text
        self["left_bar"] = Label("\n".join(list("Version " + str(Version))))
        self["right_bar"] = Label("\n".join(list("By ElieSat")))

        # Bottom Color Action Button Labels
        self["red"] = Label("Free Ipaudio")
        self["green"] = Label("Free Cccam")
        self["yellow"] = Label("Free XtreamCodes")
        self["blue"] = Label("Free Portals")

        # Items mapping: Label, Action Function, Subtitle Info
        self.menu_items = [
            ("Free Ipaudio", self.openFree1, "Open Free IP Audio player section"),
            ("Free Cccam", self.openFree2, "Open Free CCcam generator and manager"),
            ("Free XtreamCodes", self.openFree3, "Access Free Xtream IPTV playlists"),
            ("Free Portals", self.openFree4, "Browse free stalker portal links")
        ]

        # Populate MenuList
        menu_titles = [item[0] for item in self.menu_items]
        self["menu_list"] = MenuList(menu_titles)

        # Update description on list selection change
        self["menu_list"].onSelectionChanged.append(self.selectionChanged)
        self.selectionChanged()

    def setup_actions(self):
        self["setupActions"] = ActionMap(
            ["OkCancelActions", "ColorActions", "DirectionActions"],
            {
                "ok": self.okClicked,
                "cancel": self.close,
                "red": self.openFree1,
                "green": self.openFree2,
                "yellow": self.openFree3,
                "blue": self.openFree4,
                "up": self.keyUp,
                "down": self.keyDown,
            },
            -1,
        )

    def keyUp(self):
        self["menu_list"].up()

    def keyDown(self):
        self["menu_list"].down()

    def selectionChanged(self):
        index = self["menu_list"].getSelectedIndex()
        if index is not None and index < len(self.menu_items):
            desc = self.menu_items[index][2]
            self["description"].setText(f"● {desc}")

    def okClicked(self):
        index = self["menu_list"].getSelectedIndex()
        if index is not None and index < len(self.menu_items):
            action_function = self.menu_items[index][1]
            action_function()

    def openFree1(self):
        self._safe_open(Free1, "Free1")

    def openFree2(self):
        self._safe_open(Free2, "Free2")

    def openFree3(self):
        self._safe_open(Free3, "Free3")

    def openFree4(self):
        self._safe_open(Free4, "Free4")

    def _safe_open(self, screen_class, name):
        if screen_class is None:
            print(f"[Free Screen Error] Cannot open {name}: Screen module not loaded.")
            return
        try:
            self.session.open(screen_class)
        except Exception as e:
            print(f"[Free Screen] {name} open error: {e}")
