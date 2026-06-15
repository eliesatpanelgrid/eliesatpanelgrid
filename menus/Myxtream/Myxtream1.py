# -*- coding: utf-8 -*-

from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.MenuList import MenuList
from Components.ActionMap import ActionMap
from Components.Label import Label
import os
from enigma import getDesktop

try:
    from urllib.request import urlopen, Request
except:
    from urllib2 import urlopen, Request

import json

CONFIG_FILE = "/etc/enigma2/MyXtream/playlists.txt"
IPAUDIO_JSON_FILE = "/etc/enigma2/IPAudioPro.json"


def read_config():
    try:
        dir_name = os.path.dirname(CONFIG_FILE)
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)

        if not os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "w") as f:
                f.write("")

        with open(CONFIG_FILE, "r") as f:
            lines = [x.strip() for x in f.readlines() if x.strip()]
            if not lines:
                return None, None, None, "ts"

            first_line = lines[0]

            output_format = "ts"
            if "output=m3u8" in first_line:
                output_format = "m3u8"

            # --- FORMAT 2: Check if it's a full Xtream/M3U Link ---
            if "get.php" in first_line and "username=" in first_line and "password=" in first_line:
                host = first_line.split("/get.php")[0]
                
                # Fix variations of malformed ports like "/:80" into standard ":80"
                if "/:" in host:
                    host = host.replace("/:", ":")
                
                if host.endswith("/"):
                    host = host[:-1]
                
                username = ""
                if "username=" in first_line:
                    username = first_line.split("username=")[1].split("&")[0]
                    
                password = ""
                if "password=" in first_line:
                    password = first_line.split("password=")[1].split("&")[0]
                    
                if host and username and password:
                    return host, username, password, output_format

            # --- FORMAT 1: Fallback to original 3-line format ---
            if len(lines) >= 3:
                host = lines[0].strip()
                if "/:" in host:
                    host = host.replace("/:", ":")
                if host.endswith("/"):
                    host = host[:-1]
                return host, lines[1].strip(), lines[2].strip(), output_format
    except Exception as e:
        print("[MyXtream] Config parsing error:", e)
        
    return None, None, None, "ts"


def api_call(url):
    """
    Universal connection fallback mechanism. Loops through browser headers and raw protocols
    to guarantee a connection across both strict security setups and basic legacy panels.
    """
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",  # Modern Chrome (Fixes maxy4)
        "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) Enigma2 IPTV",                        # Enigma2 Standard (Fixes cafott)
        "Enigma2 Handoff",                                                                                                # Minimalistic backup agent
        ""                                                                                                                # Completely clean protocol fallback
    ]
    
    for index, ua in enumerate(user_agents):
        try:
            print("[MyXtream] Attempting connection profile %d using User-Agent: %s" % (index + 1, ua))
            
            if ua:
                req = Request(url, headers={'User-Agent': ua})
            else:
                req = Request(url)  # Raw unmasked fallback header
                
            response_bytes = urlopen(req, timeout=12).read()
            response = response_bytes.decode("utf-8", "ignore")
            
            # Validation: Verify the server actually sent backend data, not an HTML error or block-page
            if response and not response.strip().startswith("<!DOCTYPE html>"):
                print("[MyXtream] Connection profile %d SUCCEEDED! Response preview:" % (index + 1), response[:150])
                return response
            else:
                print("[MyXtream] Warning: Profile %d hit an external firewall loop/HTML page. Retrying..." % (index + 1))
        except Exception as e:
            print("[MyXtream] Connection profile %d rejected request: %s" % (index + 1, str(e)))
            continue  # Fall down directly to next network profile wrapper
            
    print("[MyXtream] ERROR: Global connectivity failure. All fallback connection profiles exhausted.")
    return None


def get_categories(host, user, password):
    url = "%s/player_api.php?username=%s&password=%s&action=get_live_categories" % (host, user, password)
    data = api_call(url)
    if not data:
        return []
    try:
        parsed = json.loads(data)
        if isinstance(parsed, dict) and "user_info" in parsed:
            print("[MyXtream] Panel sent server authorization instead of explicit category blocks.")
        return parsed if isinstance(parsed, list) else []
    except Exception as parse_err:
        print("[MyXtream] Parsing Exception handled on categories mapping:", parse_err)
        return []


def get_streams(host, user, password):
    url = "%s/player_api.php?username=%s&password=%s&action=get_live_streams" % (host, user, password)
    data = api_call(url)
    if not data:
        return []
    try:
        parsed = json.loads(data)
        return parsed if isinstance(parsed, list) else []
    except Exception as parse_err:
        print("[MyXtream] Parsing Exception handled on streaming metadata:", parse_err)
        return []


def build_stream_url(host, user, password, stream_id, container_format):
    return "%s/live/%s/%s/%s.%s" % (host, user, password, stream_id, container_format)


# ---------------- CHANNEL SCREEN ----------------

class MyXtreamChannels(Screen):

    width, height = getDesktop(0).size().width(), getDesktop(0).size().height()
    skin_file = (
        "/usr/lib/enigma2/python/Plugins/Extensions/ElieSatPanelGrid/menus/Myxtream/myxtreamc_fhd.xml"
        if width >= 1920
        else "/usr/lib/enigma2/python/Plugins/Extensions/ElieSatPanelGrid/menus/Myxtream/myxtreamc_hd.xml"
    )
    try:
        with open(skin_file, "r") as f:
            skin = f.read()
    except Exception as e:
        print(f"[ElieSatPanel] Failed to load skin: {e}")
        skin = "<screen></screen>"

    def __init__(self, session, title, channels):
        Screen.__init__(self, session)

        self.title = title
        self.channels = channels

        self["title"] = Label(title)
        self["list"] = MenuList([x[0] for x in channels])

        self["actions"] = ActionMap(
            ["OkCancelActions"],
            {
                "ok": self.promptAddToIPAudio,
                "cancel": self.close
            },
            -1
        )

    def promptAddToIPAudio(self):
        idx = self["list"].getSelectionIndex()
        if idx < 0:
            return

        self.selected_name, self.selected_url = self.channels[idx]

        self.session.openWithCallback(
            self.addChannelToJSON,
            MessageBox,
            "Channel: %s\n\nDo you want to add this stream to IPAudio Pro?" % self.selected_name,
            MessageBox.TYPE_YESNO
        )

    def addChannelToJSON(self, answer):
        if not answer:
            return

        try:
            data = {"Playlist": {"streams": []}}

            if os.path.exists(IPAUDIO_JSON_FILE):
                with open(IPAUDIO_JSON_FILE, "r") as f:
                    content = f.read().strip()
                    if content:
                        try:
                            data = json.loads(content)
                        except Exception as json_err:
                            print("[MyXtream] Corrupt JSON structure, rebuilding: ", json_err)

            if "Playlist" not in data:
                data["Playlist"] = {}
            if "streams" not in data["Playlist"]:
                data["Playlist"]["streams"] = []

            duplicate = False
            for stream in data["Playlist"]["streams"]:
                if stream.get("url") == self.selected_url:
                    duplicate = True
                    break

            if duplicate:
                self.session.open(
                    MessageBox,
                    "Stream is already present in IPAudio Pro playlist!",
                    MessageBox.TYPE_INFO
                )
                return

            new_stream = {
                "name": self.selected_name,
                "display_name": self.selected_name,
                "url": self.selected_url
            }
            data["Playlist"]["streams"].append(new_stream)

            with open(IPAUDIO_JSON_FILE, "w") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

            self.session.open(
                MessageBox,
                "Successfully added:\n%s\nto IPAudio Pro!" % self.selected_name,
                MessageBox.TYPE_INFO
            )

        except Exception as e:
            print("[MyXtream] Failed writing to IPAudio Pro JSON: ", e)
            self.session.open(
                MessageBox,
                "Error writing to IPAudio Pro configuration file.\n%s" % str(e),
                MessageBox.TYPE_ERROR
            )


# ---------------- CATEGORY SCREEN ----------------
class Myxtream(Screen):

    width, height = getDesktop(0).size().width(), getDesktop(0).size().height()
    skin_file = (
        "/usr/lib/enigma2/python/Plugins/Extensions/ElieSatPanelGrid/menus/Myxtream/myxtream_fhd.xml"
        if width >= 1920
        else "/usr/lib/enigma2/python/Plugins/Extensions/ElieSatPanelGrid/menus/Myxtream/myxtream_hd.xml"
    )
    try:
        with open(skin_file, "r") as f:
            skin = f.read()
    except Exception as e:
        print(f"[ElieSatPanel] Failed to load skin: {e}")
        skin = "<screen></screen>"

    def __init__(self, session):
        Screen.__init__(self, session)

        self["title"] = Label("Loading Xtream API...")
        self["list"] = MenuList([])

        self.categories = []
        self.streams = []
        self.container_format = "ts"

        self["actions"] = ActionMap(
            ["OkCancelActions"],
            {
                "ok": self.openCategory,
                "cancel": self.close
            },
            -1
        )

        self.onFirstExecBegin.append(self.load)

    def load(self):
        host, user, password, container_format = read_config()

        if not host:
            self.session.open(
                MessageBox,
                "Invalid config file",
                MessageBox.TYPE_ERROR
            )
            return

        self.host = host
        self.user = user
        self.password = password
        self.container_format = container_format

        self["title"].setText("Loading categories...")

        raw_categories = get_categories(host, user, password)
        self.streams = get_streams(host, user, password)

        # Fallback safeguard: If categories API field failed but streams exist, build a global category placeholder
        if not raw_categories and self.streams:
            print("[MyXtream] Categories array was empty, grouping via streams data injection.")
            unique_cat_ids = set()
            for s in self.streams:
                cid = s.get("category_id")
                if cid and cid not in unique_cat_ids:
                    unique_cat_ids.add(cid)
                    raw_categories.append({
                        "category_id": cid,
                        "category_name": "Category ID: %s" % str(cid),
                        "category_order": 0
                    })

        try:
            self.categories = sorted(
                raw_categories, 
                key=self.get_category_sort_key
            )
        except Exception as e:
            print("[MyXtream] Sorting exception, using default order:", e)
            self.categories = raw_categories

        menu_items = []
        for c in self.categories:
            name = c.get("category_name", "Unknown")
            menu_items.append(name)

        self["list"].setList(menu_items)
        self["title"].setText("Categories (%d)" % len(self.categories))

        if len(self.categories) == 0:
            self.session.open(
                MessageBox,
                "No live streaming streams or categories found.\nCheck your account subscription or connection logs.",
                MessageBox.TYPE_INFO
            )

    def get_category_sort_key(self, item):
        order = item.get("category_order", 0)
        try:
            return int(order)
        except:
            return 0

    def openCategory(self):
        idx = self["list"].getSelectionIndex()
        if idx < 0 or idx >= len(self.categories):
            return

        selected_cat = self.categories[idx]
        cat_id = selected_cat.get("category_id")
        cat_name = selected_cat.get("category_name", "Unknown")

        channels = []

        for s in self.streams:
            if str(s.get("category_id")) == str(cat_id):
                name = s.get("name", "Unknown")
                sid = s.get("stream_id")
                url = build_stream_url(self.host, self.user, self.password, sid, self.container_format)
                channels.append((name, url))

        self.session.open(
            MyXtreamChannels,
            cat_name,
            channels
        )
