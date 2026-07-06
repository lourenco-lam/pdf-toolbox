import sys
import os
import tempfile
import fitz  
import pdf_engine  
from docx2pdf import convert # New import for Word conversion
from PySide6.QtWidgets import (QFileDialog, QMessageBox, QListWidgetItem, QLabel, 
                               QListView, QMenu, QPushButton, QStackedWidget, QApplication)
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import (QFile, QIODevice, Qt, QSize, QUrl, QSettings, QEvent, QObject,
                            QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QRect)
from PySide6.QtGui import QImage, QPixmap, QIcon, QDesktopServices, QAction


class TabSlideAnimator(QObject):
    def __init__(self, tab_widget, duration=260, parent=None):
        super().__init__(parent)
        self.tab_widget = tab_widget
        self.duration = duration
        self.stack = tab_widget.findChild(QStackedWidget)

        self._pending_pixmap = None
        self._pending_index = tab_widget.currentIndex()
        self._overlay_old = None
        self._overlay_new = None
        self._anim_group = None

        tab_widget.tabBarClicked.connect(self._capture_before_switch)
        tab_widget.currentChanged.connect(self._animate_switch)

    def _capture_before_switch(self, clicked_index):
        current = self.tab_widget.currentWidget()
        if current is not None and current.isVisible():
            self._pending_pixmap = current.grab()
        self._pending_index = self.tab_widget.currentIndex()

    def _animate_switch(self, new_index):
        old_pixmap = self._pending_pixmap
        old_index = self._pending_index
        self._pending_pixmap = None

        if old_pixmap is None or new_index == old_index:
            return

        new_widget = self.tab_widget.currentWidget()
        if new_widget is None:
            return

        area_rect = self.stack.geometry() if self.stack else self.tab_widget.rect()
        new_pixmap = new_widget.grab()
        direction = 1 if new_index > old_index else -1
        width = area_rect.width()

        self._cleanup()  

        self._overlay_old = QLabel(self.tab_widget)
        self._overlay_old.setPixmap(old_pixmap)
        self._overlay_old.setGeometry(area_rect)
        self._overlay_old.show()
        self._overlay_old.raise_()

        start_new_rect = QRect(area_rect.x() + direction * width, area_rect.y(),
                                area_rect.width(), area_rect.height())
        self._overlay_new = QLabel(self.tab_widget)
        self._overlay_new.setPixmap(new_pixmap)
        self._overlay_new.setGeometry(start_new_rect)
        self._overlay_new.show()
        self._overlay_new.raise_()

        end_old_rect = QRect(area_rect.x() - direction * width, area_rect.y(),
                              area_rect.width(), area_rect.height())

        anim_old = QPropertyAnimation(self._overlay_old, b"geometry", self)
        anim_old.setDuration(self.duration)
        anim_old.setStartValue(area_rect)
        anim_old.setEndValue(end_old_rect)
        anim_old.setEasingCurve(QEasingCurve.OutCubic)

        anim_new = QPropertyAnimation(self._overlay_new, b"geometry", self)
        anim_new.setDuration(self.duration)
        anim_new.setStartValue(start_new_rect)
        anim_new.setEndValue(area_rect)
        anim_new.setEasingCurve(QEasingCurve.OutCubic)

        self._anim_group = QParallelAnimationGroup(self)
        self._anim_group.addAnimation(anim_old)
        self._anim_group.addAnimation(anim_new)
        self._anim_group.finished.connect(self._cleanup)
        self._anim_group.start()

    def _cleanup(self):
        if self._overlay_old is not None:
            self._overlay_old.deleteLater()
            self._overlay_old = None
        if self._overlay_new is not None:
            self._overlay_new.deleteLater()
            self._overlay_new = None


class PdfToolboxApp(QObject):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("Louro Devs", "PDF Toolbox")
        self.temp_word_pdf = None # Holds the background converted PDF path
        self.load_ui()
        self.setup_tab_animation()
        self.apply_ui_enhancements()
        self.setup_app_menu()
        self.initialize_signals()
        self.setup_menu_bar() 
        self.setup_event_filters()
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

        if hasattr(self.ui, 'icon_label'):
            self.ui.icon_label.setFixedSize(32, 32)
            self.ui.icon_label.setScaledContents(True)
            self.ui.icon_label.setPixmap(QPixmap(self.resource_path("icon.png")))

    def setup_tab_animation(self):
        if hasattr(self.ui, 'tabWidget'):
            self._tab_animator = TabSlideAnimator(self.ui.tabWidget, duration=260, parent=self)

    def apply_ui_enhancements(self):
        self.ui.txtSplitPath.setPlaceholderText("Drag and Drop a PDF here...")
        if hasattr(self.ui, 'txtWordPath'):
            self.ui.txtWordPath.setPlaceholderText("Drag and Drop a Word Document here...")
        
        # --- WATERMARK OVERLAYS ---
        self.watermark_merge = QLabel("Drag and Drop PDFs here...", self.ui.listMergeFiles)
        self.watermark_merge.setAlignment(Qt.AlignCenter)
        self.watermark_merge.setStyleSheet("color: rgba(128, 128, 128, 0.4); font-size: 18px; font-weight: bold; border: none;")
        self.watermark_merge.setAttribute(Qt.WA_TransparentForMouseEvents) 

        self.watermark_split = QLabel("Drag and Drop Target PDF here...", self.ui.listPages)
        self.watermark_split.setAlignment(Qt.AlignCenter)
        self.watermark_split.setStyleSheet("color: rgba(128, 128, 128, 0.4); font-size: 18px; font-weight: bold; border: none;")
        self.watermark_split.setAttribute(Qt.WA_TransparentForMouseEvents)

        if hasattr(self.ui, 'listWordPages'):
            self.watermark_word = QLabel("Drag and Drop Target Word Doc here...", self.ui.listWordPages)
            self.watermark_word.setAlignment(Qt.AlignCenter)
            self.watermark_word.setStyleSheet("color: rgba(128, 128, 128, 0.4); font-size: 18px; font-weight: bold; border: none;")
            self.watermark_word.setAttribute(Qt.WA_TransparentForMouseEvents)

        # --- GRID JUSTIFICATION ---
        for list_view in [self.ui.listPages, getattr(self.ui, 'listWordPages', None)]:
            if list_view:
                list_view.setResizeMode(QListView.Adjust)
                list_view.setUniformItemSizes(True)
                list_view.setWordWrap(True)
                list_view.setSpacing(10)
                list_view.setIconSize(QSize(130, 170))
                list_view.setGridSize(QSize(150, 200))

        # --- CUSTOM MERGE LIST DRAG & DROP UI ---
        self.ui.listMergeFiles.setDragEnabled(True)
        self.ui.listMergeFiles.setAcceptDrops(True)
        self.ui.listMergeFiles.setDropIndicatorShown(True)
        self.ui.listMergeFiles.setDragDropMode(QListView.InternalMove)
        self.ui.listMergeFiles.viewport().setCursor(Qt.OpenHandCursor)

        # --- ALL-ROUNDED THEME CSS ---
        custom_css = """
        /* Header Banner */
        QFrame#header_frame { background-color: rgb(49, 216, 75); border: none; padding: 5px; }
        QLabel#title_label { color: black; font-size: 18px; font-weight: bold; }

        /* Generic Buttons */
        QPushButton { border: 2px solid rgb(49, 216, 75); border-radius: 12px; padding: 8px 16px; font-weight: bold; background-color: #2D2D30; color: white; }
        QPushButton:hover { background-color: #3D3D40; }
        
        /* Functional Colors & Hover States (Mapped for all Tabs) */
        QPushButton#btnAddFiles, QPushButton#btnSelectSplit, QPushButton#btnSelectWord { border: 2px solid #0E639C; background-color: #0E639C; color: white; }
        QPushButton#btnAddFiles:hover, QPushButton#btnSelectSplit:hover, QPushButton#btnSelectWord:hover { background-color: #1177BB; border-color: #1177BB; }
        
        QPushButton#btnRemoveSelected, QPushButton#btnClearSplit, QPushButton#btnClearWord { border: 2px solid #C62828; background-color: #C62828; color: white; }
        QPushButton#btnRemoveSelected:hover, QPushButton#btnClearSplit:hover, QPushButton#btnClearWord:hover { background-color: #D32F2F; border-color: #D32F2F; }
        
        QPushButton#btnMerge, QPushButton#btnSplit, QPushButton#btnConvertWord { border: 2px solid rgb(49, 216, 75); background-color: rgb(49, 216, 75); color: black; }
        QPushButton#btnMerge:hover, QPushButton#btnSplit:hover, QPushButton#btnConvertWord:hover { background-color: rgb(69, 236, 95); border-color: rgb(69, 236, 95); }
        
        /* Tabs */
        QTabBar::tab { padding: 10px 25px; margin: 5px; border-radius: 12px; font-weight: bold; background-color: #2D2D30; color: #aaa; }
        QTabBar::tab:selected { background-color: rgb(49, 216, 75); color: black; }

        /* List Widgets */
        QListWidget { border: 2px solid #444; border-radius: 12px; background: #1e1e1e; }
        QListWidget::item { border-radius: 8px; margin: 4px; padding: 8px; }
        QListWidget::item:selected { background-color: #5C6BC0; }
        
        /* Menu Button */
        QPushButton#menu_button { border: none; background: transparent; font-size: 24px; border-radius: 4px; }
        QPushButton#menu_button:hover { background-color: rgba(255, 255, 255, 0.2); }

        /* Radio Button Hover Effect */
        QRadioButton { color: white; spacing: 10px; }
        QRadioButton::indicator { width: 18px; height: 18px; border-radius: 9px; border: 2px solid #555; background-color: #2D2D30; }
        QRadioButton::indicator:hover { border: 2px solid rgb(49, 216, 75); }
        QRadioButton::indicator:checked { background-color: rgb(49, 216, 75); border: 2px solid rgb(49, 216, 75); }
        """
        self.ui.setStyleSheet(custom_css)

    def setup_app_menu(self):
        if not hasattr(self.ui, 'menu_button'): return
        self.app_menu = QMenu(self.ui)
        how_to_action = QAction("How to Use", self.ui)
        about_action = QAction("About PDF Toolbox", self.ui)
        self.app_menu.addAction(how_to_action)
        self.app_menu.addAction(about_action)
        how_to_action.triggered.connect(self.show_how_to_popup)
        about_action.triggered.connect(self.show_about_popup)
        self.ui.menu_button.clicked.connect(self.show_dropdown_menu)

    def show_dropdown_menu(self):
        button = self.ui.menu_button
        pos = button.mapToGlobal(button.rect().bottomLeft())
        self.app_menu.exec(pos)

    def show_how_to_popup(self):
        msg = QMessageBox(self.ui)
        msg.setWindowTitle("How to Use PDF Toolbox")
        msg.setStyleSheet("QMessageBox { background-color: #1e1e1e; color: white; min-width: 550px; } QLabel { color: white; font-size: 13px; } QPushButton { background-color: #444444; color: white; padding: 6px 20px; border-radius: 4px; font-weight: bold; } QPushButton:hover { background-color: #555555; }")
        
        long_content = """
        <h2 style="color: #4DA8DA; margin-bottom: 0px;">Welcome to the PDF Toolbox</h2>
        <p style="color: #aaaaaa; margin-top: 0px;">This application allows you to manipulate PDF structures and convert Word documents.</p>
        
        <hr style="background-color: #444; border: none; height: 1px;">
        <h3 style="color: #2E7D32;">Merging PDFs</h3>
        <ol>
            <li style="margin-bottom: 8px;"><b>Drag and Drop</b> your PDF files directly into the empty space.</li>
            <li style="margin-bottom: 8px;">Rearrange the order by <b>dragging the files up and down</b>.</li>
            <li style="margin-bottom: 8px;">Click the green <b>Merge and Save!</b> button.</li>
        </ol>
        <hr style="background-color: #444; border: none; height: 1px;">
        <h3 style="color: #2E7D32;">Splitting / Word to PDF</h3>
        <ol>
            <li style="margin-bottom: 8px;"><b>Drag and Drop</b> your target PDF or Word file into the app. A visual grid will generate.</li>
            <li style="margin-bottom: 8px;">Select the pages you wish to extract or convert.</li>
            <li style="margin-bottom: 8px;">Choose to output as a single stitched PDF, or as separate individual PDF files.</li>
            <li>Click the green <b>Execute</b> button.</li>
        </ol>
        """
        msg.setText(long_content)
        msg.exec()
        
    def show_about_popup(self):
        msg = QMessageBox(self.ui)
        msg.setWindowTitle("About")
        msg.setStyleSheet("QMessageBox { background-color: #1e1e1e; color: white; } QLabel { color: white; } QPushButton { background-color: #444444; color: white; padding: 6px 20px; border-radius: 4px; } QPushButton:hover { background-color: #555555; }")
        
        about_text = """
        <center>
        <h2 style="color: #ffffff;">PDF Toolbox</h2>
        <p style="color: #cccccc;">Version 1.1.0</p>
        <br>
        <p>Developed by Louro Devs</p>
        <p>A professional utility for precision PDF and Document manipulation.</p>
        <hr>
        <p style='font-size: 11px; color: #888888;'>Copyright © 2026. All rights reserved.</p>
        </center>
        """
        msg.setText(about_text)
        msg.exec()

    def initialize_signals(self):
        # Merge Signals
        self.ui.btnAddFiles.clicked.connect(self.add_merge_files)
        self.ui.btnRemoveSelected.clicked.connect(self.remove_selected_file)
        self.ui.btnMoveUp.clicked.connect(self.move_file_up)
        self.ui.btnMoveDown.clicked.connect(self.move_file_down)
        self.ui.btnMerge.clicked.connect(self.execute_merge)
        
        # Split Signals
        self.ui.btnSelectSplit.clicked.connect(self.execute_file_selection)
        self.ui.btnClearSplit.clicked.connect(self.clear_split_file)
        self.ui.btnSelectAll.clicked.connect(self.select_all_pages)
        self.ui.btnClear.clicked.connect(self.clear_page_selection)
        self.ui.btnInvert.clicked.connect(self.invert_page_selection)
        self.ui.btnSplit.clicked.connect(self.execute_split)
        
        # Word Signals
        if hasattr(self.ui, 'btnSelectWord'):
            self.ui.btnSelectWord.clicked.connect(self.execute_word_selection)
            self.ui.btnClearWord.clicked.connect(self.clear_word_file)
            self.ui.btnWordSelectAll.clicked.connect(self.select_all_word_pages)
            self.ui.btnWordClear.clicked.connect(self.clear_word_selection)
            self.ui.btnWordInvert.clicked.connect(self.invert_word_selection)
            self.ui.btnConvertWord.clicked.connect(self.execute_word_conversion)

    def update_watermarks(self):
        self.watermark_merge.setVisible(self.ui.listMergeFiles.count() == 0)
        self.watermark_split.setVisible(self.ui.listPages.count() == 0)
        if hasattr(self, 'watermark_word'):
            self.watermark_word.setVisible(self.ui.listWordPages.count() == 0)

    def setup_menu_bar(self):
        menu_bar = self.ui.menuBar()
        help_menu = menu_bar.addMenu("Help")
        about_action = QAction("About", self.ui)
        about_action.triggered.connect(self.show_about_popup)
        help_menu.addAction(about_action)

    def get_last_dir(self): return self.settings.value("last_directory", os.path.expanduser("~"))
    def save_last_dir(self, file_path): self.settings.setValue("last_directory", os.path.dirname(file_path))

    def setup_event_filters(self):
        self.ui.listMergeFiles.installEventFilter(self)
        self.ui.listMergeFiles.viewport().installEventFilter(self)
        
        self.ui.txtSplitPath.setAcceptDrops(True)
        self.ui.txtSplitPath.installEventFilter(self)
        self.ui.listPages.setAcceptDrops(True)
        self.ui.listPages.installEventFilter(self)

        if hasattr(self.ui, 'txtWordPath'):
            self.ui.txtWordPath.setAcceptDrops(True)
            self.ui.txtWordPath.installEventFilter(self)
            self.ui.listWordPages.setAcceptDrops(True)
            self.ui.listWordPages.installEventFilter(self)

    def eventFilter(self, watched, event):
        if watched == self.ui.listMergeFiles.viewport():
            if event.type() == QEvent.MouseButtonPress: self.ui.listMergeFiles.viewport().setCursor(Qt.ClosedHandCursor)
            elif event.type() == QEvent.MouseButtonRelease: self.ui.listMergeFiles.viewport().setCursor(Qt.OpenHandCursor)
        if event.type() == QEvent.Resize:
            if watched == self.ui.listMergeFiles: self.watermark_merge.resize(event.size())
            elif watched == self.ui.listPages: self.watermark_split.resize(event.size())
            elif hasattr(self, 'watermark_word') and watched == self.ui.listWordPages: self.watermark_word.resize(event.size())
        elif event.type() in (QEvent.DragEnter, QEvent.DragMove):
            if event.mimeData().hasUrls(): event.acceptProposedAction(); return True
        elif event.type() == QEvent.Drop:
            if event.mimeData().hasUrls():
                event.acceptProposedAction()
                paths = [u.toLocalFile() for u in event.mimeData().urls()]
                if paths:
                    p = paths[0]
                    # Route to proper tab based on file extension
                    if p.lower().endswith('.pdf'):
                        if watched == self.ui.listMergeFiles: 
                            [self.append_merge_file(file_path) for file_path in paths if file_path.lower().endswith('.pdf')]
                        elif watched in (self.ui.txtSplitPath, self.ui.listPages): 
                            self.load_target_split_file(p)
                    elif p.lower().endswith(('.doc', '.docx')):
                        if hasattr(self.ui, 'txtWordPath') and watched in (self.ui.txtWordPath, self.ui.listWordPages):
                            self.load_target_word_file(p)
                return True
        return super().eventFilter(watched, event)

    # --- MERGE LOGIC ---
    def append_merge_file(self, path):
        item = QListWidgetItem(os.path.basename(path))
        item.setData(Qt.UserRole, path)
        self.ui.listMergeFiles.addItem(item)
        self.update_watermarks()

    def add_merge_files(self):
        fps, _ = QFileDialog.getOpenFileNames(self.ui, "Select PDFs", self.get_last_dir(), "PDF Documents (*.pdf)")
        for p in fps: self.append_merge_file(p)

    def remove_selected_file(self):
        row = self.ui.listMergeFiles.currentRow()
        if row >= 0: self.ui.listMergeFiles.takeItem(row); self.update_watermarks()

    def move_file_up(self):
        row = self.ui.listMergeFiles.currentRow()
        if row > 0: item = self.ui.listMergeFiles.takeItem(row); self.ui.listMergeFiles.insertItem(row - 1, item); self.ui.listMergeFiles.setCurrentRow(row - 1)

    def move_file_down(self):
        row = self.ui.listMergeFiles.currentRow()
        if row >= 0 and row < self.ui.listMergeFiles.count() - 1: item = self.ui.listMergeFiles.takeItem(row); self.ui.listMergeFiles.insertItem(row + 1, item); self.ui.listMergeFiles.setCurrentRow(row + 1)

    def execute_merge(self):
        c = self.ui.listMergeFiles.count()
        if c == 0: return
        s, _ = QFileDialog.getSaveFileName(self.ui, "Save", self.get_last_dir() + "/Merged.pdf", "PDF (*.pdf)")
        if s: 
            pdf_engine.merge_pdfs([self.ui.listMergeFiles.item(i).data(Qt.UserRole) for i in range(c)], s)
            
            # Message box with Open File option
            msg = QMessageBox(self.ui)
            msg.setWindowTitle("Success")
            msg.setText("Files Merged Successfully!")
            open_btn = msg.addButton("Open File", QMessageBox.ActionRole)
            msg.addButton("OK", QMessageBox.AcceptRole)
            msg.exec()
            
            if msg.clickedButton() == open_btn:
                QDesktopServices.openUrl(QUrl.fromLocalFile(s))

    # --- SPLIT LOGIC ---
    def load_target_split_file(self, fp):
        self.ui.txtSplitPath.setText(fp)
        self.load_preview_grid(fp, self.ui.listPages)

    def execute_file_selection(self):
        fp, _ = QFileDialog.getOpenFileName(self.ui, "Select PDF", self.get_last_dir(), "PDF (*.pdf)")
        if fp: self.load_target_split_file(fp)

    def clear_split_file(self):
        self.ui.txtSplitPath.clear(); self.ui.listPages.clear(); self.update_watermarks()

    def select_all_pages(self): [self.ui.listPages.item(i).setSelected(True) for i in range(self.ui.listPages.count())]
    def clear_page_selection(self): [self.ui.listPages.item(i).setSelected(False) for i in range(self.ui.listPages.count())]
    def invert_page_selection(self): [self.ui.listPages.item(i).setSelected(not self.ui.listPages.item(i).isSelected()) for i in range(self.ui.listPages.count())]

    def execute_split(self):
        sp = self.ui.txtSplitPath.text()
        if not sp: return
        pages = sorted([i.data(Qt.UserRole) for i in self.ui.listPages.selectedItems()])
        if not pages: return
        try:
            if self.ui.radioSingle.isChecked():
                s, _ = QFileDialog.getSaveFileName(self.ui, "Save", "", "PDF (*.pdf)")
                if s: 
                    pdf_engine.extract_to_single_pdf(sp, pages, s)
                    msg = QMessageBox(self.ui)
                    msg.setWindowTitle("Success")
                    msg.setText("PDF Split Successfully!")
                    open_btn = msg.addButton("Open File", QMessageBox.ActionRole)
                    msg.addButton("OK", QMessageBox.AcceptRole)
                    msg.exec()
                    if msg.clickedButton() == open_btn: QDesktopServices.openUrl(QUrl.fromLocalFile(s))
            elif self.ui.radioSeparate.isChecked():
                sd = QFileDialog.getExistingDirectory(self.ui, "Select Folder")
                if sd: 
                    pdf_engine.extract_to_separate_pdfs(sp, pages, sd)
                    QMessageBox.information(self.ui, "Success", "Pages extracted to folder!")
        except Exception as e: QMessageBox.critical(self.ui, "Error", str(e))

    # --- SHARED PREVIEW LOGIC ---
    def load_preview_grid(self, fp, list_widget):
        list_widget.clear()
        doc = fitz.open(fp)
        for i in range(len(doc)):
            pix = doc.load_page(i).get_pixmap(matrix=fitz.Matrix(0.15, 0.15))
            img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGBA8888 if pix.alpha else QImage.Format_RGB888)
            item = QListWidgetItem(f"Page {i + 1}")
            item.setIcon(QIcon(QPixmap.fromImage(img)))
            item.setData(Qt.UserRole, i)
            list_widget.addItem(item)
        doc.close()
        self.update_watermarks()

    # --- WORD TO PDF LOGIC ---
    def execute_word_selection(self):
        fp, _ = QFileDialog.getOpenFileName(self.ui, "Select Word Document", self.get_last_dir(), "Word Documents (*.doc *.docx)")
        if fp: self.load_target_word_file(fp)

    def load_target_word_file(self, fp):
        self.ui.txtWordPath.setText(fp)
        
        # --- FIX: Visible Temp File ---
        # We use a clean name without a dot so that when the pdf_engine 
        # splits the file, the resulting pages don't inherit a hidden macOS state.
        import tempfile
        base_name = os.path.splitext(os.path.basename(fp))[0]
        self.temp_word_pdf = os.path.join(tempfile.gettempdir(), f"{base_name}.pdf")
        
        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            convert(fp, self.temp_word_pdf)
            QApplication.restoreOverrideCursor()
            
            # Load the newly created temp PDF into the word preview grid
            self.load_preview_grid(self.temp_word_pdf, self.ui.listWordPages)
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self.ui, "Conversion Error", f"Failed to convert Word document.\nEnsure Microsoft Word is installed to process the file.\n\nError: {str(e)}")

    def clear_word_file(self):
        self.ui.txtWordPath.clear()
        self.ui.listWordPages.clear()
        self.update_watermarks()
        
        # Clean up temp file
        if self.temp_word_pdf and os.path.exists(self.temp_word_pdf):
            try:
                os.remove(self.temp_word_pdf)
                self.temp_word_pdf = None
            except:
                pass

    def select_all_word_pages(self): [self.ui.listWordPages.item(i).setSelected(True) for i in range(self.ui.listWordPages.count())]
    def clear_word_selection(self): [self.ui.listWordPages.item(i).setSelected(False) for i in range(self.ui.listWordPages.count())]
    def invert_word_selection(self): [self.ui.listWordPages.item(i).setSelected(not self.ui.listWordPages.item(i).isSelected()) for i in range(self.ui.listWordPages.count())]

    def execute_word_conversion(self):
        if not self.temp_word_pdf or not os.path.exists(self.temp_word_pdf): return
        pages = sorted([i.data(Qt.UserRole) for i in self.ui.listWordPages.selectedItems()])
        if not pages: return
        try:
            if self.ui.radioWordSingle.isChecked():
                s, _ = QFileDialog.getSaveFileName(self.ui, "Save PDF", "", "PDF (*.pdf)")
                if s: 
                    pdf_engine.extract_to_single_pdf(self.temp_word_pdf, pages, s)
                    msg = QMessageBox(self.ui)
                    msg.setWindowTitle("Success")
                    msg.setText("Word Document converted and saved!")
                    open_btn = msg.addButton("Open File", QMessageBox.ActionRole)
                    msg.addButton("OK", QMessageBox.AcceptRole)
                    msg.exec()
                    if msg.clickedButton() == open_btn: QDesktopServices.openUrl(QUrl.fromLocalFile(s))
            elif self.ui.radioWordSeparate.isChecked():
                sd = QFileDialog.getExistingDirectory(self.ui, "Select Folder")
                if sd: 
                    pdf_engine.extract_to_separate_pdfs(self.temp_word_pdf, pages, sd)
                    QMessageBox.information(self.ui, "Success", "Pages extracted as separate PDFs!")
        except Exception as e: QMessageBox.critical(self.ui, "Error", str(e))