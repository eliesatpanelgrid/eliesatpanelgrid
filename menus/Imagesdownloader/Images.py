# -*- coding: utf-8 -*-
from __future__ import absolute_import
import os
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.InputBox import InputBox
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.ProgressBar import ProgressBar
from Components.MenuList import MenuList
from Components.Pixmap import Pixmap
from enigma import getDesktop

from Plugins.Extensions.ElieSatPanelGrid.menus.Helpers import (
    get_local_ip,
    check_internet,
    get_image_name,
    get_python_version,
    get_storage_info,
    get_ram_info,
    is_device_unlocked,
)
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
        print("[ElieSatPanel] Failed to load skin in Images: %s" % e)
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
        self.target_dir = None

        # UI Components
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

        self["red"] = Label("Delete")
        self["green"] = Label("Rename")
        self["yellow"] = Label("")
        self["blue"] = Label("")

        # Standard MenuList used identically to Scripts class
        self["list"] = MenuList([])
        self["progress"] = ProgressBar()

        # Navigation ActionMap
        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions"],
            {
                "up": self.moveUp,
                "down": self.moveDown,
                "red": self.deleteImage,
                "green": self.renameImage,
                "cancel": self.close,
                "back": self.close,
            },
            -1,
        )

        self["list"].onSelectionChanged.append(self.updateSelection)
        self.loadLocalImages()

    def getHostname(self):
        try:
            with open("/etc/hostname", "r") as f:
                return f.readline().strip()
        except Exception:
            return os.uname().nodename.strip()

    def _safeLoadDeviceIcon(self):
        try:
            base_path = "/usr/lib/enigma2/python/Plugins/Extensions/ElieSatPanelGrid/assets/boxicons/"
            icon_path = os.path.join(base_path, "%s.png" % self.hostname)
            if not os.path.exists(icon_path):
                icon_path = os.path.join(base_path, "default.png")
            if os.path.exists(icon_path):
                self["device_icon"].instance.setPixmapFromFile(icon_path)
        except Exception as e:
            print("[ElieSatPanel] Error loading icon: %s" % e)

    def loadLocalImages(self):
        """Scans media paths in priority (hdd -> usb -> mmc) for /images/*.zip files."""
        search_paths = [
            "/media/hdd/images",
            "/media/usb/images",
            "/media/mmc/images",
        ]

        self.images_files = []
        self.display_list = []
        self.target_dir = None

        for path in search_paths:
            if os.path.exists(path) and os.path.isdir(path):
                try:
                    zip_files = [f for f in os.listdir(path) if f.lower().endswith(".zip")]
                    if zip_files:
                        self.target_dir = path
                        self.images_files = sorted(zip_files)
                        break
                except Exception as e:
                    print("[ElieSatPanel] Error reading directory %s: %s" % (path, e))

        if self.images_files:
            for img in self.images_files:
                self.display_list.append("• %s" % img)
            self["download_info"].setText("Found %d image(s) in %s" % (len(self.images_files), self.target_dir))
        else:
            self.display_list.append("• No .zip images found in hdd/usb/mmc images folder")
            self["download_info"].setText("No local images found.")

        # Populate MenuList using standard list of formatted strings
        self["list"].setList(self.display_list)
        self.updateSelection()

    def getCurrentIndex(self):
        try:
            return self["list"].getSelectedIndex()
        except Exception:
            current = self["list"].getCurrent()
            if current is not None:
                return self["list"].index(current)
            return 0

    def _get_formatted_file_size(self, file_path):
        """Calculates and formats file size into human-readable string."""
        try:
            size_bytes = os.path.getsize(file_path)
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size_bytes < 1024.0:
                    if unit in ['B', 'KB']:
                        return "%d %s" % (int(size_bytes), unit)
                    return "%.1f %s" % (size_bytes, unit)
                size_bytes /= 1024.0
            return "%.1f GB" % size_bytes
        except Exception:
            return "Unknown size"

    def updateSelection(self):
        idx = self.getCurrentIndex()
        total = len(self.images_files)

        if self.images_files and idx < total and self.target_dir:
            file_name = self.images_files[idx]
            file_path = os.path.join(self.target_dir, file_name)
            file_size_str = self._get_formatted_file_size(file_path)
            self["item_name"].setText("• %s (%s)" % (file_name, file_size_str))
        else:
            self["item_name"].setText("No images selected")

    def moveUp(self):
        self["list"].moveUp()
        self.updateSelection()

    def moveDown(self):
        self["list"].moveDown()
        self.updateSelection()

    def deleteImage(self):
        """Handles deleting the currently selected image file."""
        idx = self.getCurrentIndex()
        if not self.images_files or idx >= len(self.images_files) or not self.target_dir:
            return

        selected_file = self.images_files[idx]
        file_path = os.path.join(self.target_dir, selected_file)

        self.session.openWithCallback(
            lambda result: self._confirmDelete(result, file_path),
            MessageBox,
            "Are you sure you want to delete:\n%s?" % selected_file,
            MessageBox.TYPE_YESNO,
        )

    def _confirmDelete(self, result, file_path):
        if result:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                print("[ElieSatPanel] Failed to delete image: %s" % e)
            self.loadLocalImages()

    def renameImage(self):
        """Opens an InputBox dialog to rename the currently selected image file."""
        idx = self.getCurrentIndex()
        if not self.images_files or idx >= len(self.images_files) or not self.target_dir:
            return

        current_file = self.images_files[idx]
        name_without_ext = current_file[:-4] if current_file.lower().endswith(".zip") else current_file

        self.session.openWithCallback(
            lambda new_name: self._confirmRename(new_name, current_file),
            InputBox,
            title="Enter new name for image:",
            text=name_without_ext,
        )

    def _confirmRename(self, new_name, old_filename):
        if not new_name:
            return

        new_name = new_name.strip()
        if not new_name.lower().endswith(".zip"):
            new_name += ".zip"

        if new_name == old_filename:
            return

        old_path = os.path.join(self.target_dir, old_filename)
        new_path = os.path.join(self.target_dir, new_name)

        try:
            if os.path.exists(old_path):
                os.rename(old_path, new_path)
        except Exception as e:
            print("[ElieSatPanel] Failed to rename image: %s" % e)

        self.loadLocalImages()