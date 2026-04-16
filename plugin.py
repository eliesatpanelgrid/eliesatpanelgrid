# -*- coding: utf-8 -*-
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.Pixmap import Pixmap
from Components.Label import Label
from Tools.LoadPixmap import LoadPixmap
from enigma import eTimer, getDesktop
import os
import re
import tarfile
import shutil
import requests

PLUGIN_PATH = "/usr/lib/enigma2/python/Plugins/Extensions/ElieSatPanelGrid"

# ---------------- FHD SKIN ----------------
SKIN_FHD_XML = """
<screen name="SplashScreenFHD" position="575,280" size="768,512" flags="wfNoBorder">

    <widget name="bg_icon" position="0,0" size="768,512" backgroundColor="#000000"/>

    <widget name="splash_text" position="35,10" size="700,50"
        halign="center" valign="center"
        font="Bold;40" foregroundColor="#FFFFFF" transparent="1"/>

    <widget name="icon" position="center,center" size="768,512" transparent="1"/>

    <widget name="version_label" position="428,center+70" size="300,50"
        font="Bold;30" halign="center" valign="center"
        foregroundColor="#FFFFFF"/>

    <widget name="wait_text" position="center,360" size="700,50"
        font="Bold;30" halign="center" valign="center"
        foregroundColor="#E6BE3A" zPosition="2"/>

    <widget name="upgrade_text" position="center,420" size="700,50"
        font="Bold;30" halign="center" valign="center"
        foregroundColor="#E6BE3A" zPosition="2"/>

</screen>
"""

# ---------------- HD SKIN ----------------
SKIN_HD_XML = """
<screen name="SplashScreenHD" position="center,center" size="640,360" flags="wfNoBorder">

    <widget name="bg_icon" position="0,0" size="640,360" backgroundColor="#000000"/>

    <widget name="splash_text" position="20,10" size="600,40"
        halign="center" valign="center"
        font="Bold;28" foregroundColor="#FFFFFF" transparent="1"/>

    <widget name="icon" position="center,center" size="640,360" transparent="1"/>

    <widget name="version_label" position="340,240" size="260,40"
        font="Bold;22" halign="center" valign="center"
        foregroundColor="#FFFFFF"/>

    <widget name="wait_text" position="center,280" size="600,40"
        font="Bold;22" halign="center" valign="center"
        foregroundColor="#E6BE3A" zPosition="2"/>

    <widget name="upgrade_text" position="center,320" size="600,40"
        font="Bold;22" halign="center" valign="center"
        foregroundColor="#E6BE3A" zPosition="2"/>

</screen>
"""

def detect_skin_type():
    try:
        return "FHD" if getDesktop(0).size().width() >= 1920 else "HD"
    except:
        return "HD"


class SplashScreen(Screen):

    REPO_OWNER = "eliesatpanelgrid"
    REPO_NAME = "eliesatpanelgrid"
    FOLDER_PATH = "assets/data"
    BRANCH = "main"
    DEST_FOLDER = os.path.join(PLUGIN_PATH, "assets/data")

    UPDATE_URL = "https://github.com/eliesatpanelgrid/eliesatpanelgrid/archive/main.tar.gz"
    PACKAGE = "/tmp/eliesatpanelgrid-main.tar.gz"

    def __init__(self, session):

        self.skin_type = detect_skin_type()
        self.skin = SKIN_HD_XML if self.skin_type == "HD" else SKIN_FHD_XML
        Screen.__init__(self, session)

        self["bg_icon"] = Pixmap()
        self["icon"] = Pixmap()
        self["splash_text"] = Label("○ Powering Your E2 Experience ○")
        self["version_label"] = Label("Version: %s" % self.read_version())
        self["wait_text"] = Label("Please wait ...")
        self["upgrade_text"] = Label()

        self["wait_text"].show()
        self["upgrade_text"].hide()

        self.onLayoutFinish.append(self.load_icon)
        self.onLayoutFinish.append(self.start_version_check)

    def load_icon(self):
        icon = "splash_icon_hd.png" if self.skin_type == "HD" else "splash_icon.png"
        path = os.path.join(PLUGIN_PATH, "assets/background", icon)
        if os.path.exists(path):
            pixmap = LoadPixmap(path)
            if pixmap:
                self["icon"].instance.setPixmap(pixmap)

    def read_version(self):
        try:
            with open(os.path.join(PLUGIN_PATH, "__init__.py")) as f:
                m = re.search(r"[Vv]ersion\s*=\s*['\"](.+?)['\"]", f.read())
                return m.group(1) if m else "Unknown"
        except:
            return "Unknown"

    def start_version_check(self):
        self.version_timer = eTimer()
        self.version_timer.callback.append(self.check_version)
        self.version_timer.start(200, True)

    def check_version(self):

        local = self.read_version()
        url = "https://raw.githubusercontent.com/%s/%s/%s/__init__.py" % (
            self.REPO_OWNER, self.REPO_NAME, self.BRANCH)

        try:
            content = requests.get(url, timeout=5).text
            m = re.search(r"[Vv]ersion\s*=\s*['\"](.+?)['\"]", content)
            remote = m.group(1) if m else None

            if remote and remote != local:
                self.session.openWithCallback(
                    self.update_answer,
                    MessageBox,
                    "New version %s available. Upgrade?" % remote,
                    MessageBox.TYPE_YESNO
                )
            else:
                self.start_github_process()

        except:
            self.start_github_process()

    def update_answer(self, answer):
        if not answer:
            self.start_github_process()
            return

        self.phase = "download"
        self.downloaded = 0
        self.install_index = 0
        self.last_percent = -1

        # STATIC ONLY
        self["wait_text"].show()
        self["upgrade_text"].show()
        self["upgrade_text"].setText("Please wait ...")

        self.download_update()

    def download_update(self):

        try:
            self.req = requests.get(self.UPDATE_URL, stream=True, timeout=10)
            self.total_size = int(self.req.headers.get("content-length") or 0)

            self.update_file = open(self.PACKAGE, "wb")
            self.chunk_iter = self.req.iter_content(chunk_size=32768)

            self.downloaded = 0
            self.last_percent = -1

            self.upgrade_timer = eTimer()
            self.upgrade_timer.callback.append(self.download_and_install_tick)
            self.upgrade_timer.start(50, False)

        except:
            self.start_github_process()

    def download_and_install_tick(self):

        if self.phase == "download":

            try:
                chunk = next(self.chunk_iter)
                if not chunk:
                    self.upgrade_timer.start(50, False)
                    return

                self.update_file.write(chunk)
                self.downloaded += len(chunk)

                if self.total_size > 0:
                    percent = int((self.downloaded * 100) / self.total_size)
                    text = "Downloading... %d%%" % percent
                else:
                    percent = int(self.downloaded / 1024)
                    text = "Downloading... %d KB" % percent

                if percent != self.last_percent:
                    self.last_percent = percent
                    self["upgrade_text"].setText(text)
                    self["upgrade_text"].instance.invalidate()

            except StopIteration:

                self.update_file.close()

                self.phase = "wait_upgrade"

                # KEEP STATIC TEXT ONLY
                self["upgrade_text"].setText("Please wait ...")

                self.wait_timer = eTimer()
                self.wait_timer.callback.append(self.start_install_phase)
                self.wait_timer.start(2000, True)

        elif self.phase == "install":

            if self.install_index < self.total_members:

                member = self.members[self.install_index]
                self.tar.extract(member, "/tmp")
                self.install_index += 1

                percent = int((self.install_index * 100) / self.total_members)
                self["upgrade_text"].setText("Upgrading... %d%%" % percent)

            else:

                self.tar.close()

                try:
                    os.remove(self.PACKAGE)
                    if os.path.exists(PLUGIN_PATH):
                        shutil.rmtree(PLUGIN_PATH)
                    shutil.move("/tmp/eliesatpanelgrid-main", PLUGIN_PATH)
                except:
                    pass

                self.session.nav.stopService()
                os.system("killall -9 enigma2")
                return

        self.upgrade_timer.start(50, False)

    def start_install_phase(self):

        self.phase = "install"

        # STILL STATIC
        self["upgrade_text"].setText("Please wait ...")

        self.tar = tarfile.open(self.PACKAGE, "r:gz")
        self.members = self.tar.getmembers()
        self.total_members = len(self.members)
        self.install_index = 0

        self.upgrade_timer.start(50, False)

    def start_github_process(self):

        self["wait_text"].show()
        self["upgrade_text"].hide()
        self["wait_text"].setText("Please wait ...")

        os.makedirs(self.DEST_FOLDER, exist_ok=True)

        api = "https://api.github.com/repos/%s/%s/contents/%s?ref=%s" % (
            self.REPO_OWNER,
            self.REPO_NAME,
            self.FOLDER_PATH,
            self.BRANCH,
        )

        try:
            files = requests.get(api, timeout=5).json()
            if not isinstance(files, list):
                raise Exception("Invalid API")

        except:
            self.open_panel()
            return

        self.files_to_download = files
        self.current_file_index = 0

        self.download_timer = eTimer()
        self.download_timer.callback.append(self.download_next_file)
        self.download_timer.start(50, True)

    def download_next_file(self):

        if self.current_file_index >= len(self.files_to_download):
            self.open_panel()
            return

        info = self.files_to_download[self.current_file_index]
        url = info.get("download_url")

        if url:
            try:
                filename = os.path.basename(url)
                dest = os.path.join(self.DEST_FOLDER, filename)

                if not os.path.exists(dest):
                    open(dest, "wb").write(requests.get(url, timeout=5).content)
            except:
                pass

        self.current_file_index += 1
        self.download_timer.start(50, True)

    def open_panel(self):
        try:
            from Plugins.Extensions.ElieSatPanelGrid.main import EliesatPanel
            self.session.open(EliesatPanel)
        except:
            pass

        self.close()


def main(session, **kwargs):
    session.open(SplashScreen)


def menuHook(menuid, **kwargs):
    if menuid == "mainmenu":
        return [("ElieSatPanelGrid", main, "eliesat_panel_grid", 46)]
    return []


def Plugins(**kwargs):
    return [
        PluginDescriptor(name="ElieSatPanelGrid", description="Enigma2 Panel",
                         where=PluginDescriptor.WHERE_PLUGINMENU,
                         icon="assets/icon/panel_logo.png", fnc=main),

        PluginDescriptor(name="ElieSatPanelGrid",
                         where=PluginDescriptor.WHERE_MENU,
                         fnc=menuHook),

        PluginDescriptor(name="ElieSatPanelGrid",
                         where=PluginDescriptor.WHERE_EXTENSIONSMENU,
                         fnc=main),
    ]
