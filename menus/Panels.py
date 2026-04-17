# -*- coding: utf-8 -*-
import os
import hashlib
import requests
from threading import Timer
from enigma import getDesktop
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Components.Label import Label
from Components.ActionMap import ActionMap
from Tools.LoadPixmap import LoadPixmap
from Tools.Directories import resolveFilename, SCOPE_PLUGINS, fileExists

from Plugins.Extensions.ElieSatPanelGrid.__init__ import Version
from Plugins.Extensions.ElieSatPanelGrid.menus.FlexibleMenu import FlexibleMenu
from Plugins.Extensions.ElieSatPanelGrid.menus.Console import Console
from Plugins.Extensions.ElieSatPanelGrid.menus.Iptvadder import Iptvadder
from Plugins.Extensions.ElieSatPanelGrid.menus.Cccamadder import Cccamadder
from Plugins.Extensions.ElieSatPanelGrid.menus.News import News
from Plugins.Extensions.ElieSatPanelGrid.menus.Scripts import Scripts
from Plugins.Extensions.ElieSatPanelGrid.menus.Helpers import (
    get_local_ip, check_internet, get_image_name,
    get_python_version, get_storage_info, get_ram_info
)
from Plugins.Extensions.ElieSatPanelGrid.menus.Helpers import is_device_unlocked


# ---------------- Utility ----------------
def has_internet(timeout=3):
    try:
        import socket
        socket.setdefaulttimeout(timeout)
        s = socket.socket()
        s.connect(("8.8.8.8", 53))
        s.close()
        return True
    except:
        return False

# ---------------- TOOLSP CLASS (Addons-style) ----------------
class Panels(Screen):
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
        self.load_icon()

        # FlexibleMenu with parent reference for icon caching
        self["menu"] = FlexibleMenu([], parent=self)
        if getattr(self, "iconPixmap", None):
            self["menu"]._cached_logos[self.__class__.__name__.lower()] = self.iconPixmap

        self.build_ui()
        self.setup_actions()

        # Update description/page when selection changes
        try:
            self["menu"].onSelectionChanged.append(self.updateDescription)
            self["menu"].onSelectionChanged.append(self.updatePageInfo)
        except Exception:
            pass

        # Load menu after layout
        self.onLayoutFinish.append(self.load_panels)

        # Background update
        Timer(1, self.update_data).start()

    # ---------------- Skin ----------------
    def load_skin(self):
        screen_width = 1280
        try:
            screen_width = getDesktop(0).size().width()
        except Exception:
            pass

        base_skin_path = "/usr/lib/enigma2/python/Plugins/Extensions/ElieSatPanelGrid/assets/skin/"
        hd_skin = os.path.join(base_skin_path, "eliesatpanel_hd.xml")
        fhd_skin = os.path.join(base_skin_path, "eliesatpanel_fhd.xml")
        default_skin = os.path.join(base_skin_path, "eliesatpanel.xml")

        if screen_width >= 1920 and os.path.exists(fhd_skin):
            skin_file = fhd_skin
        elif os.path.exists(hd_skin):
            skin_file = hd_skin
        else:
            skin_file = default_skin

        try:
            with open(skin_file, "r", encoding="utf-8") as f:
                self.skin = f.read()
        except Exception:
            self.skin = """<screen name="Toolsp" position="center,center" size="1280,720">
                                <eLabel text="Skin Missing" position="center,center" size="400,50"
                                font="Regular;30" halign="center" valign="center"/>
                           </screen>"""

    # ---------------- Icon ----------------
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

    # ---------------- UI ----------------
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

    # ---------------- Load Panels ----------------
    def load_panels(self):
        """Load panels from local file with icons like Addons."""
        packages = []
        panels_file = resolveFilename(
            SCOPE_PLUGINS, "Extensions/ElieSatPanelGrid/assets/data/panels"
        )
        try:
            with open(panels_file, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()

            name = version = desc = status = ""
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                if line.startswith("Package:"):
                    name = line.split(":", 1)[1].strip()
                elif line.startswith("Version:"):
                    parts = line.split(":", 1)[1].strip().split(None, 1)
                    version = parts[0]
                    desc = parts[1] if len(parts) > 1 else ""
                elif line.startswith("Status:"):
                    status = line.split(":", 1)[1].strip()
                    if status.lower() == "pan":
                        # Icon per panel
                        icon_name = f"{name.lower()}.png"
                        icon_path = resolveFilename(
                            SCOPE_PLUGINS,
                            f"Extensions/ElieSatPanelGrid/assets/icons/{icon_name}",
                        )
                        pix = LoadPixmap(icon_path) if fileExists(icon_path) else None
                        packages.append((f"{name}-{version}", desc, pix))
                    name = version = desc = status = ""

            if not packages:
                packages.append(("No panels found with Status: Pan", "", None))

        except Exception as e:
            packages.append((f"Error reading panels: {e}", "", None))

        self.menuList = packages
        self["menu"].setList(self.menuList)
        self.updateDescription()
        self.updatePageInfo()
        print(f"[Toolsp] Loaded {len(packages)} panels with icons")

    # ---------------- OK Button ----------------
    def ok(self):
        selected = self["menu"].getCurrent()
        if not selected:
            return
        selected_label = selected[0]
        pkg_name = selected_label.rsplit("-", 1)[0] if "-" in selected_label else selected_label
        self.run_script(pkg_name)

    def run_script(self, pkg_name):
        panels_file = resolveFilename(SCOPE_PLUGINS,
                                     "Extensions/ElieSatPanelGrid/assets/data/panels")
        if not os.path.exists(panels_file):
            print("[Toolsp] Panels file missing")
            return

        script_url = self._find_script(pkg_name)
        if not script_url:
            print("[Toolsp] No script found for", pkg_name)
            return

        cmd = f'wget -q --no-check-certificate "{script_url}" -O - | /bin/sh'
        self.session.open(Console, title=f"Running {pkg_name}...", cmdlist=[cmd], closeOnSuccess=True)

    def _find_script(self, pkg_name):
        file_path = resolveFilename(SCOPE_PLUGINS,
                                    "Extensions/ElieSatPanelGrid/assets/data/panels")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
            block = {}
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                if line.startswith("Package:"):
                    if block.get("Package") == pkg_name:
                        return next((v for v in block.values() if isinstance(v, str) and v.endswith(".sh")), None)
                    block = {"Package": line.split(":", 1)[1].strip()}
                elif "=" in line:
                    key, val = line.split("=", 1)
                    block[key.strip()] = val.strip().strip("'\"")
            return None
        except Exception as e:
            print("[Toolsp] _find_script error:", e)
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
            print(f"[Toolsp] {name} error:", e)

    # ---------------- Exit / Back ----------------
    def go_back_or_exit(self):
        self.close()

    # ---------------- Description & Page Info ----------------
    def updateDescription(self):
        current = self["menu"].getCurrent()
        self["description"].setText(current[1] if current and len(current) > 1 else "")

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

    # ---------------- Update Panels from GitHub ----------------
    def update_data(self):
        url = 'https://raw.githubusercontent.com/eliesatpanelgrid/eliesatpanelgrid/refs/heads/main/assets/data/panels'
        file_path = resolveFilename(SCOPE_PLUGINS,
                                    "Extensions/ElieSatPanelGrid/assets/data/panels")
        try:
            response = requests.get(url)
            if response.status_code != 200:
                print('[Toolsp] Failed to download panels')
                return False
            new_hash = hashlib.md5(response.content).hexdigest()
            local_hash = None
            if os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    local_hash = hashlib.md5(f.read()).hexdigest()
            if local_hash != new_hash:
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                print('[Toolsp] Panels updated from GitHub')
                self.load_panels()
                return True
            return False
        except Exception as e:
            print('[Toolsp] update_data error:', e)
            return False

