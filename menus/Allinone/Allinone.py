# -*- coding: utf-8 -*-
import os
import sys
import math
import hashlib
import requests
import socket
import subprocess
from sys import version_info

# Enigma2 / GUI imports
from enigma import (
    getDesktop,
    eListboxPythonMultiContent,
    eListbox,
    ePixmap,
    eLabel,
    eSize,
    ePoint,
    gFont,
    eTimer,
    BT_SCALE,
    BT_KEEP_ASPECT_RATIO,
    BT_ALIGN_CENTER,
    RT_HALIGN_CENTER,
    RT_VALIGN_CENTER,
    RT_HALIGN_RIGHT,
)
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.Label import Label
from Components.ActionMap import ActionMap
from Components.GUIComponent import GUIComponent
from Components.MultiContent import (
    MultiContentEntryText,
    MultiContentEntryPixmap,
    MultiContentEntryPixmapAlphaTest,
)
from Tools.LoadPixmap import LoadPixmap
from Tools.Directories import resolveFilename, SCOPE_PLUGINS, fileExists
from skin import parseColor

# Plugin-specific imports
from Plugins.Extensions.ElieSatPanelGrid.menus.Allinone.FlexibleMenu2 import FlexibleMenu2
from Plugins.Extensions.ElieSatPanelGrid.__init__ import Version
from Plugins.Extensions.ElieSatPanelGrid.menus.Console import Console
from Plugins.Extensions.ElieSatPanelGrid.menus.Iptvadder.Iptvadder import Iptvadder
from Plugins.Extensions.ElieSatPanelGrid.menus.Cccamadder.Cccamadder import Cccamadder
from Plugins.Extensions.ElieSatPanelGrid.menus.News.News import News
from Plugins.Extensions.ElieSatPanelGrid.menus.Scripts.Scripts import Scripts
from Plugins.Extensions.ElieSatPanelGrid.menus.Helpers import (
    get_local_ip,
    check_internet,
    get_image_name,
    get_python_version,
    get_storage_info,
    get_ram_info,
    is_device_unlocked
)

# Python 2/3 compatibility
PY3 = version_info[0] == 3
try:
    from urllib.request import Request as compat_Request, urlopen as compat_urlopen
except ImportError:
    from urllib2 import Request as compat_Request, urlopen as compat_urlopen

# ---------------- Utility Functions & Constants ----------------
ADDONS_FILE = "/home/addons.txt"

def update_addons_file(pkg_name, is_installed):
    """Adds or removes the package name from /home/addons.txt."""
    if not pkg_name:
        return
    try:
        lines = []
        if os.path.exists(ADDONS_FILE):
            with open(ADDONS_FILE, "r") as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]

        if is_installed:
            if pkg_name not in lines:
                lines.append(pkg_name)
        else:
            if pkg_name in lines:
                lines.remove(pkg_name)

        with open(ADDONS_FILE, "w") as f:
            for l in lines:
                f.write(l + "\n")
    except Exception as e:
        print("[Addons] Error updating addons.txt:", e)

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

def is_plugin_installed(plugin_name):
    """
    Universal check for Enigma2:
    - Standard Extensions
    - SystemPlugins
    - Skins
    - OPKG Packages (Emus / Softcams / System dependencies)
    """
    if not plugin_name:
        return False

    target = plugin_name.strip()
    target_lower = target.lower()

    # 1. Directory Checks (Extensions, SystemPlugins, Skins)
    search_paths = [
        "/usr/lib/enigma2/python/Plugins/Extensions/",
        "/usr/lib/enigma2/python/Plugins/SystemPlugins/",
        "/usr/share/enigma2/",
    ]

    for base_dir in search_paths:
        if not os.path.exists(base_dir):
            continue

        if os.path.exists(os.path.join(base_dir, target)):
            return True

        try:
            installed_folders = [f.lower() for f in os.listdir(base_dir)]
            if target_lower in installed_folders:
                return True
        except Exception:
            pass

    # 2. OPKG Database Check
    try:
        cmd = f"opkg status {target_lower} | grep -i 'Status: install ok installed'"
        if subprocess.call(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE) == 0:
            return True
    except Exception:
        pass

    return False

INSTALLER_URL = "https://raw.githubusercontent.com/eliesatpanelgrid/beta/main/installer.sh"
EXTENSIONS_URL = "https://raw.githubusercontent.com/eliesatpanelgrid/eliesatpanelgrid/refs/heads/main/assets/data/extensions"
LOCAL_EXTENSIONS = "/usr/lib/enigma2/python/Plugins/Extensions/ElieSatPanelGrid/assets/data/extensions"

# ---------------- ADDONS SCREEN CLASS ----------------
class Allinone(Screen):
    skin = ""

    def __init__(self, session):
        self.session = session
        self.in_submenu = False
        self.submenu_title = None
        self.previous_index = 0
        self.submenu_indices = {}
        self.current_running_pkg = None
        self.total_packages_count = 0

        Screen.__init__(self, session)

        unlock_ok = is_device_unlocked()
        unlock_file_exists = os.path.exists("/etc/eliesat_unlocked.cfg")
        main_mac_exists = os.path.exists("/etc/eliesat_main_mac.cfg")

        if not unlock_ok or not unlock_file_exists or not main_mac_exists:
            self.close()
            return

        self.load_skin()
        self.load_icon()

        # Instantiate FlexibleMenu2
        self["menu"] = FlexibleMenu2([], parent=self)
        
        # Guard against skinAttributes being None inside FlexibleMenu2
        if not hasattr(self["menu"], "skinAttributes") or self["menu"].skinAttributes is None:
            self["menu"].skinAttributes = []

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

    def load_skin(self):
        screen_width = 1280
        try:
            screen_width = getDesktop(0).size().width()
        except Exception:
            pass

        base_skin_path = "/usr/lib/enigma2/python/Plugins/Extensions/ElieSatPanelGrid/menus/Allinone/"
        
        # FIX: Lowercase filenames matching real disk path
        hd_skin_file = os.path.join(base_skin_path, "allinone_hd.xml")
        fhd_skin_file = os.path.join(base_skin_path, "allinone_fhd.xml")

        target_file = hd_skin_file if (screen_width < 1920 and os.path.exists(hd_skin_file)) else fhd_skin_file

        try:
            with open(target_file, "r", encoding="utf-8") as f:
                self.skin = f.read()
        except Exception as e:
            print("[Addons] Error loading skin file:", e)
            self.skin = '<screen name="Allinone" position="center,center" size="1920,1080" />'

    def get_total_items_count(self):
        """Scans LOCAL_EXTENSIONS to get total number of unique items across all categories."""
        if not os.path.exists(LOCAL_EXTENSIONS):
            return 0
        try:
            with open(LOCAL_EXTENSIONS, "r") as f:
                lines = f.read().splitlines()

            count = 0
            name = False

            for line in lines:
                line = line.strip()
                if not line:
                    continue
                if line.startswith("Package:"):
                    name = True
                elif line.startswith("Status:") and name:
                    count += 1
                    name = False
            return count
        except Exception:
            return 0

    def updateDescription(self):
        curr = self["menu"].getCurrent()
        if curr and len(curr) > 1:
            self["description"].setText(curr[1])
        else:
            self["description"].setText("")

    def updatePageInfo(self):
        page = self["menu"].getCurrentPage()
        total = self["menu"].total_pages
        self["pageinfo"].setText(f"Page {page}/{total}")

    def update_button_labels(self):
        """Forces labels to update dynamically depending on active state."""
        if self.in_submenu:
            if "red" in self:
                self["red"].setText("Remove (addons)")
            if "green" in self:
                self["green"].setText("Install (addons)")
            if "yellow" in self:
                self["yellow"].setText("")
            if "blue" in self:
                self["blue"].setText("")
        else:
            if "red" in self:
                self["red"].setText("IPTV Adder")
            if "green" in self:
                self["green"].setText("Cccam Adder")
            if "yellow" in self:
                self["yellow"].setText("News")
            if "blue" in self:
                self["blue"].setText("Scripts")

    def go_back_or_exit(self):
        if self.in_submenu:
            self.load_main_menu()
        else:
            self.close()

    def handle_red_button(self):
        if self.in_submenu:
            self.run_selected_script(force_mode="uninstall")
        else:
            self.openIptvadder()

    def handle_green_button(self):
        if self.in_submenu:
            self.run_selected_script(force_mode="install")
        else:
            self.openCccamadder()

    def handle_yellow_button(self):
        if not self.in_submenu:
            self.openNews()

    def handle_blue_button(self):
        if not self.in_submenu:
            self.openScripts()

    def openIptvadder(self):
        if not is_device_unlocked():
            self.session.open(MessageBox, "Device is not unlocked!", MessageBox.TYPE_ERROR)
            return
        try:
            self.session.open(Iptvadder)
        except Exception as e:
            self.session.open(MessageBox, f"Error opening IPTV Adder: {str(e)}", MessageBox.TYPE_ERROR)

    def openCccamadder(self):
        if not is_device_unlocked():
            self.session.open(MessageBox, "Device is not unlocked!", MessageBox.TYPE_ERROR)
            return
        try:
            self.session.open(Cccamadder)
        except Exception as e:
            self.session.open(MessageBox, f"Error opening Cccam Adder: {str(e)}", MessageBox.TYPE_ERROR)

    def openNews(self):
        if not is_device_unlocked():
            self.session.open(MessageBox, "Device is not unlocked!", MessageBox.TYPE_ERROR)
            return
        try:
            self.session.open(News)
        except Exception as e:
            self.session.open(MessageBox, f"Error opening News: {str(e)}", MessageBox.TYPE_ERROR)

    def openScripts(self):
        if not is_device_unlocked():
            self.session.open(MessageBox, "Device is not unlocked!", MessageBox.TYPE_ERROR)
            return
        try:
            self.session.open(Scripts)
        except Exception as e:
            self.session.open(MessageBox, f"Error opening Scripts: {str(e)}", MessageBox.TYPE_ERROR)

    def load_icon(self):
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

    def build_ui(self):
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

        self["red"] = Label("")
        self["green"] = Label("")
        self["yellow"] = Label("")
        self["blue"] = Label("")

    def setup_actions(self):
        self["setupActions"] = ActionMap(
            ["OkCancelActions", "DirectionActions", "ColorActions", "MenuActions"],
            {
                "cancel": self.go_back_or_exit,
                "red": self.handle_red_button,
                "green": self.handle_green_button,
                "yellow": self.handle_yellow_button,
                "blue": self.handle_blue_button,
                "ok": self.ok,
                "left": lambda: self["menu"].left(),
                "right": lambda: self["menu"].right(),
                "up": lambda: self["menu"].up(),
                "down": lambda: self["menu"].down(),
            },
            -1,
        )

    def start_background_updates(self):
        if not has_internet():
            return
        self.update_timer = eTimer()
        self.update_timer.callback.append(self.update_extensions_from_github)
        self.update_timer.start(1000, True)

    def update_extensions_from_github(self):
        try:
            r = requests.get(EXTENSIONS_URL, timeout=5)
            if r.status_code == 200 and r.text.strip():
                with open(LOCAL_EXTENSIONS, "w") as f:
                    f.write(r.text)
                self.total_packages_count = self.get_total_items_count()
                if not self.in_submenu:
                    self.load_main_menu()
        except Exception as e:
            print("[Addons] Update extensions error:", e)

    def load_main_menu(self):
        self.in_submenu = False
        self.total_packages_count = self.get_total_items_count()

        self.main_categories = [
            ("Audio", "Audio", "Aud"),
            ("Backup", "Backup", "Bac"),
            ("Epg", "Epg", "Epg"),
            ("Encryption", "Encryption", "Enc"),
            ("Free", "Free", "Free"),
            ("Games", "Games", "Games"),
            ("Iptv", "Iptv", "Ipt"),
            ("Quran", "Quran", "Qur"),
            ("Multiboot", "Multiboot", "Mul"),
            ("Novaler", "Novaler", "Nov"),
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

        total_categories = len(self.main_categories)

        self["pagelabel"].setText(
            f"Categories : ({total_categories})    Items : ({self.total_packages_count})"
        )

        self.updateDescription()
        self.updatePageInfo()
        self.update_button_labels()

    def load_sub_menu(self, status, title):
        self.in_submenu = True
        self.submenu_title = title

        items = []
        saved = self.submenu_indices.get(title, 0)

        try:
            if os.path.exists(LOCAL_EXTENSIONS):
                with open(LOCAL_EXTENSIONS, "r") as f:
                    lines = f.read().splitlines()

                name = version = desc = ""
                pkg_counts = {}

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
                        statuses = [s.strip() for s in raw.replace(",", " ").split()]

                        if status in statuses and name:
                            pkg_counts[name] = pkg_counts.get(name, 0) + 1
                            script_key = f"{name}-{pkg_counts[name]}"
                            items.append(("%s-%s" % (name, version), desc, script_key, name))

            if not items:
                items = [("No packages", "No packages available", "", "")]
                sub_count = 0
            else:
                sub_count = len(items)

        except Exception as e:
            items = [("Error", str(e), "", "")]
            sub_count = 0

        self["menu"].setList(items)
        if items and saved < len(items):
            self["menu"].setIndex(saved)
        else:
            self["menu"].setIndex(0)

        if self.total_packages_count == 0:
            self.total_packages_count = self.get_total_items_count()

        self["pagelabel"].setText(f"({sub_count}/{self.total_packages_count})")

        self.updateDescription()
        self.updatePageInfo()
        self.update_button_labels()

    def ok(self):
        current = self["menu"].getCurrent()
        if not current:
            return

        if not self.in_submenu:
            self.previous_index = self["menu"].getSelectedIndex() or 0
            for cat in self.main_categories:
                if current[0] == cat[0]:
                    return self.load_sub_menu(cat[2], current[0])
        else:
            self.run_selected_script(force_mode=None)

    def _find_script_url(self, script_key):
        """Extracts execution URL using script key or falling back to package name."""
        try:
            if not os.path.exists(LOCAL_EXTENSIONS):
                return None
                
            with open(LOCAL_EXTENSIONS, "r") as f:
                lines = f.read().splitlines()

            for line in lines:
                line = line.strip()
                if line.startswith(f"{script_key}="):
                    return line.split("=", 1)[1].strip().strip("'\"")

            base_name = script_key.rsplit('-', 1)[0] if '-' in script_key else script_key
            for line in lines:
                line = line.strip()
                if line.startswith(f"{base_name}="):
                    return line.split("=", 1)[1].strip().strip("'\"")
        except Exception as e:
            print("[Addons] Error finding script URL:", e)
        return None

    def run_selected_script(self, force_mode=None):
        selected = self["menu"].getCurrent()
        if not selected or len(selected) < 4:
            return

        selected_label = selected[0]
        script_key = selected[2]
        real_name = selected[3]

        if not real_name or not script_key:
            return

        if self.in_submenu and self.submenu_title:
            self.submenu_indices[self.submenu_title] = self["menu"].getSelectedIndex() or 0

        script_url = self._find_script_url(script_key)
        if not script_url:
            print(f"[Addons] URL not found for script key: {script_key}")
            return

        is_installed = is_plugin_installed(real_name)

        if force_mode == "install":
            if is_installed:
                return
            cmd = f'wget -q --no-check-certificate "{script_url}" -O - | /bin/sh'
            action_title = f"Installing {selected_label}..."

        elif force_mode == "uninstall":
            if not is_installed:
                return
            cmd = f'wget -q --no-check-certificate "{script_url}" -O - | /bin/sh -s uninstall'
            action_title = f"Uninstalling {selected_label}..."

        else:
            if is_installed:
                cmd = f'wget -q --no-check-certificate "{script_url}" -O - | /bin/sh -s uninstall'
                action_title = f"Uninstalling {selected_label}..."
            else:
                cmd = f'wget -q --no-check-certificate "{script_url}" -O - | /bin/sh'
                action_title = f"Installing {selected_label}..."

        self.current_running_pkg = real_name

        self.session.openWithCallback(
            self.script_finished,
            Console,
            title=action_title,
            cmdlist=[cmd],
            closeOnSuccess=True
        )

    def script_finished(self, result=None):
        if self.current_running_pkg:
            installed = is_plugin_installed(self.current_running_pkg)
            update_addons_file(self.current_running_pkg, installed)

        if self.in_submenu and self.submenu_title:
            for cat in self.main_categories:
                if cat[0] == self.submenu_title:
                    self.load_sub_menu(cat[2], self.submenu_title)
                    break
        else:
            self.load_main_menu()

        self.current_running_pkg = None
