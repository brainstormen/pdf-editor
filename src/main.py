import sys
from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow

def main():
    # Enable high DPI scaling
    app = QApplication(sys.argv)
    
    # Initialize the main window
    window = MainWindow()
    window.show()
    
    # Run the application event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
