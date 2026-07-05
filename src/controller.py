import sys
import os
import fitz  
import pdf_engine  
from PySide6.QtWidgets import QFileDialog, QMessageBox, QListWidgetItem, QLabel
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QIODevice, Qt, QSize, QUrl, QSettings, QEvent, QObject
from PySide6.QtGui import QImage, QPixmap, QIcon, QDesktopServices
from PySide6.QtGui import QImage, QPixmap, QIcon, QDesktopServices, QAction

class PdfToolboxApp(QObject):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("Louro Devs", "PDF Toolbox")
        self.load_ui()
        self.apply_ui_enhancements()
        self.populate_help_tab()
        self.initialize_signals()
        self.setup_menu_bar() # NEW
        self.setup_event_filters()
        # Run once at startup to show the watermarks on the empty lists
        self.update_watermarks()
        

    def resource_path(self, relative_path):
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, relative_path)
        return os.path.join(os.path.abspath("."), relative_path)

    def load_ui(self):
        ui_file_name = self.resource_path("main_window.ui")
        ui_file = QFile(ui_file_name)
        if not ui_file.open(QIODevice.ReadOnly):
            print(f"Error: Cannot locate {ui_file_name}.")
            sys.exit(-1)
        loader = QUiLoader()
        self.ui = loader.load(ui_file) 
        ui_file.close()
        self.ui.setWindowTitle("PDF Toolbox")

    def apply_ui_enhancements(self):
        self.ui.txtSplitPath.setPlaceholderText("Drag and Drop a PDF here...")
        
        # --- WATERMARK OVERLAYS ---
        # 1. Merge Tab Watermark
        self.watermark_merge = QLabel("Drag and Drop PDFs here...", self.ui.listMergeFiles)
        self.watermark_merge.setAlignment(Qt.AlignCenter)
        self.watermark_merge.setStyleSheet("color: rgba(128, 128, 128, 0.4); font-size: 18px; font-weight: bold; border: none;")
        self.watermark_merge.setAttribute(Qt.WA_TransparentForMouseEvents) # Clicks pass right through it

        # 2. Split Tab Watermark
        self.watermark_split = QLabel("Drag and Drop Target PDF here...", self.ui.listPages)
        self.watermark_split.setAlignment(Qt.AlignCenter)
        self.watermark_split.setStyleSheet("color: rgba(128, 128, 128, 0.4); font-size: 18px; font-weight: bold; border: none;")
        self.watermark_split.setAttribute(Qt.WA_TransparentForMouseEvents)

        custom_css = """
        QTabBar::tab { padding: 12px 30px; margin-right: 4px; font-size: 14px; font-weight: bold; border-top-left-radius: 6px; border-top-right-radius: 6px; }
        QTabBar::tab:selected { background-color: #0E639C; color: white; }
        QPushButton#btnAddFiles, QPushButton#btnSelectSplit { background-color: #2E7D32; color: white; font-weight: bold; font-size: 14px; padding: 10px; border-radius: 4px; }
        QPushButton#btnAddFiles:hover, QPushButton#btnSelectSplit:hover { background-color: #1B5E20; }
        QPushButton#btnMerge, QPushButton#btnSplit { background-color: #0E639C; color: white; font-weight: bold; font-size: 15px; padding: 14px; border-radius: 6px; margin-top: 10px; }
        QPushButton#btnMerge:hover, QPushButton#btnSplit:hover { background-color: #1177BB; }
        QPushButton#btnRemoveSelected, QPushButton#btnClearSplit { background-color: #C62828; color: white; font-weight: bold; }
        QPushButton#btnRemoveSelected:hover, QPushButton#btnClearSplit:hover { background-color: #B71C1C; }
        QListWidget::item { padding: 12px; font-size: 14px; border-bottom: 1px solid rgba(128, 128, 128, 0.2); }
        """
        self.ui.setStyleSheet(custom_css)
        self.ui.listPages.setIconSize(QSize(130, 170))
        self.ui.listPages.setGridSize(QSize(150, 200))

    def populate_help_tab(self):
        """Injects the comprehensive documentation into the How to Use tab."""
        if hasattr(self.ui, 'txtHelp'):
            help_content = """
            <h2 style="color: #4DA8DA;">Welcome to the PDF Toolbox</h2>
            <p>This application allows you to merge multiple PDF documents into one, or split specific pages from a PDF, all while maintaining internal data structures like hyperlinks and bookmarks.</p>
            
            <hr>
            
            <h3 style="color: #2E7D32;">Merging PDFs</h3>
            <ol>
                <li><b>Drag and Drop</b> your PDF files directly into the empty space, or click the green <b>Add Files...</b> button to select them.</li>
                <li>Select a file in the list and use the <b>Move Up (↑)</b> and <b>Move Down (↓)</b> buttons to arrange them in the exact order you want them stitched together.</li>
                <li>If you added a file by mistake, select it and click the red <b>Remove Selected</b> button.</li>
                <li>Once your sequence is ready, click the blue <b>Merge and Save!</b> button to combine them.</li>
            </ol>
            
            <hr>
            
            <h3 style="color: #2E7D32;">Splitting PDFs</h3>
            <ol>
                <li><b>Drag and Drop</b> your target document directly into the app, or click the green <b>Select PDF to Split...</b> button. A visual grid of the pages will automatically generate.</li>
                <li>Click the pages you wish to extract. You can hold <b>Cmd</b> to select multiple individual pages, or use the selection buttons above the grid.</li>
                <li>Choose your output method at the bottom:
                    <ul>
                        <li><b>Extract to Single PDF:</b> Takes the highlighted pages and stitches them into one new file.</li>
                        <li><b>Split into Separate PDFs:</b> Exports every highlighted page as its own individual PDF file into a folder of your choice.</li>
                    </ul>
                </li>
                <li>Click the blue <b>Split into Single Pages!</b> button to execute.</li>
            </ol>
            """
            self.ui.txtHelp.setHtml(help_content)

    def initialize_signals(self):
        self.ui.btnAddFiles.clicked.connect(self.add_merge_files)
        self.ui.btnRemoveSelected.clicked.connect(self.remove_selected_file)
        self.ui.btnMoveUp.clicked.connect(self.move_file_up)
        self.ui.btnMoveDown.clicked.connect(self.move_file_down)
        self.ui.btnMerge.clicked.connect(self.execute_merge)
        
        self.ui.btnSelectSplit.clicked.connect(self.execute_file_selection)
        self.ui.btnClearSplit.clicked.connect(self.clear_split_file)
        self.ui.btnSelectAll.clicked.connect(self.select_all_pages)
        self.ui.btnClear.clicked.connect(self.clear_page_selection)
        self.ui.btnInvert.clicked.connect(self.invert_page_selection)
        self.ui.btnSplit.clicked.connect(self.execute_split)

    def update_watermarks(self):
        """Hides or shows the watermarks depending on if the lists have items."""
        self.watermark_merge.setVisible(self.ui.listMergeFiles.count() == 0)
        self.watermark_split.setVisible(self.ui.listPages.count() == 0)

    # --- QSETTINGS HELPER METHODS ---
    def setup_menu_bar(self):
        """Constructs the native macOS system menu bar."""
        menu_bar = self.ui.menuBar()
        help_menu = menu_bar.addMenu("Help")

        about_action = QAction("About PDF Toolbox", self.ui)
        # AboutRole automatically routes this to the native Apple application menu
        about_action.setMenuRole(QAction.AboutRole) 
        about_action.triggered.connect(self.show_about_dialog)

        help_menu.addAction(about_action)

    def show_about_dialog(self):
        """Renders the official branding and version information."""
        about_text = """
        <center>
        <h2 style="color: #4DA8DA;">PDF Toolbox</h2>
        <p><b>Version 1.0.0</b></p>
        <p>Developed by Louro Devs</p>
        <p>A professional utility for precision PDF structural manipulation.</p>
        <hr>
        <p style="font-size: 11px; color: gray;">Copyright © 2026. All rights reserved.</p>
        </center>
        """
        QMessageBox.about(self.ui, "About PDF Toolbox", about_text)

    def get_last_dir(self):
        return self.settings.value("last_directory", os.path.expanduser("~"))

    def save_last_dir(self, file_path):
        self.settings.setValue("last_directory", os.path.dirname(file_path))

    # --- DRAG, DROP, AND RESIZE LOGIC ---
    def setup_event_filters(self):
        """Enables drag/drop and tracks resizing to keep watermarks centered."""
        self.ui.listMergeFiles.setAcceptDrops(True)
        self.ui.listMergeFiles.installEventFilter(self)
        
        self.ui.txtSplitPath.setAcceptDrops(True)
        self.ui.txtSplitPath.installEventFilter(self)
        
        # Upgrade: Allow dropping PDFs directly onto the Split grid!
        self.ui.listPages.setAcceptDrops(True)
        self.ui.listPages.installEventFilter(self)

    def eventFilter(self, watched, event):
        """Intercepts system events for resizing and dropping files."""
        # 1. Keep watermarks perfectly centered if the user resizes the app window
        if event.type() == QEvent.Resize:
            if watched == self.ui.listMergeFiles:
                self.watermark_merge.resize(event.size())
            elif watched == self.ui.listPages:
                self.watermark_split.resize(event.size())
                
        # 2. Intercept both DragEnter AND DragMove! 
        # This stops QListWidget's internal engine from rejecting external multi-file drops.
        elif event.type() in (QEvent.DragEnter, QEvent.DragMove):
            if event.mimeData().hasUrls():
                event.acceptProposedAction()
                return True
        
        # 3. Handle the actual Drop
        elif event.type() == QEvent.Drop:
            if event.mimeData().hasUrls():
                event.acceptProposedAction() # Formally accept the OS drop
                
                urls = event.mimeData().urls()
                # Extract all valid PDF paths from the drop data
                paths = [url.toLocalFile() for url in urls if url.toLocalFile().lower().endswith('.pdf')]
                
                if paths:
                    if watched == self.ui.listMergeFiles:
                        # Loop through EVERY path in the OS package and add it
                        for path in paths:
                            self.append_merge_file(path)
                        return True
                    elif watched in (self.ui.txtSplitPath, self.ui.listPages):
                        # The split tab still only takes one target file at a time
                        self.load_target_split_file(paths[0]) 
                        return True
                        
        return super().eventFilter(watched, event)

    # --- MERGE LOGIC ---
    def append_merge_file(self, path):
        item = QListWidgetItem(os.path.basename(path))
        item.setData(Qt.UserRole, path)
        self.ui.listMergeFiles.addItem(item)
        self.save_last_dir(path)
        self.update_watermarks() # Hide watermark when file added

    def add_merge_files(self):
        file_paths, _ = QFileDialog.getOpenFileNames(self.ui, "Select PDFs", self.get_last_dir(), "PDF Documents (*.pdf)")
        for path in file_paths:
            self.append_merge_file(path)

    def remove_selected_file(self):
        row = self.ui.listMergeFiles.currentRow()
        if row >= 0: 
            self.ui.listMergeFiles.takeItem(row)
            self.update_watermarks() # Show watermark if list is now empty

    def move_file_up(self):
        row = self.ui.listMergeFiles.currentRow()
        if row > 0:
            item = self.ui.listMergeFiles.takeItem(row)
            self.ui.listMergeFiles.insertItem(row - 1, item)
            self.ui.listMergeFiles.setCurrentRow(row - 1)

    def move_file_down(self):
        row = self.ui.listMergeFiles.currentRow()
        if row >= 0 and row < self.ui.listMergeFiles.count() - 1:
            item = self.ui.listMergeFiles.takeItem(row)
            self.ui.listMergeFiles.insertItem(row + 1, item)
            self.ui.listMergeFiles.setCurrentRow(row + 1)

    def execute_merge(self):
        count = self.ui.listMergeFiles.count()
        if count == 0: return
        save_path, _ = QFileDialog.getSaveFileName(self.ui, "Save Merged PDF", self.get_last_dir() + "/Merged_Document.pdf", "PDF Documents (*.pdf)")
        if not save_path: return

        try:
            file_paths = [self.ui.listMergeFiles.item(i).data(Qt.UserRole) for i in range(count)]
            pdf_engine.merge_pdfs(file_paths, save_path) 
            self.save_last_dir(save_path)
            
            msg_box = QMessageBox(self.ui)
            msg_box.setIcon(QMessageBox.Information)
            msg_box.setWindowTitle("Success!")
            msg_box.setText(f"Successfully merged {count} files!")
            open_btn = msg_box.addButton("Open File", QMessageBox.ActionRole)
            msg_box.addButton(QMessageBox.Ok)
            msg_box.exec()
            
            if msg_box.clickedButton() == open_btn:
                QDesktopServices.openUrl(QUrl.fromLocalFile(save_path))
        except Exception as e:
            QMessageBox.critical(self.ui, "Error", f"Failed to merge:\n{str(e)}")

    # --- SPLIT LOGIC ---
    def load_target_split_file(self, file_path):
        self.ui.txtSplitPath.setText(file_path)
        self.save_last_dir(file_path)
        self.load_split_preview(file_path)

    def execute_file_selection(self):
        file_path, _ = QFileDialog.getOpenFileName(self.ui, "Select Target PDF", self.get_last_dir(), "PDF Documents (*.pdf)")
        if file_path:
            self.load_target_split_file(file_path)

    def clear_split_file(self):
        if not self.ui.txtSplitPath.text(): return
        reply = QMessageBox.question(self.ui, "Confirm Clear", "Clear target file and previews?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.ui.txtSplitPath.clear()
            self.ui.listPages.clear()
            self.update_watermarks() # Show watermark when cleared

    def load_split_preview(self, file_path):
        self.ui.listPages.clear()
        try:
            doc = fitz.open(file_path)
            for i in range(len(doc)):
                page = doc.load_page(i)
                pix = page.get_pixmap(matrix=fitz.Matrix(0.15, 0.15))
                fmt = QImage.Format_RGBA8888 if pix.alpha else QImage.Format_RGB888
                img = QImage(pix.samples, pix.width, pix.height, pix.stride, fmt)
                item = QListWidgetItem(f"Page {i + 1}")
                item.setIcon(QIcon(QPixmap.fromImage(img)))
                item.setData(Qt.UserRole, i) 
                self.ui.listPages.addItem(item)
            doc.close()
            self.update_watermarks() # Hide watermark when previews load
        except Exception as e:
            print(f"Error: {e}")

    def select_all_pages(self):
        for i in range(self.ui.listPages.count()): self.ui.listPages.item(i).setSelected(True)

    def clear_page_selection(self):
        for i in range(self.ui.listPages.count()): self.ui.listPages.item(i).setSelected(False)

    def invert_page_selection(self):
        for i in range(self.ui.listPages.count()):
            item = self.ui.listPages.item(i)
            item.setSelected(not item.isSelected())

    def execute_split(self):
        source_path = self.ui.txtSplitPath.text()
        if not source_path: return
        selected_pages = sorted([item.data(Qt.UserRole) for item in self.ui.listPages.selectedItems()])
        if not selected_pages: return

        try:
            if self.ui.radioSingle.isChecked():
                save_path, _ = QFileDialog.getSaveFileName(self.ui, "Save PDF", self.get_last_dir() + "/Extracted_Pages.pdf", "PDF Documents (*.pdf)")
                if not save_path: return
                pdf_engine.extract_to_single_pdf(source_path, selected_pages, save_path)
                self.save_last_dir(save_path)
                
                msg_box = QMessageBox(self.ui)
                msg_box.setIcon(QMessageBox.Information)
                msg_box.setText("Pages extracted successfully!")
                open_btn = msg_box.addButton("Open File", QMessageBox.ActionRole)
                msg_box.addButton(QMessageBox.Ok)
                msg_box.exec()
                if msg_box.clickedButton() == open_btn: QDesktopServices.openUrl(QUrl.fromLocalFile(save_path))

            elif self.ui.radioSeparate.isChecked():
                save_dir = QFileDialog.getExistingDirectory(self.ui, "Select Folder", self.get_last_dir())
                if not save_dir: return
                pdf_engine.extract_to_separate_pdfs(source_path, selected_pages, save_dir)
                self.save_last_dir(save_dir)
                
                msg_box = QMessageBox(self.ui)
                msg_box.setIcon(QMessageBox.Information)
                msg_box.setText(f"Exported {len(selected_pages)} PDFs!")
                open_btn = msg_box.addButton("Open Folder", QMessageBox.ActionRole)
                msg_box.addButton(QMessageBox.Ok)
                msg_box.exec()
                if msg_box.clickedButton() == open_btn: QDesktopServices.openUrl(QUrl.fromLocalFile(save_dir))
        except Exception as e:
            QMessageBox.critical(self.ui, "Error", f"Failed to split PDF:\n{str(e)}")