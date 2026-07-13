import os

filepath = r'c:\Users\krazy\Desktop\worldsmith-sandbox\python_fmg\main.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_block = """        # Left panel: Note editor
        self.panel_left = QWidget()
        pl_lay = QVBoxLayout(self.panel_left)
        pl_lay.addWidget(QLabel("<b>✍️ Narrative Lore Writer</b>"))
        self.note_writer = MarkdownNotebookEditor(self.panel_left)
        pl_lay.addWidget(self.note_writer, 1)
        self.note_writer.spatial_bind_clicked.connect(self.handle_spatial_bind_clicked)
        self.note_writer.wiki_link_clicked.connect(self.handle_wiki_link_clicked)
        self.panels_splitter.addWidget(self.panel_left)"""

new_block = """        # Left panel: Tabbed Interface for Editor, Vault, and AI
        self.panel_left = QWidget()
        pl_lay = QVBoxLayout(self.panel_left)
        
        self.left_tabs = QTabWidget()
        self.left_tabs.setStyleSheet("QTabBar::tab { background: #111116; color: #EEEEF8; padding: 8px; border: 1px solid #333; } QTabBar::tab:selected { background: #29293a; font-weight: bold; }")
        
        # TAB 1: Editor
        self.tab_editor = QWidget()
        tab_ed_lay = QVBoxLayout(self.tab_editor)
        tab_ed_lay.addWidget(QLabel("<b>✍️ Narrative Lore Writer</b>"))
        self.note_writer = MarkdownNotebookEditor(self.tab_editor)
        tab_ed_lay.addWidget(self.note_writer, 1)
        self.note_writer.spatial_bind_clicked.connect(self.handle_spatial_bind_clicked)
        self.note_writer.wiki_link_clicked.connect(self.handle_wiki_link_clicked)
        self.left_tabs.addTab(self.tab_editor, "📝 Lore Editor")
        
        # TAB 2: Vault
        self.tab_vault = QWidget()
        tab_vault_lay = QVBoxLayout(self.tab_vault)
        tab_vault_lay.addWidget(QLabel("<b>📂 Extracted Lore Vault</b>"))
        self.vault_tree = QTreeView()
        self.vault_model = QFileSystemModel()
        vault_path = os.path.join(self.project_dir, 'lore_vault')
        os.makedirs(vault_path, exist_ok=True)
        self.vault_model.setRootPath(vault_path)
        self.vault_tree.setModel(self.vault_model)
        self.vault_tree.setRootIndex(self.vault_model.index(vault_path))
        self.vault_tree.setColumnWidth(0, 250)
        self.vault_tree.hideColumn(1)
        self.vault_tree.hideColumn(2)
        self.vault_tree.hideColumn(3)
        self.vault_tree.clicked.connect(self.handle_vault_item_clicked)
        tab_vault_lay.addWidget(self.vault_tree, 1)
        self.left_tabs.addTab(self.tab_vault, "📂 Notes Vault")
        
        # TAB 3: AI Chat
        self.tab_chat = QWidget()
        tab_chat_lay = QVBoxLayout(self.tab_chat)
        tab_chat_lay.addWidget(QLabel("<b>🤖 Lordsmith AI Assistant</b>"))
        
        self.ai_prompt_history = QTextEdit()
        self.ai_prompt_history.setReadOnly(True)
        self.ai_prompt_history.setStyleSheet("background-color: #0c0c10; border: none; font-size: 14px;")
        tab_chat_lay.addWidget(self.ai_prompt_history, 1)
        
        chat_input_lay = QHBoxLayout()
        self.ai_input = QLineEdit()
        self.ai_input.setPlaceholderText("Ask the AI about your lore, request ideas, or expand notes...")
        self.ai_input.returnPressed.connect(self.handle_ai_submit)
        chat_input_lay.addWidget(self.ai_input, 1)
        
        btn_ai_send = QPushButton("Send")
        btn_ai_send.clicked.connect(self.handle_ai_submit)
        chat_input_lay.addWidget(btn_ai_send)
        tab_chat_lay.addLayout(chat_input_lay)
        self.left_tabs.addTab(self.tab_chat, "🤖 AI Chat")
        
        pl_lay.addWidget(self.left_tabs, 1)
        self.panels_splitter.addWidget(self.panel_left)"""

if old_block in content:
    content = content.replace(old_block, new_block)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Left Panel Updated')
else:
    print('Could not find Left Panel block')
