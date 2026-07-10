import sys
import traceback
import time
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt, QPoint, QPointF
from PyQt6.QtGui import QMouseEvent
from python_fmg.main import WorldsmithMainWindow

class E2ETester:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.window = WorldsmithMainWindow()
        self.errors = []
        sys.excepthook = self.handle_exception

    def handle_exception(self, exc_type, exc_value, exc_traceback):
        tb = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        self.errors.append(tb)
        print(f"\n[E2E CAUGHT EXCEPTION]\n{tb}\n")

    def run_tests(self):
        print("Starting Human-like E2E Tester...")
        self.window.show()
        self.app.processEvents()

        try:
            self.scenario_1_map_painting()
            self.scenario_2_notes_database()
            self.scenario_3_ai_workflow()
        except Exception as e:
            print(f"Test scenario failed: {e}")
            traceback.print_exc()
            self.errors.append(str(e))

        print("\n--- E2E SUMMARY ---")
        if self.errors:
            print(f"Found {len(self.errors)} unique crashes during E2E.")
            sys.exit(1)
        else:
            print("All E2E scenarios passed perfectly! No crashes detected.")
            sys.exit(0)

    def scenario_1_map_painting(self):
        print("\n[Scenario 1] Map Painting...")
        # Give it a moment
        QTest.qWait(500)
        
        # 1. Select the Burg Paint tool (simulating pressing 'B')
        self.window.cb_brush_mode.setCurrentText("Burg Paint")
        self.app.processEvents()
        
        # 2. Simulate dragging the mouse across the map to place burgs
        print("Simulating mouse drag to paint burgs...")
        
        # Create a fake mouse press at center
        center_x = self.window.map_viewer.width() // 2
        center_y = self.window.map_viewer.height() // 2
        
        press_event = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPointF(center_x, center_y),
            QPointF(center_x, center_y),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier
        )
        self.window.map_viewer.mousePressEvent(press_event)
        
        # Move the mouse
        move_event = QMouseEvent(
            QMouseEvent.Type.MouseMove,
            QPointF(center_x + 50, center_y + 50),
            QPointF(center_x + 50, center_y + 50),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier
        )
        self.window.map_viewer.mouseMoveEvent(move_event)
        
        # Release the mouse
        release_event = QMouseEvent(
            QMouseEvent.Type.MouseButtonRelease,
            QPointF(center_x + 50, center_y + 50),
            QPointF(center_x + 50, center_y + 50),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier
        )
        self.window.map_viewer.mouseReleaseEvent(release_event)
        
        self.app.processEvents()
        print(f"Finished painting. Burgs count: {len(self.window.map_engine.burgs)}")

    def scenario_2_notes_database(self):
        print("\n[Scenario 2] Notes Database...")
        # Simulate typing a title and body
        self.window.note_title_input.setText("E2E Test Note")
        self.window.note_editor.setText("This is an end-to-end test note to verify the database.")
        self.app.processEvents()
        
        # Click the save button
        print("Clicking save note...")
        self.window.btn_save_note.click()
        self.app.processEvents()
        
        # Verify it was added to the combo box
        found = False
        for i in range(self.window.cb_notes.count()):
            if self.window.cb_notes.itemText(i) == "E2E Test Note":
                found = True
                break
        if not found:
            raise Exception("Note was not added to the combo box!")
        print("Note successfully saved and verified.")

    def scenario_3_ai_workflow(self):
        print("\n[Scenario 3] AI Workflow...")
        # Write a prompt
        self.window.ai_input.setText("What is the capital of this kingdom?")
        self.app.processEvents()
        
        # To avoid blocking/waiting 30 seconds for Ollama, we intercept the AI worker
        # But we first click send to start it
        self.window.btn_send_prompt.click()
        self.app.processEvents()
        
        # The worker might be running. Let's mock its prompt_ready signal emission.
        # Actually, let's just directly call the handler to simulate the worker finishing.
        print("Simulating AI response received...")
        self.window.handle_active_prompt_ready("The capital is E2E-City.")
        self.app.processEvents()
        
        # Check if history updated
        history = self.window.ai_prompt_history.toPlainText()
        if "The capital is E2E-City." not in history:
            raise Exception("AI response was not appended to history!")
        print("AI workflow verified.")

if __name__ == '__main__':
    tester = E2ETester()
    tester.run_tests()
