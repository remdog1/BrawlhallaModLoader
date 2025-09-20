
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
import time
import py7zr
import zipfile
import traceback
import threading
import webbrowser
import requests
import subprocess
import multiprocessing

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
SERVER_NAME = "brawlhalla-mod-loader-ipc-socket" # Unique name for the socket

def InitWindowSetText(text):
    if getattr(sys, "frozen", False):
        try:
            import pyi_splash
            pyi_splash.update_text(text)
        except:
            pass

def InitWindowSetProgress(progress):
    if getattr(sys, "frozen", False):
        try:
            import pyi_splash
            # Simple progress update with percentage
            pyi_splash.update_progress(progress)
            pyi_splash.update_text(f"Loading... {progress:3d}%")
        except:
            pass

def InitWindowClose():
    if getattr(sys, "frozen", False):
        try:
            import pyi_splash
            pyi_splash.close()
        except:
            pass

def TerminateApp(exitId=0):
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
    modsPath = os.path.join(os.getcwd(), "Mods")
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
            socket.waitForReadyRead(1000)
            data = socket.readAll().data().decode('utf-8')
            socket.disconnectFromServer()
            if data:
                # The data will be the file path from the command line
                for file in data.splitlines():
                    if file:
                        self.fileImport(file)
            # Bring window to front
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
                # Update progress dialog with debug info for better user feedback
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
                self.mods.addMod(gameVersion=modData.get("gameVersion", ""), name=modData.get("name", ""), author=modData.get("author", ""), version=modData.get("version", ""), description=modData.get("description", ""), tags=modData.get("tags", []), previewsPaths=modData.get("previewsPaths", []), hash=modData.get("hash", ""), platform=modData.get("platform", ""), installed=modData.get("installed", False), currentVersion=modData.get("currentVersion", False), modFileExist=modData.get("modFileExist", False), modPath=modData.get("modPath", ""), modCachePath=modData.get("modCachePath", ""), dateAdded=modData.get("dateAdded", 0.0))
            self.setModsScreen()
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

    def showInformation(self):
        self.buttonsDialog.setTitle("About")
        string = TextFormatter.table([["Product:", PROGRAM_NAME], ["Version:", VERSION], ["GitHub tag:", GIT_VERSION or "None"], ["Status:", 'Beta' if PRERELEASE else 'Release'], ["Core version:", CORE_VERSION], ["Homepage:", f"<url=\"{GITHUB}/{REPO}\">{GITHUB}/{REPO}</url>"], [None, f"<url=\"{GAMEBANANA}\">{GAMEBANANA}</url>"], ["Author:", "I_FabrizioG_I"], ["Contacts:", "Discord: I_FabrizioG_I#8111"], [None, "VK: vk/fabriziog"]], newLine=False)
        self.buttonsDialog.setContent(TextFormatter.format(string, 11))
        self.buttonsDialog.setButtons([("Ok", self.buttonsDialog.hide)])
        self.buttonsDialog.show()

    def installMod(self):
        if self.mods.selectedModButton is not None:
            modClass = self.mods.selectedModButton.modClass
            self.controller.getModConflict(modClass.hash)

    def uninstallMod(self):
        if self.mods.selectedModButton is not None:
            modClass = self.mods.selectedModButton.modClass
            self.controller.uninstallMod(modClass.hash)

    def reinstallMod(self, mod_hash=None):
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
        if os.path.abspath(filePath).startswith(os.path.abspath(self.modsPath)):
            # File is already in Mods folder, just try to install it if it's a .bmod
            if filePath.endswith(".bmod") and self.controllerIsReady:
                self._autoInstallBmodFile(filePath)
            return
        fileName = os.path.split(filePath)[1]
        fileNameSplit = os.path.splitext(fileName)
        copied_files = []
        
        if fileNameSplit[1] == ".zip":
            with zipfile.ZipFile(filePath) as modZip:
                for file in modZip.namelist():
                    if file.endswith((".bmod", ".wem", ".bnk", ".bin")):
                        modZip.extract(file, self.modsPath)
                        copied_files.append(os.path.join(self.modsPath, file))
        else:
            if os.path.exists(os.path.join(self.modsPath, fileName)):
                i = 1
                while os.path.exists(os.path.join(self.modsPath, f"{fileNameSplit[0]} ({i}){fileNameSplit[1]}")):
                    i += 1
                fileName = f"{fileNameSplit[0]} ({i}){fileNameSplit[1]}"
            with open(filePath, "rb") as outsideMod:
                with open(os.path.join(self.modsPath, fileName), "wb") as insideMod:
                    insideMod.write(outsideMod.read())
            copied_files.append(os.path.join(self.modsPath, fileName))
        
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
        data = url.split(":", 1)[1].strip("/")
        splitData = data.split(",")
        if len(splitData) == 3:
            tag, modId, dlId = data.split(",")
            zipUrl = f"http://gamebanana.com/dl/{dlId}"
        else:
            zipUrl = ""
            return
        archivePath = os.path.join(self.modsPath, "_mod.archive")
        self.progressDialog.setMaximum(100)
        self.progressDialog.setTitle("Download mod")
        self.progressDialog.setContent("")
        self.progressDialog.show()
        QApplication.processEvents()
        try:
            with requests.get(zipUrl, stream=True) as r:
                r.raise_for_status()
                with open(archivePath, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            with open(archivePath, "rb") as file:
                _signature = file.read(3)
                if _signature.startswith(b"7z"):
                    with py7zr.SevenZipFile(archivePath) as mod7z:
                        for file in mod7z.getnames():
                            if file.endswith((".bmod", ".wem", ".bnk", ".bin")):
                                self.progressDialog.setContent(f"Extract: '{file}'")
                                QApplication.processEvents()
                                mod7z.extract(self.modsPath, [file])
                elif _signature.startswith(b"Rar"):
                    with rarfile.RarFile(archivePath) as modRar:
                        for file in modRar.namelist():
                            if file.endswith((".bmod", ".wem", ".bnk", ".bin")):
                                self.progressDialog.setContent(f"Extract: '{file}'")
                                QApplication.processEvents()
                                modRar.extract(file, self.modsPath)
                elif _signature.startswith(b"PK"):
                    with zipfile.ZipFile(archivePath) as modZip:
                        for file in modZip.namelist():
                            if file.endswith((".bmod", ".wem", ".bnk", ".bin")):
                                self.progressDialog.setContent(f"Extract: '{file}'")
                                QApplication.processEvents()
                                modZip.extract(file, self.modsPath)
            self.reloadMods()
            self.progressDialog.hide()
        except Exception as e:
            self.showError("Download error:", str(e))
        finally:
            if os.path.exists(archivePath):
                os.remove(archivePath)

def RunApp():
    # --- Single Instance Logic ---
    socket = QLocalSocket()
    socket.connectToServer(SERVER_NAME)
    # If connection is successful, another instance is running
    if socket.waitForConnected(500):
        # Send command line arguments (file path) to the running instance
        args = '\n'.join(sys.argv[1:]).encode('utf-8')
        socket.write(args)
        socket.waitForBytesWritten(1000)
        socket.disconnectFromServer()
        # Exit this new instance
        sys.exit(0)
    # --- End of Single Instance Logic ---

    if sys.platform == "win32":
        from core.core.windows import check_associations, register_associations
        if not check_associations():
            register_associations()
            # Don't return here - continue with app startup

    app = QApplication(sys.argv)
    
    # Update splash screen with initial progress
    InitWindowSetText("Initializing Brawlhalla Mod Loader...")
    InitWindowSetProgress(10)
    
    window = ModLoader()

    # --- Server setup for the first instance ---
    server = QLocalServer()
    server.newConnection.connect(window.handleNewInstance)
    # If the server is already running (from a crashed instance), remove it
    QLocalServer.removeServer(SERVER_NAME)
    server.listen(SERVER_NAME)
    window.local_server = server
    # --- End of server setup ---

    font_db = QFontDatabase()
    font_db.addApplicationFont(":/fonts/resources/fonts/Exo 2/Exo2-SemiBold.ttf")
    font_db.addApplicationFont(":/fonts/resources/fonts/Roboto/Roboto-Black.ttf")
    # ... (rest of font loading)

    if len(sys.argv) > 1:
        for file in sys.argv[1:]:
            window.fileImport(file)

    window.show()
    exitId = app.exec()
    TerminateApp(exitId)

if __name__ == "__main__":
    RunApp()