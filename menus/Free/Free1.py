# -*- coding: utf-8 -*-
import os
import sys
from sys import version_info
import json

from enigma import getDesktop
from Screens.Screen import Screen
from Components.Label import Label
from Components.ActionMap import ActionMap
from Components.MenuList import MenuList

from Plugins.Extensions.ElieSatPanelGrid.__init__ import Version
from Plugins.Extensions.ElieSatPanelGrid.menus.Helpers import (
    get_local_ip,
    check_internet,
    get_image_name,
    get_python_version,
    get_storage_info,
    get_ram_info,
    is_device_unlocked
)


def get_plugin_skin():
    screen_width = 1280
    try:
        screen_width = getDesktop(0).size().width()
    except Exception:
        pass

    current_dir = os.path.dirname(os.path.abspath(__file__))
    plugin_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
    base_skin_path = os.path.join(plugin_root, "assets", "menus", "Free")

    if not os.path.exists(base_skin_path):
        base_skin_path = "/usr/lib/enigma2/python/Plugins/Extensions/ElieSatPanelGrid/menus/Free/"

    fhd_path = os.path.join(base_skin_path, "Free1_fhd.xml")
    hd_path = os.path.join(base_skin_path, "Free1_hd.xml")

    skin_file = fhd_path if screen_width >= 1920 and os.path.exists(fhd_path) else hd_path

    try:
        with open(skin_file, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception as e:
        print(f"[Free1 Screen Error] Could not read skin file '{skin_file}': {e}")
        return """<screen name="Free1" position="0,0" size="1920,1080">
                    <widget name="menu_list" position="150,200" size="1100,600" scrollbarMode="showOnDemand"/>
                  </screen>"""


class Free1(Screen):
    def __init__(self, session):
        self.session = session
        Screen.__init__(self, session)

        if not is_device_unlocked() or not os.path.exists("/etc/eliesat_unlocked.cfg"):
            print("[Free1 Screen Error] Security lock active or missing cfg file.")
            self.close()
            return

        # ---------------- COLORS ----------------
        self.C_GREEN = "\\c0000FF00"
        self.C_RED = "\\c00FF0000"
        self.C_YELLOW = "\\c00E6BE3A"
        self.C_WHITE = "\\c00FFFFFF"

        # Check plugin installation and conditionally handle configuration files
        self.check_and_handle_configs()

        self.skin = get_plugin_skin()
        self.build_ui()
        self.setup_actions()

    def check_plugin_status(self, plugin_name):
        plugin_path = os.path.join("/usr/lib/enigma2/python/Plugins/Extensions", plugin_name)
        try:
            if os.path.exists(plugin_path) and os.path.isdir(plugin_path):
                if os.listdir(plugin_path):
                    return True
        except Exception as e:
            print(f"[Free1 Error] Checking {plugin_name} path failed: {e}")
        return False

    def check_and_handle_configs(self):
        plugins_config_map = [
            ("IPaudioPro", "/etc/enigma2/IPaudioPro.json", "json"),
            ("IPAudio", "/etc/enigma2/ipaudio.json", "json"),
            ("IPStreamer", "/etc/enigma2/ipstreamer/ipstreamer_myextream.json", "json_nested"),
            ("AudioSelectionPatcher", "/etc/enigma2/external_audio.txt", "txt")
        ]

        for plugin_name, file_path, file_type in plugins_config_map:
            if self.check_plugin_status(plugin_name):
                try:
                    if not os.path.exists(file_path):
                        directory = os.path.dirname(file_path)
                        if directory and not os.path.exists(directory):
                            os.makedirs(directory)
                        
                        if file_type in ("json", "json_nested"):
                            with open(file_path, "w", encoding="utf-8") as jf:
                                json.dump({}, jf, indent=4)
                        elif file_type == "txt":
                            with open(file_path, "w", encoding="utf-8") as tf:
                                tf.write("")
                        print(f"[Free1] Created missing configuration file for installed plugin: {file_path}")
                except Exception as e:
                    print(f"[Free1 Error] Could not create {file_path}: {e}")

    def build_ui(self):
        # Description text & static navigation text separated
        self["description"] = Label("")
        self["navigation_txt"] = Label("● Use UP/DOWN keys to select an option, or press OK to launch stream.")
        self["pagelabel"] = Label("● Free IP Audio Services")

        # System Information
        self["image_name"] = Label(f"Image: {get_image_name()}")
        self["local_ip"] = Label(f"IP: {get_local_ip()}")
        self["StorageInfo"] = Label(get_storage_info())
        self["RAMInfo"] = Label(get_ram_info())
        self["python_ver"] = Label(f"Python: {get_python_version()}")
        self["net_status"] = Label(f"Net: {check_internet()}")

        # Vertical Side Text
        self["left_bar"] = Label("\n".join(list("Version " + str(Version))))
        self["right_bar"] = Label("\n".join(list("By ElieSat")))

        # Bottom Color Action Button Labels
        self["red"] = Label("Play Stream")
        self["green"] = Label("Refresh")
        self["yellow"] = Label("")
        self["blue"] = Label("")

        # Check status for each of the 4 plugins
        ipaudio_pro_installed = self.check_plugin_status("IPaudioPro")
        ipaudio_installed = self.check_plugin_status("IPAudio")
        ipstreamer_installed = self.check_plugin_status("IPStreamer")
        audio_patcher_installed = self.check_plugin_status("AudioSelectionPatcher")

        # Format labels using Enigma2 native hex color formatting strings (Green for installed, Red for uninstalled)
        if ipaudio_pro_installed:
            lbl_ipaudio_pro = f"{self.C_GREEN}● {self.C_YELLOW}IPaudioPro [Installed]{self.C_WHITE}"
        else:
            lbl_ipaudio_pro = f"{self.C_RED}● {self.C_YELLOW}IPaudioPro [Not Installed]{self.C_WHITE}"

        if ipaudio_installed:
            lbl_ipaudio = f"{self.C_GREEN}● {self.C_YELLOW}IPAudio [Installed]{self.C_WHITE}"
        else:
            lbl_ipaudio = f"{self.C_RED}● {self.C_YELLOW}IPAudio [Not Installed]{self.C_WHITE}"

        if ipstreamer_installed:
            lbl_ipstreamer = f"{self.C_GREEN}● {self.C_YELLOW}IPStreamer [Installed]{self.C_WHITE}"
        else:
            lbl_ipstreamer = f"{self.C_RED}● {self.C_YELLOW}IPStreamer [Not Installed]{self.C_WHITE}"

        if audio_patcher_installed:
            lbl_audio_patcher = f"{self.C_GREEN}● {self.C_YELLOW}AudioSelectionPatcher [Installed]{self.C_WHITE}"
        else:
            lbl_audio_patcher = f"{self.C_RED}● {self.C_YELLOW}AudioSelectionPatcher [Not Installed]{self.C_WHITE}"

        # Items mapping: Label, Action Function, Subtitle Info
        self.menu_items = [
            (lbl_ipaudio_pro, self.actionItem1, "Connect to IP Audio Pro service"),
            (lbl_ipaudio, self.actionItem2, "Connect to IPAudio service"),
            (lbl_ipstreamer, self.actionItem3, "Connect to IPStreamer service"),
            (lbl_audio_patcher, self.actionItem4, "Configure Audio Selection Patcher")
        ]

        # Populate MenuList
        menu_titles = [item[0] for item in self.menu_items]
        self["menu_list"] = MenuList(menu_titles)

        # Update description on list selection change
        self["menu_list"].onSelectionChanged.append(self.selectionChanged)
        self.selectionChanged()

    def setup_actions(self):
        self["setupActions"] = ActionMap(
            ["OkCancelActions", "ColorActions", "DirectionActions"],
            {
                "ok": self.okClicked,
                "cancel": self.close,
                "red": self.actionItem1,
                "green": self.actionItem2,
                "yellow": self.noAction,
                "blue": self.noAction,
                "up": self.keyUp,
                "down": self.keyDown,
            },
            -1,
        )

    def keyUp(self):
        self["menu_list"].up()

    def keyDown(self):
        self["menu_list"].down()

    def selectionChanged(self):
        index = self["menu_list"].getSelectedIndex()
        if index is not None and index < len(self.menu_items):
            desc = self.menu_items[index][2]
            self["description"].setText(f"● {desc}")

    def okClicked(self):
        index = self["menu_list"].getSelectedIndex()
        if index is not None and index < len(self.menu_items):
            action_function = self.menu_items[index][1]
            action_function()

    def actionItem1(self):
        print("[Free1] Executing action for IPaudioPro")
        # Add your custom logic/player initialization here

    def actionItem2(self):
        print("[Free1] Executing action for IPAudio")
        # Add your custom logic/player initialization here

    def actionItem3(self):
        print("[Free1] Executing action for IPStreamer")
        # Add your custom logic/player initialization here

    def actionItem4(self):
        print("[Free1] Executing action for AudioSelectionPatcher")
        # Add your custom logic/player initialization here

    def noAction(self):
        pass
