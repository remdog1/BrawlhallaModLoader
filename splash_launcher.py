"""
Splash Launcher - Shows splash screen immediately, then launches main application
This runs before any heavy imports to show splash.png instantly
"""
import os
import sys
import subprocess
import time

def check_existing_instance():
    """Check if main application is already running and pass arguments to it"""
    try:
        from single_instance import check_single_instance, send_args_to_existing_instance
        
        # Check if another instance is running using mutex
        if check_single_instance():
            # Send command line arguments to the existing instance
            args = sys.argv[1:] if len(sys.argv) > 1 else []
            send_args_to_existing_instance(args)
            return True  # Successfully passed arguments to existing instance
        
        return False  # No existing instance
    except Exception as e:
        print(f"Error checking for existing instance: {e}")
        return False  # Assume no existing instance on error

def show_splash_immediately():
    """Show splash.png using a minimal PySide6 window - appears instantly"""
    try:
        # Import only what we need for splash
        from PySide6.QtWidgets import QApplication, QSplashScreen
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QPixmap
        
        # Create minimal QApplication
        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)
        
        # Find splash.png
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        
        splash_paths = [
            os.path.join(base_dir, 'splash.png'),
            os.path.join(base_dir, 'ui', 'ui_sources', 'resources', 'images', 'splash.png'),
        ]
        
        splash_path = None
        for path in splash_paths:
            if os.path.exists(path):
                splash_path = path
                break
        
        if splash_path:
            pixmap = QPixmap(splash_path)
            if not pixmap.isNull():
                splash = QSplashScreen(pixmap)
                splash.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.SplashScreen)
                splash.show()
                app.processEvents()
                return app, splash
        
        # If no splash image, return app without splash
        return app, None
    except Exception as e:
        print(f"Could not show splash: {e}")
        return None, None

if __name__ == "__main__":
    # First, check if main application is already running
    # If so, pass arguments to it and exit (don't show splash or launch new instance)
    if check_existing_instance():
        # Successfully passed arguments to existing instance, exit
        sys.exit(0)
    
    # No existing instance, show splash and launch main application
    app, splash = show_splash_immediately()
    
    if app:
        # Process events to ensure splash displays
        app.processEvents()
        time.sleep(0.1)  # Brief pause to ensure splash is visible
        app.processEvents()
    
    # Launch main application
    if getattr(sys, 'frozen', False):
        # We are the launcher exe, launch the main exe
        base_dir = os.path.dirname(sys.executable)
        main_exe = os.path.join(base_dir, "Brawlhalla Mod Loader 2025 Beta_main.exe")
        if os.path.exists(main_exe):
            # Pass through all command line arguments
            # Keep splash alive until main app starts
            process = subprocess.Popen([main_exe] + sys.argv[1:])
            # Wait a moment for main app to start, then close splash
            time.sleep(0.5)
            if splash:
                splash.close()
            if app:
                app.quit()
        else:
            print(f"Main executable not found: {main_exe}")
            if splash:
                splash.close()
            if app:
                app.quit()
    else:
        # Development mode - import and run main
        # Keep splash alive during import
        if splash:
            app.processEvents()
        
        from main import RunApp
        # Close splash before main app starts its own
        if splash:
            splash.close()
            app.processEvents()
        
        RunApp()
        
        if app:
            app.quit()
