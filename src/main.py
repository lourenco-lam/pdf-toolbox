import sys
import ctypes
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from controller import PdfToolboxApp

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 1. Force Windows to recognize the app ID for the taskbar
    if sys.platform == 'win32':
        myappid = 'lourencolam.pdftoolbox.app.1.0'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    # 2. Initialize the application controller
    window = PdfToolboxApp()

    # 3. Set the global application icon for the window frame and taskbar
    # Using the exact same bulletproof path we used for the UI banner
    icon_path = window.resource_path("icon.png")
    app.setWindowIcon(QIcon(icon_path))

    # 4. Show the window and execute the app loop
    window.ui.show()
    sys.exit(app.exec())