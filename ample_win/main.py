import sys
import os
import time
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QListWidget, QListWidgetItem, QLabel, 
                             QLineEdit, QPushButton, QFrame, QSplitter, QScrollArea,
                             QComboBox, QCheckBox, QGroupBox, QFileDialog, QDialog,
                             QProgressBar, QMessageBox, QTabWidget, QTreeWidget, 
                             QTreeWidgetItem, QTextEdit, QGridLayout, QButtonGroup,
                             QSizePolicy, QMenu)
from PySide6.QtCore import Qt, QSize, Signal, Slot, QSettings, QPoint, QRect
from PySide6.QtGui import QFont, QIcon, QPalette, QColor, QCloseEvent, QPainter, QPainterPath

from data_manager import DataManager
from mame_launcher import MameLauncher
from rom_manager import RomManager, DownloadWorker
from mame_downloader import MameDownloadWorker

class RomItemWidget(QWidget):
    def __init__(self, description, value, exists, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(2)
        
        self.title_label = QLabel(description)
        self.title_label.setStyleSheet(f"font-weight: bold; font-size: 13px; color: {'#ffffff' if exists else '#ff4d4d'};")
        
        self.status_label = QLabel("ROM found" if exists else "ROM missing")
        self.status_label.setStyleSheet(f"font-size: 11px; color: #888888;")
        
        layout.addWidget(self.title_label)
        layout.addWidget(self.status_label)

class RomManagerDialog(QDialog):
    def __init__(self, rom_manager, parent=None):
        super().__init__(parent)
        self.rom_manager = rom_manager
        self.setWindowTitle("ROMs")
        self.setMinimumSize(650, 550)
        self.filter_mode = "all" # "all" or "missing"
        self.init_ui()
        self.refresh_list()

    def init_ui(self):
        self.setObjectName("RomDialog")
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Header with Segmented Control
        header = QWidget()
        header.setFixedHeight(50)
        header_layout = QHBoxLayout(header)
        
        self.seg_all = QPushButton("All")
        self.seg_all.setCheckable(True)
        self.seg_all.setChecked(True)
        self.seg_missing = QPushButton("Missing")
        self.seg_missing.setCheckable(True)
        
        self.seg_group = QButtonGroup(self)
        self.seg_group.addButton(self.seg_all)
        self.seg_group.addButton(self.seg_missing)
        self.seg_group.buttonClicked.connect(self.on_filter_changed)
        
        header_layout.addStretch()
        header_layout.addWidget(self.seg_all)
        header_layout.addWidget(self.seg_missing)
        header_layout.addStretch()
        main_layout.addWidget(header)

        # 2. ROM List
        self.rom_list = QListWidget()
        self.rom_list.setObjectName("RomList")
        main_layout.addWidget(self.rom_list)

        # 3. Progress Area (Hidden by default)
        self.progress_area = QWidget()
        self.progress_area.setVisible(False)
        p_layout = QVBoxLayout(self.progress_area)
        self.progress_bar = QProgressBar()
        self.status_label = QLabel("")
        p_layout.addWidget(self.status_label)
        p_layout.addWidget(self.progress_bar)
        main_layout.addWidget(self.progress_area)

        # 4. Settings Footer
        footer = QWidget()
        footer.setObjectName("RomFooter")
        footer_layout = QVBoxLayout(footer)
        footer_layout.setContentsMargins(15, 15, 15, 15)
        
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("URL"))
        self.url_edit = QLineEdit(self.rom_manager.base_url)
        url_layout.addWidget(self.url_edit)
        footer_layout.addLayout(url_layout)
        
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Type"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["zip", "7z"])
        type_layout.addWidget(self.type_combo)
        type_layout.addStretch()
        footer_layout.addLayout(type_layout)
        
        # 5. Buttons Footer
        btns_layout = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_list)
        
        self.open_roms_btn = QPushButton("📁 ROMs")
        self.open_roms_btn.clicked.connect(self.open_roms_folder)
        
        self.download_btn = QPushButton("Download Missing")
        self.download_btn.setObjectName("PrimaryButton")
        self.download_btn.clicked.connect(self.download_missing)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        btns_layout.addWidget(self.refresh_btn)
        btns_layout.addWidget(self.open_roms_btn)
        btns_layout.addStretch()
        btns_layout.addWidget(self.download_btn)
        btns_layout.addWidget(self.cancel_btn)
        footer_layout.addLayout(btns_layout)
        
        main_layout.addWidget(footer)
        
        self.apply_dialog_theme()

    def on_filter_changed(self, btn):
        self.filter_mode = "all" if btn == self.seg_all else "missing"
        self.refresh_list()

    def refresh_list(self):
        self.rom_list.clear()
        statuses = self.rom_manager.get_rom_status()
        
        for s in statuses:
            if self.filter_mode == "missing" and s['exists']:
                continue
                
            item = QListWidgetItem(self.rom_list)
            widget = RomItemWidget(s['description'], s['value'], s['exists'])
            item.setSizeHint(widget.sizeHint())
            self.rom_list.addItem(item)
            self.rom_list.setItemWidget(item, widget)

    def open_roms_folder(self):
        os.startfile(self.rom_manager.roms_dir)

    def download_missing(self):
        self.rom_manager.base_url = self.url_edit.text()
        statuses = self.rom_manager.get_rom_status()
        self.to_download = [s for s in statuses if not s['exists']]
        if not self.to_download:
            QMessageBox.information(self, "Done", "All ROMs are already present!")
            return
        
        self.progress_area.setVisible(True)
        self.download_total = len(self.to_download)
        self.download_finished_count = 0
        self.progress_bar.setMaximum(self.download_total)
        self.progress_bar.setValue(0)
        
        # Batch execute downloads concurrently (instead of one by one)
        # We'll limit to a reasonable number of concurrent connections if needed, 
        # but for small ROMs, launching all at once is very fast.
        for current in self.to_download:
            value = current['value']
            ext = self.type_combo.currentText()
            url = self.rom_manager.get_download_url(value, ext)
            dest = os.path.join(self.rom_manager.roms_dir, f"{value}.{ext}")
            
            worker = DownloadWorker(url, dest, value)
            if hasattr(self.parent(), 'active_workers'):
                self.parent().active_workers.append(worker)
                
            worker.finished.connect(lambda v, s, w=worker: self.on_concurrent_download_finished(w, v, s))
            worker.start()

    def on_concurrent_download_finished(self, worker, value, success):
        if hasattr(self.parent(), 'active_workers') and worker in self.parent().active_workers:
            self.parent().active_workers.remove(worker)
        
        self.download_finished_count += 1
        self.progress_bar.setValue(self.download_finished_count)
        self.status_label.setText(f"Finished {self.download_finished_count}/{self.download_total}: {value}")
        
        if self.download_finished_count == self.download_total:
            self.progress_area.setVisible(False)
            QMessageBox.information(self, "Finished", f"Successfully downloaded all {self.download_total} ROMs!")
            self.refresh_list()

    def apply_dialog_theme(self):
        self.setStyleSheet("""
            QDialog#RomDialog { background-color: #252525; }
            #RomList { 
                background-color: #1a1a1a; 
                border-top: 1px solid #3d3d3d;
                border-bottom: 1px solid #3d3d3d;
            }
            #RomFooter { background-color: #2d2d2d; }
            
            QPushButton {
                background-color: #3d3d3d;
                border: 1px solid #555;
                color: white;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #4d4d4d; }
            QPushButton:checked { background-color: #555; border: 1px solid #0078d4; }
            
            #PrimaryButton { background-color: #0078d4; border: none; font-weight: bold; }
            #PrimaryButton:hover { background-color: #1a8ad4; }
            
            QLineEdit, QComboBox {
                background-color: #1a1a1a;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 4px;
                color: white;
            }
            
            QLabel { color: #cccccc; font-size: 12px; }
            
            QProgressBar {
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                text-align: center;
                height: 15px;
            }
            QProgressBar::chunk { background-color: #0078d4; }
        """)

# --- Sub-Slot Popup (The popover from Mac version) ---
class SubSlotPopup(QDialog):
    def __init__(self, parent, data, current_slots, on_change_callback):
        super().__init__(parent)
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.data = data
        self.current_slots = current_slots
        self.on_change_callback = on_change_callback
        self.init_ui()

    def closeEvent(self, event):
        if hasattr(self.parent(), 'active_popup') and self.parent().active_popup == self:
            self.parent().last_popup_close_time = time.time()
            self.parent().last_popup_id = id(self.data)
            self.parent().active_popup = None
        super().closeEvent(event)

    def init_ui(self):
        # Overall container to allow for the pointer arrow on top
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 10, 0, 0) # Top margin for arrow
        
        self.container = QWidget()
        self.container.setObjectName("BubbleContainer")
        self.container.setStyleSheet("""
            QWidget#BubbleContainer {
                background-color: #262626;
                border: 1px solid #3d3d3d;
                border-radius: 12px;
            }
        """)
        
        self.content_layout = QVBoxLayout(self.container)
        self.content_layout.setContentsMargins(15, 20, 15, 15)
        self.content_layout.setSpacing(8)

        # Close button
        self.close_btn = QPushButton("×", self.container)
        self.close_btn.setFixedSize(20, 20)
        self.close_btn.setStyleSheet("color: #aaa; background: #444; border-radius: 10px; border:none; font-weight:bold;")
        self.close_btn.move(250, 8)
        self.close_btn.clicked.connect(self.close)

        if 'slots' in self.data:
            for slot in self.data['slots']:
                options = slot.get('options', [])
                if any('media' in opt for opt in options):
                    combo = QComboBox()
                    combo.setFixedWidth(180)
                    combo.setFixedHeight(22)
                    combo.setProperty("appleStyle", "slot")
                    
                    slot_name = slot['name']
                    combo.setObjectName(slot_name)
                    for opt in options:
                        combo.addItem(opt.get('description') or opt['value'] or "—None—", opt['value'])

                    combo.blockSignals(True)
                    val = self.current_slots.get(slot_name)
                    idx = combo.findData(str(val))
                    if idx < 0: idx = combo.findData(val)
                    if idx >= 0: combo.setCurrentIndex(idx)
                    combo.blockSignals(False)
                    
                    combo.currentIndexChanged.connect(self.on_changed)
                    
                    # Create container with combo and arrow overlay (matching main window)
                    combo_widget = QWidget()
                    combo_widget.setFixedSize(180, 22)
                    combo.setParent(combo_widget)
                    combo.move(0, 0)
                    
                    # Arrow label overlay - narrow blue like Mac
                    arrow_label = QLabel("↕", combo_widget)
                    arrow_label.setFixedSize(20, 20)
                    arrow_label.move(160, 1)  # 160 + 20 = 180
                    arrow_label.setAlignment(Qt.AlignCenter)
                    arrow_label.setStyleSheet("""
                        background-color: #3b7ee1;
                        color: white;
                        font-size: 12px;
                        font-weight: bold;
                        padding-bottom: 3px;
                        border: none;
                        border-top-right-radius: 3px;
                        border-bottom-right-radius: 3px;
                    """)
                    arrow_label.setAttribute(Qt.WA_TransparentForMouseEvents)
                    
                    self.content_layout.addWidget(combo_widget, 0, Qt.AlignCenter)

        self.main_layout.addWidget(self.container)
        self.apply_theme()
        self.setFixedWidth(280)

    def paintEvent(self, event):
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setBrush(QColor("#262626"))
            painter.setPen(Qt.NoPen)
            
            # Draw a triangle pointing up at the middle
            path = QPainterPath()
            mw = self.width() / 2
            path.moveTo(mw - 10, 11)
            path.lineTo(mw, 0)
            path.lineTo(mw + 10, 11)
            painter.drawPath(path)
        finally:
            painter.end()

    def apply_theme(self):
        # Match main window combo styling - gray with hidden native arrow
        self.setStyleSheet("""
            QWidget#BubbleContainer {
                background-color: #262626;
                border: 1px solid #3d3d3d;
                border-radius: 12px;
            }
            QComboBox {
                background-color: #3d3d3d;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 2px 20px 2px 8px;
                color: #eee;
                font-size: 11px;
                min-height: 18px;
            }
            QComboBox::drop-down {
                width: 0px;
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                width: 0px;
                height: 0px;
            }
            QComboBox:hover {
                border-color: #777;
            }
        """)

    def on_changed(self):
        combo = self.sender()
        self.current_slots[combo.objectName()] = combo.currentData()
        self.on_change_callback()

class AmpleMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ample - Windows Port")
        self.setMinimumSize(1000, 750)
        
        # Paths
        self.app_dir = os.path.dirname(os.path.abspath(__file__))
        self.resources_path = r'c:\dev\ample\Ample\Resources'
        self.roms_dir = os.path.join(os.environ.get('APPDATA', '.'), 'Ample', 'roms')
        
        self.data_manager = DataManager(self.resources_path)
        self.rom_manager = RomManager(self.resources_path, self.roms_dir)
        self.launcher = MameLauncher()
        self.active_popup = None  # Track current open sub-slot popup
        self.last_popup_close_time = 0
        self.last_popup_id = None
        
        # Global stylesheet for combos with appleStyle="slot"
        self.setStyleSheet("""
            QComboBox[appleStyle="slot"] {
                background-color: #3d3d3d;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 2px 20px 2px 8px;
                color: #eee;
                font-size: 11px;
                min-height: 18px;
            }
            QComboBox[appleStyle="slot"]::drop-down {
                width: 0px;
                border: none;
            }
            QComboBox[appleStyle="slot"]::down-arrow {
                image: none;
                width: 0px;
                height: 0px;
            }
        """)
        
        # Thread management
        self.active_workers = []
        
        # Settings Persistence
        self.settings = QSettings(os.path.join(self.roms_dir, "settings.ini"), QSettings.IniFormat)
        
        # Initial MAME Check
        self.check_for_mame()
        self.launcher.working_dir = self.roms_dir
        
        self.selected_machine = None
        self.current_slots = {}
        self.current_media = {}
        
        self.init_ui()
        self.apply_premium_theme()
        self.load_persistent_settings()
        
        # NEW: Check for missing ROMs and show dialog automatically if needed
        self.check_and_auto_roms()

    def check_and_auto_roms(self):
        statuses = self.rom_manager.get_rom_status()
        missing = [s for s in statuses if not s['exists']]
        if missing:
            # Short timer to show dialog after window is visible
            from PySide6.QtCore import QTimer
            QTimer.singleShot(500, self.show_rom_manager)

    def init_ui(self):
        container = QWidget()
        self.setCentralWidget(container)
        main_vbox = QVBoxLayout(container)
        main_vbox.setContentsMargins(0, 0, 0, 0)
        main_vbox.setSpacing(0)

        # 1. Toolbar (macOS Style)
        toolbar = QWidget()
        toolbar.setObjectName("Toolbar")
        toolbar.setFixedHeight(60)
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(15, 0, 15, 0)
        
        tools = [
            ("💾 Disk Images", None),
            ("🎮 ROMs", self.show_rom_manager),
            ("⚙️ Settings", self.show_settings),
            ("📖 Help", None)
        ]
        for name, slot in tools:
            btn = QPushButton(name)
            btn.setObjectName("ToolbarButton")
            if slot: btn.clicked.connect(slot)
            toolbar_layout.addWidget(btn)
        toolbar_layout.addStretch()
        main_vbox.addWidget(toolbar)

        # 2. Splitter for Tree and Main Area
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setHandleWidth(1)
        self.splitter.setObjectName("MainSplitter")
        
        # Left Panel: Machine Tree
        left_panel = QWidget()
        left_panel.setObjectName("LeftPanel")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Find Machine...")
        self.search_input.setObjectName("SearchInput")
        self.search_input.textChanged.connect(self.filter_machines)
        
        self.machine_tree = QTreeWidget()
        self.machine_tree.setHeaderHidden(True)
        self.machine_tree.setObjectName("MachineTree")
        self.machine_tree.itemClicked.connect(self.on_machine_selected)
        self.machine_tree.itemDoubleClicked.connect(self.on_tree_double_clicked)
        self.populate_machine_tree(self.data_manager.models, self.machine_tree.invisibleRootItem())
        
        left_layout.addWidget(self.search_input)
        left_layout.addWidget(self.machine_tree)
        self.splitter.addWidget(left_panel)
        
        # Right Panel: Compact Configuration Area
        right_panel = QWidget()
        right_panel.setObjectName("RightPanel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(15, 10, 15, 10)
        right_layout.setSpacing(5)
        
        # Tabs (Centered and Compact)
        tab_container = QHBoxLayout()
        self.tabs = QTabWidget()
        self.tabs.setObjectName("MainTabs")
        self.tabs.setFixedHeight(120) # Compact height for video/cpu settings
        self.init_tabs()
        tab_container.addStretch()
        tab_container.addWidget(self.tabs)
        tab_container.addStretch()
        right_layout.addLayout(tab_container)

        # Body: Grid for Slots and Media
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        self.options_container = QWidget()
        self.options_grid = QGridLayout(self.options_container)
        self.options_grid.setContentsMargins(10, 10, 20, 10)
        self.options_grid.setSpacing(20)
        self.options_grid.setColumnStretch(0, 1)
        self.options_grid.setColumnStretch(1, 1)
        
        # Fixed containers to avoid grid stacking issues
        self.slots_frame = QWidget()
        self.slots_layout = QVBoxLayout(self.slots_frame)
        self.slots_layout.setContentsMargins(0, 0, 0, 0)
        self.options_grid.addWidget(self.slots_frame, 0, 0)
        
        self.media_frame = QWidget()
        self.media_layout = QVBoxLayout(self.media_frame)
        self.media_layout.setContentsMargins(0, 0, 0, 0)
        self.options_grid.addWidget(self.media_frame, 0, 1)
        
        scroll.setWidget(self.options_container)
        right_layout.addWidget(scroll)
        
        # Launch Area
        launch_layout = QHBoxLayout()
        self.cmd_preview = QLineEdit()
        self.cmd_preview.setReadOnly(True)
        self.cmd_preview.setObjectName("CommandPreview")
        self.cmd_preview.setFixedHeight(22)
        launch_layout.addWidget(self.cmd_preview)
        
        self.launch_btn = QPushButton("Launch")
        self.launch_btn.setObjectName("LaunchButton")
        self.launch_btn.setFixedSize(100, 28)
        self.launch_btn.clicked.connect(self.launch_mame)
        launch_layout.addWidget(self.launch_btn)
        right_layout.addLayout(launch_layout)
        
        self.splitter.addWidget(right_panel)
        self.splitter.setStretchFactor(1, 1) # Balanced ratio
        main_vbox.addWidget(self.splitter)



    def populate_machine_tree(self, models, parent_item):
        for model in models:
            item = QTreeWidgetItem(parent_item)
            item.setText(0, model.get('description', 'Unknown'))
            if 'value' in model:
                item.setData(0, Qt.UserRole, model['value'])
            if 'children' in model:
                self.populate_machine_tree(model['children'], item)

    def init_tabs(self):
        # --- Video Tab ---
        video_tab = QWidget()
        v_layout = QVBoxLayout(video_tab)
        v_layout.setContentsMargins(15, 10, 15, 10)
        v_layout.setSpacing(6)
        
        row1 = QHBoxLayout()
        row1.setSpacing(10)
        self.use_bgfx = QCheckBox("BGFX")
        self.use_bgfx.setChecked(True)
        self.bgfx_backend = QComboBox()
        self.bgfx_backend.addItems(["Default", "OpenGL", "Vulkan", "Direct3D 11", "Direct3D 12"])
        
        row1.addWidget(self.use_bgfx)
        row1.addWidget(QLabel("Backend:"))
        row1.addWidget(self.bgfx_backend)
        
        row1.addSpacing(15)
        row1.addWidget(QLabel("Effects:"))
        self.video_effect = QComboBox()
        self.video_effect.addItems(["Default", "None", "CRT Geometry Deluxe", "HLSL", "LCRT", "Scanlines"])
        row1.addWidget(self.video_effect)
        row1.addStretch()
        v_layout.addLayout(row1)
        
        row2 = QHBoxLayout()
        row2.setSpacing(10)
        row2.addWidget(QLabel("Window Mode:"))
        self.win_mode = QComboBox()
        self.win_mode.addItems(["Window 1x", "Window 2x", "Window 3x", "Full Screen"])
        self.win_mode.setCurrentIndex(1)
        row2.addWidget(self.win_mode)
        
        self.square_pixels = QCheckBox("Square Pixels")
        row2.addSpacing(15)
        row2.addWidget(self.square_pixels)
        row2.addStretch()
        v_layout.addLayout(row2)

        row3 = QHBoxLayout()
        row3.setSpacing(15)
        self.capture_mouse = QCheckBox("Capture Mouse")
        self.disk_sounds = QCheckBox("Disk Sound Effects")
        row3.addWidget(self.capture_mouse)
        row3.addWidget(self.disk_sounds)
        row3.addStretch()
        v_layout.addLayout(row3)

        # Connect all
        for w in [self.use_bgfx, self.bgfx_backend, self.video_effect, self.win_mode, 
                  self.square_pixels, self.capture_mouse, self.disk_sounds]:
            if isinstance(w, QCheckBox): w.stateChanged.connect(lambda: self.update_and_preview())
            else: w.currentIndexChanged.connect(lambda: self.update_and_preview())

        self.tabs.addTab(video_tab, "Video")

        # --- CPU Tab ---
        cpu_tab = QWidget()
        c_layout = QVBoxLayout(cpu_tab)
        row_c1 = QHBoxLayout()
        row_c1.addWidget(QLabel("Speed:"))
        self.cpu_speed = QComboBox()
        self.cpu_speed.addItems(["100%", "200%", "300%", "400%", "500%", "No Throttle"])
        self.cpu_speed.currentIndexChanged.connect(lambda: self.update_and_preview())
        row_c1.addWidget(self.cpu_speed)
        row_c1.addStretch()
        c_layout.addLayout(row_c1)

        row_c2 = QHBoxLayout()
        self.debugger = QCheckBox("Debug")
        self.debugger.stateChanged.connect(lambda: self.update_and_preview())
        self.rewind = QCheckBox("Rewind")
        self.rewind.stateChanged.connect(lambda: self.update_and_preview())
        row_c2.addWidget(self.debugger)
        row_c2.addWidget(self.rewind)
        row_c2.addStretch()
        c_layout.addLayout(row_c2)
        self.tabs.addTab(cpu_tab, "CPU")

        # --- A/V Tab ---
        av_tab = QWidget()
        av_layout = QVBoxLayout(av_tab)
        av_layout.setContentsMargins(15, 10, 15, 10)
        av_layout.setSpacing(6)

        def add_av_row(label, attr_prefix):
            row = QHBoxLayout()
            cb = QCheckBox(label)
            edit = QLineEdit()
            edit.setPlaceholderText(f"/path/to/file.{label.split()[-1].lower()}")
            setattr(self, f"{attr_prefix}_check", cb)
            setattr(self, f"{attr_prefix}_path", edit)
            cb.stateChanged.connect(lambda: self.update_and_preview())
            edit.textChanged.connect(lambda: self.update_and_preview())
            row.addWidget(cb)
            row.addWidget(edit, 1) # Give path field more space
            av_layout.addLayout(row)

        add_av_row("Generate AVI", "avi")
        add_av_row("Generate WAV", "wav")
        add_av_row("Generate VGM", "vgm")
        av_layout.addStretch()
        self.tabs.addTab(av_tab, "A/V")

        # --- Paths Tab ---
        paths_tab = QWidget()
        p_layout = QVBoxLayout(paths_tab)
        p_layout.setContentsMargins(15, 10, 15, 10)
        p_layout.setSpacing(6)
        
        row_p1 = QHBoxLayout()
        self.share_dir_check = QCheckBox("Share Directory")
        self.share_dir_path = QLineEdit()
        self.share_dir_path.setPlaceholderText("/path/to/directory/")
        self.share_dir_check.stateChanged.connect(lambda: self.update_and_preview())
        self.share_dir_path.textChanged.connect(lambda: self.update_and_preview())
        
        row_p1.addWidget(self.share_dir_check)
        row_p1.addWidget(self.share_dir_path, 1)
        p_layout.addLayout(row_p1)
        p_layout.addStretch()
        self.tabs.addTab(paths_tab, "Paths")
        self.mame_path_label = QLabel(f"MAME: {self.launcher.mame_path}")
        p_layout.addWidget(self.mame_path_label)
        p_layout.addStretch()
        self.tabs.addTab(paths_tab, "Paths")

    def update_and_preview(self):
        self.update_command_line()

    def filter_machines(self, text):
        query = text.lower()
        self.filter_tree_item(self.machine_tree.invisibleRootItem(), query)

    def filter_tree_item(self, item, query):
        item_text = item.text(0).lower()
        is_match = query in item_text
        any_child_match = False
        for i in range(item.childCount()):
            if self.filter_tree_item(item.child(i), query):
                any_child_match = True
        visible = is_match or any_child_match
        item.setHidden(not visible)
        if visible and query: item.setExpanded(True)
        return visible

    def on_machine_selected(self, item):
        machine_name = item.data(0, Qt.UserRole)
        if not machine_name: return
        self.selected_machine = machine_name
        self.machine_title_bar = item.text(0)
        self.setWindowTitle(f"Ample - {self.machine_title_bar}")
        
        # Sticky Settings: Don't wipe self.current_slots! 
        # This allows Slot 7 etc to carry over across compatible machines.
        self.current_media = {}
        data = self.data_manager.get_machine_description(machine_name)
        if data:
            self.current_machine_data = data
            self.initialize_default_slots(data)
            self.refresh_ui()

    def initialize_default_slots(self, data, depth=0):
        if depth > 20: return
        
        # 1. Process 'slots'
        if 'slots' in data:
            for slot in data['slots']:
                slot_name = slot.get('name')
                if not slot_name: continue
                
                if slot_name not in self.current_slots:
                    best_val = None
                    options = slot.get('options', [])
                    
                    # Target 1: Find ANY explicit default (can be empty string)
                    for opt in options:
                        if opt.get('default'):
                            best_val = opt.get('value')
                            break
                    
                    # Target 2: If NO option is marked default at all, pick the first one
                    if best_val is None and options:
                        best_val = options[0].get('value')
                    
                    if best_val is not None:
                        self.current_slots[slot_name] = best_val

                # Always recurse into children of the current selection
                current_val = self.current_slots.get(slot_name)
                for opt in slot.get('options', []):
                    # Use str() for safe comparison (ints vs strings in plist)
                    if str(opt.get('value')) == str(current_val):
                        self.initialize_default_slots(opt, depth + 1)
                        break

        # 2. Process 'devices'
        if 'devices' in data:
            for dev in data['devices']:
                self.initialize_default_slots(dev, depth + 1)

    def on_tree_double_clicked(self, item, column):
        if item.childCount() == 0:
            machine_name = item.data(0, Qt.UserRole)
            if machine_name:
                self.launch_mame()

    def update_options_ui(self, data):
        self.current_machine_data = data
        self.refresh_ui()

    def refresh_ui(self):
        # 1. Clean the fixed layouts without destroying the frames themselves
        self.clear_grid(self.slots_layout)
        self.clear_grid(self.media_layout)
        
        # 2. Re-render
        self.render_slots_ui()
        self.render_media_ui()
        self.update_command_line()

    def render_slots_ui(self):
        # We now add directly to self.slots_layout
        self.slots_layout.setContentsMargins(10, 10, 10, 10)
        self.slots_layout.setSpacing(6)
        
        if 'slots' in self.current_machine_data:
            # 1. RAM Group
            ram_slot = next((s for s in self.current_machine_data['slots'] if s['name'] == 'ramsize'), None)
            if ram_slot:
                self.add_slot_row(self.slots_layout, ram_slot)
                self.slots_layout.addSpacing(5)

            # 2. Disk Drives - EXACTLY same structure as add_slot_row
            # Mac hides popup button but it still takes up space. Hamburger at far right.
            dd_slot = next((s for s in self.current_machine_data['slots'] if s.get('description') == 'Disk Drives'), None)
            if dd_slot:
                row = QHBoxLayout()
                row.setContentsMargins(0, 0, 0, 0)
                row.setSpacing(5)
                
                # Label - IDENTICAL to add_slot_row
                lbl = QLabel("Disk Drives:")
                lbl.setFixedWidth(100)
                lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                lbl.setStyleSheet("color: #ccc; font-size: 11px;")
                row.addWidget(lbl)
                
                # Invisible container - same size as add_slot_row combo (160px)
                invisible_container = QLabel("")
                invisible_container.setFixedWidth(160)
                invisible_container.setFixedHeight(22)
                row.addWidget(invisible_container)
                
                # Hamburger at FAR RIGHT - SAME position as other rows
                cur_val = self.current_slots.get(dd_slot['name'])
                selected_opt = next((o for o in dd_slot['options'] if str(o.get('value')) == str(cur_val)), dd_slot['options'][0])
                target_data = selected_opt
                if 'devname' in selected_opt:
                    devname = selected_opt['devname']
                    m_dev = next((d for d in self.current_machine_data.get('devices', []) if d.get('name') == devname), None)
                    if m_dev: target_data = m_dev
                
                h_btn = self.create_hamburger(target_data)
                row.addWidget(h_btn)
                
                # Insert stretch at index 0 - IDENTICAL to add_slot_row
                row.insertStretch(0)
                
                self.slots_layout.addLayout(row)











            # 3. All other slots
            for slot in self.current_machine_data['slots']:
                if slot['name'] != 'ramsize' and slot.get('description') != 'Disk Drives':
                    self.add_slot_row(self.slots_layout, slot)
            
        self.slots_layout.addStretch()

    def add_slot_row(self, parent_layout, slot):
        slot_name = slot['name']
        desc = slot.get('description')
        if not desc: return

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0) # Explicitly zero margins to match Disk Drives
        row.setSpacing(5)
        lbl = QLabel(f"{desc}:")
        lbl.setFixedWidth(100)
        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl.setStyleSheet("color: #ccc; font-size: 11px;")
        
        combo = QComboBox()
        from PySide6.QtWidgets import QListView
        lv = QListView()
        combo.setView(lv)
        # MacOS list is wide, field is narrow
        lv.setMinimumWidth(350) 
        lv.setStyleSheet("background-color: #1a1a1a; color: #ddd; border: 1px solid #444; outline: none;")
        
        combo.setObjectName(slot_name)
        combo.setProperty("appleStyle", "slot")
        combo.setFixedWidth(160)  # Match Mac popup width
        combo.setFixedHeight(22)
        # Style combo - hide native arrow, we'll use overlay label
        combo.setStyleSheet("""
            QComboBox {
                background-color: #3d3d3d;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 2px 20px 2px 8px;
                color: #eee;
                font-size: 11px;
            }
            QComboBox::drop-down {
                width: 0px;
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                width: 0px;
                height: 0px;
            }
            QComboBox:hover {
                border-color: #777;
            }
        """)

        
        for opt in slot['options']:
            opt_desc = opt.get('description') or opt['value'] or "—None—"
            combo.addItem(opt_desc, opt['value'])
        
        combo.blockSignals(True)
        val = self.current_slots.get(slot_name)
        idx = combo.findData(str(val))
        if idx < 0: idx = combo.findData(val)
        if idx >= 0: combo.setCurrentIndex(idx)
        combo.blockSignals(False)
        
        combo.currentIndexChanged.connect(self.on_slot_changed)
        
        # Create container with combo and arrow overlay
        combo_widget = QWidget()
        combo_widget.setFixedSize(160, 22)
        combo.setParent(combo_widget)
        combo.move(0, 0)
        
        # Arrow label overlay - narrow blue like Mac
        arrow_label = QLabel("↕", combo_widget)
        arrow_label.setFixedSize(20, 20)
        arrow_label.move(140, 1)  # 140 + 20 = 160, narrow and covers right edge
        arrow_label.setAlignment(Qt.AlignCenter)
        arrow_label.setStyleSheet("""
            background-color: #3b7ee1;
            color: white;
            font-size: 12px;
            font-weight: bold;
            padding-bottom: 3px;
            border: none;
            border-top-right-radius: 3px;
            border-bottom-right-radius: 3px;
        """)
        arrow_label.setAttribute(Qt.WA_TransparentForMouseEvents)  # Click through to combo
        
        # Order: Label -> ComboWidget -> Hamburger (then addStretch at 0)
        row.addWidget(lbl)
        row.addWidget(combo_widget)

        # Subtle Hamburger - Unified with create_hamburger size
        selected_opt = next((o for o in slot['options'] if str(o.get('value')) == str(val)), None)
        
        has_sub = False
        target_data = selected_opt
        if selected_opt:
            if 'slots' in selected_opt or 'devices' in selected_opt:
                has_sub = True
            elif 'devname' in selected_opt:
                devname = selected_opt['devname']
                m_dev = next((d for d in self.current_machine_data.get('devices', []) if d.get('name') == devname), None)
                if m_dev and ('slots' in m_dev or 'devices' in m_dev):
                    has_sub = True
                    target_data = m_dev

        if has_sub:
            sub_btn = self.create_hamburger(target_data)
            row.addWidget(sub_btn)
        else:
            # Invisible placeholder - same size as hamburger for alignment
            invisible_hamburger = QLabel("")
            invisible_hamburger.setFixedSize(22, 22)
            row.addWidget(invisible_hamburger)

        # KEY FIX: Insert stretch at index 0 to force right-alignment
        row.insertStretch(0)

        parent_layout.addLayout(row)

    def create_hamburger(self, data):
        btn = QPushButton("≡")
        btn.setFixedSize(22, 22)
        btn.setFlat(True)
        btn.setStyleSheet("color: #999; font-size: 18px; border: none; background: transparent;")
        btn.clicked.connect(lambda _, d=data: self.show_sub_slots(d, btn))
        return btn

    def gather_active_slots(self, data, depth=0):
        if depth > 10: return []
        slots = []
        
        # Check standard slots
        if 'slots' in data:
            for slot in data['slots']:
                slots.append(slot)
                selected_val = self.current_slots.get(slot['name'])
                for opt in slot['options']:
                    if opt['value'] == selected_val:
                        slots.extend(self.gather_active_slots(opt, depth + 1))
                        break

        # Check devices
        if 'devices' in data:
            for dev in data['devices']:
                slots.extend(self.gather_active_slots(dev, depth + 1))
                
        return slots

    def show_sub_slots(self, data, button):
        # Prevent immediate reopening when clicking the same button to close (race condition)
        # Windows Qt: Popup auto-hides on mouse press OUTSIDE, then button-click fires.
        now = time.time()
        if (now - self.last_popup_close_time < 0.3) and (self.last_popup_id == id(data)):
            return

        # If there's an active popup, close it first
        if self.active_popup is not None:
            self.active_popup.close()
            # Note: closeEvent will set self.active_popup = None
            
        # Create and show the popup relative to the button
        popup = SubSlotPopup(self, data, self.current_slots, self.refresh_ui)
        self.active_popup = popup
        
        pos = button.mapToGlobal(QPoint(button.width(), 0))
        # Shift a bit to the left to align with Mac bubble
        popup.move(pos.x() - 100, pos.y() + button.height() + 5)
        popup.show()

    def render_media_ui(self):
        total_media = {}
        
        def aggregate_media(data, depth=0, is_root=False):
            if depth > 10: return
            
            # 1. Base media for this component
            if 'media' in data:
                for k, v in data['media'].items():
                    # Map common plist keys to UI labels
                    key = k
                    if k == 'cass': key = 'cassette'
                    total_media[key] = total_media.get(key, 0) + v
            
            # 2. Recurse into selected slots
            if 'slots' in data:
                for slot in data['slots']:
                    selected_val = self.current_slots.get(slot['name'])
                    for opt in slot['options']:
                        if str(opt.get('value')) == str(selected_val):
                            # Recurse into the option data (for nested slots/media)
                            aggregate_media(opt, depth + 1)
                            # Also follow devname to global devices
                            if 'devname' in opt:
                                devname = opt['devname']
                                machine_devs = self.current_machine_data.get('devices', [])
                                m_dev = next((d for d in machine_devs if d.get('name') == devname), None)
                                if m_dev: aggregate_media(m_dev, depth + 1)
                            break
            
            # 3. Handle 'devices' (ONLY if not root machine, or specifically defined as active)
            # In these plists, root 'devices' are definitions, not active instances unless in a slot.
            if not is_root and 'devices' in data:
                for dev in data['devices']:
                    aggregate_media(dev, depth + 1)
                            
        aggregate_media(self.current_machine_data, is_root=True)

        # UI FIX: Cap counts and cleanup
        for k in ['hard', 'cdrom', 'cassette']:
            if k in total_media and total_media[k] > 0:
                total_media[k] = 1
            else:
                total_media.pop(k, None)

        # Use our persistent media_layout
        self.media_layout.setContentsMargins(0, 0, 15, 0)
        self.media_layout.setSpacing(8)
        
        def add_media_group(target_layout, title, m_type_key):
            if m_type_key in total_media:
                count = total_media[m_type_key]
                row_h = QHBoxLayout()
                handle = QLabel("⠇")
                handle.setStyleSheet("color: #444; font-size: 14px; margin-right: 2px;")
                row_h.addWidget(handle)
                lbl = QLabel(f"<b>{title}</b>")
                lbl.setStyleSheet("font-size: 11px; color: #888;")
                row_h.addWidget(lbl)
                row_h.addStretch()
                target_layout.addLayout(row_h)
                
                for i in range(count):
                    key = f"{m_type_key}{i+1}" if count > 1 else m_type_key
                    row = QHBoxLayout()
                    row.setContentsMargins(15, 0, 0, 0) # Indent rows like Mac
                    row.setSpacing(5)
                    
                    lbl_choose = QLabel("Choose...")
                    lbl_choose.setStyleSheet("color: #555; font-size: 10px;")
                    lbl_choose.setFixedWidth(65)
                    lbl_choose.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    
                    edit = QLineEdit()
                    edit.setPlaceholderText("None")
                    edit.setText(self.current_media.get(key, ""))
                    edit.setFixedHeight(18)
                    edit.setStyleSheet("background-color: transparent; border: 1px solid #333; color: #888; font-size: 10px;")
                    
                    # Blue Double Arrow Button (Select)
                    btn_sel = QPushButton("↕")
                    btn_sel.setFixedSize(20, 18)
                    btn_sel.setStyleSheet("""
                        QPushButton { 
                            background-color: #3b7ee1; 
                            color: white; 
                            border: none; 
                            border-radius: 2px; 
                            font-weight: bold; 
                            font-size: 12px;
                            padding-bottom: 3px;
                        }
                        QPushButton:hover { background-color: #4a8df0; }
                    """)
                    btn_sel.clicked.connect(lambda _, k=key, e=edit: self.browse_media(k, e))
                    
                    # Eject Button
                    btn_eject = QPushButton("⏏")
                    btn_eject.setFixedSize(20, 18)
                    btn_eject.setStyleSheet("""
                        QPushButton { background-color: transparent; color: #666; border: none; font-size: 12px; }
                        QPushButton:hover { color: white; }
                    """)
                    btn_eject.clicked.connect(lambda _, k=key, e=edit: self.eject_media(k, e))
                    
                    row.addWidget(lbl_choose)
                    row.addWidget(edit)
                    row.addWidget(btn_sel)
                    row.addWidget(btn_eject)
                    target_layout.addLayout(row)

        add_media_group(self.media_layout, "5.25\" Floppies", "floppy_5_25")
        add_media_group(self.media_layout, "3.5\" Floppies", "floppy_3_5")
        add_media_group(self.media_layout, "Hard Drives", "hard")
        add_media_group(self.media_layout, "CD-ROMs", "cdrom")
        add_media_group(self.media_layout, "Cassettes", "cassette")

        self.media_layout.addStretch()

    def on_slot_changed(self):
        combo = self.sender()
        self.current_slots[combo.objectName()] = combo.currentData()
        # Full refresh because changing a slot might add more slots OR change media
        self.refresh_ui()

    def eject_media(self, key, edit):
        if key in self.current_media:
            del self.current_media[key]
            edit.clear()
            self.update_command_line()

    def browse_media(self, key, edit):
        path, _ = QFileDialog.getOpenFileName(self, f"Select file for {key}")
        if path:
            edit.setText(path)
            self.current_media[key] = path
            self.update_command_line()

    def update_command_line(self):
        if not self.selected_machine: return
        
        # Build base args
        args = self.launcher.build_args(self.selected_machine, self.current_slots, self.current_media)
        
        # Add UI Video options for preview
        win_mode = self.win_mode.currentText()
        if "Window" in win_mode:
            args.append("-window")
        else:
            args.extend(["-nowindow", "-maximize"])

        if self.use_bgfx.isChecked():
            args.extend(["-video", "bgfx"])
            backend = self.bgfx_backend.currentText().lower().replace(" ", "")
            if backend != "default":
                args.extend(["-bgfx_backend", backend])
            
            effect = self.video_effect.currentText()
            effect_map = {"CRT Geometry Deluxe": "crt-geom-deluxe", "HLSL": "hlsl", "LCRT": "lcrt", "Scanlines": "scanlines"}
            if effect in effect_map:
                args.extend(["-bgfx_screen_chains", effect_map[effect]])
        
        # CPU settings
        speed_text = self.cpu_speed.currentText()
        if speed_text == "No Throttle":
            args.append("-nothrottle")
        elif speed_text != "100%":
            speed_val = float(speed_text.replace("%", "")) / 100.0
            args.extend(["-speed", str(speed_val)])
            
        if self.rewind.isChecked():
            args.append("-rewind")
        if self.debugger.isChecked():
            args.append("-debug")
            
        # A/V settings
        if self.avi_check.isChecked() and self.avi_path.text():
            args.extend(["-aviwrite", self.avi_path.text()])
        if hasattr(self, 'wav_check') and self.wav_check.isChecked() and self.wav_path.text():
            args.extend(["-wavwrite", self.wav_path.text()])
        if hasattr(self, 'vgm_check') and self.vgm_check.isChecked() and self.vgm_path.text():
            args.extend(["-vgmwrite", self.vgm_path.text()])
        
        # Paths Settings
        if hasattr(self, 'share_dir_check') and self.share_dir_check.isChecked() and self.share_dir_path.text():
            args.extend(["-share", self.share_dir_path.text()])

        # Samples (Still useful for some machines)
        args.extend(["-rompath", self.roms_dir])
        self.cmd_preview.setText("mame " + " ".join(args))

    def clear_grid_column(self, col):
        # Extremely aggressive clearing to prevent widget ghosting
        item = self.options_grid.itemAtPosition(0, col)
        if item:
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()
            self.options_grid.removeItem(item)

    def clear_grid(self, layout):
        if not layout: return
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self.clear_grid(item.layout())
            # Layout items that are not widgets or layouts are rare but handled by takeAt

    @Slot()
    def show_rom_manager(self):
        RomManagerDialog(self.rom_manager, self).exec()

    @Slot()
    def show_settings(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Settings")
        layout = QVBoxLayout(dialog)

        path_label = QLabel(f"MAME: {self.launcher.mame_path}")
        layout.addWidget(path_label)
        
        # Bottom status and progress
        self.settings_status = QLabel("")
        layout.addWidget(self.settings_status)

        self.settings_progress = QProgressBar()
        self.settings_progress.setVisible(False)
        layout.addWidget(self.settings_progress)

        # Buttons
        btn1 = QPushButton("Select MAME...")
        btn1.clicked.connect(lambda: self.select_mame(dialog, path_label))
        layout.addWidget(btn1)
        
        btn2 = QPushButton("Download MAME")
        btn2.clicked.connect(lambda: self.download_mame(dialog, path_label))
        layout.addWidget(btn2)
        
        # Auto-run check immediately
        self.check_for_mame(path_label)
        
        dialog.exec()

    def select_mame(self, dialog, label):
        path, _ = QFileDialog.getOpenFileName(dialog, "Select MAME", "", "*.exe")
        if path:
            self.launcher.mame_path = path
            self.check_for_mame(label)

    def download_mame(self, dialog, label):
        target_dir = os.path.join(self.app_dir, "mame_bin")
        self.settings_progress.setVisible(True)
        worker = MameDownloadWorker(target_dir)
        self.active_workers.append(worker)
        worker.progress.connect(self.settings_progress.setValue)
        worker.progress.connect(lambda v, t: self.settings_progress.setMaximum(t))
        worker.status.connect(self.settings_status.setText)
        worker.finished.connect(lambda s, p: self.on_mame_dl_finished(worker, s, p, label))
        worker.start()

    def on_mame_dl_finished(self, worker, success, path, label):
        if worker in self.active_workers: self.active_workers.remove(worker)
        self.settings_progress.setVisible(False)
        self.settings_status.setText("Installer opened. Please complete extraction.")
        
        if success:
            QMessageBox.information(self, "Download Complete", 
                f"MAME installer has been opened.\n\n"
                f"1. In the installer, extract to: {self.app_dir}\\mame_bin\n"
                f"2. Once extraction is done, click 'Select MAME' to confirm.")
            
            # Immediate check in case it's already there
            self.check_for_mame(label)
        else:
            QMessageBox.critical(self, "Error", path)
            self.settings_status.setText("Download failed.")

    def check_for_mame(self, label=None):
        """Helper to check standard paths and update UI."""
        potential_paths = [
            os.path.join(self.app_dir, "mame_bin", "mame.exe"),
            os.path.join(self.app_dir, "mame.exe"),
        ]
        
        # Also check current path if it's already set and valid
        if hasattr(self, 'launcher') and self.launcher.mame_path and os.path.exists(self.launcher.mame_path) and self.launcher.mame_path != "mame":
            if self.launcher.mame_path not in potential_paths:
                potential_paths.insert(0, self.launcher.mame_path)

        for p in potential_paths:
            if os.path.exists(p) and os.path.isfile(p):
                self.launcher.mame_path = p
                if label:
                    label.setText(f"MAME: {p} <span style='color: #2ecc71;'>✅</span>")
                    label.setTextFormat(Qt.RichText)
                if hasattr(self, 'settings_status'):
                    self.settings_status.setText("MAME detected and configured!")
                return True
        
        if label:
            label.setText(f"MAME: Not found <span style='color: #e74c3c;'>❌</span>")
            label.setTextFormat(Qt.RichText)
        return False

    def launch_mame(self):
        if not self.selected_machine: return
        
        # Determine the MAME binary directory
        mame_bin_dir = os.path.dirname(self.launcher.mame_path)
        
        # Gather all options from UI
        extra_opts = [
            "-rompath", self.roms_dir,
            "-bgfx_path", os.path.join(mame_bin_dir, "bgfx"),
            "-artpath", os.path.join(mame_bin_dir, "artwork"),
            "-pluginspath", os.path.join(mame_bin_dir, "plugins"),
            "-languagepath", os.path.join(mame_bin_dir, "language"),
            "-ctrlrpath", os.path.join(mame_bin_dir, "ctrlr"),
        ]
        
        # Window Mode logic
        win_mode = self.win_mode.currentText()
        if "Window" in win_mode:
            extra_opts.append("-window")
            # For "Window 2x", we should ideally set -scale 2, 
            # but MAME handled window scale better with -window -nomax
            # and potentially -resolution if we have machine info.
            # Simplified: just -window is a good start.
        else:
            extra_opts.append("-nowindow")
            extra_opts.append("-maximize")

        # BGFX logic
        if self.use_bgfx.isChecked():
            extra_opts.extend(["-video", "bgfx"])
            backend = self.bgfx_backend.currentText().lower().replace(" ", "")
            if backend != "default":
                extra_opts.extend(["-bgfx_backend", backend])
            
            # Effects
            effect = self.video_effect.currentText()
            effect_map = {
                "CRT Geometry Deluxe": "crt-geom-deluxe",
                "HLSL": "hlsl",
                "LCRT": "lcrt",
                "Scanlines": "scanlines"
            }
            if effect in effect_map:
                extra_opts.extend(["-bgfx_screen_chains", effect_map[effect]])

        # CPU settings
        if self.cpu_speed.currentText() != "100":
            extra_opts.extend(["-speed", str(float(self.cpu_speed.currentText())/100.0)])
        if not self.throttle.isChecked():
            extra_opts.append("-nothrottle")
        if self.rewind.isChecked():
            extra_opts.append("-rewind")
        if self.debugger.isChecked():
            extra_opts.append("-debug")
            
        # A/V settings
        if not self.use_samples.isChecked():
            extra_opts.append("-nosamples")
        if self.avi_path.text():
            extra_opts.extend(["-aviwrite", self.avi_path.text()])

        self.launcher.launch(self.selected_machine, self.current_slots, self.current_media, extra_opts)

    def load_persistent_settings(self):
        """Restore window geometry and splitter state."""
        geom = self.settings.value("geometry")
        if geom:
            self.restoreGeometry(geom)
        else:
            self.resize(1100, 800)
            
        splitter_state = self.settings.value("splitterState")
        if splitter_state:
            self.splitter.restoreState(splitter_state)

        # Restore last selected machine
        last_machine = self.settings.value("lastMachine")
        if last_machine:
            item = self.find_item_by_value(self.machine_tree.invisibleRootItem(), last_machine)
            if item:
                self.machine_tree.setCurrentItem(item)
                self.on_machine_selected(item)
                # Expand to show the selection
                parent = item.parent()
                while parent:
                    parent.setExpanded(True)
                    parent = parent.parent()

    def find_item_by_value(self, parent_item, value):
        for i in range(parent_item.childCount()):
            child = parent_item.child(i)
            if child.data(0, Qt.UserRole) == value:
                return child
            res = self.find_item_by_value(child, value)
            if res: return res
        return None

    def closeEvent(self, event: QCloseEvent):
        """Save settings before exiting."""
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("splitterState", self.splitter.saveState())
        if self.selected_machine:
            self.settings.setValue("lastMachine", self.selected_machine)
        
        # Clean up threads
        for worker in self.active_workers[:]:
            worker.terminate()
            worker.wait()
        event.accept()

    def apply_premium_theme(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e1e; }
            
            #Toolbar { 
                background-color: #2d2d2d; 
                border-bottom: 1px solid #3d3d3d;
            }
            
            #ToolbarButton {
                background-color: transparent;
                border: none;
                color: #cccccc;
                padding: 8px 15px;
                font-size: 13px;
                font-weight: bold;
                border-radius: 4px;
            }
            #ToolbarButton:hover { background-color: #3d3d3d; color: white; }

            #LeftPanel { 
                background-color: #1a1a1a; 
                border-right: 1px solid #2d2d2d;
            }
            
            #SearchInput {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 5px;
                padding: 6px 10px;
                color: white;
                margin-bottom: 5px;
            }

            #MachineTree {
                background-color: transparent;
                border: none;
                color: #cccccc;
                font-size: 13px;
                show-decoration-selected: 1;
            }
            #MachineTree::item { padding: 5px; }
            #MachineTree::item:selected {
                background-color: #0078d4;
                color: white;
                border-radius: 4px;
            }
            #MachineTree::item:hover:!selected {
                background-color: #2d2d2d;
            }

            #RightPanel { background-color: #2b2b2b; }

            #SmallLabel {
                color: #666666;
                font-size: 10px;
                font-weight: bold;
                margin-top: 5px;
            }

            QTabWidget { background-color: transparent; }
            QTabWidget::pane { border: 1px solid #3d3d3d; background-color: #222; border-radius: 4px; }
            QTabBar::tab {
                background-color: #333;
                color: #888;
                padding: 4px 12px;
                font-size: 11px;
                border: 1px solid #444;
                margin-right: 1px;
            }
            QTabBar::tab:selected {
                background-color: #0078d4;
                color: white;
            }

            QLabel { color: #cccccc; font-size: 11px; }

            QComboBox[appleStyle="slot"] {
                background-color: #2a2a2a;
                border: 1px solid #444;
                border-radius: 4px;
                padding: 1px 4px;
                color: #ddd;
                font-size: 11px;
            }
            QComboBox[appleStyle="slot"]::drop-down {
                border: none;
                background-color: #3b7ee1;
                width: 16px;
                border-top-right-radius: 3px;
                border-bottom-right-radius: 3px;
            }
            QComboBox[appleStyle="slot"]::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid white;
                margin-top: 2px;
            }
            
            /* Popups: Mandatory Opaque Background for Windows */
            QComboBox QAbstractItemView {
                background-color: #1a1a1a;
                border: 1px solid #444;
                color: #ddd;
                selection-background-color: #0078d4;
                selection-color: white;
            }
            /* Alternative list target for some Windows setups */
            QListView {
                background-color: #1a1a1a;
                color: #ddd;
            }

            /* Normal ComboBoxes */
            QComboBox {
                background-color: #1a1a1a;
                border: 1px solid #333;
                border-radius: 3px;
                padding: 2px;
                color: #ccc;
            }
        """)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AmpleMainWindow()
    window.show()
    sys.exit(app.exec())
