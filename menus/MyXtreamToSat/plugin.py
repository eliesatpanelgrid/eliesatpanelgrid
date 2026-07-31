from Screens.ChannelSelection import ChannelSelectionBase
from Components.ServiceList import ServiceList
from Screens.Screen import Screen
from Plugins.Plugin import PluginDescriptor
from Components.ActionMap import ActionMap
from Components.Button import Button
from Components.ServiceEventTracker import ServiceEventTracker
from Components.MenuList import MenuList
from enigma import iPlayableService, iServiceInformation, eServiceCenter, eServiceReference, iFrontendInformation, eTimer, gRGB, eConsoleAppContainer, gFont
from Components.Label import Label
from ServiceReference import ServiceReference
from Screens.MessageBox import MessageBox
from Tools.Directories import fileExists
from twisted.web.client import getPage
from datetime import datetime
import json
import os

try:
	from urllib.parse import parse_qs, urlparse
except ImportError:
	from urlparse import parse_qs, urlparse

PLAYLIST_PATH = '/etc/enigma2/MyXtream/playlist.json'
CONFIG_PATH = '/etc/enigma2/MyXtream/playlists.txt'
LOG_PATH = '/tmp/MyXtreamToSat.log'
DEFAULT_PLAYER = "exteplayer3"
Ver = '1.0'

def trace_error():
	import sys
	import traceback
	try:
		traceback.print_exc(file=sys.stdout)
		traceback.print_exc(file=open(LOG_PATH, 'a'))
	except:
		pass

def log(data):
	now = datetime.now().strftime('%Y-%m-%d %H:%M')
	try:
		with open(LOG_PATH, 'a') as f:
			f.write(now + ' : ' + str(data) + '\r\n')
	except:
		pass

def parseColor(s):
	return gRGB(int(s[1:], 0x10))

def getPlaylist():
	if fileExists(PLAYLIST_PATH):
		with open(PLAYLIST_PATH, 'r') as f:
			try:
				return json.loads(f.read())
			except ValueError:
				trace_error()
	return None

class myxtreamtosat(Screen):

	def __init__(self, session):
		Screen.__init__(self, session)
		self.session = session
		self.__event_tracker = ServiceEventTracker(screen=self, eventmap={
			iPlayableService.evStart: self.__evStart,
			iPlayableService.evTunedIn: self.__evStart,
			iPlayableService.evEnd: self.__evEnd,
			iPlayableService.evStopped: self.__evEnd,
		})
		self.Timer = eTimer()
		try:
			self.Timer.callback.append(self.get_channel)
		except:
			self.Timer_conn = self.Timer.timeout.connect(self.get_channel)
		self.container = eConsoleAppContainer()
		self.ip_sat = False

	def kill_players(self):
		os.system("killall -9 exteplayer3 > /dev/null 2>&1")

	def current_channel(self, channel, lastservice):
		playlist = getPlaylist()
		if channel and playlist:
			for ch in playlist['playlist']:
				iptosat = ch['sref'] if 'sref' in ch else ch['channel'].strip()
				current_sref = str(ServiceReference(lastservice))
				
				if channel == iptosat or iptosat == current_sref:
					self.session.nav.stopService()
					self.kill_players()
					
					cmd = '{} "{}"'.format(DEFAULT_PLAYER, ch['url'])
					log("Playing stream: {}".format(cmd))
					self.container.execute(cmd)
					self.ip_sat = True
					return
		
		if self.ip_sat:
			self.kill_players()
			self.container.sendCtrlC()
			self.ip_sat = False

	def get_channel(self):
		service = self.session.nav.getCurrentService()
		if service:
			info = service.info()
			if info:
				FeInfo = service.frontendInfo()
				if FeInfo:
					SNR = FeInfo.getFrontendInfo(iFrontendInformation.signalQuality) / 655
					isCrypted = info.getInfo(iServiceInformation.sIsCrypted)
					if isCrypted and SNR > 10:
						lastservice = self.session.nav.getCurrentlyPlayingServiceReference()
						channel_name = ServiceReference(lastservice).getServiceName()
						self.current_channel(channel_name, lastservice)
					else:
						if self.ip_sat:
							self.kill_players()
							self.container.sendCtrlC()
							self.ip_sat = False

	def __evStart(self):
		self.Timer.start(1000)

	def __evEnd(self):
		self.Timer.stop()
		if self.ip_sat:
			self.kill_players()
			self.container.sendCtrlC()
			self.ip_sat = False

class AssignService(ChannelSelectionBase):

	skin = """<screen name="AssignService" position="0,0" size="1920,1080" backgroundColor="transparent" flags="wfNoBorder" title="MyXtreamToSat">
				<ePixmap position="0,0" zPosition="-1" size="1920,1080" pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/MyXtreamToSat/assets/background/panel_bg.jpg"/>
				<eLabel position="0,0" size="1920,130" zPosition="10" backgroundColor="#000000" />
				<eLabel text="● MyXtreamToSat" position="740,0" size="1400,50" zPosition="11" font="Bold;32" halign="left" valign="center" foregroundColor="#E6BE3A" backgroundColor="#000000" transparent="0" />

				<!-- Service & Category Lists -->
				<widget position="110,160" size="830,730" name="list" scrollbarMode="showOnDemand" />
				<widget position="980,160" size="830,730" name="list2" scrollbarMode="showOnDemand" />
				<widget name="status" position="1200,500" size="400,50" font="Bold;30" zPosition="12" halign="center" valign="center"/>
				<widget name="assign" position="110,910" size="1700,50" font="Bold;28" zPosition="12" halign="center" valign="center"/>

				<!-- Bottom buttons -->
				<eLabel position="0,1075" size="480,5" zPosition="2" backgroundColor="red" />
				<widget name="red" position="0,1000" size="480,75" zPosition="2" font="Bold;32" halign="center" valign="center" foregroundColor="#E6BE3A" backgroundColor="#000000" transparent="0" />

				<eLabel position="480,1075" size="480,5" zPosition="2" backgroundColor="green" />
				<widget name="green" position="480,1000" size="480,75" zPosition="2" font="Bold;32" halign="center" valign="center" foregroundColor="#E6BE3A" backgroundColor="#000000" transparent="0" />

				<eLabel position="960,1075" size="480,5" zPosition="2" backgroundColor="#E6BE3A" />
				<widget name="yellow" position="960,1000" size="480,75" zPosition="2" font="Bold;32" halign="center" valign="center" foregroundColor="#E6BE3A" backgroundColor="#000000" transparent="0" />

				<eLabel position="1440,1075" size="480,5" zPosition="2" backgroundColor="blue" />
				<widget name="blue" position="1440,1000" size="480,75" zPosition="2" font="Bold;32" halign="center" valign="center" foregroundColor="#E6BE3A" backgroundColor="#000000" transparent="0" />

				<!-- Side bars -->
				<eLabel position="0,130" size="80,870" zPosition="10" backgroundColor="#000000" />
				<eLabel position="1840,130" size="80,870" zPosition="10" backgroundColor="#000000" />
			</screen>"""

	def __init__(self, session, *args):
		self.session = session
		ChannelSelectionBase.__init__(self, session)
		self.bouquet_mark_edit = 0
		self["status"] = Label()
		self["assign"] = Label()
		self["red"] = Button(_("manage playlist"))
		self["green"] = Button(_("reception lists"))
		self["yellow"] = Button(_("-"))
		self["blue"] = Button(_("favourites"))

		self["ChannelSelectBaseActions"] = ActionMap(["IPtoSATActions"],
		{
			"cancel": self.exit,
			"ok": self.channelSelected,
			"left": self.left,
			"right": self.right,
			"down": self.moveDown,
			"up": self.moveUp,
			"red": self.openManagePlaylist,
			"green": self.showSatellites,
			"blue": self.showFavourites,
			"nextBouquet": self.chUP,
			"prevBouquet": self.chDOWN,
		}, -2)
		self.errortimer = eTimer()
		try:
			self.errortimer.callback.append(self.errorMessage)
		except:
			self.errortimer_conn = self.errortimer.timeout.connect(self.errorMessage)
		self.in_bouquets = False
		self.in_channels = False
		self.url = None
		self.channels = []
		self.categories = []
		self['list2'] = MenuList([])
		self.selectedList = self["list"]
		self.getUserData()
		self.onLayoutFinish.append(self.setModeTv)
		self.onShown.append(self.onWindowShow)

	def openManagePlaylist(self):
		self.session.open(EditPlaylist)

	def onWindowShow(self):
		self.onShown.remove(self.onWindowShow)
		try:
			self.disablelist2()
		except:
			pass

	def setModeTv(self):
		self.setTvMode()
		self.showFavourites()
		self.buildTitleString()

	def buildTitleString(self):
		titleStr = self.getTitle().replace('MyXtreamToSat - ', '')
		pos = titleStr.find(']')
		if pos == -1:
			pos = titleStr.find(')')
		if pos != -1:
			titleStr = titleStr[:pos + 1]
			Len = len(self.servicePath)
			if Len > 0:
				base_ref = self.servicePath[0]
				if Len > 1:
					end_ref = self.servicePath[Len - 1]
				else:
					end_ref = None
				nameStr = self.getServiceName(base_ref)
				titleStr += ' - ' + nameStr
				if end_ref is not None:
					if Len > 2:
						titleStr += '/../'
					else:
						titleStr += '/'
					nameStr = self.getServiceName(end_ref)
					titleStr += nameStr
				self.setTitle('MyXtreamToSat - ' + titleStr)

	def chUP(self):
		if self.selectedList == self["list"]:
			self.servicelist.instance.moveSelection(self.servicelist.instance.pageDown)
		elif self.selectedList == self["list2"]:
			instance = self["list2"].instance
			instance.moveSelection(instance.pageDown)

	def chDOWN(self):
		if self.selectedList == self["list"]:
			self.servicelist.instance.moveSelection(self.servicelist.instance.pageUp)
		elif self.selectedList == self["list2"]:
			instance = self["list2"].instance
			instance.moveSelection(instance.pageUp)

	def enablelist1(self):
		self["list"].instance.setSelectionEnable(1)

	def enablelist2(self):
		self["list2"].instance.setSelectionEnable(1)

	def disablelist1(self):
		self["list"].instance.setSelectionEnable(0)

	def disablelist2(self):
		self["list2"].instance.setSelectionEnable(0)

	def left(self):
		if self.selectedList == self["list2"]:
			self.selectedList = self["list"]
			self.enablelist1()
			self.disablelist2()
		self.resetWidget()

	def right(self):
		if self.selectedList.getCurrent():
			self.selectedList = self["list2"]
			self.enablelist2()
		self.resetWidget()

	def moveDown(self):
		if self.selectedList.getCurrent():
			instance = self.selectedList.instance
			instance.moveSelection(instance.moveDown)
		self.resetWidget()

	def moveUp(self):
		if self.selectedList.getCurrent():
			instance = self.selectedList.instance
			instance.moveSelection(instance.moveUp)
		self.resetWidget()

	def getUserData(self):
		if fileExists(CONFIG_PATH):
			try:
				with open(CONFIG_PATH, 'r') as f:
					content = f.read()
				
				target_line = ""
				for line in content.splitlines():
					if 'username=' in line and 'password=' in line:
						target_line = line.strip()
						break
				
				if target_line:
					if '://' in target_line:
						protocol, rest = target_line.split('://', 1)
						domain = rest.split('/')[0]
						self.host = "{}://{}".format(protocol, domain)
					else:
						self.host = "http://" + target_line.split('/')[0]
					
					parsed_url = urlparse(target_line)
					query_params = parse_qs(parsed_url.query)
					
					self.user = query_params.get('username', [''])[0]
					self.password = query_params.get('password', [''])[0]
					
					if self.host and self.user and self.password:
						self.url = '{}/player_api.php?username={}&password={}'.format(self.host, self.user, self.password)
						self.getCategories(self.url)
					else:
						raise ValueError("Missing parameters in URL")
				else:
					log('No valid URL line found in {}'.format(CONFIG_PATH))
					self.errortimer.start(200, True)
			except:
				trace_error()
				self.errortimer.start(200, True)
		else:
			log('{}, No such file or directory'.format(CONFIG_PATH))
			self.close(True)

	def errorMessage(self):
		self.session.openWithCallback(self.exit, MessageBox, _('Something is wrong in {}\nFull log in {}'.format(CONFIG_PATH, LOG_PATH)), MessageBox.TYPE_ERROR, timeout=10)

	def getCategories(self, url):
		url += '&action=get_live_categories'
		self.callAPI(url, self.getData)

	def channelSelected(self):
		if self.selectedList == self["list"]:
			ref = self.getCurrentSelection()
			if (ref.flags & 7) == 7:
				self.enterPath(ref)
				self.in_bouquets = True
		elif self.selectedList == self["list2"]:
			if self.url and not self.in_channels and len(self.categories) > 0:
				index = self['list2'].getSelectionIndex()
				cat_id = self.categories[index][1]
				url = self.url + '&action=get_live_streams&category_id=' + cat_id
				self.callAPI(url, self.getChannels)
			elif self.in_channels and len(self.channels) > 0:
				index = self['list2'].getSelectionIndex()
				xtream_channel = self.channels[index][0]
				stream_id = self.channels[index][1]
				sref = self.getSref()
				channel_name = ServiceReference(sref).getServiceName()
				self.addChannel(channel_name, stream_id, sref, xtream_channel)

	def addChannel(self, channel_name, stream_id, sref, xtream_channel):
		playlist = getPlaylist()
		if not playlist:
			playlist = {"playlist": []}
		
		if sref.startswith('1') and 'http' not in sref:
			url = '{}/{}/{}/{}'.format(self.host, self.user, self.password, stream_id)
			if not self.exists(sref, playlist):
				playlist['playlist'].append({'sref': sref, 'channel': channel_name, 'url': url})
				os.makedirs(os.path.dirname(PLAYLIST_PATH), exist_ok=True)
				with open(PLAYLIST_PATH, 'w') as f:
					json.dump(playlist, f, indent=4)
				text = channel_name + ' mapped successfully with ' + xtream_channel
				self.assignWidget("#008000", text)
			else:
				text = channel_name + ' already exists in playlist'
				self.assignWidget("#00ff2525", text)
		else:
			text = "Cannot assign channel to this service"
			self.assignWidget("#00ff2525", text)

	def exists(self, sref, playlist):
		try:
			refs = [ref['sref'] for ref in playlist['playlist']]
			return sref in refs
		except KeyError:
			return False

	def assignWidget(self, color, text):
		self['assign'].setText(text)
		self['assign'].instance.setForegroundColor(parseColor(color))

	def resetWidget(self):
		self['assign'].setText('')

	def getSref(self):
		ref = self.getCurrentSelection()
		return ref.toString()

	def callAPI(self, url, callback):
		self['list2'].hide()
		self["status"].show()
		self["status"].setText('Please wait ...')
		getPage(str.encode(url)).addCallback(callback).addErrback(self.error)

	def error(self, error=None):
		if error:
			log(error)
			self['list2'].hide()
			self["status"].show()
			self["status"].setText('Error!!')
			self.session.openWithCallback(self.exit, MessageBox, _('An Unexpected HTTP Error Occurred During The API Request !!'), MessageBox.TYPE_ERROR, timeout=10)

	def getData(self, data):
		lst = []
		js = json.loads(data)
		if js:
			for cat in js:
				lst.append((str(cat['category_name']), str(cat['category_id'])))
		self["status"].hide()
		self['list2'].show()
		self['list2'].l.setList(lst)
		self.categories = lst
		self.in_channels = False

	def getChannels(self, data):
		lst = []
		js = json.loads(data)
		if js:
			for ch in js:
				lst.append((str(ch['name']), str(ch['stream_id'])))
		self["status"].hide()
		self['list2'].show()
		self['list2'].l.setList(lst)
		self["list2"].moveToIndex(0)
		self.channels = lst
		self.in_channels = True

	def exit(self, ret=None):
		if ret:
			self.close(True)
		if self.selectedList == self['list'] and self.in_bouquets:
			self.showFavourites()
			self.in_bouquets = False
		elif self.selectedList == self["list2"] and self.in_channels:
			self.getCategories(self.url)
		else:
			self.close(True)

class EditPlaylist(Screen):

	skin = """<screen name="EditPlaylist" position="0,0" size="1920,1080" backgroundColor="transparent" flags="wfNoBorder" title="Manage Playlist">
				<ePixmap position="0,0" zPosition="-1" size="1920,1080" pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/MyXtreamToSat/assets/background/panel_bg.jpg"/>
				<eLabel position="0,0" size="1920,130" zPosition="10" backgroundColor="#000000" />
				<eLabel text="● Manage Playlist" position="740,0" size="1400,50" zPosition="11" font="Bold;32" halign="left" valign="center" foregroundColor="#E6BE3A" backgroundColor="#000000" transparent="0" />

				<!-- Channel List -->
				<widget position="110,160" size="1700,740" name="list" scrollbarMode="showOnDemand"/>
				<widget name="status" position="460,480" size="1000,60" font="Bold;32" zPosition="12" halign="center" valign="center"/>

				<!-- Bottom buttons -->
				<eLabel position="0,1075" size="480,5" zPosition="2" backgroundColor="red" />
				<widget name="red" position="0,1000" size="480,75" zPosition="2" font="Bold;32" halign="center" valign="center" foregroundColor="#E6BE3A" backgroundColor="#000000" transparent="0" />

				<eLabel position="480,1075" size="480,5" zPosition="2" backgroundColor="green" />
				<widget name="green" position="480,1000" size="480,75" zPosition="2" font="Bold;32" halign="center" valign="center" foregroundColor="#E6BE3A" backgroundColor="#000000" transparent="0" />

				<eLabel position="960,1075" size="480,5" zPosition="2" backgroundColor="#E6BE3A" />
				<widget name="yellow" position="960,1000" size="480,75" zPosition="2" font="Bold;32" halign="center" valign="center" foregroundColor="#E6BE3A" backgroundColor="#000000" transparent="0" />

				<eLabel position="1440,1075" size="480,5" zPosition="2" backgroundColor="blue" />
				<widget name="blue" position="1440,1000" size="480,75" zPosition="2" font="Bold;32" halign="center" valign="center" foregroundColor="#E6BE3A" backgroundColor="#000000" transparent="0" />

				<!-- Side bars -->
				<eLabel position="0,130" size="80,870" zPosition="10" backgroundColor="#000000" />
				<eLabel position="1840,130" size="80,870" zPosition="10" backgroundColor="#000000" />
			</screen>"""

	def __init__(self, session, *args):
		self.session = session
		Screen.__init__(self, session)
		self["status"] = Label()
		self["red"] = Button(_("reset all"))
		self["green"] = Button(_("remove selected"))
		self["yellow"] = Button(_("-"))
		self["blue"] = Button(_("-"))
		self['list'] = MenuList([])

		self["IptosatActions"] = ActionMap(["IPtoSATActions"],
		{
			"cancel": self.exit,
			"red": self.keyRed,
			"green": self.keyGreen,
		}, -2)
		self.channels = []
		self.playlist = getPlaylist()
		self.iniMenu()

	def iniMenu(self):
		if self.playlist:
			lst = []
			for channel in self.playlist['playlist']:
				try:
					lst.append(str(channel['channel']))
				except KeyError:
					pass
			if len(lst) > 0:
				self['list'].l.setList(sorted(lst))
				self.channels = sorted(lst)
				self.hideShowButtons()
				self["status"].hide()
			else:
				self.hideShowButtons(True)
				self["status"].setText('Playlist is empty')
				self["status"].show()
				self['list'].hide()
		else:
			self.hideShowButtons(True)
			self["status"].setText('Failed to load Playlist')
			self["status"].show()
			self['list'].hide()

	def keyGreen(self):
		if self.playlist and len(self.channels) > 0:
			index = self['list'].getSelectionIndex()
			playlist = sorted(self.playlist['playlist'], key=lambda k: k.get('channel', ''))
			del playlist[index]
			self.playlist['playlist'] = playlist
			with open(PLAYLIST_PATH, 'w') as f:
				json.dump(self.playlist, f, indent=4)
		self.iniMenu()

	def hideShowButtons(self, hide=False):
		if hide:
			self["red"].hide()
			self["green"].hide()
		else:
			self["red"].show()
			self["green"].show()

	def keyRed(self):
		if self.playlist and len(self.channels) > 0:
			self.playlist['playlist'] = []
			with open(PLAYLIST_PATH, 'w') as f:
				json.dump(self.playlist, f, indent=4)
		self.iniMenu()

	def exit(self, ret=None):
		self.close(True)

def autostart(reason, **kwargs):
	if reason == 0 and "session" in kwargs:
		if fileExists('/usr/bin/exteplayer3'):
			myxtreamtosat(kwargs["session"])
		else:
			log("Cannot start MyXtreamToSat, /usr/bin/exteplayer3 not found")

def Plugins(**kwargs):
	return [
		PluginDescriptor(
			name="MyXtreamToSat",
			description="MyXtreamToSat Service Assign {}".format(Ver),
			where=PluginDescriptor.WHERE_SESSIONSTART,
			fnc=autostart
		)
	]
