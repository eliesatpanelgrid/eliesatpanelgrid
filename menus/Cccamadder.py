# -*- coding: utf-8 -*-
import os
import re
from datetime import datetime
import gettext
import socket

from enigma import getDesktop
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.ConfigList import ConfigListScreen
from Components.config import (
    ConfigText, ConfigSelection, ConfigInteger, getConfigListEntry
)
from Components.MenuList import MenuList
from Components.Language import language

from Plugins.Extensions.ElieSatPanelGrid.menus.Infobox import OSCamReadersScreen
from Plugins.Extensions.ElieSatPanelGrid.__init__ import Version
from Plugins.Extensions.ElieSatPanelGrid.menus.Helpers import (
    get_local_ip, check_internet, get_image_name,
    get_python_version, get_storage_info, get_ram_info
)

# --- Translation setup ---
def localeInit():
    lang = language.getLanguage()
    gettext.bindtextdomain(
        "ElieSatPanel",
        "/usr/lib/enigma2/python/Plugins/Extensions/ElieSatPanelGrid/locale"
    )

localeInit()
_ = gettext.gettext


# ----------------------------
# Panel directories
# ----------------------------
PANEL_DIRS = [
    "/media/usb/ElieSatPanel",
    "/media/hdd/ElieSatPanel",
    "/media/mmc/ElieSatPanel"
]

# ----------------------------
# Unified Protocol Editor
# ----------------------------
class Cccamadder(Screen, ConfigListScreen):
    # ---------------- Load correct skin ----------------
    width, height = getDesktop(0).size().width(), getDesktop(0).size().height()
    skin_file = (
        "/usr/lib/enigma2/python/Plugins/Extensions/ElieSatPanelGrid/assets/skin/cccamadder_fhd.xml"
        if width >= 1920
        else "/usr/lib/enigma2/python/Plugins/Extensions/ElieSatPanelGrid/assets/skin/cccamadder_hd.xml"
    )
    try:
        with open(skin_file, "r") as f:
            skin = f.read()
    except Exception as e:
        print(f"[ElieSatPanel] Failed to load skin: {e}")
        skin = "<screen></screen>"

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        self.panel_dir = self.detect_panel_dir()
        if not os.path.exists(self.panel_dir):
            os.makedirs(self.panel_dir)

        # System info
        self["image_name"] = Label("Image: " + get_image_name())
        self["local_ip"] = Label("IP: " + get_local_ip())
        self["StorageInfo"] = Label(get_storage_info())
        self["RAMInfo"] = Label(get_ram_info())
        self["python_ver"] = Label("Python: " + get_python_version())
        self["net_status"] = Label("Net: " + check_internet())
        self["left_bar"] = Label("\n".join(list("Version " + Version)))
        self["right_bar"] = Label("\n".join(list("By ElieSat")))

        # Colored buttons
        self["red"] = Label("Oscam Status")
        self["green"] = Label("Restore")
        self["yellow"] = Label("Send And Backup")
        self["blue"] = Label("Manage Readers")

        # Config fields
        self.label_choice = ConfigSelection(
            default="ServerEagle",
            choices=[("ServerEagle", "ServerEagle"),
                     ("ElieSat", "ElieSat"),
                     ("Custom", "Custom")]
        )
        self.label_custom = ConfigText(default="server_name")
        self.label_custom.useKeyboard = False

        self.status = ConfigSelection(default="enabled", choices=[("enabled","Enabled"),("disabled","Disabled")])
        self.protocol = ConfigSelection(choices=[("cccam","CCcam"),("newcamd","NewCamd"),("mgcamd","MgCamd")])
        self.host = ConfigText(default="tv8k.cc")
        self.port = ConfigInteger(default=22222, limits=(1,99999))
        self.user = ConfigText(default="User")
        self.passw = ConfigText(default="Pass")
        self.inactivitytimeout = ConfigInteger(default=30, limits=(1,99))
        self.group = ConfigInteger(default=1, limits=(0,99))
        self.disablecrccws = ConfigSelection(default="1", choices=[("0","No"),("1","Yes")])
        self.cccamversion = ConfigSelection(
            default="2.0.11",
            choices=[
                ("2.0.11", "2.0.11"),
                ("2.1.1", "2.1.1"),
                ("2.1.2", "2.1.2"),
                ("2.1.3", "2.1.3"),
                ("2.1.4", "2.1.4"),
                ("2.2.0", "2.2.0"),
                ("2.2.1", "2.2.1"),
                ("2.3.0", "2.3.0"),
                ("2.3.1", "2.3.1"),
                ("2.3.2", "2.3.2"),
            ]
        )
        self.cccwantemu = ConfigSelection(default="1", choices=[("0","No"),("1","Yes")])
        self.ccckeepalive = ConfigSelection(default="1", choices=[("0","No"),("1","Yes")])
        self.audisabled = ConfigSelection(default="1", choices=[("0","No"),("1","Yes")])
        # NewCamd / MgCamd fields
        self.key = ConfigText(default="0102030405060708091011121314")
        self.disableserverfilter = ConfigSelection(default="1", choices=[("0","No"),("1","Yes")])
        self.connectoninit = ConfigSelection(default="1", choices=[("0","No"),("1","Yes")])

        for field in [self.host,self.user,self.passw,self.cccamversion,self.key]:
            field.useKeyboard = False

        ConfigListScreen.__init__(self, [], session=session)
        self.update_fields()
        self.label_choice.addNotifier(self.on_label_change, initial_call=False)
        self.protocol.addNotifier(self.on_protocol_change, initial_call=False)

        # Action map
        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions"],
            {
                "red": self.open_red_job,
                "green": self.open_green_job,
                "yellow": self.yellow_button,
                "blue": self.open_blue_job,
                "cancel": self.close_screen,
            }, -1
        )

    # ----------------------------
    # Config List Update
    # ----------------------------
    def update_fields(self):
        proto = self.protocol.value.lower()
        cfg_list = [
            getConfigListEntry("Label:", self.label_choice),
        ]

        # Show custom text if "Custom" selected
        if self.label_choice.value == "Custom":
            cfg_list.append(getConfigListEntry("Custom Name:", self.label_custom))

        cfg_list += [
            getConfigListEntry("Status:", self.status),
            getConfigListEntry("Protocol:", self.protocol),
            getConfigListEntry("Host:", self.host),
            getConfigListEntry("Port:", self.port),
            getConfigListEntry("Username:", self.user),
            getConfigListEntry("Password:", self.passw),
            getConfigListEntry("Inactivity Timeout:", self.inactivitytimeout),
            getConfigListEntry("Group:", self.group),
        ]
        if proto == "cccam":
            cfg_list += [
                getConfigListEntry("Disable CRC/CWS:", self.disablecrccws),
                getConfigListEntry("CCcam Version:", self.cccamversion),
                getConfigListEntry("Want Emu:", self.cccwantemu),
                getConfigListEntry("Keep Alive:", self.ccckeepalive),
                getConfigListEntry("Audio Disabled:", self.audisabled),
            ]
        elif proto in ["newcamd","mgcamd"]:
            cfg_list += [
                getConfigListEntry("Key:", self.key),
                getConfigListEntry("Disable Server Filter:", self.disableserverfilter),
                getConfigListEntry("Connect on Init:", self.connectoninit),
            ]
        self["config"].l.setList(cfg_list)

    def on_protocol_change(self, cfg=None):
        self.update_fields()

    def on_label_change(self, cfg=None):
        self.update_fields()

    # ----------------------------
    # Buttons
    # ----------------------------
    def open_red_job(self):
        self.session.open(OSCamReadersScreen)

    def open_green_job(self):
        self.session.open(GreenJobScreen)

    def yellow_button(self):
        self.add_reader()

    def open_blue_job(self):
        self.session.open(BlueJobScreen)

    def close_screen(self):
        self.close()

    # ----------------------------
    # Reader Management
    # ----------------------------
    def load_readers(self):
        file_path = os.path.join(self.panel_dir,"subscription.txt")
        readers = []
        if os.path.exists(file_path):
            with open(file_path,"r") as f:
                content = f.read()
            blocks = content.split("[reader]")
            for block in blocks:
                if not block.strip():
                    continue
                reader_info = {}
                for line in block.splitlines():
                    if "=" in line:
                        key,val = line.split("=",1)
                        reader_info[key.strip()] = val.strip()
                readers.append(reader_info)
        return readers

    def add_reader(self):
        proto = self.protocol.value.lower()
        label_value = self.label_custom.value if self.label_choice.value == "Custom" else self.label_choice.value

        # Build reader entry
        new_entry = self.create_reader_block(proto, label_value)

        # Always finish with two newlines to separate readers
        new_entry = new_entry.strip() + "\n\n"

        # Files to check/write
        target_files = [
            os.path.join(self.panel_dir, "subscription.txt"),
            "/etc/tuxbox/config/oscam.server",
            "/etc/tuxbox/config/ncam.server"
        ]

        summary = ""
        for file_path in target_files:
            if "subscription.txt" in file_path and not os.path.exists(self.panel_dir):
                os.makedirs(self.panel_dir)

            file_found = os.path.exists(file_path)
            if not file_found:
                summary += f"File not found: {file_path}\n"
                continue

            # Check if reader exists
            reader_exists = self.reader_exists(file_path)
            if reader_exists:
                summary += f"Reader already exists in: {file_path}\n"
            else:
                try:
                    with open(file_path, "a") as f:
                        # Ensure previous reader ended with a blank line
                        with open(file_path, "r") as fr:
                            content = fr.read()
                        if not content.endswith("\n\n") and len(content.strip()) > 0:
                            f.write("\n")
                        f.write(new_entry)
                    summary += f"Reader added to: {file_path}\n"
                except Exception as e:
                    summary += f"Failed to write to {file_path}: {str(e)}\n"

        if not summary:
            summary = "No files found or updated."
        self.session.open(MessageBox, summary, MessageBox.TYPE_INFO, timeout=10)

    def create_reader_block(self, proto, label_value):
        new_entry = (
            f"[reader]\n"
            f"label = {label_value}\n"
            f"protocol = {proto}\n"
            f"device = {self.host.value},{self.port.value}\n"
            f"user = {self.user.value}\n"
            f"password = {self.passw.value}\n"
        )
        if proto == "cccam":
            new_entry += (
               f"inactivitytimeout = {self.inactivitytimeout.value}\n"
               f"group = {self.group.value}\n"
               f"disablecrccws = {self.disablecrccws.value}\n"
               f"cccversion = {self.cccamversion.value}\n"
               f"cccwantemu = {self.cccwantemu.value}\n"
               f"ccckeepalive = {self.ccckeepalive.value}\n"
               f"audisabled = {self.audisabled.value}\n"
            )
        else:
            new_entry += (
               f"key = {self.key.value}\n"
               f"disableserverfilter = {self.disableserverfilter.value}\n"
               f"connectoninit = {self.connectoninit.value}\n"
               f"group = {self.group.value}\n"
               f"disablecrccws = {self.disablecrccws.value}\n"
            )
        return new_entry

    def reader_exists(self, file_path):
        try:
            with open(file_path, "r") as f:
                content = f.read()
            blocks = content.split("[reader]")
            for block in blocks:
                if (f"{self.host.value},{self.port.value}" in block and
                   self.user.value in block and
                   self.passw.value in block):
                    return True
        except Exception:
            return False
        return False

    # ----------------------------
    # Panel folder detection
    # ----------------------------
    def detect_panel_dir(self):
        for folder in PANEL_DIRS:
            cfg_file = os.path.join(folder, "panel_dir.cfg")
            if os.path.exists(cfg_file):
                return folder
        return PANEL_DIRS[1]  # default HDD

# ----------------------------
# GreenJobScreen
# ----------------------------
class GreenJobScreen(Screen):
    # ---------------- Load correct skin ----------------
    width, height = getDesktop(0).size().width(), getDesktop(0).size().height()
    skin_file = (
        "/usr/lib/enigma2/python/Plugins/Extensions/ElieSatPanelGrid/assets/skin/cccamadder2_fhd.xml"
        if width >= 1920
        else "/usr/lib/enigma2/python/Plugins/Extensions/ElieSatPanelGrid/assets/skin/cccamadder2_hd.xml"
    )
    try:
        with open(skin_file, "r") as f:
            skin = f.read()
    except Exception as e:
        print(f"[ElieSatPanel] Failed to load skin: {e}")
        skin = "<screen></screen>"

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        self.setTitle(_("Subscription Labels"))

        self["left_bar"] = Label("\n".join(list("Version " + Version)))
        self["right_bar"] = Label("\n".join(list("By ElieSat")))

        self["image_name"] = Label("Image: " + get_image_name())
        self["local_ip"] = Label("IP: " + get_local_ip())
        self["StorageInfo"] = Label(get_storage_info())
        self["RAMInfo"] = Label(get_ram_info())
        self["python_ver"] = Label("Python: " + get_python_version())
        self["net_status"] = Label("Net: " + check_internet())

        self.sub_labels_list = MenuList([], enableWrapAround=True)
        self["sub_labels"] = self.sub_labels_list
        self.update_subscription_list()

        self["red"] = Label(_("Remove Reader"))
        self["green"] = Label(_("Show Reader Block"))
        self["yellow"] = Label(_("Test Connection"))
        self["blue"] = Label(_("Show Credentials"))

        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions"],
            {
                "red": self.remove_selected_reader,
                "green": self.show_selected_reader,
                "yellow": self.test_selected_reader,
                "blue": self.show_credentials,
                "ok": self.ok_pressed,
                "cancel": self.close,
            },
            -1,
        )

    # ---------- File parsing ----------
    def read_labels_from_file(self, path):
        found = []
        try:
            with open(path, "r") as f:
                content = f.read()
            reader_blocks = re.findall(r"(\[reader\].*?)(?=\n\[|$)", content, re.DOTALL | re.IGNORECASE)
            for block in reader_blocks:
                label = re.search(r"label\s*=\s*(.+)", block, re.IGNORECASE)
                user = re.search(r"user\s*=\s*(.+)", block, re.IGNORECASE)
                passwd = re.search(r"password\s*=\s*(.+)", block, re.IGNORECASE)
                if label and user and passwd:
                    found.append((label.group(1).strip(), path, block.strip()))
        except:
            pass
        return found

    def get_subscription_labels(self):
        files = [
            "/media/hdd/ElieSatPanel/subscription.txt",
            "/media/usb/ElieSatPanel/subscription.txt",
            "/media/mmc/ElieSatPanel/subscription.txt",
        ]
        results = []
        for f in files:
            if os.path.exists(f):
                results.extend(self.read_labels_from_file(f))
        if not results:
            return [("No valid readers found", "", "")]
        return results

    def update_subscription_list(self):
        self.sub_labels_list.setList(self.get_subscription_labels())

    # ---------- Button functions ----------
    def remove_selected_reader(self):
        selected = self.sub_labels_list.getCurrent()
        if not selected or not selected[1]:
            return
        label, file_path, block = selected

        def confirm(result):
            if not result:
                return
            try:
                with open(file_path, "r") as f:
                    content = f.read()
                new_content = content.replace(block, "").strip()
                with open(file_path, "w") as f:
                    f.write(new_content)
                self.update_subscription_list()
                self.session.open(MessageBox, _("Removed reader: %s" % label), MessageBox.TYPE_INFO, 3)
            except Exception as e:
                self.session.open(MessageBox, _("Error: %s" % str(e)), MessageBox.TYPE_ERROR, 5)

        self.session.openWithCallback(confirm, MessageBox, _("Remove reader %s?" % label), MessageBox.TYPE_YESNO)

    def show_selected_reader(self):
        selected = self.sub_labels_list.getCurrent()
        if not selected:
            return
        label, file_path, block = selected
        self.session.open(MessageBox, _("File: %s\n\n%s" % (file_path, block)), MessageBox.TYPE_INFO, 10)

    def test_selected_reader(self):
        selected = self.sub_labels_list.getCurrent()
        if not selected:
            return
        label, file_path, block = selected
        host = re.search(r"device\s*=\s*([^,]+)", block)
        port = re.search(r"device\s*=\s*[^,]+,(\d+)", block)
        if not host or not port:
            self.session.open(MessageBox, _("No host/port found."), MessageBox.TYPE_ERROR, 3)
            return
        try:
            sock = socket.create_connection((host.group(1).strip(), int(port.group(1))), timeout=5)
            sock.close()
            self.session.open(MessageBox, _("Connection OK to %s:%s" % (host.group(1), port.group(1))), MessageBox.TYPE_INFO, 3)
        except Exception as e:
            self.session.open(MessageBox, _("Connection failed: %s" % str(e)), MessageBox.TYPE_ERROR, 5)

    def show_credentials(self):
        selected = self.sub_labels_list.getCurrent()
        if not selected:
            return
        label, file_path, block = selected
        host = re.search(r"device\s*=\s*([^,]+)", block)
        port = re.search(r"device\s*=\s*[^,]+,(\d+)", block)
        user = re.search(r"user\s*=\s*(.+)", block)
        passwd = re.search(r"password\s*=\s*(.+)", block)
        msg = "Label: %s\nFile: %s\nHost: %s\nPort: %s\nUser: %s\nPass: %s" % (
            label,
            os.path.basename(file_path),
            host.group(1).strip() if host else "N/A",
            port.group(1).strip() if port else "N/A",
            user.group(1).strip() if user else "N/A",
            passwd.group(1).strip() if passwd else "N/A",
        )
        self.session.open(MessageBox, msg, MessageBox.TYPE_INFO, 10)

    # ---------- OK button: Restore Reader ----------
    def ok_pressed(self):
        selected = self.sub_labels_list.getCurrent()
        if not selected or not selected[1]:
            return
        label, file_path, block = selected

        def confirm_restore(result):
            if not result:
                return

            targets = [
                ("/etc/tuxbox/config/oscam.server", "OSCam"),
                ("/etc/tuxbox/config/ncam.server", "NCam"),
            ]
            messages = []

            for target, name in targets:
                if not os.path.exists(target):
                    messages.append("%s file not found" % name)
                    continue
                try:
                    with open(target, "r") as f:
                        content = f.read()
                    if block.strip() in content:
                        messages.append("Reader already exists in %s" % name)
                        continue
                    with open(target, "a") as f:
                        f.write("\n\n" + block.strip() + "\n")
                    messages.append("Restored successfully in %s" % name)
                except Exception as e:
                    messages.append("Error restoring in %s: %s" % (name, str(e)))

            final_msg = "\n".join(messages)
            self.session.open(MessageBox, _(final_msg), MessageBox.TYPE_INFO, 5)

        self.session.openWithCallback(confirm_restore, MessageBox, _("Do you want to restore this reader?"), MessageBox.TYPE_YESNO)


# ----------------------------
# BlueJobScreen
# ----------------------------
class BlueJobScreen(Screen):
    # ---------------- Load correct skin ----------------
    width, height = getDesktop(0).size().width(), getDesktop(0).size().height()
    skin_file = (
        "/usr/lib/enigma2/python/Plugins/Extensions/ElieSatPanelGrid/assets/skin/cccamadder1_fhd.xml"
        if width >= 1920
        else "/usr/lib/enigma2/python/Plugins/Extensions/ElieSatPanelGrid/assets/skin/cccamadder1_hd.xml"
    )
    try:
        with open(skin_file, "r") as f:
            skin = f.read()
    except Exception as e:
        print(f"[ElieSatPanel] Failed to load skin: {e}")
        skin = "<screen></screen>"

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        self.setTitle(_("Subscription Labels"))

        # Bars
        self["left_bar"] = Label("\n".join(list("Version " + Version)))
        self["right_bar"] = Label("\n".join(list("By ElieSat")))

        # System info
        self["image_name"] = Label("Image: " + get_image_name())
        self["local_ip"] = Label("IP: " + get_local_ip())
        self["StorageInfo"] = Label(get_storage_info())
        self["RAMInfo"] = Label(get_ram_info())
        self["python_ver"] = Label("Python: " + get_python_version())
        self["net_status"] = Label("Net: " + check_internet())

        # Subscription list
        self.sub_labels_list = MenuList([], enableWrapAround=True)
        self["sub_labels"] = self.sub_labels_list
        self.update_subscription_list()

        # Buttons
        self["red"] = Label(_("Remove Reader"))
        self["green"] = Label(_("Show Reader Block"))
        self["yellow"] = Label(_("Test Connection"))
        self["blue"] = Label(_("Show Credentials"))

        # Actions
        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions"],
            {
                "red": self.remove_selected_reader,
                "green": self.show_selected_reader,
                "yellow": self.test_selected_reader,
                "blue": self.show_credentials,
                "ok": self.show_credentials,
                "cancel": self.close,
            },
            -1,
        )

    # ---------- File parsing ----------
    def read_labels_from_file(self, path):
        found = []
        try:
            with open(path, "r") as f:
                content = f.read()
            reader_blocks = re.findall(r"(\[reader\].*?)(?=\n\[|$)", content, re.DOTALL | re.IGNORECASE)
            for block in reader_blocks:
                label = re.search(r"label\s*=\s*(.+)", block, re.IGNORECASE)
                user = re.search(r"user\s*=\s*(.+)", block, re.IGNORECASE)
                passwd = re.search(r"password\s*=\s*(.+)", block, re.IGNORECASE)
                if label and user and passwd:
                    found.append((label.group(1).strip(), path, block.strip()))
        except:
            pass
        return found

    def get_subscription_labels(self):
        files = [
            "/media/hdd/ElieSatPanel/subscription.txt",
            "/media/usb/ElieSatPanel/subscription.txt",
            "/media/mmc/ElieSatPanel/subscription.txt",
            "/etc/tuxbox/config/oscam.server",
            "/etc/tuxbox/config/ncam.server",
        ]
        results = []
        for f in files:
            if os.path.exists(f):
                results.extend(self.read_labels_from_file(f))
        if not results:
            return [("No valid readers found", "", "")]
        return results

    def update_subscription_list(self):
        self.sub_labels_list.setList(self.get_subscription_labels())

    # ---------- Button functions ----------
    def remove_selected_reader(self):
        selected = self.sub_labels_list.getCurrent()
        if not selected or not selected[1]:
            return
        label, file_path, block = selected

        def confirm(result):
            if not result:
                return
            try:
                with open(file_path, "r") as f:
                    content = f.read()
                new_content = content.replace(block, "").strip()
                with open(file_path, "w") as f:
                    f.write(new_content)
                self.update_subscription_list()
                self.session.open(MessageBox, _("Removed reader: %s" % label), MessageBox.TYPE_INFO, 3)
            except Exception as e:
                self.session.open(MessageBox, _("Error: %s" % str(e)), MessageBox.TYPE_ERROR, 5)

        self.session.openWithCallback(confirm, MessageBox, _("Remove reader %s?" % label), MessageBox.TYPE_YESNO)

    def show_selected_reader(self):
        selected = self.sub_labels_list.getCurrent()
        if not selected:
            return
        label, file_path, block = selected
        self.session.open(MessageBox, _("File: %s\n\n%s" % (file_path, block)), MessageBox.TYPE_INFO, 10)

    def test_selected_reader(self):
        selected = self.sub_labels_list.getCurrent()
        if not selected:
            return
        label, file_path, block = selected
        host = re.search(r"device\s*=\s*([^,]+)", block)
        port = re.search(r"device\s*=\s*[^,]+,(\d+)", block)
        if not host or not port:
            self.session.open(MessageBox, _("No host/port found."), MessageBox.TYPE_ERROR, 3)
            return
        try:
            sock = socket.create_connection((host.group(1).strip(), int(port.group(1))), timeout=5)
            sock.close()
            self.session.open(MessageBox, _("Connection OK to %s:%s" % (host.group(1), port.group(1))), MessageBox.TYPE_INFO, 3)
        except Exception as e:
            self.session.open(MessageBox, _("Connection failed: %s" % str(e)), MessageBox.TYPE_ERROR, 5)

    def show_credentials(self):
        selected = self.sub_labels_list.getCurrent()
        if not selected:
            return
        label, file_path, block = selected
        host = re.search(r"device\s*=\s*([^,]+)", block)
        port = re.search(r"device\s*=\s*[^,]+,(\d+)", block)
        user = re.search(r"user\s*=\s*(.+)", block)
        passwd = re.search(r"password\s*=\s*(.+)", block)
        msg = "Label: %s\nFile: %s\nHost: %s\nPort: %s\nUser: %s\nPass: %s" % (
            label,
            os.path.basename(file_path),
            host.group(1).strip() if host else "N/A",
            port.group(1).strip() if port else "N/A",
            user.group(1).strip() if user else "N/A",
            passwd.group(1).strip() if passwd else "N/A",
        )
        self.session.open(MessageBox, msg, MessageBox.TYPE_INFO, 10)

