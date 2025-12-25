
'''
This is the main entry point for the Brawlhalla Mod Loader application.
It handles application startup, single-instance checking, and the main event loop.
'''
import os
import sys

# If the application is run as a bundle, change the working directory to the executable's directory
if getattr(sys, 'frozen', False):
    os.chdir(os.path.dirname(sys.executable))

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'core')))

# Import required modules
import time
import zipfile
import traceback
import threading
import webbrowser
import requests
import subprocess
import multiprocessing

# Suppress SSL warnings when verification is disabled (for users with corporate proxies/antivirus)
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Try to import py7zr, but don't fail if it's missing
try:
    import py7zr
    PY7ZR_AVAILABLE = True
except ImportError:
    PY7ZR_AVAILABLE = False

# (https://stackoverflow.com/questions/9144724/unknown-encoding-idna-in-python-requests)
import encodings.idna

from typing import List

JAVA_FOUND = False
try:
    import core.core as core
    from core.core import NotificationType, Notification, Environment, CORE_VERSION
    from core.core.controller.controller import Controller
    import core.core.ffdec
    JAVA_FOUND = True
except ImportError as e:
    NotificationType = Notification = Environment = CORE_VERSION = None
    if hasattr(e, 'msg') and e.msg == "Java not found!":
        JAVA_FOUND = False
    else:
        sys.excepthook(*sys.exc_info())


SUPPORT_URL = "https://www.patreon.com/bhmodloader"
PROGRAM_NAME = "Brawlhalla Mod Loader 2025 Beta"

# Use a FIXED server name so all instances can find each other
# This is critical for single-instance detection to work properly
SERVER_NAME = "brawlhalla-mod-loader-ipc-socket"

# Module-level variable to store the server instance
# This ensures it stays alive throughout the application lifetime
_local_server = None

def InitWindowSetText(text):
    try:
        from custom_splash import update_splash_text
        update_splash_text(text)
    except:
        pass

def InitWindowSetProgress(progress):
    try:
        from custom_splash import update_splash_progress
        update_splash_progress(progress)
    except:
        pass

def InitWindowClose():
    try:
        from custom_splash import close_splash
        close_splash()
    except:
        pass

def TerminateApp(exitId=0):
    # Release mutex before exiting
    try:
        from single_instance import release_mutex
        release_mutex()
    except:
        pass
    
    for proc in multiprocessing.active_children():
        try:
            proc.kill()
        except:
            pass
    sys.exit(exitId)


class ImportQueue:
    def __init__(self):
        self.urlQueue = []
        self.signalUrl = None
        self._readUrlQueue = False
        self.fileQueue = []
        self.signalFile = None
        self._readFileQueue = False

    def setUrlSignal(self, signalUrl):
        self.signalUrl = signalUrl

    def _emitUrl(self):
        while True:
            try:
                if self.signalUrl is None:
                    time.sleep(0.1)
                else:
                    self.signalUrl.emit()
                    break
            except:
                time.sleep(0.1)

    def addUrl(self, url):
        self.urlQueue.append(url)
        if not self._readUrlQueue:
            threading.Thread(target=self._emitUrl).start()

    def iterUrl(self):
        self._readUrlQueue = True
        while self.urlQueue:
            yield self.urlQueue.pop(0)
        self._readUrlQueue = False

    def setFileSignal(self, signalFile):
        self.signalFile = signalFile

    def _emitFile(self):
        while True:
            try:
                if self.signalFile is None:
                    time.sleep(0.1)
                else:
                    self.signalFile.emit()
                    break
            except:
                time.sleep(0.1)

    def addFile(self, file):
        self.fileQueue.append(file)
        if not self._readFileQueue:
            threading.Thread(target=self._emitFile).start()

    def iterFile(self):
        self._readFileQueue = True
        while self.fileQueue:
            yield self.fileQueue.pop(0)
        self._readFileQueue = False


import ctypes
myappid = u'BrawlhallaModLoader.Remdog.1.0' # arbitrary string
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

from PySide6 import QtCore
from PySide6.QtCore import QSize, QTranslator, QLocale, QTimer, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtGui import QIcon, QFontDatabase
from PySide6.QtWidgets import QMainWindow, QApplication

from ui.ui_handler.window import Window
from ui.ui_handler.header import HeaderFrame
from ui.ui_handler.loading import Loading
from ui.ui_handler.mods import Mods
from ui.ui_handler.progressdialog import ProgressDialog
from ui.ui_handler.buttonsdialog import ButtonsDialog
from ui.ui_handler.acceptdialog import AcceptDialog

from ui.utils.layout import ClearFrame, AddToFrame
from ui.utils.version import GetLatest, GITHUB, REPO, VERSION, GIT_VERSION, PRERELEASE, GAMEBANANA
from ui.utils.textformater import TextFormatter
from ui.utils.mainthread import QExecMainThread

import ui.ui_sources.translate as translate

class ModLoader(QMainWindow):
    importQueue = ImportQueue()
    # Use executable directory when frozen, otherwise current working directory
    if getattr(sys, 'frozen', False):
        _base_path = os.path.dirname(sys.executable)
    else:
        _base_path = os.getcwd()
    modsPath = os.path.join(_base_path, "Mods")
    errors: List[Notification] = []
    app = None
    pendingBmodInstalls = []  # Queue for .bmod files to install when controller is ready

    def __init__(self):
        super().__init__()
        self.ui = Window()
        self.ui.setupUi(self)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        QExecMainThread.init(self)
        InitWindowSetText("Initializing UI...")
        InitWindowSetProgress(15)
        self.setWindowTitle(PROGRAM_NAME)
        self.setWindowIcon(QIcon(os.path.join(os.path.dirname(__file__), 'ui/ui_sources/resources/icons/App.ico')))
        self.loading = Loading()
        self.header = HeaderFrame(githubMethod=lambda: webbrowser.open(f"{GITHUB}/{REPO}"),
                                  supportMethod=lambda: webbrowser.open(SUPPORT_URL),
                                  infoMethod=self.showInformation)
        self.mods = Mods(installMethod=self.installMod,
                         uninstallMethod=self.uninstallMod,
                         reinstallMethod=self.reinstallMod,
                         deleteMethod=self.deleteMod,
                         reloadMethod=self.reloadMods,
                         openFolderMethod=self.openModsFolder)
        self.progressDialog = ProgressDialog(self)
        self.buttonsDialog = ButtonsDialog(self)
        self.acceptDialog = AcceptDialog(self)
        self.setLoadingScreen()
        self.setMinimumSize(QSize(850, 550))
        threading.Thread(target=self.checkNewVersion).start()
        self.queueUrlSignal.connect(self.queueUrl)
        self.queueFileSignal.connect(self.queueFile)
        self.importQueue.setUrlSignal(self.queueUrlSignal)
        self.importQueue.setFileSignal(self.queueFileSignal)
        self.setForeground()
        self.controller = None
        self.controllerIsReady = False
        if JAVA_FOUND:
            threading.Thread(target=self.runController).start()
            self.controllerGetterTimer = QTimer()
            self.controllerGetterTimer.timeout.connect(self.controllerHandler)
            self.controllerGetterTimer.start(10)
        else:
            message = ("Java not found!\n\nRecommended java: "
                       "<url=\"https://libericajdk.ru/pages/downloads/#/java-8-lts\">"
                       "https://libericajdk.ru/pages/downloads/#/java-8-lts</url>")
            self.showError("Fatal Error:", TextFormatter.format(message, 11), terminate=True)
        InitWindowClose()
        self.__class__.app = self

    def handleNewInstance(self):
        ''' Handles messages from new instances of the application. '''
        socket = self.local_server.nextPendingConnection()
        if socket:
            try:
                # Always bring window to front first
                self.setForeground()
                
                # Wait for data with increased timeout
                if socket.waitForReadyRead(3000):
                    data = socket.readAll().data().decode('utf-8')
                    socket.disconnectFromServer()
                    if data:
                        # Handle both file paths and URLs from command line
                        for arg in data.splitlines():
                            if arg:
                                arg = arg.strip().strip('"').strip("'")  # Sanitize the argument
                                if not arg:  # Skip empty strings after sanitization
                                    continue
                                try:
                                    # Handle cases where Windows passes the path with file:// protocol
                                    if arg.startswith("file://"):
                                        import urllib.parse
                                        arg = urllib.parse.unquote(arg[7:])  # Remove "file://" and decode
                                        # Remove leading slash if present (Windows paths)
                                        if arg.startswith("/") and len(arg) > 1 and arg[1] == ":":
                                            arg = arg[1:]
                                    
                                    # Normalize the path (but not URLs)
                                    if not arg.startswith(("http://", "https://", "bmod://")):
                                        arg = os.path.normpath(arg)
                                    
                                    # Check if it's a URL (GameBanana or bmod://)
                                    if arg.startswith("http://") or arg.startswith("https://") or arg.startswith("bmod://"):
                                        self.urlImport(arg)
                                    else:
                                        # Assume it's a file path
                                        self.fileImport(arg)
                                except Exception as e:
                                    print(f"Error handling argument '{arg}': {e}")
                                    import traceback
                                    traceback.print_exc()
                else:
                    # No data received, but connection was made - just bring window to front
                    socket.disconnectFromServer()
            except Exception as e:
                print(f"Error in handleNewInstance: {e}")
                import traceback
                traceback.print_exc()
                try:
                    socket.disconnectFromServer()
                except:
                    pass
            finally:
                # Always bring window to front when another instance tries to connect
                self.setForeground()

    def runController(self):
        try:
            self.loading.setText("Loading ModLoader Core")
            InitWindowSetProgress(10)
            self.controller = Controller()
            InitWindowSetProgress(25)
            self.controller.setModsPath(self.modsPath)
            InitWindowSetProgress(40)
            self.controller.reloadMods()
            InitWindowSetProgress(60)
            self.controller.getModsData()
            InitWindowSetProgress(80)
            self.controller.installBaseMod(f"{PROGRAM_NAME}: {VERSION}")
            InitWindowSetProgress(100)
            self.controllerIsReady = True
        except Exception:
            traceback.print_exc()

    def controllerHandler(self):
        if self.controller is None: return
        data = self.controller.getData()
        if data is None: return
        cmd = data[0]
        if cmd == Environment.Notification:
            notification: core.notifications.Notification = data[1]
            ntype = notification.notificationType
            if ntype == NotificationType.LoadingMod:
                modPath = notification.args[0]
                InitWindowSetText(f"Loading mod '{modPath or 'from cache'}'")
                # Add some progress indication for mod loading
                if hasattr(self, '_modLoadingProgress'):
                    self._modLoadingProgress += 5
                    InitWindowSetProgress(min(95, self._modLoadingProgress))
                else:
                    self._modLoadingProgress = 70
                    InitWindowSetProgress(70)
            elif ntype == NotificationType.ModElementsCount:
                modHash, count = notification.args
                self.progressDialog.setMaximum(count)
            elif ntype == NotificationType.ModConflictSearchInSwf:
                modHash, swfName = notification.args
                self.progressDialog.setContent(f"Searching in: {swfName}")
                self.progressDialog.addValue()
            elif ntype == NotificationType.ModConflictNotFound:
                modHash, = notification.args
                self.progressDialog.setValue(0)
                self.controller.installMod(modHash)
            elif ntype == NotificationType.ModConflict:
                modHash, modConflictHashes = notification.args
                self.acceptDialog.setTitle("Conflict mods!")
                content = "Mods:"
                for modConflictHash in modConflictHashes:
                    if modConflictHash in self.mods.mods:
                        mod = self.mods.mods[modConflictHash]
                        content += f"\n- {mod.name}"
                    else:
                        content += f"\n- UNKNOWN MOD: {modConflictHash}"
                        print("ERROR Один из установленных модов не найден в модлодере!")
                self.acceptDialog.setContent(content)
                self.acceptDialog.setAccept(lambda: [self.acceptDialog.hide(), self.controller.installMod(modHash)])
                self.acceptDialog.setCancel(self.acceptDialog.hide)
                self.progressDialog.hide()
                self.acceptDialog.show()
            elif ntype == NotificationType.InstallingModSwf:
                modHash, swfName = notification.args
                self.progressDialog.setContent(f"Open game file: {swfName}")
            elif ntype == NotificationType.InstallingModSwfSprite:
                modHash, sprite = notification.args
                self.progressDialog.setContent(f"Installing sprite: {sprite}")
                self.progressDialog.addValue()
            elif ntype == NotificationType.InstallingModSwfSound:
                modHash, sound = notification.args
                self.progressDialog.setContent(f"Installing sound: {sound}")
                self.progressDialog.addValue()
            elif ntype == NotificationType.InstallingModFile:
                modHash, fileName = notification.args
                self.progressDialog.setContent(f"Installing file: {fileName}")
                self.progressDialog.addValue()
            elif ntype == NotificationType.InstallingModFileCache:
                modHash, fileName = notification.args
                self.progressDialog.setContent(f"Caching file: {fileName}")
                self.progressDialog.addValue()
            elif ntype == NotificationType.InstallingModSwfScript:
                modHash, scriptName = notification.args
                self.progressDialog.setContent(f"Installing script: {scriptName}")
                self.progressDialog.addValue()
            elif ntype == NotificationType.InstallingModFinished:
                modHash = notification.args[0]
                if modHash in self.mods.mods:
                    modClass = self.mods.mods[modHash]
                    modClass.installed = True
                    self.mods.updateData()
                    if self.mods.selectedModButton:
                        self.mods.selectedModButton.updateData()
                self.progressDialog.hide()
                self.showErrorNotifications()
            elif ntype == NotificationType.Debug:
                debug_message = notification.args[0]
                # Only show useful progress messages to user
                if "Processing file" in debug_message or "Processing SWF" in debug_message or "Processing script" in debug_message or "Processing sound" in debug_message or "Processing sprite" in debug_message:
                    self.progressDialog.setContent(debug_message)
            elif ntype == NotificationType.UninstallingModSwf:
                modHash, swfName = notification.args
                self.progressDialog.setContent(swfName)
            elif ntype == NotificationType.UninstallingModSwfSprite:
                modHash, sprite = notification.args
                self.progressDialog.setContent(sprite)
                self.progressDialog.addValue()
            elif ntype == NotificationType.UninstallingModSwfSound:
                modHash, sprite = notification.args
                self.progressDialog.setContent(sprite)
                self.progressDialog.addValue()
            elif ntype == NotificationType.UninstallingModFile:
                modHash, fileName = notification.args
                self.progressDialog.setContent(fileName)
                self.progressDialog.addValue()
            elif ntype == NotificationType.UninstallingModFinished:
                modHash = notification.args[0]
                modClass = self.mods.mods[modHash]
                modClass.installed = False
                self.mods.updateData()
                self.mods.selectedModButton.updateData()
                self.progressDialog.hide()
                self.showErrorNotifications()
            elif ntype == NotificationType.DecompilingMod:
                modHash, = notification.args
                self.progressDialog.setContent("Decompiling...")
            elif ntype == NotificationType.DecompilingModFinished:
                self.progressDialog.hide()
                self.showError("Decompile Finished", "The mod has been decompiled successfully.")
            elif ntype in [NotificationType.CompileModSourcesSpriteHasNoSymbolclass, NotificationType.CompileModSourcesSpriteEmpty, NotificationType.CompileModSourcesSpriteNotFoundInFolder, NotificationType.CompileModSourcesUnsupportedCategory, NotificationType.CompileModSourcesUnknownFile, NotificationType.CompileModSourcesSaveError, NotificationType.LoadingModIsEmpty, NotificationType.InstallingModNotFoundFileElement, NotificationType.InstallingModNotFoundGameSwf, NotificationType.InstallingModSwfScriptError, NotificationType.InstallingModSwfSoundSymbolclassNotExist, NotificationType.InstallingModSoundNotExist, NotificationType.InstallingModSwfSpriteSymbolclassNotExist, NotificationType.InstallingModSpriteNotExist, NotificationType.UninstallingModSwfOriginalElementNotFound, NotificationType.UninstallingModSwfElementNotFound]:
                self.errors.append(notification)
        elif cmd == Environment.ReloadMods:
            self.mods.removeAllMods()
        elif cmd == Environment.GetModsData:
            for modData in data[1]:
                self.mods.addMod(gameVersion=modData.get("gameVersion", ""), name=modData.get("name", ""), author=modData.get("author", ""), version=modData.get("version", ""), description=modData.get("description", ""), tags=modData.get("tags", []), previewsPaths=modData.get("previewsPaths", []), hash=modData.get("hash", ""), platform=modData.get("platform", ""), installed=modData.get("installed", False), currentVersion=modData.get("currentVersion", False), modFileExist=modData.get("modFileExist", False), modPath=modData.get("modPath", ""), modCachePath=modData.get("modCachePath", ""), dateAdded=modData.get("dateAdded", 0.0), features=modData.get("features", []))
            self.setModsScreen()
            self.mods.reapply_custom_styling()
            self.showErrorNotifications()
            self.setAttribute(QtCore.Qt.WA_TranslucentBackground, False)
            self.setWindowFlags(QtCore.Qt.Window)
            self.show()
            InitWindowClose()
            
            # Process any pending .bmod installations
            self._processPendingBmodInstalls()
        elif cmd == Environment.GetModConflict:
            searching, modHash = data[1]
            if searching:
                modClass = self.mods.mods[modHash]
                self.progressDialog.setTitle(f"Searching conflicts '{modClass.name}'...")
                self.progressDialog.setContent("Searching...")
                self.progressDialog.show()
        elif cmd == Environment.InstallMod:
            installing, modHash = data[1]
            if installing:
                modClass = self.mods.mods[modHash]
                self.progressDialog.setTitle(f"Installing mod '{modClass.name}'...")
                self.progressDialog.setContent("Loading mod...")
                self.progressDialog.show()
        elif cmd == Environment.UninstallMod:
            uninstalling, modHash = data[1]
            if uninstalling:
                modClass = self.mods.mods[modHash]
                self.progressDialog.setTitle(f"Uninstalling mod '{modClass.name}'...")
                self.progressDialog.setContent("")
                self.progressDialog.show()
        elif cmd == Environment.DecompileMod:
            decompiling, modHash = data[1]
            if decompiling:
                modClass = self.mods.mods[modHash]
                self.progressDialog.setTitle(f"Decompiling mod '{modClass.name}'...")
                self.progressDialog.setContent("Starting...")
                self.progressDialog.show()
        else:
            print(f"Controller <- {str(data)}\n", end="")

    def showErrorNotifications(self):
        if self.errors:
            errors = []
            errorsNotifications = self.errors.copy()
            self.errors.clear()
            for notif in errorsNotifications:
                ntype = notif.notificationType
                string = ""
                if ntype == NotificationType.LoadingModIsEmpty: string = f"Mod '{notif.args[1]}' is empty"
                elif ntype == NotificationType.InstallingModNotFoundFileElement: string = f"Not found element '{notif.args[1]}' in bmod "
                elif ntype == NotificationType.InstallingModNotFoundGameSwf: string = f"Not found game file '{notif.args[1]}'"
                elif ntype == NotificationType.InstallingModSwfScriptError: string = f"Script '{notif.args[1]}' not installed"
                elif ntype == NotificationType.InstallingModSwfSoundSymbolclassNotExist: string = f"Not found sound '{notif.args[1]}' in '{notif.args[2]}'"
                elif ntype == NotificationType.InstallingModSoundNotExist: string = f"Not found sound '{notif.args[1]} ({notif.args[2]})' in '{notif.args[3]}'"
                elif ntype == NotificationType.InstallingModSwfSpriteSymbolclassNotExist: string = f"Not found sprite '{notif.args[1]}' in '{notif.args[2]}'"
                elif ntype == NotificationType.InstallingModSpriteNotExist: string = f"Not found sprite '{notif.args[1]} ({notif.args[2]})' in mod file"
                elif ntype == NotificationType.UninstallingModSwfOriginalElementNotFound: string = f"Not found orig element '{notif.args[1]}' in '{notif.args[2]}'"
                elif ntype == NotificationType.UninstallingModSwfElementNotFound: string = f"Not found mod element '{notif.args[1]}' in '{notif.args[2]}'"
                if string: errors.append(string)
                else: errors.append(repr(notif))
            if errors:
                string = ""
                for error in errors: string += f"{error}\n"
                self.showError("Errors:", string)

    @QExecMainThread
    def showError(self, title, content, action=None, terminate=False):
        self.buttonsDialog.setTitle(title)
        if self.acceptDialog.isShown(): self.acceptDialog.hide()
        if self.buttonsDialog.isShown(): self.buttonsDialog.hide()
        if self.progressDialog.isShown(): self.progressDialog.hide()
        if action is None: action = self.buttonsDialog.hide
        if terminate: action = TerminateApp
        self.buttonsDialog.setContent(content)
        self.buttonsDialog.setButtons([("Copy error", lambda: self.copyToClipboard(f"{title}\n\n{content}")), ("Ok", action)])
        self.buttonsDialog.show()

    def copyToClipboard(self, text):
        cb = QApplication.clipboard()
        cb.clear()
        cb.setText(text)

    def setLoadingScreen(self):
        ClearFrame(self.ui.mainFrame)
        AddToFrame(self.ui.mainFrame, self.loading)
        self.loading.setText("Loading mods sources...")
        InitWindowSetText("Preparing mod loader...")
        InitWindowSetProgress(15)

    def setModsScreen(self):
        ClearFrame(self.ui.mainFrame)
        AddToFrame(self.ui.mainFrame, self.header)
        AddToFrame(self.ui.mainFrame, self.mods)
        # Restore header background after UI refresh
        self.header.restore_background()

    def showInformation(self):
        self.buttonsDialog.setTitle("About")
        string = TextFormatter.table([["Product:", PROGRAM_NAME], ["Version:", VERSION], ["GitHub tag:", GIT_VERSION or "None"], ["Status:", 'Beta' if PRERELEASE else 'Release'], ["Core version:", CORE_VERSION], ["Homepage:", f"<url=\"{GITHUB}/{REPO}\">{GITHUB}/{REPO}</url>"], [None, f"<url=\"{GAMEBANANA}\">{GAMEBANANA}</url>"], ["Author:", "I_FabrizioG_I , Bucccket , LVLONE"], ["Contacts:", "Discord: Modhalla"]], newLine=False)
        self.buttonsDialog.setContent(TextFormatter.format(string, 11))
        self.buttonsDialog.setButtons([("Ok", self.buttonsDialog.hide)])
        self.buttonsDialog.show()

    def installMod(self):
        if not self.controllerIsReady:
            print("Controller not ready, cannot install mod")
            return
        if self.mods.selectedModButton is not None:
            modClass = self.mods.selectedModButton.modClass
            self.controller.getModConflict(modClass.hash)

    def uninstallMod(self):
        if not self.controllerIsReady:
            print("Controller not ready, cannot uninstall mod")
            return
        if self.mods.selectedModButton is not None:
            modClass = self.mods.selectedModButton.modClass
            self.controller.uninstallMod(modClass.hash)

    def reinstallMod(self, mod_hash=None):
        if not self.controllerIsReady:
            print("Controller not ready, cannot reinstall mod")
            return
        if mod_hash:
            self.controller.uninstallMod(mod_hash)
            self.controller.getModConflict(mod_hash)
        elif self.mods.selectedModButton is not None:
            modClass = self.mods.selectedModButton.modClass
            self.controller.uninstallMod(modClass.hash)
            self.controller.getModConflict(modClass.hash)

    def decompileMod(self):
        if self.mods.selectedModButton is not None:
            modClass = self.mods.selectedModButton.modClass
            self.controller.decompileMod(modClass.hash)

    def deleteMod(self):
        if self.mods.selectedModButton is not None:
            modClass = self.mods.selectedModButton.modClass
            self.buttonsDialog.deleteButtons()
            self.buttonsDialog.setTitle(f"Delete mod '{modClass.name}'")
            if modClass.installed:
                self.buttonsDialog.setContent("To delete mod, you need to uninstall it")
            else:
                self.buttonsDialog.setContent("")
                self.buttonsDialog.addButton("Delete", self._deleteMod)
            self.buttonsDialog.addButton("Cancel", self.buttonsDialog.hide)
            self.buttonsDialog.show()

    def reloadMods(self):
        if not getattr(self, "controllerIsReady", False):
            QTimer.singleShot(100, self.reloadMods)
            return
        self.setLoadingScreen()
        self.controller.reloadMods()
        self.controller.getModsData()

    def openModsFolder(self):
        os.startfile(self.modsPath)

    def _deleteMod(self):
        modClass = self.mods.selectedModButton.modClass
        modClass.modFileExist = False
        self.controller.deleteMod(modClass.hash)
        self.reloadMods()
        self.buttonsDialog.hide()

    def resizeEvent(self, event):
        self.progressDialog.onResize()
        self.acceptDialog.onResize()
        self.buttonsDialog.onResize()
        super().resizeEvent(event)

    @QExecMainThread
    def newVersion(self, url: str, fileUrl: str, version: str, body: str):
        self.buttonsDialog.setTitle(f"New version available '{version}'")
        self.buttonsDialog.setContent(TextFormatter.format(body, 11))
        self.buttonsDialog.deleteButtons()
        self.buttonsDialog.addButton("GO TO SITE", lambda: webbrowser.open(url))
        self.buttonsDialog.addButton("UPDATE", lambda: [self.buttonsDialog.hide(), self.updateApp(fileUrl, version)])
        self.buttonsDialog.addButton("CANCEL", self.buttonsDialog.hide)
        self.buttonsDialog.show()

    def handleUpdateApp(self, blocknum, blocksize, totalsize):
        readedData = blocknum * blocksize
        if totalsize > 0:
            downloadPercentage = int(readedData * 100 / totalsize)
            self.progressDialog.setValue(downloadPercentage)
            QApplication.processEvents()

    def updateApp(self, fileUrl: str, version: str):
        return None

    def checkNewVersion(self):
        latest = GetLatest()
        if latest is not None:
            newVersion, fileUrl, version, body = latest
            self.newVersion(newVersion, fileUrl, version, body)

    @QExecMainThread
    def setForeground(self):
        self.showNormal()
        self.activateWindow()
        self.raise_()
        try:
            if sys.platform.startswith("win"):
                import win32gui, win32com.client
                shell = win32com.client.Dispatch("WScript.Shell")
                shell.SendKeys('%')
                win32gui.SetForegroundWindow(self.winId())
        except:
            pass

    queueFileSignal = Signal()

    def queueFile(self):
        for file in self.importQueue.iterFile():
            self.fileImport(file)

    def fileImport(self, filePath: str):
        self.setForeground()
        
        # Validate and sanitize the file path
        if not filePath or not isinstance(filePath, str):
            print(f"❌ Invalid file path: {filePath}")
            return
        
        # Strip whitespace and quotes
        filePath = filePath.strip().strip('"').strip("'")
        
        # Handle URL-encoded paths (Windows sometimes passes these)
        try:
            import urllib.parse
            # Try to decode if it looks URL-encoded
            if '%' in filePath:
                filePath = urllib.parse.unquote(filePath)
        except:
            pass
        
        # Normalize the path (handle forward slashes, etc.)
        filePath = os.path.normpath(filePath)
        
        # Check if it's a URL instead of a file path
        if filePath.startswith(("http://", "https://", "bmod://")):
            self.urlImport(filePath)
            return
        
        # Validate that the path exists and is a file
        try:
            if not os.path.exists(filePath):
                print(f"File not found: {filePath}")
                self.showError("File Error", f"File not found:\n{filePath}\n\nPlease ensure the file exists and you have permission to access it.")
                return
            
            if not os.path.isfile(filePath):
                print(f"Path is not a file: {filePath}")
                self.showError("File Error", f"Path is not a file:\n{filePath}")
                return
            
            # Check if we can read the file
            if not os.access(filePath, os.R_OK):
                print(f"No read permission for file: {filePath}")
                self.showError("File Error", f"Cannot read file:\n{filePath}\n\nYou may not have permission to access this file.")
                return
        except PermissionError as e:
            print(f"Permission error accessing file: {filePath} - {e}")
            self.showError("File Error", f"Cannot access file:\n{filePath}\n\nPermission denied. Please ensure you have access to this file.")
            return
        except Exception as e:
            print(f"Error validating file: {filePath} - {e}")
            self.showError("File Error", f"Error accessing file:\n{filePath}\n\n{str(e)}")
            return
            
        if os.path.abspath(filePath).startswith(os.path.abspath(self.modsPath)):
            # File is already in Mods folder, just try to install it if it's a .bmod
            if filePath.endswith(".bmod") and self.controllerIsReady:
                self._autoInstallBmodFile(filePath)
            return
        fileName = os.path.split(filePath)[1]
        fileNameSplit = os.path.splitext(fileName)
        copied_files = []
        
        if fileNameSplit[1] == ".zip":
            try:
                with zipfile.ZipFile(filePath) as modZip:
                    for file in modZip.namelist():
                        if file.endswith((".bmod", ".wem", ".bnk", ".bin")):
                            modZip.extract(file, self.modsPath)
                            copied_files.append(os.path.join(self.modsPath, file))
            except zipfile.BadZipFile:
                self.showError("File Error", f"Invalid ZIP file:\n{filePath}")
                return
            except Exception as e:
                self.showError("File Error", f"Error reading ZIP file:\n{str(e)}")
                return
        else:
            try:
                # Ensure mods directory exists
                os.makedirs(self.modsPath, exist_ok=True)
                
                if os.path.exists(os.path.join(self.modsPath, fileName)):
                    i = 1
                    while os.path.exists(os.path.join(self.modsPath, f"{fileNameSplit[0]} ({i}){fileNameSplit[1]}")):
                        i += 1
                    fileName = f"{fileNameSplit[0]} ({i}){fileNameSplit[1]}"
                
                destination = os.path.join(self.modsPath, fileName)
                
                # Use shutil.copy2 to preserve metadata and handle permissions better
                import shutil
                try:
                    shutil.copy2(filePath, destination)
                except PermissionError:
                    # Fallback to manual copy if shutil fails
                    with open(filePath, "rb") as outsideMod:
                        with open(destination, "wb") as insideMod:
                            shutil.copyfileobj(outsideMod, insideMod)
                
                copied_files.append(destination)
            except PermissionError as e:
                self.showError("File Error", f"Cannot copy file to mods folder:\n{str(e)}\n\nPlease ensure you have write permission to:\n{self.modsPath}")
                return
            except Exception as e:
                self.showError("File Error", f"Error copying file:\n{str(e)}")
                import traceback
                traceback.print_exc()
                return
        
        # Reload mods to detect the new files
        self.reloadMods()
        
        # Auto-install .bmod files if Mod Loader is ready, or queue them if not
        if copied_files:
            for file_path in copied_files:
                if file_path.endswith(".bmod"):
                    if self.controllerIsReady:
                        self._autoInstallBmodFile(file_path)
                    else:
                        # Queue for installation when controller is ready
                        self.pendingBmodInstalls.append(file_path)

    def _autoInstallBmodFile(self, file_path: str):
        """Auto-install a .bmod file when it's imported"""
        try:
            # Find the mod by file path
            for mod_hash, mod_class in self.mods.mods.items():
                if mod_class.modPath == file_path:
                    # Show progress dialog
                    self.progressDialog.setTitle(f"Auto-installing mod '{mod_class.name}'...")
                    self.progressDialog.setContent("Installing mod...")
                    self.progressDialog.show()
                    
                    # Install the mod
                    self.controller.installMod(mod_hash)
                    break
        except Exception as e:
            print(f"Error auto-installing mod {file_path}: {e}")

    def _processPendingBmodInstalls(self):
        """Process any pending .bmod file installations"""
        if self.pendingBmodInstalls and self.controllerIsReady:
            for file_path in self.pendingBmodInstalls[:]:  # Copy list to avoid modification during iteration
                self._autoInstallBmodFile(file_path)
                self.pendingBmodInstalls.remove(file_path)

    queueUrlSignal = Signal()

    def queueUrl(self):
        for url in self.importQueue.iterUrl():
            self.urlImport(url)

    def urlImport(self, url: str):
        self.setForeground()
        
        # Handle both old bmod:// protocol and new GameBanana URLs
        if url.startswith("bmod://"):
            # Old protocol format: bmod://tag,modId,dlId
            data = url.split(":", 1)[1].strip("/")
            splitData = data.split(",")
            if len(splitData) == 3:
                tag, modId, dlId = data.split(",")
                zipUrl = f"https://gamebanana.com/dl/{dlId}"
            else:
                zipUrl = ""
                return
        elif "gamebanana.com/mods/" in url:
            # New GameBanana URL format: https://gamebanana.com/mods/610574
            try:
                # Extract mod ID from URL
                mod_id = url.split("/mods/")[1].split("/")[0].split("?")[0]
                
                # GameBanana's current download API format
                # We need to get the download URL from the mod page
                from bs4 import BeautifulSoup
                
                # Ensure URL is complete
                if not url.startswith("http://") and not url.startswith("https://"):
                    url = f"https://{url}"
                
                # Get the mod page to find the download link with retry logic
                max_retries = 3
                response = None
                ssl_warning_shown = False
                for attempt in range(max_retries):
                    try:
                        # First try with SSL verification enabled
                        response = requests.get(url, timeout=15, headers={
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                        }, verify=True)
                        response.raise_for_status()
                        break
                    except requests.exceptions.SSLError as ssl_error:
                        # SSL certificate verification failed - retry with verification disabled
                        if not ssl_warning_shown:
                            print(f"SSL certificate verification failed, retrying without verification: {ssl_error}")
                            ssl_warning_shown = True
                        try:
                            response = requests.get(url, timeout=15, headers={
                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                            }, verify=False)
                            response.raise_for_status()
                            break
                        except requests.exceptions.RequestException as retry_error:
                            if attempt == max_retries - 1:
                                raise Exception(f"Failed to fetch mod page: {str(retry_error)}")
                            time.sleep(1 * (attempt + 1))  # Exponential backoff
                    except requests.exceptions.RequestException as e:
                        if attempt == max_retries - 1:
                            raise
                        time.sleep(1 * (attempt + 1))  # Exponential backoff
                
                if not response:
                    raise Exception("Failed to fetch mod page after retries")
                
                # Parse HTML to find download link
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for download button or link with multiple strategies
                download_link = None
                
                # Strategy 1: Try different CSS selectors for download links
                selectors = [
                    'a[href*="/dl/"]',
                    'a[href*="download"]',
                    '.DownloadButton',
                    '.download-button',
                    '[data-download-url]',
                    'a[data-action="Download"]',
                    'button[data-action="Download"]',
                    '.DownloadButton a',
                    '[class*="download"] a'
                ]
                
                for selector in selectors:
                    elements = soup.select(selector)
                    for element in elements:
                        href = element.get('href') or element.get('data-download-url') or element.get('data-href')
                        if href and ('/dl/' in href or 'download' in href.lower()):
                            download_link = href
                            break
                    if download_link:
                        break
                
                # Strategy 2: Try to find download ID in data attributes or scripts
                if not download_link:
                    # Look for download ID in data attributes
                    download_elements = soup.find_all(attrs={'data-download-id': True})
                    if download_elements:
                        dl_id = download_elements[0].get('data-download-id')
                        if dl_id:
                            download_link = f"/dl/{dl_id}"
                    
                    # Look in JavaScript/data attributes
                    if not download_link:
                        scripts = soup.find_all('script')
                        for script in scripts:
                            if script.string and '/dl/' in script.string:
                                import re
                                match = re.search(r'/dl/(\d+)', script.string)
                                if match:
                                    download_link = f"/dl/{match.group(1)}"
                                    break
                
                # Construct the final download URL
                if download_link:
                    # Clean up the download link
                    download_link = download_link.strip()
                    
                    # Handle relative URLs
                    if download_link.startswith('/'):
                        zipUrl = f"https://gamebanana.com{download_link}"
                    # Handle absolute URLs
                    elif download_link.startswith('http://') or download_link.startswith('https://'):
                        zipUrl = download_link
                    # Handle partial paths (e.g., "dl/154")
                    elif download_link.startswith('dl/'):
                        zipUrl = f"https://gamebanana.com/{download_link}"
                    # Handle just the ID number
                    elif download_link.isdigit():
                        zipUrl = f"https://gamebanana.com/dl/{download_link}"
                    # Otherwise, try to construct from the link
                    else:
                        # Extract any numbers that might be download IDs
                        import re
                        numbers = re.findall(r'\d+', download_link)
                        if numbers:
                            zipUrl = f"https://gamebanana.com/dl/{numbers[-1]}"
                        else:
                            zipUrl = f"https://gamebanana.com/dl/{download_link}"
                else:
                    # Fallback: try GameBanana API endpoint
                    try:
                        api_url = f"https://gamebanana.com/apiv11/Mod/{mod_id}"
                        try:
                            api_response = requests.get(api_url, timeout=10, headers={
                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                            }, verify=True)
                        except requests.exceptions.SSLError:
                            # Retry without SSL verification if certificate check fails
                            api_response = requests.get(api_url, timeout=10, headers={
                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                            }, verify=False)
                        if api_response.status_code == 200:
                            api_data = api_response.json()
                            # Try to find download URL in API response
                            if 'Files' in api_data and len(api_data['Files']) > 0:
                                file_id = api_data['Files'][0].get('_idRow')
                                if file_id:
                                    zipUrl = f"https://gamebanana.com/dl/{file_id}"
                                else:
                                    raise Exception("No download ID found in API response")
                            else:
                                raise Exception("No files found in API response")
                        else:
                            raise Exception(f"API returned status {api_response.status_code}")
                    except Exception as api_error:
                        print(f"API fallback failed: {api_error}")
                        # Last resort: try to construct from mod ID (may not work)
                        zipUrl = f"https://gamebanana.com/dl/{mod_id}"
                
                # Validate the final URL
                if not zipUrl or not zipUrl.startswith('http'):
                    raise Exception(f"Invalid download URL constructed: {zipUrl}")
                
                print(f"GameBanana download URL: {zipUrl}")
                    
            except Exception as e:
                print(f"Error parsing GameBanana URL: {e}")
                import traceback
                traceback.print_exc()
                self.showError("URL Error", f"Could not parse GameBanana URL:\n{str(e)}\n\nPlease ensure the URL is correct and try again.")
                return
        else:
            self.showError("URL Error", "Unsupported URL format. Please use a GameBanana mod URL.")
            return
        archivePath = os.path.join(self.modsPath, "_mod.archive")
        self.progressDialog.setMaximum(100)
        self.progressDialog.setTitle("Download mod")
        self.progressDialog.setContent("")
        self.progressDialog.show()
        QApplication.processEvents()
        try:
            # Validate URL before downloading
            if not zipUrl or not zipUrl.startswith('http'):
                raise Exception(f"Invalid download URL: {zipUrl}")
            
            # Download with retry logic
            max_download_retries = 3
            download_success = False
            ssl_warning_shown = False
            for attempt in range(max_download_retries):
                try:
                    self.progressDialog.setContent(f"Downloading mod... (Attempt {attempt + 1}/{max_download_retries})")
                    QApplication.processEvents()
                    
                    # First try with SSL verification enabled
                    try:
                        r = requests.get(zipUrl, stream=True, timeout=30, headers={
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                        }, verify=True)
                        r.raise_for_status()
                    except requests.exceptions.SSLError as ssl_error:
                        # SSL certificate verification failed - retry with verification disabled
                        if not ssl_warning_shown:
                            print(f"SSL certificate verification failed, retrying without verification: {ssl_error}")
                            ssl_warning_shown = True
                        r = requests.get(zipUrl, stream=True, timeout=30, headers={
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                        }, verify=False)
                        r.raise_for_status()
                    
                    # Get content length for progress
                    total_size = int(r.headers.get('content-length', 0))
                    downloaded = 0
                    
                    with open(archivePath, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                                if total_size > 0:
                                    progress = int((downloaded / total_size) * 100)
                                    self.progressDialog.setValue(progress)
                                    QApplication.processEvents()
                    
                    r.close()
                    download_success = True
                    break
                except requests.exceptions.RequestException as e:
                    if attempt == max_download_retries - 1:
                        raise Exception(f"Download failed after {max_download_retries} attempts: {str(e)}")
                    time.sleep(2 * (attempt + 1))  # Exponential backoff
            
            if not download_success:
                raise Exception("Download failed after all retry attempts")
            
            # Track extracted files to ensure they're in the right place
            extracted_files = []
            
            with open(archivePath, "rb") as file:
                _signature = file.read(3)
                if _signature.startswith(b"7z"):
                    if PY7ZR_AVAILABLE:
                        with py7zr.SevenZipFile(archivePath) as mod7z:
                            for file_name in mod7z.getnames():
                                if file_name.endswith((".bmod", ".wem", ".bnk", ".bin")):
                                    self.progressDialog.setContent(f"Extract: '{file_name}'")
                                    QApplication.processEvents()
                                    # Extract to temp location first, then move to Mods folder
                                    import tempfile
                                    with tempfile.TemporaryDirectory() as temp_dir:
                                        mod7z.extract(temp_dir, [file_name])
                                        # Get just the filename (no path)
                                        base_name = os.path.basename(file_name)
                                        source_path = os.path.join(temp_dir, file_name)
                                        dest_path = os.path.join(self.modsPath, base_name)
                                        
                                        # Handle duplicate names
                                        if os.path.exists(dest_path):
                                            name, ext = os.path.splitext(base_name)
                                            counter = 1
                                            while os.path.exists(dest_path):
                                                dest_path = os.path.join(self.modsPath, f"{name} ({counter}){ext}")
                                                counter += 1
                                        
                                        if os.path.exists(source_path):
                                            import shutil
                                            shutil.move(source_path, dest_path)
                                            extracted_files.append(dest_path)
                                            print(f"✅ Extracted: {base_name} -> {dest_path}")
                    else:
                        self.progressDialog.setContent("7z files not supported - py7zr not installed")
                        QApplication.processEvents()
                        print("⚠️ Cannot extract 7z file - py7zr not available")
                        print("   Install with: pip install py7zr")
                elif _signature.startswith(b"Rar"):
                    with rarfile.RarFile(archivePath) as modRar:
                        for file_name in modRar.namelist():
                            if file_name.endswith((".bmod", ".wem", ".bnk", ".bin")):
                                self.progressDialog.setContent(f"Extract: '{file_name}'")
                                QApplication.processEvents()
                                # Extract to temp location first, then move to Mods folder
                                import tempfile
                                with tempfile.TemporaryDirectory() as temp_dir:
                                    modRar.extract(file_name, temp_dir)
                                    # Get just the filename (no path)
                                    base_name = os.path.basename(file_name)
                                    source_path = os.path.join(temp_dir, file_name)
                                    dest_path = os.path.join(self.modsPath, base_name)
                                    
                                    # Handle duplicate names
                                    if os.path.exists(dest_path):
                                        name, ext = os.path.splitext(base_name)
                                        counter = 1
                                        while os.path.exists(dest_path):
                                            dest_path = os.path.join(self.modsPath, f"{name} ({counter}){ext}")
                                            counter += 1
                                    
                                    if os.path.exists(source_path):
                                        import shutil
                                        shutil.move(source_path, dest_path)
                                        extracted_files.append(dest_path)
                                        print(f"✅ Extracted: {base_name} -> {dest_path}")
                elif _signature.startswith(b"PK"):
                    with zipfile.ZipFile(archivePath) as modZip:
                        for file_name in modZip.namelist():
                            if file_name.endswith((".bmod", ".wem", ".bnk", ".bin")):
                                self.progressDialog.setContent(f"Extract: '{file_name}'")
                                QApplication.processEvents()
                                # Extract directly to Mods folder, handling subdirectories
                                base_name = os.path.basename(file_name)
                                dest_path = os.path.join(self.modsPath, base_name)
                                
                                # Handle duplicate names
                                if os.path.exists(dest_path):
                                    name, ext = os.path.splitext(base_name)
                                    counter = 1
                                    while os.path.exists(dest_path):
                                        dest_path = os.path.join(self.modsPath, f"{name} ({counter}){ext}")
                                        counter += 1
                                
                                # Extract the file data and write directly to destination
                                file_data = modZip.read(file_name)
                                with open(dest_path, 'wb') as out_file:
                                    out_file.write(file_data)
                                
                                extracted_files.append(dest_path)
                                print(f"✅ Extracted: {base_name} -> {dest_path}")
            
            # Verify extraction succeeded
            if not extracted_files:
                raise Exception("No mod files (.bmod, .wem, .bnk, .bin) found in downloaded archive")
            
            # Log extracted files
            print(f"📦 Extracted {len(extracted_files)} file(s) to Mods folder:")
            for file_path in extracted_files:
                print(f"   - {os.path.basename(file_path)}")
            
            self.reloadMods()
            self.progressDialog.hide()
        except Exception as e:
            self.showError("Download error:", str(e))
        finally:
            if os.path.exists(archivePath):
                os.remove(archivePath)

def RunApp():
    # Update PyInstaller splash immediately if available
    try:
        import pyi_splash
        if pyi_splash.is_alive():
            pyi_splash.update_text("Initializing...")
    except:
        pass
    
    # --- Single Instance Logic ---
    # Use Windows Mutex for reliable single-instance detection
    # This works across all entry points (splash launcher, run.py, main.py)
    from single_instance import check_single_instance, send_args_to_existing_instance
    
    # Check if another instance is already running
    if check_single_instance():
        print(f"✓ Found existing instance, forwarding arguments...")
        # Send command line arguments to the existing instance
        # Retry logic is handled inside send_args_to_existing_instance
        args = sys.argv[1:] if len(sys.argv) > 1 else []
        if send_args_to_existing_instance(args):
            print(f"✓ Arguments forwarded successfully")
            # Exit this new instance immediately
            sys.exit(0)
        else:
            # If we couldn't send args, it might mean the server isn't ready yet
            # But we still shouldn't start a new instance - exit anyway
            print("Warning: Could not send arguments to existing instance, but mutex indicates instance is running")
            print("This may happen if the existing instance is still starting up.")
            sys.exit(0)
    
    print(f"✓ No existing instance found, starting new instance...")
    
    # --- End of Single Instance Logic ---
    
    # We are the first instance - set up server IMMEDIATELY
    # This must happen before creating the window so subsequent instances can detect us
    from PySide6.QtNetwork import QLocalServer
    from PySide6.QtWidgets import QApplication
    
    # Remove any stale server from crashed instances
    QLocalServer.removeServer(SERVER_NAME)
    
    # Create or reuse QApplication for server setup
    temp_app = QApplication.instance()
    if temp_app is None:
        temp_app = QApplication(sys.argv)
    
    # Set up server early - we'll connect it to the window later
    # Store in module-level variable to ensure it persists
    global _local_server
    _local_server = QLocalServer()
    # Set parent to QApplication to ensure it stays alive
    _local_server.setParent(temp_app)
    
    if not _local_server.listen(SERVER_NAME):
        # If listen fails, try removing and listening again
        QLocalServer.removeServer(SERVER_NAME)
        if not _local_server.listen(SERVER_NAME):
            print("Warning: Could not set up local server for single-instance check")
    
    # Process events to ensure server is ready
    temp_app.processEvents()
    # Give it a moment to fully initialize
    time.sleep(0.1)
    temp_app.processEvents()
    
    # Verify server is actually listening
    if not _local_server.isListening():
        print(f"Warning: Server failed to listen on {SERVER_NAME}")
        # Try one more time
        QLocalServer.removeServer(SERVER_NAME)
        if not _local_server.listen(SERVER_NAME):
            print(f"Error: Could not establish server on {SERVER_NAME}")
    else:
        print(f"✓ Single-instance server listening on {SERVER_NAME}")
    
    # Ensure server is ready before proceeding
    temp_app.processEvents()
    time.sleep(0.1)  # Brief pause to ensure server is fully ready
    temp_app.processEvents()
    
    # IMPORTANT: Register as latest IMMEDIATELY after server is ready
    # This ensures file associations point to the current executable
    if sys.platform == "win32":
        try:
            from core.core.windows import register_as_latest, update_protocol_handlers, is_admin
            current_exe = register_as_latest()
            print(f"✓ Registered current executable as latest: {current_exe}")
            
            # ALWAYS try to update protocol handlers to point to current executable
            # This is critical so .bmod files and GameBanana links use the correct exe
            # If we're running as admin, this will work. If not, user will see a message.
            if is_admin():
                print("Running as Administrator - updating file associations...")
                if update_protocol_handlers():
                    print("✓ Successfully updated protocol handlers!")
                else:
                    print("⚠ Failed to update protocol handlers")
            else:
                # Try anyway - might work if user has permissions
                print("Attempting to update protocol handlers (admin may be required)...")
                if update_protocol_handlers():
                    print("✓ Successfully updated protocol handlers!")
                else:
                    print("⚠ Could not update protocol handlers - admin privileges required")
                    print("  Please run the mod loader as Administrator to update file associations")
        except Exception as e:
            print(f"Warning: Could not register as latest: {e}")
            import traceback
            traceback.print_exc()

    # Update splash
    try:
        import pyi_splash
        if pyi_splash.is_alive():
            pyi_splash.update_text("Registering protocols...")
    except:
        pass

    if sys.platform == "win32":
        from core.core.windows import (
            check_associations, register_associations
        )
        # If associations don't exist, register them (requires admin)
        if not check_associations():
            register_associations()
            # Don't return here - continue with app startup

    # Update splash
    try:
        import pyi_splash
        if pyi_splash.is_alive():
            pyi_splash.update_text("Starting application...")
    except:
        pass

    # Create or reuse QApplication
    app = temp_app
    
    # Initialize splash screen right after QApplication
    try:
        from custom_splash import show_splash
        splash_screen = show_splash()
        if splash_screen:
            print("Splash screen initialized")
    except Exception as e:
        print(f"Failed to initialize splash screen: {e}")
        splash_screen = None
    
    # Update splash screen with initial progress
    InitWindowSetText("Initializing Brawlhalla Mod Loader...")
    InitWindowSetProgress(10)
    
    window = ModLoader()
    
    # Close PyInstaller splash if still open
    try:
        import pyi_splash
        if pyi_splash.is_alive():
            pyi_splash.close()
    except:
        pass
    
    # Close splash screen when main window is ready
    try:
        from custom_splash import close_splash
        close_splash()
    except:
        pass

    # --- Connect server to window handler ---
    # Server is already set up, just connect it to the window
    # Use the module-level server variable
    if _local_server:
        _local_server.newConnection.connect(window.handleNewInstance)
        window.local_server = _local_server
    else:
        print("Error: Local server not initialized!")
    # --- End of server setup ---

    font_db = QFontDatabase()
    font_db.addApplicationFont(":/fonts/resources/fonts/Exo 2/Exo2-SemiBold.ttf")
    font_db.addApplicationFont(":/fonts/resources/fonts/Roboto/Roboto-Black.ttf")
    eras_font_id = font_db.addApplicationFont(":/fonts/resources/fonts/eras/eras-itc-bold.ttf")

    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if arg:
                try:
                    # Sanitize the argument - handle Windows path quirks
                    arg = arg.strip().strip('"').strip("'")
                    
                    # Handle cases where Windows passes the path with file:// protocol
                    if arg.startswith("file://"):
                        import urllib.parse
                        arg = urllib.parse.unquote(arg[7:])  # Remove "file://" and decode
                        # Remove leading slash if present (Windows paths)
                        if arg.startswith("/") and len(arg) > 1 and arg[1] == ":":
                            arg = arg[1:]
                    
                    if not arg:  # Skip empty strings after sanitization
                        continue
                    
                    # Normalize the path
                    arg = os.path.normpath(arg) if not arg.startswith(("http://", "https://", "bmod://")) else arg
                    
                    # Check if it's a URL (GameBanana or bmod://)
                    if arg.startswith("http://") or arg.startswith("https://") or arg.startswith("bmod://"):
                        window.urlImport(arg)
                    else:
                        # Assume it's a file path
                        window.fileImport(arg)
                except Exception as e:
                    print(f"Error handling argument '{arg}': {e}")
                    import traceback
                    traceback.print_exc()
                    # Show user-friendly error
                    try:
                        window.showError("Import Error", f"Could not import file:\n{arg}\n\nError: {str(e)}")
                    except:
                        pass

    window.show()
    exitId = app.exec()
    TerminateApp(exitId)

if __name__ == "__main__":
    RunApp()