# -*- coding: utf-8 -*-
from __future__ import absolute_import
from Plugins.Extensions.ElieSatPanelGrid.menus.Helpers import (
    get_local_ip,
    check_internet,
    get_image_name,
    get_python_version,
    get_storage_info,
    get_ram_info,
    is_device_unlocked
)
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.ProgressBar import ProgressBar
from Components.ChoiceList import ChoiceEntryComponent, ChoiceList
from Components.Pixmap import Pixmap
from enigma import eTimer, getDesktop
import requests
import os
import re
from Plugins.Extensions.ElieSatPanelGrid.__init__ import Version

USER_AGENT = {'User-agent': 'Enigma2-FlashOnline-Style/1.0'}

FEEDS = {
    "Novaler": "https://novaler.com/downloads/enigma2/{box}",
    "Opendroid": "https://opendroid.org/json.php?box={box}",
    "Teamblue (for gigablue devices)": "https://images.teamblue.tech/json/{box}",
    "Pure2": "https://www.pur-e2.club/OU/images/json/{box}",
    "Openvision": "https://images.openvision.dedyn.io/json/{box}",
    "OpenHDF": "https://flash.hdfreaks.cc/openhdf/json/{box}",
    "OpenATV": "https://images.mynonpublic.com/openatv/json/{box}",
    "OpenViX": "https://www.openvix.co.uk/json/{box}",
    "OpenPLI": "https://downloads.openpli.org/json/{box}",
    "OpenblackHole": "https://images.openbh.net/json/{box}",
    "Egami (for zgemma-novaler devices)": "https://image.egami-image.com/json/{box}",
    "OpenSPA": "https://openspa.webhop.info/online/json.php?box={box}"
}


GROUPS = [
    ["classm", "starsatlx", "genius", "evo", "galaxym6", "axodin", "axodinc", "odinm7"],
    ["geniuse3hd", "evoe3hd", "axase3", "axase3c", "e3hd"],
    ["maram9", "odinm9"],
    ["ventonhdx", "sezam5000hd", "mbtwin", "beyonwizt3", "inihdx"],
    ["sezam1000hd", "xpeedlx1", "xpeedlx2", "mbmini", "atemio5x00", "bwidowx", "inihde"],
    ["atemio6000", "atemio6100", "atemio6200", "mbminiplus", "mbhybrid", "bwidowx2", "beyonwizt2", "opticumtt", "evoslim", "xpeedlxpro", "inihde2"],
    ["xpeedlx3", "sezammarvel", "atemionemesis", "mbultra", "beyonwizt4", "inihdp"],
    ["xp1000mk", "xp1000max", "sf8", "xp1000plus", "xp1000"],
    ["mixoslumi", "eboxlumi"],
    ["mixosf7", "ebox7358"],
    ["mixosf5mini", "gi9196lite", "ebox5100"],
    ["mixosf5", "gi9196m", "ebox5000"],
    ["sogno8800hd", "uniboxhde", "blackbox7405"],
    ["enfinity", "marvel1", "ew7358"],
    ["mutant2400", "quadbox2400", "hd2400"],
    ["mutant11", "hd11"],
    ["mutant1100", "vizyonvita", "hd1100"],
    ["mutant1200", "hd1200"],
    ["mutant1265", "hd1265"],
    ["mutant1500", "hd1500"],
    ["mutant500c", "hd500c"],
    ["mutant530c", "hd530c"],
    ["vimastec1000", "vs1000"],
    ["enibox", "mago", "x1plus", "sf108", "vg5000"],
    ["t2cable", "jj7362"],
    ["x2plus", "ew7356"],
    ["bre2ze", "ew7362"],
    ["evomini", "ch62lc"],
    ["zgemmash1", "zgemmas2s", "zgemmass", "zgemmash2", "sh1"],
    ["zgemmahs", "zgemmah2s", "zgemmah2h", "novatwin", "novacombo", "zgemmah3ac", "zgemmah32tc", "zgemmah2splus", "h3"],
    ["zgemmaslc", "lc"],
    ["zgemmai55", "novaip", "i55"],
    ["zgemmai55plus", "i55plus"],
    ["zgemmai55se", "i55se"],
    ["zgemmah4", "h4"],
    ["zgemmah5", "zgemmah52s", "zgemmah5ac", "zgemmah52tc", "zgemmah52splus", "h5"],
    ["zgemmah6", "h6"],
    ["zgemmah7", "h7", "zgemmah7s", "multibox-4k-ultra-hd"],
    ["zgemmah17combo", "h17"],
    ["zgemmah82h", "h8"],
    ["zgemmah9s", "zgemmah9t", "zgemmah9splus", "zgemmah92s", "zgemmah92h", "h9"],
    ["zgemmah92hse", "zgemmah9sse", "h9se"],
    ["zgemmah9combose", "zgemmah9twinse", "h9combose"],
    ["zgemmah9combo", "zgemmah9twin", "h9combo"],
    ["zgemmah102s", "zgemmah102h", "zgemmah10combo", "h10"],
    ["zgemmah11s", "zgemmah112h", "h11"],
    ["zgemmahzeros", "hzero"],
    ["xcombo", "vg2000"],
    ["tyrant", "vg1000"],
    ["mbmicro", "e4hd", "e4hdhybrid", "7000s"],
    ["mbmicrov2", "7005s"],
    ["twinboxlcd", "singleboxlcd", "7100s"],
    ["twinboxlcdci5", "7105s"],
    ["sf208", "sf228", "7210s"],
    ["sf238", "7215s"],
    ["9910lx", "7220s"],
    ["9911lx", "e4hdcombo", "9920lx", "7225s"],
    ["odin2hybrid", "7300s"],
    ["odinplus", "7400s"],
    ["e4hdultra", "protek4k", "8100s"],
    ["xpeedlxcs2", "xpeedlxcc", "et7x00mini", "ultramini"],
    ["mbtwinplus", "sf3038", "alphatriple", "g300"],
    ["sf128", "sf138", "g100"],
    ["bre2zet2c", "g101"],
    ["osmega", "xc7346"],
    ["spycat", "osmini", "spycatmini", "osminiplus", "spycatminiplus", "xc7362"],
    ["spycat4kmini", "spycat4k", "spycat4kcombo", "xc7439"],
    ["dcube", "mkcube", "ultima", "cube"],
    ["amikomini", "dynaspark", "dynasparkplus", "amiko8900", "sognorevolution", "arguspingulux", "arguspinguluxmini", "arguspinguluxplus", "sparkreloaded", "sabsolo", "fulanspark1", "sparklx", "gis8120", "spark"],
    ["dynaspark7162", "amikoalien", "sognotriple", "sparktriplex", "sabtriple", "sparkone", "giavatar", "spark7162"],
    ["tm2t", "tmnano", "tmnano2t", "tmsingle", "tmtwin", "iqonios100hd", "iqonios300hd", "iqonios300hdv2", "optimussos1", "mediabox", "iqonios200hd", "roxxs200hd", "mediaart200hd", "optimussos2", "dags7335"],
    ["tmnano2super", "tmnano3t", "force1", "force1plus", "megaforce1plus", "worldvisionf1", "worldvisionf1plus", "optimussos1plus", "optimussos2plus", "optimussos3plus", "dags7356"],
    ["tmnanose", "tmnanosem2", "tmnanosem2plus", "tmnanosecombo", "force2plus", "force2", "megaforce2", "optimussos", "force2se", "fusionhd", "fusionhdse", "purehd", "force2nano", "tmnanom3", "valalinux", "dags7362"],
    ["force2plushv", "purehdse", "lunix", "lunixco", "dags73625"],
    ["revo4k", "force3uhd", "force3uhdplus", "tmtwin4k", "galaxy4k", "tm4ksuper", "lunix34k", "dags7252"],
    ["force4", "lunix4k", "dags72604"],
    ["gb800se", "gb800ue", "gb7325"],
    ["gb800seplus", "gb800ueplus", "gbipbox", "gb7358"],
    ["gbultrase", "gbultraue", "gbx1", "gbx3", "gb7362"],
    ["gbx2", "gbultraueh", "gbx3h", "gb73625"],
    ["gbquad", "gbquadplus", "gb7356"],
    ["gbquad4k", "gbue4k", "gbquad4kpro", "gb7252"],
    ["gbx34k", "gb72604"],
    ["gbtrio4k", "gbip4k", "gbtrio4kpro", "gbmv200"],
    ["sf98", "force2nano", "evoslimse", "yh7362"],
    ["evoslimt2c", "yh62tc"],
    ["vipert2c", "yh625tc"],
    ["vipercombo", "yh625dt"],
    ["vipercombohdd", "ch625dt"],
    ["viperslim", "yh73625"],
    ["mutant51", "ax51", "bre2ze4k", "hd51"],
    ["mutant60", "ax60", "hd60"],
    ["mutant61", "ax61", "hd61"],
    ["mutant66se", "hd66se"],
    ["vimastec1500", "vs1500"],
    ["gi11000", "viper4k51", "et1x000"],
    ["beyonwizu4", "et13000"],
    ["dinoboth265", "axashistwin", "u41"],
    ["spycatminiv2", "anadolprohd5", "iziboxecohd", "jdhdduo", "vipertwin", "vipersingle", "u42"],
    ["turing", "u43"],
    ["axashistwinplus", "u45"],
    ["dinobot4k", "mediabox4k", "anadol4k", "u5"],
    ["axashis4kcombo", "dinobot4kl", "anadol4kv2", "anadol4kcombo", "protek4kx1", "u51"],
    ["dinobot4kplus", "axashis4kcomboplus", "u52"],
    ["dinobot4kmini", "u53"],
    ["arivacombo", "u532"],
    ["arivatwin", "u533"],
    ["dinobot4kpro", "u54"],
    ["dinobotu55", "iziboxone4k", "hitube4k", "iziboxx3", "u55"],
    ["axashisc4k", "dinobot4kelite", "u56"],
    ["viper4kv20", "protek4kx2", "iziboxelite4k", "dinobot4ktwin", "hitube4kpro", "viper4kv30", "hitube4kplus", "iziboxx4", "u57"],
    ["iziboxone4kplus", "viper4kv40", "u571"],
    ["dinobot4kse", "ferguson4k", "u5pvr"],
    ["clap4k", "cc1"],
    ["maxytecmultise", "axmultiboxse", "anadolmultiboxse", "novaler4kse", "multiboxse", "multibox-4k-se-ultra-hd"],
    ["anadolmulti", "maxytecmulti", "anadolmultitwin", "axmulticombo", "axmultitwin", "novaler4k", "multibox", "multibox-4k-ultra-hd"],
    ["novaler4kpro", "multiboxpro", "multibox-4k-pro-ultra-hd"]
]

BOX_FALLBACKS = {}
for group in GROUPS:
    for hostname in group:
        BOX_FALLBACKS[hostname] = group

class Imagesdownloader(Screen):
    width, height = getDesktop(0).size().width(), getDesktop(0).size().height()
    skin_file = (
        "/usr/lib/enigma2/python/Plugins/Extensions/ElieSatPanelGrid/assets/skin/imagesdownloader_fhd.xml"
        if width >= 1920
        else "/usr/lib/enigma2/python/Plugins/Extensions/ElieSatPanelGrid/assets/skin/imagesdownloader_hd.xml"
    )
    try:
        with open(skin_file, "r") as f:
            skin = f.read()
    except Exception as e:
        print(f"[ElieSatPanel] Failed to load skin: {e}")
        skin = "<screen></screen>"

    LOG_FILE = "/tmp/extra1_downloads.log"

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session

        # ---------------- ONLY LOAD IF DEVICE UNLOCKED AND FILES EXIST ----------------
        unlock_ok = is_device_unlocked()
        unlock_file_exists = os.path.exists("/etc/eliesat_unlocked.cfg")
        main_mac_exists = os.path.exists("/etc/eliesat_main_mac.cfg")

        if not unlock_ok or not unlock_file_exists or not main_mac_exists:
            self.close()
            return

        # ---------------- PANEL INITIALIZATION ----------------
        self.hostname = self.getHostname()

        # ---------------- Device Icon ----------------
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

        self["red"] = Label("Red")
        self["green"] = Label("Green")
        self["yellow"] = Label("Yellow")
        self["blue"] = Label("Blue")
        self["list"] = ChoiceList([])
        self["progress"] = ProgressBar()

        # ---------------- Feed management ----------------
        self.feedData = {}
        self.current_feed = None
        self.prev_current_feed = None
        self.last_selected_feed = None
        self.last_selected_category = None
        self.last_selected_image = None
        self.expanded_categories = []

        self.download_in_progress = False
        self.download_finished = False
        self.download_target = None
        self.download_file = None
        self.download_resp = None
        self.chunk_iter = None

        # ---------------- Timer ----------------
        self.progress_timer = eTimer()
        self.progress_timer.callback.append(self._updateDownload)

        self.actions_enabled = False
        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions"],
            {
                "ok": self._safeKeyOk,
                "cancel": self._safeKeyCancel,
                "back": self._safeKeyCancel,
                "red": self._cancelDownloadUnified,
            },
            -1,
        )

        # ---------------- Loading state ----------------
        self.loading = True
        self.loading_message = "Uploading images, please wait..."
        self["list"].setList([ChoiceEntryComponent("loading", (self.loading_message, ""))])
        self.onLayoutFinish.append(self._startLoadingFeeds)

    # ---------------- Device Icon Loader ----------------
    def _safeLoadDeviceIcon(self):
        try:
            self._loadDeviceIcon()
        except Exception as e:
            print(f"[ElieSatPanel] Error loading device icon: {e}")

    def _loadDeviceIcon(self):
        base_path = "/usr/lib/enigma2/python/Plugins/Extensions/ElieSatPanelGrid/assets/boxicons/"
        icon_name = f"{self.hostname}.png"
        icon_path = os.path.join(base_path, icon_name)

        if not os.path.exists(icon_path):
            icon_path = os.path.join(base_path, "default.png")

        if os.path.exists(icon_path):
            try:
                self["device_icon"].instance.setPixmapFromFile(icon_path)
            except Exception as e:
                print(f"[ElieSatPanel] Failed to set pixmap: {e}")
        else:
            print(f"[ElieSatPanel] Device icon not found: {icon_path}")

    # ---------------- Safe key handlers ----------------
    def _safeKeyOk(self):
        if self.actions_enabled:
            self.keyOk()

    def _safeKeyCancel(self):
        if self.actions_enabled:
            self.keyCancel()

    # ---------------- Hostname ----------------
    def getHostname(self):
        try:
            with open("/etc/hostname", "r") as f:
                return f.readline().strip()
        except:
            return os.uname().nodename.strip()

    def getBoxList(self, feed_name):
        if self.hostname in BOX_FALLBACKS:
            return BOX_FALLBACKS[self.hostname]
        return [self.hostname]

    # ---------------- Feed loading ----------------
    def _startLoadingFeeds(self):
        from threading import Thread
        Thread(target=self._loadFeedsThread).start()

    def _loadFeedsThread(self):
        self.loadAllFeeds()
        self.loading = False
        self.actions_enabled = True
        self.updateFeeds()

    # ---------------- Helpers ----------------
    def getHostname(self):
        try:
            with open("/etc/hostname", "r") as f:
                return f.readline().strip()
        except:
            return os.uname().nodename.strip()

    def getBoxList(self, feed_name):
        if self.hostname in BOX_FALLBACKS:
            return BOX_FALLBACKS[self.hostname]
        return [self.hostname]

    # ---------------- Feed fetching ----------------
    def fetchFeed(self, feed_name):
        import re
        import os
        from urllib.parse import quote
        parsed = {}
        box_list = self.getBoxList(feed_name)

        # ---------------- Novaler ----------------
        if feed_name == "Novaler":
            for box in box_list:
                site = f"https://novaler.com/downloads/enigma2/{box}"
                try:
                    r = requests.get(site, headers=USER_AGENT, timeout=15)
                    r.raise_for_status()
                    html = r.text
                except Exception:
                    continue
                matches = re.findall(r'/uploads[^"]*\.zip', html)
                for href in matches:
                    parts = href.strip("/").split("/")
                    if len(parts) < 2:
                        continue
                    category = parts[-2]
                    file_name = parts[-1]
                    full_link = "https://novaler.com" + href
                    parsed.setdefault(category, {})[file_name] = {"link": full_link, "name": file_name}
            return {cat: dict(sorted(parsed[cat].items(), reverse=True))
                    for cat in sorted(parsed.keys(), reverse=True)} \
                    if parsed else {"Error": {"Device unsupported": ""}}

        # ---------------- OpenSPA ----------------
        elif feed_name == "OpenSPA":
            for box in box_list:
                try:
                    site = f"https://openspa.webhop.info/online/json.php?box={box}"
                    r = requests.get(site, headers=USER_AGENT, timeout=15)
                    r.raise_for_status()
                    lines = r.text.splitlines()
                except Exception:
                    continue
                current_version = ""
                temp_name = None
                temp_link = None
                for line in lines:
                    line = line.strip()
                    if '"OPENSPA' in line:
                        current_version = line.replace('{', '').replace('}', '').replace('"', '').replace(',', '').replace(':', '').strip()
                        parsed.setdefault(current_version, {})
                        continue
                    if '"name"' in line and current_version:
                        temp_name = line.replace('"', '').replace(',', '').replace('{', '').replace('}', '').replace('name:', '').strip()
                    elif '"link"' in line and current_version:
                        temp_link = line.replace('"', '').replace(',', '').replace('link:', '').replace('\\/', '/').strip()
                    if temp_name:
                        link_to_use = temp_link or f"https://openspa.webhop.info/online/images/{box}/{quote(current_version)}/{quote(temp_name)}.zip"
                        parsed[current_version][temp_name] = {"link": link_to_use, "name": temp_name}
                        temp_name = None
                        temp_link = None
            return {v: dict(sorted(parsed[v].items(), reverse=True))
                    for v in sorted(parsed.keys(), reverse=True)} \
                    if parsed else {"Error": {"Device unsupported": ""}}

        # ---------------- OpenHDF (Separate Treat) ----------------
        elif feed_name.lower() == "openhdf":
            for box in box_list:
                try:
                    url = FEEDS[feed_name].format(box=box)
                    r = requests.get(url, headers=USER_AGENT, timeout=15)
                    r.raise_for_status()
                    data = r.json()
                except Exception:
                    continue

                if not isinstance(data, dict):
                    continue

                for version_title, file_dict in data.items():
                    version = version_title.replace("openHDF Images Version:", "").strip()
                    if not isinstance(file_dict, dict):
                        continue

                    parsed.setdefault(version, {})

                    for file_name, file_info in file_dict.items():
                        if not isinstance(file_info, dict):
                            continue

                        link = file_info.get("link") or file_info.get("url")
                        if not link:
                            continue

                        name = file_info.get("name") or os.path.basename(link)
                        parsed[version][file_name] = {"link": link, "name": name}

            return {v: dict(sorted(parsed[v].items(), reverse=True))
                    for v in sorted(parsed.keys(), reverse=True)} \
                    if parsed else {"Error": {"Device unsupported": ""}}

        # ---------------- Other JSON feeds ----------------
        else:
            for box in box_list:
                try:
                    url = FEEDS[feed_name].format(box=box)
                    r = requests.get(url, headers=USER_AGENT, timeout=15)
                    r.raise_for_status()
                    data = r.json()
                    if isinstance(data, dict):
                        for k, v in data.items():
                            parsed[k] = v
                except Exception:
                    continue

            return {v: dict(sorted(parsed[v].items(), reverse=True))
                    for v in sorted(parsed.keys(), reverse=True)} \
                    if parsed else {"Error": {"Device unsupported": ""}}

    # ---------------- Feed management ----------------
    def loadAllFeeds(self):
        for f in FEEDS.keys():
            if f not in self.feedData:
                self.feedData[f] = self.fetchFeed(f)

    def updateFeeds(self, expanded_name=None):
        if getattr(self, "loading", False):
            self["list"].setList([ChoiceEntryComponent("loading", (self.loading_message, ""))])
            return

        items = []
        move_index = None
        cur = self["list"].getCurrent()
        selected_text = cur[0][0] if cur else None

        if self.current_feed:
            feed = self.feedData.get(self.current_feed, {})

            if feed == {"Error": {"Device unsupported": ""}}:
                items.append(ChoiceEntryComponent("feed", (f"⊕ {self.current_feed}", "Collapsed")))
                items.append(ChoiceEntryComponent("error", ("● Device unsupported", "")))
                self["list"].setList(items)
                if self.last_selected_feed == self.current_feed:
                    self["list"].moveToIndex(0)
                return

            items.append(ChoiceEntryComponent("feed", (f"▼ {self.current_feed}", "Expanded")))
            idx = 1
            for cat in sorted(feed.keys(), reverse=True):
                cat_expanded = cat in self.expanded_categories
                symbol = "▼" if cat_expanded else "▶"
                items.append(ChoiceEntryComponent("category", (f"{symbol} {cat}", "Expanded" if cat_expanded else "Collapsed")))
                if cat_expanded:
                    if expanded_name is not None and cat == expanded_name:
                        move_index = idx
                    for img in sorted(feed[cat].keys(), reverse=True):
                        info = feed[cat][img]
                        items.append(ChoiceEntryComponent("image", (f"- {info.get('name', img)}", info)))
                        idx += 1
        else:
            for f in sorted(FEEDS.keys()):
                items.append(ChoiceEntryComponent("feed", (f"⊕ {f}", "Collapsed")))

        self["list"].setList(items)

        # Restore last selected image
        restored = False
        if self.last_selected_image and self.current_feed:
            for idx, item in enumerate(items):
                text, status = item[0]
                name = text.strip().lstrip("⊕▼▶-").strip()
                if isinstance(status, dict) and name == self.last_selected_image:
                    self["list"].moveToIndex(idx)
                    restored = True
                    break
        if not restored and self.last_selected_feed and not self.current_feed:
            for idx, item in enumerate(items):
                name = item[0][0].strip().lstrip("⊕▼▶-").strip()
                if name == self.last_selected_feed:
                    self["list"].moveToIndex(idx)
                    break

    # ---------------- Actions ----------------
    def keyCancel(self):
        if self.download_in_progress:
            self._cancelDownloadUnified()
        elif self.current_feed:
            if self.expanded_categories:
                self.expanded_categories = []
                self.updateFeeds()
            else:
                self.last_selected_feed = self.current_feed
                self.current_feed = None
                self.updateFeeds()
        else:
            self.close()

    def keyOk(self):
        if getattr(self, "download_finished", False):
            self.download_finished = False
            self["download_info"].setText("")
            self["item_name"].setText("")
            self["progress"].setValue(0)
            return

        if getattr(self, "download_in_progress", False):
            return

        cur = self["list"].getCurrent()
        if not cur:
            return

        text, status = cur[0][0], cur[0][1]
        name = text.strip().lstrip("⊕▼▶-").strip()
        expanded_name = None

        if name == "Device unsupported":
            self.expanded_categories = []
            self.last_selected_feed = self.current_feed
            self.updateFeeds()
            return

        if name in FEEDS:
            if self.current_feed == name:
                self.current_feed = None
                self.expanded_categories = []
            else:
                self.prev_current_feed = self.current_feed
                self.current_feed = name
                self.expanded_categories = []

                feed = self.feedData.get(self.current_feed, {})
                first_idx = None
                idx = 1
                for cat in sorted(feed.keys(), reverse=True):
                    for img in sorted(feed[cat].keys(), reverse=True):
                        first_idx = idx
                        break
                    if first_idx is not None:
                        break
                    idx += 1 + len(feed[cat])
                if first_idx is not None:
                    self["list"].moveToIndex(first_idx)

        elif status in ["Collapsed", "Expanded"]:
            if name in self.expanded_categories:
                self.expanded_categories.remove(name)
            else:
                self.expanded_categories.append(name)
                expanded_name = name

        elif isinstance(status, dict) and "link" in status:
            self.last_selected_image = name
            self.last_selected_category = expanded_name
            if not getattr(self, "download_finished", False):
                self._startDownload(status)

        self.last_selected_feed = self.current_feed if self.current_feed else self.last_selected_feed
        self.updateFeeds(expanded_name=expanded_name)

    # ---------------- Download ----------------
    def getDownloadPath(self):
        if os.path.exists("/media/hdd/images"):
            return "/media/hdd/images"
        elif os.path.exists("/media/usb/images"):
            return "/media/usb/images"
        return "/tmp"

    def _startDownload(self, file_info):
        try:
            self.download_in_progress = True
            self.download_finished = False
            url = file_info.get("link")
            filename = file_info.get("name") or os.path.basename(url)
            if not filename.endswith(".zip"):
                filename += ".zip"

            path = self.getDownloadPath()
            os.makedirs(path, exist_ok=True)
            self.download_target = os.path.join(path, filename)

            USER_AGENT = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            self.download_resp = requests.get(url, headers=USER_AGENT, stream=True, timeout=30)
            self.download_resp.raise_for_status()

            self.download_total = int(self.download_resp.headers.get("Content-Length", 0))
            self.download_current = 0
            self.download_file = open(self.download_target, "wb")
            self.chunk_iter = self.download_resp.iter_content(1024 * 64)

            self["progress"].setValue(0)
            self["item_name"].setText(filename)
            self["download_info"].setText("0% (0 KB)")
            self._logDownload("START", url)

            self.progress_timer.start(100, True)
        except Exception as e:
            self.download_in_progress = False
            self._cancelDownloadUnified()
            self._logDownload("FAIL", url, str(e))

    def _updateDownload(self):
        if not getattr(self, "download_in_progress", False):
            return
        try:
            chunk = next(self.chunk_iter, None)
            if chunk:
                self.download_file.write(chunk)
                self.download_current += len(chunk)
                percent = int(self.download_current * 100 / self.download_total) if self.download_total else 0
                size_info = f"{self.download_current // 1024}/{self.download_total // 1024} KB"
                self["progress"].setValue(percent)
                self["download_info"].setText(f"{percent}% ({size_info})")
                self.progress_timer.start(100, True)
            else:
                self._finishDownload()
        except StopIteration:
            self._finishDownload()
        except Exception as e:
            self._cancelDownloadUnified()
            self._logDownload("FAIL", self.download_target, str(e))

    def _finishDownload(self):
        if getattr(self, "download_file", None):
            self.download_file.close()
        if getattr(self, "download_resp", None):
            self.download_resp.close()

        self.download_in_progress = False
        self.download_finished = True

        # ---------------- Copy to additional directories ----------------
        target_dirs = [
            "/media/hdd/ImagesUpload/",
            "/media/hdd/open-multiboot-upload/",
            "/media/hdd/OPDBootUpload/",
            "/media/hdd/EgamiBootUpload/"
        ]

        import shutil

        copy_total = len([d for d in target_dirs if os.path.exists(d)])
        copy_done = 0

        for dir_path in target_dirs:
            if os.path.exists(dir_path):
                try:
                    shutil.copy2(self.download_target, dir_path)
                    copy_done += 1
                    percent = int(copy_done * 100 / copy_total) if copy_total else 100
                    self["progress"].setValue(percent)
                    self["download_info"].setText(f"Copying... {percent}%")
                    self.progress_timer.start(100, True)
                    self._logDownload("COPY", f"{self.download_target} -> {dir_path}")
                except Exception as e:
                    self._logDownload("COPY_FAIL", f"{self.download_target} -> {dir_path}", str(e))

        self["progress"].setValue(100)
        self["item_name"].setText(f"Downloaded & copied: {os.path.basename(self.download_target)}")
        self["download_info"].setText("100%")
        self._logDownload("SUCCESS", self.download_target)

    def _cancelDownloadUnified(self):
        if getattr(self, "download_in_progress", False):
            self.download_in_progress = False
            try:
                if self.download_file:
                    self.download_file.close()
                if self.download_resp:
                    self.download_resp.close()
            except:
                pass
            if self.download_target and os.path.exists(self.download_target):
                try:
                    os.remove(self.download_target)
                except:
                    pass
            self.download_file = None
            self.download_resp = None
            self.download_target = None

        self.download_finished = False
        self["progress"].setValue(0)
        self["download_info"].setText("Canceled")
        self["item_name"].setText("Download canceled")

    # ---------------- Logging ----------------
    def _logDownload(self, status, target, error=None):
        try:
            with open(self.LOG_FILE, "a") as f:
                if error:
                    f.write(f"{status} | {target} | {error}\n")
                else:
                    f.write(f"{status} | {target}\n")
        except:
            pass

