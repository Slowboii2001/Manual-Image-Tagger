import sys
import json
import traceback
from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QListWidget, QListWidgetItem, 
                             QLabel, QFileDialog, QAbstractItemView, QLineEdit, QSlider,
                             QSplitter, QMessageBox, QLayout, QScrollArea, QStackedWidget,
                             QButtonGroup)
from PyQt6.QtCore import Qt, QSize, QPoint, QRect, QMimeData, QVariantAnimation, QEvent
from PyQt6.QtGui import QPixmap, QIcon, QImageReader, QDrag

class FlowLayout(QLayout):
    """
    Custom core layout engine that arranges widgets horizontally and wraps them 
    sequentially down to the next line when horizontal boundaries are reached.
    """
    def __init__(self, parent=None, margin=0, hspacing=6, vspacing=6):
        super().__init__(parent)
        self._itemList = []
        self._hspacing = hspacing
        self._vspacing = vspacing
        self.setContentsMargins(margin, margin, margin, margin)

    def __del__(self):
        while self.count() > 0:
            self.takeAt(0)

    def addItem(self, item):
        self._itemList.append(item)

    def count(self):
        return len(self._itemList)

    def itemAt(self, index):
        if 0 <= index < len(self._itemList):
            return self._itemList[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._itemList):
            return self._itemList.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._doLayout(QRect(0, 0, width, 0), applyGeometry=False)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._doLayout(rect, applyGeometry=True)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._itemList:
            if item.widget() and item.widget().isHidden():
                continue
            size = size.expandedTo(item.minimumSize())
        margins = self.getContentsMargins()
        size += QSize(margins[0] + margins[2], margins[1] + margins[3])
        return size

    def _doLayout(self, rect, applyGeometry=False):
        left, top, right, bottom = self.getContentsMargins()
        effectiveRect = rect.adjusted(+left, +top, -right, -bottom)
        x = effectiveRect.x()
        y = effectiveRect.y()
        lineHeight = 0

        for item in self._itemList:
            if item.widget() and item.widget().isHidden():
                continue
                
            nextX = x + item.sizeHint().width() + self._hspacing
            if nextX - self._hspacing > effectiveRect.right() and lineHeight > 0:
                x = effectiveRect.x()
                y = y + lineHeight + self._vspacing
                nextX = x + item.sizeHint().width() + self._hspacing
                lineHeight = 0

            if applyGeometry:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = nextX
            lineHeight = max(lineHeight, item.sizeHint().height())

        return y + lineHeight - effectiveRect.y() + top + bottom


class TagTileWidget(QWidget):
    """ Custom widget for Tag tiles. Handles text-wrapping, highlights, and drag execution. """
    def __init__(self, tag_text, initial_count=0, parent=None):
        super().__init__(parent)
        self.tag_text = tag_text
        self.is_selected = False
        
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 6, 4) 
        layout.setSpacing(6)

        self.lbl_count = QLabel(f"{initial_count}")
        self.lbl_count.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_text = QLabel(tag_text)
        self.lbl_text.setWordWrap(True) 
        self.lbl_text.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        layout.addWidget(self.lbl_count, 0)
        layout.addWidget(self.lbl_text, 1)

        self.update_styles("") 

    def update_count(self, new_count):
        self.lbl_count.setText(f"{new_count}")
        if self.parent() and hasattr(self.parent(), 'recalculate_tile_sizes'):
            self.parent().recalculate_tile_sizes()

    def update_styles(self, search_query=""):
        query = search_query.lower().strip()
        is_match = (query in self.tag_text.lower()) if query else True
        
        if self.is_selected:
            if query and not is_match:
                self.setStyleSheet("background-color: #1a4480; border: 1px solid #103060; border-radius: 4px;")
                self.lbl_count.setStyleSheet("background-color: rgba(255, 255, 255, 0.08); color: #aaaaaa; font-weight: bold; border-radius: 3px; padding: 2px 6px;")
                self.lbl_text.setStyleSheet("color: #aaaaaa; padding-left: 2px;")
            else:
                self.setStyleSheet("background-color: #2b78e4; border: 1px solid #004cb3; border-radius: 4px;")
                self.lbl_count.setStyleSheet("background-color: rgba(255, 255, 255, 0.18); color: white; font-weight: bold; border-radius: 3px; padding: 2px 6px;")
                self.lbl_text.setStyleSheet("color: white; padding-left: 2px;")
        else:
            if query:
                if is_match:
                    self.setStyleSheet("background-color: #2d2a20; border: 1px solid #ffcc00; border-radius: 4px;")
                    self.lbl_count.setStyleSheet("background-color: #1a1a1a; color: #ffcc00; font-weight: bold; border-radius: 3px; padding: 2px 6px; border: 1px solid #443c1a;")
                    self.lbl_text.setStyleSheet("color: #ffffff; font-weight: 500; padding-left: 2px;")
                else:
                    self.setStyleSheet("background-color: #161616; border: 1px solid #222222; border-radius: 4px;")
                    self.lbl_count.setStyleSheet("background-color: #121212; color: #444444; font-weight: bold; border-radius: 3px; padding: 2px 6px; border: 1px solid #1a1a1a;")
                    self.lbl_text.setStyleSheet("color: #555555; padding-left: 2px;")
            else:
                self.setStyleSheet("background-color: #262626; border: 1px solid #3a3a3a; border-radius: 4px;")
                self.lbl_count.setStyleSheet("background-color: #1a1a1a; color: #7fdbff; font-weight: bold; border-radius: 3px; padding: 2px 6px; border: 1px solid #2d2d2d;")
                self.lbl_text.setStyleSheet("color: #e0e0e0; padding-left: 2px;")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_position = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if (event.position().toPoint() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
            return
            
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(self.tag_text)
        drag.setMimeData(mime_data)
        
        pixmap = self.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(event.position().toPoint())
        
        drag.exec(Qt.DropAction.MoveAction)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if hasattr(self, 'drag_start_position'):
                delta = (event.position().toPoint() - self.drag_start_position).manhattanLength()
                if delta < QApplication.startDragDistance():
                    if self.parent() and hasattr(self.parent(), 'select_tile'):
                        self.parent().select_tile(self)
        super().mouseReleaseEvent(event)


class TagContainerWidget(QWidget):
    """ Custom fluid grid container that calculates geometric placement dynamically
        and gently auto-scrolls when dragging items near panel edges. """
    def __init__(self, main_app, parent=None):
        super().__init__(parent)
        self.main_app = main_app
        self.layout = FlowLayout(self, margin=6, hspacing=6, vspacing=6)
        self.setAcceptDrops(True)
        self.tiles = []
        self.current_width_setting = 130
        self.current_height_setting = 36 
        
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("background-color: #121212;")

    def add_tag_tile(self, tag_text, count=0):
        if any(t.tag_text == tag_text for t in self.tiles):
            return
        tile = TagTileWidget(tag_text, count, self)
        self.tiles.append(tile)
        self.layout.addWidget(tile)
        
        current_search = self.main_app.txt_search_tags.text() if hasattr(self.main_app, 'txt_search_tags') else ""
        tile.update_styles(current_search)
        self.recalculate_tile_sizes()

    def remove_selected_tags(self):
        for tile in list(self.tiles):
            if tile.is_selected:
                self.layout.removeWidget(tile)
                tile.setParent(None)
                self.tiles.remove(tile)
        self.recalculate_tile_sizes()
        self.main_app.sync_data_engine(source="tag")

    def clear_all(self):
        for tile in list(self.tiles):
            self.layout.removeWidget(tile)
            tile.setParent(None)
        self.tiles.clear()
        self.recalculate_tile_sizes()

    def clearSelection(self):
        current_search = self.main_app.txt_search_tags.text() if hasattr(self.main_app, 'txt_search_tags') else ""
        for tile in self.tiles:
            tile.is_selected = False
            tile.update_styles(current_search)

    def selectedItems(self):
        return [t for t in self.tiles if t.is_selected]

    def select_tile(self, target_tile):
        current_search = self.main_app.txt_search_tags.text() if hasattr(self.main_app, 'txt_search_tags') else ""
        
        if self.main_app.btn_mode_toggle.isChecked() and self.main_app.main_workspace_stack.currentIndex() == 0:
            target_tile.is_selected = not target_tile.is_selected
            target_tile.update_styles(current_search)
            self.main_app.toggle_tag_for_current_focus_image(target_tile.tag_text, target_tile.is_selected)
        else:
            for tile in self.tiles:
                tile.is_selected = (tile == target_tile)
                tile.update_styles(current_search)
            self.main_app.sync_data_engine(source="tag")

    def filter_tags(self, search_text):
        for tile in self.tiles:
            tile.update_styles(search_text)
        self.update()

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        event.acceptProposedAction()

    def recalculate_tile_sizes(self):
        if not self.tiles:
            return
        fm = self.fontMetrics()
        max_height_needed = self.current_height_setting
        
        for tile in self.tiles:
            if tile.isHidden():
                continue
                
            count_str = tile.lbl_count.text()
            count_width = fm.horizontalAdvance(count_str)
            occupied_width = count_width + 42
            available_text_width = self.current_width_setting - occupied_width
            if available_text_width < 25:
                available_text_width = 25
                
            target_rect = fm.boundingRect(
                0, 0, 
                available_text_width, 2000, 
                Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignLeft,
                tile.tag_text
            )
            required_height = target_rect.height() + 16
            
            if required_height > max_height_needed:
                max_height_needed = required_height
                
        for tile in self.tiles:
            tile.setFixedSize(self.current_width_setting, max_height_needed)
            
        self.layout.invalidate()
        self.updateGeometry()


class SmoothScrollArea(QScrollArea):
    """ Custom QScrollArea that intercepts wheel events and applies a smooth animation. """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scroll_animation = QVariantAnimation(self)
        self.scroll_animation.setDuration(250) 
        self.scroll_animation.valueChanged.connect(self.apply_smooth_scroll_step)
        self.target_scroll_value = 0

    def wheelEvent(self, event):
        v_scrollbar = self.verticalScrollBar()
        if v_scrollbar.minimum() == v_scrollbar.maximum():
            super().wheelEvent(event)
            return

        event.accept()
        angle_delta = event.angleDelta().y()
        scroll_increment = int(-angle_delta * 0.5) 
        
        if self.scroll_animation.state() == QVariantAnimation.State.Running:
            start_val = self.target_scroll_value
        else:
            start_val = v_scrollbar.value()

        self.target_scroll_value = max(v_scrollbar.minimum(), min(v_scrollbar.maximum(), start_val + scroll_increment))
        
        self.scroll_animation.stop()
        self.scroll_animation.setStartValue(v_scrollbar.value())
        self.scroll_animation.setEndValue(self.target_scroll_value)
        self.scroll_animation.start()

    def apply_smooth_scroll_step(self, value):
        self.verticalScrollBar().setValue(value)


class SmoothListWidget(QListWidget):
    """ Custom QListWidget subclass that implements smooth wheel scrolling and dynamic balancing margins. """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scroll_animation = QVariantAnimation(self)
        self.scroll_animation.setDuration(250)
        self.scroll_animation.valueChanged.connect(self.apply_smooth_scroll_step)
        self.target_scroll_value = 0
        self.current_left_margin = -1 

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'center_items'):
            self.center_items()

    def showEvent(self, event):
        super().showEvent(event)
        if hasattr(self, 'center_items'):
            self.center_items()

    def center_items(self):
        if self.viewMode() != QListWidget.ViewMode.IconMode:
            return
        grid_size = self.gridSize()
        if grid_size.isEmpty():
            return
        
        available_width = self.width() - 20
        grid_width = grid_size.width()
        if grid_width <= 0:
            return
            
        columns_per_row = available_width // grid_width
        if columns_per_row == 0:
            columns_per_row = 1
            
        total_used_width = columns_per_row * grid_width
        calculated_side_margin = max(0, (available_width - total_used_width) // 2)
        
        if calculated_side_margin != self.current_left_margin:
            self.current_left_margin = calculated_side_margin
            self.setStyleSheet(f"""
                QListWidget {{ 
                    background-color: #121212; 
                    border: 1px solid #333; 
                    border-radius: 6px; 
                    padding-left: {calculated_side_margin}px;
                }}
                QListWidget::item {{ border: 2px solid transparent; border-radius: 6px; }}
                QListWidget::item:selected {{ background-color: #2b78e4; border: 2px solid #004cb3; }}
                QListWidget::item:hover {{ background-color: #222222; }}
            """)

    def wheelEvent(self, event):
        v_scrollbar = self.verticalScrollBar()
        if v_scrollbar.minimum() == v_scrollbar.maximum():
            super().wheelEvent(event)
            return

        event.accept()
        angle_delta = event.angleDelta().y()
        scroll_increment = int(-angle_delta * 0.5) 
        
        if self.scroll_animation.state() == QVariantAnimation.State.Running:
            start_val = self.target_scroll_value
        else:
            start_val = v_scrollbar.value()

        self.target_scroll_value = max(v_scrollbar.minimum(), min(v_scrollbar.maximum(), start_val + scroll_increment))
        
        self.scroll_animation.stop()
        self.scroll_animation.setStartValue(v_scrollbar.value())
        self.scroll_animation.setEndValue(self.target_scroll_value)
        self.scroll_animation.start()

    def apply_smooth_scroll_step(self, value):
        self.verticalScrollBar().setValue(value)


class FocusImageLabel(QLabel):
    """ Custom display viewport widget that handles high-fidelity image scaling dynamically. """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(100, 100)
        self.main_pixmap = QPixmap()
        
    def set_focus_pixmap(self, pixmap):
        self.main_pixmap = pixmap
        self.update_scaled_pixmap()
        
    def update_scaled_pixmap(self):
        if self.main_pixmap.isNull():
            self.clear()
            self.setText("No Image Selected")
            return
            
        sz = self.size()
        if sz.width() <= 0 or sz.height() <= 0:
            return
            
        scaled = self.main_pixmap.scaled(
            sz, 
            Qt.AspectRatioMode.KeepAspectRatio, 
            Qt.TransformationMode.SmoothTransformation
        )
        super().setPixmap(scaled)
        
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_scaled_pixmap()


class ChainRowWidget(QWidget):
    """ Custom workspace row layout context designed to map cascaded tag arrays. """
    def __init__(self, initial_name="NEW TAG CHAIN", initial_tags=None, parent=None):
        super().__init__(parent)
        self.tags_sequence = initial_tags if initial_tags else []
        self.is_selected = False

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setObjectName("ChainRowFrame")
        self.setStyleSheet("""
            QWidget#ChainRowFrame {
                background-color: #1a1a1a;
                border: 2px solid #333333;
                border-radius: 6px;
            }
        """)

        row_layout = QVBoxLayout(self)
        row_layout.setContentsMargins(12, 12, 12, 12)
        row_layout.setSpacing(10)

        self.txt_chain_name = QLineEdit(initial_name)
        self.txt_chain_name.setStyleSheet("""
            QLineEdit {
                background-color: transparent;
                border: none;
                border-bottom: 1px dashed #555;
                font-size: 14px;
                font-weight: bold;
                color: #7fdbff;
                padding: 2px;
            }
            QLineEdit:focus { border-bottom: 1px solid #2b78e4; color: white; }
        """)
        self.txt_chain_name.textChanged.connect(self.dispatch_chain_modification_alert)
        row_layout.addWidget(self.txt_chain_name)

        self.drop_container = QWidget()
        self.drop_container.setAcceptDrops(True)
        self.drop_container.dragEnterEvent = self.handle_inner_drag_enter
        self.drop_container.dropEvent = self.handle_inner_drop_event
        
        self.nodes_hbox = QHBoxLayout(self.drop_container)
        self.nodes_hbox.setContentsMargins(0, 4, 0, 4)
        self.nodes_hbox.setSpacing(8)
        self.nodes_hbox.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        row_layout.addWidget(self.drop_container)
        self.render_chain_nodes_ui()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            main_window = self.window()
            if hasattr(main_window, 'clear_all_chain_row_selections'):
                main_window.clear_all_chain_row_selections()
            
            self.is_selected = True
            self.setStyleSheet("QWidget#ChainRowFrame { background-color: #222a36; border: 2px solid #2b78e4; border-radius: 6px; }")
            self.drag_start_position = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if not hasattr(self, 'drag_start_position'):
            return
        if (event.position().toPoint() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
            return
            
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(f"chain:{id(self)}")
        drag.setMimeData(mime_data)
        
        pixmap = self.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(event.position().toPoint())
        
        drag.exec(Qt.DropAction.MoveAction)

    def handle_inner_drag_enter(self, event):
        if event.mimeData().hasText() and not event.mimeData().text().startswith("chain:"):
            event.acceptProposedAction()

    def handle_inner_drop_event(self, event):
        tag_text = event.mimeData().text().strip()
        if tag_text and tag_text not in self.tags_sequence and not tag_text.startswith("chain:"):
            self.tags_sequence.append(tag_text)
            self.render_chain_nodes_ui()
            self.dispatch_chain_modification_alert()
        event.acceptProposedAction()

    def render_chain_nodes_ui(self):
        print(f"[RENDER] Row tags: {self.tags_sequence}")
        while self.nodes_hbox.count() > 0:
            item = self.nodes_hbox.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        if not self.tags_sequence:
            placeholder = QLabel("Drag tag cards down here to stitch sequences together...")
            placeholder.setStyleSheet("color: #555555; font-style: italic;")
            self.nodes_hbox.addWidget(placeholder)
            return

        for idx, tag in enumerate(self.tags_sequence):
            node_tile = QPushButton(tag)
            node_tile.setStyleSheet("""
                QPushButton {
                    background-color: #262626;
                    border: 1px solid #444;
                    border-radius: 4px;
                    padding: 6px 12px;
                    color: white;
                    font-weight: 500;
                }
                QPushButton:hover { background-color: #a62424; border: 1px solid #821c1c; color: white; }
            """)
            node_tile.setToolTip("Click to prune this tag card out of sequence lines.")
            node_tile.clicked.connect(lambda checked, t=tag: self.remove_tag_from_sequence(t))
            self.nodes_hbox.addWidget(node_tile)

            if idx < len(self.tags_sequence) - 1:
                divider = QLabel("➔")
                divider.setStyleSheet("color: #ffcc00; font-weight: bold; font-size: 14px; padding: 0 2px;")
                self.nodes_hbox.addWidget(divider)

    def remove_tag_from_sequence(self, tag_text):
        if tag_text in self.tags_sequence:
            self.tags_sequence.remove(tag_text)
            self.render_chain_nodes_ui()
            self.dispatch_chain_modification_alert()

    def dispatch_chain_modification_alert(self):
        main_window = self.window()
        if hasattr(main_window, 'commit_chain_workspace_to_config_file'):
            main_window.commit_chain_workspace_to_config_file()


class ChainContainerWidget(QWidget):
    """ Container holding workflow rows. Enables seamless sorting and auto-scrolling transitions. """
    def __init__(self, main_app, parent=None):
        super().__init__(parent)
        self.main_app = main_app
        self.setAcceptDrops(True)
        
        # FIXED: Explicitly force background rendering style hooks to squash white theme fallbacks
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("background-color: #121212;")
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(8, 8, 8, 8)
        self.layout.setSpacing(12)
        self.rows = []
        self.layout.addStretch(1)

    def add_chain_row(self, row_widget):
        self.layout.insertWidget(self.layout.count() - 1, row_widget)
        self.rows.append(row_widget)

    def clear_all_rows(self):
        for row in list(self.rows):
            self.layout.removeWidget(row)
            row.setParent(None)
        self.rows.clear()

    def dragEnterEvent(self, event):
        if event.mimeData().hasText() and event.mimeData().text().startswith("chain:"):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasText() and event.mimeData().text().startswith("chain:"):
            event.acceptProposedAction()
            
            scroll_area = self.main_app.chains_canvas_scroll
            v_scrollbar = scroll_area.verticalScrollBar()
            if v_scrollbar.minimum() == v_scrollbar.maximum():
                return
                
            viewport_pos = self.mapTo(scroll_area.viewport(), event.position().toPoint())
            viewport_height = scroll_area.viewport().height()
            threshold = max(25, int(viewport_height * 0.15))
            current_scroll = v_scrollbar.value()
            
            if viewport_pos.y() < threshold:
                factor = (threshold - viewport_pos.y()) / threshold
                v_scrollbar.setValue(max(v_scrollbar.minimum(), current_scroll - max(1, int(10 * factor))))
            elif viewport_pos.y() > (viewport_height - threshold):
                factor = (viewport_pos.y() - (viewport_height - threshold)) / threshold
                v_scrollbar.setValue(min(v_scrollbar.maximum(), current_scroll + max(1, int(10 * factor))))

    def dropEvent(self, event):
        dragged_text = event.mimeData().text()
        if not dragged_text.startswith("chain:"):
            return
            
        chain_id_str = dragged_text.split(":")[1]
        drop_pos = event.position().toPoint()
        
        src_idx = -1
        for i, row in enumerate(self.rows):
            if str(id(row)) == chain_id_str:
                src_idx = i
                break
        if src_idx == -1:
            return

        dest_idx = len(self.rows)
        for i, row in enumerate(self.rows):
            if i == src_idx: continue
            rect = row.geometry()
            if rect.top() <= drop_pos.y() <= rect.bottom():
                if drop_pos.y() < (rect.y() + rect.height() / 2):
                    dest_idx = i
                else:
                    dest_idx = i + 1
                break
            elif drop_pos.y() < rect.top():
                dest_idx = i
                break

        if src_idx != dest_idx:
            row_widget = self.rows.pop(src_idx)
            if dest_idx > src_idx:
                dest_idx -= 1
            self.rows.insert(dest_idx, row_widget)
            
            for r in self.rows:
                self.layout.removeWidget(r)
            for i, r in enumerate(self.rows):
                self.layout.insertWidget(i, r)
                
            self.layout.invalidate()
            self.main_app.commit_chain_workspace_to_config_file()
            
        event.acceptProposedAction()


class ImageTaggerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Batch Image Tagger (Pro Studio Layout)")
        self.resize(1100, 850)

        self.config_path = Path(__file__).parent.resolve() / "config.json"
        self.config_data = {}
        
        self.current_folder = None
        self.is_syncing = False  

        self.apply_global_dark_theme()
        self.init_ui()
        
        QApplication.instance().installEventFilter(self)
        
        self.load_local_config_file()
        self.restore_application_state()

    def apply_global_dark_theme(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #1c1c1c; }
            QWidget { color: #e0e0e0; font-family: 'Segoe UI', sans-serif; font-size: 13px; }
            QLabel { color: #e0e0e0; }
            QLineEdit { background-color: #2d2d2d; border: 1px solid #444; border-radius: 4px; padding: 4px; color: white; }
            QLineEdit:focus { border: 1px solid #2b78e4; }
            QPushButton { background-color: #3a3a3a; border: 1px solid #555; border-radius: 4px; padding: 6px 12px; color: white; }
            QPushButton:hover { background-color: #4a4a4a; border: 1px solid #666; }
            QPushButton:pressed { background-color: #2d2d2d; }
            QScrollBar:vertical { background: #1c1c1c; width: 12px; margin: 0px; }
            QScrollBar::handle:vertical { background: #444; min-height: 20px; border-radius: 6px; }
            QScrollBar::handle:vertical:hover { background: #555; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { bias: none; }
            QListWidget { background-color: #121212; border: 1px solid #333; border-radius: 6px; }
            
            QPushButton#mode_toggle_btn {
                background-color: #262626;
                border: 1px solid #444;
                border-radius: 13px;
                padding: 4px 14px;
                color: #7fdbff;
                font-weight: bold;
            }
            QPushButton#mode_toggle_btn:checked {
                background-color: #2b78e4;
                border: 1px solid #004cb3;
                color: white;
            }
            
            QPushButton#view_mode_tab_btn {
                background-color: #262626;
                border: 1px solid #444;
                border-radius: 4px;
                padding: 6px 16px;
                color: #aaaaaa;
                font-weight: bold;
            }
            QPushButton#view_mode_tab_btn:checked {
                background-color: #323232;
                border: 1px solid #2b78e4;
                color: white;
            }
            
            QPushButton#nav_arrow_btn {
                background-color: #222222;
                border: 1px solid #333;
                border-radius: 6px;
                font-size: 18px;
                font-weight: bold;
                color: #888;
                min-width: 40px;
                max-width: 40px;
            }
            QPushButton#nav_arrow_btn:hover {
                background-color: #2d2d2d;
                border: 1px solid #2b78e4;
                color: white;
            }
        """)

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        parent_layout = QVBoxLayout(main_widget)

        # --- TOP LEVEL HEADER ROW CONTROLS ---
        top_layout = QHBoxLayout()
        self.btn_select_folder = QPushButton("Select Folder")
        self.btn_select_folder.clicked.connect(self.select_folder_dialog)
        
        self.btn_tab_tagger = QPushButton("Tagger")
        self.btn_tab_tagger.setObjectName("view_mode_tab_btn")
        self.btn_tab_tagger.setCheckable(True)
        self.btn_tab_tagger.setChecked(True)
        self.btn_tab_tagger.clicked.connect(self.switch_to_tagger_screen)
        
        self.btn_tab_chains = QPushButton("Tag Chains")
        self.btn_tab_chains.setObjectName("view_mode_tab_btn")
        self.btn_tab_chains.setCheckable(True)
        self.btn_tab_chains.clicked.connect(self.switch_to_chains_screen)
        
        self.tab_group = QButtonGroup(self)
        self.tab_group.addButton(self.btn_tab_tagger)
        self.tab_group.addButton(self.btn_tab_chains)
        self.tab_group.setExclusive(True)
        
        self.btn_mode_toggle = QPushButton("Mode: Grid View")
        self.btn_mode_toggle.setObjectName("mode_toggle_btn")
        self.btn_mode_toggle.setCheckable(True)
        self.btn_mode_toggle.toggled.connect(self.toggle_workspace_view_mode)

        self.btn_add_chain = QPushButton("Add Chain")
        self.btn_add_chain.setStyleSheet("background-color: #1b8549; color: white; border: 1px solid #156939; font-weight: bold;")
        self.btn_add_chain.clicked.connect(self.add_new_chain_row_container)
        self.btn_add_chain.hide()

        self.btn_remove_chain = QPushButton("Remove Chain")
        self.btn_remove_chain.setStyleSheet("background-color: #a62424; color: white; border: 1px solid #821c1c; font-weight: bold;")
        self.btn_remove_chain.clicked.connect(self.remove_currently_selected_chain_row)
        self.btn_remove_chain.hide()
        
        self.lbl_folder_path = QLabel("No folder selected.")
        self.lbl_folder_path.setStyleSheet("color: #aaaaaa; font-style: italic; padding-left: 5px;")
        
        top_layout.addWidget(self.btn_select_folder)
        top_layout.addWidget(self.btn_tab_tagger)
        top_layout.addWidget(self.btn_tab_chains)
        top_layout.addWidget(self.btn_mode_toggle)
        top_layout.addWidget(self.btn_add_chain)
        top_layout.addWidget(self.btn_remove_chain)
        top_layout.addWidget(self.lbl_folder_path, 1) 
        parent_layout.addLayout(top_layout)

        # --- CENTRAL WORKSPACE PRIMARY STACK ---
        self.main_workspace_stack = QStackedWidget()
        parent_layout.addWidget(self.main_workspace_stack, 1)

        # --- MASTER TAGS CORE WORKSPACE MODULE ---
        self.tags_panel = QWidget()
        tags_layout = QVBoxLayout(self.tags_panel)
        tags_layout.setContentsMargins(0, 5, 0, 0) 

        tags_header = QHBoxLayout()
        tags_header.addWidget(QLabel("<b>Tag Tiles Workspace (Drag freely to reorder priority):</b>"))
        tags_header.addStretch(1) 
        
        tags_header.addWidget(QLabel("Tile Width:"))
        self.tag_width_slider = QSlider(Qt.Orientation.Horizontal)
        self.tag_width_slider.setMinimum(90) 
        self.tag_width_slider.setMaximum(250)
        self.tag_width_slider.setValue(130)  
        self.tag_width_slider.setFixedWidth(110)
        self.tag_width_slider.valueChanged.connect(self.change_tag_width)
        tags_header.addWidget(self.tag_width_slider)
        tags_header.addSpacing(10)
        
        tags_header.addWidget(QLabel("Tile Height:"))
        self.tag_height_slider = QSlider(Qt.Orientation.Horizontal)
        self.tag_height_slider.setMinimum(30) 
        self.tag_height_slider.setMaximum(150)
        self.tag_height_slider.setValue(36)  
        self.tag_height_slider.setFixedWidth(110)
        self.tag_height_slider.valueChanged.connect(self.change_tag_height)
        tags_header.addWidget(self.tag_height_slider)
        tags_layout.addLayout(tags_header)
        
        tag_input_layout = QHBoxLayout()
        self.txt_new_tag = QLineEdit()
        self.txt_new_tag.setPlaceholderText("Create new tag tile...")
        self.btn_add_tag = QPushButton("Add Tag")
        self.btn_add_tag.setStyleSheet("background-color: #1b8549; color: white; font-weight: bold; border: 1px solid #156939;")
        self.btn_add_tag.clicked.connect(self.add_custom_tag)
        self.btn_remove_tag = QPushButton("Remove Tag")
        self.btn_remove_tag.setStyleSheet("background-color: #a62424; color: white; font-weight: bold; border: 1px solid #821c1c;")
        self.btn_remove_tag.clicked.connect(self.remove_selected_tag)
        
        tag_input_layout.addWidget(self.txt_new_tag)
        tag_input_layout.addWidget(self.btn_add_tag)
        tag_input_layout.addWidget(self.btn_remove_tag)
        tags_layout.addLayout(tag_input_layout)

        search_layout = QHBoxLayout()
        self.txt_search_tags = QLineEdit()
        self.txt_search_tags.setPlaceholderText("🔍 Highlight matching tags...")
        self.txt_search_tags.setStyleSheet("QLineEdit { padding: 5px; font-weight: 500; border: 1px solid #333; background-color: #151515; }")
        self.txt_search_tags.textChanged.connect(lambda text: self.tag_list.filter_tags(text))
        search_layout.addWidget(self.txt_search_tags)
        tags_layout.addLayout(search_layout)

        self.tag_scroll_area = SmoothScrollArea()
        self.tag_scroll_area.setWidgetResizable(True)
        self.tag_scroll_area.setStyleSheet("QScrollArea { background-color: #121212; border: 1px solid #333; border-radius: 6px; }")
        
        self.tag_list = TagContainerWidget(self)
        self.tag_scroll_area.setWidget(self.tag_list)
        tags_layout.addWidget(self.tag_scroll_area)

        # SCREEN 1: PRIMARY TAGGER VISUAL GRID
        self.tagger_root_widget = QWidget()
        tagger_root_layout = QVBoxLayout(self.tagger_root_widget)
        tagger_root_layout.setContentsMargins(0, 0, 0, 0)
        
        self.workspace_splitter = QSplitter(Qt.Orientation.Vertical)
        self.workspace_splitter.setStyleSheet("QSplitter::handle { background-color: #333; height: 4px; } QSplitter::handle:hover { background-color: #2b78e4; }")
        tagger_root_layout.addWidget(self.workspace_splitter)
        
        self.main_workspace_stack.addWidget(self.tagger_root_widget)

        # --- SUB PANEL A: IMAGES GRID MODULE ---
        self.images_panel = QWidget()
        images_layout = QVBoxLayout(self.images_panel)
        images_layout.setContentsMargins(0, 0, 0, 0) 

        gallery_header = QHBoxLayout()
        gallery_header.addWidget(QLabel("<b>Images Grid:</b>"))
        gallery_header.addStretch(1) 
        
        gallery_header.addWidget(QLabel("Grid Zoom:"))
        self.size_slider = QSlider(Qt.Orientation.Horizontal)
        self.size_slider.setMinimum(60)
        self.size_slider.setMaximum(500)  
        self.size_slider.setValue(150)    
        self.size_slider.setFixedWidth(140)
        self.size_slider.valueChanged.connect(self.change_thumbnail_size)
        gallery_header.addWidget(self.size_slider)
        images_layout.addLayout(gallery_header)

        self.image_list = SmoothListWidget()
        self.image_list.setViewMode(QListWidget.ViewMode.IconMode)
        self.image_list.setIconSize(QSize(150, 150))
        self.image_list.setGridSize(QSize(160, 160)) 
        self.image_list.setSpacing(6)                 
        self.image_list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.image_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.image_list.setItemAlignment(Qt.AlignmentFlag.AlignCenter)
        images_layout.addWidget(self.image_list)

        # --- SUB PANEL B: IMAGE VIEW VIEWPORT (FOCUS MODE) ---
        self.focus_panel = QWidget()
        focus_layout = QHBoxLayout(self.focus_panel)
        focus_layout.setContentsMargins(0, 0, 0, 0)
        focus_layout.setSpacing(8)
        
        self.btn_prev_image = QPushButton("◀")
        self.btn_prev_image.setObjectName("nav_arrow_btn")
        self.btn_prev_image.clicked.connect(lambda: self.navigate_images(-1))
        
        center_viewport_container = QWidget()
        center_viewport_layout = QVBoxLayout(center_viewport_container)
        center_viewport_layout.setContentsMargins(0, 0, 0, 0)
        center_viewport_layout.setSpacing(6)
        
        self.lbl_focus_counter = QLabel("0 / 0")
        self.lbl_focus_counter.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_focus_counter.setStyleSheet("font-weight: bold; color: #7fdbff; font-size: 14px; padding-bottom: 2px;")
        
        self.lbl_focus_image = FocusImageLabel()
        
        center_viewport_layout.addWidget(self.lbl_focus_counter, 0)
        center_viewport_layout.addWidget(self.lbl_focus_image, 1)
        
        self.btn_next_image = QPushButton("▶")
        self.btn_next_image.setObjectName("nav_arrow_btn")
        self.btn_next_image.clicked.connect(lambda: self.navigate_images(1))
        
        focus_layout.addWidget(self.btn_prev_image)
        focus_layout.addWidget(center_viewport_container, 1)
        focus_layout.addWidget(self.btn_next_image)

        self.image_area_stack = QStackedWidget()
        self.image_area_stack.addWidget(self.images_panel)
        self.image_area_stack.addWidget(self.focus_panel)
        self.workspace_splitter.addWidget(self.image_area_stack)

        self.workspace_splitter.addWidget(self.tags_panel)
        self.workspace_splitter.setSizes([500, 300])

        # SCREEN 2: TAG CHAINS WORKSPACE MANAGER
        self.init_chain_selection_ui_workspace()

        # --- FOOTER BANNER ---
        self.lbl_status_banner = QLabel("✨ Workspace Armed: Hold and drag tag cards to shuffle priorities between other items.")
        self.lbl_status_banner.setStyleSheet("padding: 6px; background-color: #262626; color: #00ffff; font-size: 12px; border-radius: 4px; border: 1px solid #333;")
        self.lbl_status_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        parent_layout.addWidget(self.lbl_status_banner)

        self.image_list.itemSelectionChanged.connect(lambda: self.sync_data_engine(source="image"))

    def init_chain_selection_ui_workspace(self):
        """ Re-architected workflow rows wrapper using a Focus-style Horizontal Splitter. """
        self.chain_root_widget = QWidget()
        chain_hbox_layout = QHBoxLayout(self.chain_root_widget)
        chain_hbox_layout.setContentsMargins(0, 0, 0, 0)

        self.chain_workspace_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.chain_workspace_splitter.setStyleSheet("QSplitter::handle { background-color: #333; width: 4px; } QSplitter::handle:hover { background-color: #2b78e4; }")
        chain_hbox_layout.addWidget(self.chain_workspace_splitter)

        self.chains_canvas_scroll = SmoothScrollArea()
        self.chains_canvas_scroll.setWidgetResizable(True)
        self.chains_canvas_scroll.setStyleSheet("QScrollArea { background-color: #121212; border: none; }")
        
        self.chains_container = ChainContainerWidget(self)
        self.chains_canvas_scroll.setWidget(self.chains_container)
        
        self.chain_workspace_splitter.addWidget(self.chains_canvas_scroll)
        self.main_workspace_stack.addWidget(self.chain_root_widget)

    def switch_to_tagger_screen(self):
        self.main_workspace_stack.setCurrentIndex(0)
        self.btn_add_chain.hide()
        self.btn_remove_chain.hide()
        self.btn_mode_toggle.show()
        
        self.workspace_splitter.addWidget(self.tags_panel)
        self.workspace_splitter.setSizes([500, 300])
        self.image_list.center_items()

    def switch_to_chains_screen(self):
        self.main_workspace_stack.setCurrentIndex(1)
        self.btn_mode_toggle.hide()
        self.btn_add_chain.show()
        self.btn_remove_chain.show()
        
        self.chain_workspace_splitter.addWidget(self.tags_panel)
        self.chain_workspace_splitter.setSizes([650, 450])
        self.rebuild_chain_rows_from_config_file()

    def rebuild_chain_rows_from_config_file(self):
        self.clear_all_chain_row_selections()
        self.chains_container.clear_all_rows()

        saved_chains = self.config_data.get("tag_chains_dict", self.config_data.get("selection_chains_dict", []))
        for chain_data in saved_chains:
            name = chain_data.get("name", "CHAIN NODE MAP")
            tags = chain_data.get("tags", [])
            row_widget = ChainRowWidget(name, tags, self)
            self.chains_container.add_chain_row(row_widget)

    def add_new_chain_row_container(self):
        row_widget = ChainRowWidget("EDITABLE CHAIN NAME", [], self)
        self.chains_container.add_chain_row(row_widget)
        self.commit_chain_workspace_to_config_file()
        self.chains_canvas_scroll.verticalScrollBar().setValue(self.chains_canvas_scroll.verticalScrollBar().maximum())

    def clear_all_chain_row_selections(self):
        for widget in self.chains_container.rows:
            widget.is_selected = False
            widget.setStyleSheet("QWidget#ChainRowFrame { background-color: #1a1a1a; border: 2px solid #333; border-radius: 6px; }")

    def remove_currently_selected_chain_row(self):
        target_widget = None
        for widget in self.chains_container.rows:
            if widget.is_selected:
                target_widget = widget
                break

        if target_widget:
            self.chains_container.layout.removeWidget(target_widget)
            self.chains_container.rows.remove(target_widget)
            target_widget.setParent(None)
            self.commit_chain_workspace_to_config_file()
            self.statusBar().showMessage("🗑️ Chain sequence entry cleared.", 3000)
        else:
            QMessageBox.information(self, "No Selection Detected", "Please click on a chain row box container first to select it for removal.")

    def commit_chain_workspace_to_config_file(self):
        compiled_chains = []
        for widget in self.chains_container.rows:
            compiled_chains.append({
                "name": widget.txt_chain_name.text().strip(),
                "tags": widget.tags_sequence
            })
        self.config_data["tag_chains_dict"] = compiled_chains
        self.save_local_config_file()

    def execute_cascading_chain_implications(self, tags_list, trigger_tag):
        saved_chains = self.config_data.get("tag_chains_dict", self.config_data.get("selection_chains_dict", []))
        processing_queue = [trigger_tag]
        mutated = False
        
        while processing_queue:
            current = processing_queue.pop(0)
            for chain_entry in saved_chains:
                chain = chain_entry.get("tags", [])
                if current in chain:
                    idx = chain.index(current)
                    for trailing_tag in chain[idx+1:]:
                        if trailing_tag not in tags_list:
                            tags_list.append(trailing_tag)
                            processing_queue.append(trailing_tag)
                            mutated = True
        return mutated

    def toggle_workspace_view_mode(self, focus_mode_active):
        if focus_mode_active:
            self.btn_mode_toggle.setText("Mode: Focus View")
            self.workspace_splitter.setOrientation(Qt.Orientation.Horizontal)
            self.image_area_stack.setCurrentIndex(1) 
            
            if self.image_list.currentRow() == -1 and self.image_list.count() > 0:
                self.image_list.setCurrentRow(0)
                
            self.load_focus_image_from_selection()
            self.focus_panel.setFocus() 
            self.sync_focus_mode_tags()
            self.workspace_splitter.setSizes([650, 450])
        else:
            self.btn_mode_toggle.setText("Mode: Grid View")
            self.workspace_splitter.setOrientation(Qt.Orientation.Vertical)
            self.image_area_stack.setCurrentIndex(0) 
            
            self.image_list.blockSignals(True)
            self.image_list.clearSelection()
            self.image_list.blockSignals(False)
            
            self.tag_list.clearSelection()
            self.workspace_splitter.setSizes([500, 300])
            self.image_list.center_items()

    def navigate_images(self, direction):
        if self.image_list.count() == 0:
            return
            
        current_row = self.image_list.currentRow()
        if current_row == -1:
            current_row = 0
            
        next_row = current_row + direction
        if 0 <= next_row < self.image_list.count():
            self.image_list.clearSelection()
            self.image_list.setCurrentRow(next_row)

    def load_focus_image_from_selection(self):
        if not self.current_folder:
            self.lbl_focus_image.set_focus_pixmap(QPixmap())
            self.lbl_focus_counter.setText("0 / 0")
            return
            
        total_images = self.image_list.count()
        current_item = self.image_list.currentItem()
        
        if current_item:
            current_row = self.image_list.currentRow()
            X = current_row + 1 if current_row != -1 else 0
            self.lbl_focus_counter.setText(f"{X} / {total_images}")
            
            img_name = current_item.data(Qt.ItemDataRole.UserRole)
            file_path = self.current_folder / img_name
            if file_path.exists():
                reader = QImageReader(str(file_path))
                reader.setAutoTransform(True)
                pixmap = QPixmap.fromImageReader(reader)
                self.lbl_focus_image.set_focus_pixmap(pixmap)
                return
                
        self.lbl_focus_image.set_focus_pixmap(QPixmap())
        self.lbl_focus_counter.setText(f"0 / {total_images}")

    def sync_focus_mode_tags(self):
        if not self.current_folder:
            return
        current_item = self.image_list.currentItem()
        if not current_item:
            return
            
        img_name = current_item.data(Qt.ItemDataRole.UserRole)
        txt_path = self.current_folder / Path(img_name).with_suffix('.txt')
        
        current_tags = []
        if txt_path.exists():
            try:
                with open(txt_path, "r", encoding="utf-8") as f:
                    current_tags = [t.strip() for t in f.read().split(",") if t.strip()]
            except Exception:
                pass
                
        current_search = self.txt_search_tags.text()
        for tile in self.tag_list.tiles:
            tile.is_selected = (tile.tag_text in current_tags)
            tile.update_styles(current_search)

    def toggle_tag_for_current_focus_image(self, tag_text, is_attached):
        if not self.current_folder:
            return
        current_item = self.image_list.currentItem()
        if not current_item:
            return
            
        img_name = current_item.data(Qt.ItemDataRole.UserRole)
        txt_path = self.current_folder / Path(img_name).with_suffix('.txt')
        
        current_tags = []
        if txt_path.exists():
            try:
                with open(txt_path, "r", encoding="utf-8") as f:
                    current_tags = [t.strip() for t in f.read().split(",") if t.strip()]
            except Exception:
                pass
                
        if is_attached:
            if tag_text not in current_tags:
                current_tags.append(tag_text)
                self.execute_cascading_chain_implications(current_tags, tag_text)
        else:
            if tag_text in current_tags:
                current_tags.remove(tag_text)
                
        self.is_syncing = True
        self.save_ordered_tags_to_file(txt_path, current_tags)
        self.calculate_current_folder_counts()
        self.is_syncing = False
        self.sync_focus_mode_tags() 

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.KeyPress:
            if self.btn_mode_toggle.isChecked() and self.main_workspace_stack.currentIndex() == 0:
                focused_widget = QApplication.focusWidget()
                if not isinstance(focused_widget, QLineEdit):
                    if event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Up):
                        self.navigate_images(-1)
                        return True 
                    elif event.key() in (Qt.Key.Key_Right, Qt.Key.Key_Down):
                        self.navigate_images(1)
                        return True 
        return super().eventFilter(obj, event)

    def load_local_config_file(self):
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self.config_data = json.load(f)
            except Exception:
                self.config_data = {}

    def save_local_config_file(self):
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config_data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving workspace state file: {e}")

    def change_thumbnail_size(self, value):
        self.image_list.setIconSize(QSize(value, value))
        self.image_list.setGridSize(QSize(value + 10, value + 10))
        self.image_list.center_items() 

    def change_tag_width(self, value):
        self.tag_list.current_width_setting = value
        self.tag_list.recalculate_tile_sizes()

    def change_tag_height(self, value):
        self.tag_list.current_height_setting = value
        self.tag_list.recalculate_tile_sizes()

    def restore_application_state(self):
        self.image_list.blockSignals(True)

        saved_tags = self.config_data.get("tag_library_list", None)
        if saved_tags is not None:
            for tag in saved_tags:
                self.tag_list.add_tag_tile(tag, 0) 

        saved_zoom = self.config_data.get("grid_zoom_value", 150)
        self.size_slider.setValue(saved_zoom)
        self.change_thumbnail_size(saved_zoom)

        saved_tile_width = self.config_data.get("tag_tile_width", 130)
        self.tag_width_slider.setValue(saved_tile_width)
        self.tag_list.current_width_setting = saved_tile_width
        
        saved_tile_height = self.config_data.get("tag_tile_height", 36)
        self.tag_height_slider.setValue(saved_tile_height)
        self.tag_list.current_height_setting = saved_tile_height
        
        self.image_list.blockSignals(False)

        saved_path = self.config_data.get("last_folder", "")
        if saved_path:
            folder_path = Path(saved_path)
            if folder_path.exists() and folder_path.is_dir():
                self.load_folder(folder_path)
        else:
            self.tag_list.recalculate_tile_sizes()

    def closeEvent(self, event):
        self.config_data["grid_zoom_value"] = self.size_slider.value()
        self.config_data["tag_tile_width"] = self.tag_width_slider.value()
        self.config_data["tag_tile_height"] = self.tag_height_slider.value()
        self.config_data["tag_library_list"] = [tile.tag_text for tile in self.tag_list.tiles]
        self.save_local_config_file()
        super().closeEvent(event)

    def select_folder_dialog(self):
        start_dir = str(self.current_folder) if self.current_folder else ""
        folder = QFileDialog.getExistingDirectory(self, "Select Image Folder", start_dir)
        if folder:
            self.config_data["last_folder"] = folder
            self.save_local_config_file()
            self.load_folder(Path(folder))

    def load_folder(self, folder_path):
        self.image_list.blockSignals(True)
        self.is_syncing = True 

        self.current_folder = folder_path
        self.lbl_folder_path.setText(str(self.current_folder))
        self.image_list.clear()

        valid_extensions = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
        for file_path in self.current_folder.iterdir():
            if file_path.suffix.lower() in valid_extensions:
                item = QListWidgetItem() 
                item.setData(Qt.ItemDataRole.UserRole, file_path.name)
                
                reader = QImageReader(str(file_path))
                reader.setAutoTransform(True) 
                img_size = reader.size()
                
                if not img_size.isEmpty():
                    img_size.scale(500, 500, Qt.AspectRatioMode.KeepAspectRatio)
                    reader.setScaledSize(img_size)
                    loaded_img = reader.read()
                    
                    if not loaded_img.isNull():
                        item.setIcon(QIcon(QPixmap.fromImage(loaded_img)))
                
                self.image_list.addItem(item)
                
        disovered_tags = set()
        for txt_path in self.current_folder.glob("*.txt"):
            try:
                with open(txt_path, "r", encoding="utf-8") as f:
                    tags = [t.strip() for t in f.read().split(",") if t.strip()]
                    disovered_tags.update(tags)
            except Exception:
                pass 

        existing_tags = [tile.tag_text for tile in self.tag_list.tiles]
        for new_tag in disovered_tags:
            if new_tag not in existing_tags:
                self.tag_list.add_tag_tile(new_tag, 0)
        
        self.is_syncing = False 
        self.image_list.blockSignals(False)
        self.image_list.clearSelection()
        
        self.calculate_current_folder_counts() 
        self.change_tag_width(self.tag_width_slider.value())
        self.image_list.center_items() 
        self.load_focus_image_from_selection()
        self.sync_focus_mode_tags()
        self.statusBar().showMessage(f"Loaded {self.image_list.count()} images.", 4000)

    def calculate_current_folder_counts(self):
        if self.current_folder is None: return

        tag_counts = {}
        for txt_path in self.current_folder.glob("*.txt"):
            try:
                with open(txt_path, "r", encoding="utf-8") as f:
                    tags = [t.strip() for t in f.read().split(",") if t.strip()]
                    for tag in tags:
                        tag_counts[tag] = tag_counts.get(tag, 0) + 1
            except Exception:
                pass 

        for tile in self.tag_list.tiles:
            count = tag_counts.get(tile.tag_text, 0)
            tile.update_count(count)

    def handle_tags_rearranged(self):
        if self.is_syncing or not self.current_folder:
            return
        
        self.is_syncing = True
        for txt_path in self.current_folder.glob("*.txt"):
            try:
                with open(txt_path, "r", encoding="utf-8") as f:
                    current_tags = [t.strip() for t in f.read().split(",") if t.strip()]
                if current_tags:
                    self.save_ordered_tags_to_file(txt_path, current_tags)
            except Exception:
                pass
                
        self.is_syncing = False
        self.tag_list.recalculate_tile_sizes()
        self.statusBar().showMessage("🔄 Folder Re-indexed.", 2000)

    def add_custom_tag(self):
        tag_text = self.txt_new_tag.text().strip()
        if tag_text:
            existing_items = [tile.tag_text for tile in self.tag_list.tiles]
            if tag_text not in existing_items:
                self.tag_list.add_tag_tile(tag_text, 0)
                self.tag_list.recalculate_tile_sizes()
            self.txt_new_tag.clear()
            self.calculate_current_folder_counts()

    def remove_selected_tag(self):
        self.tag_list.remove_selected_tags()

    def save_ordered_tags_to_file(self, txt_path, tags_list):
        ordered_tags = [tile.tag_text for tile in self.tag_list.tiles]
        tag_order_map = {tag: index for index, tag in enumerate(ordered_tags)}
        
        tags_list.sort(key=lambda t: tag_order_map.get(t, 9999))
        seen = set()
        clean_tags = [x for x in tags_list if not (x in seen or seen.add(x))]
        
        try:
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(", ".join(clean_tags))
        except Exception as e:
            print(f"Error compiling output file {txt_path}: {e}")

    def sync_data_engine(self, source=""):
        if self.is_syncing or not self.current_folder:
            return

        if self.main_workspace_stack.currentIndex() == 1:
            return

        if self.btn_mode_toggle.isChecked() and self.main_workspace_stack.currentIndex() == 0:
            if source == "image":
                self.is_syncing = True
                self.load_focus_image_from_selection()
                self.sync_focus_mode_tags()
                self.is_syncing = False
            return

        selected_tag_items = self.tag_list.selectedItems()
        active_tag = selected_tag_items[0].tag_text if selected_tag_items else None

        if source == "tag":
            self.is_syncing = True
            self.image_list.clearSelection()
            
            if active_tag:
                for i in range(self.image_list.count()):
                    item = self.image_list.item(i)
                    img_name = item.data(Qt.ItemDataRole.UserRole)
                    txt_path = self.current_folder / Path(img_name).with_suffix('.txt')
                    
                    if txt_path.exists():
                        try:
                            with open(txt_path, "r", encoding="utf-8") as f:
                                current_tags = [t.strip() for t in f.read().split(",") if t.strip()]
                            if active_tag in current_tags:
                                item.setSelected(True)
                        except Exception:
                            pass
            self.is_syncing = False

        elif source == "image":
            if not active_tag:
                return
            
            self.is_syncing = True
            for i in range(self.image_list.count()):
                item = self.image_list.item(i)
                img_name = item.data(Qt.ItemDataRole.UserRole)
                txt_path = self.current_folder / Path(img_name).with_suffix('.txt')
                
                current_tags = []
                if txt_path.exists():
                    try:
                        with open(txt_path, "r", encoding="utf-8") as f:
                            current_tags = [t.strip() for t in f.read().split(",") if t.strip()]
                    except Exception:
                        pass

                is_selected_in_ui = item.isSelected()
                file_changed = False

                if is_selected_in_ui and (active_tag not in current_tags):
                    current_tags.append(active_tag)
                    self.execute_cascading_chain_implications(current_tags, active_tag)
                    file_changed = True
                elif not is_selected_in_ui and (active_tag in current_tags):
                    current_tags.remove(active_tag)
                    file_changed = True

                if file_changed:
                    self.save_ordered_tags_to_file(txt_path, current_tags)

            self.is_syncing = False 
            self.calculate_current_folder_counts() 


def global_crash_exception_hook(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
        
    formatted_log = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    print(formatted_log, file=sys.stderr) 
    
    try:
        now = datetime.now()
        filename_time = now.strftime("%Y-%m-%d_%H-%M-%S")
        header_time = now.strftime("%Y-%m-%d %H:%M:%S")
        
        log_path = Path(__file__).parent.resolve() / f"crash_{filename_time}.log"
        with open(log_path, "w", encoding="utf-8") as f:
            f.write("=========================================\n")
            f.write(f"        APPLICATION CRASH LOG REPORT     \n")
            f.write(f"        Timestamp: {header_time}         \n")
            f.write("=========================================\n\n")
            f.write(formatted_log)
    except Exception as log_err:
        print(f"Could not save crash dump report file: {log_err}", file=sys.stderr)
    
    error_dialog = QMessageBox()
    error_dialog.setIcon(QMessageBox.Icon.Critical)
    error_dialog.setWindowTitle("Workspace Crash Intercepted")
    error_dialog.setText("<b>The application encountered an internal system error:</b>")
    error_dialog.setInformativeText(str(exc_value))
    error_dialog.setDetailedText(formatted_log)
    error_dialog.exec()

sys.excepthook = global_crash_exception_hook

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ImageTaggerApp()
    window.show()
    sys.exit(app.exec())