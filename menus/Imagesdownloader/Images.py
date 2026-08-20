# -*- coding: utf-8 -*-
from __future__ import absolute_import
from Plugins.Extensions.ElieSatPanelGrid.menus.Helpers import (
    get_local_ip,
    check_internet,
    get_image_name,
    get_python_version,
    get_storage_info,
    get_ram_info,
    is_device_unlocked
)
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.ProgressBar import ProgressBar
from Components.ChoiceList import ChoiceList
from Components.Pixmap import Pixmap
from enigma import getDesktop
import os
from Plugins.Extensions.ElieSatPanelGrid.__init__ import Version


class Images(Screen):
    width, height = getDesktop(0).size().width(), getDesktop(0).size().height()
    skin_file = (
        "/usr/lib/enigma2/python/Plugins/Extensions/ElieSatPanelGrid/menus/Imagesdownloader/images_fhd.xml"
        if width >= 1920
        else "/usr/lib/enigma2/python/Plugins/Extensions/ElieSatPanelGrid/menus/Imagesdownloader/images_hd.xml"
    )
    try:
        with open(skin_file, "r") as f:
            skin = f.read()
    except Exception as e:
        print(f"[ElieSatPanel] Failed to load skin in Images: {e}")
        skin = "<screen></screen>"

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session

        # Security check
        unlock_ok = is_device_unlocked()
        unlock_file_exists = os.path.exists("/etc/eliesat_unlocked.cfg")
        main_mac_exists = os.path.exists("/etc/eliesat_main_mac.cfg")

        if not unlock_ok or not unlock_file_exists or not main_mac_exists:
            self.close()
            return

        self.hostname = self.getHostname()

        # UI Components matching skin layout
        self["device_icon"] = Pixmap()
        self.onLayoutFinish.append(self._safeLoadDeviceIcon)

        self["item_name"] = Label("")
        self["image_name"] = Label("Image: " + get_image_name())
        self["local_ip"] = Label("IP: " + get_local_ip())
        self["StorageInfo"] = Label(get_storage_info())
        self["RAMInfo"] = Label(get_ram_info())
        self["python_ver"] = Label("Python: " + get_python_version())
        self["net_status"] = Label("Net: " + check_internet())
        self["device_name"] = Label("Device: " + self.hostname)
        self["download_info"] = Label("")

        self["left_bar"] = Label("\n".join(list("Version " + Version)))
        self["right_bar"] = Label("B\ny\n \nE\nl\ni\ne\nS\na\nt")

        self["red"] = Label("")
        self["green"] = Label("")
        self["yellow"] = Label("")
        self["blue"] = Label("")
        self["list"] = ChoiceList([])
        self["progress"] = ProgressBar()

        # Navigation ActionMap
        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions"],
            {
                "cancel": self.close,
                "back": self.close,
            },
            -1,
        )

    def getHostname(self):
        try:
            with open("/etc/hostname", "r") as f:
                return f.readline().strip()
        except Exception:
            return os.uname().nodename.strip()

    def _safeLoadDeviceIcon(self):
        try:
            base_path = "/usr/lib/enigma2/python/Plugins/Extensions/ElieSatPanelGrid/assets/boxicons/"
            icon_path = os.path.join(base_path, f"{self.hostname}.png")
            if not os.path.exists(icon_path):
                icon_path = os.path.join(base_path, "default.png")
            if os.path.exists(icon_path):
                self["device_icon"].instance.setPixmapFromFile(icon_path)
        except Exception as e:
            print(f"[ElieSatPanel] Error loading icon: {e}")