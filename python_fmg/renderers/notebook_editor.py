import os
import sys
import sqlite3
from PyQt6.QtWidgets import QTextEdit
from PyQt6.QtCore import pyqtSignal

class MarkdownNotebookEditor(QTextEdit):
    link_clicked = pyqtSignal(str)
    tag_detected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Write notes using [[WikiLinks]] or #tags. Press Save Note to persist.")
        self.db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "lore_forge_world.db"))
        self.textChanged.connect(self.parse_realtime_syntax)

    def parse_realtime_syntax(self):
        """
        Scans note text in real-time to index tags and find link references.
        """
        text = self.toPlainText()
        import re
        
        # 1. Match Obsidian tags (e.g. #faction, #npc, #place)
        tags = re.findall(r"#(\w+)", text)
        for tag in tags:
            self.tag_detected.emit(tag)
            
        # 2. Match WikiLinks (e.g. [[Ostraka City]])
        links = re.findall(r"\[\[(.*?)\]\]", text)
        for link in links:
            self.link_clicked.emit(link)
