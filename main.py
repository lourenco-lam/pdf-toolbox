import sys
import qdarktheme
from PySide6.QtWidgets import QApplication
from controller import PdfToolboxApp  # Imports our new controller module

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Base dark theme
    app.setStyleSheet(qdarktheme.load_stylesheet("dark"))
    
    # Initialize the controller and render the UI
    toolbox = PdfToolboxApp()
    toolbox.ui.show()
    
    # Execute the event loop
    sys.exit(app.exec())