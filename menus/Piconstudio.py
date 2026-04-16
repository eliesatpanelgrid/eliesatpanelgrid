# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function

import os
import sys
import time
import re

from Screens.Screen import Screen
from Screens.MessageBox import MessageBox

from Components.ActionMap import ActionMap
from Components.Sources.List import List
from Components.Label import Label
from Components.ProgressBar import ProgressBar

from Tools.LoadPixmap import LoadPixmap
from Tools.Directories import resolveFilename, SCOPE_PLUGINS

from enigma import getDesktop, eConsoleAppContainer, eTimer

from threading import Timer
import requests
import hashlib

from Plugins.Extensions.ElieSatPanelGrid.__init__ import Version
from Plugins.Extensions.ElieSatPanelGrid.menus.Helpers import (
    get_local_ip, check_internet, get_image_name,
    get_python_version, get_storage_info, get_ram_info
)


def _(txt):
    return txt

    # ---------------- GitHub Update ----------------
    def update_extensions_from_github(self):
        try:
            response = requests.get(EXTENSIONS_URL, timeout=10)
            if response.status_code != 200:
                print(f"[Picons] Failed to fetch extensions: {response.status_code}")
                return False

            new_hash = hashlib.md5(response.content).hexdigest()
            local_hash = None
            if os.path.exists(LOCAL_EXTENSIONS):
                with open(LOCAL_EXTENSIONS, "rb") as f:
                    local_hash = hashlib.md5(f.read()).hexdigest()

            if local_hash == new_hash:
                print("[Picons] Extensions already up-to-date")
                return False

            with open(LOCAL_EXTENSIONS, "wb") as f:
                f.write(response.content)

            print("[Picons] Extensions file updated from GitHub")

            if not self.in_submenu:
                self.load_main_menu()
            else:
                for cat in self.main_categories:
                    if cat[0] == self.submenu_title:
                        self.load_sub_menu(cat[2], cat[0])
                        break
            return True
        except Exception as e:
            print("[Picons] update_extensions_from_github error:", e)
            return False

def open_file(path, mode="r"):
    if sys.version_info[0] >= 3:
        return open(path, mode, encoding="utf-8", errors="ignore")
    return open(path, mode)

EXTENSIONS_URL = "https://raw.githubusercontent.com/eliesat/eliesatpanelgrid/refs/heads/main/assets/data//picons"
LOCAL_EXTENSIONS = "/usr/lib/enigma2/python/Plugins/Extensions/ElieSatPanelGrid/assets/data/picons"

class InstallationReport(Screen):
    skin = """
    <screen name="InstallationReport" position="center,center" size="800,500" title="Installation Report">
        <widget name="report" position="10,10" size="780,480" font="Regular;32" foregroundColor="#FFFFFF" backgroundColor="#000000" />
    </screen>"""

    def __init__(self, session, installed, failed):
        Screen.__init__(self, session)
        self["report"] = Label(self.buildText(installed, failed))

        # Allow exiting with Return/Back button
        self["actions"] = ActionMap(["OkCancelActions"], 
                                    {"cancel": self.close, "ok": self.close}, -1)

    def buildText(self, installed, failed):
        text = "Installed Items:\n"
        if installed:
            text += "\n".join(installed)
        else:
            text += "None"
        text += "\n\nFailed Items:\n"
        if failed:
            text += "\n".join(failed)
        else:
            text += "None"
        return text


class Piconstudio(Screen):

    width = getDesktop(0).size().width()
    skin = open(
        "/usr/lib/enigma2/python/Plugins/Extensions/ElieSatPanelGrid/assets/skin/%s"
        % ("eliesatpanel_list_fhd.xml" if width >= 1920 else "eliesatpanel_list_hd.xml")
    ).read()

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        self.setTitle(_("PiconStudio"))

        # ================= UI =================
        self["menu"] = List([])
        self["selection_count"] = Label(_("Selected: 0"))

        self["key_red"] = Label(_("Cancel"))
        self["key_green"] = Label(_("Install"))
        self["key_yellow"] = Label(_("Select All"))
        self["key_blue"] = Label(_("Report"))

        self["image_name"] = Label("Image: " + get_image_name())
        self["local_ip"] = Label("IP: " + get_local_ip())
        self["StorageInfo"] = Label(get_storage_info())
        self["RAMInfo"] = Label(get_ram_info())
        self["python_ver"] = Label("Python: " + get_python_version())
        self["net_status"] = Label("Net: " + check_internet())

        self["left_bar"] = Label("\n".join(list("Version " + Version)))
        self["right_bar"] = Label("\n".join(list("By ElieSat")))

        # ---- INSTALL UI ----
        self["item_name"] = Label("")
        self["download_info"] = Label("")
        self["download_info"].show()

        self["progress"] = ProgressBar()
        self["progress"].setRange((0, 100))
        self["progress"].setValue(0)
        self["progress"].hide()

        # ================= ACTIONS =================
        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions"],
            {
                "ok": self.toggleSelection,
                "cancel": self.close,
                "red": self.stopInstallation,
                "green": self.installSelected,
                "yellow": self.toggleSelectAll,
                "blue": self.showReport,
            },
            -1
        )

        # ================= DATA =================
        self.checked_icon = LoadPixmap(
            resolveFilename(
                SCOPE_PLUGINS,
                "Extensions/ElieSatPanelGrid/assets/icon/checked.png"
            )
        )
        self.unchecked_icon = LoadPixmap(
            resolveFilename(
                SCOPE_PLUGINS,
                "Extensions/ElieSatPanelGrid/assets/icon/unchecked.png"
            )
        )

        self.list = []
        self.selected_plugins = []
        self.download_queue = []

        self.container = None
        self.current_pkg = None

        # ===== PROGRESS =====
        self.total_packages = 0
        self.current_index = 0
        self.install_fake_progress = 0
        self.progressTimer = eTimer()
        self.progressTimer.callback.append(self._onInstallProgress)
        self.pauseTimer = None

        # ===== RESULT TRACKING =====
        self.total_selected = 0
        self.success_installs = 0
        self.installed_items = []
        self.failed_items = []

        # ===== INSTALLATION FLAG =====
        self.installation_in_progress = False

        # ===== DONE MESSAGE FLAG =====
        self.showing_done_message = False

        # ===== BUILD MENU =====
        self.buildList()

        Timer(1, self.update_extensions_from_github).start()

    # ================= FILE =================
    def status_path(self):
        path = "/usr/lib/enigma2/python/Plugins/Extensions/ElieSatPanelGrid/assets/data/picons"
        return path if os.path.isfile(path) else None

    # ================= LIST (FIXED HEADER LOGIC) =================
    def buildList(self):
        self.list = []
        self.selected_plugins = []

        path = self.status_path()
        if not path:
            self.showError(_("Picons file not found"))
            return

        # ---------- parse packages ----------
        packages = []
        name = version = description = status = None

        for line in open_file(path):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            low = line.lower()

            if low.startswith("package:"):
                name = line.split(":", 1)[1].strip()

            elif low.startswith("version:"):
                parts = line.split(":", 1)[1].strip().split(None, 1)
                version = parts[0]
                description = parts[1] if len(parts) > 1 else ""

            elif low.startswith("status:"):
                status = line.split(":", 1)[1].strip()

            elif "=" in line and name:
                packages.append({
                    "name": name,
                    "version": version,
                    "description": description,
                    "statuses": status.split() if status else ["Unknown"]
                })
                name = version = description = status = None

        # ---------- read header order from file ----------
        existing_headers = []
        with open(path) as f:
            for line in f:
                if line.lower().startswith("status:"):
                    for st in line.split(":", 1)[1].strip().split():
                        if st not in existing_headers:
                            existing_headers.append(st)

        # ---------- FIX: group packages by status ----------
        grouped = {}
        for pkg in packages:
            for st in pkg["statuses"]:
                grouped.setdefault(st, []).append(pkg)

        # ---------- FIX: build list in correct order ----------
        self.list = []

        for st in existing_headers:
            if st not in grouped:
                continue

            self.list.append(
                (None, "☆  %s" % st, "", "", "HEADER", "", "", "")
            )

            for pkg in grouped[st]:
                self.list.append(
                    (
                        self.unchecked_icon,
                        pkg["name"],
                        pkg["version"],
                        pkg["description"],
                        st,
                        pkg["name"],
                        pkg["version"],
                        pkg["description"],
                    )
                )

        self["menu"].setList(self.list)
        self.updateCounter()

    # ================= SELECT =================
    def toggleSelection(self):
        if self.showing_done_message:
            self.closeReportMessage()
            return

        cur = self["menu"].getCurrent()
        if not cur:
            return

        icon, name, version, description, status, *_ = cur
        if status == "HEADER":
            return

        index = self["menu"].getIndex()

        if name in self.selected_plugins:
            self.selected_plugins.remove(name)
            icon = self.unchecked_icon
        else:
            self.selected_plugins.append(name)
            icon = self.checked_icon

        self.list[index] = (
            icon, name, version, description, status, name, version, description
        )
        self["menu"].updateList(self.list)
        self.updateCounter()

    def updateCounter(self):
        self["selection_count"].setText(_("Selected: %d") % len(self.selected_plugins))

    # ================= SELECT ALL =================
    def toggleSelectAll(self):
        items = [row for row in self.list if row[4] != "HEADER"]

        if len(self.selected_plugins) < len(items):
            self.selected_plugins = [row[1] for row in items]
            for i, row in enumerate(self.list):
                if row[4] != "HEADER":
                    self.list[i] = (self.checked_icon,) + row[1:]
        else:
            self.selected_plugins = []
            for i, row in enumerate(self.list):
                if row[4] != "HEADER":
                    self.list[i] = (self.unchecked_icon,) + row[1:]

        self["menu"].updateList(self.list)
        self.updateCounter()

    # ================= INSTALL =================
    def installSelected(self):
        if not self.selected_plugins:
            self.showError(_("Nothing selected"))
            return

        self.installation_in_progress = True
        self.download_queue = list(self.selected_plugins)
        self.total_packages = len(self.download_queue)
        self.total_selected = self.total_packages
        self.success_installs = 0
        self.current_index = 0
        self.selected_plugins = []

        self.startNext()

    def startNext(self):
        if self.current_index >= self.total_packages:
            self.installation_in_progress = False
            failed_count = self.total_selected - self.success_installs
            self["item_name"].setText(
                _("Done: %d/%d installed, %d failed") % (self.success_installs, self.total_selected, failed_count)
            )
            self["download_info"].setText("")
            self["progress"].setValue(100)
            self["progress"].show()
            self.showing_done_message = True
            self.buildList()
            return

        self.current_pkg = self.download_queue[self.current_index]
        self.current_index += 1

        url = None
        for line in open_file(self.status_path()):
            if line.startswith(self.current_pkg + "="):
                url = line.split("'")[1]
                break

        if not url:
            self.failed_items.append(self.current_pkg)
            self.startNext()
            return

        self.download_url = url
        self.download_file = "/tmp/%s.sh" % self.current_pkg
        self.install_fake_progress = 0

        self["item_name"].setText(_("Preparing %s ...") % self.current_pkg)
        self["download_info"].setText("")
        self["progress"].setValue(int(((self.current_index - 1) / self.total_packages) * 100))
        self["progress"].show()

        self._downloadScript()

    # ================= DOWNLOAD =================
    def _downloadScript(self):
        cmd = "wget --progress=dot:giga -O %s --no-check-certificate %s" % (
            self.download_file, self.download_url
        )
        self.container = eConsoleAppContainer()
        self.container.dataAvail.append(self._onDownloadData)
        self.container.appClosed.append(self._onDownloadFinished)
        self.container.execute(cmd)

    def _onDownloadData(self, data):
        try:
            text = data.decode("utf-8", "ignore").strip().replace("\n", " ")
            m = re.findall(r'(\d+)%', text)
            if m:
                percent = int(m[-1])
                overall = int(
                    ((self.current_index - 1) / self.total_packages +
                     (percent / 100.0) * (0.5 / self.total_packages)) * 100
                )
                self["progress"].setValue(overall)
                self["item_name"].setText(
                    _("Downloading %s ... %d%%") % (self.current_pkg, percent)
                )
                self["download_info"].setText(text[-50:])
        except:
            pass

    def _onDownloadFinished(self, ret):
        self["item_name"].setText(_("Downloading %s ... 100%%") % self.current_pkg)
        self["download_info"].setText("Download finished")
        self.pauseTimer = eTimer()
        self.pauseTimer.callback.append(self._startInstall)
        self.pauseTimer.start(500, True)

    # ================= INSTALL SCRIPT =================
    def _startInstall(self):
        os.system("chmod 755 %s" % self.download_file)
        self.install_fake_progress = 0
        self["item_name"].setText(_("Installing %s ... 0%%") % self.current_pkg)
        self["download_info"].setText("")
        self.progressTimer.start(1000, False)

        self.container = eConsoleAppContainer()
        self.container.dataAvail.append(self._onInstallData)
        self.container.appClosed.append(self._onScriptFinished)
        self.container.execute("sh %s" % self.download_file)

    def _onInstallData(self, data):
        try:
            text = data.decode("utf-8", "ignore").strip().replace("\n", " ")
            self["download_info"].setText(text[-50:])
        except:
            pass

    def _onInstallProgress(self):
        if self.install_fake_progress < 90:
            self.install_fake_progress += 2
        elif self.install_fake_progress < 98:
            self.install_fake_progress += 0.5

        overall = int(
            ((self.current_index - 1) / self.total_packages +
             (0.5 + (self.install_fake_progress / 100.0) * 0.5) / self.total_packages) * 100
        )

        self["progress"].setValue(overall)
        self["item_name"].setText(
            _("Installing %s ... %d%%") % (self.current_pkg, int(self.install_fake_progress))
        )

    def _onScriptFinished(self, ret):
        if self.progressTimer.isActive():
            self.progressTimer.stop()

        if ret == 0:
            self.success_installs += 1
            self.installed_items.append(self.current_pkg)
        else:
            self.failed_items.append(self.current_pkg)

        if os.path.exists(self.download_file):
            os.remove(self.download_file)

        self["download_info"].setText("Script finished")

        self.pauseTimer = eTimer()
        self.pauseTimer.callback.append(self.startNext)
        self.pauseTimer.start(700, True)

    # ================= STOP INSTALLATION =================
    def stopInstallation(self):
        if not self.installation_in_progress:
            return

        if self.progressTimer.isActive():
            self.progressTimer.stop()
        if self.pauseTimer:
            self.pauseTimer.stop()

        if self.container:
            try:
                self.container.kill()
            except Exception:
                pass
            self.container = None

        for pkg in self.download_queue:
            temp_file = f"/tmp/{pkg}.sh"
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                    print(f"[Picons] Removed temporary script: {temp_file}")
                except Exception as e:
                    print(f"[Picons] Failed to remove temporary script {temp_file}: {e}")

        if hasattr(self, 'download_file') and self.download_file and os.path.exists(self.download_file):
            try:
                os.remove(self.download_file)
                print(f"[Picons] Removed current temporary script: {self.download_file}")
            except Exception as e:
                print(f"[Picons] Failed to remove current temporary script: {e}")
            self.download_file = None

        self["progress"].setValue(0)
        self["progress"].hide()
        self["item_name"].setText(_("Installation canceled"))
        self["download_info"].setText("")

        self.download_queue = []
        self.installation_in_progress = False

        self.buildList()

    # ================= DONE MESSAGE =================
    def closeReportMessage(self):
        if self.showing_done_message:
            self["item_name"].setText("")
            self["download_info"].setText("")
            self["progress"].setValue(0)
            self["progress"].hide()
            self.showing_done_message = False

    # ================= REPORT =================
    def showReport(self):
        self.session.open(InstallationReport, self.installed_items, self.failed_items)

    # ================= ERROR =================
    def showError(self, txt):
        self.session.open(MessageBox, txt, MessageBox.TYPE_ERROR)

    # ================= CLOSE =================
    def close(self):
        if self.showing_done_message:
            self.closeReportMessage()
            return
        if self.installation_in_progress:
            self.showError(_("Cannot exit during installation"))
            return
        Screen.close(self)

    # ================= GITHUB UPDATE =================
    def update_extensions_from_github(self):
        try:
            response = requests.get(EXTENSIONS_URL, timeout=10)
            if response.status_code != 200:
                print(f"[Picons] Failed to fetch extensions: {response.status_code}")
                return False

            new_hash = hashlib.md5(response.content).hexdigest()
            local_hash = None
            if os.path.exists(LOCAL_EXTENSIONS):
                with open(LOCAL_EXTENSIONS, "rb") as f:
                    local_hash = hashlib.md5(f.read()).hexdigest()

            if local_hash == new_hash:
                print("[Picons] Extensions already up-to-date")
                return False

            with open(LOCAL_EXTENSIONS, "wb") as f:
                f.write(response.content)

            print("[Picons] Extensions file updated from GitHub")

            # ===== AUTO REFRESH MENU =====
            self.buildList()
            return True
        except Exception as e:
            print("[Picons] update_extensions_from_github error:", e)
            return False

