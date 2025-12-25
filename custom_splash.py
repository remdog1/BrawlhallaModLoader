import sys
import os

splash_screen = None

def show_splash():
    """Show the custom splash screen - simplified version"""
    global splash_screen
    try:
        from PySide6.QtWidgets import QSplashScreen, QApplication
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QPixmap, QFont
        
        # Only create if we don't have one already
        if splash_screen is None:
            # Try multiple paths for the splash image
            possible_paths = []
            
            if getattr(sys, 'frozen', False):
                # In PyInstaller bundle, try sys._MEIPASS first
                possible_paths.append(os.path.join(sys._MEIPASS, "ui/ui_sources/resources/images/splash.png"))
                possible_paths.append(os.path.join(sys._MEIPASS, "splash.png"))
                possible_paths.append(os.path.join(os.path.dirname(sys.executable), "ui/ui_sources/resources/images/splash.png"))
                possible_paths.append(os.path.join(os.path.dirname(sys.executable), "splash.png"))
            else:
                # In development, try current directory and ui resources
                possible_paths.append("ui/ui_sources/resources/images/splash.png")
                possible_paths.append("splash.png")
                possible_paths.append(os.path.join(os.path.dirname(__file__), "ui/ui_sources/resources/images/splash.png"))
                possible_paths.append(os.path.join(os.path.dirname(__file__), "splash.png"))
            
            splash_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    splash_path = path
                    break
            
            if splash_path and os.path.exists(splash_path):
                pixmap = QPixmap(splash_path)
                if pixmap.isNull():
                    pixmap = QPixmap(400, 300)
                    pixmap.fill(Qt.blue)
            else:
                pixmap = QPixmap(400, 300)
                pixmap.fill(Qt.blue)
            
            splash_screen = QSplashScreen(pixmap)
            
            # Set up the splash screen
            splash_screen.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.SplashScreen)
            splash_screen.setAttribute(Qt.WA_TranslucentBackground, False)
            
            # Set font for text
            font = QFont("Arial", 12)
            splash_screen.setFont(font)
            
            # Show the splash screen
            splash_screen.show()
            splash_screen.raise_()
            splash_screen.activateWindow()
            
            # Process events to make sure it displays
            QApplication.processEvents()
        
        return splash_screen
    except Exception as e:
        return None

def update_splash_text(text):
    """Update splash screen text"""
    global splash_screen
    try:
        if splash_screen:
            from PySide6.QtCore import Qt
            from PySide6.QtWidgets import QApplication
            splash_screen.showMessage(text, Qt.AlignBottom | Qt.AlignCenter, Qt.white)
            QApplication.processEvents()
    except Exception as e:
        pass

def update_splash_progress(progress):
    """Update splash screen progress"""
    global splash_screen
    try:
        if splash_screen:
            from PySide6.QtCore import Qt
            from PySide6.QtWidgets import QApplication
            splash_screen.showMessage(f"Loading... {progress}%", Qt.AlignBottom | Qt.AlignCenter, Qt.white)
            QApplication.processEvents()
    except Exception as e:
        pass

def close_splash():
    """Close the splash screen"""
    global splash_screen
    try:
        if splash_screen:
            from PySide6.QtWidgets import QApplication
            splash_screen.close()
            QApplication.processEvents()
            splash_screen = None
    except Exception as e:
        splash_screen = None





