from typing import List, Dict
import os
import sys
import datetime
import random
import json
import time

from PySide6.QtWidgets import QWidget, QPushButton, QVBoxLayout, QFrame, QLabel, QMenu, QGridLayout, QHBoxLayout, QSizePolicy, QTextEdit, QLayout
from PySide6.QtGui import QPixmap, QPaintEvent, QIcon, QCursor, QAction, QBrush, QPalette
from PySide6.QtCore import QSize, Qt, QPoint, QTimer

from .performance import performance_cache, animation_manager, layout_manager, background_optimizer

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
    def __init__(self, n, method, parent=None):
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

        super().__init__(group="PreviewNavigate", button=self.previewNavigate, method=method, parent=parent)


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
    
    # Variables to track view mode
    VIEW_LIST = "list"
    VIEW_THUMBNAIL_TEXT = "thumbnail_text"
    VIEW_THUMBNAIL_ONLY = "thumbnail_only"
    currentViewMode = VIEW_LIST

    def __init__(self, installMethod, uninstallMethod, reinstallMethod, deleteMethod, reloadMethod, openFolderMethod):
        super().__init__()

        self.ui = Ui_Mods()
        self.ui.setupUi(self)

        # Set up background image for mod list
        self.bg_path = os.path.join(os.path.dirname(__file__), '..', 'ui_sources', 'resources', 'icons', 'uiupdate', 'mod_list_background.png')
        self.set_mod_list_background()
        
        # Set up background image for bottom action bar
        self.bottom_bar_bg_path = os.path.join(os.path.dirname(__file__), '..', 'ui_sources', 'resources', 'icons', 'uiupdate', 'button_menu_bar.png')
        # Use QTimer to set background after UI is fully initialized
        QTimer.singleShot(100, self.set_bottom_bar_background)
        
        # Set up background image for mod description area
        self.mod_description_bg_path = os.path.join(os.path.dirname(__file__), '..', 'ui_sources', 'resources', 'icons', 'uiupdate', 'mod_description_backround.png')
        self.set_mod_description_background()

        # Set up optimized resize handling for smooth image scaling
        self._resize_timer = QTimer()
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(lambda: self._handle_delayed_resize())
        self._last_size = None

        self.preview = None
        self.previews: List[QPixmap] = []
        self.previewsNavigate: List[NavigateButton] = [NavigateButton(n, self.setPreviewNum) for n in range(6)]
        self.previewRatio = 1

        bodyWidget = QWidget()
        self.body = Ui_ModBody()
        self.body.setupUi(bodyWidget)
        self.ui.scrollBody.setWidget(bodyWidget)

        self.ui.modBody.installEventFilter(self)
        # Use the new scrollable layout instead of the old modDescriptionsAndActions
        self.modDescriptionsAndActionsLayout = self.body.scrollableLayout

        self.body.leftPreview.clicked.connect(self.leftPreview)
        self.body.rightPreview.clicked.connect(self.rightPreview)

        modsListFrame = QFrame()
        layout = QVBoxLayout(modsListFrame)
        layout.setSpacing(0)
        layout.setContentsMargins(2, 5, 2, 5)
        self.modsList = QFrame()
        self.modsList.setMaximumWidth(self.ui.modsList.maximumWidth())
        # Initial layout will be set by setupListView()
        layout.addWidget(self.modsList, 0, Qt.AlignTop)
        self.ui.scrollModsList.setWidget(modsListFrame)
        
        # Setup initial view mode
        self.setupListView()

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

        # Connect button clicks with bounce animations
        self.modsActions.install.clicked.connect(lambda: (animation_manager.bounce_scale(self.modsActions.install, 1.1, 200), installMethod()))
        self.modsActions.uninstall.clicked.connect(lambda: (animation_manager.bounce_scale(self.modsActions.uninstall, 1.1, 200), uninstallMethod()))
        self.modsActions.reinstall.clicked.connect(lambda: (animation_manager.bounce_scale(self.modsActions.reinstall, 1.1, 200), reinstallMethod()))
        self.modsActions.deleteMod.clicked.connect(lambda: (animation_manager.bounce_scale(self.modsActions.deleteMod, 1.1, 200), deleteMethod()))
        self.ui.reloadModsList.clicked.connect(reloadMethod)
        self.ui.reinstallAllModsButton.clicked.connect(self.reinstallAllMods)
        self.ui.openModsFolderButton.clicked.connect(openFolderMethod)
        self.ui.openModsFolderButton.setToolTip("Open mods folder")
        
        # Connect install all mods button (disabled - not working correctly)
        self.ui.installAllMods.clicked.connect(self.installAllMods)
        self.ui.installAllMods.setEnabled(False)
        
        # Store install method for installAllMods
        self.installMethod = installMethod
        
        # Add view toggle button
        from PySide6.QtWidgets import QPushButton
        from PySide6.QtGui import QIcon, QPixmap
        self.viewToggleButton = QPushButton(self.ui.leftButtons)
        self.viewToggleButton.setObjectName("viewToggleButton")
        self.viewToggleButton.setMinimumSize(30, 30)
        self.viewToggleButton.setMaximumSize(30, 30)
        self.viewToggleButton.setCursor(Qt.PointingHandCursor)
        self.viewToggleButton.setToolTip("Toggle view mode (Text / Text+Thumbnail / Grid)")
        
        # Load custom icon
        icon_path = os.path.join(os.path.dirname(__file__), '..', 'ui_sources', 'resources', 'icons', 'listview-button.png')
        if os.path.exists(icon_path):
            icon_pixmap = QPixmap(icon_path)
            if not icon_pixmap.isNull():
                # Scale to match other button icons (30x30)
                scaled_icon = icon_pixmap.scaled(30, 30, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                icon = QIcon(scaled_icon)
                self.viewToggleButton.setIcon(icon)
                self.viewToggleButton.setText("")  # Clear any text
            else:
                self.viewToggleButton.setText("📋")
        else:
            self.viewToggleButton.setText("📋")
        
        self.viewToggleButton.clicked.connect(self.toggleViewMode)
        # Insert after installAllMods button
        self.ui.leftButtons.layout().insertWidget(3, self.viewToggleButton)
        
        # Set up custom PNG install button
        self.setup_custom_install_button()
        
        # Set up custom PNG delete button
        self.setup_custom_delete_button()
        
        # Set up custom PNG reinstall button
        self.setup_custom_reinstall_button()
        
        # Set up custom PNG uninstall button
        self.setup_custom_uninstall_button()
        
        # Connect sort button to menu
        self.ui.modsSortButton.clicked.connect(self.showSortMenu)
        self.ui.modsSortButton.setToolTip("Reorder mods list")
        
        # Connect view toggle button
        self.ui.viewToggleButton.clicked.connect(self.toggleViewMode)

        # Initialize filtered mods list (will be populated as mods are added)
        self.filteredModsButtons = []
        
        # Connect search - works with all view modes now
        self.ui.searchArea.textChanged.connect(self.searchEvent)

        AddToFrame(self.body.modActions, actionsWidget)

        self.setPreviewsPaths([self.defaultPreview])
        
        # Initialize timestamp tracking
        # Use executable directory when frozen, otherwise current working directory
        if getattr(sys, 'frozen', False):
            _base_path = os.path.dirname(sys.executable)
        else:
            _base_path = os.getcwd()
        self.timestamps_file = os.path.join(_base_path, 'mod_timestamps.json')
        # Initialize mod_timestamps before loading
        self.mod_timestamps = {}
        # Load existing timestamps or create new file
        self.mod_timestamps = self.load_timestamps()

    def set_mod_list_background(self):
        """Set the background image for the mod list"""
        if os.path.exists(self.bg_path):
            pixmap = QPixmap(self.bg_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(
                    self.ui.modsList.size(),
                    Qt.KeepAspectRatioByExpanding,
                    Qt.SmoothTransformation
                )
                palette = self.ui.modsList.palette()
                palette.setBrush(self.ui.modsList.backgroundRole(), QBrush(scaled_pixmap))
                self.ui.modsList.setPalette(palette)
                self.ui.modsList.setAutoFillBackground(True)

    def set_bottom_bar_background(self):
        """Set the background image for the bottom navigation bar"""
        if os.path.exists(self.bottom_bar_bg_path):
            # Remove default frame styling first
            self.ui.modsListActions.setFrameShape(QFrame.NoFrame)
            self.ui.modsListActions.setFrameShadow(QFrame.Plain)
            
            pixmap = QPixmap(self.bottom_bar_bg_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(
                    self.ui.modsListActions.size(),
                    Qt.KeepAspectRatioByExpanding,
                    Qt.SmoothTransformation
                )
                palette = self.ui.modsListActions.palette()
                palette.setBrush(self.ui.modsListActions.backgroundRole(), QBrush(scaled_pixmap))
                self.ui.modsListActions.setPalette(palette)
                self.ui.modsListActions.setAutoFillBackground(True)

    def set_mod_description_background(self):
        """Set the background image for the mod description area using QPixmap"""
        if os.path.exists(self.mod_description_bg_path):
            pixmap = QPixmap(self.mod_description_bg_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(
                    self.ui.modBody.size(),
                    Qt.KeepAspectRatioByExpanding,
                    Qt.SmoothTransformation
                )
                palette = self.ui.modBody.palette()
                palette.setBrush(self.ui.modBody.backgroundRole(), QBrush(scaled_pixmap))
                self.ui.modBody.setPalette(palette)
                self.ui.modBody.setAutoFillBackground(True)

    def setup_custom_install_button(self):
        """Set up the install button with custom PNG image"""
        # Path to the PNG image
        install_png = os.path.join(os.path.dirname(__file__), '..', 'ui_sources', 'resources', 'icons', 'uiupdate', 'install_button.png')
        
        if os.path.exists(install_png):
            # Load the image as QPixmap to check its size
            install_pixmap = QPixmap(install_png)
            
            # Scale down the image to fit the button (adjusted size: 120x52)
            scaled_install = install_pixmap.scaled(120, 52, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            
            # Create icon from scaled pixmap
            install_icon = QIcon(scaled_install)
            
            # Set up the button with icon
            self.modsActions.install.setIcon(install_icon)
            self.modsActions.install.setIconSize(QSize(120, 52))
            
            # Hide text
            self.modsActions.install.setText("")
            
            # Set transparent background with hover effect
            self.modsActions.install.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: none;
                    color: transparent;
                }
                QPushButton:hover {
                    background-color: rgba(67, 193, 95, 0.3);
                }
                QPushButton:pressed {
                    background-color: rgba(67, 193, 95, 0.5);
                }
            """)
            
            # Add hover animations
            self.modsActions.install.enterEvent = lambda event: animation_manager.smooth_hover_scale(self.modsActions.install, 1.05, 150)
            self.modsActions.install.leaveEvent = lambda event: animation_manager.smooth_hover_return(self.modsActions.install, 150)
            
        else:
            pass
            # Keep original styling if PNG not found

    def setup_custom_delete_button(self):
        """Set up the delete button with custom PNG image"""
        # Path to the PNG image
        delete_png = os.path.join(os.path.dirname(__file__), '..', 'ui_sources', 'resources', 'icons', 'uiupdate', 'delete_button.png')
        
        if os.path.exists(delete_png):
            # Load the image as QPixmap to check its size
            delete_pixmap = QPixmap(delete_png)
            
            # Scale down the image to fit the button (adjusted size: 120x52)
            scaled_delete = delete_pixmap.scaled(120, 52, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            
            # Create icon from scaled pixmap
            delete_icon = QIcon(scaled_delete)
            
            # Set up the button with icon
            self.modsActions.deleteMod.setIcon(delete_icon)
            self.modsActions.deleteMod.setIconSize(QSize(120, 52))
            
            # Hide text
            self.modsActions.deleteMod.setText("")
            
            # Set transparent background with hover effect (red theme for delete)
            self.modsActions.deleteMod.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: none;
                    color: transparent;
                }
                QPushButton:hover {
                    background-color: rgba(255, 80, 80, 0.3);
                }
                QPushButton:pressed {
                    background-color: rgba(255, 80, 80, 0.5);
                }
            """)
            
            # Add hover animations
            self.modsActions.deleteMod.enterEvent = lambda event: animation_manager.smooth_hover_scale(self.modsActions.deleteMod, 1.05, 150)
            self.modsActions.deleteMod.leaveEvent = lambda event: animation_manager.smooth_hover_return(self.modsActions.deleteMod, 150)
            
        else:
            pass
            # Keep original styling if PNG not found

    def setup_custom_reinstall_button(self):
        """Set up the reinstall button with custom PNG image"""
        # Path to the PNG image
        reinstall_png = os.path.join(os.path.dirname(__file__), '..', 'ui_sources', 'resources', 'icons', 'uiupdate', 'reinstall_button.png')
        
        if os.path.exists(reinstall_png):
            # Load the image as QPixmap to check its size
            reinstall_pixmap = QPixmap(reinstall_png)
            
            # Scale down the image to fit the button (adjusted size: 120x52)
            scaled_reinstall = reinstall_pixmap.scaled(120, 52, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            
            # Create icon from scaled pixmap
            reinstall_icon = QIcon(scaled_reinstall)
            
            # Set up the button with icon
            self.modsActions.reinstall.setIcon(reinstall_icon)
            self.modsActions.reinstall.setIconSize(QSize(120, 52))
            
            # Hide text
            self.modsActions.reinstall.setText("")
            
            # Set transparent background with hover effect (purple theme for reinstall)
            self.modsActions.reinstall.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: none;
                    color: transparent;
                }
                QPushButton:hover {
                    background-color: rgba(205, 51, 199, 0.3);
                }
                QPushButton:pressed {
                    background-color: rgba(205, 51, 199, 0.5);
                }
            """)
            
            # Add hover animations
            self.modsActions.reinstall.enterEvent = lambda event: animation_manager.smooth_hover_scale(self.modsActions.reinstall, 1.05, 150)
            self.modsActions.reinstall.leaveEvent = lambda event: animation_manager.smooth_hover_return(self.modsActions.reinstall, 150)
            
        else:
            pass
            # Keep original styling if PNG not found

    def setup_custom_uninstall_button(self):
        """Set up the uninstall button with custom PNG image"""
        # Path to the PNG image
        uninstall_png = os.path.join(os.path.dirname(__file__), '..', 'ui_sources', 'resources', 'icons', 'uiupdate', 'uninstall_button.png')
        
        if os.path.exists(uninstall_png):
            # Load the image as QPixmap to check its size
            uninstall_pixmap = QPixmap(uninstall_png)
            
            # Scale down the image to fit the button (adjusted size: 120x52)
            scaled_uninstall = uninstall_pixmap.scaled(120, 52, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            
            # Create icon from scaled pixmap
            uninstall_icon = QIcon(scaled_uninstall)
            
            # Set up the button with icon
            self.modsActions.uninstall.setIcon(uninstall_icon)
            self.modsActions.uninstall.setIconSize(QSize(120, 52))
            
            # Hide text
            self.modsActions.uninstall.setText("")
            
            # Set transparent background with hover effect (teal theme for uninstall)
            self.modsActions.uninstall.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: none;
                    color: transparent;
                }
                QPushButton:hover {
                    background-color: rgba(0, 185, 163, 0.3);
                }
                QPushButton:pressed {
                    background-color: rgba(0, 185, 163, 0.5);
                }
            """)
            
            # Add hover animations
            self.modsActions.uninstall.enterEvent = lambda event: animation_manager.smooth_hover_scale(self.modsActions.uninstall, 1.05, 150)
            self.modsActions.uninstall.leaveEvent = lambda event: animation_manager.smooth_hover_return(self.modsActions.uninstall, 150)
            
        else:
            pass
            # Keep original styling if PNG not found

    def load_timestamps(self):
        """Load timestamps from file, create empty file if it doesn't exist"""
        if os.path.exists(self.timestamps_file):
            try:
                with open(self.timestamps_file, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
                    return {}
            except (IOError, json.JSONDecodeError) as e:
                print(f"Error loading timestamps: {e}, creating new file")
                # Return empty dict, will be saved when needed
                return {}
        else:
            # File doesn't exist, create it with empty dict
            print(f"Timestamp file not found, creating: {self.timestamps_file}")
            empty_dict = {}
            # Save empty file immediately
            try:
                timestamps_dir = os.path.dirname(self.timestamps_file)
                if timestamps_dir and not os.path.exists(timestamps_dir):
                    os.makedirs(timestamps_dir, exist_ok=True)
                with open(self.timestamps_file, 'w') as f:
                    json.dump(empty_dict, f, indent=4)
                print(f"Created timestamp file: {self.timestamps_file}")
            except Exception as e:
                print(f"Warning: Could not create timestamp file: {e}")
            return empty_dict

    def save_timestamps(self):
        try:
            # Ensure the directory exists
            timestamps_dir = os.path.dirname(self.timestamps_file)
            if timestamps_dir and not os.path.exists(timestamps_dir):
                os.makedirs(timestamps_dir, exist_ok=True)
            with open(self.timestamps_file, 'w') as f:
                json.dump(self.mod_timestamps, f, indent=4)
        except IOError as e:
            print(f"Warning: Could not save timestamps to {self.timestamps_file}: {e}")

    def loadPreview(self, pixmap: QPixmap):
        self.previewRatio = pixmap.width() / pixmap.height()
        self.body.modPreview.setPixmap(pixmap)
        # Force immediate resize to apply correct height on startup
        self._perform_resize(force=True)

    def searchEvent(self, text):
        """Filter mods based on search text - works with all view modes"""
        if not text:
            self.filteredModsButtons = self.modsButtons.copy()
        else:
            text = text.casefold()

            if len(text.split(" ")) == 1:
                text = f" {text}"

            self.filteredModsButtons = [
                modButton
                for modButton in self.modsButtons
                if any([
                    text in f" {modButton.modClass.name.lower()}",
                    text in f" {modButton.modClass.author.lower()}",
                    modButton.modClass.gameVersion.startswith(text.strip()),
                    any([tag.casefold().lower().startswith(text.strip()) for tag in modButton.modClass.tags])
                ])
            ]

        # Refresh the mod list with filtered results
        self.refreshModList()
        
        # If there's a selected mod in the filtered results, ensure it stays selected
        if self.selectedModButton is not None and self.selectedModButton in self.filteredModsButtons:
            try:
                self.selectedModButton.select()
            except RuntimeError:
                pass

    def onResize(self, *a):
        """Optimized resize handler with debouncing and caching"""
        # Use debounced update to prevent excessive recalculations
        layout_manager.debounced_update(self, self._perform_resize, 50)
    
    def _perform_resize(self, force=False):
        """Actual resize calculations with caching"""
        current_size = QSize(self.ui.scrollBody.width(), self.ui.modBody.height())
        
        # Check if we need to update based on size change (unless forced)
        if not force and not layout_manager.should_update_layout(self, current_size):
            return
        
        width = self.ui.scrollBody.width() - (7 if self.ui.scrollBody.verticalScrollBar().isVisible() else 0)
        # Calculate height based on image aspect ratio - ensure it's tall enough
        imageHeight = int(width / self.previewRatio)

        self.body.modPreview.setGeometry(0, 0, width, imageHeight)
        self.body.modPreviewInfo.setGeometry(0, 0, width, imageHeight)

        lMargin, tMargin, rMargin, bMargin = self.modDescriptionsAndActionsLayout.getContentsMargins()
        spacing = self.modDescriptionsAndActionsLayout.spacing()

        # Force the frame to be the correct height immediately
        self.body.modPreviewFrame.setMinimumHeight(imageHeight)
        self.body.modPreviewFrame.setMaximumHeight(imageHeight + 1)  # Allow slight overflow for rounding

        modDescriptionHeight = self.ui.modBody.height() - imageHeight - self.body.modTags.height() - \
                               self.body.modFeatures.height() - self.body.modActions.height() - tMargin - bMargin - spacing * \
                               (self.modDescriptionsAndActionsLayout.count() - 1) - 20  # Add extra 20px buffer for features

        modDescriptionDocumentHeight = self.body.modDescription.document().size().height()

        if modDescriptionDocumentHeight > modDescriptionHeight:
            self.body.modDescription.setMinimumHeight(modDescriptionDocumentHeight)
        else:
            self.body.modDescription.setMinimumHeight(modDescriptionHeight)
        
        # Only update backgrounds if size changed significantly
        self.set_mod_list_background()
        self.set_bottom_bar_background()
        self.set_mod_description_background()

    def onModsListResize(self, event):
        # Only call onParentResize on ModButton widgets, not on all widgets
        layout = self.modsList.layout()
        if layout:
            widgets_to_process = []
            for n in range(layout.count()):
                item = layout.takeAt(0)
                if item.widget():
                    widget = item.widget()
                    widgets_to_process.append((item, widget))
            
            # Process widgets and add them back
            for item, widget in widgets_to_process:
                # Only call onParentResize on ModButton widgets
                if isinstance(widget, ModButton):
                    try:
                        widget.onParentResize()
                    except (AttributeError, RuntimeError):
                        pass
                layout.addItem(item)

        self.origScrollModsListResizeEvent(event)
        
        # Refresh mod list if in grid or text+thumbnail view to update sizes dynamically
        if self.currentViewMode in [self.VIEW_GRID_THUMBNAIL, self.VIEW_TEXT_THUMBNAIL]:
            # Use a timer to debounce rapid resize events
            if not hasattr(self, '_resize_refresh_timer'):
                self._resize_refresh_timer = QTimer()
                self._resize_refresh_timer.setSingleShot(True)
                self._resize_refresh_timer.timeout.connect(self.refreshModList)
            self._resize_refresh_timer.stop()
            self._resize_refresh_timer.start(200)  # Wait 200ms after resize stops

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

        if len(paths) <= 1:
            self.body.leftPreview.hide()
            self.body.rightPreview.hide()
        else:
            self.body.leftPreview.show()
            self.body.rightPreview.show()

        for n, path in enumerate(paths):
            pixmap = self.cachePreview(path)
            self.previews.append(pixmap)

        self.loadPreview(self.previews[0])
        self.setPreviewNum(0)

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
        # Set the mod name with Eras font
        self.body.modName.setText(modClass.name)
        # Set author and version separately with labels
        self.body.modSource.setText(f"Author: {modClass.author}")
        self.body.modVersion.setText(f"Version: {modClass.version}")
        self.body.modDescription.setText(modClass.description)
        
        # Create individual tag bubbles instead of simple text
        self.createNewTagBubbles(modClass.tags)
        
        # Create feature bubbles
        if modClass.features:
            self.createFeatureBubbles(modClass.features)
        else:
            # Clear any existing feature containers for mods without features
            self.clearFeatureBubbles()

    def createNewTagBubbles(self, tags):
        """Create tag bubbles using the new HTML system"""
        
        # Clear ALL existing tag containers
        for i in reversed(range(self.body.scrollableLayout.count())):
            child = self.body.scrollableLayout.itemAt(i).widget()
            if child and (child.objectName().startswith("tagBubble_") or 
                         child.objectName() == "tagsContainer" or 
                         child.objectName() == "newTagsContainer"):
                child.setParent(None)
        
        # Use ONLY the new HTML system
        self.createNewTagSystem(tags)

    def createNewTagSystem(self, tags):
        """Create tags using dynamic wrapping based on container width"""
        
        # Clear any existing new tag containers
        for i in reversed(range(self.body.scrollableLayout.count())):
            child = self.body.scrollableLayout.itemAt(i).widget()
            if child and child.objectName() == "newTagsContainer":
                child.setParent(None)
        
        # Only create container if there are actual tags
        if not tags or not any(tag.strip() for tag in tags):
            return
        
        # Create a custom wrapping container
        tag_container = DynamicTagContainer()
        tag_container.setObjectName("newTagsContainer")
        
        # Add some top margin to move tags down from thumbnail, reduce bottom margin to bring install button closer
        tag_container.setContentsMargins(15, 20, 15, 0)  # Reduced bottom margin from 5 to 0px
        
        # Define clean color schemes
        color_schemes = [
            {"bg": "#4A90E2", "text": "#FFFFFF"},  # Blue
            {"bg": "#7B68EE", "text": "#FFFFFF"}   # Purple
        ]
        
        # Create individual QLabel widgets for each tag
        for i, tag in enumerate(tags):
            if not tag.strip():
                continue
                
            
            # Choose color scheme
            colors = color_schemes[i % len(color_schemes)]
            
            # Create QLabel for the tag
            tag_label = QLabel(tag.strip())
            tag_label.setObjectName(f"tagBubble_{i}")
            
            # Style the label with proper padding and spacing
            tag_label.setStyleSheet(f"""
                QLabel {{
                    background-color: {colors["bg"]};
                    color: {colors["text"]};
                    border-radius: 15px;
                    padding: 6px 12px;
                    font-size: 12px;
                    font-weight: 500;
                    border: 2px solid yellow;
                }}
            """)
            
            # Add to dynamic container
            tag_container.addTag(tag_label)
        
        # Insert the tag container widget at the top (where Tags: label used to be)
        self.body.scrollableLayout.insertWidget(0, tag_container)
        
        # Trigger layout update after a short delay to ensure proper sizing
        QTimer.singleShot(200, tag_container.updateLayout)

    def createFeatureBubbles(self, features):
        """Create feature bubbles using LIGHTWEIGHT approach - like tags but dynamic"""
        
        
        # Clear any existing feature containers
        layout = self.body.modFeatures.layout()
        if layout:
            for i in reversed(range(layout.count())):
                child = layout.itemAt(i).widget()
                if child:
                    child.setParent(None)
        
        # Only create bubbles if there are actual features
        if not features or not any(feature.strip() for feature in features):
            return
        
        
        # LIGHTWEIGHT APPROACH: Use the same logic as tags
        feature_container = QWidget()
        feature_container.setObjectName("featuresContainer")
        feature_container.setContentsMargins(15, 8, 15, 8)  # Same margins as tags
        
        # Create a simple vertical layout
        main_layout = QVBoxLayout(feature_container)
        main_layout.setSpacing(4)  # Same spacing as tags
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSizeConstraint(QLayout.SetMinimumSize)
        
        # Define color schemes
        color_schemes = [
            {"bg": "#006400", "text": "#FFFFFF"},  # Dark Green
            {"bg": "#1E3A8A", "text": "#FFFFFF"}   # Dark Blue
        ]
        
        # Create features in rows - simple approach
        current_row = QHBoxLayout()
        current_row.setSpacing(6)  # Same spacing as tags
        current_row.setContentsMargins(0, 0, 0, 0)
        main_layout.addLayout(current_row)
        
        current_width = 0
        max_width = 400  # Reasonable width limit
        
        for i, feature in enumerate(features):
            if not feature.strip():
                continue
                
            
            # Create label
            feature_label = QLabel(feature.strip())
            feature_label.setObjectName(f"featureBubble_{i}")
            
            # Style exactly like tags but with feature colors
            colors = color_schemes[i % len(color_schemes)]
            feature_label.setStyleSheet(f"""
                QLabel {{
                    background-color: {colors["bg"]};
                    color: {colors["text"]};
                    border-radius: 12px;
                    padding: 4px 10px;
                    font-size: 10px;
                    font-weight: bold;
                    border: 2px solid white;
                }}
            """)
            
            # Get the label's preferred size
            feature_label.adjustSize()
            label_width = feature_label.sizeHint().width()
            
            # If this would exceed the width, start a new row
            if current_width + label_width > max_width and current_width > 0:
                current_row.addStretch()  # Fill remaining space
                
                # Create new row
                current_row = QHBoxLayout()
                current_row.setSpacing(6)
                current_row.setContentsMargins(0, 0, 0, 0)
                main_layout.addLayout(current_row)
                current_width = 0
            
            # Add to current row
            current_row.addWidget(feature_label)
            current_width += label_width + 6  # Add spacing
        
        # Fill remaining space in last row
        current_row.addStretch()
        
        # Set size policy to expand horizontally but size to content vertically
        feature_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        # Ensure the container advertises the correct height to parent layouts
        feature_container.adjustSize()
        feature_container.updateGeometry()
        
        # Add the feature container to the modFeatures frame
        self.body.modFeatures.layout().addWidget(feature_container)
        
        # Make the modFeatures frame grow vertically as needed
        self.body.modFeatures.setMinimumHeight(0)
        self.body.modFeatures.setMaximumHeight(16777215)
        self.body.modFeatures.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.body.modFeatures.updateGeometry()
        
        feature_container.show()
        

    def positionFeatureBubbles(self, feature_container):
        """Position feature bubbles correctly without causing them to disappear"""
        
        # Get available width
        parent = feature_container.parent()
        if parent:
            available_width = parent.width() - 20  # 20px margin
        else:
            available_width = 300
        
        available_width = max(200, available_width)
        
        current_x = 0
        current_y = 0
        line_height = 0
        spacing = 6
        
        for i, feature in enumerate(feature_container.features):
            # Get the size the feature wants to be
            feature_size = feature.sizeHint()
            feature_width = feature_size.width()
            feature_height = feature_size.height()
            
            
            # If this feature would overflow, move to next line
            if current_x + feature_width > available_width and current_x > 0:
                current_x = 0
                current_y += line_height + 4  # 4px spacing between lines
                line_height = 0
                
            # Position the feature
            feature.move(current_x, current_y)
            feature.resize(feature_width, feature_height)
            feature.show()  # Ensure the feature is visible
            
            # Update position for next feature
            current_x += feature_width + spacing
            line_height = max(line_height, feature_height)
            
        # Update container height
        total_height = current_y + line_height + 30
        feature_container.setMinimumHeight(total_height)

    def clearFeatureBubbles(self):
        """Clear all feature bubbles from the modFeatures frame"""
        layout = self.body.modFeatures.layout()
        if layout:
            for i in reversed(range(layout.count())):
                child = layout.itemAt(i).widget()
                if child:
                    child.setParent(None)

    def selectMod(self, modClass: ModClass):
        for modButton in self.modsButtons:
            if modButton.modClass == modClass:
                self.selectedModButton = modButton

        self.updateData()

    def addModButton(self, modClass: ModClass):
        modButton = ModButton(modClass=modClass,
                              method=self.selectMod)

        self.modsButtons.append(modButton)
        
<<<<<<< Updated upstream
        # Add to current view mode
        if self.currentViewMode == self.VIEW_LIST:
            AddToFrame(self.modsList, modButton)
        else:
            # For other view modes (thumbnail_text or thumbnail_only), refresh the entire list
            # Use a short delay to allow all mods to be added first for better performance
            QTimer.singleShot(100, self.refreshModList)

        # Add fade-in animation for new mod button
        animation_manager.fade_in(modButton, 300)

        if not self.selectedModButton:
            modButton.select()

    def reinstallAllMods(self):
        """Reinstall all installed mods"""
        installed_mods = [
            mod_button.modClass
            for mod_button in self.modsButtons
            if mod_button.modClass.installed
        ]
        
        if not installed_mods:
            # Show message that there are no installed mods
            from ..utils.systemdialog import Info
            from main import PROGRAM_NAME
            Info(PROGRAM_NAME, "No installed mods to reinstall.")
            return
        
        self.window().buttonsDialog.setTitle("Reinstall All Mods")
        self.window().buttonsDialog.setContent(f"Are you sure you want to reinstall {len(installed_mods)} mod(s)?")
        self.window().buttonsDialog.setButtons([
            ("Proceed", self._reinstallAllMods),
            ("Cancel", self.window().buttonsDialog.hide)
        ])
        self.window().buttonsDialog.show()

    def _reinstallAllMods(self):
        """Actually reinstall all installed mods"""
        self.window().buttonsDialog.hide()
        installed_mods = [
            mod_button.modClass
            for mod_button in self.modsButtons
            if mod_button.modClass.installed
        ]
        for mod in installed_mods:
            self.window().reinstallMod(mod.hash)
    
    def installAllMods(self):
        """Install all uninstalled mods"""
        uninstalled_mods = [
            mod_button.modClass
            for mod_button in self.modsButtons
            if not mod_button.modClass.installed
        ]
        
        if not uninstalled_mods:
            # Show message that all mods are already installed
            from ..utils.systemdialog import Info
            from main import PROGRAM_NAME
            Info(PROGRAM_NAME, "All mods are already installed.")
            return
        
        self.window().buttonsDialog.setTitle("Install All Mods")
        self.window().buttonsDialog.setContent(f"Are you sure you want to install {len(uninstalled_mods)} mod(s)?")
        self.window().buttonsDialog.setButtons([
            ("Proceed", self._installAllMods),
            ("Cancel", self.window().buttonsDialog.hide)
        ])
        self.window().buttonsDialog.show()
    
    def _installAllMods(self):
        """Actually install all uninstalled mods"""
        self.window().buttonsDialog.hide()
        uninstalled_mods = [
            mod_button.modClass
            for mod_button in self.modsButtons
            if not mod_button.modClass.installed
        ]
        for mod in uninstalled_mods:
            # Select the mod first, then install it
            self.selectMod(mod)
            self.installMethod()
    
    def toggleViewMode(self):
        """Cycle through view modes: text -> text+thumbnail -> grid -> text"""
        if self.currentViewMode == self.VIEW_TEXT:
            self.currentViewMode = self.VIEW_TEXT_THUMBNAIL
        elif self.currentViewMode == self.VIEW_TEXT_THUMBNAIL:
            self.currentViewMode = self.VIEW_GRID_THUMBNAIL
        else:  # VIEW_GRID_THUMBNAIL
            self.currentViewMode = self.VIEW_TEXT
        
        # Refresh the mod list with the new view mode
        self.refreshModList()
    
    def refreshModList(self):
        """Refresh the mod list display based on current view mode"""
        # Store current selection
        selected_mod = self.selectedModButton.modClass if self.selectedModButton else None
        
        # Ensure filteredModsButtons is initialized
        if not hasattr(self, 'filteredModsButtons'):
            self.filteredModsButtons = []
        
        # Properly clear all widgets from the layout without deleting ModButton objects
        layout = self.modsList.layout()
        if layout:
            # First, collect all widgets and remove them from layout
            widgets_to_remove = []
            mod_buttons_to_clear = []
            
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    widget = item.widget()
                    # Separate ModButtons from other widgets
                    if isinstance(widget, ModButton):
                        mod_buttons_to_clear.append(widget)
                    else:
                        widgets_to_remove.append(widget)
            
            # Remove ModButtons from parent (but don't delete them)
            for mod_button in mod_buttons_to_clear:
                try:
                    mod_button.setParent(None)
                except RuntimeError:
                    continue
            
            # Delete non-ModButton widgets (grid containers, etc.)
            for widget in widgets_to_remove:
                try:
                    widget.setParent(None)
                    widget.deleteLater()
                except RuntimeError:
                    continue
        
        # Also ensure all ModButtons are not parented to modsList
        for mod_button in self.modsButtons:
            try:
                if mod_button.parent() == self.modsList:
                    mod_button.setParent(None)
            except RuntimeError:
                # Widget already deleted, skip it
                continue
        
        # Use filtered mods if search is active, otherwise use all mods
        # Check if there's an active search filter
        search_text = self.ui.searchArea.text() if hasattr(self.ui, 'searchArea') else ""
        if search_text:
            # Use filtered mods if search is active
            mods_to_display = self.filteredModsButtons if self.filteredModsButtons else self.modsButtons
        else:
            # No search filter - use all mods
            mods_to_display = self.modsButtons
        
        # Rebuild mod list based on view mode
        if self.currentViewMode == self.VIEW_TEXT:
            # Standard text view - use existing ModButton
            for mod_button in mods_to_display:
                try:
                    mod_button.restore(self.modsList)
                    # Hide thumbnail if it exists
                    if hasattr(mod_button.ui, 'thumbnailLabel'):
                        mod_button.ui.thumbnailLabel.hide()
                except RuntimeError:
                    # Widget was deleted, skip it
                    continue
        elif self.currentViewMode == self.VIEW_TEXT_THUMBNAIL:
            # Text + thumbnail view - modify ModButton to show thumbnail
            for mod_button in mods_to_display:
                try:
                    mod_button.restore(self.modsList)
                    # Show/add thumbnail
                    self._addThumbnailToModButton(mod_button)
                except RuntimeError:
                    # Widget was deleted, skip it
                    continue
        else:  # VIEW_GRID_THUMBNAIL
            # Grid view - create grid layout with filtered mods
            self._createGridLayout(mods_to_display)
        
        # Restore selection
        if selected_mod:
            for mod_button in mods_to_display:
                try:
                    if mod_button.modClass == selected_mod:
                        mod_button.select()
                        break
                except RuntimeError:
                    # Widget was deleted, skip it
                    continue
    
    def _addThumbnailToModButton(self, mod_button):
        """Add thumbnail image to a ModButton for text+thumbnail view"""
        # Calculate thumbnail size - use height of mod button (typically 48px) minus padding
        thumbnail_max_size = 56  # Slightly larger for better visibility
        
        # Check if thumbnail label already exists
        if not hasattr(mod_button.ui, 'thumbnailLabel'):
            # Create thumbnail label - don't set fixed size, let it size based on pixmap
            thumbnail_label = QLabel(mod_button.ui.background)
            thumbnail_label.setObjectName("thumbnailLabel")
            thumbnail_label.setScaledContents(True)
            thumbnail_label.setStyleSheet("border-radius: 4px;")
            thumbnail_label.setAlignment(Qt.AlignCenter)
            mod_button.ui.thumbnailLabel = thumbnail_label
            
            # Insert thumbnail at the beginning of the layout
            mod_button.ui.background.layout().insertWidget(0, thumbnail_label)
        else:
            mod_button.ui.thumbnailLabel.show()
        
        # Load and set thumbnail image with proper aspect ratio
        thumbnail_pixmap = self._getModThumbnail(mod_button.modClass, thumbnail_max_size)
        if thumbnail_pixmap:
            # Set the pixmap - the label will size itself based on the pixmap dimensions
            mod_button.ui.thumbnailLabel.setPixmap(thumbnail_pixmap)
            # Set size based on actual pixmap size to maintain aspect ratio
            mod_button.ui.thumbnailLabel.setMinimumSize(thumbnail_pixmap.size())
            mod_button.ui.thumbnailLabel.setMaximumSize(thumbnail_pixmap.size())
    
    def _getModThumbnail(self, mod_class, max_size=64):
        """Get thumbnail pixmap for a mod (first preview image) with proper aspect ratio"""
        if not mod_class.previewsPaths:
            return None
        
        # Try to load first preview image
        first_preview_path = mod_class.previewsPaths[0]
        
        # Create cache key with size
        cache_key = f"{first_preview_path}_{max_size}"
        
        # Check cache first
        if cache_key in self.cachePreviews:
            return self.cachePreviews[cache_key]
        
        # Load image
        if os.path.exists(first_preview_path):
            pixmap = QPixmap(first_preview_path)
            if not pixmap.isNull():
                original_width = pixmap.width()
                original_height = pixmap.height()
                
                if original_width > 0 and original_height > 0:
                    # Calculate aspect ratio
                    aspect_ratio = original_width / original_height
                    
                    # Calculate dimensions that fit within max_size while maintaining aspect ratio
                    # Use max_size as the maximum dimension (either width or height)
                    if aspect_ratio >= 1.0:  # Width >= Height (landscape or square)
                        new_width = max_size
                        new_height = int(max_size / aspect_ratio)
                    else:  # Height > Width (portrait)
                        new_height = max_size
                        new_width = int(max_size * aspect_ratio)
                    
                    # Scale with high quality transformation, maintaining aspect ratio
                    scaled_pixmap = pixmap.scaled(
                        new_width, new_height, 
                        Qt.KeepAspectRatio, 
                        Qt.SmoothTransformation
                    )
                    self.cachePreviews[cache_key] = scaled_pixmap
                    return scaled_pixmap
        
        return None
    
    def _createGridLayout(self, mods_to_display=None):
        """Create a 2-column grid layout for thumbnail view"""
        from PySide6.QtWidgets import QGridLayout, QWidget
        
        # Use provided mods or default to all mods
        if mods_to_display is None:
            mods_to_display = self.modsButtons
        
        # Create a container widget for the grid
        grid_container = QWidget()
        grid_layout = QGridLayout(grid_container)
        grid_layout.setSpacing(6)  # Reduced spacing between grid items
        grid_layout.setContentsMargins(4, 4, 4, 4)  # Reduced margins
        
        # Calculate item width based on available space
        available_width = self.modsList.width() - 20  # Account for margins and spacing
        item_width = max(150, (available_width - 10) // 2)  # 2 columns with spacing, minimum 150px
        
        # Add mods in 2-column grid
        row = 0
        col = 0
        for mod_button in mods_to_display:
            # Create a grid item widget for this mod
            grid_item = self._createGridItem(mod_button.modClass, item_width)
            grid_layout.addWidget(grid_item, row, col)
            
            col += 1
            if col >= 2:  # 2 columns
                col = 0
                row += 1
        
        # Add stretch to fill remaining space
        grid_layout.setRowStretch(row + 1, 1)
        
        # Add grid container to modsList
        layout = self.modsList.layout()
        if layout:
            layout.addWidget(grid_container)
            layout.addStretch()  # Add stretch to push items to top
    
    def _createGridItem(self, mod_class, item_width=180):
        """Create a grid item widget for a mod (thumbnail card) with proper aspect ratio"""
        from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
        
        # Calculate thumbnail width (account for margins and padding)
        thumbnail_max_width = item_width - 16  # Account for margins (8px each side)
        
        # Create container widget
        item_widget = QWidget()
        item_widget.setMinimumWidth(item_width)
        item_widget.setMaximumWidth(item_width)
        item_widget.setCursor(Qt.PointingHandCursor)
        item_widget.setProperty("modClass", mod_class)  # Store mod class reference
        
        # Check if this is the selected mod
        is_selected = (self.selectedModButton and 
                      self.selectedModButton.modClass == mod_class)
        
        if is_selected:
            item_widget.setStyleSheet("""
                QWidget {
                    background-color: #FF24638C;
                    border-radius: 8px;
                    border: 2px solid #43C15F;
                }
                QWidget:hover {
                    background-color: #FF24638C;
                }
            """)
        else:
            item_widget.setStyleSheet("""
                QWidget {
                    background-color: #0024638C;
                    border-radius: 8px;
                }
                QWidget:hover {
                    background-color: #7724638C;
                }
            """)
        
        layout = QVBoxLayout(item_widget)
        layout.setSpacing(3)  # Reduced spacing
        layout.setContentsMargins(6, 6, 6, 6)  # Reduced margins
        
        # Get thumbnail with proper aspect ratio first
        thumbnail_pixmap = self._getModThumbnail(mod_class, thumbnail_max_width)
        
        # Thumbnail image - size based on actual pixmap to maintain aspect ratio
        thumbnail_label = QLabel()
        thumbnail_label.setScaledContents(True)
        thumbnail_label.setStyleSheet("border-radius: 4px;")
        thumbnail_label.setAlignment(Qt.AlignCenter)
        
        if thumbnail_pixmap:
            # Use actual pixmap dimensions to maintain aspect ratio
            pixmap_width = thumbnail_pixmap.width()
            pixmap_height = thumbnail_pixmap.height()
            thumbnail_label.setPixmap(thumbnail_pixmap)
            thumbnail_label.setMinimumSize(pixmap_width, pixmap_height)
            thumbnail_label.setMaximumSize(pixmap_width, pixmap_height)
        else:
            # Use default preview
            default_pixmap = QPixmap(self.defaultPreview)
            if not default_pixmap.isNull():
                # Scale default preview maintaining aspect ratio
                scaled = default_pixmap.scaled(
                    thumbnail_max_width, thumbnail_max_width, 
                    Qt.KeepAspectRatio, 
                    Qt.SmoothTransformation
                )
                thumbnail_label.setPixmap(scaled)
                thumbnail_label.setMinimumSize(scaled.size())
                thumbnail_label.setMaximumSize(scaled.size())
        
        layout.addWidget(thumbnail_label)
        
        # Mod name
        name_label = QLabel(mod_class.name)
        name_label.setStyleSheet("color: #eeeeee; font-weight: bold; font-size: 11px;")
        name_label.setWordWrap(True)
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setMaximumWidth(thumbnail_max_width)
        layout.addWidget(name_label)
        
        # Author
        author_label = QLabel(f"by {mod_class.author}")
        author_label.setStyleSheet("color: #B1BA96; font-size: 9px;")
        author_label.setAlignment(Qt.AlignCenter)
        author_label.setWordWrap(True)
        author_label.setMaximumWidth(thumbnail_max_width)
        layout.addWidget(author_label)
        
        # Make clickable - connect to selectMod
        def on_click(event):
            self.selectMod(mod_class)
            # Refresh grid to update selection highlighting
            if self.currentViewMode == self.VIEW_GRID_THUMBNAIL:
                self.refreshModList()
        
        item_widget.mousePressEvent = on_click
        
        return item_widget

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
               modFileExist: bool,
               modPath: str,
               modCachePath: str,
               dateAdded: float,
               features: List[str] = None):

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
                       modFileExist,
                       modPath,
                       modCachePath,
                       dateAdded,
                       features)

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
        
        # Reset filtered mods list
        self.filteredModsButtons = []

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
            def get_mod_time(mod_button):
                timestamp = mod_button.modClass.dateAdded
                mod_hash = mod_button.modClass.hash

                if timestamp > 0:
                    return timestamp

                if mod_hash in self.mod_timestamps:
                    return self.mod_timestamps[mod_hash]

                new_timestamp = time.time()
                self.mod_timestamps[mod_hash] = new_timestamp
                self.save_timestamps()
                return new_timestamp
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

<<<<<<< Updated upstream
    def toggleViewMode(self):
        """Cycle through the three view modes"""
        if self.currentViewMode == self.VIEW_LIST:
            self.currentViewMode = self.VIEW_THUMBNAIL_TEXT
            self.ui.viewToggleButton.setIcon(QIcon(":/icons/resources/icons/thumbnail.png"))
        elif self.currentViewMode == self.VIEW_THUMBNAIL_TEXT:
            self.currentViewMode = self.VIEW_THUMBNAIL_ONLY
            self.ui.viewToggleButton.setIcon(QIcon(":/icons/resources/icons/About.png"))
        else:  # VIEW_THUMBNAIL_ONLY
            self.currentViewMode = self.VIEW_LIST
            self.ui.viewToggleButton.setIcon(QIcon(":/icons/resources/icons/SortModsList.png"))
        
        # Refresh the mod list with the new view mode
        self.refreshModList()

    def refreshModList(self):
        """Refresh the mod list with the current view mode"""
        # Store current selection
        selected_hash = None
        if self.selectedModButton:
            selected_hash = self.selectedModButton.modClass.hash
        
        # Clear current layout
        ClearFrame(self.modsList)
        
        # Recreate layout based on view mode
        if self.currentViewMode == self.VIEW_LIST:
            self.setupListView()
        elif self.currentViewMode == self.VIEW_THUMBNAIL_TEXT:
            self.setupThumbnailTextView()
        else:  # VIEW_THUMBNAIL_ONLY
            self.setupThumbnailOnlyView()
        
        # Restore selection
        if selected_hash:
            for modButton in self.modsButtons:
                if modButton.modClass.hash == selected_hash:
                    modButton.select()
                    break

    def setupListView(self):
        """Setup the traditional list view"""
        layout = QVBoxLayout(self.modsList)
        layout.setSpacing(1)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Add all mod buttons
        for modButton in self.modsButtons:
            layout.addWidget(modButton)

    def setupThumbnailTextView(self):
        """Setup thumbnail + text view"""
        layout = QVBoxLayout(self.modsList)
        layout.setSpacing(5)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Add all mod buttons with larger thumbnails
        for modButton in self.modsButtons:
            # Create a custom widget for thumbnail + text view
            thumbnail_widget = self.createThumbnailTextWidget(modButton)
            layout.addWidget(thumbnail_widget)

    def setupThumbnailOnlyView(self):
        """Setup thumbnail-only view with 2-column grid"""
        layout = QGridLayout(self.modsList)
        layout.setSpacing(5)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Add mod buttons in 2-column grid
        for i, modButton in enumerate(self.modsButtons):
            row = i // 2
            col = i % 2
            thumbnail_widget = self.createThumbnailOnlyWidget(modButton)
            layout.addWidget(thumbnail_widget, row, col)

    def createThumbnailTextWidget(self, modButton):
        """Create a widget for thumbnail + text view"""
        from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QLabel
        from PySide6.QtCore import Qt
        
        widget = QFrame()
        widget.setStyleSheet("""
            QFrame {
                background-color: #2C2C2C;
                border: 1px solid #404040;
                border-radius: 5px;
                padding: 5px;
            }
            QFrame:hover {
                background-color: #3C3C3C;
            }
        """)
        
        layout = QHBoxLayout(widget)
        layout.setSpacing(10)
        
        # Thumbnail
        thumbnail_label = QLabel()
        thumbnail_label.setFixedSize(80, 60)
        thumbnail_label.setStyleSheet("border: 1px solid #555;")
        thumbnail_label.setAlignment(Qt.AlignCenter)
        
        # Get first preview image
        if modButton.modClass.previewsPaths:
            preview_path = modButton.modClass.previewsPaths[0]
            if preview_path in self.cachePreviews:
                pixmap = self.cachePreviews[preview_path]
                thumbnail_label.setPixmap(pixmap.scaled(80, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                thumbnail_label.setText("No Preview")
        else:
            thumbnail_label.setText("No Preview")
        
        layout.addWidget(thumbnail_label)
        
        # Text info
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        
        name_label = QLabel(modButton.modClass.name)
        name_label.setStyleSheet("font-weight: bold; color: white;")
        text_layout.addWidget(name_label)
        
        author_label = QLabel(f"by {modButton.modClass.author}")
        author_label.setStyleSheet("color: #AAAAAA;")
        text_layout.addWidget(author_label)
        
        version_label = QLabel(f"[{modButton.modClass.gameVersion}]")
        if modButton.modClass.currentVersion:
            version_label.setStyleSheet("color: #43C15F;")
        else:
            version_label.setStyleSheet("color: #3FAED1;")
        text_layout.addWidget(version_label)
        
        layout.addLayout(text_layout)
        layout.addStretch()
        
        # Make it clickable
        widget.mousePressEvent = lambda event: modButton.select()
        
        return widget

    def createThumbnailOnlyWidget(self, modButton):
        """Create a widget for thumbnail-only view"""
        from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
        from PySide6.QtCore import Qt
        
        widget = QFrame()
        widget.setStyleSheet("""
            QFrame {
                background-color: #2C2C2C;
                border: 1px solid #404040;
                border-radius: 5px;
                padding: 5px;
            }
            QFrame:hover {
                background-color: #3C3C3C;
            }
        """)
        
        layout = QVBoxLayout(widget)
        layout.setSpacing(5)
        
        # Thumbnail
        thumbnail_label = QLabel()
        thumbnail_label.setFixedSize(120, 90)
        thumbnail_label.setStyleSheet("border: 1px solid #555;")
        thumbnail_label.setAlignment(Qt.AlignCenter)
        
        # Get first preview image
        if modButton.modClass.previewsPaths:
            preview_path = modButton.modClass.previewsPaths[0]
            if preview_path in self.cachePreviews:
                pixmap = self.cachePreviews[preview_path]
                thumbnail_label.setPixmap(pixmap.scaled(120, 90, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                thumbnail_label.setText("No Preview")
        else:
            thumbnail_label.setText("No Preview")
        
        layout.addWidget(thumbnail_label)
        
        # Make it clickable
        widget.mousePressEvent = lambda event: modButton.select()
        
        return widget
    
    def reapply_custom_styling(self):
        """Reapply all custom backgrounds and button styling after UI refresh"""
        self.set_mod_list_background()
        self.set_mod_description_background()
        QTimer.singleShot(100, self.set_bottom_bar_background)
        QTimer.singleShot(150, self._reapply_button_styling)

    def _reapply_button_styling(self):
        """Reapply button styling with delay"""
        self.setup_custom_install_button()
        self.setup_custom_delete_button()
        self.setup_custom_reinstall_button()
        self.setup_custom_uninstall_button()

    def resizeEvent(self, event):
        """Handle resize events with debouncing for smooth performance"""
        super().resizeEvent(event)
        
        # Only process resize events for the main Mods widget (not child widgets)
        if hasattr(self, '_last_size') and hasattr(self, '_resize_timer'):
            # Only update if size actually changed significantly
            current_size = event.size()
            if self._last_size is None or abs(current_size.width() - self._last_size.width()) > 5 or abs(current_size.height() - self._last_size.height()) > 5:
                self._last_size = current_size
                # Debounce resize updates to prevent excessive redraws
                self._resize_timer.stop()
                self._resize_timer.start(50)  # 50ms delay for smooth performance

    def _handle_delayed_resize(self):
        """Handle delayed resize updates for smooth performance"""
        # Update backgrounds with new size
        self.set_mod_list_background()
        self.set_mod_description_background()
        self.set_bottom_bar_background()
        
        # Update mod preview if visible
        if hasattr(self, 'body') and self.body.modPreview.isVisible():
            self.updatePreviewSize()

    def updatePreviewSize(self):
        """Update preview size efficiently"""
        if self.preview and not self.preview.isNull():
            # Get current preview frame size
            preview_size = self.body.modPreview.size()
            
            # Scale preview smoothly
            scaled_preview = self.preview.scaled(
                preview_size,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            
            # Update preview immediately for responsive feel
            self.body.modPreview.setPixmap(scaled_preview)


class FlowLayoutWidget(QWidget):
    """A custom widget that implements true flow layout like text wrapping"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.widgets = []
        self.setContentsMargins(15, 8, 15, 8)
        self.resize_timer = QTimer()
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self.updateLayout)
        
    def addWidget(self, widget):
        """Add a widget to the flow layout"""
        self.widgets.append(widget)
        widget.setParent(self)
        self.updateLayout()
        
    def forceUpdate(self):
        """Force an immediate layout update"""
        self.resize_timer.stop()
        self.updateLayout()
        
    def updateLayout(self):
        """Update the layout to flow like text"""
        if not self.widgets:
            return
            
        # Get available width with more padding - use actual widget width
        widget_width = self.width()
        available_width = widget_width - 50  # Increased padding for better wrapping
        if available_width <= 0:
            available_width = 400  # Fallback
            
        
        # Position widgets in flowing layout
        x = 0
        y = 0
        row_height = 0
        spacing = 8
        
        for widget in self.widgets:
            # Get widget size
            widget_size = widget.sizeHint()
            tag_width = widget_size.width()
            tag_height = widget_size.height()
            
            
            # Check if widget fits on current row
            if x + tag_width > available_width and x > 0:
                # Move to next row
                x = 0
                y += row_height + spacing
                row_height = 0
                
            # Position widget
            widget.move(x, y)
            widget.resize(tag_width, tag_height)
            widget.show()
            
            # Update position for next widget
            x += tag_width + spacing
            row_height = max(row_height, tag_height)
            
        # Update widget height
        total_height = y + row_height + 16  # Add bottom margin
        self.resize(widget_width, total_height)
        
        # Notify parent layout that size has changed
        self.updateGeometry()
        
        
    def resizeEvent(self, event):
        """Handle resize events to reflow the layout"""
        super().resizeEvent(event)
        # Use timer to debounce rapid resize events
        self.resize_timer.start(50)  # 50ms delay
        
    def sizeHint(self):
        """Return the preferred size"""
        if not self.widgets:
            return QSize(0, 0)
            
        # Calculate total height needed with more padding
        widget_width = self.width()
        available_width = widget_width - 50  # Increased padding for better wrapping
        if available_width <= 0:
            available_width = 400
            
        x = 0
        y = 0
        row_height = 0
        spacing = 8
        
        for widget in self.widgets:
            widget_size = widget.sizeHint()
            tag_width = widget_size.width()
            tag_height = widget_size.height()
            
            if x + tag_width > available_width and x > 0:
                x = 0
                y += row_height + spacing
                row_height = 0
                
            x += tag_width + spacing
            row_height = max(row_height, tag_height)
            
        total_height = y + row_height + 16
        return QSize(widget_width, total_height)
        
    def minimumSizeHint(self):
        """Return the minimum size"""
        return self.sizeHint()
        
    def hasHeightForWidth(self):
        """Tell Qt that this widget's height depends on its width"""
        return True
        
    def heightForWidth(self, width):
        """Calculate height based on width for proper layout integration"""
        if not self.widgets:
            return 0
            
        # Calculate total height needed for given width with more padding
        available_width = width - 50  # Increased padding for better wrapping
        if available_width <= 0:
            available_width = 400
            
        x = 0
        y = 0
        row_height = 0
        spacing = 8
        
        for widget in self.widgets:
            widget_size = widget.sizeHint()
            tag_width = widget_size.width()
            tag_height = widget_size.height()
            
            if x + tag_width > available_width and x > 0:
                x = 0
                y += row_height + spacing
                row_height = 0
                
            x += tag_width + spacing
            row_height = max(row_height, tag_height)
            
        total_height = y + row_height + 16
        return total_height


class DynamicFeatureContainer(QWidget):
    """Custom widget that dynamically wraps features based on available width"""
    
    def __init__(self):
        super().__init__()
        self.features = []
        self.setContentsMargins(15, 8, 15, 8)
        self.resize_timer = QTimer()
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self.updateLayout)
        
    def addFeature(self, feature_label):
        """Add a feature label to the container"""
        self.features.append(feature_label)
        feature_label.setParent(self)
        # Don't trigger automatic layout updates - they cause bubbles to disappear
        # QTimer.singleShot(100, self.updateLayout)
        
    def updateLayout(self):
        """Optimized layout update with caching and debouncing"""
        if not self.features:
            return
        
        # Force immediate layout update to ensure all features are positioned
        self._perform_layout_update()
    
    def _perform_layout_update(self):
        """Actual layout calculations with proper wrapping"""
        
        if not self.features:
            return
        
        # Get available width from parent
        parent = self.parent()
        if parent:
            available_width = parent.width() - 30  # 30px margin for padding
        else:
            available_width = 400
        
        # Ensure reasonable minimum width
        available_width = max(300, available_width)
        
        
        current_x = 0
        current_y = 0
        line_height = 0
        spacing = 6  # 6px spacing between features
        
        for i, feature in enumerate(self.features):
            
            # Force the feature to calculate its preferred size
            feature.adjustSize()
            feature_size = feature.sizeHint()
            feature_width = feature_size.width()
            feature_height = feature_size.height()
            
            
            # Check if this feature would overflow the line
            if current_x + feature_width > available_width and current_x > 0:
                # Move to next line
                current_x = 0
                current_y += line_height + 4  # 4px spacing between lines
                line_height = 0
            
            # Position the feature at its natural size
            feature.move(current_x, current_y)
            feature.resize(feature_width, feature_height)
            feature.show()
            
            
            # Update position for next feature
            current_x += feature_width + spacing
            line_height = max(line_height, feature_height)
        
        # Set container size to accommodate all features
        total_height = current_y + line_height + 20  # Add bottom margin
        self.setMinimumHeight(total_height)
        self.setMaximumHeight(total_height)  # Prevent vertical expansion
        self.setMinimumWidth(available_width)
        self.setMaximumWidth(available_width)  # Prevent horizontal expansion
        
        
        # Force parent to update
        if self.parent():
            self.parent().updateGeometry()
        
    def resizeEvent(self, event):
        """Handle resize events"""
        super().resizeEvent(event)
        # Don't trigger layout updates on resize - they cause bubbles to disappear
        # self.resize_timer.start(200)
        
    def showEvent(self, event):
        """Handle show events - update layout when widget becomes visible"""
        super().showEvent(event)
        # Don't trigger layout updates on show - they cause bubbles to disappear
        # QTimer.singleShot(100, self.updateLayout)
        
    def sizeHint(self):
        """Return the preferred size"""
        if not self.features:
            return QSize(0, 0)
            
        # Don't trigger layout updates in sizeHint - they cause bubbles to disappear
        # self.updateLayout()
        return self.minimumSizeHint()
        
    def minimumSizeHint(self):
        """Return the minimum size"""
        if not self.features:
            return QSize(0, 0)
            
        # Calculate minimum size needed
        total_width = sum(feature.sizeHint().width() for feature in self.features) + (len(self.features) - 1) * 6 + 30
        max_height = max(feature.sizeHint().height() for feature in self.features) + 40  # Add more height to prevent cutoff
        
        return QSize(total_width, max_height)


class DynamicFeatureContainerFixed(QWidget):
    """Custom widget that dynamically wraps features using the EXACT same logic as DynamicTagContainer"""
    
    def __init__(self):
        super().__init__()
        self.features = []  # Use 'features' instead of 'tags'
        self.setContentsMargins(15, 8, 15, 8)
        self.resize_timer = QTimer()
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self.updateLayout)
        
    def addFeature(self, feature_label):
        """Add a feature label to the container - same logic as addTag"""
        self.features.append(feature_label)
        feature_label.setParent(self)
        # Delay the layout update to ensure the widget is properly sized
        QTimer.singleShot(200, self.updateLayout)  # Increased from 50 to 200ms
        
    def updateLayout(self):
        """Optimized layout update with caching and debouncing - same as DynamicTagContainer"""
        if not self.features:
            return
        
        # Use debounced update to prevent excessive recalculations
        layout_manager.debounced_update(self, self._perform_layout_update, 100)  # Increased from 30 to 100ms
    
    def _perform_layout_update(self):
        """Actual layout calculations with caching - EXACT same logic as DynamicTagContainer"""
        
        current_size = self.size()
        
        # Check if we need to update based on size change
        if not layout_manager.should_update_layout(self, current_size):
            return
            
        # Get the actual mod description area width
        # Walk up to find the Mods widget and get its scrollBody width
        parent = self.parent()
        available_width = 400  # Default reasonable width
        
        if parent:
            
            # Walk up to find the Mods widget
            current = parent
            while current:
                if hasattr(current, 'ui') and hasattr(current.ui, 'scrollBody'):
                    # Found the Mods widget - use its scrollBody width
                    scroll_body_width = current.ui.scrollBody.width()
                    available_width = scroll_body_width - 100  # 100px margin for padding
                    break
                current = current.parent()
            
            # If we didn't find the Mods widget, use parent width
            if available_width == 400:
                available_width = parent.width() - 60
        
        # Use the actual available width without artificial constraints
        # The scrollBody width minus margin is the real available space
        
        current_x = 0
        current_y = 0
        line_height = 0
        
        for i, feature in enumerate(self.features):  # Use 'features' instead of 'tags'
            
            # Get the size the feature wants to be
            feature_size = feature.sizeHint()
            feature_width = feature_size.width()
            feature_height = feature_size.height()
            
            
            # If this feature would overflow, move to next line
            if current_x + feature_width > available_width and current_x > 0:
                current_x = 0
                current_y += line_height + 6  # 6px spacing between lines
                line_height = 0
                
            # Position the feature
            feature.move(current_x, current_y)
            feature.resize(feature_width, feature_height)
            feature.show()
            
            
            # Update position for next feature
            current_x += feature_width + 6  # 6px spacing between features (proper spacing)
            line_height = max(line_height, feature_height)
        
        # Set container size to accommodate all features
        total_height = current_y + line_height + 16  # Add bottom margin
        self.setMinimumHeight(total_height)
        self.setMaximumHeight(total_height)  # Prevent vertical expansion
        # Use the actual available width without constraints
        self.setMinimumWidth(available_width)
        self.setMaximumWidth(available_width)  # Use the actual available width
        
        
        # Notify parent layout that size has changed
        self.updateGeometry()
        
    def resizeEvent(self, event):
        """Handle resize events to reflow the layout"""
        super().resizeEvent(event)
        self.resize_timer.start(200)
        
    def showEvent(self, event):
        """Handle show events - update layout when widget becomes visible"""
        super().showEvent(event)
        QTimer.singleShot(100, self.updateLayout)
        
    def sizeHint(self):
        """Return the preferred size"""
        if not self.features:
            return QSize(0, 0)
            
        # Calculate size needed for all features
        return self.minimumSizeHint()
        
    def minimumSizeHint(self):
        """Return the minimum size"""
        if not self.features:
            return QSize(0, 0)
            
        # Calculate minimum size needed - account for proper spacing
        total_width = sum(feature.sizeHint().width() for feature in self.features) + (len(self.features) - 1) * 6 + 30
        max_height = max(feature.sizeHint().height() for feature in self.features) + 40
        
        return QSize(total_width, max_height)


class DynamicFeatureContainerFromTags(QWidget):
    """Features container that uses EXACT Tags logic but with proper spacing"""
    
    def __init__(self):
        super().__init__()
        self.features = []  # Use 'features' instead of 'tags'
        self.setContentsMargins(15, 8, 15, 8)
        self.resize_timer = QTimer()
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self.updateLayout)
        
    def addFeature(self, feature_label):
        """Add a feature label to the container - same logic as addTag"""
        self.features.append(feature_label)
        feature_label.setParent(self)
        # Delay the layout update to ensure the widget is properly sized
        QTimer.singleShot(50, self.updateLayout)
        
    def updateLayout(self):
        """Optimized layout update with caching and debouncing - same as DynamicTagContainer"""
        if not self.features:
            return
        
        # Use debounced update to prevent excessive recalculations
        layout_manager.debounced_update(self, self._perform_layout_update, 30)
    
    def _perform_layout_update(self):
        """Actual layout calculations with caching - EXACT same logic as DynamicTagContainer"""
        
        current_size = self.size()
        
        # Check if we need to update based on size change
        if not layout_manager.should_update_layout(self, current_size):
            return
            
        # Get the actual visible width from the mod description area
        parent = self.parent()
        available_width = 300  # Default fallback
        
        if parent:
            
            # Walk up to find the Mods widget and get its scrollBody width
            current = parent
            while current:
                if hasattr(current, 'ui') and hasattr(current.ui, 'scrollBody'):
                    # Found the Mods widget - use its scrollBody width
                    scroll_body_width = current.ui.scrollBody.width()
                    available_width = scroll_body_width - 100  # 100px margin for padding
                    break
                current = current.parent()
            
            # If we didn't find the Mods widget, use parent width
            if available_width == 300:
                available_width = parent.width() - 60
        
        # Ensure reasonable bounds for proper wrapping
        available_width = max(250, min(available_width, 500))  # Min 250px, max 500px
        
        current_x = 0
        current_y = 0
        line_height = 0
        
        for i, feature in enumerate(self.features):  # Use 'features' instead of 'tags'
            
            # Get the size the feature wants to be
            feature_size = feature.sizeHint()
            feature_width = feature_size.width()
            feature_height = feature_size.height()
            
            
            # If this feature would overflow, move to next line - MORE AGGRESSIVE WRAPPING
            if current_x + feature_width > available_width and current_x > 0:
                current_x = 0
                current_y += line_height + 6  # 6px spacing between lines
                line_height = 0
            elif current_x + feature_width > available_width:
                # Even if it's the first feature on a line, if it's too wide, wrap it
                current_x = 0
                current_y += line_height + 6
                line_height = 0
                
            # Position the feature
            feature.move(current_x, current_y)
            feature.resize(feature_width, feature_height)
            feature.show()  # Ensure feature is visible
            
            
            # Update position for next feature - USE PROPER SPACING
            current_x += feature_width + 6  # 6px spacing between features (proper spacing)
            line_height = max(line_height, feature_height)
        
        # Set container size to accommodate all features - DON'T CONSTRAIN WIDTH
        total_height = current_y + line_height + 16  # Add bottom margin
        self.setMinimumHeight(total_height)
        self.setMaximumHeight(total_height)  # Prevent vertical expansion
        # Don't constrain width - let it expand naturally
        self.setMinimumWidth(available_width)
        
        
        # Notify parent layout that size has changed
        self.updateGeometry()
        
    def resizeEvent(self, event):
        """Handle resize events to reflow the layout"""
        super().resizeEvent(event)
        self.resize_timer.start(200)
        
    def showEvent(self, event):
        """Handle show events - update layout when widget becomes visible"""
        super().showEvent(event)
        QTimer.singleShot(100, self.updateLayout)
        
    def sizeHint(self):
        """Return the preferred size"""
        if not self.features:
            return QSize(0, 0)
            
        # Calculate size needed for all features
        return self.minimumSizeHint()
        
    def minimumSizeHint(self):
        """Return the minimum size"""
        if not self.features:
            return QSize(0, 0)
            
        # Calculate minimum size needed - account for proper spacing
        total_width = sum(feature.sizeHint().width() for feature in self.features) + (len(self.features) - 1) * 6 + 30
        max_height = max(feature.sizeHint().height() for feature in self.features) + 40
        
        return QSize(total_width, max_height)


class DynamicTagContainer(QWidget):
    """Custom widget that dynamically wraps tags based on available width"""
    
    def __init__(self):
        super().__init__()
        self.tags = []
        self.setContentsMargins(15, 8, 15, 8)
        self.resize_timer = QTimer()
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self.updateLayout)
        
    def addTag(self, tag_label):
        """Add a tag label to the container"""
        self.tags.append(tag_label)
        tag_label.setParent(self)
        # Delay the layout update to ensure the widget is properly sized
        QTimer.singleShot(50, self.updateLayout)
        
    def updateLayout(self):
        """Optimized layout update with caching and debouncing"""
        if not self.tags:
            return
        
        # Use debounced update to prevent excessive recalculations
        layout_manager.debounced_update(self, self._perform_layout_update, 30)
    
    def _perform_layout_update(self):
        """Actual layout calculations with caching"""
        current_size = self.size()
        
        # Check if we need to update based on size change
        if not layout_manager.should_update_layout(self, current_size):
            return
            
        # SIMPLE APPROACH: Use the parent widget's width minus 20px margin
        parent = self.parent()
        if parent:
            available_width = parent.width() - 20  # 20px margin from visible edge
        else:
            available_width = 300
        
        # Ensure minimum width
        available_width = max(200, available_width)
        
        current_x = 0
        current_y = 0
        line_height = 0
        
        for tag in self.tags:
            # Get the size the tag wants to be
            tag_size = tag.sizeHint()
            tag_width = tag_size.width()
            tag_height = tag_size.height()
            
            # If this tag would overflow, move to next line
            if current_x + tag_width > available_width and current_x > 0:
                current_x = 0
                current_y += line_height + 6  # 6px spacing between lines
                line_height = 0
                
            # Position the tag
            tag.move(current_x, current_y)
            tag.resize(tag_width, tag_height)
            
            # Update position for next tag
            current_x += tag_width + 6  # 6px spacing between tags (consistent with feature bubbles)
            line_height = max(line_height, tag_height)
            
        # Update container height and width
        total_height = current_y + line_height + 2  # Reduced bottom margin from 8 to 2
        self.setMinimumHeight(total_height)
        self.setMaximumWidth(available_width)
        self.setMinimumWidth(200)  # Ensure minimum width
        
        # Force the parent layout to update
        if self.parent():
            self.parent().updateGeometry()
        
    def resizeEvent(self, event):
        """Handle resize events"""
        super().resizeEvent(event)
        # Use timer to debounce resize events
        self.resize_timer.start(50)
        
    def showEvent(self, event):
        """Handle show events - update layout when widget becomes visible"""
        super().showEvent(event)
        QTimer.singleShot(100, self.updateLayout)
        
    def sizeHint(self):
        """Return the preferred size"""
        if not self.tags:
            return QSize(0, 0)
            
        # Calculate size based on current layout
        self.updateLayout()
        return self.minimumSizeHint()
        
    def minimumSizeHint(self):
        """Return the minimum size"""
        if not self.tags:
            return QSize(0, 0)
            
        # Calculate minimum size needed
        total_width = sum(tag.sizeHint().width() for tag in self.tags) + (len(self.tags) - 1) * 1 + 30
        max_height = max(tag.sizeHint().height() for tag in self.tags) + 16
        
        return QSize(total_width, max_height)

    def reapply_custom_styling(self):
        """Reapply all custom backgrounds and button styling after UI refresh"""
        self.set_mod_list_background()
        self.set_mod_description_background()
        QTimer.singleShot(100, self.set_bottom_bar_background)
        QTimer.singleShot(150, self._reapply_button_styling)

    def _reapply_button_styling(self):
        """Reapply button styling with delay"""
        self.setup_custom_install_button()
        self.setup_custom_delete_button()
        self.setup_custom_reinstall_button()
        self.setup_custom_uninstall_button()

    def resizeEvent(self, event):
        """Handle resize events with debouncing for smooth performance"""
        super().resizeEvent(event)
        
        # Only process resize events for the main Mods widget (not child widgets)
        if hasattr(self, '_last_size') and hasattr(self, '_resize_timer'):
            # Only update if size actually changed significantly
            current_size = event.size()
            if self._last_size is None or abs(current_size.width() - self._last_size.width()) > 5 or abs(current_size.height() - self._last_size.height()) > 5:
                self._last_size = current_size
                # Debounce resize updates to prevent excessive redraws
                self._resize_timer.stop()
                self._resize_timer.start(50)  # 50ms delay for smooth performance

    def _handle_delayed_resize(self):
        """Handle delayed resize updates for smooth performance"""
        # Update backgrounds with new size
        self.set_mod_list_background()
        self.set_mod_description_background()
        self.set_bottom_bar_background()
        
        # Update mod preview if visible
        if hasattr(self, 'body') and self.body.modPreview.isVisible():
            self.updatePreviewSize()

    def updatePreviewSize(self):
        """Update preview size efficiently"""
        if self.preview and not self.preview.isNull():
            # Get current preview frame size
            preview_size = self.body.modPreview.size()
            
            # Scale preview smoothly
            scaled_preview = self.preview.scaled(
                preview_size,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            
            # Update preview immediately for responsive feel
            self.body.modPreview.setPixmap(scaled_preview)


>>>>>>> Stashed changes
