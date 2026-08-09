# -*- coding: utf-8 -*-
import os
from enigma import getDesktop
from Plugins.Extensions.ElieSatPanelGrid.menus.Console import Console
from Plugins.Extensions.ElieSatPanelGrid.menus.Cccamadder.Showstatus import Showstatus
from Plugins.Extensions.ElieSatPanelGrid.__init__ import Version

try:
    from Plugins.Extensions.ElieSatPanelGrid.__init__ import Panel
except ImportError:
    Panel = "ElieSatPanel"

from Components.ActionMap import NumberActionMap, ActionMap
from Components.Sources.StaticText import StaticText
from Components.Label import Label
from Components.Pixmap import Pixmap
from Tools.LoadPixmap import LoadPixmap
from Tools.Directories import fileExists, resolveFilename, SCOPE_PLUGINS
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Components.ConfigList import ConfigListScreen
from Components.config import (
    ConfigText,
    ConfigSelection,
    ConfigInteger,
    getConfigListEntry
)

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
    get_ram_info,
    restart_softcam_services
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

PANEL_DIRS = [
    "/media/hdd/ElieSatPanel",
    "/media/usb/ElieSatPanel",
    "/media/mmc/ElieSatPanel",
    "/etc/enigma2/ElieSatPanel"
]

class Cccamadder(Screen, ConfigListScreen):

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session

        try:
            skin_file = resolveFilename(SCOPE_PLUGINS, "Extensions/ElieSatPanelGrid/menus/Cccamadder/Cccamadder_fhd.xml")
            with open(skin_file, "r") as f:
                self.skin = f.read()
        except Exception as e:
            print("[ServerEagleSat Submenu] Critical Error Reading Skin File:", e)
            self.skin = "<screen name='ServerEagleSat' position='center,center' size='1920,1080' backgroundColor='#000000'/>"

        self.setTitle(_("ServerEagleSat - Add Reader"))
        self.panel_dir = self.detect_panel_dir()
        
        if not os.path.exists(self.panel_dir):
            try:
                os.makedirs(self.panel_dir)
            except Exception:
                pass
        
        sub_file = os.path.join(self.panel_dir, "subscription.txt")
        if not os.path.exists(sub_file):
            try:
                with open(sub_file, "w") as f:
                    f.write("")
            except Exception:
                pass

        self.system_info = SystemInfo()

        self.label_choice = ConfigSelection(default="ServerEagle", choices=[("ServerEagle", "ServerEagle"), ("ElieSat", "ElieSat"), ("Custom", "Custom")])
        self.label_custom = ConfigText(default="server_name", fixed_size=False)
        self.label_custom.useKeyboard = True
        
        self.status = ConfigSelection(default="enabled", choices=[("enabled", "Enabled"), ("disabled", "Disabled")])
        self.protocol = ConfigSelection(default="cccam", choices=[("cccam", "CCcam"), ("newcamd", "NewCamd"), ("mgcamd", "MgCamd")])
        self.host = ConfigText(default="tv8k.cc", fixed_size=False)
        self.host.useKeyboard = True
        self.port = ConfigInteger(default=44355, limits=(1, 65535))
        self.user = ConfigText(default="servereaglesat", fixed_size=False)
        self.user.useKeyboard = True
        self.passw = ConfigText(default="servereaglesat", fixed_size=False)
        self.passw.useKeyboard = True
        self.inactivitytimeout = ConfigInteger(default=30, limits=(1, 99))
        self.group = ConfigInteger(default=1, limits=(0, 99))
        
        self.disablecrccws = ConfigSelection(default="1", choices=[("0", "No"), ("1", "Yes")])
        self.cccamversion = ConfigSelection(default="2.0.11", choices=[(v, v) for v in ["2.0.11", "2.1.1", "2.1.2", "2.1.3", "2.1.4", "2.2.0", "2.2.1", "2.3.0", "2.3.1", "2.3.2"]])
        self.cccwantemu = ConfigSelection(default="1", choices=[("0", "No"), ("1", "Yes")])
        self.ccckeepalive = ConfigSelection(default="1", choices=[("0", "No"), ("1", "Yes")])
        self.audisabled = ConfigSelection(default="1", choices=[("0", "No"), ("1", "Yes")])
        
        self.key = ConfigText(default="0102030405060708091011121314", fixed_size=False)
        self.key.useKeyboard = True
        self.disableserverfilter = ConfigSelection(default="1", choices=[("0", "No"), ("1", "Yes")])
        self.connectoninit = ConfigSelection(default="1", choices=[("0", "No"), ("1", "Yes")])

        self.load_last_reader_to_config()

        ConfigListScreen.__init__(self, [], session=session)
        
        self.update_fields()

        self.label_choice.addNotifier(self.on_config_change, initial_call=False)
        self.protocol.addNotifier(self.on_config_change, initial_call=False)

        self["NumberActions"] = NumberActionMap(["NumberActions"], {
            '0': self.keyNumberGlobal,
            '1': self.keyNumberGlobal,
            '2': self.keyNumberGlobal,
            '3': self.keyNumberGlobal,
            '4': self.keyNumberGlobal,
            '5': self.keyNumberGlobal,
            '6': self.keyNumberGlobal,
            '7': self.keyNumberGlobal,
            '8': self.keyNumberGlobal,
            '9': self.keyNumberGlobal
        })

        self["config_actions"] = ActionMap(["SetupActions", "DirectionActions"], {
            "left": self.keyLeft,
            "right": self.keyRight,
            "up": self.keyUp,
            "down": self.keyDown
        }, -1)

        self["shortcuts"] = NumberActionMap(
            ["ShortcutActions", "WizardActions", "ColorActions", "HotkeyActions"],
            {
                "ok": self.keyOK,
                "cancel": self.exit,
                "back": self.exit,
                "green": self.keyGreenSave,
                "red": self.sharing,
                "yellow": self.scriptslist,  # Swapped: Yellow now triggers Select Reader/Backup
                "blue": self.grid,           # Swapped: Blue now triggers Delete/Remove Reader
                "info": self.infoKey,
            }
        )

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

        self["red"] = Label(_("Show Status"))
        self["green"] = Label(_("Save"))
        self["yellow"] = Label(_("Select Backup"))
        self["blue"] = Label(_("Remove Backup"))

        self.onLayoutFinish.append(self.loadScreenData)

    def parse_subscription_file(self):
        file_path = os.path.join(self.panel_dir, "subscription.txt")
        if not os.path.exists(file_path):
            return []
        try:
            with open(file_path, "r") as f:
                content = f.read()
            blocks = content.split("[reader]")
            readers = []
            for b in blocks:
                if not b.strip():
                    continue
                info = {}
                lines = []
                for line in b.splitlines():
                    if "=" in line:
                        k, v = line.split("=", 1)
                        info[k.strip()] = v.strip()
                    lines.append(line)
                info["_raw_lines"] = lines
                readers.append(info)
            return readers
        except Exception as e:
            print("[ServerEagleSat] Error parsing subscription file:", e)
            return []

    def load_last_reader_to_config(self):
        readers = self.parse_subscription_file()
        if not readers:
            self.host.value = "tv8k.cc"
            self.port.value = 22222
            self.user.value = "servereaglesat"
            self.passw.value = "servereaglesat"
            self.protocol.value = "cccam"
            self.status.value = "enabled"
            self.label_choice.value = "ServerEagle"
            self.label_custom.value = "server_name"
            return
        try:
            last = readers[-1]
            if "protocol" in last:
                p_val = last["protocol"].lower()
                if p_val in ["cccam", "newcamd", "mgcamd"]:
                    self.protocol.value = p_val
            if "device" in last and "," in last["device"]:
                h_val, p_val = last["device"].split(",", 1)
                self.host.value = h_val.strip()
                try:
                    self.port.value = int(p_val.strip())
                except Exception:
                    pass
            if "user" in last:
                self.user.value = last["user"]
            if "password" in last:
                self.passw.value = last["password"]
            if "enable" in last:
                self.status.value = "enabled" if last["enable"] == "1" else "disabled"
            if "group" in last:
                try:
                    self.group.value = int(last["group"])
                except Exception:
                    pass
            if "disablecrccws" in last and last["disablecrccws"] in ["0", "1"]:
                self.disablecrccws.value = last["disablecrccws"]
            if "inactivitytimeout" in last:
                try:
                    self.inactivitytimeout.value = int(last["inactivitytimeout"])
                except Exception:
                    pass
            if "cccversion" in last:
                self.cccamversion.value = last["cccversion"]
            if "cccwantemu" in last and last["cccwantemu"] in ["0", "1"]:
                self.cccwantemu.value = last["cccwantemu"]
            if "ccckeepalive" in last and last["ccckeepalive"] in ["0", "1"]:
                self.ccckeepalive.value = last["ccckeepalive"]
            if "audisabled" in last and last["audisabled"] in ["0", "1"]:
                self.audisabled.value = last["audisabled"]
            if "key" in last:
                self.key.value = last["key"]
            if "disableserverfilter" in last and last["disableserverfilter"] in ["0", "1"]:
                self.disableserverfilter.value = last["disableserverfilter"]
            if "connectoninit" in last and last["connectoninit"] in ["0", "1"]:
                self.connectoninit.value = last["connectoninit"]
            if "label" in last:
                lbl = last["label"]
                if lbl in ["ServerEagle", "ElieSat"]:
                    self.label_choice.value = lbl
                else:
                    self.label_choice.value = "Custom"
                    self.label_custom.value = lbl
        except Exception as e:
            print("[ServerEagleSat] Error Restoring History Configuration Setup:", e)

    def update_fields(self):
        cfg_list = [
            getConfigListEntry("Label:", self.label_choice),
        ]
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

        proto = self.protocol.value.lower()
        if proto == "cccam":
            cfg_list += [
                getConfigListEntry("Disable CRC/CWS:", self.disablecrccws),
                getConfigListEntry("CCcam Version:", self.cccamversion),
                getConfigListEntry("Want Emu:", self.cccwantemu),
                getConfigListEntry("Keep Alive:", self.ccckeepalive),
                getConfigListEntry("Audio Disabled:", self.audisabled),
            ]
        elif proto in ["newcamd", "mgcamd"]:
            cfg_list += [
                getConfigListEntry("Key:", self.key),
                getConfigListEntry("Disable Server Filter:", self.disableserverfilter),
                getConfigListEntry("Connect on Init:", self.connectoninit),
            ]

        self["config"].l.setList(cfg_list)

    def on_config_change(self, cfg=None):
        self.update_fields()

    def get_egami_rules(self):
        return (
            '[ -d /usr/emu_scripts ] && d="/usr/emu_scripts" && p="EGcam_"; '
            'if [ -n "$d" ]; then '
            'for s in $d/${p}*.sh; do [[ "$s" != *"_Ci.sh"* ]] && [ -f "$s" ] && "$s" stop; done; '
            'sleep 2; l=0; '
            'for s in $d/${p}*[nN][cC][aA][mI]*.sh; do [ -f "$s" ] && { "$s" start & l=1; break; }; done; '
            'if [ $l -eq 0 ]; then '
            'for s in $d/${p}*[oO][sS][cA][aA][mM]*.sh; do [ -f "$s" ] && { "$s" start & break; }; done; '
            'fi; fi'
        )

    def keyGreenSave(self):
        summary_report = self.add_reader()
        success, restart_report = restart_softcam_services(custom_egami_cmd=self.get_egami_rules())
        final_message = f"{summary_report}\n---------------------------------------\n{restart_report}"
        self.session.open(MessageBox, final_message, MessageBox.TYPE_INFO)

    def sharing(self):
        self.session.open(Showstatus)

    def build_entry_string(self, label, enable, protocol, host, port, user, password, extra_dict=None):
        entry = (
            "[reader]\n"
            f"label = {label}\n"
            f"enable = {enable}\n"
            f"protocol = {protocol}\n"
            f"device = {host},{port}\n"
            f"user = {user}\n"
            f"password = {password}\n"
        )
        if extra_dict:
            for k, v in extra_dict.items():
                if k not in ["label", "enable", "protocol", "device", "user", "password", "_raw_lines"]:
                    entry += f"{k} = {v}\n"
        entry = entry.strip() + "\n\n"
        return entry

    def add_reader(self):
        proto = self.protocol.value.lower()
        lbl_val = self.label_custom.value if self.label_choice.value == "Custom" else self.label_choice.value
        enable_val = "1" if self.status.value == "enabled" else "0"

        extra = {}
        if proto == "cccam":
            extra = {
                "inactivitytimeout": self.inactivitytimeout.value,
                "group": self.group.value,
                "disablecrccws": self.disablecrccws.value,
                "cccversion": self.cccamversion.value,
                "cccwantemu": self.cccwantemu.value,
                "ccckeepalive": self.ccckeepalive.value,
                "audisabled": self.audisabled.value
            }
        else:
            extra = {
                "key": self.key.value,
                "disableserverfilter": self.disableserverfilter.value,
                "connectoninit": self.connectoninit.value,
                "group": self.group.value,
                "disablecrccws": self.disablecrccws.value
            }

        entry = self.build_entry_string(lbl_val, enable_val, proto, self.host.value, self.port.value, self.user.value, self.passw.value, extra)
        return self.write_to_targets(entry, self.host.value, self.port.value, self.user.value, self.passw.value)

    def write_to_targets(self, entry_str, host, port, user, password):
        targets = [
            os.path.join(self.panel_dir, "subscription.txt"),
            "/etc/tuxbox/config/ncam.server",
            "/etc/tuxbox/config/ncam-icam/ncam.server",
            "/etc/tuxbox/config/oscam.server",
            "/etc/tuxbox/config/oscam/oscam.server",
            "/etc/tuxbox/config/oscam-emu/oscam.server",
            "/etc/tuxbox/config/oscam-master/oscam.server",
            "/etc/tuxbox/config/oscam-smod/oscam.server",
            "/etc/tuxbox/config/oscamicamnew/oscam.server",
            "/etc/tuxbox/config/oscamicamall/oscam.server",
            "/etc/tuxbox/config/oscam-icam/oscam.server"
        ]

        target_label = self.label_custom.value if self.label_choice.value == "Custom" else self.label_choice.value
        match_device = f"{host},{port}"
        summary = ""

        for path in targets:
            if "subscription.txt" in path and not os.path.exists(self.panel_dir):
                try:
                    os.makedirs(self.panel_dir)
                except Exception:
                    continue

            if not os.path.exists(path):
                continue

            try:
                with open(path, "r") as fr:
                    content = fr.read()

                blocks = content.split("[reader]")
                cleaned_blocks = []
                was_replaced = False
                credential_duplicate_found = False

                for b in blocks:
                    if not b.strip():
                        continue
                    
                    block_label = ""
                    block_device = ""
                    block_user = ""
                    block_pass = ""

                    for line in b.splitlines():
                        line_stripped = line.strip()
                        if "=" in line_stripped:
                            k, v = line_stripped.split("=", 1)
                            k, v = k.strip().lower(), v.strip()
                            if k == "label":
                                block_label = v
                            elif k == "device":
                                block_device = v
                            elif k == "user":
                                block_user = v
                            elif k == "password":
                                block_pass = v

                    if block_device == match_device and block_user == user and block_pass == password and block_label != target_label:
                        credential_duplicate_found = True

                    if block_label == target_label:
                        was_replaced = True
                    else:
                        cleaned_blocks.append("[reader]" + b)

                if credential_duplicate_found:
                    summary += f"Skipped (Credentials already exist): {path}\n"
                    continue

                new_content = "".join(cleaned_blocks).strip()
                if new_content:
                    new_content += "\n\n"
                new_content += entry_str

                with open(path, "w") as fw:
                    fw.write(new_content)

                if was_replaced:
                    summary += f"Updated existing label in: {path}\n"
                else:
                    summary += f"Successfully written: {path}\n"
            except Exception as ex:
                summary += f"Write failure {path}: {str(ex)}\n"

        if not summary:
            summary = "No eligible active softcam config files discovered."
        
        return summary

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
            print("[ServerEagleSat Submenu] Hardware Specifications Load Failure:", e)

        try:
            local_ip = get_local_ip()
            if "ipInfo" in self:
                self["ipInfo"].setText(str(local_ip))
            if "local_ip" in self:
                self["local_ip"].setText("IP: " + str(local_ip))

            net_status = check_internet()
            status_text = _("Connected") if net_status == "Online" else _("Disconnected")
            if "internet" in self:
                self["internet"].setText(status_text)
            if "net_status" in self:
                self["net_status"].setText("Net: " + str(net_status))
        except Exception as e:
            print("[ServerEagleSat Submenu] Network Target Mapping Failure:", e)

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
            print("SUBMENU ICON ERROR:", e)

    def detect_panel_dir(self):
        for folder in PANEL_DIRS:
            if os.path.exists(folder) or os.path.exists(os.path.join(folder, "panel_dir.cfg")):
                return folder
        if os.path.exists("/media/hdd"):
            return "/media/hdd/ServerEagleSat"
        elif os.path.exists("/media/usb"):
            return "/media/usb/ServerEagleSat"
        elif os.path.exists("/media/mmc"):
            return "/media/mmc/ServerEagleSat"
        return "/media/hdd/ServerEagleSat"

    def keyNumberGlobal(self, number):
        current_item = self["config"].getCurrent()
        is_input_field = False
        
        if current_item and len(current_item) > 1:
            config_element = current_item[1]
            element_type = config_element.__class__.__name__
            if element_type in ["ConfigInteger", "ConfigText"]:
                is_input_field = True

        if is_input_field:
            ConfigListScreen.keyNumberGlobal(self, number)
        elif number == 0:
            self.session.open(Console, _("Updating..."), [
                "wget --no-check-certificate https://raw.githubusercontent.com/eliesat/eliesatpanel/main/installer.sh -qO - | /bin/sh"
            ])
        else:
            ConfigListScreen.keyNumberGlobal(self, number)

    def exit(self):
        self.close()

    def grid(self):
        readers = self.parse_subscription_file()
        if not readers:
            self.session.open(MessageBox, _("No backup readers found to remove."), MessageBox.TYPE_INFO)
            return

        choices = []
        for index, r in enumerate(readers):
            label = r.get("label", "Unknown")
            device = r.get("device", "0,0")
            url, port = device.split(",", 1) if "," in device else (device, "0")
            username = r.get("user", "Unknown")
            password = r.get("password", "Unknown")

            display_line = f"{label} | {url.strip()} | {port.strip()} | {username} | {password}"
            choices.append((display_line, index))

        self.session.openWithCallback(self.on_reader_selected_to_remove, ChoiceBox, title=_("Select a reader to remove:"), list=choices)

    def on_reader_selected_to_remove(self, choice):
        if choice is None:
            return

        selected_index = choice[1]
        file_path = os.path.join(self.panel_dir, "subscription.txt")
        
        try:
            readers = self.parse_subscription_file()
            if selected_index >= len(readers):
                return

            del readers[selected_index]

            new_content = ""
            for r in readers:
                new_content += self.build_entry_string(
                    r.get("label", "Unknown"),
                    r.get("enable", "1"),
                    r.get("protocol", "cccam"),
                    r.get("device", "0,0").split(",")[0],
                    r.get("device", "0,0").split(",")[1] if "," in r.get("device", "0,0") else "0",
                    r.get("user", ""),
                    r.get("password", ""),
                    r
                )

            with open(file_path, "w") as f:
                f.write(new_content.strip() + "\n\n" if new_content.strip() else "")

            self.session.open(MessageBox, _("Reader removed successfully from backup storage!"), MessageBox.TYPE_INFO)
            
            self.load_last_reader_to_config()
            self.update_fields()

        except Exception as e:
            self.session.open(MessageBox, _(f"Failed to remove chosen reader configuration block:\n{str(e)}"), MessageBox.TYPE_ERROR)

    def scriptslist(self):
        readers = self.parse_subscription_file()
        if not readers:
            self.session.open(MessageBox, _("No readers found in subscription file."), MessageBox.TYPE_INFO)
            return

        choices = []
        for index, r in enumerate(readers):
            label = r.get("label", "Unknown")
            device = r.get("device", "0,0")
            url, port = device.split(",", 1) if "," in device else (device, "0")
            username = r.get("user", "Unknown")
            password = r.get("password", "Unknown")

            display_line = f"{label} | {url.strip()} | {port.strip()} | {username} | {password}"
            choices.append((display_line, index))

        self.session.openWithCallback(self.on_reader_selected, ChoiceBox, title=_("Select Reader to Select/Move:"), list=choices)

    def on_reader_selected(self, choice):
        if choice is None:
            return

        selected_index = choice[1]
        file_path = os.path.join(self.panel_dir, "subscription.txt")

        try:
            readers = self.parse_subscription_file()
            if not readers or selected_index >= len(readers):
                return

            chosen_reader = readers.pop(selected_index)
            readers.append(chosen_reader)

            new_content = ""
            for r in readers:
                new_content += self.build_entry_string(
                    r.get("label", "Unknown"),
                    r.get("enable", "1"),
                    r.get("protocol", "cccam"),
                    r.get("device", "0,0").split(",")[0],
                    r.get("device", "0,0").split(",")[1] if "," in r.get("device", "0,0") else "0",
                    r.get("user", ""),
                    r.get("password", ""),
                    r
                )

            with open(file_path, "w") as f:
                f.write(new_content.strip() + "\n\n")

            self.load_last_reader_to_config()
            self.update_fields()

        except Exception as e:
            print("[ServerEagleSat] Error arranging reader sequence block:", e)

    def infoKey(self):
        self.session.open(Console, _("Please wait..."), [
            "wget --no-check-certificate https://gitlab.com/eliesat/scripts/-/raw/main/check/_check-all.sh -qO - | /bin/sh"
        ])
        
    def keyOK(self):
        ConfigListScreen.keyOK(self)
