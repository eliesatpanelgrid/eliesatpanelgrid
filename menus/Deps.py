# -*- coding: utf-8 -*-
import os
import sys
import subprocess
import threading
import time
from Screens.Screen import Screen
from Components.Label import Label
from Components.ScrollLabel import ScrollLabel
from Components.ActionMap import ActionMap
from enigma import eTimer, getDesktop

from Plugins.Extensions.ElieSatPanelGrid.menus.Helpers import (
    get_local_ip,
    check_internet,
    get_image_name,
    get_python_version,
    get_storage_info,
    get_ram_info,
)
from Plugins.Extensions.ElieSatPanelGrid.__init__ import Version


class Deps(Screen):

    lib_special = [
        "libavcodec60","libavcodec61","libavcodec62","libavcodec63",
        "libavformat60","libavformat61","libavformat62","libavformat63",
        "libpython3.9-1.0","libpython3.10-1.0","libpython3.11-1.0",
        "libpython3.12-1.0","libpython3.13-1.0","libpython3.14-1.0"
    ]

    def __init__(self, session):
        # ---------------- SKIN LOADER ----------------
        screen_width = getDesktop(0).size().width()
        if screen_width >= 1920:
            skin_path = "/usr/lib/enigma2/python/Plugins/Extensions/ElieSatPanelGrid/assets/skin/deps_fhd.xml"
        else:
            skin_path = "/usr/lib/enigma2/python/Plugins/Extensions/ElieSatPanelGrid/assets/skin/deps_hd.xml"

        if os.path.exists(skin_path):
            with open(skin_path, "r") as f:
                self.skin = f.read()
        else:
            self.skin = """<screen name="Deps" position="center,center" size="1280,720">
                <eLabel text="Skin missing!" position="center,center" size="400,40"
                    font="Regular;24" halign="center" valign="center"/>
            </screen>"""

        Screen.__init__(self, session)
        self.setTitle("Smart Dependency Checker")

        # ---------------- UI ----------------
        self["left_bar"] = Label("\n".join(list("Version " + Version)))
        self["right_bar"] = Label("\n".join(list("By ElieSat")))

        self["image_name"] = Label("Image: " + get_image_name())
        self["local_ip"] = Label("IP: " + get_local_ip())
        self["StorageInfo"] = Label(get_storage_info())
        self["RAMInfo"] = Label(get_ram_info())
        self["python_ver"] = Label("Python: " + get_python_version())
        self["net_status"] = Label("Net: " + check_internet())

        self["deps_text"] = ScrollLabel("")
        self["dep_status"] = Label("Scanning feeds...")
        self["page_info"] = Label("")

        # Button labels
        self["red"] = Label(_("Stop"))
        self["green"] = Label(_("Install available"))
        self["yellow"] = Label(_("Show not available"))
        self["blue"] = Label(_("Rescan deps"))

        # ---------------- NEW LABELS ----------------
        self["current_install"] = Label("")  # orange label for current installing package
        self["stop_msg"] = Label("")          # temporary stop message (5 sec)

        # ---------------- ACTIONS ----------------
        self["actions"] = ActionMap(
            ["OkCancelActions", "DirectionActions", "ColorActions"],
            {
                "cancel": self.handle_exit,
                "red": self.stop_installation,
                "green": self.install_available,
                "yellow": self.show_not_available,
                "blue": self.rescan_deps,
                "up": self.pageUp,
                "down": self.pageDown,
                "left": self.pageUp,
                "right": self.pageDown,
            },
            -1
        )

        # ---------------- DATA ----------------
        self.pyver = sys.version_info[0]
        self.deps = []
        self.feed_list = set()
        self.index = 0
        self.output_lines = []

        self.count_installed = 0
        self.count_available = 0
        self.count_not_available = 0

        # ---------------- COLORS ----------------
        self.C_GREEN = "\\c0000FF00"
        self.C_YELLOW = "\\c00FFD700"  # Name color
        self.C_ORANGE = "\\c00FFA500"  # Available but not installed
        self.C_RED = "\\c00FF0000"
        self.C_WHITE = "\\c00FFFFFF"

        # ---------------- TIMER ----------------
        self.timer = eTimer()
        self.timer.callback.append(self.scan_next)

        # ---------------- INSTALL THREAD ----------------
        self.install_thread = None
        self.stop_flag = False

        # ---------------- FILTER ----------------
        self.current_filter = "all"

        # ---------------- INIT ----------------
        self.rescan_deps()

    # ==========================================================
    # EXIT HANDLER
    # ==========================================================
    def handle_exit(self):
        if self.current_filter != "all":
            self.show_all()
        else:
            self.close()

    # ==========================================================
    # SHOW FILTERS
    # ==========================================================
    def show_not_available(self):
        self.current_filter = "not_available"
        filtered = [line for line in self.output_lines if self.C_RED in line]
        # Add missing lib_special packages
        for lib in self.lib_special:
            if lib not in self.feed_list:
                filtered.append(f"{self.C_RED}● {lib}{self.C_WHITE}")
        self["deps_text"].setText("\n".join(filtered))

    def show_all(self):
        self.current_filter = "all"
        self["deps_text"].setText("\n".join(self.output_lines))

    # ==========================================================
    # RESCAN DEPS
    # ==========================================================
    def rescan_deps(self):
        self.output_lines = []
        self.count_installed = 0
        self.count_available = 0
        self.count_not_available = 0
        self.index = 0
        self.current_filter = "all"

        self.load_deps()
        self.load_feed()
        self["deps_text"].setText("Scanning dependencies...\n")
        self.update_status()
        self.timer.start(20, True)

    # ==========================================================
    # INSTALL AVAILABLE DEPS
    # ==========================================================
    def install_available(self):
        if self.install_thread and self.install_thread.is_alive():
            return
        self.stop_flag = False
        self.install_thread = threading.Thread(target=self._install_worker)
        self.install_thread.start()

    def stop_installation(self):
        self.stop_flag = True
        if not self.install_thread or not self.install_thread.is_alive():
            self["stop_msg"].setText("\\c00FFA500Installation stopped\\c00FFFFFF")
            threading.Timer(5, lambda: self["stop_msg"].setText("")).start()

    def _install_worker(self):
        for i, pkg in enumerate(self.deps):
            if self.stop_flag:
                self["stop_msg"].setText("\\c00FFA500Installation stopped\\c00FFFFFF")
                threading.Timer(5, lambda: self["stop_msg"].setText("")).start()
                break

            if pkg in self.lib_special and pkg not in self.feed_list:
                continue

            if pkg in self.feed_list:
                try:
                    out = subprocess.check_output(
                        ["opkg", "status", pkg],
                        universal_newlines=True,
                        stderr=subprocess.DEVNULL
                    )
                    if "install ok installed" in out:
                        continue

                    self["current_install"].setText(f"\\c00FFA500Installing: {pkg}\\c00FFFFFF")
                    subprocess.call(["opkg", "install", pkg])
                    self.count_installed += 1
                    self.count_available -= 1

                    for idx, line in enumerate(self.output_lines):
                        if pkg in line:
                            self.output_lines[idx] = line.replace(self.C_ORANGE, self.C_GREEN)
                            break

                    self.update_status()
                    self["deps_text"].setText("\n".join(self.output_lines))
                    time.sleep(0.2)

                except:
                    pass

        self["current_install"].setText("")

    # ==========================================================
    # FULL DEP LIST
    # ==========================================================
    def load_deps(self):
        base = [
            "wget","alsa-conf","alsa-state","alsa-plugins","alsa-utils","alsa-utils-aplay",
            "astra-sm","bzip2","binutils","curl","duktape","dvbsnoop","enigma2",
            "enigma2-plugin-extensions-e2iplayer-deps","exteplayer3","ffmpeg","gstplayer",
            "perl-module-io-zlib","libasound2","libusb-1.0-0","libxml2","libxslt",
            "libc6","libgcc1","libstdc++6","openvpn","rtmpdump","transmission",
            "transmission-client","enigma2-plugin-systemplugins-serviceapp","unrar",
            "zip","xz","zstd","gstreamer1.0-plugins-good","gstreamer1.0-plugins-base",
            "gstreamer1.0-plugins-bad","gstreamer1.0-plugins-ugly"
        ]
        py3 = [
            "python3-core","python3-twisted-web","python3-pillow","python3-json",
            "livestreamersrv","python3-backports-lzma","python3-beautifulsoup4",
            "python3-certifi","python3-chardet","python3-cfscrape","python3-codecs",
            "python3-compression","python3-cryptography","python3-dateutil",
            "python3-difflib","python3-fuzzywuzzy","python3-future","python3-futures3",
            "python3-html","python3-image","python3-js2py","python3-levenshtein",
            "python3-lxml","python3-mmap","python3-misc","python3-mechanize",
            "python3-multiprocessing","python3-netclient","python3-netserver",
            "python3-pkgutil","python3-pycurl","python3-pycryptodome","python3-pydoc",
            "python3-pyexecjs","python3-pyopenssl","python3-rarfile","python3-pysocks",
            "python3-requests","python3-requests-cache","python3-shell",
            "python3-sqlite3","python3-six","python3-treq","python3-transmission-rpc",
            "python3-unixadmin","python3-urllib3","python3-xmlrpc","python3-zoneinfo",
        ]
        py2 = [
            "f4mdump","hlsdl","kodi-addon-pvr-iptvsimple","python-lzma",
            "python-argparse","python-beautifulsoup4","python-certifi",
            "python-chardet","python-codecs","python-compression","python-core",
            "python-pycurl","python-cryptography","python-difflib","python-futures",
            "python-html","python-image","python-imaging","python-json",
            "python-js2py","python-lxml","python-mechanize","python-multiprocessing",
            "python-misc","python-mmap","python-ndg-httpsclient","python-netclient",
            "python-pycrypto","python-pyexecjs","python-pydoc","python-pyopenssl",
            "python-requests","python-robotparser","python-six","python-shell",
            "python-sqlite3","python-pysocks","python-subprocess",
            "python-twisted-web","python-unixadmin","python-urllib3","python-xmlrpc",
        ]
        self.deps = base + (py3 if self.pyver == 3 else py2) + self.lib_special

    # ==========================================================
    # LOAD FEED
    # ==========================================================
    def load_feed(self):
        try:
            out = subprocess.check_output(["opkg", "list"], universal_newlines=True)
            self.feed_list = set(line.split()[0] for line in out.splitlines())
        except:
            self.feed_list = set()

    # ==========================================================
    # SCAN NEXT
    # ==========================================================
    def scan_next(self):
        if self.index >= len(self.deps):
            self.update_status(final=True)
            return

        pkg = self.deps[self.index]

        if pkg in self.feed_list:
            try:
                out = subprocess.check_output(
                    ["opkg", "status", pkg],
                    universal_newlines=True,
                    stderr=subprocess.DEVNULL
                )
                if "install ok installed" in out:
                    dot_color = self.C_GREEN
                    self.count_installed += 1
                else:
                    dot_color = self.C_ORANGE
                    self.count_available += 1
            except:
                dot_color = self.C_ORANGE
                self.count_available += 1
        else:
            dot_color = self.C_RED
            self.count_not_available += 1

        # Print lib_special only if available or installed, skip main screen if not available
        if pkg in self.lib_special:
            if pkg not in self.feed_list and dot_color == self.C_RED:
                line_to_add = None
            else:
                line_to_add = f"{dot_color}● {self.C_YELLOW}{pkg}{self.C_WHITE}"
        else:
            line_to_add = f"{dot_color}● {self.C_YELLOW}{pkg}{self.C_WHITE}"

        if line_to_add:
            self.output_lines.append(line_to_add)

        if self.current_filter == "not_available" and dot_color != self.C_RED:
            pass
        else:
            self["deps_text"].setText("\n".join(self.output_lines))

        self.update_status()
        self.index += 1
        self.timer.start(20, True)

    # ==========================================================
    # STATUS
    # ==========================================================
    def update_status(self, final=False):
        total = len(self.deps)
        text = (
            f"Total: {total} | "
            f"Installed: {self.count_installed} | "
            f"Available: {self.count_available} | "
            f"Not Available: {self.count_not_available}"
        )
        if final:
            text = "Scan complete | " + text
        self["dep_status"].setText(text)

    # ==========================================================
    # NAV
    # ==========================================================
    def pageUp(self):
        try:
            self["deps_text"].pageUp()
        except:
            pass

    def pageDown(self):
        try:
            self["deps_text"].pageDown()
        except:
            pass
