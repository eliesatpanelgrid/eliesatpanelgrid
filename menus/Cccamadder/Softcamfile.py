# -*- coding: utf-8 -*-
import os
from enigma import getDesktop
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap
from Tools.LoadPixmap import LoadPixmap
from Tools.Directories import fileExists, resolveFilename, SCOPE_PLUGINS

# Direct import for Version without fallback
from Plugins.Extensions.ElieSatPanelGrid.__init__ import Version

# Panel fallback preserved
try:
    from Plugins.Extensions.ElieSatPanelGrid.__init__ import Panel
except ImportError:
    Panel = "ElieSatPanel"

try:
    from Components.Language import _
except ImportError:
    def _(txt):
        return txt

from Plugins.Extensions.ElieSatPanelGrid.menus.Helpers import (
    get_local_ip,
    check_internet,
    get_image_name,
    get_python_version,
    get_storage_info,
    get_ram_info
)

try:
    from Plugins.Extensions.ElieSatPanelGrid.menus.Helpers import SystemInfo
except ImportError:
    class SystemInfo(object):
        def memInfo(self, *args, **kwargs): pass
        def FlashMem(self, *args, **kwargs): pass
        def devices(self, *args, **kwargs): pass
        def mainInfo(self, *args, **kwargs): pass
        def cpuinfo(self, *args, **kwargs): pass
        def getPythonVersionString(self, *args, **kwargs): pass
        def getGStreamerVersionString(self, *args, **kwargs): pass


class Softcamfile(Screen):

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session

        # Load the exact same skin file as Cccamadder
        try:
            skin_file = resolveFilename(SCOPE_PLUGINS, "Extensions/ElieSatPanelGrid/menus/Cccamadder/Cccamadder_fhd.xml")
            with open(skin_file, "r") as f:
                self.skin = f.read()
        except Exception as e:
            print("[Showstatus] Critical Error Reading Skin File:", e)
            self.skin = "<screen name='Showstatus' position='center,center' size='1920,1080' backgroundColor='#000000'/>"

        self.setTitle(_("ServerEagleSat - Show Status"))
        self.system_info = SystemInfo()

        # Navigation and Exit action maps
        self["shortcuts"] = ActionMap(
            ["ShortcutActions", "WizardActions", "ColorActions"],
            {
                "cancel": self.exit,
                "back": self.exit,
            }, -1
        )

        # Standard interface elements shared with the main screen
        self["left_bar"] = Label("\n".join(list("Version " + str(Version))))
        self["right_bar"] = Label("\n".join(list("By ElieSat")))
        self["python_ver"] = Label("Python: " + str(get_python_version()))
        self["image_name"] = Label("Image: " + str(get_image_name()))
        self["local_ip"] = Label("IP: " + str(get_local_ip()))
        self["ipInfo"] = Label(str(get_local_ip()))
        self["internet"] = Label(_("Connected") if check_internet() == "Online" else _("Disconnected"))
        self["StorageInfo"] = Label(str(get_storage_info()))
        self["RAMInfo"] = Label(str(get_ram_info()))
        self["net_status"] = Label("Net: " + str(check_internet()))

        self["Version"] = Label(_("V" + str(Version)))
        self["Panel"] = Label(_(str(Panel)))
        self["boxicon"] = Pixmap()

        self["red"] = Label(_("Exit"))
        self["green"] = Label("")
        self["yellow"] = Label("")
        self["blue"] = Label("")

        self.onLayoutFinish.append(self.loadScreenData)

    def loadScreenData(self):
        self.loadBoxIcon()
        try:
            self.system_info.memInfo(self)
            self.system_info.FlashMem(self)
            self.system_info.devices(self)
            self.system_info.mainInfo(self)
            self.system_info.cpuinfo(self)
            self.system_info.getPythonVersionString(self)
            self.system_info.getGStreamerVersionString(self)
        except Exception as e:
            print("[Showstatus] Hardware Specifications Load Failure:", e)

    def loadBoxIcon(self):
        try:
            box = "default"
            if os.path.exists("/etc/hostname"):
                with open("/etc/hostname", "r") as f:
                    box = f.read().strip().lower()
            
            folder = resolveFilename(SCOPE_PLUGINS, "Extensions/ServerEagleSat/icons_list/boxicons/")
            icon = os.path.join(folder, "%s.png" % box)
            if not fileExists(icon):
                icon = os.path.join(folder, "default.png")
                
            if fileExists(icon) and "boxicon" in self:
                pix = LoadPixmap(cached=True, path=icon)
                if pix and getattr(self["boxicon"], "instance", None):
                    self["boxicon"].instance.setPixmap(pix)
                    self["boxicon"].show()
        except Exception as e:
            print("[Showstatus] ICON ERROR:", e)

    def exit(self):
        self.close()