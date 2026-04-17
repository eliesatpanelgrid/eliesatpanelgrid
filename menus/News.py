# -*- coding: utf-8 -*-
import os
import urllib
try:
    import urllib.request as urllib2  # Python3
except:
    import urllib2  # Python2

from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.ScrollLabel import ScrollLabel
from Components.Label import Label
from Plugins.Extensions.ElieSatPanelGrid.menus.Helpers import (
    get_local_ip,
    check_internet,
    get_image_name,
    get_python_version,
    get_storage_info,
    get_ram_info,
)
from Plugins.Extensions.ElieSatPanelGrid.__init__ import Version
from enigma import getDesktop


class News(Screen):
    def __init__(self, session):
        # 🔹 Choose skin based on resolution
        screen_width = getDesktop(0).size().width()
        skin_path = "/usr/lib/enigma2/python/Plugins/Extensions/ElieSatPanelGrid/assets/skin/news_hd.xml"
        if screen_width >= 1920:
            skin_path = "/usr/lib/enigma2/python/Plugins/Extensions/ElieSatPanelGrid/assets/skin/news_fhd.xml"

        if os.path.exists(skin_path):
            with open(skin_path, "r") as f:
                self.skin = f.read()
        else:
            # fallback inline skin if missing
            self.skin = """<screen name="News" position="center,center" size="1280,720">
                <eLabel text="News skin missing!" position="center,center" size="400,40"
                    font="Regular;24" halign="center" valign="center" />
            </screen>"""

        Screen.__init__(self, session)
        self.session = session
        self.setTitle(_("Info"))

        # Vertical bars text
        vertical_left = "\n".join(list("Version " + Version))
        vertical_right = "\n".join(list("By ElieSat"))
        self["left_bar"] = Label(vertical_left)
        self["right_bar"] = Label(vertical_right)

        # System info
        self["image_name"] = Label("Image: " + get_image_name())
        self["local_ip"] = Label("IP: " + get_local_ip())
        self["StorageInfo"] = Label(get_storage_info())
        self["RAMInfo"] = Label(get_ram_info())
        self["python_ver"] = Label("Python: " + get_python_version())
        self["net_status"] = Label("Net: " + check_internet())

        # Scrollable GitHub text
        self["github_text"] = ScrollLabel("Loading...")
        self["page_info"] = Label("Page 1/1")

        # Button labels
        self["red"] = Label(_("Close"))
        self["green"] = Label(_(""))
        self["yellow"] = Label(_(""))
        self["blue"] = Label(_(""))

        # Actions
        self["actions"] = ActionMap(
            ["OkCancelActions", "DirectionActions", "ColorActions"],
            {
                "cancel": self.close,
                "red": self.close,
                "up": self.pageUp,
                "down": self.pageDown,
                "left": self.pageUp,
                "right": self.pageDown,
            },
            -1,
        )

        self.total_pages = 1
        self.current_page = 1

        # Load info.txt from GitHub
        self.loadGithubText()

    def updatePageInfo(self):
        self["page_info"].setText("Page %d/%d" % (self.current_page, self.total_pages))

    def pageUp(self):
        self["github_text"].pageUp()
        if self.current_page > 1:
            self.current_page -= 1
        self.updatePageInfo()

    def pageDown(self):
        self["github_text"].pageDown()
        if self.current_page < self.total_pages:
            self.current_page += 1
        self.updatePageInfo()

    def loadGithubText(self):
        try:
            url = "https://raw.githubusercontent.com/eliesat/eliesatpanelgrid/refs/heads/main/assets/data/info.txt"
            try:
                response = urllib2.urlopen(url)
            except:
                response = urllib.urlopen(url)
            data = response.read()
            try:
                data = data.decode("utf-8")
            except:
                pass

            self["github_text"].setText(data)

            # 🔹 Calculate approximate pages
            lines = data.splitlines()
            lines_per_page = 20
            self.total_pages = max(1, (len(lines) + lines_per_page - 1) // lines_per_page)
            self.current_page = 1
            self.updatePageInfo()

        except Exception as e:
            print("Error loading info.txt:", e)
            self["github_text"].setText("Server down or unreachable.")
            self.total_pages = 1
            self.current_page = 1
            self.updatePageInfo()

