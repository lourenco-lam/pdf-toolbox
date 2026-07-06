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

    # 3. Set the global application icon dynamically based on the OS
    icon_extension = "ico" if sys.platform == "win32" else "icns"
    app.setWindowIcon(QIcon(window.resource_path(f"src/icon.{icon_extension}")))

    # 4. Show the window and execute the app loop
    window.ui.show()
    sys.exit(app.exec())