# -*- coding: utf-8 -*-
import os
import re
import json
from enigma import eTimer, getDesktop

from Plugins.Extensions.ElieSatPanelGrid.menus.Helpers import (
    get_local_ip,
    check_internet,
    get_image_name,
    get_python_version,
    get_storage_info,
    get_ram_info,
)

from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.config import ConfigText, ConfigSelection, getConfigListEntry
from Components.ConfigList import ConfigListScreen
from Plugins.Extensions.ElieSatPanelGrid.__init__ import Version
from Plugins.Extensions.ElieSatPanelGrid.menus.Infobox import IptvScreen


class Iptvadder(Screen, ConfigListScreen):

    width, height = getDesktop(0).size().width(), getDesktop(0).size().height()

    skin_file = (
        "/usr/lib/enigma2/python/Plugins/Extensions/ElieSatPanelGrid/menus/Iptvadder/iptvadder_fhd.xml"
        if width >= 1920
        else "/usr/lib/enigma2/python/Plugins/Extensions/ElieSatPanelGrid/menus/Iptvadder/iptvadder_hd.xml"
    )

    try:
        with open(skin_file, "r") as f:
            skin = f.read()
    except:
        skin = "<screen></screen>"

    # 🌟 CENTRAL SERVER MAPPING TABLE
    SERVER_MAPPING = {
        "custom": ("http://url.com", "user", "pass"),
        "serverx1": ("http://cafott.com", None, None),
        "serverx2": ("http://vipxtv.net", None, None),
        "serverx3": ("http://servx.pro", None, None),
        "serverx4": ("http://hxb8j.otvipserv.com", None, None),
        "serverx5": ("http://smartott.org", None, None),
        "serverx6": ("http://vireexaa.com", None, None),
        "serverx7": ("http://rfcot.com", None, None),
        "serverx8": ("http://qwerlo.com", None, None),
        "jepro1": ("http://a345d.info", None, None),
        "ultra": ("http://ultra.gotop.me", None, None),
        "strong8k1": ("https://fine61764.wd.business-cloud-8k.ru", None, None),
        "strong8k2": ("https://cf.cdn-90.me", None, None),
        "neo4k1": ("http://april80089.wd.business-cloud-neo.ru", None, None),
        "neo4k2": ("http://cf.business-cloud-neo.ru", None, None),
        "neo4k3": ("http://pro.business-cloud-neo.ru", None, None),
        "neo4k4": ("http://tv.business-cloud-neo.ru", None, None),
    }

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        self.setTitle(_("Subscription Editor"))

        self.label = ConfigSelection(
            default="custom",
            choices=[
                ("custom", "custom"),
                ("serverx1", "serverx1"),
                ("serverx2", "serverx2"),
                ("serverx3", "serverx3"),
                ("serverx4", "serverx4"),
                ("serverx5", "serverx5"),
                ("serverx6", "serverx6"),
                ("serverx7", "serverx7"),
                ("serverx8", "serverx8"),
                ("jepro1", "server jepro1"),
                ("ultra", "server ultra"),
                ("strong8k1", "server strong 8k1"),
                ("strong8k2", "server strong 8k2"),
                ("neo4k1", "server neo4k1"),
                ("neo4k2", "server neo4k2"),
                ("neo4k3", "server neo4k3"),
                ("neo4k4", "server neo4k4"),
            ],
        )

        self.url = ConfigText(default="http://url.com")
        self.port = ConfigText(default="80")
        self.username = ConfigText(default="user")
        self.password = ConfigText(default="pass")

        self.label.addNotifier(self.label_changed, initial_call=False)

        self.clist = [
            getConfigListEntry("Label:", self.label),
            getConfigListEntry("URL:", self.url),
            getConfigListEntry("Port:", self.port),
            getConfigListEntry("Username:", self.username),
            getConfigListEntry("Password:", self.password),
        ]

        ConfigListScreen.__init__(self, self.clist, session=session)
        self["config"].l.setList(self.clist)

        self["left_bar"] = Label("\n".join(list("Version " + Version)))
        self["right_bar"] = Label("\n".join(list("By ElieSat")))

        self["image_name"] = Label("Image: " + get_image_name())
        self["local_ip"] = Label("IP: " + get_local_ip())
        self["StorageInfo"] = Label(get_storage_info())
        self["RAMInfo"] = Label(get_ram_info())
        self["python_ver"] = Label("Python: " + get_python_version())
        self["net_status"] = Label("Net: " + check_internet())

        self["red"] = Label(_("Show Live Status"))
        self["green"] = Label(_("Save"))
        self["blue"] = Label(_("Delete Options Menu"))
        self["yellow"] = Label(_("Select Subscription Line"))

        self["panel_path"] = Label("")

        self.panel_dir = self.find_panel_dir()

        # Ensure plugins configuration files exist permanently if plugins are present
        self.ensure_myxtream_playlist_exists()
        self.ensure_xtreamnew_file_exists()

        self["playlists"] = Label(self.get_playlists_dirs())

        self.load_saved_subscription()

        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions"],
            {
                "red": self.show_isubscription_path,
                "green": self.send_backup,
                "yellow": self.select_subscription_line,
                "blue": self.delete_subscription_line,
                "cancel": self.close,
            },
            -1,
        )

    def is_xportal_installed(self):
        return os.path.exists("/usr/lib/enigma2/python/Plugins/Extensions/XPortal")

    def is_myxtream_installed(self):
        return os.path.exists("/usr/lib/enigma2/python/Plugins/Extensions/ElieSatPanelGrid/menus/Myxtream")

    def is_xtreamnew_installed(self):
        return os.path.exists("/usr/lib/enigma2/python/Plugins/Extensions/XtreamNew")

    def ensure_myxtream_playlist_exists(self):
        if self.is_myxtream_installed():
            myxtream_dir = "/etc/enigma2/MyXtream"
            myxtream_file = os.path.join(myxtream_dir, "playlists.txt")
            if not os.path.exists(myxtream_file):
                try:
                    if not os.path.exists(myxtream_dir):
                        os.makedirs(myxtream_dir)
                    open(myxtream_file, "w").close()
                except:
                    pass

    def ensure_xtreamnew_file_exists(self):
        if self.is_xtreamnew_installed():
            xtreamnew_dir = "/etc/enigma2/xtreamnew"
            xtreamnew_file = os.path.join(xtreamnew_dir, "settings.json")
            if not os.path.exists(xtreamnew_file):
                try:
                    if not os.path.exists(xtreamnew_dir):
                        os.makedirs(xtreamnew_dir)
                    default_data = {
                        "playlists": [],
                        "last_playlist": 0,
                        "favorites": {"live": [], "vod": [], "series": []},
                        "resume": {},
                        "ui": {"last_section": "live"},
                        "settings": {
                            "player_type": 4097,
                            "live_player_type": 4097,
                            "vod_player_type": 4097,
                            "enable_picons": False,
                            "enable_background_preload": True,
                            "epg_auto_update": False,
                            "epg_auto_time": "06:00",
                            "epg_auto_interval_hours": 12,
                            "cache_path": "/media/hdd/XtreamNew/cache",
                            "tmdb_api": "",
                            "tmdb_language": "en",
                            "series_theme_enabled": True,
                            "series_theme_source": "local_ytdlp",
                            "series_theme_volume": 18,
                            "series_theme_delay": 2,
                            "series_theme_loop": True,
                            "series_theme_folder": "/media/hdd/XtreamNew/series_themes",
                            "series_theme_ytdlp_path": "",
                            "plot_translation_mode": "disabled",
                            "actor_translation_mode": "disabled",
                            "groq_api_key": "",
                            "groq_model": "llama-3.3-70b-versatile",
                            "vod_layout_style": "home_grid",
                            "series_layout_style": "home_grid",
                            "live_layout_style": "sidebar",
                            "main_menu_style": "grid",
                            "ui_color_theme": "Blue",
                            "plot_word_limit": 20,
                            "epg_download_path": "/media/hdd/XtreamNew/epg",
                            "live_epg_source": "server",
                            "xtream_epggrabber_path": "/etc/epgimport/xtream_epggrabber",
                            "ipaudio_playlist_path": "/media/hdd/ipaudio/playlist.json",
                            "iptv_export_enabled": True,
                            "iptv_export_format": "liteaudio",
                            "iptv_export_file": "/media/hdd/ipaudio/playlist.json",
                            "iptv_export_folder": "/media/hdd/ipaudio",
                            "download_path": "/media/hdd/XtreamNew/downloads",
                            "backup_path": "/media/hdd/XtreamNew/backup",
                            "settings_data_path": "/etc/enigma2/xtreamnew",
                            "show_adult_channels": False
                        }
                    }
                    with open(xtreamnew_file, "w") as f:
                        json.dump(default_data, f, indent=4)
                except:
                    pass

    def get_playlists_dirs(self):
        plugins = []
        for root, _, files in os.walk("/etc/enigma2"):
            if "playlists.txt" in files:
                folder = os.path.basename(root)
                name = folder.replace("_", " ").replace("-", " ").strip().title()
                if name and name not in plugins:
                    plugins.append(name)

        if self.is_xportal_installed() and "Xportal" not in plugins:
            plugins.append("Xportal")

        if self.is_xtreamnew_installed() and "Xtreamnew" not in plugins:
            plugins.append("Xtreamnew")

        return "Available plugins playlists:\n(" + ", ".join(plugins) + ")" if plugins else "Available plugins playlists:\n(<not found>)"

    def get_all_playlists_files(self):
        files = []
        for root, _, fs in os.walk("/etc/enigma2"):
            if "playlists.txt" in fs:
                files.append(os.path.join(root, "playlists.txt"))
        return files

    def load_saved_subscription(self):
        if not self.panel_dir:
            return

        subfile = os.path.join(self.panel_dir, "isubscription.txt")
        if not os.path.exists(subfile):
            return

        try:
            with open(subfile, "r") as f:
                lines = [l.strip() for l in f.readlines() if l.strip()]

            if not lines:
                return

            last_line = None
            for line in reversed(lines):
                if "/get.php?" in line or "http" in line:
                    last_line = line
                    break

            if not last_line:
                return

            self.parse_and_fill_credentials(last_line)
        except:
            pass

    def parse_and_fill_credentials(self, url_line):
        m = re.match(
            r'(http[s]?://[^:/]+)(?::(\d+))?/get\.php\?username=([^&]+)&password=([^&]+)',
            url_line,
        )
        if m:
            extracted_url = m.group(1)
            extracted_port = m.group(2) or ""
            extracted_user = m.group(3)
            extracted_pass = m.group(4)

            self.url.setValue(extracted_url)
            self.port.setValue(extracted_port)
            self.username.setValue(extracted_user)
            self.password.setValue(extracted_pass)

            matched_label = "custom"
            for label_key, val_tuple in self.SERVER_MAPPING.items():
                if label_key != "custom" and val_tuple[0] == extracted_url:
                    matched_label = label_key
                    break

            self.label.setValue(matched_label)
            self.refresh_config()

    def select_subscription_line(self):
        if not self.panel_dir:
            return
        subfile = os.path.join(self.panel_dir, "isubscription.txt")
        if not os.path.exists(subfile):
            self["panel_path"].setText("No file found")
            return

        try:
            with open(subfile, "r") as f:
                lines = [l.strip() for l in f.readlines() if l.strip()]

            if not lines:
                self["panel_path"].setText("File is empty")
                return

            menu_list = []
            for idx, line in enumerate(lines):
                menu_list.append((line, idx))

            self.session.openWithCallback(
                self.select_subscription_line_chosen,
                ChoiceBox,
                title=_("Select a subscription line to move to the bottom & load:"),
                list=menu_list
            )
        except:
            self["panel_path"].setText("Error reading file")

    def select_subscription_line_chosen(self, answer):
        if answer is None:
            return
        
        selected_line = answer[0]
        selected_idx = answer[1]

        subfile = os.path.join(self.panel_dir, "isubscription.txt")
        try:
            with open(subfile, "r") as f:
                lines = [l.strip() for l in f.readlines() if l.strip()]

            line_to_move = lines.pop(selected_idx)
            lines.append(line_to_move)

            with open(subfile, "w") as f:
                f.write("\n".join(lines) + "\n")

            self.parse_and_fill_credentials(line_to_move)
            self["panel_path"].setText("Line moved to bottom and active:\n%s" % line_to_move)
        except:
            self["panel_path"].setText("Error processing file updates")

    def delete_subscription_line(self):
        menu_list = [
            (_("All (backups) -> Remove all URLs from subscriptions file"), "clear_backups"),
            (_("All (subscriptions) -> Remove all URLs from other plugin paths"), "clear_subscriptions")
        ]

        if self.panel_dir:
            subfile = os.path.join(self.panel_dir, "isubscription.txt")
            if os.path.exists(subfile):
                try:
                    with open(subfile, "r") as f:
                        lines = [l.strip() for l in f.readlines() if l.strip()]
                    for idx, line in enumerate(lines):
                        menu_list.append((line, idx))
                except:
                    pass

        self.session.openWithCallback(
            self.delete_subscription_line_chosen,
            ChoiceBox,
            title=_("Select a deletion action or a specific line to REMOVE:"),
            list=menu_list
        )

    def delete_subscription_line_chosen(self, answer):
        if answer is None:
            return
            
        action_type = answer[1]

        if action_type == "clear_backups":
            if self.panel_dir:
                subfile = os.path.join(self.panel_dir, "isubscription.txt")
                try:
                    with open(subfile, "w") as f:
                        f.write("")
                    self["panel_path"].setText("All urls removed from subscriptions file successfully!")
                except:
                    self["panel_path"].setText("Error cleaning backups file")
            return

        if action_type == "clear_subscriptions":
            try:
                for fpath in self.get_all_playlists_files():
                    if os.path.exists(fpath):
                        with open(fpath, "w") as f:
                            f.write("")
                
                if self.is_xportal_installed():
                    xportal_txt = "/etc/enigma2/XPortal/xtream.txt"
                    if os.path.exists(xportal_txt):
                        with open(xportal_txt, "w") as f:
                            f.write("")

                if self.is_xtreamnew_installed():
                    xtreamnew_file = "/etc/enigma2/xtreamnew/settings.json"
                    if os.path.exists(xtreamnew_file):
                        try:
                            with open(xtreamnew_file, "r") as f:
                                data = json.load(f)
                            data["playlists"] = []
                            with open(xtreamnew_file, "w") as f:
                                json.dump(data, f, indent=4)
                        except:
                            pass

                self["panel_path"].setText("All urls removed from external paths successfully!")
            except:
                self["panel_path"].setText("Error clearing subscription targets")
            return

        selected_idx = action_type
        subfile = os.path.join(self.panel_dir, "isubscription.txt")
        try:
            with open(subfile, "r") as f:
                lines = [l.strip() for l in f.readlines() if l.strip()]

            lines.pop(selected_idx)

            with open(subfile, "w") as f:
                f.write("\n".join(lines) + "\n")

            self["panel_path"].setText("Deleted line successfully!")
            self.load_saved_subscription()
        except:
            self["panel_path"].setText("Error deleting subscription line")

    def send_backup(self):
        # Guarantee MyXtream and XtreamNew files exist before processing
        self.ensure_myxtream_playlist_exists()
        self.ensure_xtreamnew_file_exists()

        port_val = self.port.value.strip()
        url_val = self.url.value.strip()
        user_val = self.username.value.strip()
        pass_val = self.password.value.strip()
        label_val = self.label.value.strip()

        if port_val:
            new_line = "%s:%s/get.php?username=%s&password=%s&type=m3u_plus&output=ts" % (
                url_val, port_val, user_val, pass_val
            )
            host_url = "%s:%s" % (url_val, port_val)
        else:
            new_line = "%s/get.php?username=%s&password=%s&type=m3u_plus&output=ts" % (
                url_val, user_val, pass_val
            )
            host_url = url_val

        def update_file_lines(filepath, line_to_add):
            lines = []
            if os.path.exists(filepath):
                try:
                    with open(filepath, "r") as f:
                        lines = [l.strip() for l in f.readlines() if l.strip()]
                except:
                    pass
            
            lines = [l for l in lines if l != line_to_add]
            lines.append(line_to_add)
            
            try:
                parent_dir = os.path.dirname(filepath)
                if parent_dir and not os.path.exists(parent_dir):
                    os.makedirs(parent_dir)
                with open(filepath, "w") as f:
                    f.write("\n".join(lines) + "\n")
            except:
                pass

        if self.panel_dir:
            subfile = os.path.join(self.panel_dir, "isubscription.txt")
            update_file_lines(subfile, new_line)

        for fpath in self.get_all_playlists_files():
            update_file_lines(fpath, new_line)

        # Update XPortal if installed
        if self.is_xportal_installed():
            try:
                xportal_dir = "/etc/enigma2/XPortal"
                if not os.path.exists(xportal_dir):
                    os.makedirs(xportal_dir)
                xportal_txt = os.path.join(xportal_dir, "xtream.txt")
                
                xportal_line = "name=%s ; link=%s" % (label_val, new_line)
                
                xp_lines = []
                if os.path.exists(xportal_txt):
                    with open(xportal_txt, "r") as f:
                        xp_lines = [l.strip() for l in f.readlines() if l.strip()]
                
                xp_lines = [l for l in xp_lines if ("link=%s" % new_line) not in l]
                xp_lines.append(xportal_line)
                
                with open(xportal_txt, "w") as f:
                    f.write("\n".join(xp_lines) + "\n")
            except:
                pass

        # Update XtreamNew if installed
        if self.is_xtreamnew_installed():
            try:
                xtreamnew_file = "/etc/enigma2/xtreamnew/settings.json"
                if os.path.exists(xtreamnew_file):
                    with open(xtreamnew_file, "r") as f:
                        xn_data = json.load(f)

                    if "playlists" not in xn_data:
                        xn_data["playlists"] = []

                    new_playlist_item = {
                        "name": label_val,
                        "host": host_url,
                        "username": user_val,
                        "password": pass_val,
                        "output": "ts",
                        "portal_type": "xtream",
                        "mac": ""
                    }

                    # Remove existing entries with identical host and username to prevent duplicates
                    xn_data["playlists"] = [
                        p for p in xn_data["playlists"] 
                        if not (p.get("host") == host_url and p.get("username") == user_val)
                    ]
                    xn_data["playlists"].append(new_playlist_item)

                    with open(xtreamnew_file, "w") as f:
                        json.dump(xn_data, f, indent=4)
            except:
                pass

        # Update playlist labels on UI
        self["playlists"].setText(self.get_playlists_dirs())
        self["panel_path"].setText("Saved successfully in available plugins playlists")

    def label_changed(self, config_element):
        key = config_element.value
        if key in self.SERVER_MAPPING:
            url, user, pwd = self.SERVER_MAPPING[key]
            self.url.setValue(url)
            if key == "custom":
                self.username.setValue(user)
                self.password.setValue(pwd)

        self.refresh_config()

    def refresh_config(self):
        self.clist = [
            getConfigListEntry("Label:", self.label),
            getConfigListEntry("URL:", self.url),
            getConfigListEntry("Port:", self.port),
            getConfigListEntry("Username:", self.username),
            getConfigListEntry("Password:", self.password),
        ]
        self["config"].l.setList(self.clist)
        self["config"].setCurrentIndex(0)

    def find_panel_dir(self):
        search_roots = ["/media/hdd", "/media/mmc"]
        try:
            search_roots += [
                os.path.join("/media", d)
                for d in os.listdir("/media")
                if d.startswith("usb")
            ]
        except:
            pass

        for root in search_roots:
            path = os.path.join(root, "ElieSatPanel", "panel_dir.cfg")
            if os.path.exists(path):
                folder = os.path.dirname(path)
                subfile = os.path.join(folder, "isubscription.txt")
                if not os.path.exists(subfile):
                    try:
                        open(subfile, "w").close()
                    except:
                        pass
                return folder

        # Fallback to internal storage path if no mounted storage device exists
        fallback_dir = "/etc/enigma2/ElieSatPanel"
        subfile = os.path.join(fallback_dir, "isubscription.txt")
        try:
            if not os.path.exists(fallback_dir):
                os.makedirs(fallback_dir)
            if not os.path.exists(subfile):
                open(subfile, "w").close()
        except:
            pass

        return fallback_dir

    def show_isubscription_path(self):
        self.session.open(IptvScreen)
