# -*- coding: utf-8 -*-
import os
import sys
import math
import hashlib
import requests
import socket
from sys import version_info
from threading import Timer

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

# Plugin-specific imports (updated for ElieSatPanelGrid)
from Plugins.Extensions.ElieSatPanelGrid.__init__ import Version
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

# ---------------- Utility Functions & Constants ----------------
ADDONS_FILE = "/home/addons.txt"

def update_addons_file(pkg_name, is_installed):
    """Adds or removes the package name from /home/addons.txt."""
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
    """Check if plugin directory exists in Enigma2 Extensions."""
    if not plugin_name:
        return False
    base_dir = "/usr/lib/enigma2/python/Plugins/Extensions/"
    target = plugin_name.strip()
    
    if os.path.exists(os.path.join(base_dir, target)):
        return True
    
    try:
        if os.path.exists(base_dir):
            installed_folders = [f.lower() for f in os.listdir(base_dir)]
            if target.lower() in installed_folders:
                return True
    except Exception:
        pass
    return False

INSTALLER_URL = "https://raw.githubusercontent.com/eliesatpanelgrid/beta/main/installer.sh"
EXTENSIONS_URL = "https://raw.githubusercontent.com/eliesatpanelgrid/eliesatpanelgrid/refs/heads/main/assets/data/extensions"
LOCAL_EXTENSIONS = "/usr/lib/enigma2/python/Plugins/Extensions/ElieSatPanelGrid/assets/data/extensions"


# ---------------- FLEXIBLE MENU COMPONENT ----------------
class FlexibleMenu(GUIComponent):
    """A grid-like flexible menu that accepts a list of (title, description) pairs."""

    _cached_logos = {}

    def __init__(self, list_=None, parent=None):
        GUIComponent.__init__(self)
        self.parent = parent
        self.l = eListboxPythonMultiContent()
        self.list = list_ or []
        self._normalize_list()
        self.entries = dict()
        self.onSelectionChanged = []
        self.current = 0
        self.total_pages = 1

        def isOpenPLi():
            try:
                if fileExists("/etc/opkg/all-feed.conf"):
                    with open("/etc/opkg/all-feed.conf", "r") as f:
                        data = f.read().lower()
                        if "openpli" in data:
                            return True
            except Exception:
                pass
            return False

        is_pli = isOpenPLi()

        if getDesktop(0).size().width() >= 1920:
            if is_pli:
                self.normalFont = gFont("Regular", 30)
                self.selFont = gFont("Regular", 30)
            else:
                self.normalFont = gFont("Bold", 30)
                self.selFont = gFont("Bold", 30)
            self.boxwidth = 240
            self.boxheight = 240
            self.activeboxwidth = 285
            self.activeboxheight = 285
            self.margin = 30
            self.panelheight = 570
            self.itemPerPage = 18
            self.columns = 6
        else:
            if is_pli:
                self.normalFont = gFont("Regular", 20)
                self.selFont = gFont("Regular", 20)
            else:
                self.normalFont = gFont("Bold", 20)
                self.selFont = gFont("Bold", 20)
            self.boxwidth = 160
            self.boxheight = 180
            self.activeboxwidth = 210
            self.activeboxheight = 210
            self.margin = 10
            self.panelheight = 380
            self.itemPerPage = 12
            self.columns = 4

        self.selectedicon = "●"
        self.unselectedicon = "○"

        self.ptr_dot_on = self._loadPixmapSafe("Extensions/ElieSatPanelGrid/assets/icon/dot_on.png")
        self.ptr_dot_off = self._loadPixmapSafe("Extensions/ElieSatPanelGrid/assets/icon/dot_off.png")
        self.ptr_pagerleft = self._loadPixmapSafe("Extensions/ElieSatPanelGrid/assets/icon/pager_left.png")
        self.ptr_pagerright = self._loadPixmapSafe("Extensions/ElieSatPanelGrid/assets/icon/pager_right.png")

        self.itemPixmap = None
        self.selPixmap = None
        self.listWidth = 0
        self.listHeight = 0
        self.dots = []

    def _loadPixmapSafe(self, path):
        try:
            return LoadPixmap(resolveFilename(SCOPE_PLUGINS, path))
        except Exception:
            return None

    def _normalize_list(self):
        normalized = []
        for item in (self.list or []):
            try:
                if isinstance(item, (list, tuple)) and len(item) >= 1:
                    title = str(item[0])
                    desc = str(item[1]) if len(item) > 1 else ""
                    extra = tuple(item[2:]) if len(item) > 2 else ()
                    normalized.append((title, desc) + extra)
                else:
                    normalized.append((str(item), ""))
            except Exception:
                continue
        self.list = normalized

    def getList(self):
        return self.list

    def applySkin(self, desktop, parent):
        attribs = []
        for (attrib, value) in getattr(self, "skinAttributes", []):
            try:
                if attrib == "itemPerPage":
                    self.itemPerPage = int(value)
                    self.columns = max(1, self.itemPerPage // 2)
                elif attrib == "panelheight":
                    self.panelheight = int(value)
                elif attrib == "margin":
                    self.margin = int(value)
                elif attrib == "boxSize":
                    if "," in value:
                        self.boxwidth, self.boxheight = [int(v) for v in value.split(",")]
                    else:
                        self.boxwidth = self.boxheight = int(value)
                elif attrib == "activeSize":
                    if "," in value:
                        self.activeboxwidth, self.activeboxheight = [int(v) for v in value.split(",")]
                    else:
                        self.activeboxwidth = self.activeboxheight = int(value)
                elif attrib == "size":
                    self.listWidth, self.listHeight = [int(v) for v in value.split(",")]
                    if self.instance:
                        self.instance.resize(eSize(self.listWidth, self.listHeight))
                elif attrib == "itemPixmap":
                    self.itemPixmap = LoadPixmap(value)
                elif attrib == "selPixmap":
                    self.selPixmap = LoadPixmap(value)
                else:
                    attribs.append((attrib, value))
            except Exception:
                continue

        self.l.setFont(0, self.normalFont)
        self.l.setItemHeight(self.panelheight)
        self.skinAttributes = attribs
        self.buildEntry()
        return GUIComponent.applySkin(self, desktop, parent)

    GUI_WIDGET = eListbox

    def postWidgetCreate(self, instance):
        self.instance = instance
        instance.setContent(self.l)
        instance.setSelectionEnable(0)
        instance.setScrollbarMode(eListbox.showNever)

        self.pager_left = ePixmap(self.instance)
        self.pager_center = eLabel(self.instance)
        self.pager_right = ePixmap(self.instance)
        self.pagelabel = eLabel(self.instance)
        self.countlabel = eLabel(self.instance)

        isFHD = getDesktop(0).size().width() >= 1920
        font_size = 22 if isFHD else 16
        self.countlabel.setFont(gFont("Regular", font_size))
        self.countlabel.setVAlign(eLabel.alignCenter)
        self.countlabel.setHAlign(eLabel.alignRight)
        self.countlabel.setTransparent(1)
        self.countlabel.setZPosition(100)

        self.pagelabel.setFont(gFont("Icons", 18))
        self.pagelabel.setVAlign(eLabel.alignCenter)
        self.pagelabel.setHAlign(eLabel.alignCenter)
        self.pagelabel.setBackgroundColor(parseColor("#FF272727"))
        self.pagelabel.setTransparent(1)
        self.pagelabel.setZPosition(100)
        self.pagelabel.move(ePoint(0, self.panelheight - 10))
        self.pagelabel.resize(eSize(1660, 20))

        self.pager_center.setBackgroundColor(parseColor("#00272727"))
        self.pager_left.resize(eSize(20, 20))
        self.pager_right.resize(eSize(20, 20))
        if self.ptr_pagerleft:
            self.pager_left.setPixmap(self.ptr_pagerleft)
        if self.ptr_pagerright:
            self.pager_right.setPixmap(self.ptr_pagerright)
        try:
            self.pager_left.setScale(2)
            self.pager_right.setScale(2)
            self.pager_left.setAlphatest(2)
            self.pager_right.setAlphatest(2)
        except Exception:
            pass
        self.pager_left.hide()
        self.pager_right.hide()
        self.pager_center.hide()
        self.pagelabel.hide()

    def preWidgetRemove(self, instance):
        instance.setContent(None)
        self.instance = None

    def selectionChanged(self):
        for f in self.onSelectionChanged:
            try:
                f()
            except Exception:
                pass

    def setList(self, list_):
        self.list = list_ or []
        self._normalize_list()
        if self.current >= len(self.list):
            self.current = max(0, len(self.list) - 1)
        if self.instance:
            self.setL(True)

    def _get_item_logo(self, full_text):
        if "-" in full_text:
            pkg_name = full_text.rsplit("-", 1)[0]
        else:
            pkg_name = full_text

        is_installed = is_plugin_installed(pkg_name)
        
        icon_file = "addons1.png" if is_installed else "addons.png"
        icon_path = resolveFilename(SCOPE_PLUGINS, f"Extensions/ElieSatPanelGrid/assets/icons/{icon_file}")

        if fileExists(icon_path):
            if icon_file not in self._cached_logos:
                self._cached_logos[icon_file] = LoadPixmap(icon_path)
            return self._cached_logos[icon_file]

        cls_name = getattr(getattr(self, "parent", None), "__class__", None)
        cls_name = cls_name.__name__.lower() if cls_name else "default"

        if cls_name not in self._cached_logos:
            logoPath = resolveFilename(
                SCOPE_PLUGINS,
                f"Extensions/ElieSatPanelGrid/assets/icons/{cls_name}.png"
            )
            if not fileExists(logoPath):
                logoPath = resolveFilename(
                    SCOPE_PLUGINS,
                    "Extensions/ElieSatPanelGrid/assets/icons/default.png"
                )
            self._cached_logos[cls_name] = LoadPixmap(logoPath) if fileExists(logoPath) else None

        return self._cached_logos.get(cls_name)

    def buildEntry(self):
        self.entries.clear()
        if len(self.list) == 0:
            return

        width = self.boxwidth + self.margin
        height = self.boxheight + self.margin
        xoffset = (self.activeboxwidth - self.boxwidth) // 2
        yoffset = (self.activeboxheight - self.boxheight) // 2
        isFHD = getDesktop(0).size().width() >= 1920
        self.total_pages = int(math.ceil(float(len(self.list)) / self.itemPerPage)) if self.itemPerPage > 0 else 1

        is_in_submenu = getattr(self.parent, "in_submenu", False)

        for page_index in range(self.total_pages):
            x = 0
            y = 0
            for idx in range(page_index * self.itemPerPage, min((page_index + 1) * self.itemPerPage, len(self.list))):
                elem = self.list[idx]
                try:
                    full_text = elem[0]
                    desc = elem[1] if len(elem) > 1 else ""
                except Exception:
                    continue

                if "-" in full_text:
                    name, version = full_text.rsplit("-", 1)
                else:
                    name = full_text
                    version = ""

                if is_in_submenu:
                    logo = self._get_item_logo(full_text)
                else:
                    cls_name = getattr(getattr(self, "parent", None), "__class__", None)
                    cls_name = cls_name.__name__.lower() if cls_name else "default"
                    logo = self._cached_logos.get(cls_name)

                key = full_text
                active_height = self.activeboxheight
                inactive_height = self.boxheight
                page = page_index + 1
                text_width = self.activeboxwidth
                text_x = x + xoffset + (self.boxwidth - text_width) // 2

                active_texts = (
                    MultiContentEntryText(pos=(x, y + self.activeboxheight - (60 if isFHD else 65)),
                                          size=(text_width, 35), font=0, text=name,
                                          flags=RT_HALIGN_CENTER | RT_VALIGN_CENTER,
                                          color=0x00FF8C00),
                    MultiContentEntryText(pos=(x, y + self.activeboxheight - (30 if isFHD else 45)),
                                          size=(text_width, 35), font=0, text=version,
                                          flags=RT_HALIGN_CENTER | RT_VALIGN_CENTER,
                                          color=0x00FF8C00),
                )
                inactive_texts = (
                    MultiContentEntryText(pos=(text_x, y + yoffset + self.boxheight - (60 if isFHD else 65)),
                                          size=(text_width, 35), font=0, text=name,
                                          flags=RT_HALIGN_CENTER | RT_VALIGN_CENTER),
                    MultiContentEntryText(pos=(text_x, y + yoffset + self.boxheight - (30 if isFHD else 45)),
                                          size=(text_width, 35), font=0, text=version,
                                          flags=RT_HALIGN_CENTER | RT_VALIGN_CENTER),
                )

                self.entries[key] = {
                    "active": (
                        MultiContentEntryPixmap(pos=(x - 5, y - 5), size=(self.activeboxwidth + 10, active_height + 10),
                                                png=self.selPixmap, flags=BT_SCALE),
                        MultiContentEntryPixmapAlphaTest(pos=(x, y), size=(self.activeboxwidth, active_height - 60),
                                                         png=logo, flags=BT_SCALE | BT_ALIGN_CENTER | BT_KEEP_ASPECT_RATIO),
                    ) + active_texts,
                    "u_active": (
                        MultiContentEntryPixmap(pos=(x + xoffset, y + yoffset), size=(self.boxwidth, inactive_height),
                                                png=self.itemPixmap, flags=BT_SCALE),
                        MultiContentEntryPixmapAlphaTest(pos=(x + xoffset, y + yoffset),
                                                         size=(self.boxwidth, inactive_height - 60),
                                                         png=logo, flags=BT_SCALE | BT_ALIGN_CENTER | BT_KEEP_ASPECT_RATIO),
                    ) + inactive_texts,
                    "page": page
                }

                x += width
                if (idx % self.columns) == (self.columns - 1):
                    x = 0
                    y += height

        self.setL()

    def setL(self, refresh=False):
        if refresh:
            self.entries.clear()
            self.buildEntry()
            return
        if len(self.entries) > 0 and len(self.list) > 0:
            res = [None]
            if self.current > (len(self.list) - 1):
                self.current = (len(self.list) - 1)
            try:
                current_key = self.list[self.current][0]
                current = self.entries.get(current_key)
            except Exception:
                current = None
                if len(self.entries):
                    first_key = next(iter(self.entries))
                    current = self.entries[first_key]
                    self.current = 0

            current_page = current.get("page") if current else 1
            page_items = []
            for _, value in self.entries.items():
                if value["page"] == current_page:
                    page_items.extend(value["active"] if value == current else value["u_active"])

            try:
                self.l.setList([res + page_items])
            except Exception:
                try:
                    self.l.setList([])
                except Exception:
                    pass

            self.setpage()
        else:
            try:
                self.l.setList([])
            except Exception:
                pass

    def setpage(self):
        # Update counter label at bottom right
        if self.countlabel:
            count = len(self.list)
            is_in_sub = getattr(self.parent, "in_submenu", False)
            label_text = f"Items: {count}" if is_in_sub else f"Categories: {count}"
            self.countlabel.setText(label_text)
            
            cw = 220
            ch = 30
            cy = self.panelheight - 25
            cx = self.listWidth - cw - 20 if self.listWidth > 0 else 1400
            self.countlabel.move(ePoint(cx, cy))
            self.countlabel.resize(eSize(cw, ch))
            self.countlabel.show()

        # Update dot pagination indicators
        if self.ptr_dot_on and self.ptr_dot_off and self.total_pages > 1:
            dot_size = 14
            dot_margin = 10
            total_dots_w = (self.total_pages * dot_size) + ((self.total_pages - 1) * dot_margin)
            start_x = (self.listWidth // 2) - (total_dots_w // 2) if self.listWidth > 0 else 500
            y = self.panelheight - 18

            # Hide text pagers when using dots
            self.pager_left.hide()
            self.pager_right.hide()
            self.pager_center.hide()
            self.pagelabel.hide()

            # Create or adjust dot pixmaps dynamically
            while len(self.dots) < self.total_pages:
                dot = ePixmap(self.instance)
                dot.resize(eSize(dot_size, dot_size))
                try:
                    dot.setScale(1)
                    dot.setAlphatest(2)
                except Exception:
                    pass
                dot.setZPosition(100)
                self.dots.append(dot)

            curr_p = self.getCurrentPage()
            for idx, dot in enumerate(self.dots):
                if idx < self.total_pages:
                    dot_x = start_x + (idx * (dot_size + dot_margin))
                    dot.move(ePoint(dot_x, y))
                    dot.setPixmap(self.ptr_dot_on if (idx + 1) == curr_p else self.ptr_dot_off)
                    dot.show()
                else:
                    dot.hide()
        elif self.total_pages > 1:
            # Fallback to standard text pager if image assets are missing
            for d in self.dots:
                d.hide()
            self.pagetext = ""
            if len(self.list) > 0:
                for i in range(1, self.total_pages + 1):
                    self.pagetext += " " + (self.selectedicon if i == self.getCurrentPage() else self.unselectedicon)
                self.pagetext += " "
            self.pagelabel.setText(self.pagetext)
            try:
                w = int(self.pagelabel.calculateSize().width() / 2)
            except Exception:
                w = 100
            y = self.panelheight - 10
            try:
                self.pager_center.resize(eSize((w * 2), 20))
                self.pager_center.move(ePoint((self.listWidth // 2) - w + 20, y))
                self.pager_left.move(ePoint((self.listWidth // 2) - w, y))
                self.pager_right.move(ePoint((self.listWidth // 2) + (w - 16), y))
            except Exception:
                pass
            try:
                self.pager_left.show()
                self.pager_right.show()
                self.pager_center.show()
                self.pagelabel.show()
            except Exception:
                pass
        else:
            for d in self.dots:
                d.hide()
            try:
                self.pager_left.hide()
                self.pager_right.hide()
                self.pager_center.hide()
                self.pagelabel.hide()
            except Exception:
                pass

    def getCurrentPage(self):
        if len(self.entries) > 0 and len(self.list) > 0:
            if self.current > (len(self.list) - 1):
                self.current = (len(self.list) - 1)
            try:
                current_key = self.list[self.current][0]
                current = self.entries.get(current_key, None)
                if current:
                    return current["page"]
            except Exception:
                pass
            return 1
        return 1

    def left(self):
        if self.current > 0:
            self.current -= 1
            self.setL()
            self.selectionChanged()

    def right(self):
        if self.current < len(self.list) - 1:
            self.current += 1
            self.setL()
            self.selectionChanged()

    def up(self):
        if self.current >= self.columns:
            self.current -= self.columns
            self.setL()
            self.selectionChanged()

    def down(self):
        if self.current + self.columns < len(self.list):
            self.current += self.columns
            self.setL()
            self.selectionChanged()

    def getCurrent(self):
        if 0 <= self.current < len(self.list):
            return self.list[self.current]
        return None

    def getSelectedIndex(self):
        return self.current

    def setIndex(self, index):
        if 0 <= index < len(self.list):
            self.current = index
            self.setL()
            self.selectionChanged()


# ---------------- ADDONS SCREEN CLASS ----------------
class Addons(Screen):
    skin = ""

    def __init__(self, session):
        self.session = session
        self.in_submenu = False
        self.submenu_title = None
        self.previous_index = 0
        self.submenu_indices = {}
        self.current_running_pkg = None

        Screen.__init__(self, session)

        unlock_ok = is_device_unlocked()
        unlock_file_exists = os.path.exists("/etc/eliesat_unlocked.cfg")
        main_mac_exists = os.path.exists("/etc/eliesat_main_mac.cfg")

        if not unlock_ok or not unlock_file_exists or not main_mac_exists:
            self.close()
            return

        self.load_skin()
        self.load_icon()

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

    def go_back_or_exit(self):
        if self.in_submenu:
            self.load_main_menu()
        else:
            self.close()

    def openIptvadder(self):
        self.session.open(Iptvadder)

    def openCccamadder(self):
        self.session.open(Cccamadder)

    def openNews(self):
        self.session.open(News)

    def openScripts(self):
        self.session.open(Scripts)

    def load_skin(self):
        screen_width = 1280
        try:
            screen_width = getDesktop(0).size().width()
        except Exception:
            pass

        base_skin_path = "/usr/lib/enigma2/python/Plugins/Extensions/ElieSatPanelGrid/assets/skin/"
        skin_files = {
            "hd": os.path.join(base_skin_path, "eliesatpanelsub_hd.xml"),
            "fhd": os.path.join(base_skin_path, "eliesatpanelsub_fhd.xml"),
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
        except Exception:
            self.skin = """<screen name="Addons" position="center,center" size="1280,720">
                                <eLabel text="Skin Missing" position="center,center" size="400,50"
                                font="Regular;30" halign="center" valign="center"/>
                            </screen>"""

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

        self["red"] = Label("IPTV Adder")
        self["green"] = Label("Cccam Adder")
        self["yellow"] = Label("News")
        self["blue"] = Label("Scripts")

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

    def start_background_updates(self):
        if not has_internet():
            return
        Timer(1, self.update_extensions_from_github).start()

    def update_extensions_from_github(self):
        try:
            r = requests.get(EXTENSIONS_URL, timeout=5)
            if r.status_code == 200 and r.text.strip():
                with open(LOCAL_EXTENSIONS, "w") as f:
                    f.write(r.text)
        except Exception as e:
            print("[Addons] Update extensions error:", e)

    def load_main_menu(self):
        self.in_submenu = False
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
        self.updateDescription()
        self.updatePageInfo()

    def load_sub_menu(self, status, title):
        self.in_submenu = True
        self.submenu_title = title
        items = []
        saved = self.submenu_indices.get(title, 0)

        try:
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
                    statuses = raw.replace(",", " ").split()

                    if status in statuses:
                        pkg_counts[name] = pkg_counts.get(name, 0) + 1
                        script_key = f"{name}-{pkg_counts[name]}"
                        items.append(("%s-%s" % (name, version), desc, script_key, name))

                    name = version = desc = ""

            if not items:
                items = [("No packages", "", "", "")]

        except Exception as e:
            items = [("Error", str(e), "", "")]

        self["menu"].setList(items)
        self["menu"].setIndex(saved)
        self.updateDescription()
        self.updatePageInfo()

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

    def _find_script_url(self, script_key):
        """Extracts the execution URL using the unique script key (e.g., Ipaudiopro-1)."""
        try:
            with open(LOCAL_EXTENSIONS, "r") as f:
                lines = f.read().splitlines()

            for line in lines:
                line = line.strip()
                if line.startswith(f"{script_key}="):
                    url = line.split("=", 1)[1].strip().strip("'\"")
                    return url
        except Exception as e:
            print("[Addons] Error finding script URL:", e)
        return None

    def run_selected_script(self):
        selected = self["menu"].getCurrent()
        if not selected or len(selected) < 4:
            return

        selected_label = selected[0]
        script_key = selected[2]   # e.g., "Ipaudiopro-1" or "Ipaudiopro-2"
        real_name = selected[3]    # e.g., "Ipaudiopro"

        if not os.path.exists(LOCAL_EXTENSIONS) or not script_key:
            return

        script_url = self._find_script_url(script_key)
        if not script_url:
            return

        self.current_running_pkg = real_name
        is_installed = is_plugin_installed(real_name)

        if is_installed:
            cmd = f'wget -q --no-check-certificate "{script_url}" -O - | /bin/sh -s uninstall'
            action_title = f"Uninstalling {selected_label}..."
        else:
            cmd = f'wget -q --no-check-certificate "{script_url}" -O - | /bin/sh'
            action_title = f"Installing {selected_label}..."

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
