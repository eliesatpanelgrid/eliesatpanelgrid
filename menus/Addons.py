# -*- coding: utf-8 -*-
import os
import sys
import hashlib
import requests
import socket
from sys import version_info
from threading import Timer

# Enigma2 / GUI imports
from enigma import getDesktop
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.Label import Label
from Components.ActionMap import ActionMap
from Components.GUIComponent import GUIComponent
from Tools.LoadPixmap import LoadPixmap
from Tools.Directories import resolveFilename, SCOPE_PLUGINS, fileExists

# Plugin-specific imports (updated for ElieSatPanelGrid)
from Plugins.Extensions.ElieSatPanelGrid.__init__ import Version
from Plugins.Extensions.ElieSatPanelGrid.menus.FlexibleMenu import FlexibleMenu
from Plugins.Extensions.ElieSatPanelGrid.menus.Console import Console
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

# Python 2/3 compatibility for urllib
PY3 = version_info[0] == 3
try:
    from urllib.request import Request as compat_Request, urlopen as compat_urlopen
except ImportError:
    from urllib2 import Request as compat_Request, urlopen as compat_urlopen

# ---------------- Utility Functions ----------------
def has_internet(timeout=3):
    """Check for internet connection."""
    s = None
    try:
        socket.setdefaulttimeout(timeout)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("8.8.8.8", 53))
        return True
    except Exception:
        return False
    finally:
        try:
            if s:
                s.close()
        except Exception:
            pass

# URLs / Constants
INSTALLER_URL = "https://raw.githubusercontent.com/eliesat/beta/main/installer.sh"
EXTENSIONS_URL = "https://raw.githubusercontent.com/eliesat/eliesatpanelgrid/refs/heads/main/assets/data/extensions"
LOCAL_EXTENSIONS = "/usr/lib/enigma2/python/Plugins/Extensions/ElieSatPanelGrid/assets/data/extensions"

# ---------------- Addons Screen Class ----------------
class Addons(Screen):
    skin = ""

    def __init__(self, session):
        self.session = session
        self.in_submenu = False
        self.submenu_title = None
        self.previous_index = 0
        self.submenu_indices = {}

        Screen.__init__(self, session)
        # ---------------- ONLY LOAD IF DEVICE UNLOCKED AND FILES EXIST ----------------
        unlock_ok = is_device_unlocked()
        unlock_file_exists = os.path.exists("/etc/eliesat_unlocked.cfg")
        main_mac_exists = os.path.exists("/etc/eliesat_main_mac.cfg")

        if not unlock_ok or not unlock_file_exists or not main_mac_exists:
            # Close the screen immediately if checks fail
            self.close()
            return

        self.load_skin()
        self.load_icon()  # <-- Load class-specific icon

        # Pass self as parent so FlexibleMenu can load correct icon
        self["menu"] = FlexibleMenu([], parent=self)
        if getattr(self, "iconPixmap", None):
            self["menu"]._cached_logos[self.__class__.__name__.lower()] = self.iconPixmap

        self.build_ui()
        self.setup_actions()
        self.onLayoutFinish.append(self.load_main_menu)

        try:
            self["menu"].onSelectionChanged.append(self.updateDescription)
            self["menu"].onSelectionChanged.append(self.updatePageInfo)
        except Exception:
            pass

        self.start_background_updates()

    # ---------------- Skin ----------------
    def load_skin(self):
        """Load correct skin based on screen resolution."""
        screen_width = 1280
        try:
            screen_width = getDesktop(0).size().width()
        except Exception:
            pass

        base_skin_path = "/usr/lib/enigma2/python/Plugins/Extensions/ElieSatPanelGrid/assets/skin/"
        skin_files = {
            "hd": os.path.join(base_skin_path, "eliesatpanel_hd.xml"),
            "fhd": os.path.join(base_skin_path, "eliesatpanel_fhd.xml"),
            "default": os.path.join(base_skin_path, "eliesatpanel.xml"),
        }

        skin_file = (
            skin_files["fhd"]
            if screen_width >= 1920 and os.path.exists(skin_files["fhd"])
            else skin_files["hd"]
            if os.path.exists(skin_files["hd"])
            else skin_files["default"]
        )

        try:
            with open(skin_file, "r", encoding="utf-8") as f:
                self.skin = f.read()
        except FileNotFoundError:
            self.skin = """<screen name="Addons" position="center,center" size="1280,720">
                                <eLabel text="Skin Missing" position="center,center" size="400,50"
                                font="Regular;30" halign="center" valign="center"/>
                            </screen>"""

    # ---------------- Icon ----------------
    def load_icon(self):
        """Load screen icon for this class only."""
        try:
            class_name = self.__class__.__name__.lower()
            icon_path = resolveFilename(
                SCOPE_PLUGINS,
                f"Extensions/ElieSatPanelGrid/assets/icons/{class_name}.png",
            )
            if not fileExists(icon_path):
                icon_path = resolveFilename(
                    SCOPE_PLUGINS,
                    "Extensions/ElieSatPanelGrid/assets/icons/default.png",
                )
            self.iconPixmap = LoadPixmap(icon_path)
        except Exception:
            self.iconPixmap = None

    # ---------------- UI Components ----------------
    def build_ui(self):
        """Initialize other UI components."""
        self["description"] = Label("")
        self["pageinfo"] = Label("")
        self["pagelabel"] = Label("")
        self["image_name"] = Label(f"Image: {get_image_name()}")
        self["local_ip"] = Label(f"IP: {get_local_ip()}")
        self["StorageInfo"] = Label(get_storage_info())
        self["RAMInfo"] = Label(get_ram_info())
        self["python_ver"] = Label(f"Python: {get_python_version()}")
        self["net_status"] = Label(f"Net: {check_internet()}")

        self["left_bar"] = Label("\n".join(list("Version " + Version)))
        self["right_bar"] = Label("\n".join(list("By ElieSat")))

        self["red"] = Label("IPTV Adder")
        self["green"] = Label("Cccam Adder")
        self["yellow"] = Label("News")
        self["blue"] = Label("Scripts")

    # ---------------- Key Actions ----------------
    def setup_actions(self):
        self["setupActions"] = ActionMap(
            ["OkCancelActions", "DirectionActions", "ColorActions", "MenuActions"],
            {
                "cancel": self.go_back_or_exit,
                "red": self.openIptvadder,
                "green": self.openCccamadder,
                "yellow": self.openNews,
                "blue": self.openScripts,
                "ok": self.ok,
                "left": lambda: self["menu"].left(),
                "right": lambda: self["menu"].right(),
                "up": lambda: self["menu"].up(),
                "down": lambda: self["menu"].down(),
            },
            -1,
        )

    # ---------------- Background Updates ----------------
    def start_background_updates(self):
        """Run background extension update only (plugin update removed)."""
        if not has_internet():
            print("[Addons] No internet detected: background updates aborted")
            return
        Timer(1, self.update_extensions_from_github).start()

    # ---------------- Menu Management ----------------
    def load_main_menu(self):
        self.in_submenu = False
        self.main_categories = [
            ("Allinone", "All installable plugins", "Plg"),
            ("Audio", "Audio", "Aud"),
            ("Backup", "Backup", "Bac"),
            ("Epg", "Epg", "Epg"),
            ("Encryption", "Encryption", "Enc"),
            ("Free", "Free", "Free"),
            ("Iptv", "Iptv", "Ipt"),
            ("Quran", "Quran", "Qur"),
            ("Multiboot", "Multiboot", "Mul"),
            ("Novaler", "Novaler", "Nov"),
            ("Panels", "Panels", "Pan"),
            ("Picons", "Picons", "Pic"),
            ("Settings", "Settings", "Set"),
            ("Sport", "Sport", "Spo"),
            ("Subtitle", "Subtitle", "Sub"),
            ("System", "System", "Sys"),
            ("Radio", "Radio", "Rad"),
            ("Utility", "Utility", "Uti"),
            ("Weather", "Weather", "Wea"),
        ]

        categories_display = [(x[0], x[1]) for x in self.main_categories]
        self["menu"].setList(categories_display)
        idx = min(int(getattr(self, "previous_index", 0)), len(categories_display) - 1)
        self["menu"].setIndex(idx)
        self.updateDescription()
        self.updatePageInfo()

    # ---------------- Submenu Loader ----------------
    def load_sub_menu(self, status, title):
        self.in_submenu = True
        self.submenu_title = title
        items = []
        saved = self.submenu_indices.get(title, 0)

        try:
            with open(LOCAL_EXTENSIONS, "r") as f:
                lines = f.read().splitlines()

            name = version = desc = ""

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                if line.startswith("Package:"):
                    name = line.split(":", 1)[1].strip()

                elif line.startswith("Version:"):
                    p = line.split(":", 1)[1].strip().split(None, 1)
                    version = p[0]
                    desc = p[1] if len(p) > 1 else ""

                elif line.startswith("Status:"):
                    raw = line.split(":", 1)[1].strip()
                    statuses = raw.replace(",", " ").split()

                    if status in statuses:
                        items.append(("%s-%s" % (name, version), desc))

                    name = version = desc = ""

            if not items:
                items = [("No packages", "")]

        except Exception as e:
            items = [("Error", str(e))]

        self["menu"].setList(items)
        self["menu"].setIndex(saved)
        self.updateDescription()
        self.updatePageInfo()

    # ---------------- OK Button ----------------
    def ok(self):
        current = self["menu"].getCurrent()
        if not current:
            return

        if not self.in_submenu:
            self.previous_index = self["menu"].getSelectedIndex() or 0
            for cat in self.main_categories:
                if current[0] == cat[0]:
                    return self.load_sub_menu(cat[2], current[0])
            self.run_selected_script()
        else:
            self.submenu_indices[self.submenu_title] = self["menu"].getSelectedIndex() or 0
            self.run_selected_script()

    # ---------------- Run Scripts ----------------
    def run_selected_script(self):
        selected = self["menu"].getCurrent()
        if not selected:
            return
        selected_label = selected[0]
        pkg_name = selected_label.rsplit("-", 1)[0] if "-" in selected_label else selected_label

        if not os.path.exists(LOCAL_EXTENSIONS):
            print("[Addons] extensions file missing")
            return

        script_url = self._find_script_url(pkg_name)
        if not script_url:
            print("[Addons] No script found for", selected_label)
            return

        cmd = f'wget -q --no-check-certificate "{script_url}" -O - | /bin/sh'
        self.session.open(Console, title=f"Running {selected_label}...", cmdlist=[cmd], closeOnSuccess=True)

    def _find_script_url(self, pkg_name):
        try:
            with open(LOCAL_EXTENSIONS, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
            block = {}
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                if line.startswith("Package:"):
                    if block and block.get("Package") == pkg_name:
                        return next((v for v in block.values() if isinstance(v, str) and v.endswith(".sh")), None)
                    block = {"Package": line.split(":", 1)[1].strip()}
                elif "=" in line:
                    key, val = line.split("=", 1)
                    block[key.strip()] = val.strip().strip("'\"")
            return None
        except Exception as e:
            print("[Addons] _find_script_url error:", e)
            return None

    # ---------------- Colored Buttons ----------------
    def openIptvadder(self): self._safe_open(Iptvadder, "IPTV Adder")
    def openCccamadder(self): self._safe_open(Cccamadder, "Cccam Adder")
    def openNews(self): self._safe_open(News, "News")
    def openScripts(self): self._safe_open(Scripts, "Scripts")

    def _safe_open(self, screen, name):
        try:
            self.session.open(screen)
        except Exception as e:
            print(f"[Addons] {name} error:", e)

    # ---------------- Exit / Back ----------------
    def go_back_or_exit(self):
        if self.in_submenu:
            self.submenu_indices[self.submenu_title] = self["menu"].getSelectedIndex() or 0
            self.load_main_menu()
        else:
            self.close()

    # ---------------- Description & Page Info ----------------
    def updateDescription(self):
        current = self["menu"].getCurrent()
        desc_text = current[1] if current and len(current) > 1 else ""
        self["description"].setText(desc_text or "")

    def updatePageInfo(self):
        try:
            currentPage = int(self["menu"].getCurrentPage())
        except Exception:
            currentPage = 1
        try:
            totalPages = int(self["menu"].total_pages) if hasattr(self["menu"], "total_pages") else 1
        except Exception:
            totalPages = 1

        self["pageinfo"].setText(f"Page {currentPage}/{totalPages}")
        dots = " ".join(["●" if i == currentPage else "○" for i in range(1, totalPages + 1)])
        self["pagelabel"].setText(dots)

    # ---------------- GitHub Extensions Update ----------------
    def update_extensions_from_github(self):
        """Update extensions file from GitHub repository."""
        if not has_internet():
            print("[Addons] No internet: skipping extensions update")
            return False
        try:
            response = requests.get(EXTENSIONS_URL, timeout=10)
            if response.status_code != 200:
                print(f"[Addons] Failed to fetch extensions: {response.status_code}")
                return False

            new_hash = hashlib.md5(response.content).hexdigest()
            local_hash = None
            if os.path.exists(LOCAL_EXTENSIONS):
                with open(LOCAL_EXTENSIONS, "rb") as f:
                    local_hash = hashlib.md5(f.read()).hexdigest()

            if local_hash == new_hash:
                print("[Addons] Extensions already up-to-date")
                return False

            with open(LOCAL_EXTENSIONS, "wb") as f:
                f.write(response.content)

            print("[Addons] Extensions file updated from GitHub")

            if not self.in_submenu:
                self.load_main_menu()
            else:
                for cat in self.main_categories:
                    if cat[0] == self.submenu_title:
                        self.load_sub_menu(cat[2], cat[0])
                        break
            return True
        except Exception as e:
            print("[Addons] update_extensions_from_github error:", e)
            return False

