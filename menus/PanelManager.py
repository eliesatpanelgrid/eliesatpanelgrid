# -*- coding: utf-8 -*-
import os
import re
import uuid

# ---------------- SAFE COMPAT IMPORT (NO CRASH) ----------------
try:
    import urllib2
except:
    import urllib.request as urllib2

from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Components.Label import Label
from Components.ActionMap import ActionMap
from enigma import getDesktop

# ---------------- Unlock marker path ----------------
UNLOCK_FLAG = "/etc/eliesat_unlocked.cfg"
MAIN_MAC_FILE = "/etc/eliesat_main_mac.cfg"  # Stores main MAC for password generation

# ---------------- PANEL DIRECTORIES ----------------
PANEL_DIRS = [
    "/media/hdd/ElieSatPanel",   # default
    "/media/usb/ElieSatPanel",
    "/media/mmc/ElieSatPanel"
]

# ---------------- WHITELIST (ADDED) ----------------
WHITELIST_URL = "https://raw.githubusercontent.com/eliesatpanelgrid/Iists/main/whitelist"

def check_mac_whitelist(mac):
    try:
        if not mac:
            return False

        mac_clean = mac.replace(":", "").replace("-", "").upper()
        if len(mac_clean) < 12:
            return False

        token = mac_clean[0:2] + ":" + mac_clean[-2:]  # e.g. 20:60

        try:
            req = urllib2.Request(WHITELIST_URL)
            data = urllib2.urlopen(req, timeout=5).read()
            try:
                data = data.decode("utf-8")
            except:
                pass
            data = data.upper()
        except:
            return False

        return token in data

    except:
        return False


# ---------------- Default folder config ----------------
def get_config_path(folder):
    return os.path.join(folder, "panel_dir.cfg")

SUB_FILE = "subscription.txt"

# ---------------- Utilities ----------------
def save_last_dir(directory):
    try:
        config_file = get_config_path(directory)
        with open(config_file, "w") as f:
            f.write(directory)
    except Exception:
        pass

def load_last_dir():
    for folder in PANEL_DIRS:
        cfg = get_config_path(folder)
        if os.path.exists(cfg):
            try:
                with open(cfg, "r") as f:
                    d = f.read().strip()
                    if d in PANEL_DIRS:
                        return d
            except Exception:
                pass
    return PANEL_DIRS[0]

def create_subscription_file(directory):
    try:
        path = os.path.join(directory, SUB_FILE)
        if not os.path.exists(path):
            open(path, "w").close()
    except Exception:
        pass

def delete_subscription_files(except_dir=None):
    for folder in PANEL_DIRS:
        if folder == except_dir:
            continue
        path = os.path.join(folder, SUB_FILE)
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass

def ensure_panel_folder(folder):
    if not os.path.exists(folder):
        os.makedirs(folder)
    save_last_dir(folder)
    create_subscription_file(folder)
    delete_subscription_files(except_dir=folder)

# ---------------- INITIAL SETUP ----------------
for folder in PANEL_DIRS:
    if not os.path.exists(folder):
        os.makedirs(folder)

ensure_panel_folder(PANEL_DIRS[0])

# ---------------- MAC / Password helpers ----------------
def get_mac_address():
    ifaces = ("eth0", "eth1", "wan0", "wlan0", "wlan1", "lan0")
    for iface in ifaces:
        path = "/sys/class/net/%s/address" % iface
        try:
            if os.path.exists(path):
                with open(path) as f:
                    mac = f.read().strip()
                if mac and mac != "00:00:00:00:00:00":
                    return mac.upper()
        except Exception:
            pass
    try:
        mac_int = uuid.getnode()
        mac_hex = "%012X" % mac_int
        return ":".join(mac_hex[i:i+2] for i in range(0, 12, 2))
    except Exception:
        return None

def get_main_mac():
    if os.path.exists(MAIN_MAC_FILE):
        try:
            with open(MAIN_MAC_FILE, "r") as f:
                mac = f.read().strip().upper()
                if mac:
                    return mac
        except Exception:
            pass

    mac = get_mac_address()
    if mac:
        try:
            with open(MAIN_MAC_FILE, "w") as f:
                f.write(mac)
        except Exception:
            pass
    return mac

def make_password_from_mac(mac):
    if not mac:
        return None
    mac_clean = mac.replace(":", "").replace("-", "").upper()
    if len(mac_clean) < 8:
        return None

    base = mac_clean[3] + mac_clean[5] + mac_clean[7] + mac_clean[9]

    digits_str = "".join(ch for ch in base if ch.isdigit())
    mult = int(digits_str) * 5 if digits_str else 0

    full_pass = "%s%s" % (mult, base)
    return full_pass[:4]

def is_unlocked():
    if not os.path.exists(UNLOCK_FLAG):
        return False
    try:
        with open(UNLOCK_FLAG, "r") as f:
            saved_password = f.read().strip()
        expected_password = make_password_from_mac(get_main_mac())
        return bool(saved_password and expected_password and saved_password == expected_password)
    except Exception:
        return False

def set_unlocked(password):
    try:
        with open(UNLOCK_FLAG, "w") as f:
            f.write((password or "").strip())
        return True
    except Exception:
        return False

# ---------------- PANEL MANAGER SCREEN ----------------
class PanelManager(Screen):
    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session

        # ---------------- MAC ----------------
        self.mac = get_main_mac() or "Unknown"

        # ---------------- SAFE WHITELIST CHECK (NO CRASH GUARANTEE) ----------------
        try:
            allowed = check_mac_whitelist(self.mac)
        except:
            allowed = True  # never block plugin load due to error

        if not allowed:
            try:
                self.session.open(
                    MessageBox,
                    "❌ You are not allowed to use this plugin.",
                    MessageBox.TYPE_ERROR
                )
            except:
                pass
            self.close()
            return

        # ---------------- Load correct skin ----------------
        width, height = getDesktop(0).size().width(), getDesktop(0).size().height()
        skin_file = "/usr/lib/enigma2/python/Plugins/Extensions/ElieSatPanelGrid/assets/skin/panel_manager_fhd.xml" \
            if width >= 1920 else "/usr/lib/enigma2/python/Plugins/Extensions/ElieSatPanelGrid/assets/skin/panel_manager_hd.xml"
        try:
            with open(skin_file, "r") as f:
                self.skin = f.read()
        except Exception:
            self.skin = "<screen></screen>"

        self.dir_index = PANEL_DIRS.index(load_last_dir())
        self.current_dir = PANEL_DIRS[self.dir_index]

        self.username_value = "ElieSat"
        self.password_value = ""
        self.device_name = os.uname().nodename
        self.expected_password = make_password_from_mac(self.mac)

        # ---------------- Labels ----------------
        self["title_custom"] = Label("Panel Manager")
        self["username_label"] = Label("Username:")
        self["username"] = Label(self.username_value)
        self["password_label"] = Label("Password:")
        self["password"] = Label("")
        self["dir_label"] = Label("Default Folder Path:")
        self["dir"] = Label(self.current_dir)
        self["device_label"] = Label("Device Name:")
        self["device"] = Label(self.device_name)
        self["mac_label"] = Label("MAC Address:")
        self["mac_value"] = Label(self.mac)
        self["focus_hint"] = Label("")

        self["red_label"] = Label("Unlock")
        self["green_label"] = Label("Apply Path")
        self["yellow_label"] = Label("Show")
        self["blue_label"] = Label("Reset")

        self.focus_items = ["username", "password", "dir", "device"]
        self.focus_index = 0
        self._refresh_fields_and_focus()

        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions", "DirectionActions"],
            {
                "ok": self._ok_pressed,
                "red": self.apply_password,
                "green": self.apply_dir,
                "yellow": self.show_status,
                "blue": self.reset_password,
                "cancel": self.close,
                "up": self.focus_up,
                "down": self.focus_down,
                "left": self.cycle_left,
                "right": self.cycle_right
            }, -1
        )

        if is_unlocked() and self.expected_password:
            self.password_value = self.expected_password
            self["focus_hint"].setText("Unlocked on this device (saved).")
            self._refresh_fields_and_focus()

    # ---------------- Rest unchanged ----------------
    def _refresh_fields_and_focus(self):
        sel = self.focus_items[self.focus_index]
        if sel == "username":
            hint = "Selected: Username (OK to edit)"
        elif sel == "password":
            hint = "Selected: Password (OK to edit, Red = Unlock)"
        elif sel == "dir":
            hint = "Selected: Folder (OK or Green = Apply Path; Left/Right = Cycle)"
        else:
            hint = "Selected: Device Name (OK to edit)"
        self["focus_hint"].setText(hint)

        self["username"].setText("> " + self.username_value if sel == "username" else self.username_value)
        self["password"].setText("> " + "*" * len(self.password_value) if sel == "password" else "*" * len(self.password_value))
        self["dir"].setText("> " + self.current_dir if sel == "dir" else self.current_dir)
        self["device"].setText("> " + self.device_name if sel == "device" else self.device_name)
        self["mac_value"].setText(self.mac)

    def focus_up(self):
        self.focus_index = (self.focus_index - 1) % len(self.focus_items)
        self._refresh_fields_and_focus()

    def focus_down(self):
        self.focus_index = (self.focus_index + 1) % len(self.focus_items)
        self._refresh_fields_and_focus()

    def _ok_pressed(self):
        sel = self.focus_items[self.focus_index]
        if sel == "username":
            self.session.openWithCallback(self._onUsernameEntered, VirtualKeyBoard, title="Enter username", text=self.username_value)
        elif sel == "password":
            self.session.openWithCallback(self._onPasswordEntered, VirtualKeyBoard, title="Enter password", text=self.password_value)
        elif sel == "device":
            self.session.openWithCallback(self._onDeviceEntered, VirtualKeyBoard, title="Enter device name", text=self.device_name)
        else:
            self.apply_dir()

    def _onUsernameEntered(self, result):
        if result: self.username_value = result.strip()
        self._refresh_fields_and_focus()

    def _onPasswordEntered(self, result):
        if result: self.password_value = result.strip()
        self._refresh_fields_and_focus()

    def _onDeviceEntered(self, result):
        if result: self.device_name = result.strip()
        self._refresh_fields_and_focus()

    def apply_password(self):
        if is_unlocked():
            self.session.open(MessageBox, "Already unlocked on this device.", MessageBox.TYPE_INFO)
            return
        if not self.expected_password:
            self.session.open(MessageBox, "Cannot read MAC address.", MessageBox.TYPE_ERROR)
            return
        if (self.username_value.strip().upper() != "ELIESAT" or
            self.password_value.strip().upper() != self.expected_password.strip().upper()):
            self.session.open(MessageBox, "Access denied — wrong username or password.", MessageBox.TYPE_ERROR)
            return
        if set_unlocked(self.expected_password):
            self.session.open(MessageBox, "Password accepted — device unlocked successfully.", MessageBox.TYPE_INFO)
        else:
            self.session.open(MessageBox, "Failed to save unlock flag in /etc/.", MessageBox.TYPE_ERROR)

    def apply_dir(self):
        try:
            last_dir = load_last_dir()

            if last_dir == self.current_dir and os.path.exists(os.path.join(self.current_dir, SUB_FILE)):
                self.session.open(MessageBox, f"Directory already applied:\n{self.current_dir}", MessageBox.TYPE_INFO)
                return

            ensure_panel_folder(self.current_dir)
            self._refresh_fields_and_focus()

            self.session.open(MessageBox, f"Default folder path applied:\n{self.current_dir}\n\nsubscription.txt updated.", MessageBox.TYPE_INFO)

        except Exception as e:
            self.session.open(MessageBox, f"Failed to apply folder:\n{e}", MessageBox.TYPE_ERROR)

    def reset_password(self):
        self.password_value = ""
        if os.path.exists(UNLOCK_FLAG):
            os.remove(UNLOCK_FLAG)
        self._refresh_fields_and_focus()
        self.session.open(MessageBox, "Password has been reset.", MessageBox.TYPE_INFO)

    def show_status(self):
        try:
            active_dir = load_last_dir()
            lines = []
            for folder in PANEL_DIRS:
                path = os.path.join(folder, SUB_FILE)
                if folder == active_dir:
                    lines.append(f"{folder}\n  → ACTIVE")
                elif os.path.exists(path):
                    lines.append(f"{folder}\n  → Present")
                else:
                    lines.append(f"{folder}\n  → Missing")
            msg = "\n\n".join(lines)
            self.session.open(MessageBox, f"Subscription File Status:\n\n{msg}", MessageBox.TYPE_INFO)
        except Exception as e:
            self.session.open(MessageBox, f"Failed to show status:\n{e}", MessageBox.TYPE_ERROR)

    def cycle_left(self):
        if self.focus_items[self.focus_index] != "dir":
            return
        self.dir_index = (self.dir_index - 1) % len(PANEL_DIRS)
        self.current_dir = PANEL_DIRS[self.dir_index]
        self._refresh_fields_and_focus()

    def cycle_right(self):
        if self.focus_items[self.focus_index] != "dir":
            return
        self.dir_index = (self.dir_index + 1) % len(PANEL_DIRS)
        self.current_dir = PANEL_DIRS[self.dir_index]
        self._refresh_fields_and_focus()
