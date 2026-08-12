import sys
import ctypes
import io
import os
from PySide6.QtWidgets import QApplication, QStyleFactory, QSplashScreen
from PySide6.QtGui import QIcon, QPalette, QColor, QPixmap
from PySide6.QtCore import QSharedMemory, Qt
from controller import PdfToolboxApp

def main():
    # --- PYINSTALLER WINDOWED MODE FIX ---
    if sys.stdout is None:
        sys.stdout = io.StringIO()
    if sys.stderr is None:
        sys.stderr = io.StringIO()

    app = QApplication(sys.argv)

    # --- SPLASH SCREEN ---
    # We need to determine the path to icon.png before the controller is loaded
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
        
    # Load your existing icon and scale it up slightly for the loading screen
    splash_pixmap = QPixmap(os.path.join(base_path, "icon.png"))
    splash_pixmap = splash_pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    
    # Create the splash screen and force it to stay on top
    splash = QSplashScreen(splash_pixmap, Qt.WindowStaysOnTopHint)
    splash.show()
    app.processEvents() # Force the OS to draw the image immediately before moving on

    # --- SINGLE INSTANCE CHECK ---
    shared_memory = QSharedMemory("PdfToolbox_App_Instance")
    if not shared_memory.create(1):
        if sys.platform == 'win32':
            hwnd = ctypes.windll.user32.FindWindowW(None, "PDF Toolbox")
            if hwnd:
                ctypes.windll.user32.ShowWindow(hwnd, 9)  # 9 = SW_RESTORE
                ctypes.windll.user32.SetForegroundWindow(hwnd)
        return 0 

    # --- FORCE DARK MODE ---
    app.setStyle(QStyleFactory.create("Fusion"))
    dark_palette = QPalette()
    
    dark_palette.setColor(QPalette.Window, QColor(45, 45, 45))
    dark_palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
    dark_palette.setColor(QPalette.Base, QColor(30, 30, 30))
    dark_palette.setColor(QPalette.AlternateBase, QColor(45, 45, 45))
    dark_palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 255))
    dark_palette.setColor(QPalette.ToolTipText, QColor(255, 255, 255))
    dark_palette.setColor(QPalette.Text, QColor(255, 255, 255))
    dark_palette.setColor(QPalette.Button, QColor(45, 45, 45))
    dark_palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
    dark_palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
    dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.HighlightedText, QColor(0, 0, 0))
    
    app.setPalette(dark_palette)

    if sys.platform == 'win32':
        myappid = 'lourencolam.pdftoolbox.app.1.1'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    # Initialize the application controller (This is the heavy part that takes time)
    window = PdfToolboxApp()

    # Set the global application icon for the window frame and taskbar
    icon_path = window.resource_path("icon.png")
    app.setWindowIcon(QIcon(icon_path))

    # Show the window and instantly close the splash screen
    window.ui.show()
    splash.finish(window.ui)
    
    # Execute the app loop
    exit_code = app.exec()

    # Explicitly delete C++ objects before Python teardown
    del window
    del shared_memory
    
    return exit_code

if __name__ == "__main__":
    sys.exit(main())