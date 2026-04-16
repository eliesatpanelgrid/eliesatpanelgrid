#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import os
import re
import gettext
from enigma import (
    eListboxPythonMultiContent,
    gFont,
    RT_HALIGN_LEFT,
    RT_VALIGN_CENTER,
    loadPNG,
    getDesktop,
    ePoint
)

from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from Components.MultiContent import (
    MultiContentEntryText,
    MultiContentEntryPixmapAlphaTest,
)
from Components.Pixmap import Pixmap
from Components.PluginComponent import plugins
from Components.PluginList import PluginEntryComponent
from Components.Sources.List import List

from Screens.Screen import Screen
from Plugins.Plugin import PluginDescriptor

from Plugins.Extensions.ElieSatPanelGrid.menus.Helpers import (
    get_local_ip,
    check_internet,
    get_image_name,
    get_python_version,
    get_storage_info,
    get_ram_info,
)
from Plugins.Extensions.ElieSatPanelGrid.__init__ import Version
_ = gettext.gettext

def getDesktopSize():
    s = getDesktop(0).size()
    return (s.width(), s.height())

def isFHD():
    return getDesktopSize()[0] == 1920

def isHD():
    w = getDesktopSize()[0]
    return 1280 <= w < 1920


class Uninstaller(Screen):
    def __init__(self, session, plugin_path=None):
        self.session = session
        if plugin_path is None:
            plugin_path = "/usr/lib/enigma2/python/Plugins/Extensions/"
        self.plugin_path = plugin_path
        self.skin_path = plugin_path

        self.pluginlist = plugins.getPlugins(PluginDescriptor.WHERE_PLUGINMENU)
        self.list = [PluginEntryComponent(plugin) for plugin in self.pluginlist]
        self.list_new = []

        for plugin_data in self.list:
            start, name, desc, icon = plugin_data
            if 'PluginsPanel' in name:
                continue
            self.list_new.append((
                start,
                name[7],
                desc[7],
                icon[5],
                '0',
                '0'
            ))
        self.list = self.list_new
        print('[wall-e]: Plugin count:', len(self.list))

        self.posi = []
        skincontent = ''

        if isFHD():
            posx, posy = 300, 220

            for x in range(24):
                if x % 6 == 0 and x != 0:
                    posx = 300
                    posy += 180  # increased row spacing

                self.posi.append((posx, posy))

                skincontent += f'''
                <widget name="zeile{x}" position="{posx},{posy}" size="180,80" scale="1" alphatest="blend" />
                <widget name="name{x}" position="{posx},{posy+110}" size="180,40"
                    font="Regular;24" halign="center" valign="center"
                    foregroundColor="#E6BE3A" backgroundColor="#000000" transparent="1" />
                '''

                posx += 240

            self.skin = f'''
            <screen name="Uninstaller" position="0,0" size="1920,1080" backgroundColor="transparent" flags="wfNoBorder" title="Uninstaller">

                <ePixmap position="0,0" zPosition="-1" size="1920,1080"
                    pixmap="/usr/lib/enigma2/python/Plugins/Extensions/ElieSatPanelGrid/assets/background/panel_bg.jpg"/>

                <eLabel position="0,0" size="1920,130" zPosition="10" backgroundColor="#000000" />

                <eLabel text="● Plugin Browser"
                    position="350,0" size="1400,50" zPosition="11"
                    font="Bold;32" halign="left" valign="center"
                    foregroundColor="#E6BE3A" backgroundColor="#000000"
                    transparent="0" />

                <widget name="info" position="0,120" size="1920,60"
                    valign="center" halign="center" zPosition="10"
                    foregroundColor="#E6BE3A"
                    backgroundColor="#000000"
                    font="Bold;32"
                    transparent="0" />

                <widget name="disc" position="0,940" size="1920,60"
                    valign="center" halign="center" zPosition="10"
                    foregroundColor="#E6BE3A"
                    backgroundColor="#000000"
                    font="Bold;32"
                    transparent="0" />

                {skincontent}

                <eLabel position="0,1075" size="480,5" backgroundColor="red"/>
                <widget name="red" position="0,1000" size="480,75" font="Bold;32"
                    halign="center" valign="center" text="Remove"
                    foregroundColor="#E6BE3A" backgroundColor="#000000"/>

                <eLabel position="480,1075" size="480,5" backgroundColor="green"/>
                <widget name="green" position="480,1000" size="480,75" font="Bold;32"
                    halign="center" valign="center" text="-"
                    foregroundColor="#E6BE3A" backgroundColor="#000000"/>

                <eLabel position="960,1075" size="480,5" backgroundColor="#E6BE3A"/>
                <widget name="yellow" position="960,1000" size="480,75" font="Bold;32"
                    halign="center" valign="center" text="-"
                    foregroundColor="#E6BE3A" backgroundColor="#000000"/>

                <eLabel position="1440,1075" size="480,5" backgroundColor="blue"/>
                <widget name="blue" position="1440,1000" size="480,75" font="Bold;32"
                    halign="center" valign="center" text="-"
                    foregroundColor="#E6BE3A" backgroundColor="#000000"/>

                <eLabel position="0,130" size="80,870" zPosition="10" backgroundColor="#000000" />
                <eLabel position="1840,130" size="80,870" zPosition="10" backgroundColor="#000000" />

                <widget name="left_bar"
                    position="10,160" size="60,760" zPosition="20"
                    font="Regular;26" halign="center"
                    foregroundColor="#E6BE3A" backgroundColor="#000000" />

                <widget name="right_bar"
                    position="1850,160" size="60,760" zPosition="20"
                    font="Regular;26" halign="center"
                    foregroundColor="#E6BE3A" backgroundColor="#000000" />

                <widget source="global.CurrentTime" render="Label"
                    position="1350,50" size="500,35" zPosition="12"
                    font="Bold;32" halign="center"
                    foregroundColor="#E6BE3A" transparent="1">
                    <convert type="ClockToText">Format %A %d %B</convert>
                </widget>

                <widget source="global.CurrentTime" render="Label"
                    position="1350,90" size="500,35" zPosition="12"
                    font="Bold;32" halign="center"
                    foregroundColor="#E6BE3A" transparent="1">
                    <convert type="ClockToText">Format %H:%M:%S</convert>
                </widget>

            </screen>
            '''
        else:
            posx, posy = 10, 60

            for x in range(20):
                if x % 5 == 0 and x != 0:
                    posx = 10
                    posy += 80

                self.posi.append((posx, posy))
                skincontent += f'<widget name="zeile{x}" position="{posx},{posy}" size="150,50" scale="1" alphatest="blend" />'
                posx += 160

            self.skin = f'''
            <screen name="Uninstaller" position="center,center" size="610,455" title="">
                <widget name="info" position="0,2" size="610,24"
                    valign="center" halign="center"
                    font="Regular;24" foregroundColor="#E6BE3A" transparent="1" />
                <widget name="disc" position="0,378" size="610,40"
                    valign="center" halign="center"
                    font="Regular;19" foregroundColor="#E6BE3A" transparent="1" />
                {skincontent}
            </screen>
            '''

        Screen.__init__(self, session)

        self['actions'] = ActionMap(
            ['OkCancelActions', 'DirectionActions'],
            {
                'cancel': self.exit,
                'ok': self.ok,
                'left': self.left,
                'right': self.right,
                'up': self.up,
                'down': self.down
            },
            -1
        )

        self['info'] = Label('')
        self['disc'] = Label('')

        self.items_per_page = 24 if isFHD() else 20

        for x in range(self.items_per_page):
            self['zeile' + str(x)] = Pixmap()
            self['zeile' + str(x)].hide()
            if isFHD():
                self['name' + str(x)] = Label('')

        self.achsex = 0
        self.page = 0
        self.total_pages = (len(self.list) + self.items_per_page - 1) // self.items_per_page
        self.onFirstExecBegin.append(self._onFirstExecBegin)

        self["left_bar"] = Label("\n".join(list("Version " + Version)))
        self["right_bar"] = Label("\n".join(list("By ElieSat")))

        self["red"] = Label(_("Stop"))
        self["green"] = Label(_("Install available"))
        self["yellow"] = Label(_("Show not available"))
        self["blue"] = Label(_("Rescan deps"))

    def paintnew(self, a, b):
        start_index = self.page * self.items_per_page
        end_index = min(start_index + self.items_per_page, len(self.list))

        normal_size = (180, 80)
        selected_size = (220, 120)

        for i in range(self.items_per_page):
            plugin_index = start_index + i

            if plugin_index < len(self.list):
                pixmap = self['zeile' + str(i)]
                pixmap.instance.setPixmap(self.list[plugin_index][3])

                if i == self.achsex:
                    x, y = self.posi[i]
                    w, h = selected_size
                    pixmap.resize(w, h)
                    pixmap.move(ePoint(x - (w - normal_size[0]) // 2, y - (h - normal_size[1]) // 2))
                else:
                    x, y = self.posi[i]
                    w, h = normal_size
                    pixmap.resize(w, h)
                    pixmap.move(ePoint(x, y))

                pixmap.show()

                if isFHD():
                    self['name' + str(i)].setText(self.list[plugin_index][1])
                    self['name' + str(i)].show()
            else:
                self['zeile' + str(i)].hide()
                if isFHD():
                    self['name' + str(i)].setText('')

        if start_index + self.achsex < len(self.list):
            plugin_name = self.list[start_index + self.achsex][1]
            plugin_desc = self.list[start_index + self.achsex][2]
            self['info'].setText(f"{plugin_name} (Showing {end_index}/{len(self.list)})")
            self['disc'].setText(plugin_desc)

    def up(self):
        columns = 6
        absolute_index = self.page * self.items_per_page + self.achsex
        if absolute_index - columns >= 0:
            absolute_index -= columns
            self.page = absolute_index // self.items_per_page
            self.achsex = absolute_index % self.items_per_page
            self._onFirstExecBegin()

    def down(self):
        columns = 6
        absolute_index = self.page * self.items_per_page + self.achsex
        if absolute_index + columns < len(self.list):
            absolute_index += columns
            self.page = absolute_index // self.items_per_page
            self.achsex = absolute_index % self.items_per_page
            self._onFirstExecBegin()

    def left(self):
        absolute_index = self.page * self.items_per_page + self.achsex
        if absolute_index > 0:
            absolute_index -= 1
            self.page = absolute_index // self.items_per_page
            self.achsex = absolute_index % self.items_per_page
            self._onFirstExecBegin()

    def right(self):
        absolute_index = self.page * self.items_per_page + self.achsex
        if absolute_index < len(self.list) - 1:
            absolute_index += 1
            self.page = absolute_index // self.items_per_page
            self.achsex = absolute_index % self.items_per_page
            self._onFirstExecBegin()

    def _onFirstExecBegin(self):
        self.paintnew(0, 0)
        self.setTitle('')

    def ok(self):
        index = self.page * self.items_per_page + self.achsex
        if index < len(self.list):
            plugin = self.list[index][0]
            plugin(session=self.session)

    def exit(self):
        self.close(self.session, '')
