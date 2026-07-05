# PDF Toolbox

A robust, standalone desktop application engineered for the precise structural manipulation, concatenation, and extraction of PDF documents. 

Developed by Louro Devs, this utility provides a highly optimized graphical user interface (GUI) built upon the Qt framework, enabling professionals to process complex documentation without relying on cloud-based solutions or compromising data integrity.

## Core Capabilities

* **Sequence Concatenation:** Merges multiple PDF documents into a single contiguous file. Supports precise manual reordering and batch processing via OS-level drag-and-drop integration.
* **Structural Extraction:** Utilizes the PyMuPDF (MuPDF) rendering engine to generate high-fidelity visual page arrays. Users can isolate and extract specific page indices into a unified output file or iterate them into distinct, independent PDF files.
* **State Persistence:** Implements `QSettings` to maintain local execution context across sessions, optimizing repetitive filesystem navigations.
* **Cross-Platform Architecture:** The Model-View-Controller (MVC) decoupling ensures the core processing engine remains agnostic, allowing compilation for both macOS (Apple Silicon/Intel) and Windows environments.

## Technical Specifications & Dependencies

This application is built using Python and requires the following libraries for source execution:

* `PySide6` (Qt for Python GUI framework)
* `PyMuPDF` (High-performance C-based PDF rendering and manipulation)
* `pyqtdarktheme` (Native UI styling integration)

See `requirements.txt` for exact version targeting.

## Installation & Execution

### Standalone Executable (macOS)
1. Download the latest release from the `dist/` directory.
2. Transfer `PDF Toolbox.app` to your local `/Applications` directory.
3. Launch the application. *(Note: Initial execution may require bypassing macOS Gatekeeper for unsigned binaries via System Settings > Privacy & Security).*

### Source Compilation
To compile the standalone application from source utilizing PyInstaller, execute the following build directives within the virtual environment:

```bash
# Clean previous build caches
rm -rf build dist "PDF Toolbox.spec"

# Compile macOS Bundle
pyinstaller --name "PDF Toolbox" --windowed --icon="src/icon.icns" --add-data "src/main_window.ui:." --hidden-import controller --hidden-import pdf_engine src/main.py