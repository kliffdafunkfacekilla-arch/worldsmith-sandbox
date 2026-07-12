import re
from PyQt6.QtWidgets import QTextEdit
from PyQt6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont
from PyQt6.QtCore import pyqtSignal, Qt

class LordsmithSyntaxHighlighter(QSyntaxHighlighter):
    """
    Real-time regular expression scanner that color-codes world entities,
    wiki-links, and coordinate bindings inside the notebook prose.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlighting_rules = []

        # 1. Wiki-Links Rules: [[Note Title]]
        wiki_link_format = QTextCharFormat()
        wiki_link_format.setForeground(QColor("#04D361"))
        wiki_link_format.setFontWeight(QFont.Weight.Bold)
        self.highlighting_rules.append((re.compile(r"\[\[.*?\]\]"), wiki_link_format))

        # 2. Coordinate Spatial Bindings Rules: (cell_idx: 250) or Cell #250
        coord_format = QTextCharFormat()
        coord_format.setForeground(QColor("#38bdf8"))
        coord_format.setFontUnderline(True)
        self.highlighting_rules.append((re.compile(r"\(cell_idx:\s*\d+\)"), coord_format))
        self.highlighting_rules.append((re.compile(r"Cell\s*#\d+"), coord_format))

        # 3. Headers Highlighting Rules: # Title, ## Subtitle
        header_format = QTextCharFormat()
        header_format.setForeground(QColor("#a855f7"))
        header_format.setFontWeight(QFont.Weight.Bold)
        self.highlighting_rules.append((re.compile(r"^#{1,6}\s+.*$"), header_format))

        # 4. Bold Prose Rules: **Text**
        bold_format = QTextCharFormat()
        bold_format.setFontWeight(QFont.Weight.Bold)
        bold_format.setForeground(QColor("#EEEEF8"))
        self.highlighting_rules.append((re.compile(r"\*\*.*?\*\*"), bold_format))

    def highlightBlock(self, text):
        for pattern, format in self.highlighting_rules:
            for match in pattern.finditer(text):
                start, end = match.span()
                self.setFormat(start, end - start, format)


class MarkdownNotebookEditor(QTextEdit):
    """
    Symmetrical Notebook Editor Component. Features custom font formatting,
    inline element tokenizing, and text click parsing to dynamically emit 
    re-routing signals straight back into the workspace state-machine.
    """
    # Signals to pass structural click updates to the central window engine
    wiki_link_clicked = pyqtSignal(str)     # Emits extracted Note Title
    spatial_bind_clicked = pyqtSignal(int)  # Emits extracted Cell Index

    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlighter = LordsmithSyntaxHighlighter(self.document())
        self._apply_editor_styling()

    def _apply_editor_styling(self):
        self.setStyleSheet("""
            QTextEdit {
                background-color: #121216;
                border: 1px solid #29292E;
                color: #e1e1e6;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 14px;
                line-height: 1.5;
                padding: 8px;
            }
        """)
        self.setPlaceholderText("Begin writing your chronicle lore prose here...\\nUse [[Wiki-Links]] to tag connected entries or link cells using 'Cell #250'.")

    def mousePressEvent(self, event):
        """
        Intercepts raw cursor hits to extract clicked tokens and evaluate if the
        user targeted an interactive wiki-link or structural coordinate node.
        """
        # Allow default behavior to position text cursor cleanly first
        super().mousePressEvent(event)
        
        cursor = self.cursorForPosition(event.position().toPoint())
        block_text = cursor.block().text()
        pos_in_block = cursor.positionInBlock()

        if not block_text:
            return

        # Case A: Evaluate if a classic Wiki-Link [[Title]] was clicked
        wiki_pattern = re.compile(r"\[\[(.*?)\]\]")
        for match in wiki_pattern.finditer(block_text):
            start, end = match.span()
            if start <= pos_in_block <= end:
                extracted_title = match.group(1).strip()
                if extracted_title:
                    self.wiki_link_clicked.emit(extracted_title)
                return

        # Case B: Evaluate if a Coordinate Node (Cell #250) was clicked
        coord_pattern = re.compile(r"Cell\s*#(\d+)")
        for match in coord_pattern.finditer(block_text):
            start, end = match.span()
            if start <= pos_in_block <= end:
                cell_idx = int(match.group(1))
                self.spatial_bind_clicked.emit(cell_idx)
                return

        # Case C: Alternate markup form: (cell_idx: 250)
        idx_pattern = re.compile(r"\(cell_idx:\s*(\d+)\)")
        for match in idx_pattern.finditer(block_text):
            start, end = match.span()
            if start <= pos_in_block <= end:
                cell_idx = int(match.group(1))
                self.spatial_bind_clicked.emit(cell_idx)
                return
