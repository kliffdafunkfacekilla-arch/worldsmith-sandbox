import sys
import traceback
import time
from PyQt6.QtWidgets import QApplication, QPushButton, QComboBox, QCheckBox, QToolButton, QMessageBox
from PyQt6.QtGui import QAction
from python_fmg.main import LordsmithStudioMainWindow

class Fuzzer:
    def __init__(self):
        self.app = QApplication(sys.argv)
        # Mock QMessageBox so it doesn't block
        QMessageBox.information = lambda *args, **kwargs: None
        QMessageBox.critical = lambda *args, **kwargs: None
        QMessageBox.warning = lambda *args, **kwargs: None
        QMessageBox.question = lambda *args, **kwargs: QMessageBox.StandardButton.Yes
        
        from PyQt6.QtWidgets import QDialog, QFileDialog, QInputDialog, QMenu
        QDialog.exec = lambda *args, **kwargs: None
        QFileDialog.getOpenFileName = classmethod(lambda *args, **kwargs: ("", ""))
        QFileDialog.getSaveFileName = classmethod(lambda *args, **kwargs: ("", ""))
        QFileDialog.getExistingDirectory = classmethod(lambda *args, **kwargs: "")
        QInputDialog.getText = classmethod(lambda *args, **kwargs: ("Fuzzed Text", True))
        QInputDialog.getInt = classmethod(lambda *args, **kwargs: (1, True))
        QInputDialog.getItem = classmethod(lambda *args, **kwargs: ("Item", True))
        QMenu.exec = lambda *args, **kwargs: None
        
        self.window = LordsmithStudioMainWindow()
        
        self.errors = []
        sys.excepthook = self.handle_exception

    def handle_exception(self, exc_type, exc_value, exc_traceback):
        tb = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        self.errors.append(tb)
        print(f"\n[FUZZER CAUGHT EXCEPTION]\n{tb}\n")

    def run(self):
        print("Starting UI Fuzzer...")
        # Give UI a moment to init
        self.app.processEvents()
        self.window.show()

        # 1. Test QPushButtons
        buttons = self.window.findChildren(QPushButton)
        print(f"Found {len(buttons)} QPushButtons.")
        for btn in buttons:
            if btn.isEnabled() and btn.isVisible():
                print(f"Clicking button: {btn.text() or btn.objectName()}")
                try:
                    btn.click()
                    self.app.processEvents()
                except Exception as e:
                    print(f"Exception clicking {btn.text()}: {e}")

        # 2. Test QToolButtons
        tool_buttons = self.window.findChildren(QToolButton)
        print(f"Found {len(tool_buttons)} QToolButtons.")
        for btn in tool_buttons:
            if btn.isEnabled() and btn.isVisible():
                if btn.menu() is not None:
                    print(f"Skipping tool button with menu: {btn.text() or btn.objectName()}")
                    continue
                print(f"Clicking tool button: {btn.text() or btn.objectName()}")
                try:
                    btn.click()
                    self.app.processEvents()
                except Exception as e:
                    print(f"Exception clicking {btn.text()}: {e}")

        # 3. Test QActions (from menus/toolbars)
        actions = self.window.findChildren(QAction)
        print(f"Found {len(actions)} QActions.")
        for action in actions:
            if action.isEnabled():
                print(f"Triggering action: {action.text()}")
                try:
                    action.trigger()
                    self.app.processEvents()
                except Exception as e:
                    print(f"Exception triggering {action.text()}: {e}")

        # 4. Test QComboBoxes
        combos = self.window.findChildren(QComboBox)
        print(f"Found {len(combos)} QComboBoxes.")
        for combo in combos:
            if combo.isEnabled() and combo.count() > 0:
                print(f"Changing combo box: {combo.objectName()}")
                try:
                    # Select next item if possible, or first item
                    next_idx = (combo.currentIndex() + 1) % combo.count()
                    combo.setCurrentIndex(next_idx)
                    self.app.processEvents()
                except Exception as e:
                    print(f"Exception changing {combo.objectName()}: {e}")

        print("\n--- FUZZER SUMMARY ---")
        if self.errors:
            print(f"Found {len(self.errors)} unique crashes.")
            sys.exit(1)
        else:
            print("No crashes detected! Perfect run.")
            sys.exit(0)

if __name__ == '__main__':
    fuzzer = Fuzzer()
    fuzzer.run()
