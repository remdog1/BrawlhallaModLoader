from typing import List, Dict
import os
import datetime

from PySide6.QtWidgets import QWidget, QPushButton, QVBoxLayout, QFrame, QLabel, QMenu
from PySide6.QtGui import QPixmap, QPaintEvent, QIcon, QCursor, QAction
from PySide6.QtCore import QSize, Qt, QPoint

from .modbutton import ModButton
from .modclass import ModClass

from ..ui_sources.ui_mods import Ui_Mods
from ..ui_sources.ui_mod_body import Ui_ModBody
from ..ui_sources.ui_mods_actions import Ui_ModsActions

from ..utils.buttons import AddButtonWidthToTexSize
from ..utils.layout import AddToFrame, ClearFrame
from ..utils.buttongroup import ButtonGroup


# TODO: Add gif or video in previews


class NavigateButton(ButtonGroup):
    def __init__(self, n, method):
        self.n = n

        self.previewNavigate = QPushButton()
        self.previewNavigate.setCursor(QCursor(Qt.PointingHandCursor))
        self.previewNavigate.setStyleSheet(u"background-color: #00000000;")
        icon = QIcon()
        icon.addFile(u":/icons/resources/icons/UnselectedCircle.png", QSize(), QIcon.Normal, QIcon.Off)
        icon.addFile(u":/icons/resources/icons/SelectedCircle.png", QSize(), QIcon.Active, QIcon.On)
        self.previewNavigate.setIcon(icon)
        self.previewNavigate.setIconSize(QSize(8, 8))
        self.previewNavigate.setCheckable(True)

        super().__init__("PreviewNavigate", self.previewNavigate, method=method)

        if self.n == 0:
            self.previewNavigate.setChecked(True)

    def pressed(self):
        if not self.button.isChecked():
            self.pressedMethod(self.n)

        for k in self.getSelfGroup():
            if k.button.isChecked():
                k.button.setChecked(False)

        return False

    def released(self):
        self.button.setChecked(True)

        return True

    def setActive(self):
        self.button.setChecked(True)

        for k in self.getSelfGroup():
            if k.button != self.button:
                k.button.setChecked(False)

    def remove(self):
        self.button.setParent(None)

    def addToFrame(self, frame):
        AddToFrame(frame, self.button)

    def hasParent(self):
        return bool(self.button.parent())


class Mods(QWidget):
    defaultPreview = ":/images/resources/images/DefaultPreview.png"
    cachePreviews: Dict[str, QPixmap] = {}
    selectedModButton: ModButton = None
    mods: Dict[str, ModClass] = {}
    modsButtons: List[ModButton] = []
    
    # Variables to track sorting state
    SORT_BY_NAME = "name"
    SORT_BY_DATE = "date"
    SORT_BY_SIZE = "size"
    sortBy = SORT_BY_NAME
    sortAscending = True

    def __init__(self, installMethod, uninstallMethod, reinstallMethod, deleteMethod, reloadMethod, openFolderMethod):
        super().__init__()

        self.ui = Ui_Mods()
        self.ui.setupUi(self)

        self.preview = None
        self.previews: List[QPixmap] = []
        self.previewsNavigate: List[NavigateButton] = [NavigateButton(n, self.setPreviewNum) for n in range(6)]
        self.previewRatio = 1

        bodyWidget = QWidget()
        self.body = Ui_ModBody()
        self.body.setupUi(bodyWidget)
        self.ui.scrollBody.setWidget(bodyWidget)

        self.ui.modBody.installEventFilter(self)
        self.modDescriptionsAndActionsLayout = self.body.modDescriptionsAndActions.layout()

        self.body.leftPreview.clicked.connect(self.leftPreview)
        self.body.rightPreview.clicked.connect(self.rightPreview)

        modsListFrame = QFrame()
        layout = QVBoxLayout(modsListFrame)
        layout.setSpacing(0)
        layout.setContentsMargins(2, 5, 2, 5)
        self.modsList = QFrame()
        self.modsList.setMaximumWidth(self.ui.modsList.maximumWidth())
        layout2 = QVBoxLayout(self.modsList)
        layout2.setSpacing(1)
        layout2.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.modsList, 0, Qt.AlignTop)
        self.ui.scrollModsList.setWidget(modsListFrame)

        self.resizeEvent = self.onResize
        self.origScrollModsListResizeEvent = self.ui.scrollModsList.resizeEvent
        self.ui.scrollModsList.resizeEvent = self.onModsListResize

        actionsWidget = QWidget()
        self.modsActions = Ui_ModsActions()
        self.modsActions.setupUi(actionsWidget)

        AddButtonWidthToTexSize(self.modsActions.webPage, 40)
        AddButtonWidthToTexSize(self.modsActions.install, 40)
        AddButtonWidthToTexSize(self.modsActions.uninstall, 40)
        AddButtonWidthToTexSize(self.modsActions.reinstall, 40)
        AddButtonWidthToTexSize(self.modsActions.update, 40)
        AddButtonWidthToTexSize(self.modsActions.deleteMod, 40)

        self.modsActions.install.clicked.connect(installMethod)
        self.modsActions.uninstall.clicked.connect(uninstallMethod)
        self.modsActions.reinstall.clicked.connect(reinstallMethod)
        self.modsActions.deleteMod.clicked.connect(deleteMethod)
        self.ui.reloadModsList.clicked.connect(reloadMethod)
        self.ui.openModsFolderButton.clicked.connect(openFolderMethod)
        
        # Connect sort button to menu
        self.ui.modsSortButton.clicked.connect(self.showSortMenu)

        self.ui.searchArea.textChanged.connect(self.searchEvent)

        AddToFrame(self.body.modActions, actionsWidget)

        self.setPreviewsPaths([self.defaultPreview])

    def loadPreview(self, pixmap: QPixmap):
        self.previewRatio = pixmap.width() / pixmap.height()
        self.body.modPreview.setPixmap(pixmap)
        self.onResize()

    def searchEvent(self, text):
        if not text:
            displayModButtons = self.modsButtons
        else:
            text = text.casefold()

            if len(text.split(" ")) == 1:
                text = f" {text}"

            displayModButtons = [
                modButton
                for modButton in self.modsButtons
                if any([
                    text in f" {modButton.modClass.name.lower()}",
                    text in f" {modButton.modClass.author.lower()}",
                    modButton.modClass.gameVersion.startswith(text.strip()),
                    any([tag.casefold().lower().startswith(text.strip()) for tag in modButton.modClass.tags])
                ])
            ]

        # Remove all mod buttons from the UI
        for modButton in self.modsButtons:
            modButton.remove()

        # Re-add the filtered mod buttons, maintaining current sort order
        for modButton in displayModButtons:
            modButton.restore(self.modsList)
        
        # If there's a selected mod in the filtered results, ensure it stays selected
        if self.selectedModButton is not None and self.selectedModButton in displayModButtons:
            self.selectedModButton.select()

    def onResize(self, *a):
        width = self.ui.scrollBody.width() - (7 if self.ui.scrollBody.verticalScrollBar().isVisible() else 0)
        imageHeight = self.ui.scrollBody.width() // self.previewRatio

        self.body.modPreview.setGeometry(0, 0, width, imageHeight)
        self.body.modPreviewInfo.setGeometry(0, 0, width, imageHeight)

        lMargin, tMargin, rMargin, bMargin = self.modDescriptionsAndActionsLayout.getContentsMargins()
        spacing = self.modDescriptionsAndActionsLayout.spacing()

        self.body.modPreviewFrame.setMinimumHeight(imageHeight)

        modDescriptionHeight = self.ui.modBody.height() - imageHeight - self.body.modTags.height() - \
                               self.body.modActions.height() - tMargin - bMargin - spacing * \
                               (self.modDescriptionsAndActionsLayout.count() - 1)

        modDescriptionDocumentHeight = self.body.modDescription.document().size().height()

        if modDescriptionDocumentHeight > modDescriptionHeight:
            self.body.modDescription.setMinimumHeight(modDescriptionDocumentHeight)
        else:
            self.body.modDescription.setMinimumHeight(modDescriptionHeight)

    def onModsListResize(self, event):
        for n in range(self.modsList.layout().count()):
            w = self.modsList.layout().takeAt(0).widget()
            w.onParentResize()
            self.modsList.layout().addWidget(w)

        self.origScrollModsListResizeEvent(event)

    def eventFilter(self, qobject, event):
        # if event.type() not in [QEvent.HoverMove, QEvent.PolishRequest, QEvent.Paint, QEvent.MouseMove]:
        #    print(event.type())

        if isinstance(event, QPaintEvent):
            self.onResize(event)

        return False

    def leftPreview(self):
        n = 0
        for preview in self.previews:
            if self.body.modPreview.pixmap().cacheKey() == preview.cacheKey():
                break
            else:
                n += 1

        if n == 0:
            self.setPreviewNum(len(self.previews) - 1)
        else:
            self.setPreviewNum(n - 1)

    def rightPreview(self):
        n = 0
        for preview in self.previews:
            if self.body.modPreview.pixmap().cacheKey() == preview.cacheKey():
                break
            else:
                n += 1

        if n == len(self.previews) - 1:
            self.setPreviewNum(0)
        else:
            self.setPreviewNum(n + 1)

    def cachePreview(self, path: str) -> QPixmap:
        if path not in self.cachePreviews:
            pixmap = QPixmap(path.replace("\\", "/"))
            self.cachePreviews[path] = pixmap
        else:
            pixmap = self.cachePreviews[path]

        return pixmap

    def setPreviewNum(self, n):
        if -1 < n < len(self.previews):
            self.previewsNavigate[n].setActive()
            self.loadPreview(self.previews[n])

    def setPreviewsPaths(self, paths: List[str]):
        self.previews.clear()

        for previewNavigate in self.previewsNavigate:
            if previewNavigate.hasParent():
                previewNavigate.remove()

        for n in range(len(paths)):
            self.previewsNavigate[n].addToFrame(self.body.previewsNavigateFrame)
            if n == 0:
                self.previewsNavigate[n].pressed()
                self.previewsNavigate[n].released()

        if not paths:
            paths = [self.defaultPreview]

        if len(paths) == 1:
            self.body.leftPreview.setMaximumWidth(0)
            self.body.rightPreview.setMaximumWidth(0)
        else:
            self.body.leftPreview.setMaximumWidth(30)
            self.body.rightPreview.setMaximumWidth(30)

        for n, path in enumerate(paths):
            pixmap = self.cachePreview(path)
            self.previews.append(pixmap)

        self.loadPreview(self.previews[0])

    def updateData(self):
        modClass = self.selectedModButton.modClass

        self.modsActions.webPage.setParent(None)
        self.modsActions.install.setParent(None)
        self.modsActions.uninstall.setParent(None)
        self.modsActions.reinstall.setParent(None)
        self.modsActions.update.setParent(None)
        self.modsActions.deleteMod.setParent(None)

        if modClass.installed:
            if modClass.modFileExist:
                AddToFrame(self.modsActions.mainFrame, self.modsActions.reinstall)
            AddToFrame(self.modsActions.mainFrame, self.modsActions.uninstall)
        elif modClass.modFileExist:
            AddToFrame(self.modsActions.mainFrame, self.modsActions.install)

        #if modClass.modFileExist:
        AddToFrame(self.modsActions.mainFrame, self.modsActions.deleteMod)

        self.setPreviewsPaths(modClass.previewsPaths)
        self.body.modName.setText(modClass.name)
        self.body.modSource.setText("Source: " + str(modClass.platform))
        self.body.modVersion.setText("Version: " + str(modClass.version))
        self.body.modDescription.setText(modClass.description)
        self.body.modTags.setText("Tags: " + ", ".join(modClass.tags))

    def selectMod(self, modClass: ModClass):
        for modButton in self.modsButtons:
            if modButton.modClass == modClass:
                self.selectedModButton = modButton

        self.updateData()

    def addModButton(self, modClass: ModClass):
        modButton = ModButton(modClass=modClass,
                              method=self.selectMod)

        self.modsButtons.append(modButton)
        AddToFrame(self.modsList, modButton)

        if not self.selectedModButton:
            modButton.select()

    def addMod(self,
               gameVersion: str,
               name: str,
               author: str,
               version: str,
               description: str,
               tags: List[str],
               previewsPaths: List[str],
               hash: str,
               platform: str,
               installed: bool,
               currentVersion: bool,
               modFileExist: bool):

        for path in previewsPaths:
            self.cachePreview(path)

        mod = ModClass(gameVersion,
                       name,
                       author,
                       version,
                       description,
                       tags,
                       previewsPaths,
                       hash,
                       platform,
                       installed,
                       currentVersion,
                       modFileExist)

        self.mods[hash] = mod
        self.addModButton(mod)
        
        # Apply current sort when a new mod is added
        if len(self.modsButtons) > 1:  # Only sort if there's more than one mod
            self.sortMods(self.sortBy, self.sortAscending)

    def removeAllMods(self):
        ClearFrame(self.modsList)

        self.selectedModButton = None
        for modButton in self.modsButtons:
            modButton.__del__()
            del modButton
        self.modsButtons.clear()

        for modClass in self.mods.values():
            del modClass
        self.mods.clear()

    # Add a method to show the sort menu
    def showSortMenu(self):
        menu = QMenu(self)
        
        # Apply styling to match the app's theme
        menu.setStyleSheet("""
            QMenu {
                background-color: #363636;
                color: #eeeeee;
                border: 1px solid #767676;
                border-radius: 3px;
            }
            QMenu::item {
                padding: 5px 18px 5px 12px;
            }
            QMenu::item:selected {
                background-color: #767676;
            }
            QMenu::separator {
                height: 1px;
                background: #767676;
                margin: 4px 8px;
            }
        """)
        
        # Sort by Name
        actionNameAZ = QAction("Name (A-Z)", self)
        actionNameZA = QAction("Name (Z-A)", self)
        actionNameAZ.triggered.connect(lambda: self.sortMods(self.SORT_BY_NAME, True))
        actionNameZA.triggered.connect(lambda: self.sortMods(self.SORT_BY_NAME, False))
        
        # Sort by Date
        actionDateNew = QAction("Date Added (Newest First)", self)
        actionDateOld = QAction("Date Added (Oldest First)", self)
        actionDateNew.triggered.connect(lambda: self.sortMods(self.SORT_BY_DATE, False))
        actionDateOld.triggered.connect(lambda: self.sortMods(self.SORT_BY_DATE, True))
        
        # Sort by Size
        actionSizeSmall = QAction("File Size (Smallest First)", self)
        actionSizeLarge = QAction("File Size (Largest First)", self)
        actionSizeSmall.triggered.connect(lambda: self.sortMods(self.SORT_BY_SIZE, True))
        actionSizeLarge.triggered.connect(lambda: self.sortMods(self.SORT_BY_SIZE, False))
        
        # Add actions to menu
        menu.addAction(actionNameAZ)
        menu.addAction(actionNameZA)
        menu.addSeparator()
        menu.addAction(actionDateNew)
        menu.addAction(actionDateOld)
        menu.addSeparator()
        menu.addAction(actionSizeSmall)
        menu.addAction(actionSizeLarge)
        
        # Show menu above the button
        pos = self.ui.modsSortButton.mapToGlobal(QPoint(0, 0))
        menu.exec(QPoint(pos.x(), pos.y() - menu.sizeHint().height()))
    
    # Add method to sort mods
    def sortMods(self, sortBy, ascending):
        self.sortBy = sortBy
        self.sortAscending = ascending
        
        # Sort the modsButtons list based on criteria
        if sortBy == self.SORT_BY_NAME:
            self.modsButtons.sort(key=lambda mb: mb.modClass.name.lower(), reverse=not ascending)
        elif sortBy == self.SORT_BY_DATE:
            # Get the mod file path based on hash - safer than accessing a potentially missing attribute
            def get_mod_time(mod_button):
                mod_hash = mod_button.modClass.hash
                # Check if the mod exists in mods dictionary
                if mod_hash in self.mods:
                    # Try to find the mod file
                    mod_files = []
                    for root, dirs, files in os.walk(os.path.join(os.getcwd(), "Mods")):
                        for file in files:
                            if mod_button.modClass.modFileExist and file.endswith(".bmod"):
                                file_path = os.path.join(root, file)
                                try:
                                    return os.path.getmtime(file_path)
                                except:
                                    pass
                return 0  # Default value if file not found
                                
            self.modsButtons.sort(key=get_mod_time, reverse=not ascending)
        elif sortBy == self.SORT_BY_SIZE:
            # Get the mod file size based on mod name and hash
            def get_mod_size(mod_button):
                try:
                    # Skip if mod doesn't have a file
                    if not mod_button.modClass.modFileExist:
                        return 0
                    
                    mod_name = mod_button.modClass.name
                    mod_hash = mod_button.modClass.hash
                    mods_dir = os.path.join(os.getcwd(), "Mods")
                    
                    # First try: direct match with hash in filename
                    for root, _, files in os.walk(mods_dir):
                        for file in files:
                            if file.endswith(".bmod") and mod_hash in file:
                                file_path = os.path.join(root, file)
                                return os.path.getsize(file_path)
                    
                    # Second try: match with sanitized mod name
                    # Remove special characters from mod name for filename comparison
                    sanitized_name = ''.join(c for c in mod_name if c.isalnum() or c in ' -_').strip()
                    sanitized_name = sanitized_name.lower().replace(' ', '')
                    
                    for root, _, files in os.walk(mods_dir):
                        for file in files:
                            if not file.endswith(".bmod"):
                                continue
                                
                            file_name = os.path.splitext(file)[0].lower()
                            file_name = ''.join(c for c in file_name if c.isalnum()).strip()
                            
                            if sanitized_name and sanitized_name in file_name:
                                file_path = os.path.join(root, file)
                                return os.path.getsize(file_path)
                    
                    # Third try: if we have only one mod file and one mod, use that
                    if len(self.mods) == 1:
                        for root, _, files in os.walk(mods_dir):
                            for file in files:
                                if file.endswith(".bmod"):
                                    file_path = os.path.join(root, file)
                                    return os.path.getsize(file_path)
                    
                    # Last resort: check each subdirectory with the mod name
                    for root, dirs, _ in os.walk(mods_dir):
                        for dir_name in dirs:
                            if sanitized_name and sanitized_name in dir_name.lower().replace(' ', ''):
                                dir_path = os.path.join(root, dir_name)
                                # Get total size of all files in this directory
                                total_size = 0
                                for sub_root, _, files in os.walk(dir_path):
                                    for file in files:
                                        try:
                                            file_path = os.path.join(sub_root, file)
                                            total_size += os.path.getsize(file_path)
                                        except (IOError, OSError):
                                            continue
                                return total_size
                
                except Exception as e:
                    print(f"Error getting size for mod {mod_button.modClass.name}: {str(e)}")
                    return 0
                
                return 0  # Default if no matching file found
                            
            self.modsButtons.sort(key=get_mod_size, reverse=not ascending)
        
        # Remove all mod buttons from the UI
        for modButton in self.modsButtons:
            modButton.remove()
        
        # Re-add mod buttons in sorted order
        for modButton in self.modsButtons:
            modButton.restore(self.modsList)
        
        # If a mod was selected, make sure it stays selected
        if self.selectedModButton is not None:
            self.selectedModButton.select()
