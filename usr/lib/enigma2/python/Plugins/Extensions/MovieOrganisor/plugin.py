# Movie Organiser by Grog68 with python 3 only commits by me)

import glob
import os
from re import sub
from datetime import date, datetime, timedelta
from time import localtime, time, strftime, mktime, sleep

from enigma import eTimer, quitMainloop, getDesktop

from Components.ActionMap import ActionMap
from Components.config import config, configfile, ConfigSubsection, ConfigYesNo, ConfigSelection, ConfigClock, getConfigListEntry
from Components.ConfigList import ConfigListScreen
from Components.Sources.StaticText import StaticText
from Plugins.Plugin import PluginDescriptor
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Tools.Directories import resolveFilename, SCOPE_CURRENT_PLUGIN, SCOPE_CURRENT_SKIN, SCOPE_METADIR

config.plugins.movieorganisor = ConfigSubsection()
config.plugins.movieorganisor.mergenew = ConfigYesNo(default=True)
config.plugins.movieorganisor.renamenew = ConfigYesNo(default=False)
config.plugins.movieorganisor.recordingpath = ConfigSelection(default=config.movielist.videodirs.value[0], choices=config.movielist.videodirs.value)
config.plugins.movieorganisor.standby = ConfigYesNo(default=False)
config.plugins.movieorganisor.schedule = ConfigYesNo(default=False)
config.plugins.movieorganisor.scheduletime = ConfigClock(default=0)
config.plugins.movieorganisor.repeattype = ConfigSelection(default="hourly", choices=[
	("15minute", _("15 Minutes")),
	("halfhour", _("Half hour")),
	("hourly", _("Hourly")),
	("3hour", _("3 Hours")),
	("6hour", _("6 Hours"))
])

movieorganisorversion = "3.99"

def mk_esc(esc_chars):
	return lambda s: ("").join([ "\\" + c if c in esc_chars else c for c in s ])


esc = mk_esc('{}[]()<>+*_-!$&#\'." ')
autoMovieOrganisorTimer = None

def capwords(directory):
	capdirectory = (" ").join(s.capitalize() for s in directory.split())
	return capdirectory


def domovieorganisation():
	path = config.plugins.movieorganisor.recordingpath.value
	recordingnames = glob.glob(os.path.join(path, "*"))
	seriesarray = []
	filesarray = []
	directories = []
	for name in recordingnames:
		seriesname = ""
		names = os.path.basename(name)
		if config.plugins.movieorganisor.renamenew.value:
			new_name = names
			new_name = new_name.replace("New_ ", "")
			try:
				os.system("mv %s %s" % (os.path.join(path, esc(names)), os.path.join(path, esc(new_name))))
				print("[MovieOrganisor] Renames %s" % os.path.join(path, esc(names)))
				if new_name.endswith('meta'):
					os.system("sed -i 's/New\:\ //g' "+os.path.join(path, esc(new_name)))
			except Exception:
				print("[MovieOrganisor]error renaming %s" % os.path.join(path, esc(names)))
			names = new_name
		capdirectory = capwords(names)
		if os.path.isdir(os.path.join(path, names)) and names != capdirectory:
			try:
				os.rename(os.path.join(path, names), os.path.join(path, capdirectory))
				print("[MovieOrganisor] Renames %s" % os.path.join(path, names))
			except Exception:
				print("[MovieOrganisor] error renaming %s" % os.path.join(path, names))

		if os.path.isdir(os.path.join(path, capdirectory)):
			directories.append(capdirectory)
		elif names.endswith(".ts"):
			name1 = names.rsplit(".", 1)[0]
			filesarray.append(names)
			seriesname = name1.split(" - ", 2)[(-1)]
			if not config.plugins.movieorganisor.mergenew.value:
				seriesname = seriesname.replace("New_ ", "")
			if "New_" in seriesname:
				if seriesname.count("_") > 1:
					seriesname = seriesname.rsplit("_", 1)[0]
			elif "_" in seriesname:
				seriesname = seriesname.rsplit("_", 1)[0]
			seriesarray.append(seriesname)
		elif names.endswith(".stream"):
			name1 = names.rsplit(".", 1)[0]
			filesarray.append(names)
			seriesname = name1.split(" - ", 2)[1]
			seriesname = re.sub("S[0-9]* E[0-9]*", "", seriesname)
			seriesarray.append(seriesname)
		elif names.endswith(".mp4"):
			name1 = names.rsplit(".", 1)[0]
			filesarray.append(names)
			seriesname = name1.split("- ", 1)[0]
			if "_" in seriesname:
				seriesname = seriesname.rsplit("_", 1)[0]
			seriesarray.append(seriesname)

	series = set(seriesarray)
	for seriesn in series:
		capdirectory = capwords(seriesn)
		if not os.path.isdir(os.path.join(path, capdirectory)) and seriesarray.count(seriesn) > 1:
			os.makedirs(os.path.join(path, capdirectory))

	for name in filesarray:
		updatemeta = ""
		name1, nameext = name.rsplit(".", 1)
		file_mod_time = datetime.fromtimestamp(os.stat(os.path.join(path, name)).st_mtime)
		now = datetime.today()
		max_delay = timedelta(minutes=5)
		if now - file_mod_time > max_delay:
			seriesname = name1.split(" - ", 2)[(-1)]
			if nameext == "mp4":
				seriesname = name1.split("- ", 1)[0]
			elif nameext == "stream":
				seriesname = name1.split(" - ", 2)[1]
				seriesname = sub("S[0-9]* E[0-9]*", "", seriesname)
			if not config.plugins.movieorganisor.mergenew.value:
				seriesname = seriesname.replace("New_ ", "")
				if "_" in seriesname:
					updatemeta = seriesname.rsplit("_", 1)[1]
					seriesname = seriesname.rsplit("_", 1)[0]
			elif "New_" in seriesname:
				if seriesname.count("_") > 1:
					updatemeta = seriesname.rsplit("_", 1)[1]
					seriesname = seriesname.rsplit("_", 1)[0]
			elif "_" in seriesname:
				updatemeta = seriesname.rsplit("_", 1)[1]
				seriesname = seriesname.rsplit("_", 1)[0]
			meta = None
			if updatemeta.isdigit():
				newline = os.linesep
				metafilename = os.path.join(path, name + ".meta")
				if os.path.isfile(metafilename):
					f = open(os.path.join(path, name + ".meta"), "r")
					meta = f.readlines()
					f.close()
				if meta:
					poweroutage = " part " + str(int(updatemeta) + 1) + " (power outage)"
					if poweroutage not in meta[1]:
						newmeta = meta[1].rstrip() + poweroutage + newline
						meta[1] = newmeta
						f = open(os.path.join(path, name) + ".meta", "w")
						f.writelines(meta)
						f.close()
			capdirectory = capwords(seriesname)
			if os.path.isdir(os.path.join(path, capdirectory)):
				name1 = esc(name1)
				capdirectory = esc(capdirectory)
				os.system("mv %s %s" % (os.path.join(path, name1 + ".*"), os.path.join(path, capdirectory)))

	for directory in directories:
		fullpath = os.path.join(path, directory)
		files = os.listdir(fullpath)
		noofrecordings = 0
		recordingname = ""
		for filename in files:
			if filename.endswith(".ts") or filename.endswith(".stream") or filename.endswith(".mp4"):
				recordingname = esc(filename.rsplit(".", 1)[0])
				noofrecordings = noofrecordings + 1
		if noofrecordings == 1:
			directory1 = esc(directory)
			os.system("mv %s %s" % (os.path.join(path, directory1 + "/" + recordingname + ".*"), path))
		if noofrecordings < 2:
			if os.listdir(fullpath) == []:
				try:
					os.rmdir(fullpath)
					print("[MovieOrganisor] Removing %s" % fullpath)
				except Exception:
					print("[MovieOrganisor] error removing %s" % fullpath)
	return


def MovieOrganisorautostart(reason, session =  None, **kwargs):
	"""called with reason=1 to during /sbin/shutdown.sysvinit, with reason=0 at startup?"""
	global _session
	global autoMovieOrganisorTimer
	now = int(time())
	if reason == 0:
		print("[MovieOrganisor] AutoStart Enabled")
		if session is not None:
			_session = session
			if autoMovieOrganisorTimer is None:
				autoMovieOrganisorTimer = AutoMovieOrganisorTimer(session)
	else:
		print("[MovieOrganisor] Stop")
		autoMovieOrganisorTimer.stop()
	return


class AutoMovieOrganisorTimer:

	def __init__(self, session):
		global MovieOrganisorTime
		self.session = session
		self.movieorganisortimer = eTimer()
		self.movieorganisortimer.callback.append(self.MovieOrganisoronTimer)
		self.movieorganisoractivityTimer = eTimer()
		self.movieorganisoractivityTimer.timeout.get().append(self.movieorganisordatedelay)
		now = int(time())
		if config.plugins.movieorganisor.schedule.value:
			print("[MovieOrganisor] MovieOrganisor Schedule Enabled at ", strftime("%c", localtime(now)))
			if now > 1262304000:
				self.movieorganisordate()
			else:
				print("[MovieOrganisor] MovieOrganisor Time not yet set.")
				MovieOrganisorTime = 0
				self.movieorganisoractivityTimer.start(120)
		else:
			MovieOrganisorTime = 0
			print("[MovieOrganisor] MovieOrganisor Schedule Disabled at", strftime("(now = %c)", localtime(now)))
			self.movieorganisoractivityTimer.stop()

	def movieorganisordatedelay(self):
		self.movieorganisoractivityTimer.stop()
		self.movieorganisordate()

	def getMovieOrganisorTime(self):
		backupclock = config.plugins.movieorganisor.scheduletime.value
		nowt = time()
		now = localtime(nowt)
		return int(mktime((now.tm_year,
		 now.tm_mon,
		 now.tm_mday,
		 backupclock[0],
		 backupclock[1],
		 0,
		 now.tm_wday,
		 now.tm_yday,
		 now.tm_isdst)))

	def movieorganisordate(self, atLeast=0):
		global MovieOrganisorTime
		self.movieorganisortimer.stop()
		MovieOrganisorTime = self.getMovieOrganisorTime()
		print("MovieOrganisorTime is %d" % MovieOrganisorTime)
		now = int(time())
		if MovieOrganisorTime > 0:
			if MovieOrganisorTime < now + atLeast:
				if config.plugins.movieorganisor.repeattype.value == "15minute":
					while int(MovieOrganisorTime) - 30 < now:
						MovieOrganisorTime += 900

				elif config.plugins.movieorganisor.repeattype.value == "halfhour":
					while int(MovieOrganisorTime) - 30 < now:
						MovieOrganisorTime += 1800

				if config.plugins.movieorganisor.repeattype.value == "hourly":
					while int(MovieOrganisorTime) - 30 < now:
						MovieOrganisorTime += 3600

				elif config.plugins.movieorganisor.repeattype.value == "3hour":
					while int(MovieOrganisorTime) - 30 < now:
						MovieOrganisorTime += 10800

				elif config.plugins.movieorganisor.repeattype.value == "6hour":
					while int(MovieOrganisorTime) - 30 < now:
						MovieOrganisorTime += 21600

				elif config.plugins.movieorganisor.repeattype.value == "12hour":
					while int(MovieOrganisorTime) - 30 < now:
						MovieOrganisorTime += 43200

				elif config.plugins.movieorganisor.repeattype.value == "24hour":
					while int(MovieOrganisorTime) - 30 < now:
						MovieOrganisorTime += 86400

			next = MovieOrganisorTime - now
			self.movieorganisortimer.startLongTimer(next)
		else:
			MovieOrganisorTime = -1
		# print("[MovieOrganisor] MovieOrganisor Time set to", strftime("%c", localtime(MovieOrganisorTime), strftime("(now = %c)", localtime(now))))
		return MovieOrganisorTime

	def backupstop(self):
		self.movieorganisortimer.stop()

	def MovieOrganisoronTimer(self):
		self.movieorganisortimer.stop()
		now = int(time())
		wake = self.getMovieOrganisorTime()
		atLeast = 0
		if wake - now < 60:
			print("[MovieOrganisor] MovieOrganisor onTimer occured at", strftime("%c", localtime(now)))
			from Screens.Standby import inStandby
			if not inStandby or config.plugins.movieorganisor.standby.value:
				self.doMovieOrganisor(True)
			else:
				print("[MovieOrganisor] in Standby, so doing nothing", strftime("%c", localtime(now)))
				self.movieorganisordate(60)
		else:
			print("[MovieOrganisor] Where are not close enough", strftime("%c", localtime(now)))
			self.movieorganisordate(60)

	def doMovieOrganisor(self, answer):
		now = int(time())
		print("[MovieOrganisor] Running MovieOrganisor", strftime("%c", localtime(now)))
		self.timer = eTimer()
		self.timer.callback.append(self.go())
		self.timer.start(500, 1)

	def go(session):
		global MovieOrganisorTime
		domovieorganisation()
		now = int(time())
		if config.plugins.movieorganisor.schedule.value:
			if autoMovieOrganisorTimer is not None:
				print("[MovieOrganisor] MovieOrganisor Schedule Enabled at", strftime("%c", localtime(now)))
				autoMovieOrganisorTimer.movieorganisordate()
		elif autoMovieOrganisorTimer is not None:
			MovieOrganisorTime = 0
			print("[MovieOrganisor] MovieOrganisor Schedule Disabled at", strftime("%c", localtime(now)))
			autoMovieOrganisorTimer.backupstop()
		return


class MovieOrganisorSetupScreen(Screen, ConfigListScreen):
	skin = """
	<screen position="c-25%,e-75%" size="50%,50%" title="Movie Organsior setup">
		<widget source="key_red" render="Label" position="12%,e-18%" size="15%,8%" font="Regular;30" foregroundColor="key_text" halign="center" valign="center" backgroundColor="key_red" />
		<widget source="key_green" render="Label" position="32%,e-18%" size="15%,8%"  font="Regular;30"  foregroundColor="key_text" halign="center" valign="center" backgroundColor="key_green" />
		<widget source="key_yellow" render="Label" position="52%,e-18%" size="15%,8%"  font="Regular;30"  foregroundColor="key_text" halign="center" valign="center" backgroundColor="key_yellow" />
		<widget source="key_blue" render="Label" position="72%,e-18%" size="15%,8%"  font="Regular;30"   foregroundColor="key_text" halign="center" valign="center" backgroundColor="key_blue" />
		<widget name="config" position="c-40%,e-90%" size="80%,50%" font="Regular;25" />
		<widget name="new_version" render="Label" position="10%,e-45%" size="80%,20%" font="Regular;30" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
		<widget name="sig" render="Label" position="10%,e-5%" size="80%,5%" font="Regular;21" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
	</screen>"""

	def __init__(self, session):
		global movieupdatecheckurl
		global new_version
		global new_version1
		global new_version_check
		Screen.__init__(self, session)
		Screen.setTitle(self, _("Movie Organisor Setup (Final version)"))
		timenow = time()
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))
		self["key_yellow"] = StaticText(_("Run now"))
		self["key_blue"] = StaticText(_(""))
		self["sig"] = StaticText(_("Plugin by grog68"))
		self["actions"] = ActionMap(["SetupActions", "ColorActions", "MenuActions"], {
			"ok": self.keyGo, 
			"save": self.keyGo, 
			"cancel": self.keyCancel, 
			"green": self.keyGo, 
			"red": self.keyCancel, 
			"yellow": self.keySaveandGo, 
			"blue": self.keyGo,
			"menu": self.closeRecursive
		}, -2)
		self.onChangedEntry = []
		self.list = []
		ConfigListScreen.__init__(self, self.list, session=self.session, on_change=self.changedEntry)
		self.createSetup()


	def createSetup(self):
		self.list = []
		self.list.append(getConfigListEntry(_("Enabled"), config.plugins.movieorganisor.schedule))
		if config.plugins.movieorganisor.schedule.value:
			self.list.append(getConfigListEntry(_("Path of your recordings folder"), config.plugins.movieorganisor.recordingpath))
			self.list.append(getConfigListEntry(_("Run every"), config.plugins.movieorganisor.repeattype))
			self.list.append(getConfigListEntry(_("Remove the text 'New:' from recording names?"), config.plugins.movieorganisor.renamenew))
			if not config.plugins.movieorganisor.renamenew.value:
				self.list.append(getConfigListEntry(_("Keep recordings marked 'New:' separate?"), config.plugins.movieorganisor.mergenew))
			self.list.append(getConfigListEntry(_("Run while in standby"), config.plugins.movieorganisor.standby))
		self["config"].list = self.list
		self["config"].l.setList(self.list)

	def changedEntry(self):
		if self["config"].getCurrent()[0] == _("Enabled"):
			self.createSetup()
		if self["config"].getCurrent()[0] == _("Remove the text 'New:' from recording names?"):
			self.createSetup()
		for x in self.onChangedEntry:
			x()

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)

	def keyRight(self):
		ConfigListScreen.keyRight(self)

	def keyGo(self):
		for x in self["config"].list:
			x[1].save()
		configfile.save()
		autoMovieOrganisorTimer = AutoMovieOrganisorTimer(_session)
		self.close()

	def keyCancel(self):
		for x in self["config"].list:
			x[1].cancel()
		self.close()

	def keySaveandGo(self):
		for x in self["config"].list:
			x[1].save()
		configfile.save()
		domovieorganisation()
		self.close()


def main(session, **kwargs):
	session.open(MovieOrganisorSetupScreen)


def Plugins(**kwargs):
	plist = [PluginDescriptor(name=_("Movie Organisor"), description=_("Organise your series recordings into folders"), icon='plugin.png', where=PluginDescriptor.WHERE_PLUGINMENU, fnc=main)]
	plist.append(PluginDescriptor(name="Movie Organisor", description="Organise your series recordings into folders", where=PluginDescriptor.WHERE_SESSIONSTART, fnc=MovieOrganisorautostart))
	return plist
