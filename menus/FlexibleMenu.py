# -*- coding: utf-8 -*-
import math
from sys import version_info
from threading import Timer

from Tools.LoadPixmap import LoadPixmap
from Tools.Directories import resolveFilename, SCOPE_PLUGINS, fileExists
from Components.GUIComponent import GUIComponent
from Components.MultiContent import (
    MultiContentEntryText,
    MultiContentEntryPixmap,
    MultiContentEntryPixmapAlphaTest,
)
from Screens.Screen import Screen
from skin import parseColor
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


# ---------------- FLEXIBLE MENU ----------------
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

        # -------------------- IMAGE DETECTION --------------------
        def isOpenPLi():
            try:
                if fileExists("/etc/opkg/all-feed.conf"):
                    with open("/etc/opkg/all-feed.conf", "r") as f:
                        data = f.read().lower()
                        if "openpli" in data:
                            return True
            except:
                pass
            return False

        is_pli = isOpenPLi()
        # -----------------------------------------------------------

        # HD/FHD dynamic defaults
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

        # Preload pager pixmaps
        self.ptr_pagerleft = self._loadPixmapSafe("Extensions/ElieSatPanelGrid/assets/icon/pager_left.png")
        self.ptr_pagerright = self._loadPixmapSafe("Extensions/ElieSatPanelGrid/assets/icon/pager_right.png")

        self.itemPixmap = None
        self.selPixmap = None
        self.listWidth = 0
        self.listHeight = 0

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
                    normalized.append((title, desc))
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

        logo = self._cached_logos.get(cls_name)

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

    # --------------------- LIST DISPLAY ---------------------
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

    # --------------------- PAGER ---------------------
    def setpage(self):
        if self.total_pages > 1:
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

    # --------------------- MOVEMENT ---------------------
    def left(self):
        self.move(1, "backwards")

    def right(self):
        self.move(1, "forward")

    def up(self):
        self.move(self.columns, "backwards")

    def down(self):
        if len(self.list) > 0:
            if self.current + self.columns > (len(self.list) - 1) and self.current != (len(self.list) - 1):
                self.current = len(self.list) - 1
                self.setL()
                self.selectionChanged()
            else:
                self.move(self.columns, "forward")

    def move(self, step, direction):
        if len(self.list) > 0:
            self.current = (self.current - step if direction == "backwards" else self.current + step) % len(self.list)
            self.setL()
            self.selectionChanged()

    def getCurrent(self):
        if len(self.list) > 0:
            try:
                return self.list[self.current]
            except Exception:
                return self.list[0]
        return None

    def getSelectedIndex(self):
        return self.current

    def setIndex(self, index):
        try:
            self.current = int(index)
        except Exception:
            self.current = 0
        if self.instance:
            self.setL()
