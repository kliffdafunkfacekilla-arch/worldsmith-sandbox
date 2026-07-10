import sqlite3
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QComboBox, QRadioButton, QButtonGroup)
from PyQt6.QtCore import Qt

class MapBindingDialog(QDialog):
    def __init__(self, db_path, map_engine, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Bind Note to Map")
        self.resize(400, 250)
        self.setStyleSheet("background: #1e1e28; color: #EEEEF8;")
        
        self.db_path = db_path
        self.map_engine = map_engine
        
        # Result data
        self.bind_mode = None    # 'entity' or 'marker'
        self.bind_type = None    # 'state', 'burg', 'religion', 'culture'
        self.bind_target = None  # id or name
        
        layout = QVBoxLayout(self)
        
        # Options
        self.radio_entity = QRadioButton("Link to existing Map Layer Entity")
        self.radio_marker = QRadioButton("Place Custom Marker Pin on Map")
        self.radio_entity.setChecked(True)
        
        self.btn_group = QButtonGroup(self)
        self.btn_group.addButton(self.radio_entity)
        self.btn_group.addButton(self.radio_marker)
        
        layout.addWidget(self.radio_entity)
        
        # Entity selection group
        self.cb_layer = QComboBox()
        self.cb_layer.addItems(["States", "Burgs", "Religions", "Cultures"])
        self.cb_layer.currentIndexChanged.connect(self.populate_entities)
        
        self.cb_entity = QComboBox()
        
        entity_layout = QHBoxLayout()
        entity_layout.setContentsMargins(20, 0, 0, 10)
        entity_layout.addWidget(QLabel("Layer:"))
        entity_layout.addWidget(self.cb_layer)
        entity_layout.addWidget(QLabel("Entity:"))
        entity_layout.addWidget(self.cb_entity, 1)
        
        layout.addLayout(entity_layout)
        
        layout.addWidget(self.radio_marker)
        
        self.radio_entity.toggled.connect(lambda: self.cb_layer.setEnabled(self.radio_entity.isChecked()))
        self.radio_entity.toggled.connect(lambda: self.cb_entity.setEnabled(self.radio_entity.isChecked()))
        
        layout.addStretch()
        
        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        self.btn_accept = QPushButton("Confirm")
        self.btn_accept.setStyleSheet("background: #04D361; color: black; font-weight: bold;")
        self.btn_accept.clicked.connect(self.accept_binding)
        
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(self.btn_accept)
        layout.addLayout(btn_layout)
        
        self.populate_entities()
        
    def populate_entities(self):
        self.cb_entity.clear()
        layer = self.cb_layer.currentText()
        
        if not self.map_engine:
            return
            
        try:
            if layer == "States":
                for state in getattr(self.map_engine, "states", []):
                    if state.get("name") and state.get("name") != "Unknown":
                        self.cb_entity.addItem(state["name"], userData=state.get("i"))
            elif layer == "Burgs":
                for burg in getattr(self.map_engine, "burgs", []):
                    if burg.get("name") and burg.get("name") != "Unknown":
                        self.cb_entity.addItem(burg["name"], userData=burg.get("i"))
            elif layer == "Religions":
                for rel in getattr(self.map_engine, "religions", []):
                    if rel.get("name") and rel.get("name") != "Unknown":
                        self.cb_entity.addItem(rel["name"], userData=rel.get("i"))
            elif layer == "Cultures":
                for cult in getattr(self.map_engine, "cultures", []):
                    if cult.get("name") and cult.get("name") != "Unknown":
                        self.cb_entity.addItem(cult["name"], userData=cult.get("i"))
        except Exception as e:
            print(f"Error populating map entities: {e}")
            
    def accept_binding(self):
        if self.radio_entity.isChecked():
            self.bind_mode = 'entity'
            layer = self.cb_layer.currentText()
            if layer == "States":
                self.bind_type = "state"
            elif layer == "Burgs":
                self.bind_type = "burg"
            elif layer == "Religions":
                self.bind_type = "religion"
            elif layer == "Cultures":
                self.bind_type = "culture"
                
            self.bind_target = self.cb_entity.currentData()
            if self.bind_target is None:
                return # Can't bind if none selected
        else:
            self.bind_mode = 'marker'
            self.bind_type = 'marker'
            
        self.accept()
