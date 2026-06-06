import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QSplitter, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeySequence

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Antigravity PDF Editor")
        self.resize(1200, 800)
        
        # Central widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create UI components
        self._setup_menubar()
        self._setup_toolbar()
        self._setup_workspace()
        
        # Enable drag and drop
        self.setAcceptDrops(True)
        
    def _setup_menubar(self):
        menubar = self.menuBar()
        
        # File Menu
        file_menu = menubar.addMenu("&File")
        
        open_action = QAction("&Open PDF...", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)
        
        save_action = QAction("&Save As...", self)
        save_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit Menu (Placeholder for Undo/Redo/etc)
        edit_menu = menubar.addMenu("&Edit")
        undo_action = QAction("Undo", self)
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        edit_menu.addAction(undo_action)
        
    def _setup_toolbar(self):
        self.toolbar = self.addToolBar("Main Toolbar")
        self.toolbar.setMovable(False)
        # We will add tools here like: Zoom, Select, Edit Text, Annotate, etc.
        
    def _setup_workspace(self):
        # Splitter to separate thumbnails (left) and document view (right)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_layout.addWidget(self.splitter)
        
        # Placeholder for thumbnails
        self.thumbnails_panel = QWidget()
        self.thumbnails_panel.setMinimumWidth(200)
        self.thumbnails_panel.setStyleSheet("background-color: #2d2d30;")
        self.splitter.addWidget(self.thumbnails_panel)
        
        # Placeholder for document view
        self.document_view = QWidget()
        self.document_view.setStyleSheet("background-color: #1e1e1e;")
        self.splitter.addWidget(self.document_view)
        
        # Set initial sizes
        self.splitter.setSizes([200, 1000])

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls and urls[0].toLocalFile().lower().endswith('.pdf'):
                event.accept()
                return
        event.ignore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            self.load_pdf(file_path)
            
    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open PDF", "", "PDF Files (*.pdf)"
        )
        if file_path:
            self.load_pdf(file_path)
            
    def save_file(self):
        pass # To be implemented
            
    def load_pdf(self, file_path):
        # TODO: Connect to PyMuPDF core to load document
        QMessageBox.information(self, "Load PDF", f"Loading: {file_path}")
