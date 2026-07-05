import math
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QFont

class CelestialPreviewWidget(QWidget):
    """
    Renders moon phases dynamically based on the current orbital period day index.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setMinimumHeight(100)
        self.current_day = 1
        
        # Configure custom orbital moons (Name, Period in days, color)
        self.moons = [
            {"name": "Inner Moon (Sari)", "period": 14.0, "color": "#04D361"},
            {"name": "Outer Moon (Ostra)", "period": 28.0, "color": "#a855f7"}
        ]

    def set_day(self, day):
        self.current_day = day
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Background
        painter.fillRect(self.rect(), QBrush(QColor("#18181b")))
        
        spacing = self.width() / (len(self.moons) + 1)
        r = 20
        cy = self.height() // 2 - 10
        
        for idx, moon in enumerate(self.moons):
            name = moon["name"]
            period = moon["period"]
            color = QColor(moon["color"])
            
            # Calculate orbital cycle phase percentage
            phase_pct = (self.current_day % period) / period
            cx = int(spacing * (idx + 1))
            
            # Dark moon shadow backing
            painter.setBrush(QBrush(QColor("#27272a")))
            painter.setPen(QPen(QColor("#3f3f46"), 1))
            painter.drawEllipse(cx - r, cy - r, r * 2, r * 2)
            
            # Draw moon light shape based on phase
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)
            
            if 0.45 <= phase_pct <= 0.55:
                # Full Moon
                painter.drawEllipse(cx - r, cy - r, r * 2, r * 2)
            elif phase_pct < 0.05 or phase_pct > 0.95:
                # New Moon outline
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.setPen(QPen(color, 1, Qt.PenStyle.DashLine))
                painter.drawEllipse(cx - r, cy - r, r * 2, r * 2)
            else:
                # Crescent representation
                if phase_pct < 0.5:
                    painter.drawChord(cx - r, cy - r, r * 2, r * 2, -90 * 16, 180 * 16)
                else:
                    painter.drawChord(cx - r, cy - r, r * 2, r * 2, 90 * 16, 180 * 16)
            
            # Label
            painter.setPen(QColor("#e4e4e7"))
            painter.setFont(QFont("Segoe UI", 8))
            painter.drawText(cx - 60, cy + r + 15, 120, 20, Qt.AlignmentFlag.AlignCenter, name)
