# -*- coding: utf-8 -*-
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


class Abt(Screen):

    def __init__(self, session):

        screen_width = getDesktop(0).size().width()

        if screen_width >= 1920:
            skin = """
<screen name="About" position="0,0" size="1920,1080" backgroundColor="transparent" flags="wfNoBorder" title="About">
<ePixmap position="0,0" zPosition="-1" size="1920,1080" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/ElieSatPanelGrid/assets/background/panel_bg.jpg"/>
<eLabel position="0,0" size="1920,130" zPosition="10" backgroundColor="#000000"/>
<eLabel text="● About ElieSatPanel" position="350,0" size="1400,50" zPosition="11" font="Bold;32" halign="left" valign="center" foregroundColor="#E6BE3A" backgroundColor="#000000"/>
<eLabel position="0,130" size="80,870" zPosition="10" backgroundColor="#000000"/>
<eLabel position="1840,130" size="80,870" zPosition="10" backgroundColor="#000000"/>
<widget name="about_text" position="200,180" size="1200,780" zPosition="12" font="Bold;32" halign="left" valign="top" foregroundColor="#E6BE3A" transparent="1"/>
<widget name="page_info" position="1700,940" size="200,60" zPosition="12" font="Bold;32" halign="left" valign="center" foregroundColor="#E6BE3A" transparent="1"/>
<widget source="global.CurrentTime" render="Label" position="1350,180" size="500,35" zPosition="12" font="Bold;32" halign="center" valign="center" foregroundColor="#E6BE3A" transparent="1"><convert type="ClockToText">Format %A %d %B</convert></widget>
<widget source="global.CurrentTime" render="Label" position="1350,220" size="500,35" zPosition="12" font="Bold;32" halign="center" valign="center" foregroundColor="#E6BE3A" transparent="1"><convert type="ClockToText">Format %H:%M:%S</convert></widget>
<widget name="image_name" position="1470,420" size="420,35" zPosition="12" font="Bold;32" halign="left" valign="center" foregroundColor="#E6BE3A" transparent="1"/>
<widget name="python_ver" position="1470,460" size="420,35" zPosition="12" font="Bold;32" halign="left" valign="center" foregroundColor="#E6BE3A" transparent="1"/>
<widget name="local_ip" position="1470,500" size="420,35" zPosition="12" font="Bold;32" halign="left" valign="center" foregroundColor="#E6BE3A" transparent="1"/>
<widget name="StorageInfo" position="1470,540" size="420,35" zPosition="12" font="Bold;32" halign="left" valign="center" foregroundColor="#E6BE3A" transparent="1"/>
<widget name="RAMInfo" position="1470,580" size="420,35" zPosition="12" font="Bold;32" halign="left" valign="center" foregroundColor="#E6BE3A" transparent="1"/>
<widget name="net_status" position="1470,620" size="420,35" zPosition="12" font="Bold;32" halign="left" valign="center" foregroundColor="#E6BE3A" transparent="1"/>
<widget name="left_bar" position="20,160" size="60,860" zPosition="20" font="Regular;26" halign="center" valign="top" foregroundColor="#E6BE3A" backgroundColor="#000000"/>
<widget name="right_bar" position="1860,160" size="60,860" zPosition="20" font="Regular;26" halign="center" valign="top" foregroundColor="#E6BE3A" backgroundColor="#000000"/>
</screen>
"""
        else:
            skin = """
<screen name="About" position="0,0" size="1280,720" backgroundColor="transparent" flags="wfNoBorder" title="About">
<ePixmap position="0,0" zPosition="-1" size="1280,720" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/ElieSatPanelGrid/assets/background/panel_bg.jpg"/>
<eLabel position="0,0" size="1280,90" zPosition="10" backgroundColor="#000000"/>
<eLabel text="● About ElieSatPanel" position="200,0" size="900,40" zPosition="11" font="Bold;24" halign="left" valign="center" foregroundColor="#E6BE3A" backgroundColor="#000000"/>
<eLabel position="0,90" size="60,560" zPosition="10" backgroundColor="#000000"/>
<eLabel position="1220,90" size="60,560" zPosition="10" backgroundColor="#000000"/>
<widget name="about_text" position="120,120" size="760,480" zPosition="12" font="Regular;22" halign="left" valign="top" foregroundColor="#E6BE3A" transparent="1"/>
<widget name="page_info" position="1040,640" size="200,40" zPosition="12" font="Regular;22" halign="left" valign="center" foregroundColor="#E6BE3A" transparent="1"/>
<widget source="global.CurrentTime" render="Label" position="900,120" size="340,30" zPosition="12" font="Regular;22" halign="center" valign="center" foregroundColor="#E6BE3A" transparent="1"><convert type="ClockToText">Format %A %d %B</convert></widget>
<widget source="global.CurrentTime" render="Label" position="900,150" size="340,30" zPosition="12" font="Regular;22" halign="center" valign="center" foregroundColor="#E6BE3A" transparent="1"><convert type="ClockToText">Format %H:%M:%S</convert></widget>
<widget name="image_name" position="900,260" size="340,30" zPosition="12" font="Regular;22" halign="left" valign="center" foregroundColor="#E6BE3A" transparent="1"/>
<widget name="python_ver" position="900,290" size="340,30" zPosition="12" font="Regular;22" halign="left" valign="center" foregroundColor="#E6BE3A" transparent="1"/>
<widget name="local_ip" position="900,320" size="340,30" zPosition="12" font="Regular;22" halign="left" valign="center" foregroundColor="#E6BE3A" transparent="1"/>
<widget name="StorageInfo" position="900,350" size="340,30" zPosition="12" font="Regular;22" halign="left" valign="center" foregroundColor="#E6BE3A" transparent="1"/>
<widget name="RAMInfo" position="900,380" size="340,30" zPosition="12" font="Regular;22" halign="left" valign="center" foregroundColor="#E6BE3A" transparent="1"/>
<widget name="net_status" position="900,410" size="340,30" zPosition="12" font="Regular;22" halign="left" valign="center" foregroundColor="#E6BE3A" transparent="1"/>
<widget name="left_bar" position="10,100" size="40,540" zPosition="20" font="Regular;18" halign="center" valign="top" foregroundColor="#E6BE3A" backgroundColor="#000000"/>
<widget name="right_bar" position="1230,100" size="40,540" zPosition="20" font="Regular;18" halign="center" valign="top" foregroundColor="#E6BE3A" backgroundColor="#000000"/>
</screen>
"""

        self.skin = skin
        Screen.__init__(self, session)
        self.session = session

        about_lines = [
            "● ElieSatPanel, Enjoy a smoother Enigma2 experience!",
            "Lightweight Enigma2 plugin",
            "Quick access to system info, shortcuts & tools",
            "",
            "◆ Features:",
            "  • Display system info (Image, IP, Storage, RAM, Python)",
            "  • Scrollable news, updates & GitHub info",
            "  • Version always visible",
            "  • Works on HD & FHD screens",
            "",
            "◆ Version Info:",
            "  Beta (weekly updates)",
            "",
            "◆ Credits:",
            "  Developed by ElieSat",
            "  Special thanks: JePro & Eagle Servers",
            "",
            "◆ Support:",
            "  WhatsApp: +961 70 787 872",
            "  GitHub: github.com/eliesat/eliesatpanel",
            "",
            "◆ Note:",
            "  Thank you for using ElieSatPanel!",
        ]

        self["about_text"] = ScrollLabel("\n".join(about_lines))
        self["page_info"] = Label("Page 1/1")
        self["left_bar"] = Label("\n".join(list("Version " + Version)))
        self["right_bar"] = Label("\n".join(list("By ElieSat")))

        self["image_name"] = Label("Image: " + get_image_name())
        self["local_ip"] = Label("IP: " + get_local_ip())
        self["StorageInfo"] = Label(get_storage_info())
        self["RAMInfo"] = Label(get_ram_info())
        self["python_ver"] = Label("Python: " + get_python_version())
        self["net_status"] = Label("Net: " + check_internet())

        self["actions"] = ActionMap(
            ["OkCancelActions", "DirectionActions"],
            {
                "cancel": self.close,
                "up": self.pageUp,
                "down": self.pageDown,
                "left": self.pageUp,
                "right": self.pageDown,
            },
            -1,
        )

    def pageUp(self):
        self["about_text"].pageUp()

    def pageDown(self):
        self["about_text"].pageDown()
