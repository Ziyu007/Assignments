# notes_organizer.py
import os
import json
from datetime import datetime, timezone

from styles.notes_organizer_styles import get_notes_organizer_styles
from database import db_manager as db

from PyQt5.QtCore import Qt, QPoint, QRect, QTimer, QSize, pyqtSignal
from PyQt5.QtGui import (
    QPixmap, QPainter, QImage, QPen, QColor, QFont, QPainterPath, QCursor,
    QTransform, QIcon, QTextListFormat, QTextCharFormat, QBrush
)
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit, QMessageBox,
    QTabWidget, QFileDialog, QToolButton, QMenu, QPushButton,
    QFrame, QComboBox, QColorDialog, QAction, QActionGroup,
    QDialog, QDialogButtonBox
)

APP_ROOT  = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MEDIA_DIR = os.path.join(APP_ROOT, "notes_media")

# locate assets
ASSET_DIR_CANDIDATES = ["Photo", "assets", "icons", "images"]
def _find_asset(*names) -> str:
    for base in ASSET_DIR_CANDIDATES:
        for n in names:
            p = os.path.join(APP_ROOT, base, n)
            if os.path.exists(p):
                return p
    return ""

def PHOTO(name):
    """Return the first asset path that matches name (best-effort)."""
    return _find_asset(name)

# ======================= Image crop dialog =======================
class _CropCanvas(QWidget):
    """Canvas that lets the user drag/resize a crop box over an image."""
    HANDLE = 10
    def __init__(self, pm: QPixmap, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self._pm = pm
        self._target = QRect()
        self._sel = QRect()
        self._drag_mode = None
        self._drag_start = QPoint()
        self._sel_start = QRect()

    def sizeHint(self):
        w = min(900, max(520, self._pm.width()))
        h = min(700, max(360, self._pm.height()))
        return QSize(w, h)

    def _fit_rect(self) -> QRect:
        """Fit the image into the widget, keeping aspect ratio."""
        if self.width() <= 2 or self.height() <= 2 or self._pm.isNull():
            return QRect(0, 0, 0, 0)
        pw, ph = self._pm.width(), self._pm.height()
        vw, vh = self.width()-20, self.height()-20
        scale = min(vw / pw, vh / ph)
        tw, th = int(pw*scale), int(ph*scale)
        x = (self.width() - tw)//2
        y = (self.height() - th)//2
        return QRect(x, y, tw, th)

    def _init_sel_if_needed(self):
        """Create a default selection box when the view first shows."""
        if self._sel.isNull() and not self._target.isNull():
            w = int(self._target.width() * 0.7)
            h = int(self._target.height() * 0.7)
            x = self._target.x() + (self._target.width() - w)//2
            y = self._target.y() + (self._target.height() - h)//2
            self._sel = QRect(x, y, w, h)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._target = self._fit_rect()
        self._init_sel_if_needed()
        if not self._sel.isNull():
            self._sel = self._sel.intersected(self._target)

    def _handle_rects(self):
        """Return rects for the four resize handles."""
        h = self.HANDLE
        r = self._sel
        return {
            "nw": QRect(r.left()-h//2,  r.top()-h//2,     h, h),
            "ne": QRect(r.right()-h//2, r.top()-h//2,     h, h),
            "sw": QRect(r.left()-h//2,  r.bottom()-h//2,  h, h),
            "se": QRect(r.right()-h//2, r.bottom()-h//2,  h, h),
        }

    def _cursor_for_pos(self, pos: QPoint):
        """Return the right cursor for a given mouse position."""
        if self._sel.isNull():
            return Qt.ArrowCursor
        for k, rc in self._handle_rects().items():
            if rc.contains(pos):
                return Qt.SizeFDiagCursor if k in ("nw","se") else Qt.SizeBDiagCursor
        return Qt.SizeAllCursor if self._sel.contains(pos) else Qt.ArrowCursor

    def mouseMoveEvent(self, e):
        """Resize or move the selection while dragging."""
        if self._drag_mode:
            delta = e.pos() - self._drag_start
            new = QRect(self._sel_start)
            if self._drag_mode == "move":
                new.translate(delta)
                if new.left() < self._target.left():   new.moveLeft(self._target.left())
                if new.top()  < self._target.top():    new.moveTop(self._target.top())
                if new.right() > self._target.right(): new.moveRight(self._target.right())
                if new.bottom()> self._target.bottom():new.moveBottom(self._target.bottom())
            else:
                if "n" in self._drag_mode:
                    new.setTop(min(self._sel_start.bottom()-10, self._sel_start.top() + delta.y()))
                    if new.top() < self._target.top(): new.setTop(self._target.top())
                if "s" in self._drag_mode:
                    new.setBottom(max(self._sel_start.top()+10, self._sel_start.bottom() + delta.y()))
                    if new.bottom() > self._target.bottom(): new.setBottom(self._target.bottom())
                if "w" in self._drag_mode:
                    new.setLeft(min(self._sel_start.right()-10, self._sel_start.left() + delta.x()))
                    if new.left() < self._target.left(): new.setLeft(self._target.left())
                if "e" in self._drag_mode:
                    new.setRight(max(self._sel_start.left()+10, self._sel_start.right() + delta.x()))
                    if new.right() > self._target.right(): new.setRight(self._target.right())
            self._sel = new
            self.update()
        else:
            self.setCursor(self._cursor_for_pos(e.pos()))
        super().mouseMoveEvent(e)

    def mousePressEvent(self, e):
        """Start dragging: pick handle, move, or select."""
        if e.button() == Qt.LeftButton and self._target.contains(e.pos()):
            hrs = self._handle_rects()
            for k, rc in hrs.items():
                if rc.contains(e.pos()):
                    self._drag_mode = k
                    self._drag_start = e.pos()
                    self._sel_start = QRect(self._sel)
                    break
            else:
                if self._sel.contains(e.pos()):
                    self._drag_mode = "move"
                    self._drag_start = e.pos()
                    self._sel_start = QRect(self._sel)
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        """Stop dragging."""
        if e.button() == Qt.LeftButton:
            self._drag_mode = None
        super().mouseReleaseEvent(e)

    def paintEvent(self, e):
        """Draw image, dim overlays, selection, and handles. Selection interior stays transparent."""
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform)

        if not self._pm.isNull() and not self._target.isNull():
            p.drawPixmap(self._target, self._pm)

        # Dim outside the fitted image
        dim = QColor(0, 0, 0, 170)
        p.setPen(Qt.NoPen)
        p.setBrush(dim)
        p.drawRect(0, 0, self.width(), max(0, self._target.top()))
        p.drawRect(0, self._target.bottom()+1, self.width(),
                   max(0, self.height() - (self._target.bottom()+1)))
        p.drawRect(0, self._target.top(), max(0, self._target.left()), self._target.height())
        p.drawRect(self._target.right()+1, self._target.top(),
                   max(0, self.width() - (self._target.right()+1)), self._target.height())

        # Dim inside the fitted image but outside the selection
        if not self._sel.isNull():
            p.drawRect(self._target.left(), self._target.top(),
                       self._target.width(), max(0, self._sel.top() - self._target.top()))
            p.drawRect(self._target.left(), self._sel.bottom()+1,
                       self._target.width(), max(0, self._target.bottom() - (self._sel.bottom())))
            p.drawRect(self._target.left(), self._sel.top(),
                       max(0, self._sel.left() - self._target.left()), self._sel.height())
            p.drawRect(self._sel.right()+1, self._sel.top(),
                       max(0, self._target.right() - self._sel.right()), self._sel.height())

            # Selection border & handles (interior transparent)
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(QColor("#ffffff"), 2))
            p.drawRect(self._sel.adjusted(0, 0, -1, -1))

            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#ffffff"))
            for rc in self._handle_rects().values():
                p.drawRect(rc)

        # Subtle border around the fitted target
        if not self._target.isNull():
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(QColor(255,255,255,80), 1))
            p.drawRect(self._target.adjusted(0, 0, -1, -1))

        p.end()

    def crop_pixmap(self) -> QPixmap:
        """Return the cropped pixmap (or original if selection is invalid)."""
        if self._pm.isNull() or self._sel.isNull() or self._sel.width() < 2 or self._sel.height() < 2:
            return self._pm.copy()
        sx = max(0, self._sel.x() - self._target.x())
        sy = max(0, self._sel.y() - self._target.y())
        scale_x = self._pm.width()  / self._target.width()
        scale_y = self._pm.height() / self._target.height()
        ix = int(sx * scale_x)
        iy = int(sy * scale_y)
        iw = int(self._sel.width()  * scale_x)
        ih = int(self._sel.height() * scale_y)
        rect = QRect(ix, iy, iw, ih).intersected(QRect(0, 0, self._pm.width(), self._pm.height()))
        if rect.width() <= 0 or rect.height() <= 0:
            return self._pm.copy()
        return self._pm.copy(rect)

class CropDialog(QDialog):
    """Modal dialog that hosts the crop canvas and returns the result."""
    def __init__(self, pm: QPixmap, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Crop Image")
        self.setModal(True)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self.canvas = _CropCanvas(pm, self)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        instr = QLabel("Adjust the crop frame, then press OK.")
        f = instr.font(); f.setBold(True); instr.setFont(f)
        lay.addWidget(instr)
        lay.addWidget(self.canvas, 1)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

        self._out = None

    def accept(self):
        self._out = self.canvas.crop_pixmap()
        super().accept()

    def result_pixmap(self) -> QPixmap:
        return self._out if isinstance(self._out, QPixmap) else QPixmap()

# ======================= Drawing / overlay =======================
class Stroke:
    """A freehand stroke with color, width and alpha."""
    __slots__ = ("points", "color", "width", "alpha", "mode")
    def __init__(self, points, color, width, alpha=255, mode="pen"):
        self.points = points
        self.color  = QColor(color)
        self.width  = int(width)
        self.alpha  = int(alpha)
        self.mode   = mode
    def paint(self, painter: QPainter, y_offset: int):
        """Draw the stroke on the painter (y_offset adjusts for scroll)."""
        if len(self.points) < 2: return
        pen = QPen(self.color)
        c = QColor(self.color); c.setAlpha(self.alpha)
        pen.setColor(c); pen.setWidth(self.width)
        pen.setCapStyle(Qt.RoundCap); pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)
        path = QPainterPath(QPoint(self.points[0].x(), self.points[0].y() - y_offset))
        for pt in self.points[1:]:
            path.lineTo(pt.x(), pt.y() - y_offset)
        painter.drawPath(path)

class InkTextEdit(QTextEdit):
    """
    Rich text editor with extra layers:
    - Freehand strokes (pencil, pen, marker) + eraser (normal/lasso)
    - Floating images with crop, resize, move, and delete
    - Undo/redo for strokes and image adds
    Emits:
      overlayChanged -> whenever overlay content changes (images/strokes/eraser/etc.)
    """
    selectionChangedForImage = pyqtSignal(bool)
    imageCountChanged        = pyqtSignal(int)
    overlayChanged           = pyqtSignal()      

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptRichText(True)
        self.setMinimumHeight(360)
        self.setObjectName("notesEditor")

        # drawing state
        self.tool        = None
        self.eraser_mode = "normal"
        self.colors      = {"pencil": QColor("#555555"),
                            "pen":    QColor("#000000"),
                            "marker": QColor("#ffeb3b")}
        self.widths      = {"pencil": 2, "pen": 4, "marker": 14, "eraser": 20}
        self.alphas      = {"pencil": 255, "pen": 255, "marker": 110}

        self.strokes      = []
        self._current_pts = []
        self.undo_stack   = []
        self.redo_stack   = []

        # images
        self.images         = []
        self.selected_idx   = None
        self._drag_offset   = QPoint(0, 0)
        self._resizing      = False
        self._resize_from   = None
        self._start_scale   = None

        # image UI hit areas
        self._press_pos_view = None
        self._crop_btn_rect      = None
        self._resize_handle_rect = None
        self._btn_delete_rect    = None

        # cursors
        self._cursor_pixmaps = {}
        self._cursor_base    = 28
        self._apply_tool_cursor()

        self.viewport().setMouseTracking(True)

    # ---- coordinates
    def _vy(self): return self.verticalScrollBar().value()
    def _to_doc(self, p: QPoint)  -> QPoint: return QPoint(p.x(), p.y() + self._vy())
    def _to_view(self, p: QPoint) -> QPoint: return QPoint(p.x(), p.y() - self._vy())

    # ---- cursors
    def set_tool_pixmaps(self, mapping: dict, base_size: int = 28):
        """Set custom cursors for drawing tools."""
        self._cursor_pixmaps = {}
        for k, path in mapping.items():
            pm = QPixmap(path) if path else QPixmap()
            if not pm.isNull():
                self._cursor_pixmaps[k] = pm
        self._cursor_base = int(base_size)
        self._apply_tool_cursor()

    def _apply_tool_cursor(self):
        """Apply the cursor that matches the current tool."""
        cur = QCursor(Qt.IBeamCursor)
        if self.tool in ("pencil", "pen", "marker", "eraser"):
            pm = self._cursor_pixmaps.get(self.tool)
            if pm and not pm.isNull():
                sz = max(8, int(round(self._cursor_base)))
                try: dpr = float(pm.devicePixelRatioF())
                except Exception:
                    try: dpr = float(pm.devicePixelRatio())
                    except Exception: dpr = 1.0
                w = max(1, int(sz * dpr)); h = max(1, int(sz * dpr))
                base = pm.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                base.setDevicePixelRatio(dpr)
                cur = QCursor(base)
            elif self.tool == "eraser":
                cur = QCursor(Qt.CrossCursor)
        self.viewport().setCursor(cur)

    def _update_hover_cursor(self, view_pos: QPoint):
        """Update cursor when hovering over images or handles."""
        if self.tool in ("pencil","pen","marker","eraser"):
            self._apply_tool_cursor(); return
        hit = self._hit_image(view_pos)
        if hit == "handle_resize":
            self.viewport().setCursor(Qt.SizeFDiagCursor)
        elif isinstance(hit, int):
            self.viewport().setCursor(Qt.OpenHandCursor)
        else:
            self.viewport().setCursor(Qt.IBeamCursor)

    def enterEvent(self, e):
        self._update_hover_cursor(self.mapFromGlobal(QCursor.pos()))
        super().enterEvent(e)

    def leaveEvent(self, e):
        self.viewport().unsetCursor()
        super().leaveEvent(e)

    def set_mode(self, mode: str):
        """Switch to a drawing/eraser tool."""
        self.tool = mode
        self._apply_tool_cursor()

    def clear_mode_to_text(self):
        """Return to text-edit mode."""
        self.tool = None
        self._apply_tool_cursor()

    def set_tool_size(self, mode: str, width: int):
        """Change brush size for a tool."""
        if mode in self.widths:
            self.widths[mode] = max(1, int(width))

    def set_eraser_mode(self, mode: str):
        """Set eraser to normal or lasso mode."""
        self.eraser_mode = "lasso" if str(mode).lower().startswith("l") else "normal"
        self._apply_tool_cursor()

    # ---- images
    def _compose_pm(self, im: dict):
        """Rebuild the pixmap when scale or angle changes."""
        src   = im["source"]
        scale = im.get("scale", 1.0)
        angle = im.get("angle", 0.0)
        if src.isNull(): im["pm"] = QPixmap(); return
        new_w = max(1, int(round(src.width()  * scale)))
        new_h = max(1, int(round(src.height() * scale)))
        scaled = src.scaled(new_w, new_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        if angle % 360 != 0:
            t = QTransform(); t.rotate(angle)
            scaled = scaled.transformed(t, Qt.SmoothTransformation)
        im["pm"] = scaled

    def insert_image(self, path: str):
        """Insert an image near the current viewport."""
        pm = QPixmap(path)
        if pm.isNull():
            QMessageBox.warning(self, "Image", "Failed to load image."); return
        pos_doc = QPoint(40, self._vy() + 40)
        im = {"orig": pm.copy(),"source": pm.copy(),"pm": pm.copy(),
              "pos": pos_doc,"opacity": 1.0,"angle": 0.0,"scale": 1.0}
        self.images.append(im)
        self.undo_stack.append(("add_image", len(self.images)-1))
        self.redo_stack.clear()
        self.selected_idx = len(self.images)-1
        self.imageCountChanged.emit(len(self.images))
        self.selectionChangedForImage.emit(True)
        self.viewport().update()
        self.overlayChanged.emit()  

    # ---- undo/redo
    def undo(self):
        """Undo last stroke/image add/erase."""
        changed = False
        if self.undo_stack:
            kind, payload = self.undo_stack.pop()
            if kind == "stroke" and self.strokes:
                self.redo_stack.append(("stroke", self.strokes.pop()))
                changed = True
            elif kind == "add_image" and self.images:
                self.redo_stack.append(("add_image", self.images.pop()))
                self.imageCountChanged.emit(len(self.images))
                changed = True
            elif kind == "erase":
                self.redo_stack.append(("erase", self.strokes[:]))
                self.strokes = payload
                changed = True
        self.viewport().update()
        if changed:
            self.overlayChanged.emit()  

    def redo(self):
        """Redo last undone action."""
        if not self.redo_stack: return
        kind, payload = self.redo_stack.pop()
        changed = False
        if kind == "stroke":
            self.strokes.append(payload); self.undo_stack.append(("stroke", None)); changed = True
        elif kind == "add_image":
            self.images.append(payload);  self.undo_stack.append(("add_image", len(self.images)-1))
            self.imageCountChanged.emit(len(self.images)); changed = True
        elif kind == "erase":
            self.undo_stack.append(("erase", self.strokes[:]))
            self.strokes = payload; changed = True
        self.viewport().update()
        if changed:
            self.overlayChanged.emit()  

    # ---- eraser helpers
    def _near_any(self, pt: QPoint, pts, radius: int) -> bool:
        r2 = radius * radius; x, y = pt.x(), pt.y()
        for p in pts:
            dx, dy = p.x()-x, p.y()-y
            if dx*dx + dy*dy <= r2: return True
        return False

    def _erase_with_radius(self, stroke, eraser_pts, radius):
        """Return stroke segments after erasing around given points."""
        segs, cur = [], []
        for p in stroke.points:
            if self._near_any(p, eraser_pts, radius):
                if len(cur) >= 2:
                    segs.append(Stroke(cur, stroke.color, stroke.width, stroke.alpha, stroke.mode))
                cur = []
            else:
                cur.append(p)
        if len(cur) >= 2:
            segs.append(Stroke(cur, stroke.color, stroke.width, stroke.alpha, stroke.mode))
        return segs

    def _point_in_poly(self, p: QPoint, poly: list) -> bool:
        """Point-in-polygon test for lasso eraser."""
        x, y = p.x(), p.y()
        inside = False
        n = len(poly)
        for i in range(n):
            x1, y1 = poly[i].x(), poly[i].y()
            x2, y2 = poly[(i+1) % n].x(), poly[(i+1) % n].y()
            if ((y1 > y) != (y2 > y)) and (x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-9) + x1):
                inside = not inside
        return inside

    # ---- events
    def mousePressEvent(self, e):
        """Begin draw/erase, or select/drag/resize image, or click crop/delete."""
        if e.button() == Qt.LeftButton:
            hit = self._hit_image(e.pos())
            if hit == "btn_crop":
                self._start_crop_selected(); return
            if hit == "btn_delete":
                self._confirm_delete_selected_image(); return
            if hit == "handle_resize" and self.selected_idx is not None:
                self._resizing    = True
                self._resize_from = e.pos()
                self._start_scale = self.images[self.selected_idx]["scale"]
                self.viewport().setCursor(Qt.SizeFDiagCursor); return
            if isinstance(hit, int):
                self.clear_mode_to_text()
                self.selected_idx = hit
                im = self.images[self.selected_idx]
                self._drag_offset = self._to_doc(e.pos()) - im["pos"]
                self.selectionChangedForImage.emit(True)
                self.viewport().setCursor(Qt.ClosedHandCursor)
                self.viewport().update(); return

            if self.selected_idx is not None:
                self.selected_idx = None
                self.selectionChangedForImage.emit(False)
                self.viewport().update()

            if self.tool in ("pencil", "pen", "marker", "eraser"):
                self._current_pts = [self._to_doc(e.pos())]
                self._press_pos_view = e.pos()
                self.redo_stack.clear()
                return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        """Drag image, resize image, or draw/erase while moving."""
        if not (e.buttons() & Qt.LeftButton):
            self._update_hover_cursor(e.pos())

        if self._resizing and self.selected_idx is not None and (e.buttons() & Qt.LeftButton):
            im    = self.images[self.selected_idx]
            delta = e.pos() - self._resize_from
            factor = max(0.1, 1.0 + (delta.x() + delta.y()) / 240.0)
            im["scale"] = max(0.1, min(8.0, self._start_scale * factor))
            self._compose_pm(im)
            self.viewport().update(); return

        if self.selected_idx is not None and (e.buttons() & Qt.LeftButton):
            im = self.images[self.selected_idx]
            im["pos"] = self._to_doc(e.pos()) - self._drag_offset
            self.viewport().update(); return

        if self._current_pts and (e.buttons() & Qt.LeftButton):
            self._current_pts.append(self._to_doc(e.pos()))
            self.viewport().update(); return

        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        """Finish current draw/erase/drag/resize action."""
        if e.button() == Qt.LeftButton:
            if self.tool in ("pencil", "pen", "marker", "eraser"):
                if self._press_pos_view is not None:
                    if (e.pos() - self._press_pos_view).manhattanLength() < 6 and len(self._current_pts) <= 1:
                        self._current_pts = []
                        self._press_pos_view = None
                        self.clear_mode_to_text()
                        self.setFocus(Qt.MouseFocusReason)
                        tc = self.cursorForPosition(e.pos())
                        self.setTextCursor(tc)
                        self._update_hover_cursor(e.pos())
                        self.viewport().update()
                        super().mouseReleaseEvent(e)
                        return
                self._press_pos_view = None

            # finish resizing
            if self._resizing:
                self._resizing = False
                self._apply_tool_cursor()
                self._update_hover_cursor(e.pos())
                self.viewport().update()
                self.overlayChanged.emit()  # <-- NEW (size persisted via image file; pos unchanged)
                return

            # if we were dragging an image (position changed), persist
            if self.selected_idx is not None and not self._current_pts and (e.button() == Qt.LeftButton):
                # We don't track a 'wasDragging' flag; emitting is harmless.
                self.overlayChanged.emit()  # <-- NEW

            if not self._current_pts:
                self._update_hover_cursor(e.pos())
                super().mouseReleaseEvent(e); return

            if self.tool == "eraser":
                before = self.strokes[:]
                if self.eraser_mode == "normal":
                    radius = max(4, self.widths["eraser"])
                    new_strokes = []
                    for s in self.strokes:
                        new_strokes.extend(self._erase_with_radius(s, self._current_pts, radius))
                    self.strokes = new_strokes
                else:
                    poly = self._current_pts[:]
                    self.strokes = [s for s in self.strokes
                                    if not any(self._point_in_poly(pt, poly) for pt in s.points)]
                self.undo_stack.append(("erase", before))
                self.redo_stack.clear()
                self.overlayChanged.emit()  
            else:
                pts = self._smooth(self._current_pts)
                if self.tool == "pencil":
                    color, width, alpha = self.colors["pencil"], self.widths["pencil"], self.alphas["pencil"]
                elif self.tool == "marker":
                    color, width, alpha = self.colors["marker"], self.widths["marker"], self.alphas["marker"]
                else:
                    color, width, alpha = self.colors["pen"],    self.widths["pen"],    self.alphas["pen"]
                self.strokes.append(Stroke(pts, color, width, alpha, self.tool))
                self.undo_stack.append(("stroke", None))
                self.overlayChanged.emit()  # <-- NEW

            self._current_pts = []
            self._update_hover_cursor(e.pos())
            self.viewport().update(); return
        super().mouseReleaseEvent(e)


    def _start_crop_selected(self):
        """Open crop dialog for the selected image."""
        if self.selected_idx is None: return
        im = self.images[self.selected_idx]
        base = im.get("orig", im.get("source", im.get("pm", QPixmap())))
        if base.isNull(): return
        dlg = CropDialog(base, self)
        if dlg.exec_() == QDialog.Accepted:
            out = dlg.result_pixmap()
            if out and not out.isNull():
                im["orig"] = out.copy()
                im["source"] = out.copy()
                im["pm"] = out.copy()
                im["scale"] = 1.0
                im["angle"] = 0.0
                self.viewport().update()
                self.overlayChanged.emit() 

    def paintEvent(self, ev):
        """Draw images, selection boxes, handles, and strokes on top of text."""
        super().paintEvent(ev)
        p = QPainter(self.viewport()); yoff = self._vy()
        p.setRenderHint(QPainter.Antialiasing)

        self._crop_btn_rect = None
        self._resize_handle_rect= None
        self._btn_delete_rect = None

        for i, im in enumerate(self.images):
            p.save(); p.setOpacity(im["opacity"])
            pos_v = self._to_view(im["pos"])
            p.drawPixmap(pos_v, im["pm"])
            p.restore()

            if self.selected_idx == i:
                rect_v = QRect(pos_v, im["pm"].size())
                pen = QPen(QColor(11,31,94,180)); pen.setWidth(2)
                p.setPen(pen); p.setBrush(Qt.NoBrush); p.drawRect(rect_v.adjusted(0,0,-1,-1))

                # crop button
                btn_w, btn_h = 46, 22
                bx = rect_v.left() + 6
                by = rect_v.top() - btn_h - 6
                if by < 2: by = rect_v.top() + 6
                self._crop_btn_rect = QRect(bx, by, btn_w, btn_h)
                p.setBrush(QColor(255,255,255,240)); p.setPen(QPen(QColor("#0b1f5e")))
                p.drawRoundedRect(self._crop_btn_rect, 6, 6)
                f = QFont(); f.setBold(True); f.setPointSize(9); p.setFont(f)
                p.drawText(self._crop_btn_rect, Qt.AlignCenter, "Crop")

                # delete button
                del_size = 18
                self._btn_delete_rect = QRect(rect_v.right()-del_size-6, rect_v.top()+6, del_size, del_size)
                p.setBrush(QColor(255,255,255,240)); p.setPen(QPen(QColor("#0b1f5e")))
                p.drawRoundedRect(self._btn_delete_rect, 5, 5)
                f2 = QFont(); f2.setBold(True); f2.setPointSize(10); p.setFont(f2)
                p.drawText(self._btn_delete_rect, Qt.AlignCenter, "×")

                # resize handle
                h = 16
                self._resize_handle_rect = QRect(rect_v.right()-h+1, rect_v.bottom()-h+1, h, h)
                p.setBrush(QColor(255, 255, 255, 240))
                p.setPen(QPen(QColor("#0b1f5e")))
                p.drawRoundedRect(self._resize_handle_rect, 4, 4)
                gpen = QPen(QColor("#0b1f5e")); gpen.setWidth(2)
                p.setPen(gpen)
                rr = self._resize_handle_rect.adjusted(4, 4, -4, -4)
                p.drawLine(rr.bottomLeft(), rr.topRight())

        for s in self.strokes: s.paint(p, yoff)

        if self._current_pts and self.tool in ("pencil","pen","marker"):
            if self.tool == "pencil":
                color, width, alpha = self.colors["pencil"], self.widths["pencil"], self.alphas["pencil"]
            elif self.tool == "marker":
                color, width, alpha = self.colors["marker"], self.widths["marker"], self.alphas["marker"]
            else:
                color, width, alpha = self.colors["pen"],    self.widths["pen"],    self.alphas["pen"]
            pen = QPen(color); c = QColor(color); c.setAlpha(alpha)
            pen.setColor(c); pen.setWidth(width)
            pen.setCapStyle(Qt.RoundCap); pen.setJoinStyle(Qt.RoundJoin); p.setPen(pen)
            path = QPainterPath(self._to_view(self._current_pts[0]))
            for pt in self._current_pts[1:]: path.lineTo(self._to_view(pt))
            p.drawPath(path)

        if self.tool == "eraser" and self.eraser_mode == "lasso" and self._current_pts:
            pts_v = [self._to_view(pt) for pt in self._current_pts]
            if len(pts_v) >= 2:
                pen = QPen(QColor(11, 31, 94, 170)); pen.setWidth(1); pen.setStyle(Qt.DashLine)
                p.setPen(pen)
                path = QPainterPath(pts_v[0])
                for pt in pts_v[1:]:
                    path.lineTo(pt)
                p.drawPath(path)
        p.end()

    def _hit_image(self, p_view: QPoint):
        """Hit test UI parts or images; return token or index."""
        if getattr(self, "_crop_btn_rect", None) and self._crop_btn_rect.contains(p_view): return "btn_crop"
        if getattr(self, "_btn_delete_rect", None) and self._btn_delete_rect.contains(p_view): return "btn_delete"
        if getattr(self, "_resize_handle_rect", None) and self._resize_handle_rect.contains(p_view): return "handle_resize"
        p_doc = self._to_doc(p_view)
        for i in reversed(range(len(self.images))):
            im = self.images[i]; pm, pos = im["pm"], im["pos"]
            if QRect(pos, pm.size()).contains(p_doc): return i
        return None

    def _confirm_delete_selected_image(self):
        """Ask and remove the selected image."""
        if self.selected_idx is None: return
        if QMessageBox.question(self, "Delete Image", "Delete this image?",
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes:
            self.images.pop(self.selected_idx)
            self.selected_idx = None
            self.imageCountChanged.emit(len(self.images))
            self.selectionChangedForImage.emit(False)
            self.viewport().update()
            self.overlayChanged.emit() 

    # ---- helpers
    def _smooth(self, pts):
        """Simple smoothing for freehand points."""
        if len(pts) < 3: return pts[:]
        out = [pts[0]]
        for i in range(1, len(pts)-1):
            p0, p1, p2 = pts[i-1], pts[i], pts[i+1]
            qx = 0.25*p0.x() + 0.5*p1.x() + 0.25*p2.x()
            qy = 0.25*p0.y() + 0.5*p1.y() + 0.25*p2.y()
            out.append(QPoint(int(qx), int(qy)))
        out.append(pts[-1]); return out

    # ---- persistence
    def overlay_to_dict(self):
        """Serialize strokes and images (including pos/scale/angle/opacity)."""
        return {
            "strokes": [{
                "points": [(p.x(), p.y()) for p in s.points],
                "color":  (s.color.red(), s.color.green(), s.color.blue()),
                "width":  s.width,
                "alpha":  s.alpha,
                "mode":   s.mode
            } for s in self.strokes],
            "images": [{
                "abspath": None,  # replaced with saved path in NoteTabWidget.to_payload()
                "pos": (im["pos"].x(), im["pos"].y()),
                "opacity": im.get("opacity", 1.0),
                "scale": im.get("scale", 1.0),
                "angle": im.get("angle", 0.0),
            } for im in self.images]
        }

    def dict_to_overlay(self, d: dict):
        """Load strokes and images from a dict."""
        self.strokes = []
        for s in d.get("strokes", []):
            pts = [QPoint(int(x), int(y)) for (x, y) in s.get("points", [])]
            col = s.get("color", (0,0,0)); qc = QColor(col[0], col[1], col[2])
            self.strokes.append(Stroke(pts, qc, s.get("width", 2), s.get("alpha",255), s.get("mode","pen")))

        self.images = []
        for imd in d.get("images", []):
            path = imd.get("abspath") or ""
            pm = QPixmap(path) if path and os.path.exists(path) else QPixmap()
            if pm.isNull(): continue
            pos = imd.get("pos", (40, 40))
            scale = float(imd.get("scale", 1.0))
            angle = float(imd.get("angle", 0.0))
            im = {"orig": pm.copy(), "source": pm.copy(), "pm": pm.copy(),
                  "pos": QPoint(int(pos[0]), int(pos[1])), "opacity": float(imd.get("opacity", 1.0)),
                  "angle": angle, "scale": scale}
            self._compose_pm(im)
            self.images.append(im)

        self.imageCountChanged.emit(len(self.images))
        self.viewport().update()

    def flattened_overlay_image(self, width_px=None) -> QImage:
        """Render editor content + overlay into a single image."""
        if width_px is None: width_px = max(640, self.viewport().width())
        doc = self.document().clone(); doc.setTextWidth(width_px)
        height_px = int(doc.size().height()) + 20
        img = QImage(width_px, max(200, height_px), QImage.Format_ARGB32); img.fill(Qt.white)
        p = QPainter(img)
        doc.drawContents(p, QRect(0, 0, width_px, height_px))
        for im in self.images:
            p.save(); p.setOpacity(im["opacity"]); p.drawPixmap(im["pos"], im["pm"]); p.restore()
        for s in self.strokes: s.paint(p, 0)
        p.end(); return img

# ======================= Small popup for tool settings =======================
class _ToolPopup(QWidget):
    """Frameless rounded popup container for color/size controls."""
    def __init__(self, parent=None):
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setObjectName("toolPopupFrame")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(8)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect().adjusted(0, 0, -1, -1)
        p.setPen(QPen(QColor("#0b1f5e"), 1))
        p.setBrush(QColor("#ffffff"))
        from PyQt5.QtCore import QRectF
        p.drawRoundedRect(QRectF(r), 12, 12)
        p.end()

# ============================ Note tab UI ============================
class NoteTabWidget(QWidget):
    """One note tab: title, toolbar, rich editor, overlay tools, autosave."""
    def __init__(self, note_id, user_id, title="", content="", overlay=None):
        super().__init__()
        self.note_id = note_id
        self.user_id = user_id
        os.makedirs(MEDIA_DIR, exist_ok=True)

        root = QVBoxLayout(self); root.setContentsMargins(10, 8, 10, 10); root.setSpacing(8)

        # title
        title_area = QVBoxLayout()
        lbl = QLabel("Note Title"); lbl.setObjectName("noteTitle")
        title_row = QHBoxLayout()
        self.title_input = QLineEdit(title); self.title_input.setObjectName("cuteTitleInput")
        self.title_input.setPlaceholderText("Enter a title (max 50 chars)"); self.title_input.setMaxLength(50)
        self.counter = QLabel(f"{len(self.title_input.text())}/50"); self.counter.setObjectName("titleCounter")
        self.title_input.textChanged.connect(lambda s: self.counter.setText(f"{len(s)}/50"))
        title_row.addWidget(self.title_input); title_row.addWidget(self.counter)
        title_area.addWidget(lbl); title_area.addLayout(title_row); root.addLayout(title_area)

        # toolbar (text + draw tools)
        tb = QHBoxLayout(); tb.setSpacing(12)

        def tb_btn(name, tip):
            b = QToolButton()
            b.setIcon(QIcon(PHOTO(name)))
            b.setToolTip(tip)
            b.setObjectName("notesTB")
            b.setProperty("toolbarControl", True)
            return b

        def mk_txt_btn(txt, tip):
            b = QToolButton()
            b.setText(txt)
            b.setToolTip(tip)
            b.setObjectName("notesTB")
            b.setProperty("toolbarControl", True)
            b.setProperty("bigText", True)
            return b

        self.btn_bold      = mk_txt_btn("B","Bold")
        self.btn_italic    = mk_txt_btn("I","Italic")
        self.btn_underline = mk_txt_btn("U","Underline")
        self.btn_bullets   = mk_txt_btn("•","Bulleted list")

        self.cb_fontsize = QComboBox()
        self.cb_fontsize.setObjectName("notesTB")
        self.cb_fontsize.setProperty("toolbarControl", True)
        self.cb_fontsize.setProperty("bigText", True)
        self.cb_fontsize.addItems([str(s) for s in (10,12,14,16,18,20,24,28,32)])
        self.cb_fontsize.setCurrentText("14")
        for i in range(self.cb_fontsize.count()): self.cb_fontsize.setItemData(i, Qt.AlignCenter, Qt.TextAlignmentRole)

        self.btn_fontcolor = QToolButton()
        self.btn_fontcolor.setObjectName("notesTB")
        self.btn_fontcolor.setProperty("toolbarControl", True)
        self.btn_fontcolor.setToolTip("Font color")
        self._font_color = QColor("#000000")

        for w in (self.btn_bold, self.btn_italic, self.btn_underline, self.btn_bullets,
                  self.cb_fontsize, self.btn_fontcolor):
            tb.addWidget(w)

        self.btn_img = tb_btn("image.png", "Insert Image"); tb.addWidget(self.btn_img)

        self.btn_pencil = tb_btn("pencil.png", "Pencil")
        self.btn_pen    = tb_btn("pen.png",    "Pen")
        self.btn_mark   = tb_btn("marker.png", "Highlighter")
        self.btn_eras   = tb_btn("eraser.png", "Eraser (N/L)")

        ICON_SIZE = 40
        BTN_PAD   = 16
        self._BTN_SIZE = ICON_SIZE + BTN_PAD

        for b in (self.btn_pencil, self.btn_pen, self.btn_mark, self.btn_eras): tb.addWidget(b)

        self.btn_undo   = tb_btn("undo.png", "Undo")
        self.btn_redo   = tb_btn("redo_notes.png", "Redo")
        tb.addWidget(self.btn_undo); tb.addWidget(self.btn_redo)

        tb.addStretch(); root.addLayout(tb)

        # uniform button sizing
        for b in (
            self.btn_bold, self.btn_italic, self.btn_underline, self.btn_bullets,
            self.cb_fontsize, self.btn_fontcolor,
            self.btn_img, self.btn_undo, self.btn_redo,
            self.btn_pencil, self.btn_pen, self.btn_mark, self.btn_eras
        ):
            b.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
            b.setFixedSize(ICON_SIZE + BTN_PAD, ICON_SIZE + BTN_PAD)

        self._btn_base_icons = {}
        for b in (self.btn_pencil, self.btn_pen, self.btn_mark, self.btn_eras,
                  self.btn_undo, self.btn_redo, self.btn_img):
            self._btn_base_icons[b] = b.icon()

        # editor
        wrap = QFrame(); wrap.setObjectName("noteBG")
        wrap_lay = QHBoxLayout(wrap); wrap_lay.setContentsMargins(10,10,10,10); wrap_lay.setSpacing(6)

        self.editor = InkTextEdit()
        if content and "<" in content and "</" in content:
            self.editor.setHtml(content)
        else:
            self.editor.setPlainText(content)
        if overlay:
            self.editor.dict_to_overlay(overlay)

        wrap_lay.addWidget(self.editor, 1); root.addWidget(wrap, 1)

        # autosave debounce
        self._save_timer = QTimer(self); self._save_timer.setSingleShot(True); self._save_timer.setInterval(800)
        self.title_input.textChanged.connect(self._debounce_save)
        self.editor.textChanged.connect(self._debounce_save)
        self.editor.overlayChanged.connect(self._debounce_save)  

        # actions
        self.btn_img.clicked.connect(self._insert_image)
        self.btn_undo.clicked.connect(self.editor.undo)
        self.btn_redo.clicked.connect(self.editor.redo)

        self.btn_pencil.clicked.connect(lambda: self._tool_popup("pencil", self.btn_pencil))
        self.btn_pen.clicked.connect   (lambda: self._tool_popup("pen",    self.btn_pen))
        self.btn_mark.clicked.connect  (lambda: self._tool_popup("marker", self.btn_mark))

        self.btn_bold.clicked.connect(self._toggle_bold)
        self.btn_italic.clicked.connect(self._toggle_italic)
        self.btn_underline.clicked.connect(self._toggle_underline)
        self.btn_bullets.clicked.connect(self._toggle_bullets)
        self.cb_fontsize.currentTextChanged.connect(self._change_font_size)
        self.btn_fontcolor.clicked.connect(self._pick_font_color)

        # sync font-size box with cursor
        self._syncing_size = False
        self.editor.currentCharFormatChanged.connect(self._sync_font_size_from_cursor)

        # cursors for draw tools
        pencil_path = PHOTO("pencil.png"); pen_path = PHOTO("pen.png")
        marker_path = PHOTO("marker.png"); eraser_path = PHOTO("eraser.png")
        self.editor.set_tool_pixmaps(
            {"pencil": pencil_path, "pen": pen_path, "marker": marker_path, "eraser": eraser_path},
            base_size=ICON_SIZE - 10
        )

        # ======= LOAD PERSISTED TOOL PREFS BEFORE BADGES =======
        self._prefs_timer = QTimer(self); self._prefs_timer.setSingleShot(True); self._prefs_timer.setInterval(600)
        self._prefs_timer.timeout.connect(self._save_tool_prefs)
        self._load_tool_prefs()

        # color badges
        self._update_fontcolor_icon(store_base=True)
        self._apply_accent_badge(self.btn_pencil, self.editor.colors["pencil"])
        self._apply_accent_badge(self.btn_pen,    self.editor.colors["pen"])
        self._apply_accent_badge(self.btn_mark,   self.editor.colors["marker"])
        self._apply_accent_badge(self.btn_fontcolor, self._font_color)

        # eraser dropdown (Normal/Lasso)
        def _build_eraser_menu():
            menu = QMenu(self); menu.setProperty("toolbarMenu", True)
            group = QActionGroup(menu); group.setExclusive(True)
            act_n = QAction("Normal (N)", menu); act_n.setCheckable(True)
            act_l = QAction("Lasso (L)",  menu); act_l.setCheckable(True)
            group.addAction(act_n); group.addAction(act_l)
            is_lasso = (self.editor.eraser_mode == "lasso")
            act_l.setChecked(is_lasso)
            act_n.setChecked(not is_lasso) if False else act_n.setChecked(not is_lasso)
            act_n.triggered.connect(lambda: self._set_eraser_mode_ui("normal"))
            act_l.triggered.connect(lambda: self._set_eraser_mode_ui("lasso"))
            menu.addAction(act_n); menu.addAction(act_l)
            menu.aboutToShow.connect(lambda: self.editor.set_mode("eraser"))
            self._eraser_menu_normal = act_n; self._eraser_menu_lasso = act_l
            return menu

        def _sync_eraser_menu_state():
            if hasattr(self, "_eraser_menu_normal"):
                self._eraser_menu_lasso.setChecked(self.editor.eraser_mode == "lasso")
                self._eraser_menu_normal.setChecked(self.editor.eraser_mode != "lasso")

        self._eraser_menu = _build_eraser_menu()
        self.btn_eras.setPopupMode(QToolButton.InstantPopup)
        self.btn_eras.setMenu(self._eraser_menu)
        self._eraser_menu.aboutToShow.connect(_sync_eraser_menu_state)

    # ======= PERSISTENCE OF TOOL PREFS (colors/sizes/eraser mode) =======
    def _load_tool_prefs(self):
        """Load per-user tool preferences from DB and apply to editor."""
        try:
            prefs = db.get_notes_tool_prefs(self.user_id)
        except Exception:
            prefs = None
        if not prefs:
            return
        # colors
        for k in ("pencil", "pen", "marker"):
            hx = prefs.get("colors", {}).get(k)
            if hx:
                try:
                    self.editor.colors[k] = QColor(hx)
                except Exception:
                    pass
        # sizes
        for k in ("pencil", "pen", "marker", "eraser"):
            val = prefs.get("widths", {}).get(k)
            if isinstance(val, (int, float)) and val > 0:
                self.editor.widths[k] = int(val)
        # eraser mode
        mode = prefs.get("eraser_mode")
        if mode in ("normal", "lasso"):
            self.editor.eraser_mode = mode

    def _schedule_prefs_save(self):
        """Debounce saves to avoid disk spam."""
        self._prefs_timer.start()

    def _save_tool_prefs(self):
        """Persist current tool prefs to DB for this user."""
        prefs = {
            "colors": {k: self.editor.colors[k].name() for k in ("pencil", "pen", "marker")},
            "widths": {k: int(self.editor.widths[k]) for k in ("pencil", "pen", "marker", "eraser")},
            "eraser_mode": self.editor.eraser_mode
        }
        try:
            db.set_notes_tool_prefs(self.user_id, prefs)
        except Exception as e:
            # Silent failure is fine for prefs
            print(f"Note prefs save failed: {e}")

    # ---- icon badge helpers
    def _apply_accent_badge(self, btn: QToolButton, color: QColor):
        """Draw a small color dot over a toolbar icon to show the active color."""
        base_icon = self._btn_base_icons.get(btn, btn.icon())
        sz = btn.iconSize()
        if sz.width() <= 0 or sz.height() <= 0:
            sz = QSize(40, 40)
        pm = base_icon.pixmap(sz)
        if pm.isNull():
            pm = QPixmap(sz)
            pm.fill(Qt.transparent)

        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        r = max(6, sz.width() // 5)
        rect = QRect(sz.width() - r - 2, sz.height() - r - 2, r, r)
        p.setPen(QPen(QColor("#0b1f5e"), 1))
        p.setBrush(QBrush(color))
        p.drawEllipse(rect)
        p.end()
        btn.setIcon(QIcon(pm))

    def _set_eraser_mode_ui(self, mode: str):
        """Switch eraser mode and keep cursor consistent."""
        self.editor.set_eraser_mode(mode)
        self._schedule_prefs_save()

    def _update_fontcolor_icon(self, store_base=False):
        """Draw a bold 'A' icon; the color dot shows selected font color."""
        size = getattr(self, "_BTN_SIZE", 56)
        pm = QPixmap(size, size)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        f = QFont()
        f.setBold(True)
        f.setPixelSize(int(size * 0.60))
        p.setFont(f)
        p.setPen(QColor("#0b1f5e"))
        p.drawText(pm.rect(), Qt.AlignCenter, "A")
        p.end()
        icon = QIcon(pm)
        self.btn_fontcolor.setIcon(icon)
        self.btn_fontcolor.setIconSize(QSize(size - 16, size - 16))
        if store_base:
            self._btn_base_icons[self.btn_fontcolor] = icon

    # ---- text formatting
    def _merge_fmt(self, fmt: QTextCharFormat):
        """Apply a char format to selection or at cursor."""
        cur = self.editor.textCursor()
        if not cur.hasSelection():
            self.editor.mergeCurrentCharFormat(fmt)
        else:
            cur.mergeCharFormat(fmt)
            self.editor.mergeCurrentCharFormat(fmt)

    def _toggle_bold(self):
        fmt = QTextCharFormat()
        fmt.setFontWeight(QFont.Normal if self.editor.fontWeight() > QFont.Normal else QFont.Bold)
        self._merge_fmt(fmt)

    def _toggle_italic(self):
        fmt = QTextCharFormat()
        fmt.setFontItalic(not self.editor.fontItalic())
        self._merge_fmt(fmt)

    def _toggle_underline(self):
        fmt = QTextCharFormat()
        fmt.setFontUnderline(not self.editor.fontUnderline())
        self._merge_fmt(fmt)

    def _toggle_bullets(self):
        """Toggle a bulleted list on the current paragraph(s)."""
        cur = self.editor.textCursor()
        if cur.currentList():
            lst = cur.currentList()
            cur.beginEditBlock()
            block = cur.block()
            lst.remove(block)
            cur.endEditBlock()
        else:
            lf = QTextListFormat(); lf.setStyle(QTextListFormat.ListDisc)
            cur.createList(lf)

    def _change_font_size(self, s: str):
        """Apply a font size from the combobox value."""
        if getattr(self, "_syncing_size", False):
            return
        try:
            val = float(s)
        except Exception:
            return
        fmt = QTextCharFormat(); fmt.setFontPointSize(val)
        self._merge_fmt(fmt)

    def _sync_font_size_from_cursor(self, fmt: QTextCharFormat):
        """Keep the combobox showing the size under the caret."""
        size = fmt.fontPointSize()
        if size <= 0:
            size = self.editor.fontPointSize()
            if size <= 0:
                size = self.editor.currentFont().pointSizeF() or 0
        if size > 0:
            size_int = int(round(size))
            items = []
            for i in range(self.cb_fontsize.count()):
                try:
                    items.append(int(self.cb_fontsize.itemText(i)))
                except Exception:
                    pass
            if size_int not in items:
                items.append(size_int)
                items = sorted(set(items))
                self.cb_fontsize.blockSignals(True)
                self.cb_fontsize.clear()
                self.cb_fontsize.addItems([str(v) for v in items])
                for i in range(self.cb_fontsize.count()):
                    self.cb_fontsize.setItemData(i, Qt.AlignCenter, Qt.TextAlignmentRole)
                self.cb_fontsize.blockSignals(False)
            self._syncing_size = True
            self.cb_fontsize.setCurrentText(str(size_int))
            self._syncing_size = False

    # ----- popup helpers for color/size ----
    def _apply_swatch_bg(self, btn: QPushButton, col: QColor):
        """Style the color swatch button with the given color."""
        btn.setFixedSize(26, 26)
        btn.setStyleSheet(
            f"QPushButton{{border:1px solid #0b1f5e;border-radius:6px;padding:0;background:{col.name()};}}"
            f"QPushButton:hover{{background:{col.lighter(105).name()};}}"
            f"QPushButton:pressed{{background:{col.darker(105).name()};}}"
        )

    def _dot_icon(self, dot_diam: int, box: int = 26, lift_px: float = 0.0) -> QIcon:
        """Make a circular dot icon used to choose sizes."""
        pm = QPixmap(box, box); pm.fill(Qt.transparent)
        p = QPainter(pm); p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen); p.setBrush(QColor("#0b1f5e"))
        from PyQt5.QtCore import QRectF
        cx = box / 2.0
        cy = box / 2.0 + float(lift_px)
        p.drawEllipse(QRectF(cx - dot_diam/2.0, cy - dot_diam/2.0, dot_diam, dot_diam))
        p.end()
        return QIcon(pm)

    def _pick_font_color(self):
        """Open a color picker and apply selected text color."""
        c = QColorDialog.getColor(getattr(self, "_font_color", QColor("#000000")),
                                  self, "Font color", QColorDialog.DontUseNativeDialog)
        if c.isValid():
            self._font_color = c
            fmt = QTextCharFormat(); fmt.setForeground(c); self._merge_fmt(fmt)
            self._update_fontcolor_icon(store_base=True); self._apply_accent_badge(self.btn_fontcolor, c)

    def _tool_popup(self, name: str, anchor_btn: QToolButton):
        """Show a small popup for tool color and size, anchored to a button."""
        self.editor.set_mode(name)
        pop = _ToolPopup(self)

        def add_lbl(text):
            lbl = QLabel(text, pop)
            f = lbl.font(); f.setBold(True); lbl.setFont(f)
            lbl.setStyleSheet("color:#0b1f5e;")
            pop.layout().addWidget(lbl)

        # color swatch
        if name in ("pencil", "pen", "marker"):
            add_lbl("Color:")
            swatch = QPushButton("", pop)
            swatch.setProperty("toolPopup", True)
            current = self.editor.colors.get(name, QColor("#000000"))
            self._apply_swatch_bg(swatch, current)

            def _pick():
                c = QColorDialog.getColor(current, self, "Pick color", QColorDialog.DontUseNativeDialog)
                if c.isValid():
                    self.editor.colors[name] = c
                    self._apply_swatch_bg(swatch, c)
                    if name == "pencil": self._apply_accent_badge(self.btn_pencil, c)
                    elif name == "pen":  self._apply_accent_badge(self.btn_pen, c)
                    elif name == "marker": self._apply_accent_badge(self.btn_mark, c)
                    self._schedule_prefs_save()

            swatch.clicked.connect(_pick)
            pop.layout().addWidget(swatch)

        # size dots
        add_lbl("Size:")
        DOT_DIAMS = [10, 16, 22, 26]
        WIDTHS = {
            "pencil": [2, 4, 6, 8],
            "pen":    [4, 6, 8, 10],
            "marker": [12, 16, 20, 26],
        }
        current_width = self.editor.widths.get(name, 4)
        widths_for_tool = WIDTHS.get(name, WIDTHS["pencil"])

        def on_size_clicked(width_val):
            self.editor.set_tool_size(name, width_val)
            self._schedule_prefs_save()
            pop.close()

        def dot(dot_px, width_val, is_current=False):
            btn = QPushButton("", pop)
            btn.setProperty("toolPopup", True)
            btn.setFixedSize(32, 32)
            btn.setIcon(self._dot_icon(dot_px, box=26))
            btn.setIconSize(QSize(26, 26))
            base = (
                "QPushButton{border:1px solid #0b1f5e;border-radius:6px;"
                "background:#ffffff;padding:0;}"
                "QPushButton:hover{background:#f1f5ff;}"
            )
            if is_current:
                base = (
                    "QPushButton{border:2px solid #0b1f5e;border-radius:6px;"
                    "background:#eef4ff;padding:0;}"
                    "QPushButton:hover{background:#e6f0ff;}"
                )
            btn.setStyleSheet(base)
            btn.clicked.connect(lambda: on_size_clicked(width_val))
            return btn

        for diam, wv in zip(DOT_DIAMS, widths_for_tool):
            pop.layout().addWidget(dot(diam, wv, is_current=(wv == current_width)))

        g = anchor_btn.mapToGlobal(anchor_btn.rect().bottomLeft())
        pop.adjustSize()
        pop.move(g)
        pop.show()

    # ---- save payload / IO ----
    def to_payload(self) -> dict:
        """Build the content payload for saving to DB (and write image files)."""
        overlay = self.editor.overlay_to_dict()
        img_out = []
        for i, im in enumerate(self.editor.images):
            pm, pos = im["pm"], im["pos"]
            # include user_id to avoid collisions across accounts
            abs_path = os.path.join(MEDIA_DIR, f"{self.user_id}-{self.note_id}-{i}.png")
            pm.save(abs_path, "PNG")
            img_out.append({
                "abspath": abs_path,
                "pos": (pos.x(), pos.y()),
                "opacity": im.get("opacity", 1.0),
                "scale": im.get("scale", 1.0),
                "angle": im.get("angle", 0.0),
            })
        overlay["images"] = img_out
        return {
            "title": (self.title_input.text().strip() or "Untitled"),
            "content": self.editor.toHtml(),
            "overlay": overlay,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "user_id": self.user_id
        }

    def _insert_image(self):
        """Open file picker and insert chosen image."""
        path, _ = QFileDialog.getOpenFileName(self, "Insert Image", "", "Images (*.png *.jpg *.jpeg)")
        if path: self.editor.insert_image(path)

    def _debounce_save(self): self._save_timer.start()

# ============================ Organizer Shell ===============================
class NoteOrganizerWidget(QWidget):
    def __init__(self, on_return_callback=None, user_id=None):
        super().__init__()
        self.on_return_callback = on_return_callback
        self.user_id = user_id
        self.setWindowTitle("Notes Editor")
        self.setMinimumSize(780, 720)
        self.setObjectName("notesOrganizer")
        self.setStyleSheet(get_notes_organizer_styles())

        main = QVBoxLayout(self); main.setContentsMargins(10, 10, 10, 10); main.setSpacing(8)

        # header toolbar
        tb = QHBoxLayout(); tb.setSpacing(6)
        def tb_btn(name, tip):
            b = QToolButton(); b.setIcon(QIcon(PHOTO("{}".format(name)))); b.setIconSize(QSize(26,26))
            b.setToolTip(tip); b.setObjectName("notesTB"); b.setProperty("toolbarControl", True)
            return b
        self.btn_back   = tb_btn("notes_back.png", "Back")
        self.btn_save   = tb_btn("save.png",       "Save")

        self.btn_export = QToolButton()
        self.btn_export.setObjectName("notesTB")
        self.btn_export.setProperty("toolbarControl", True)
        self.btn_export.setText("Export")
        self.btn_export.setPopupMode(QToolButton.InstantPopup)
        m = QMenu(self); m.setProperty("toolbarMenu", True)
        m.addAction("Export as TXT", self._export_txt)
        self.btn_export.setMenu(m)

        for b in (self.btn_back, self.btn_save, self.btn_export): tb.addWidget(b)
        tb.addStretch(); main.addLayout(tb)

        # tabs
        self.tabs = QTabWidget(); self.tabs.setObjectName("notesTabs")
        self.tabs.setTabsClosable(True); self.tabs.tabCloseRequested.connect(self._close_tab)
        try:
            bar = self.tabs.tabBar()
            bar.setUsesScrollButtons(True)
            bar.setExpanding(False)
            bar.setElideMode(Qt.ElideNone)
            self.tabs.setMovable(True)
            if hasattr(bar, "tabMoved"):
                bar.tabMoved.connect(lambda _f, _t: self._update_stepper())
        except Exception:
            pass

        main.addWidget(self.tabs, 1)

        # corner panel: prev/next + new tab
        corner = QWidget(self.tabs); corner.setObjectName("tabCornerPanel")
        cl = QHBoxLayout(corner); cl.setContentsMargins(0,0,0,0); cl.setSpacing(6)

        self.btn_prev = QToolButton(corner); self.btn_prev.setObjectName("tabStepper")
        self.btn_prev.setText("‹"); self.btn_prev.setToolTip("Previous note"); self.btn_prev.setFixedSize(15, 15)

        self.btn_next = QToolButton(corner); self.btn_next.setObjectName("tabStepper")
        self.btn_next.setText("›"); self.btn_next.setToolTip("Next note"); self.btn_next.setFixedSize(15, 15)

        cl.addWidget(self.btn_prev); cl.addWidget(self.btn_next)

        self._corner_add_btn = QToolButton(corner)
        self._corner_add_btn.setIcon(QIcon(PHOTO("new.png"))); self._corner_add_btn.setIconSize(QSize(22, 22))
        self._corner_add_btn.setToolTip("New tab"); self._corner_add_btn.setObjectName("cornerNew")
        self._corner_add_btn.setFixedSize(24, 20); self._corner_add_btn.setAutoRaise(True)
        self._corner_add_btn.setFocusPolicy(Qt.NoFocus); self._corner_add_btn.clicked.connect(self._new_note)

        cl.addWidget(self._corner_add_btn)
        self.tabs.setCornerWidget(corner, Qt.TopRightCorner)

        # wire actions
        self.btn_back.clicked.connect(lambda: self.on_return_callback() if self.on_return_callback else None)
        self.btn_save.clicked.connect(lambda: self._save_active(show_popup=True))
        self.btn_prev.clicked.connect(self._go_prev)
        self.btn_next.clicked.connect(self._go_next)
        self.tabs.currentChanged.connect(lambda _=None: self._update_stepper())

        # open recent or create first
        rows = None
        try:
            rows = db.list_notes(user_id=self.user_id, order="updated_desc", limit=10)
        except TypeError:
            rows = db.list_notes(self.user_id, order="updated_desc", limit=10)
        if rows:
            for r in rows:
                self._open_by_id(r["id"])
        else:
            self._new_note()
        self._update_stepper()

    def close_tab_for_note(self, note_id: int) -> bool:
        """Close the tab for a note if it's open. Returns True if closed."""
        for i in range(self.tabs.count()):
            w = self.tabs.widget(i)
            if isinstance(w, NoteTabWidget) and getattr(w, "note_id", None) == note_id:
                self.tabs.removeTab(i)
                if self.tabs.count() == 0:
                    self._new_note()
                self._update_stepper()
                return True
        return False

    def _gc_deleted_tabs(self):
        removed_any = False
        for i in reversed(range(self.tabs.count())):
            w = self.tabs.widget(i)
            if isinstance(w, NoteTabWidget):
                nid = getattr(w, "note_id", None)
                ok = None
                try:
                    ok = db.get_note(nid, user_id=self.user_id)
                except TypeError:
                    ok = db.get_note(nid, self.user_id)
                if nid is None or not ok:
                    self.tabs.removeTab(i)
                    removed_any = True
        if removed_any:
            if self.tabs.count() == 0:
                self._new_note()
            self._update_stepper()

    def showEvent(self, e):
        """Prune dead tabs whenever this page is shown."""
        super().showEvent(e)
        self._gc_deleted_tabs()

    # ---- stepper helpers
    def _go_prev(self):
        i = self.tabs.currentIndex()
        if i > 0:
            self.tabs.setCurrentIndex(i - 1)
        self._update_stepper()

    def _go_next(self):
        i = self.tabs.currentIndex()
        n = self.tabs.count()
        if i < n - 1:
            self.tabs.setCurrentIndex(i + 1)
        self._update_stepper()

    def _update_stepper(self):
        """Enable/disable ‹ › controls based on tab index/count."""
        n = self.tabs.count()
        i = self.tabs.currentIndex()
        self.btn_prev.setEnabled(n > 1 and i > 0)
        self.btn_next.setEnabled(n > 1 and i < n - 1)

    # ---- internals
    def _open_by_id(self, nid: int):
        """Open a note by id (reuse tab if already open)."""
        for i in range(self.tabs.count()):
            w = self.tabs.widget(i)
            if isinstance(w, NoteTabWidget) and getattr(w, "note_id", None) == nid:
                self.tabs.setCurrentIndex(i); self._update_stepper(); return

        row = None
        try:
            row = db.get_note(nid, user_id=self.user_id)
        except TypeError:
            row = db.get_note(nid, self.user_id)
        if not row: return

        overlay = None
        raw_overlay = row.get("overlay") if isinstance(row, dict) else None
        if raw_overlay:
            try: overlay = json.loads(raw_overlay)
            except Exception: overlay = None

        tab = NoteTabWidget(nid, self.user_id, row.get("title","Untitled"), row.get("content",""), overlay=overlay)
        idx = self.tabs.addTab(tab, self._elided(row.get("title","Untitled")))
        self.tabs.setCurrentIndex(idx)

        tab.title_input.textChanged.connect(lambda s, tw=tab: self._update_tab_text_for(tw, s))
        tab._save_timer.timeout.connect(self._save_active)
        self._update_stepper()

    def _update_tab_text_for(self, tab_widget: QWidget, title: str):
        """Update the tab text to match current note title (with elide)."""
        i = self.tabs.indexOf(tab_widget)
        if i != -1:
            self.tabs.setTabText(i, self._elided(title or "Untitled"))

    def _elided(self, s: str) -> str: return s if len(s) <= 18 else (s[:15] + "…")

    def _new_note(self):
        """Create a new blank note and open it in a tab."""
        nid = None
        try:
            nid = db.create_note("Untitled", "", user_id=self.user_id)
        except TypeError:
            nid = db.create_note("Untitled", "", self.user_id)
        self._open_by_id(nid)
        self._update_stepper()

    def _close_tab(self, index: int):
        """Save the note in the tab being closed, then remove it."""
        w = self.tabs.widget(index)
        if isinstance(w, NoteTabWidget):
            payload = w.to_payload()
            try:
                db.update_note(w.note_id, payload["title"], payload["content"],
                               json.dumps(payload["overlay"]), user_id=self.user_id)
            except TypeError:
                try:
                    db.update_note(w.note_id, payload["title"], payload["content"],
                                   json.dumps(payload["overlay"]), self.user_id)
                except TypeError:
                    db.update_note(w.note_id, payload["title"], payload["content"],
                                   json.dumps(payload["overlay"]), user_id=self.user_id)
        self.tabs.removeTab(index)
        if self.tabs.count() > 0 and self.tabs.currentIndex() == -1:
            self.tabs.setCurrentIndex(max(0, index - 1))
        self._update_stepper()

    def _save_active(self, show_popup: bool=False):
        """Save current tab's note. If deleted elsewhere, close the tab."""
        w = self.tabs.currentWidget()
        if not isinstance(w, NoteTabWidget):
            return

        ok = None
        try:
            ok = db.get_note(w.note_id, user_id=self.user_id)
        except TypeError:
            ok = db.get_note(w.note_id, self.user_id)

        if not ok:
            idx = self.tabs.indexOf(w)
            if idx != -1:
                self.tabs.removeTab(idx)
            if self.tabs.count() == 0:
                self._new_note()
            self._update_stepper()
            if show_popup:
                QMessageBox.warning(self, "Note deleted", "This note was deleted elsewhere. The tab has been closed.")
            return

        payload = w.to_payload()
        try:
            db.update_note(w.note_id, payload["title"], payload["content"],
                           json.dumps(payload["overlay"]), user_id=self.user_id)
        except TypeError:
            try:
                db.update_note(w.note_id, payload["title"], payload["content"],
                               json.dumps(payload["overlay"]), self.user_id)
            except TypeError:
                db.update_note(w.note_id, payload["title"], payload["content"],
                               json.dumps(payload["overlay"]), user_id=self.user_id)
        self._update_tab_text_for(w, payload["title"])
        if show_popup:
            QMessageBox.information(self, "Saved", "Your note has been saved.")

    def _export_txt(self):
        """Export the current note to a .txt file (title + plain text)."""
        w = self.tabs.currentWidget()
        if not isinstance(w, NoteTabWidget): return
        title = w.title_input.text().strip() or "Untitled"
        path, _ = QFileDialog.getSaveFileName(self, "Export TXT", f"{title}.txt", "Text Files (*.txt)")
        if not path: return
        with open(path, "w", encoding="utf-8") as f:
            f.write(title + "\n\n" + w.editor.toPlainText())
        QMessageBox.information(self, "Export", "TXT file saved.")
