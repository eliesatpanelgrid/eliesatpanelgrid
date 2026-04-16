# -*- coding: utf-8 -*-
import os
import sys
import math
import socket
import subprocess
from sys import version_info
from threading import Timer

from Plugins.Plugin import PluginDescriptor
from skin import parseColor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.InputBox import InputBox
from Tools.LoadPixmap import LoadPixmap
from Tools.Directories import resolveFilename, SCOPE_PLUGINS, fileExists
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.GUIComponent import GUIComponent
from Components.MultiContent import (
    MultiContentEntryText,
    MultiContentEntryPixmap,
    MultiContentEntryPixmapAlphaTest,
)
from Components.ConfigList import ConfigListScreen
from Components.config import ConfigText, getConfigListEntry
from enigma import (
    eListboxPythonMultiContent,
    eListbox,
    ePixmap,
    eLabel,
    eSize,
    ePoint,
    gFont,
    getDesktop,
    BT_SCALE,
    BT_KEEP_ASPECT_RATIO,
    BT_ALIGN_CENTER,
    RT_HALIGN_CENTER,
    RT_VALIGN_CENTER,
)

# Updated imports for new folder name
from Plugins.Extensions.ElieSatPanelGrid.__init__ import Version
from Plugins.Extensions.ElieSatPanelGrid.menus.Console import Console
from Plugins.Extensions.ElieSatPanelGrid.menus.Iptvadder import Iptvadder
from Plugins.Extensions.ElieSatPanelGrid.menus.Cccamadder import Cccamadder
from Plugins.Extensions.ElieSatPanelGrid.menus.News import News
from Plugins.Extensions.ElieSatPanelGrid.menus.Scripts import Scripts
from Plugins.Extensions.ElieSatPanelGrid.menus.PanelManager import PanelManager
from Plugins.Extensions.ElieSatPanelGrid.menus.PanelManager import is_unlocked, set_unlocked
from Plugins.Extensions.ElieSatPanelGrid.menus.Addons import Addons
from Plugins.Extensions.ElieSatPanelGrid.menus.Deps import Deps
from Plugins.Extensions.ElieSatPanelGrid.menus.Display import Display
from Plugins.Extensions.ElieSatPanelGrid.menus.Feeds import Feeds
from Plugins.Extensions.ElieSatPanelGrid.menus.Imagesdownload import Imagesdownload
from Plugins.Extensions.ElieSatPanelGrid.menus.Imagesbackup import Imagesbackup
from Plugins.Extensions.ElieSatPanelGrid.menus.Picons import Picons
from Plugins.Extensions.ElieSatPanelGrid.menus.Settings import Settings
from Plugins.Extensions.ElieSatPanelGrid.menus.Skins import Skins
from Plugins.Extensions.ElieSatPanelGrid.menus.Softcams import Softcams
from Plugins.Extensions.ElieSatPanelGrid.menus.Tools import Tools
from Plugins.Extensions.ElieSatPanelGrid.menus.Panels import Panels
from Plugins.Extensions.ElieSatPanelGrid.menus.About import Abt
from Plugins.Extensions.ElieSatPanelGrid.menus.Imagesdownloader import Imagesdownloader
from Plugins.Extensions.ElieSatPanelGrid.menus.Piconstudio import Piconstudio
from Plugins.Extensions.ElieSatPanelGrid.menus.Infobox import Infobox
from Plugins.Extensions.ElieSatPanelGrid.menus.Libraries import Libraries
from Plugins.Extensions.ElieSatPanelGrid.menus.Uninstaller import Uninstaller
from Plugins.Extensions.ElieSatPanelGrid.menus.Helpers import (
    get_local_ip,
    check_internet,
    get_image_name,
    get_python_version,
    get_storage_info,
    get_ram_info,
)

# Python 3/2 compatibility
PY3 = version_info[0] == 3
try:
    # Python 3
    from urllib.request import Request as compat_Request, urlopen as compat_urlopen
except ImportError:
    # Python 2
    from urllib2 import Request as compat_Request, urlopen as compat_urlopen

# Installer URL
installer = 'https://raw.githubusercontent.com/eliesat/eliesatpanelgrid/main/__init__.py'


# ---------------- FLEXIBLE MENU ----------------
# ---------- IMAGE DETECTION ----------
def getImageType():
    try:
        if fileExists("/etc/opkg/all-feed.conf"):
            with open("/etc/opkg/all-feed.conf", "r") as f:
                data = f.read().lower()
                if "openpli" in data:
                    return "openpli"
                if "openatv" in data:
                    return "openatv"
                if "openbh" in data:
                    return "openbh"
                if "openvision" in data:
                    return "openvision"
    except Exception:
        pass
    return "unknown"


class FlexibleMenu(GUIComponent):
    _cached_logos = {}

    def __init__(self, list_):
        GUIComponent.__init__(self)

        self.l = eListboxPythonMultiContent()
        self.list = list_ or []
        self.entries = dict()
        self.onSelectionChanged = []
        self.current = 0
        self.total_pages = 1
        self._moving = False

        IMAGE = getImageType()

        # ---------------- HD/FHD defaults ----------------
        if getDesktop(0).size().width() >= 1920:

            if IMAGE == "openpli":
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

            if IMAGE == "openpli":
                self.normalFont = gFont("Regular", 20)
                self.selFont = gFont("Regular", 20)
            else:
                self.normalFont = gFont("Bold", 20)
                self.selFont = gFont("Bold", 20)

            self.boxwidth = 240
            self.boxheight = 240
            self.activeboxwidth = 285
            self.activeboxheight = 285
            self.margin = 30
            self.panelheight = 570
            self.itemPerPage = 18
            self.columns = 6

        # ---------- pager icons ----------
        self.ptr_pagerleft = None
        self.ptr_pagerright = None

        try:
            self.ptr_pagerleft = LoadPixmap(
                resolveFilename(
                    SCOPE_PLUGINS,
                    "Extensions/ElieSatPanelGrid/assets/icon/pager_left.png"
                )
            )
        except Exception:
            pass

        try:
            self.ptr_pagerright = LoadPixmap(
                resolveFilename(
                    SCOPE_PLUGINS,
                    "Extensions/ElieSatPanelGrid/assets/icon/pager_right.png"
                )
            )
        except Exception:
            pass

        self.itemPixmap = None
        self.selPixmap = None
        self.listWidth = 0
        self.listHeight = 0

        # ---------- pager symbols ----------
        if PY3:
            import html
            self.selectedicon = str(html.unescape("&#xe837;"))
            self.unselectedicon = str(html.unescape("&#xe836;"))
        else:
            try:
                import HTMLParser
                h = HTMLParser.HTMLParser()
                self.selectedicon = str(h.unescape("&#xe837;"))
                self.unselectedicon = str(h.unescape("&#xe836;"))
            except Exception:
                self.selectedicon = "*"
                self.unselectedicon = "."

    GUI_WIDGET = eListbox

    # ------------------------------------------------

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
        self.l.setFont(1, self.selFont)
        self.l.setItemHeight(self.panelheight)

        self.skinAttributes = attribs
        self.buildEntry()

        return GUIComponent.applySkin(self, desktop, parent)

    # ------------------------------------------------

    def postWidgetCreate(self, instance):

        self.instance = instance
        instance.setContent(self.l)
        instance.setSelectionEnable(0)
        instance.setScrollbarMode(eListbox.showNever)

        self.pager_left = ePixmap(self.instance)
        self.pager_center = eLabel(self.instance)
        self.pager_right = ePixmap(self.instance)
        self.pagelabel = eLabel(self.instance)

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

        try:

            if self.ptr_pagerleft:
                self.pager_left.setPixmap(self.ptr_pagerleft)

            if self.ptr_pagerright:
                self.pager_right.setPixmap(self.ptr_pagerright)

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

        from threading import Timer
        Timer(0.05, self.setL).start()

    # ------------------------------------------------

    def preWidgetRemove(self, instance):
        instance.setContent(None)
        self.instance = None

    # ------------------------------------------------

    def selectionChanged(self):

        for f in self.onSelectionChanged:
            try:
                f()
            except Exception:
                pass

    # ------------------------------------------------

    def setList(self, list_):

        self.list = list_ or []

        if self.instance:
            self.setL(True)

# ------------------------------------------------

    def buildEntry(self):

        self.entries.clear()

        if not self.list:
            return

        width = self.boxwidth + self.margin
        height = self.boxheight + self.margin

        xoffset = (self.activeboxwidth - self.boxwidth) // 2
        yoffset = (self.activeboxheight - self.boxheight) // 2

        x = 0
        y = 0
        count = 0
        page = 1

        self.total_pages = int(math.ceil(float(len(self.list)) / self.itemPerPage))

        for elem in self.list:

            try:
                name = elem[0]
            except Exception:
                continue

            if count >= self.itemPerPage:
                count = 0
                page += 1
                y = 0

            logo = self._cached_logos.get(name)

            if not logo:

                try:

                    icon_name = name.lower().replace(" ", "_") + ".png"

                    logoPath = resolveFilename(
                        SCOPE_PLUGINS,
                        "Extensions/ElieSatPanelGrid/assets/icons/" + icon_name
                    )

                    if not fileExists(logoPath):

                        logoPath = resolveFilename(
                            SCOPE_PLUGINS,
                            "Extensions/ElieSatPanelGrid/assets/icons/default.png"
                        )

                    if fileExists(logoPath):

                        logo = LoadPixmap(logoPath)
                        self._cached_logos[name] = logo

                except Exception:
                    logo = None

            self.entries[name] = {

                "active": (

                    MultiContentEntryPixmap(
                        pos=(x, y),
                        size=(self.activeboxwidth, self.activeboxheight),
                        png=self.selPixmap,
                        flags=BT_SCALE
                    ),

                    MultiContentEntryPixmapAlphaTest(
                        pos=(x, y),
                        size=(self.activeboxwidth, self.activeboxheight - 40),
                        png=logo,
                        flags=BT_SCALE | BT_ALIGN_CENTER | BT_KEEP_ASPECT_RATIO
                    ),

                    MultiContentEntryText(
                        pos=(x, y + self.activeboxheight - 40),
                        size=(self.activeboxwidth, 35),
                        font=0,
                        text=name,
                        flags=RT_HALIGN_CENTER | RT_VALIGN_CENTER,
                        color=0x00FF8C00
                    ),

                ),

                "u_active": (

                    MultiContentEntryPixmap(
                        pos=(x + xoffset, y + yoffset),
                        size=(self.boxwidth, self.boxheight),
                        png=self.itemPixmap,
                        flags=BT_SCALE
                    ),

                    MultiContentEntryPixmapAlphaTest(
                        pos=(x + xoffset, y + yoffset),
                        size=(self.boxwidth, self.boxheight - 40),
                        png=logo,
                        flags=BT_SCALE | BT_ALIGN_CENTER | BT_KEEP_ASPECT_RATIO
                    ),

                    MultiContentEntryText(
    pos=(x + xoffset - 20, y + yoffset + self.boxheight - 40),
    size=(self.boxwidth + 40, 35),
    font=0,
    text=name,
    flags=RT_HALIGN_CENTER | RT_VALIGN_CENTER
),
                ),

                "page": page
            }

            x += width
            count += 1

            if count % self.columns == 0:
                x = 0
                y += height

        self.setL()

    # ------------------------------------------------

    def setL(self, refresh=False):

        if refresh:
            self.entries.clear()
            self.buildEntry()
            return

        if not self.entries or not self.list:
            self.l.setList([])
            return

        res = [None]

        if self.current >= len(self.list):
            self.current = len(self.list) - 1

        current_key = self.list[self.current][0]

        current = self.entries.get(current_key)

        if not current:
            current_key = next(iter(self.entries))
            current = self.entries[current_key]
            self.current = 0

        current_page = current["page"]

        for _, value in self.entries.items():
            if value["page"] == current_page and value != current:
                res.extend(value["u_active"])

        res.extend(current["active"])

        try:
            self.l.setList([res])
        except Exception:
            self.l.setList([])

        self.setpage()

    # ------------------------------------------------

    def setpage(self):

        if self.total_pages <= 1:

            try:
                self.pager_left.hide()
                self.pager_right.hide()
                self.pager_center.hide()
                self.pagelabel.hide()
            except Exception:
                pass

            return

        self.pagetext = ""

        for i in range(1, self.total_pages + 1):

            if i == self.getCurrentPage():
                self.pagetext += " " + self.selectedicon
            else:
                self.pagetext += " " + self.unselectedicon

        self.pagetext += " "

        self.pagelabel.setText(self.pagetext)

        try:
            w = int(self.pagelabel.calculateSize().width() / 2)
        except Exception:
            w = 100

        y = self.panelheight - 10

        try:

            self.pager_center.resize(eSize(w * 2, 20))
            self.pager_center.move(ePoint((self.listWidth // 2) - w + 20, y))

            self.pager_left.move(ePoint((self.listWidth // 2) - w, y))
            self.pager_right.move(ePoint((self.listWidth // 2) + (w - 16), y))

            self.pager_left.show()
            self.pager_right.show()
            self.pager_center.show()
            self.pagelabel.show()

        except Exception:
            pass

    # ------------------------------------------------

    def getCurrentPage(self):

        if not self.entries or not self.list:
            return 0

        current = self.entries.get(self.list[self.current][0])

        return current["page"] if current else 0

    # -------------------- Optimized Smooth Navigation --------------------
    def _debounced_move(self, step, direction):
        if self._moving:
            return
        self._moving = True
        try:
            if not self.list:
                return
            if direction == "backwards":
                self.current -= step
            else:
                self.current += step
            if self.current >= len(self.list):
                self.current = 0
            elif self.current < 0:
                self.current = len(self.list) - 1
            self.setL()
            self.selectionChanged()
        finally:
            from threading import Timer
            Timer(0.07, self._release_nav_lock).start()

    def _release_nav_lock(self):
        self._moving = False

    def left(self):
        self._debounced_move(1, "backwards")

    def right(self):
        self._debounced_move(1, "forward")

    def up(self):
        self._debounced_move(self.columns, "backwards")

    def down(self):
        if self.list and self.current + self.columns > len(self.list) - 1 and self.current != len(self.list) - 1:
            self.current = len(self.list) - 1
            self.setL()
            self.selectionChanged()
        else:
            self._debounced_move(self.columns, "forward")

    # ---------------------------------------------------------------------

    def getCurrent(self):
        if self.list:
            return self.list[self.current]

    def getSelectedIndex(self):
        return self.current

    def setIndex(self, index):
        self.current = index
        if self.instance:
            self.setL()


# ---------------- MAIN PANEL ----------------
from Plugins.Extensions.ElieSatPanelGrid.menus.PanelManager import PanelManager, is_unlocked

class EliesatPanel(Screen):
    skin = ""

    def __init__(self, session):
        # Detect screen width
        screen_width = 1280
        try:
            screen_width = getDesktop(0).size().width()
        except Exception:
            pass

        # Load skin file
        base_skin_path = "/usr/lib/enigma2/python/Plugins/Extensions/ElieSatPanelGrid/assets/skin/"
        hd_skin = os.path.join(base_skin_path, "eliesatpanel_hd.xml")
        fhd_skin = os.path.join(base_skin_path, "eliesatpanel_fhd.xml")
        skin_file = hd_skin
        if screen_width >= 1920 and os.path.exists(fhd_skin):
            skin_file = fhd_skin
        elif os.path.exists(hd_skin):
            skin_file = hd_skin
        else:
            skin_file = os.path.join(base_skin_path, "eliesatpanel.xml")

        # Read skin
        try:
            with open(skin_file, "r") as f:
                self.skin = f.read()
        except Exception:
            self.skin = """<screen name="ElieSatPanel" position="center,center" size="1280,720" title="ElieSatPanel">
                <eLabel text="Eliesat Panel - Skin Missing" position="center,center" size="400,50"
                    font="Regular;30" halign="center" valign="center" />
            </screen>"""

        Screen.__init__(self, session)

        # --- Widgets ---
        self["menu"] = FlexibleMenu([])
        self["description"] = Label("")
        self["pageinfo"] = Label("")
        self["pagelabel"] = Label("")

        # --- Color buttons ---
        self["red"] = Label("IPTV Adder")
        self["green"] = Label("Cccam Adder")
        self["yellow"] = Label("News")
        self["blue"] = Label("Scripts")

        # --- System info ---
        self["image_name"] = Label("Image: " + get_image_name())
        self["local_ip"] = Label("IP: " + get_local_ip())
        self["StorageInfo"] = Label(get_storage_info())
        self["RAMInfo"] = Label(get_ram_info())
        self["python_ver"] = Label("Python: " + get_python_version())
        self["net_status"] = Label("Net: " + check_internet())

        # Start update timer
        t = Timer(0.5, self.update_me)
        t.start()

        # --- Panel version / side bars ---
        vertical_left = "\n".join(list("Version " + Version))
        vertical_right = "\n".join(list("By ElieSat"))
        self["left_bar"] = Label(vertical_left)
        self["right_bar"] = Label(vertical_right)

        # --- Menu list ---
        self.menuList = [
            ("Addons", "Manage and install plugins"),
            ("Display", "Change your image bootlogos and spinners"),
            ("Feeds", "Update and install feeds"),
            ("Images-download", "Download new images"),
            ("Images-backup", "Enjoy images updated backups"),
            ("Panels", "Explore E2 panels with developers links"),
            ("Picons", "Install and manage channel picons"),
            ("Settings", "Try new channels and frequencies"),
            ("Skins", "Choose and apply skins"),
            ("Softcams", "Manage softcams"),
            ("Tools", "Useful tools and extras"),
            ("About", "About"),
            ("ImagesDownloader", "بلاجين تنزيل صور خام من الموقع الرسمي"),
            ("PiconStudio", "Trial"),
            ("Infobox", "Trial"),
            ("Libraries", "Trial"),
            ("Uninstaller", "Trial"),
            ("Initializer", "Trial"),
            ("Backups", "Trial"),
            ("Bouquetmerger", "Trial"),
            ("Installer", "Trial"),
        ]
        self["menu"].setList(self.menuList)

        # --- Description & page info ---
        self["menu"].onSelectionChanged.append(self.updateDescription)
        self["menu"].onSelectionChanged.append(self.updatePageInfo)
        self.updateDescription()
        self.updatePageInfo()

        # --- Actions ---
        self["setupActions"] = ActionMap(
            ["OkCancelActions", "DirectionActions", "ColorActions", "MenuActions"],
            {
                "cancel": self.close,
                "red": self.openIptvadder,
                "green": self.openCccamadder,
                "yellow": self.openNews,
                "blue": self.openScripts,
                "ok": self.ok,
                "left": self.left,
                "right": self.right,
                "up": self.up,
                "down": self.down,
                "menu": self.open_directory_selector,  # Always open PanelManager
            },
            -1,
        )

    # --- Navigation ---
    def left(self): self["menu"].left()
    def right(self): self["menu"].right()
    def up(self): self["menu"].up()
    def down(self): self["menu"].down()

    # --- OK press ---
    def ok(self):
        current = self["menu"].getCurrent()
        if current:
            name = current[0]

            # Lock submenus if not unlocked
            if not is_unlocked() and name not in ("Tools-panel", "About"):
                self.session.open(MessageBox, "Panel is locked. Unlock via Menu button first.", type=MessageBox.TYPE_ERROR, timeout=5)
                return

            submenu_map = {
                "Addons": Addons,
                "Display": Display,
                "Feeds": Feeds,
                "Images-download": Imagesdownload,
                "Images-backup": Imagesbackup,
                "Panels": Panels,
                "Picons": Picons,
                "Settings": Settings,
                "Skins": Skins,
                "Softcams": Softcams,
                "Tools": Tools,
                "About": Abt,
                "ImagesDownloader": Imagesdownloader,
                "PiconStudio": Piconstudio,
                "Infobox": Infobox,
                "Libraries": Deps,
                "Uninstaller": Uninstaller,
            }
            if name in submenu_map:
                self.session.open(submenu_map[name])
            else:
                self.session.open(MessageBox, f"{name} - Coming Soon", type=MessageBox.TYPE_INFO, timeout=5)

    # --- Color button methods ---
    def openIptvadder(self):
        if not is_unlocked():
            self.session.open(MessageBox, "Panel is locked. Unlock via Menu button first.", type=MessageBox.TYPE_ERROR, timeout=5)
            return
        try: self.session.open(Iptvadder)
        except: self.session.open(MessageBox, "Cannot open Iptvadder.", type=MessageBox.TYPE_ERROR, timeout=5)

    def openCccamadder(self):
        if not is_unlocked():
            self.session.open(MessageBox, "Panel is locked. Unlock via Menu button first.", type=MessageBox.TYPE_ERROR, timeout=5)
            return
        try: self.session.open(Cccamadder)
        except: self.session.open(MessageBox, "Cannot open Cccamadder.", type=MessageBox.TYPE_ERROR, timeout=5)

    def openNews(self):
        if not is_unlocked():
            self.session.open(MessageBox, "Panel is locked. Unlock via Menu button first.", type=MessageBox.TYPE_ERROR, timeout=5)
            return
        try: self.session.open(News)
        except: self.session.open(MessageBox, "Cannot open News.", type=MessageBox.TYPE_ERROR, timeout=5)

    def openScripts(self):
        if not is_unlocked():
            self.session.open(MessageBox, "Panel is locked. Unlock via Menu button first.", type=MessageBox.TYPE_ERROR, timeout=5)
            return
        try: self.session.open(Scripts)
        except: self.session.open(MessageBox, "Cannot open Scripts.", type=MessageBox.TYPE_ERROR, timeout=5)

    # --- Menu button ---
    def open_directory_selector(self):
        # Always allow opening PanelManager to unlock
        self.session.open(PanelManager)

    # --- Description / Page info updates ---
    def updateDescription(self):
        current = self["menu"].getCurrent()
        if current:
            self["description"].setText(current[1] if len(current) > 1 else "")

    def updatePageInfo(self):
        currentPage = self["menu"].getCurrentPage()
        totalPages = self["menu"].total_pages
        self["pageinfo"].setText(f"Page {currentPage}/{totalPages}")
        dots = " ".join(["●" if i == currentPage else "○" for i in range(1, totalPages + 1)])
        self["pagelabel"].setText(dots)

    # --- Update handler ---
    def update_me(self):
        try:
            remote_version = '0.0'
            remote_changelog = ''
            req = compat_Request(installer, headers={'User-Agent': 'Mozilla/5.0'})
            page = compat_urlopen(req).read()
            data = page.decode("utf-8") if PY3 else page.encode("utf-8")

            if data:
                for line in data.split("\n"):
                    if line.startswith("Version"):
                        remote_version = line.split("'")[1]
                    if line.startswith("changelog"):
                        remote_changelog = line.split("'")[1]
                        break

            if float(Version) < float(remote_version):
                self.session.openWithCallback(
                    self.install_update,
                    MessageBox,
                    _("New version %s is available.\n%s\n\nDo you want to install it now?" %
                      (remote_version, remote_changelog)),
                    MessageBox.TYPE_YESNO
                )
        except Exception as e:
            print("[ElieSatPanel] update_me error:", e)

# ---------------- PLUGIN INSTALL ----------------

    def install_update(self, answer=False):
        if answer:
            self.session.open(
                Console,
                title='Updating please wait...',

cmdlist=['wget -q "https://www.dropbox.com/scl/fi/qkmk5xsxwpzdbnpon6hts/installer-grid.sh?rlkey=bylcyjwqvjrj8acrsku07orww&st=mckpf7h0&dl=0" -O - | sh'],
                finishedCallback=self.myCallback,
                closeOnSuccess=False
            )

    def myCallback(self, result=None):
        print("[ElieSatPanel] Update finished:", result)
