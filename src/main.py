import sys
import ctypes
import io
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from controller import PdfToolboxApp

if __name__ == "__main__":
    # --- PYINSTALLER WINDOWED MODE FIX ---
    # Redirect standard output/error to a dummy stream so libraries 
    # that attempt to print to the console do not crash the GUI.
    if sys.stdout is None:
        sys.stdout = io.StringIO()
    if sys.stderr is None:
        sys.stderr = io.StringIO()

    app = QApplication(sys.argv)

    # Force Windows to recognize the app ID for the taskbar
    if sys.platform == 'win32':
        myappid = 'lourencolam.pdftoolbox.app.1.1'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    # Initialize the application controller
    window = PdfToolboxApp()

    # Set the global application icon for the window frame and taskbar
    icon_path = window.resource_path("icon.png")
    app.setWindowIcon(QIcon(icon_path))

    # Show the window and execute the app loop
    window.ui.show()
    sys.exit(app.exec())