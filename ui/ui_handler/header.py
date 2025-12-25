from PySide6.QtWidgets import QWidget, QFrame
from PySide6.QtCore import QSize, QPropertyAnimation, QEasingCurve, Qt
from PySide6.QtGui import QPixmap, QBrush, QPalette, QIcon
import os

from .performance import animation_manager

from ..ui_sources.ui_header import Ui_Header
from ..utils.buttongroup import ButtonGroup
from ..utils.buttons import ButtonTextSize


class HeaderButton(ButtonGroup):
    duration = 150
    easingCurve = QEasingCurve.OutBack

    def __init__(self, button, line, frame, isDefault=False, method=None):
        self.line: QFrame = line
        self.frame: QFrame = frame

        self.animPlus: QPropertyAnimation = None
        self.animMinus: QPropertyAnimation = None

        #self.button.setCursor(QCursor(Qt.PointingHandCursor))

        super().__init__("headerTabs", button, method=method)

        width = self.resizeFrame()
        if isDefault:
            self.button.setChecked(True)
            self.line.setMinimumWidth(width)
            self.pressedMethod()
            
        # For PNG buttons, we might want to hide the line animation
        # Check if this is the mods button (has PNG styling)
        if hasattr(button, 'styleSheet') and 'background-image' in button.styleSheet():
            # This is a PNG button, hide the line
            self.line.setVisible(False)

    def resizeFrame(self):
        # For PNG buttons, use fixed width instead of text-based width
        if hasattr(self.button, 'styleSheet') and 'background-image' in self.button.styleSheet():
            # This is a PNG button, use reduced width for closer spacing (140 instead of 160)
            width = 140  # Reduced from 160 to bring buttons closer together
            self.frame.setMinimumWidth(width)
            return width
        else:
            # Original text-based sizing
            width = ButtonTextSize(self.button).width()
            self.frame.setMinimumWidth(width + 30)
            return width + 30

    def enter(self):
        if not self.button.isChecked():
            if self.animMinus is None:
                default = 0
            else:
                default = self.animMinus.currentValue()

            self.animPlus = QPropertyAnimation(self.line, b"minimumWidth")
            self.animPlus.setDuration(self.duration)
            self.animPlus.setStartValue(default)
            self.animPlus.setEndValue(self.frame.width()//2)
            self.animPlus.setEasingCurve(self.easingCurve)
            self.animPlus.start()

    def leave(self):
        if not self.button.isChecked():
            if self.animPlus is None:
                default = self.frame.width()
            else:
                default = self.animPlus.currentValue()

                if default == self.frame.width():
                    default = self.frame.width()//2

            self.animMinus = QPropertyAnimation(self.line, b"minimumWidth")
            self.animMinus.setDuration(self.duration)
            self.animMinus.setStartValue(default)
            self.animMinus.setEndValue(0)
            self.animMinus.setEasingCurve(self.easingCurve)
            self.animMinus.start()

    def released(self):
        self.button.setAutoExclusive(False)
        self.button.setChecked(True)
        self.button.setAutoExclusive(True)

        return True

    def pressed(self):
        if self.button.isChecked():
            return True

        else:
            if self.animPlus is None:
                oldWidth = 0
            else:
                oldWidth = self.animPlus.currentValue()
                if oldWidth == self.frame.width():
                    oldWidth = self.frame.width() // 2

            self.animPlus = QPropertyAnimation(self.line, b"minimumWidth")
            self.animPlus.setDuration(self.duration)
            self.animPlus.setStartValue(oldWidth)
            self.animPlus.setEndValue(self.frame.width())
            self.animPlus.setEasingCurve(QEasingCurve.InCubic)
            self.animPlus.start()

            for headerButton in self.getSelfGroup():
                if headerButton.button.isChecked():
                    headerButton.button.setAutoExclusive(False)
                    headerButton.button.setChecked(False)
                    headerButton.leave()
                    headerButton.button.setAutoExclusive(True)
                    break

            self.pressedMethod()

            return False


class HeaderIconButton(ButtonGroup):
    duration = 100
    easingCurve = QEasingCurve.OutBack

    baseSize = 26
    hoverSize = 28
    pressSize = 24

    def __init__(self, button, method=None):
        super().__init__("headerButtons", button, method=method)

        self.animPlus: QPropertyAnimation = QPropertyAnimation(self.button, b"iconSize")
        self.animPlus.setDuration(self.duration)
        self.animPlus.setEasingCurve(self.easingCurve)
        self.animPlus.setStartValue(QSize(self.baseSize, self.baseSize))

        self.animMinus: QPropertyAnimation = QPropertyAnimation(self.button, b"iconSize")
        self.animMinus.setDuration(self.duration)
        self.animMinus.setEasingCurve(self.easingCurve)
        self.animMinus.setStartValue(QSize(self.baseSize, self.baseSize))

    def enter(self):
        self.animPlus.setStartValue(self.animPlus.currentValue())
        self.animPlus.setEndValue(QSize(self.hoverSize, self.hoverSize))
        self.animPlus.start()

    def leave(self):
        self.animMinus.setStartValue(self.animPlus.currentValue())
        self.animMinus.setEndValue(QSize(self.baseSize, self.baseSize))
        self.animMinus.start()

    def pressed(self):
        self.animMinus.setStartValue(self.animPlus.currentValue())
        self.animMinus.setEndValue(QSize(self.pressSize, self.pressSize))
        self.animMinus.start()

        self.pressedMethod()
        return False

    def released(self):
        self.animPlus.setStartValue(self.animPlus.currentValue())
        self.animPlus.setEndValue(QSize(self.hoverSize, self.hoverSize))
        self.animPlus.start()
        return False


class HeaderFrame(QWidget):
    buttonAnimPlus = None
    buttonAnimMinus = None

    def __init__(self, githubMethod, supportMethod, infoMethod):
        super().__init__()

        self.ui = Ui_Header()
        self.ui.setupUi(self)

        # Set up background image
        self.bg_path = os.path.join(os.path.dirname(__file__), '..', 'ui_sources', 'resources', 'icons', 'uiupdate', 'top_nav_background.png')
        self.set_header_background()

        # Set up custom PNG mods button
        self.setup_custom_mods_button()
        
        # Set up custom PNG gamebanana button
        self.setup_custom_gamebanana_button()
        
        # Set up custom PNG settings button
        self.setup_custom_settings_button()

        self.headerModsButton = HeaderButton(self.ui.modsButton,
                                             self.ui.modsLine,
                                             self.ui.modsButtonFrame,
                                             isDefault=True, method=lambda: print("Mods"))
        self.headerGamebananaButton = HeaderButton(self.ui.gamebananaButton,
                                                   self.ui.gamebananaLine,
                                                   self.ui.gamebananaButtonFrame,
                                                   method=self.open_gamebanana_website)
        self.headerSettingsButton = HeaderButton(self.ui.settingsButton,
                                                 self.ui.settingsLine,
                                                 self.ui.settingsButtonFrame)
        
        # Hide the unused Tools button to fix spacing
        self.ui.toolsButton.setVisible(False)
        self.ui.toolsButtonFrame.setVisible(False)

        # self.headerGithubButton = HeaderIconButton(self.ui.githubButton, githubMethod)  # Removed
        # self.headerSupportButton = HeaderIconButton(self.ui.supportButton, supportMethod)  # Removed
        self.headerLanguageButton = HeaderIconButton(self.ui.languageButton)
        self.headerInfoButton = HeaderIconButton(self.ui.infoButton, infoMethod)
        
        # Hide the GitHub and support/Patreon buttons
        self.ui.githubButton.setVisible(False)
        self.ui.supportButton.setVisible(False)


    def set_header_background(self):
        """Set the background image for the header using QPixmap"""
        if os.path.exists(self.bg_path):
            pixmap = QPixmap(self.bg_path)
            scaled_pixmap = pixmap.scaled(
                self.ui.buttonsFrame.size(),
                Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation
            )
            palette = self.ui.buttonsFrame.palette()
            palette.setBrush(self.ui.buttonsFrame.backgroundRole(), QBrush(scaled_pixmap))
            self.ui.buttonsFrame.setPalette(palette)
            self.ui.buttonsFrame.setAutoFillBackground(True)

    def setup_custom_mods_button(self):
        """Set up the mods button with custom PNG images and hover effects"""
        # Paths to the PNG images
        normal_png = os.path.join(os.path.dirname(__file__), '..', 'ui_sources', 'resources', 'icons', 'uiupdate', 'mods_button.png')
        hover_png = os.path.join(os.path.dirname(__file__), '..', 'ui_sources', 'resources', 'icons', 'uiupdate', 'hovered_mods_button.png')
        
        if os.path.exists(normal_png) and os.path.exists(hover_png):
            
            # Load the images as QPixmaps to check their size
            normal_pixmap = QPixmap(normal_png)
            hover_pixmap = QPixmap(hover_png)
            
            # Scale down the images to fit the button (increased by 1/3: 107x40)
            scaled_normal = normal_pixmap.scaled(107, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            scaled_hover = hover_pixmap.scaled(107, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            
            # Create icons from scaled pixmaps
            normal_icon = QIcon(scaled_normal)
            hover_icon = QIcon(scaled_hover)
            
            # Set up the button with icons
            self.ui.modsButton.setIcon(normal_icon)
            self.ui.modsButton.setIconSize(QSize(107, 40))
            
            # Hide text
            self.ui.modsButton.setText("")
            
            # Set transparent background
            self.ui.modsButton.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: none;
                    color: transparent;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.1);
                }
            """)
            
            # Set button size (reduced width for closer spacing: 140x51)
            self.ui.modsButton.setMinimumSize(QSize(140, 51))
            self.ui.modsButton.setMaximumSize(QSize(140, 51))
            
            # Store icons for state changes
            self.normal_icon = normal_icon
            self.hover_icon = hover_icon
            
            # Connect hover events to change icon
            self.ui.modsButton.enterEvent = self.on_mods_button_enter
            self.ui.modsButton.leaveEvent = self.on_mods_button_leave
            
            # Set initial icon based on button state (mods button starts as checked/active)
            if self.ui.modsButton.isChecked():
                self.ui.modsButton.setIcon(self.hover_icon)  # Use hover icon for active state
            else:
                self.ui.modsButton.setIcon(self.normal_icon)
            
        else:
            pass
            # Fallback to original styling
            self.ui.modsButton.setStyleSheet("""
                QPushButton {
                    color: #eeeeee;
                    background-color: transparent;
                    border: none;
                }
            """)
    
    def on_mods_button_enter(self, event):
        """Handle mouse enter event for mods button with animation"""
        if hasattr(self, 'hover_icon'):
            self.ui.modsButton.setIcon(self.hover_icon)
        # Add smooth hover scale animation
        animation_manager.smooth_hover_scale(self.ui.modsButton, 1.05, 150)
        super().enterEvent(event)
    
    def on_mods_button_leave(self, event):
        """Handle mouse leave event for mods button with animation"""
        # Use hover icon if button is checked (active), otherwise use normal icon
        if hasattr(self, 'hover_icon') and hasattr(self, 'normal_icon'):
            if self.ui.modsButton.isChecked():
                self.ui.modsButton.setIcon(self.hover_icon)  # Keep hover icon when active
            else:
                self.ui.modsButton.setIcon(self.normal_icon)  # Use normal icon when inactive
        # Add smooth return animation
        animation_manager.smooth_hover_return(self.ui.modsButton, 150)
        super().leaveEvent(event)

    def setup_custom_gamebanana_button(self):
        """Set up the gamebanana button with custom PNG image and hover state"""
        # Paths to the PNG images
        gamebanana_png = os.path.join(os.path.dirname(__file__), '..', 'ui_sources', 'resources', 'icons', 'uiupdate', 'gamebanana_buttons.png')
        gamebanana_hover_png = os.path.join(os.path.dirname(__file__), '..', 'ui_sources', 'resources', 'icons', 'uiupdate', 'hovered_gamebanana_buttons.png')
        
        if os.path.exists(gamebanana_png) and os.path.exists(gamebanana_hover_png):
            # Load the images as QPixmaps to check their size
            gamebanana_pixmap = QPixmap(gamebanana_png)
            gamebanana_hover_pixmap = QPixmap(gamebanana_hover_png)
            
            # Scale down the images to fit the button (increased by 1/3: 107x31)
            scaled_gamebanana = gamebanana_pixmap.scaled(107, 31, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            scaled_gamebanana_hover = gamebanana_hover_pixmap.scaled(107, 31, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            
            # Create icons from scaled pixmaps
            gamebanana_icon = QIcon(scaled_gamebanana)
            gamebanana_hover_icon = QIcon(scaled_gamebanana_hover)
            
            # Set up the button with icon
            self.ui.gamebananaButton.setIcon(gamebanana_icon)
            self.ui.gamebananaButton.setIconSize(QSize(107, 31))
            
            # Hide text
            self.ui.gamebananaButton.setText("")
            
            # Set transparent background
            self.ui.gamebananaButton.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: none;
                    color: transparent;
                }
            """)
            
            # Set button size to accommodate the PNG image properly (reduced width for closer spacing: 140x51)
            self.ui.gamebananaButton.setMinimumSize(QSize(140, 51))
            self.ui.gamebananaButton.setMaximumSize(QSize(140, 51))
            
            # Store icons for state changes
            self.gamebanana_icon = gamebanana_icon
            self.gamebanana_hover_icon = gamebanana_hover_icon
            
            # Connect hover events to change icon
            self.ui.gamebananaButton.enterEvent = self.on_gamebanana_button_enter
            self.ui.gamebananaButton.leaveEvent = self.on_gamebanana_button_leave
            
        else:
            pass
            # Fallback to original styling
            self.ui.gamebananaButton.setStyleSheet("""
                QPushButton {
                    color: #eeeeee;
                    background-color: transparent;
                    border: none;
                }
            """)
    
    def on_gamebanana_button_enter(self, event):
        """Handle mouse enter event for gamebanana button with animation"""
        if hasattr(self, 'gamebanana_hover_icon'):
            self.ui.gamebananaButton.setIcon(self.gamebanana_hover_icon)
        # Add smooth hover scale animation
        animation_manager.smooth_hover_scale(self.ui.gamebananaButton, 1.05, 150)
        super().enterEvent(event)
    
    def on_gamebanana_button_leave(self, event):
        """Handle mouse leave event for gamebanana button with animation"""
        if hasattr(self, 'gamebanana_icon'):
            self.ui.gamebananaButton.setIcon(self.gamebanana_icon)
        # Add smooth return animation
        animation_manager.smooth_hover_return(self.ui.gamebananaButton, 150)
        super().leaveEvent(event)
    
    def open_gamebanana_website(self):
        """Open GameBanana website in default browser"""
        import webbrowser
        gamebanana_url = "https://gamebanana.com/games/5704"
        webbrowser.open(gamebanana_url)

    def setup_custom_settings_button(self):
        """Set up the settings button with custom PNG image and hover state"""
        # Paths to the PNG images
        settings_png = os.path.join(os.path.dirname(__file__), '..', 'ui_sources', 'resources', 'icons', 'uiupdate', 'settings_button.png')
        settings_hover_png = os.path.join(os.path.dirname(__file__), '..', 'ui_sources', 'resources', 'icons', 'uiupdate', 'hovered_settings_button.png')
        
        if os.path.exists(settings_png) and os.path.exists(settings_hover_png):
            # Load the images as QPixmaps to check their size
            settings_pixmap = QPixmap(settings_png)
            settings_hover_pixmap = QPixmap(settings_hover_png)
            
            # Scale down the images to fit the button (increased by 1/3: 107x31)
            scaled_settings = settings_pixmap.scaled(107, 31, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            scaled_settings_hover = settings_hover_pixmap.scaled(107, 31, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            
            # Create icons from scaled pixmaps
            settings_icon = QIcon(scaled_settings)
            settings_hover_icon = QIcon(scaled_settings_hover)
            
            # Set up the button with icon
            self.ui.settingsButton.setIcon(settings_icon)
            self.ui.settingsButton.setIconSize(QSize(107, 31))
            
            # Hide text
            self.ui.settingsButton.setText("")
            
            # Set transparent background
            self.ui.settingsButton.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: none;
                    color: transparent;
                }
            """)
            
            # Set button size to accommodate the PNG image properly (reduced width for closer spacing: 140x51)
            self.ui.settingsButton.setMinimumSize(QSize(140, 51))
            self.ui.settingsButton.setMaximumSize(QSize(140, 51))
            
            # Store icons for state changes
            self.settings_icon = settings_icon
            self.settings_hover_icon = settings_hover_icon
            
            # Connect hover events to change icon
            self.ui.settingsButton.enterEvent = self.on_settings_button_enter
            self.ui.settingsButton.leaveEvent = self.on_settings_button_leave
            
        else:
            pass
            # Fallback to original styling
            self.ui.settingsButton.setStyleSheet("""
                QPushButton {
                    color: #eeeeee;
                    background-color: transparent;
                    border: none;
                }
            """)
    
    def on_settings_button_enter(self, event):
        """Handle mouse enter event for settings button with animation"""
        if hasattr(self, 'settings_hover_icon'):
            self.ui.settingsButton.setIcon(self.settings_hover_icon)
        # Add smooth hover scale animation
        animation_manager.smooth_hover_scale(self.ui.settingsButton, 1.05, 150)
        super().enterEvent(event)
    
    def on_settings_button_leave(self, event):
        """Handle mouse leave event for settings button with animation"""
        if hasattr(self, 'settings_icon'):
            self.ui.settingsButton.setIcon(self.settings_icon)
        # Add smooth return animation
        animation_manager.smooth_hover_return(self.ui.settingsButton, 150)
        super().leaveEvent(event)

    def setModsButtonPressed(self, method):
        self.headerModsButton.setPressed(method)

    def setGamebananaButtonPressed(self, method):
        self.headerGamebananaButton.setPressed(method)

    def setSettingsButtonPressed(self, method):
        self.headerSettingsButton.setPressed(method)

    def resizeEvent(self, event):
        size = self.size()
        new_size = event.size()
        self.resize(QSize(new_size.width(), size.height()))
        # Update background when resizing
        self.set_header_background()
    
    def restore_background(self):
        """Restore the header background after UI refresh"""
        self.set_header_background()

