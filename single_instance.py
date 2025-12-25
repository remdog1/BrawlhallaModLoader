"""
Single Instance Detection Module
Uses Windows Mutex for reliable single-instance detection across all entry points
Based on: https://www.sqlpey.com/python/ensuring-single-instance-python/
"""
import sys
import os

# Mutex name - must be unique for this application
MUTEX_NAME = "BrawlhallaModLoader2025Beta_SingleInstance"

# Module-level mutex handle
_mutex_handle = None

def check_single_instance():
    """
    Check if another instance is already running using Windows Mutex.
    Returns True if another instance is running, False otherwise.
    """
    if sys.platform != "win32":
        # For non-Windows, fall back to a simple check
        # This could be enhanced with file locks or sockets for cross-platform support
        return False
    
    try:
        import win32event
        import win32api
        import winerror
        
        # Try to create a mutex
        # If it already exists, GetLastError will return ERROR_ALREADY_EXISTS
        global _mutex_handle
        _mutex_handle = win32event.CreateMutex(None, False, MUTEX_NAME)
        
        # Check if mutex already existed
        if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
            # Another instance is running
            return True
        
        # We successfully created the mutex - we're the first instance
        return False
        
    except ImportError:
        # pywin32 not available, fall back to QLocalSocket method
        print("Warning: win32event not available, using QLocalSocket fallback")
        return check_single_instance_socket()
    except Exception as e:
        print(f"Error checking single instance with mutex: {e}")
        # Fall back to socket method
        return check_single_instance_socket()

def check_single_instance_socket():
    """
    Fallback method using QLocalSocket (Qt's IPC mechanism)
    """
    try:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtNetwork import QLocalSocket
        
        SERVER_NAME = "brawlhalla-mod-loader-ipc-socket"
        
        # Create minimal QApplication for socket operations
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        socket = QLocalSocket()
        socket.connectToServer(SERVER_NAME)
        app.processEvents()
        
        # Give it a moment to connect
        import time
        time.sleep(0.1)
        app.processEvents()
        
        # If connection is successful, another instance is running
        if socket.waitForConnected(1000):
            socket.close()
            app.quit()
            return True
        
        socket.close()
        app.quit()
        return False
        
    except Exception as e:
        print(f"Error checking single instance with socket: {e}")
        return False

def send_args_to_existing_instance(args):
    """
    Send command line arguments to the existing running instance via QLocalSocket
    """
    try:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtNetwork import QLocalSocket
        
        SERVER_NAME = "brawlhalla-mod-loader-ipc-socket"
        
        # Create minimal QApplication for socket operations
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        # Try multiple times to connect (server might not be ready immediately)
        max_attempts = 5
        for attempt in range(max_attempts):
            socket = QLocalSocket()
            socket.connectToServer(SERVER_NAME)
            app.processEvents()
            
            import time
            time.sleep(0.3)  # Give it time to connect
            app.processEvents()
            
            if socket.waitForConnected(2000):
                # Send arguments
                if args:
                    args_str = '\n'.join(args).encode('utf-8')
                    socket.write(args_str)
                    app.processEvents()
                    
                    if socket.waitForBytesWritten(3000):
                        socket.flush()
                        socket.disconnectFromServer()
                        socket.close()
                        app.quit()
                        print(f"✓ Successfully forwarded {len(args)} argument(s) to existing instance")
                        return True
                    else:
                        print(f"Warning: Could not write arguments (attempt {attempt + 1}/{max_attempts})")
                else:
                    # No arguments, just bring window to front
                    socket.disconnectFromServer()
                    socket.close()
                    app.quit()
                    return True
            
            socket.close()
            
            # If connection failed and we have more attempts, wait a bit longer
            if attempt < max_attempts - 1:
                time.sleep(0.5)
                app.processEvents()
        
        app.quit()
        print("Warning: Could not connect to existing instance after multiple attempts")
        return False
        
    except Exception as e:
        print(f"Error sending args to existing instance: {e}")
        import traceback
        traceback.print_exc()
        return False

def release_mutex():
    """
    Release the mutex when the application exits
    """
    global _mutex_handle
    if _mutex_handle:
        try:
            import win32api
            win32api.CloseHandle(_mutex_handle)
            _mutex_handle = None
        except:
            pass

