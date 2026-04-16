# -*- coding: utf-8 -*-
import os
from os import chmod, system as os_system
from os.path import exists, join

from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from enigma import eConsoleAppContainer, getDesktop, eTimer

from Plugins.Extensions.ElieSatPanelGrid.menus.Helpers import (
    get_local_ip,
    check_internet,
    get_image_name,
    get_python_version,
    get_storage_info,
    get_ram_info,
)
from Plugins.Extensions.ElieSatPanelGrid.__init__ import Version
from Plugins.Extensions.ElieSatPanelGrid.menus.Console import Console

scriptpath = "/usr/script/"
if not os.path.exists(scriptpath):
    os.makedirs(scriptpath, exist_ok=True)


class Scripts(Screen):
    def __init__(self, session):
        width, height = getDesktop(0).size().width(), getDesktop(0).size().height()

        skin_file = (
            "/usr/lib/enigma2/python/Plugins/Extensions/ElieSatPanelGrid/assets/skin/scripts_fhd.xml"
            if width >= 1920
            else "/usr/lib/enigma2/python/Plugins/Extensions/ElieSatPanelGrid/assets/skin/scripts_hd.xml"
        )

        with open(skin_file, "r") as f:
            self.skin = f.read()

        Screen.__init__(self, session)
        self.session = session

        self.items_per_page = 10
        self.current_page = 1
        self.total_pages = 1

        self.setTitle(_("Scripts Manager"))

        self["left_bar"] = Label("\n".join(list("Version " + Version)))
        self["right_bar"] = Label("\n".join(list("By ElieSat")))

        self["image_name"] = Label("Image: " + get_image_name())
        self["local_ip"] = Label("IP: " + get_local_ip())
        self["StorageInfo"] = Label(get_storage_info())
        self["RAMInfo"] = Label(get_ram_info())
        self["python_ver"] = Label("Python: " + get_python_version())
        self["net_status"] = Label("Net: " + check_internet())

        self["red"] = Label(_("Remove List"))
        self["yellow"] = Label("-")
        self["blue"] = Label("-")
        self["green"] = Label(_("Update List"))

        self["script_name"] = Label("")
        self["page_info"] = Label("Page 1/1")
        self["counter"] = Label("")

        self["list"] = MenuList([])
        self["list"].onSelectionChanged.append(self.updateSelection)

        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions"],
            {
                "ok": self.run,
                "green": self.update,
                "yellow": self.noop,
                "blue": self.noop,
                "red": self.remove,
                "up": self.moveUp,
                "down": self.moveDown,
                "left": self.pageLeft,
                "right": self.pageRight,
                "cancel": self.close,
            },
            -1,
        )

        self.flickerTimer = eTimer()
        try:
            self.flickerTimer.callback.append(self._flicker)
        except:
            self.flickerTimer_conn = self.flickerTimer.timeout.connect(self._flicker)

        self.msgTimer = eTimer()
        try:
            self.msgTimer.callback.append(self._clearMessage)
        except:
            self.msgTimer_conn = self.msgTimer.timeout.connect(self._clearMessage)

        self._flicker_state = False
        self._flicker_visible = False
        self._message_mode = False

        self.loadScripts()

    def noop(self):
        return

    def _showMessage(self, text, duration=2):
        self._stopFlicker()
        self._message_mode = True
        self["script_name"].setText(text)
        self.msgTimer.start(duration * 1000)

    def _clearMessage(self):
        self.msgTimer.stop()
        self._message_mode = False
        self.updateSelection()

    def _startFlicker(self):
        self._flicker_state = True
        self._flicker_visible = True
        self.flickerTimer.start(500)

    def _stopFlicker(self):
        self.flickerTimer.stop()
        self._flicker_state = False
        self._flicker_visible = False

    def _flicker(self):
        if not self._flicker_state:
            return

        if self._flicker_visible:
            self["script_name"].setText("")
        else:
            self["script_name"].setText("Updating scripts list please wait ...")

        self._flicker_visible = not self._flicker_visible

    def loadScripts(self):
        self.scripts = []
        self.display_list = []

        if os.path.exists(scriptpath):
            self.scripts = [
                x for x in os.listdir(scriptpath)
                if x.endswith(".sh") or x.endswith(".py")
            ]

        self.scripts.sort()

        for script in self.scripts:
            self.display_list.append("• %s" % script)

        self["list"].setList(self.display_list)
        self.updateSelection()

    def updateSelection(self):
        if self._message_mode:
            return

        idx = self.getCurrentIndex()
        total = len(self.scripts)

        if self.scripts and idx < total:
            self["script_name"].setText("• %s" % self.scripts[idx])
        else:
            self["script_name"].setText(_("No scripts found"))

        self.total_pages = max(1, (total + self.items_per_page - 1) // self.items_per_page)
        self.current_page = (idx // self.items_per_page) + 1 if total else 1

        self["page_info"].setText("Page %d/%d" % (self.current_page, self.total_pages))

        # FIXED COUNTER LOGIC (page-based, not item-based)
        if total > 0:
            start_index = (self.current_page - 1) * self.items_per_page
            end_index = min(start_index + self.items_per_page, total)
            showing = end_index
            self["counter"].setText("(showing %d/%d)" % (showing, total))
        else:
            self["counter"].setText("(showing 0/0)")

    def getCurrentIndex(self):
        try:
            return self["list"].getSelectedIndex()
        except:
            current = self["list"].getCurrent()
            if current is not None:
                return self["list"].index(current)
            return 0

    def update(self):
        self._startFlicker()

        cmd = (
            "wget --no-check-certificate "
            "https://raw.githubusercontent.com/eliesat/scripts/main/installer.sh "
            "-qO - | /bin/sh"
        )

        self.container_update = eConsoleAppContainer()

        try:
            self.container_update.appClosed.append(self._updateFinished)
        except:
            self.container_update.appClosed_conn = self.container_update.appClosed.connect(self._updateFinished)

        self.container_update.execute(cmd)

    def _updateFinished(self, retval):
        self._stopFlicker()
        self.loadScripts()

        if retval == 0:
            self._showMessage("Scripts updated successfully!")
        else:
            self._showMessage("Update failed!")

    def moveUp(self):
        self["list"].moveUp()
        self.updateSelection()

    def moveDown(self):
        self["list"].moveDown()
        self.updateSelection()

    def pageLeft(self):
        idx = max(0, self.getCurrentIndex() - self.items_per_page)
        self["list"].setIndex(idx)
        self.updateSelection()

    def pageRight(self):
        idx = min(len(self.scripts) - 1, self.getCurrentIndex() + self.items_per_page)
        self["list"].setIndex(idx)
        self.updateSelection()

    def run(self):
        idx = self.getCurrentIndex()
        script = self.scripts[idx] if self.scripts else None

        if not script:
            self._showMessage("No script selected!")
            return

        full_path = join(scriptpath, script)

        if not exists(full_path):
            self._showMessage("Script not found!")
            return

        if full_path.endswith(".sh"):
            chmod(full_path, 0o755)
            cmd = full_path
        else:
            cmd = "python " + full_path

        self.session.open(Console, _("Executing: %s") % script, [cmd])

    def remove(self):
        self._startFlicker()

        self.container_remove = eConsoleAppContainer()

        try:
            self.container_remove.appClosed.append(self._removeFinished)
        except:
            self.container_remove.appClosed_conn = self.container_remove.appClosed.connect(self._removeFinished)

        cmd = "find /usr/script -type f -exec rm -f {} \\;"
        self.container_remove.execute(cmd)

    def _removeFinished(self, retval):
        self._stopFlicker()
        self.loadScripts()

        if retval == 0:
            self._showMessage("Scripts successfully removed!")
        else:
            self._showMessage("Remove failed!")

    def doClose(self):
        try:
            if hasattr(self, "container"):
                self.container.dataAvail.clear()
                self.container.appClosed.clear()
        except:
            pass

        Screen.doClose(self)
