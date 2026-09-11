# -*- coding: utf-8 -*-
import os
import sys
from sys import version_info
import json

from enigma import getDesktop, eServiceReference
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


class InstalledPluginsScreen(Screen):
    def __init__(self, session):
        self.session = session
        Screen.__init__(self, session)
        self.skin = get_plugin_skin()

        # ---------------- COLORS ----------------
        self.C_GREEN = "\\c0000FF00"
        self.C_RED = "\\c00FF0000"
        self.C_YELLOW = "\\c00E6BE3A"
        self.C_WHITE = "\\c00FFFFFF"

        self.setup_ui()
        self.setup_actions()

    def check_plugin_status(self, plugin_name):
        plugin_path = os.path.join("/usr/lib/enigma2/python/Plugins/Extensions", plugin_name)
        try:
            if os.path.exists(plugin_path) and os.path.isdir(plugin_path):
                if os.listdir(plugin_path):
                    return True
        except Exception as e:
            print(f"[InstalledPlugins Error] Checking {plugin_name} path failed: {e}")
        return False

    def setup_ui(self):
        self["description"] = Label("")
        self["navigation_txt"] = Label("● Press CANCEL or BLUE to return to main menu.")
        self["pagelabel"] = Label("● Installed Audio Plugins")

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
        self["red"] = Label("")
        self["green"] = Label("")
        self["yellow"] = Label("")
        self["blue"] = Label("Back")

        ipaudio_pro_installed = self.check_plugin_status("IPaudioPro")
        ipaudio_installed = self.check_plugin_status("IPAudio")
        ipstreamer_installed = self.check_plugin_status("IPStreamer")
        audio_patcher_installed = self.check_plugin_status("AudioSelectionPatcher")

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

        self.menu_items = [
            (lbl_ipaudio_pro, "Status information for IPaudioPro plugin"),
            (lbl_ipaudio, "Status information for IPAudio plugin"),
            (lbl_ipstreamer, "Status information for IPStreamer plugin"),
            (lbl_audio_patcher, "Status information for AudioSelectionPatcher plugin")
        ]

        menu_titles = [item[0] for item in self.menu_items]
        self["menu_list"] = MenuList(menu_titles)
        self["menu_list"].onSelectionChanged.append(self.selectionChanged)
        self.selectionChanged()

    def setup_actions(self):
        self["setupActions"] = ActionMap(
            ["OkCancelActions", "ColorActions"],
            {
                "ok": self.close,
                "cancel": self.close,
                "blue": self.close,
            },
            -1,
        )

    def selectionChanged(self):
        index = self["menu_list"].getSelectedIndex()
        if index is not None and index < len(self.menu_items):
            desc = self.menu_items[index][1]
            self["description"].setText(f"● {desc}")


class Free1(Screen):
    def __init__(self, session):
        self.session = session
        Screen.__init__(self, session)

        if not is_device_unlocked() or not os.path.exists("/etc/eliesat_unlocked.cfg"):
            print("[Free1 Screen Error] Security lock active or missing cfg file.")
            self.close()
            return

        self.is_playing = False
        self.playing_index = -1

        # ---------------- COLORS ----------------
        self.C_GREEN = "\\c0000FF00"
        self.C_RED = "\\c00FF0000"
        self.C_YELLOW = "\\c00E6BE3A"
        self.C_ORANGE = "\\c00FF8000"
        self.C_WHITE = "\\c00FFFFFF"

        self.skin = get_plugin_skin()
        self.build_ui()
        self.setup_actions()

    def load_free_audio_json(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(current_dir, "freeaudio.json")
        items = []

        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        parts = line.split("|", 1)
                        if len(parts) == 2:
                            name = parts[0].strip()
                            url = parts[1].strip()
                            items.append((name, url))
            except Exception as e:
                print(f"[Free1 Error] Failed to read freeaudio.json lines: {e}")
        else:
            print(f"[Free1 Warning] freeaudio.json not found at {json_path}")

        if not items:
            items = [
                ("Anis Max 1", "http://radio.anisfm.vip/live/mx/1?token=6ZQ7WCPU#"),
                ("Anis Max 2", "http://radio.anisfm.vip/live/mx/2?token=6ZQ7WCPU#")
            ]
        return items

    def build_ui(self):
        self["description"] = Label("")
        self["navigation_txt"] = Label("● Press OK to listen, YELLOW to stop, RED to remove invalid.")
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
        self["red"] = Label("RemoveInvalid")
        self["green"] = Label("SaveToPlayLists")
        self["yellow"] = Label("StopListening")
        self["blue"] = Label("ShowInstalledPlugins")

        # Initialize MenuList component once
        self.menu_items = []
        self["menu_list"] = MenuList([])
        self["menu_list"].onSelectionChanged.append(self.selectionChanged)

        self.reloadMenu()

    def reloadMenu(self):
        raw_audio_items = self.load_free_audio_json()
        self.menu_items = []

        for i, (name, url) in enumerate(raw_audio_items):
            color = self.C_ORANGE if (self.is_playing and self.playing_index == i) else self.C_YELLOW
            menu_title = f"{color}● {name}"
            menu_desc = f"Stream URL: {url}"
            self.menu_items.append((menu_title, url, menu_desc, name))

        menu_titles = [item[0] for item in self.menu_items]
        
        if hasattr(self["menu_list"], "l"):
            self["menu_list"].l.setList(menu_titles)

        self.selectionChanged()

    def setup_actions(self):
        self["setupActions"] = ActionMap(
            ["OkCancelActions", "ColorActions", "DirectionActions"],
            {
                "ok": self.okClicked,
                "cancel": self.cancelClicked,
                "red": self.RemoveInvalid,
                "green": self.Save,
                "yellow": self.stopPlayback,
                "blue": self.ShowInstalledPlugins,
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
        else:
            self["description"].setText("● No items available")

    def okClicked(self):
        index = self["menu_list"].getSelectedIndex()
        if index is not None and index < len(self.menu_items):
            station_name = self.menu_items[index][3]
            stream_url = self.menu_items[index][1]
            try:
                sref = eServiceReference(4097, 0, stream_url)
                sref.setName(station_name)
                self.session.nav.playService(sref)
                self.is_playing = True
                self.playing_index = index
                self.reloadMenu()
                print(f"[Free1] Playing stream -> {station_name}")
            except Exception as e:
                print(f"[Free1 Error] Failed to play stream: {e}")

    def cancelClicked(self):
        if self.is_playing:
            try:
                self.session.nav.stopService()
            except Exception:
                pass
        self.close()

    def ShowInstalledPlugins(self):
        print("[Free1] ShowInstalledPlugins triggered via Blue button.")
        self.session.open(InstalledPluginsScreen)

    def Save(self):
        print("[Free1] SaveToPlayLists triggered via Green button.")

    def check_url_validity(self, url):
        try:
            if sys.version_info[0] >= 3:
                import urllib.request
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                response = urllib.request.urlopen(req, timeout=3)
                code = response.getcode()
                response.close()
                return 200 <= code < 400
            else:
                import urllib2
                req = urllib2.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                response = urllib2.urlopen(req, timeout=3)
                code = response.getcode()
                response.close()
                return 200 <= code < 400
        except Exception:
            return False

    def RemoveInvalid(self):
        print("[Free1] Checking validity of all stream URLs via Red button...")
        current_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(current_dir, "freeaudio.json")

        if os.path.exists(json_path):
            try:
                lines = []
                with open(json_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()

                valid_lines = []
                for line in lines:
                    stripped = line.strip()
                    if not stripped:
                        continue
                    parts = stripped.split("|", 1)
                    if len(parts) == 2:
                        name = parts[0].strip()
                        url = parts[1].strip()
                        if self.check_url_validity(url):
                            valid_lines.append(line if line.endswith("\n") else line + "\n")
                        else:
                            print(f"[Free1] Removing dead/invalid URL: {name} -> {url}")
                    else:
                        valid_lines.append(line if line.endswith("\n") else line + "\n")

                with open(json_path, "w", encoding="utf-8") as f:
                    f.writelines(valid_lines)

                if self.is_playing:
                    self.session.nav.stopService()
                    self.is_playing = False
                    self.playing_index = -1

                print("[Free1] URL check and cleanup completed.")
            except Exception as e:
                print(f"[Free1 Error] Failed to check and clean JSON URLs: {e}")

        self.reloadMenu()

    def stopPlayback(self):
        if self.is_playing:
            try:
                self.session.nav.stopService()
                self.is_playing = False
                self.playing_index = -1
                self.reloadMenu()
                print("[Free1] Stopped playback via Yellow button.")
            except Exception as e:
                print(f"[Free1 Error] Failed to stop stream: {e}")
