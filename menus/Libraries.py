# -*- coding: utf-8 -*-

# -----------------------------
# IMPORTS
# -----------------------------
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
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.Label import Label
from Plugins.Extensions.ElieSatPanelGrid.__init__ import Version

from enigma import getDesktop  # REQUIRED
from Components.Language import language  # Ensures _() is loaded
from Tools.Directories import resolveFilename, SCOPE_PLUGINS  # Optional, typical in Enigma2 plugins

import os


# -----------------------------
# MAIN CLASS
# -----------------------------
class Libraries(Screen):

    width, height = getDesktop(0).size().width(), getDesktop(0).size().height()

    skin_file = (
        "/usr/lib/enigma2/python/Plugins/Extensions/ElieSatPanel/assets/skin/piconstudio_fhd.xml"
        if width >= 1920
        else "/usr/lib/enigma2/python/Plugins/Extensions/ElieSatPanel/assets/skin/piconstudio_hd.xml"
    )

    try:
        with open(skin_file, "r") as f:
            skin = f.read()
    except Exception as e:
        print(f"[ElieSatPanel] Failed to load skin: {e}")
        skin = "<screen></screen>"

    def __init__(self, session):
        Screen.__init__(self, session)

        # -----------------------------
        # SECURITY / LOCK CHECKS
        # -----------------------------
        unlock_ok = is_device_unlocked()
        unlock_file_exists = os.path.exists("/etc/eliesat_unlocked.cfg")
        main_mac_exists = os.path.exists("/etc/eliesat_main_mac.cfg")

        if not unlock_ok or not unlock_file_exists or not main_mac_exists:
            self.close()
            return

        self.session = session
        self.setTitle(_("PiconStudio"))

        # -----------------------------
        # LEFT / RIGHT VERTICAL TEXT
        # -----------------------------
        vertical_left = "\n".join(list("Version " + Version))
        vertical_right = "\n".join(list("By ElieSat"))

        self["left_bar"] = Label(vertical_left)
        self["right_bar"] = Label(vertical_right)

        # -----------------------------
        # SYSTEM INFO LABELS
        # -----------------------------
        self["image_name"] = Label("Image: " + get_image_name())
        self["local_ip"] = Label("IP: " + get_local_ip())
        self["StorageInfo"] = Label(get_storage_info())
        self["RAMInfo"] = Label(get_ram_info())
        self["python_ver"] = Label("Python: " + get_python_version())
        self["net_status"] = Label("Net: " + check_internet())

        # -----------------------------
        # BUTTON LABELS
        # -----------------------------
        self["red"] = Label(_("Red"))
        self["green"] = Label(_("Green"))
        self["yellow"] = Label(_("Yellow"))
        self["blue"] = Label(_("Blue"))

        # -----------------------------
        # BUTTON ACTIONS
        # -----------------------------
        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions"],
            {
                "red": self.dummy,
                "green": self.dummy,
                "yellow": self.dummy,
                "blue": self.dummy,
                "cancel": self.close,
            },
            -1,
        )

    # -----------------------------
    # EMPTY BUTTON ACTION
    # -----------------------------
    def dummy(self):
        self.session.open(
            MessageBox,
            _("This button is not linked yet."),
            MessageBox.TYPE_INFO,
            timeout=3
        )

