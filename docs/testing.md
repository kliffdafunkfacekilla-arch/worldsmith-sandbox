# Testing the UI and Core Logic

Because Worldsmith Sandbox relies on a heavy PyQt6 interface running complex procedural map generation alongside asynchronous AI workers, rigorous automated testing is required to prevent regressions.

The `tests/` directory contains two custom testing harnesses designed to validate the application autonomously.

## 1. The Autonomous Fuzzer (`tests/auto_tester.py`)
The fuzzer is designed to detect surface-level exceptions, missing imports, and broken signal wirings in the Qt interface. 
It operates by programmatically identifying every `QPushButton`, `QToolButton`, `QAction`, and `QComboBox` in the MainWindow and ruthlessly executing `.click()` or changing selection values. 
To prevent the event loop from hanging on blocking modals, it dynamically mocks `QDialog.exec`, `QMessageBox`, and `QFileDialog` methods at runtime.

**To run the fuzzer:**
```bash
python -m tests.auto_tester
```
*Note: The script will abort with an exit code of `1` if it detects any unhandled Exceptions in the tracebacks, otherwise it prints a clean bill of health.*

## 2. End-to-End (E2E) Simulation Tester (`tests/e2e_tester.py`)
While the fuzzer catches typos, the E2E Tester is built on `PyQt6.QtTest` to simulate realistic, sequential human workflows that test the deep procedural and database logic of the application.

It executes the following workflows:
1. **The Map Painter Scenario**: Simulates a user selecting a magic brush and injecting fake `QMouseEvent`s across the map canvas to verify the terrain actually updates.
2. **The Dialog & Database Scenario**: Simulates a user writing a note and saving it, verifying the entry correctly persists into the SQLite database and triggers UI refreshes.
3. **The AI Workflow Scenario**: Hooks into the asynchronous Qt Signals emitted by the AI Worker threads to verify that AI context successfully parses and populates the text history areas.

**To run the E2E tests:**
```bash
python -m tests.e2e_tester
```
