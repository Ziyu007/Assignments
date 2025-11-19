import os
from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel,
    QListWidget, QListWidgetItem, QMessageBox, QButtonGroup, QToolButton, QMenu,
    QFileDialog, QInputDialog, QTableWidget, QTableWidgetItem, QAbstractItemView,
    QHeaderView, QListView
)
from PyQt5.QtCore import Qt, QSize, QPoint, pyqtSignal
from PyQt5.QtGui import QIcon, QPixmap

from styles.dashboard_styles import get_dashboard_styles
from database.db_manager import get_connection

APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# ---------- sizing ----------
SIDEBAR_WIDTH = 178
PLUS_W        = 36
SEARCH_W      = 260
ROW_H         = 26
ACTIONS_W     = 46
LEVEL_STEP    = 14
NOTE_EXTRA_INDENT = 12

# ---------- assets ----------
ASSET_DIRS = ["Photo", "assets", "icons", "images"]
def _find_first(cands):
    for d in ASSET_DIRS:
        for n in cands:
            p = os.path.join(APP_ROOT, d, n)
            if os.path.exists(p):
                return p
    return ""

FILE_ICON_PATH   = _find_first(["note_file.png"])
FOLDER_ICON_PATH = _find_first(["folder.png"])
FILTER_ICON_PATH = _find_first(["filter.png"])
DOTS_ICON_PATH   = _find_first(["more.png"])
EDIT_ICON_PATH   = _find_first(["edit.png"])
BACK_ICON_PATH   = _find_first(["back.png", "notes_back.png"])


class _ClickLabel(QLabel):
    """Label that calls a callback when clicked."""
    def __init__(self, text, on_click, parent=None):
        super().__init__(text, parent)
        self._on = on_click
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and callable(self._on):
            self._on()
        super().mousePressEvent(e)


class FixedColumnsIconList(QListWidget):
    """Icon grid with a fixed number of columns that resizes nicely."""
    def __init__(self, columns=5, base_item_h=110, icon_max=96, parent=None):
        super().__init__(parent)
        self.columns = max(1, int(columns))
        self.base_item_h = base_item_h
        self.icon_max = icon_max
        self.setObjectName("gridView")
        self.setViewMode(QListWidget.IconMode)
        self.setMovement(QListWidget.Static)
        self.setResizeMode(QListWidget.Adjust)
        self.setWrapping(True)
        self.setSpacing(10)
        self.setWordWrap(True)
        self.setUniformItemSizes(True)
        self.setSelectionMode(QListView.SingleSelection)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._recalc_grid()
    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._recalc_grid()
    def _recalc_grid(self):
        vp_w = max(1, self.viewport().width())
        spacing = self.spacing()
        cols = self.columns
        item_w = max(110, (vp_w - spacing * (cols + 1)) // cols)
        self.setGridSize(QSize(item_w, self.base_item_h))
        icon = min(self.icon_max, int(item_w * 0.6))
        self.setIconSize(QSize(icon, icon))


class DashboardWidget(QWidget):
    """
    Notes dashboard (per-user):
    - Left: folders (tree) and special items.
    - Right: list or grid of notes.
    - Top: search, sort, add.
    """
    noteDeleted = pyqtSignal(int)

    def __init__(self, user_id, on_add_note_clicked=None, on_back_home=None, on_note_deleted=None):
        super().__init__()
        if user_id is None:
            raise ValueError("DashboardWidget requires a non-null user_id")
        self.user_id = user_id
        self.on_add_note_clicked = on_add_note_clicked
        self.on_back_home = on_back_home
        self.on_note_deleted = on_note_deleted

        # app-level state
        self.sort_mode = 0                # 0 = date desc, 1 = title asc
        self.current_folder_id = None     # None=All, -1=Uncategorized
        self.current_folder_name = None
        self._expanded_folders = set()    # expanded nodes in sidebar
        self.view_mode = "list"           # "list" or "grid"

        # window chrome
        self.setObjectName("dashboardRoot")
        self.setStyleSheet(get_dashboard_styles())
        self.setWindowTitle("Note Organizer Dashboard")
        self.setMinimumSize(760, 500)

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(6)
        self.layout = root

        self._setup_top()
        self._setup_main()
        self._setup_footer()

        # initial data load
        self._refresh_folders()
        self._refresh_center()
        self._refilter_notes()

    # ---------- top bar ----------
    def _setup_top(self):
        bar = QHBoxLayout(); bar.setSpacing(6)

        title = QLabel("Dashboard"); title.setObjectName("dashTitle")

        self.search_bar = QLineEdit(placeholderText="Search notes…")
        self.search_bar.setObjectName("searchField")
        self.search_bar.setFixedWidth(SEARCH_W)
        self.search_bar.textChanged.connect(self._refilter_notes)

        self.filter_btn = QToolButton(objectName="filterBtn")
        if FILTER_ICON_PATH:
            self.filter_btn.setIcon(QIcon(FILTER_ICON_PATH))
        self._attach_sort_menu()

        self.btn_list = QPushButton("List", objectName="viewBtnLeft")
        self.btn_grid = QPushButton("Grid", objectName="viewBtnRight")
        for b in (self.btn_list, self.btn_grid): b.setCheckable(True)
        self.btn_list.setChecked(True)
        grp = QButtonGroup(self); grp.setExclusive(True)
        grp.addButton(self.btn_list); grp.addButton(self.btn_grid)
        self.btn_list.clicked.connect(lambda: self._set_view_mode("list"))
        self.btn_grid.clicked.connect(lambda: self._set_view_mode("grid"))
        seg = QHBoxLayout(); seg.setSpacing(0); seg.setContentsMargins(0,0,0,0)
        seg_wrap = QWidget(objectName="segWrap"); seg_wrap.setLayout(seg)
        seg.addWidget(self.btn_list); seg.addWidget(self.btn_grid)

        self.add_button = QToolButton(objectName="addButton")
        self.add_button.setText("+")
        self.add_button.setFixedWidth(PLUS_W)
        self.add_button.setPopupMode(QToolButton.InstantPopup)
        self._attach_add_menu()

        bar.addWidget(title); bar.addStretch()
        bar.addWidget(self.search_bar)
        bar.addWidget(self.filter_btn)
        bar.addWidget(seg_wrap)
        bar.addWidget(self.add_button)
        self.layout.addLayout(bar)

    def _attach_sort_menu(self):
        """Build the sort menu and link actions."""
        m = QMenu(self); m.setObjectName("popupMenu")
        a_date = m.addAction("Sort by Date (new → old)")
        a_name = m.addAction("Sort by Name (A → Z)")
        for i, a in enumerate((a_date, a_name)):
            a.setCheckable(True); a.setChecked(i == self.sort_mode)
        a_date.triggered.connect(lambda: self._set_sort_mode(0))
        a_name.triggered.connect(lambda: self._set_sort_mode(1))
        self.filter_btn.setMenu(m)
        self.filter_btn.setPopupMode(QToolButton.InstantPopup)

    def _attach_add_menu(self):
        """Build the + menu with note, folder, and import."""
        m = QMenu(self); m.setObjectName("addMenu")
        m.addAction("Add Note", lambda: self._add_note_here(self.current_folder_id))
        m.addAction("New Folder", lambda: self._add_subfolder(self.current_folder_id))
        m.addAction("Import Note (.txt)", lambda: self._import_note(self.current_folder_id))
        self.add_button.setMenu(m)

    def _set_sort_mode(self, mode):
        """Apply a new sort mode then refresh."""
        if mode == self.sort_mode: return
        self.sort_mode = mode
        self._attach_sort_menu()
        self._refilter_notes()

    # ---------- main area ----------
    def _setup_main(self):
        main = QHBoxLayout(); main.setSpacing(6)

        # sidebar
        self.folder_list = QListWidget(objectName="folderList")
        self.folder_list.setFixedWidth(SIDEBAR_WIDTH)
        # allow horizontal scroll if long names/indent
        self.folder_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.folder_list.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.folder_list.setAutoScroll(True)
        self.folder_list.itemClicked.connect(self._on_sidebar_click)
        self.folder_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.folder_list.customContextMenuRequested.connect(self._folder_context_menu)
        self.folder_list.currentItemChanged.connect(lambda *_: self._refresh_folder_row_styles())

        # right: list or grid
        self.right = QVBoxLayout(); self.right.setSpacing(4)

        self.table = QTableWidget(0, 3, self)
        self.table.setObjectName("notesTable")
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(ROW_H)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        hdr = self.table.horizontalHeader()
        hdr.setStretchLastSection(False)
        hdr.setSectionResizeMode(0, QHeaderView.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.Fixed)
        self.table.setColumnWidth(2, ACTIONS_W)
        self.table.setHorizontalHeaderLabels(["Name", "Date Modified", ""])
        self.table.cellDoubleClicked.connect(self._open_row_by_doubleclick)

        self.grid = FixedColumnsIconList(columns=5, base_item_h=110, icon_max=96, parent=self)
        self.grid.itemDoubleClicked.connect(self._grid_open_item)
        self.grid.setContextMenuPolicy(Qt.CustomContextMenu)
        self.grid.customContextMenuRequested.connect(self._grid_context_menu)

        self.empty_label = QLabel("No notes found.\nClick + to add a new note.")
        self.empty_label.setObjectName("emptyLabel")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.hide()

        self.right.addWidget(self.table, 1)
        self.right.addWidget(self.grid, 1)
        self.right.addWidget(self.empty_label, 1)

        main.addWidget(self.folder_list)
        main.addLayout(self.right)
        self.layout.addLayout(main)

    def _refresh_center(self):
        """Show either the table or the grid."""
        is_list = (self.view_mode == "list")
        self.table.setVisible(is_list)
        self.grid.setVisible(not is_list)

    def _set_view_mode(self, mode: str):
        """Switch between list and grid views."""
        if mode == self.view_mode: return
        self.view_mode = mode
        self.btn_list.setChecked(mode == "list")
        self.btn_grid.setChecked(mode == "grid")
        self._refresh_center()
        self._refilter_notes()

    # ---------- footer ----------
    def _setup_footer(self):
        foot = QHBoxLayout()
        self.status_label = QLabel("Ready", objectName="statusText")
        foot.addWidget(self.status_label); foot.addStretch()
        self.layout.addLayout(foot)

        # back to home action
        self.btn_back_home = QPushButton()
        self.btn_back_home.setObjectName("iconBackButton")
        if BACK_ICON_PATH:
            self.btn_back_home.setIcon(QIcon(BACK_ICON_PATH))
        self.btn_back_home.setText(" Back to Home")
        self.btn_back_home.setIconSize(QSize(16, 16))
        self.btn_back_home.setFixedSize(750, 40)
        self.btn_back_home.setCursor(Qt.PointingHandCursor)
        self.btn_back_home.clicked.connect(self._go_home)
        self.layout.addWidget(self.btn_back_home, 0, Qt.AlignCenter)

    # ---------- db helpers ----------
    def _db(self):
        """Open a DB connection."""
        return get_connection()

    def _folder_exists(self, folder_id):
        """Check if a folder exists for this user; return (exists, name_or_None)."""
        if folder_id in (None, -1):
            return True, None
        conn = self._db(); cur = conn.cursor()
        cur.execute("SELECT name FROM folders WHERE id=? AND user_id=?", (folder_id, self.user_id))
        row = cur.fetchone(); conn.close()
        return (bool(row), row[0] if row else None)

    # ---------- sidebar build ----------
    def _refresh_folders(self):
        """Rebuild the sidebar: special rows, folders, and expanded notes."""
        self.folder_list.clear()
        self._add_special_item_row("All Notes", "all")
        self._add_special_item_row("Uncategorized", "uncat")

        conn = self._db(); cur = conn.cursor()
        cur.execute(
            "SELECT id, name, parent_id FROM folders WHERE user_id=? ORDER BY LOWER(name)",
            (self.user_id,)
        )
        rows = cur.fetchall(); conn.close()

        tree = {}
        for fid, name, parent in rows:
            tree.setdefault(parent, []).append((fid, name))

        def add_branch(parent_id, level=0):
            for fid, name in sorted(tree.get(parent_id, []), key=lambda t: t[1].lower()):
                self._add_folder_item_row(fid, name, level)

                if fid in self._expanded_folders:
                    # inline notes under expanded folder (scoped to user)
                    conn2 = self._db(); cur2 = conn2.cursor()
                    cur2.execute(
                        "SELECT id, title FROM notes WHERE folder_id=? AND user_id=? ORDER BY LOWER(title)",
                        (fid, self.user_id)
                    )
                    for nid, title in cur2.fetchall():
                        self._add_note_item_row(nid, title or "Untitled", level + 1)
                    conn2.close()

                    # recurse to children
                    add_branch(fid, level + 1)

        add_branch(None)
        self._select_sidebar_row()
        self._refresh_folder_row_styles()

    def _row_widget(self, left_pad_px, icon_path, text, click_cb, show_edit=False, edit_cb=None):
        """Build one sidebar row (folder/note/special) as a custom widget."""
        it = QListWidgetItem()
        w = QWidget(); w.setObjectName("folderRow")
        w.setProperty("selected", False)

        lay = QHBoxLayout(w)
        lay.setContentsMargins(6 + left_pad_px, 2, 4, 2)
        lay.setSpacing(6)

        # optional icon
        icon_w = 0
        if icon_path:
            ic = QLabel()
            pm = QPixmap(icon_path).scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            ic.setPixmap(pm)
            lay.addWidget(ic)
            icon_w = 20

        # clickable text
        lbl = _ClickLabel(text, click_cb); lbl.setObjectName("folderText")
        lbl.setToolTip(text)
        lay.addWidget(lbl, 1)

        # optional inline edit button
        edit_w = 0
        if show_edit and edit_cb:
            btn = QToolButton(w); btn.setObjectName("folderEdit")
            if EDIT_ICON_PATH: btn.setIcon(QIcon(EDIT_ICON_PATH))
            btn.setFixedSize(18, 18); btn.setAutoRaise(True); btn.setFocusPolicy(Qt.NoFocus)
            btn.clicked.connect(lambda _=False, b=btn: edit_cb(b))
            lay.addWidget(btn, 0, Qt.AlignRight)
            edit_w = 18

        # compute desired width so horizontal scrollbar can appear when needed
        fm = lbl.fontMetrics()
        text_px = fm.horizontalAdvance(text or "")
        extra = (6 + left_pad_px) + 4 + 6 + 10
        want_w = extra + icon_w + text_px + edit_w
        it.setSizeHint(QSize(max(110, want_w), 24))

        return it, w

    def _add_special_item_row(self, label, tag):
        """Add 'All Notes' / 'Uncategorized' rows."""
        def click():
            self.current_folder_id = None if tag == "all" else -1
            self.current_folder_name = None
            self._refilter_notes()
            self._refresh_folder_row_styles()
        it, w = self._row_widget(0, FOLDER_ICON_PATH, label, click, show_edit=False, edit_cb=None)
        it.setData(Qt.UserRole, ("special", tag))
        self.folder_list.addItem(it); self.folder_list.setItemWidget(it, w)

    def _add_folder_item_row(self, fid, name, level):
        """Add a folder row (with edit menu)."""
        it, w = self._row_widget(
            level * LEVEL_STEP, FOLDER_ICON_PATH, name,
            click_cb=lambda _=False, _fid=fid, _name=name: self._on_folder_row_clicked(_fid, _name),
            show_edit=True,
            edit_cb=lambda anchor_btn, _fid=fid, _name=name: self._folder_edit_menu(_fid, _name, anchor_btn)
        )
        it.setData(Qt.UserRole, ("folder", fid, name))
        self.folder_list.addItem(it); self.folder_list.setItemWidget(it, w)

    def _add_note_item_row(self, nid, title, level):
        """Add an inline note row under an expanded folder."""
        it, w = self._row_widget(
            level * LEVEL_STEP + NOTE_EXTRA_INDENT, FILE_ICON_PATH, title or "Untitled",
            click_cb=lambda _nid=nid: self._open_note_from_sidebar(_nid),
            show_edit=False, edit_cb=None
        )
        it.setData(Qt.UserRole, ("note", nid))
        self.folder_list.addItem(it); self.folder_list.setItemWidget(it, w)

    def _refresh_folder_row_styles(self):
        """Keep custom row widgets visually in sync with selection."""
        current = self.folder_list.currentItem()
        for i in range(self.folder_list.count()):
            it = self.folder_list.item(i)
            w = self.folder_list.itemWidget(it)
            if not w:
                continue
            selected = (it is current)
            if w.property("selected") != selected:
                w.setProperty("selected", selected)
            w.style().unpolish(w); w.style().polish(w); w.update()
            for lbl in w.findChildren(QLabel):
                lbl.style().unpolish(lbl); lbl.style().polish(lbl); lbl.update()

    def _rehome_and_delete_folder_tree(self, root_folder_id: int):
        """
        Move all notes that live in root_folder_id or any of its descendant folders
        to Uncategorized (folder_id = NULL), then delete that whole folder subtree.
        All operations are scoped to the current user.
        """
        conn = self._db()
        cur = conn.cursor()
        try:
            # Rehome notes in the entire subtree
            cur.execute(
                """
                WITH RECURSIVE sub(id) AS (
                    SELECT ?
                    UNION ALL
                    SELECT f.id
                    FROM folders f
                    JOIN sub s ON f.parent_id = s.id
                    WHERE f.user_id = ?
                )
                UPDATE notes
                SET folder_id = NULL
                WHERE user_id   = ?
                AND folder_id IN (SELECT id FROM sub)
                """,
                (root_folder_id, self.user_id, self.user_id)
            )

            # Delete the subtree of folders
            cur.execute(
                """
                WITH RECURSIVE sub(id) AS (
                    SELECT ?
                    UNION ALL
                    SELECT f.id
                    FROM folders f
                    JOIN sub s ON f.parent_id = s.id
                    WHERE f.user_id = ?
                )
                DELETE FROM folders
                WHERE user_id = ?
                AND id IN (SELECT id FROM sub)
                """,
                (root_folder_id, self.user_id, self.user_id)
            )

            conn.commit()
        finally:
            conn.close()


    def _on_folder_row_clicked(self, fid, name):
        """Expand/collapse a folder row and show its notes."""
        if fid in self._expanded_folders: self._expanded_folders.remove(fid)
        else: self._expanded_folders.add(fid)
        self.current_folder_id = fid
        self.current_folder_name = name
        self._refresh_folders()
        self._refilter_notes()

    def _open_note_from_sidebar(self, nid):
        """Open a note when clicked in the sidebar."""
        if self.on_add_note_clicked:
            self.on_add_note_clicked(nid)

    def _select_sidebar_row(self):
        """Ensure the correct sidebar row is selected."""
        want = ("special", "all") if self.current_folder_id is None else \
               (("special", "uncat") if self.current_folder_id == -1 else ("folder", self.current_folder_id, None))
        for i in range(self.folder_list.count()):
            data = self.folder_list.item(i).data(Qt.UserRole)
            if not data: continue
            if data[0] == "special" and data[1] == want[1]:
                self.folder_list.setCurrentRow(i); return
            if data[0] == "folder" and want[0] == "folder" and data[1] == want[1]:
                self.folder_list.setCurrentRow(i); return

    # ---------- data fetch ----------
    def _fetch_notes(self):
        """Query notes for the current folder and search text (scoped to user)."""
        q = (self.search_bar.text() or "").strip().lower()
        conn = self._db(); cur = conn.cursor()

        sql = "SELECT id, title, COALESCE(updated_at, created_at) AS modified_at FROM notes"
        args, where = [self.user_id], ["user_id=?"]

        if self.current_folder_id == -1:
            # uncategorized for this user; be robust if stray folder_id strings exist
            where.append("(folder_id IS NULL "
                         " OR TRIM(CAST(folder_id AS TEXT)) = '' "
                         " OR folder_id NOT IN (SELECT id FROM folders WHERE user_id=?))")
            args.append(self.user_id)
        elif self.current_folder_id not in (None, -1):
            where.append("folder_id = ?"); args.append(self.current_folder_id)

        if q:
            where.append("LOWER(title) LIKE ?"); args.append(f"%{q}%")

        sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY " + ("modified_at DESC, LOWER(title)" if self.sort_mode == 0 else "LOWER(title)")

        cur.execute(sql, args)
        rows = cur.fetchall()
        conn.close()
        return rows

    def _child_folders(self):
        """Get child folders under the current folder (or root), for this user."""
        if self.current_folder_id == -1: return []
        conn = self._db(); cur = conn.cursor()
        if self.current_folder_id is None:
            cur.execute("SELECT id, name FROM folders WHERE parent_id IS NULL AND user_id=? ORDER BY LOWER(name)",
                        (self.user_id,))
        else:
            cur.execute("SELECT id, name FROM folders WHERE parent_id=? AND user_id=? ORDER BY LOWER(name)",
                        (self.current_folder_id, self.user_id))
        out = cur.fetchall(); conn.close()
        return out

    # ---------- fill center ----------
    def _refilter_notes(self):
        """Refresh the list/grid with current filters and update status."""
        rows = self._fetch_notes()
        search_text = (self.search_bar.text() or "").strip().lower()

        if self.view_mode == "list":
            self._fill_table(rows)
            has_child = False
        else:
            children = self._child_folders()
            folders = [(fid, name) for fid, name in children if (not search_text) or (search_text in (name or "").lower())]
            self._fill_grid(rows, folder_rows=folders)
            has_child = len(folders) > 0

        self.status_label.setText(f"{len(rows)} note(s)")
        self._update_empty_state(empty_notes=(len(rows) == 0), has_child_folders=has_child)

    def _fill_table(self, rows):
        """Populate the table view."""
        self.table.setRowCount(0)
        for (nid, title, modified) in rows:
            title = title or "Untitled"
            d, t = self._split_dt(modified)
            dt_text = (d + "  " + t) if (d or t) else ""

            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setRowHeight(r, ROW_H)

            name_item = QTableWidgetItem(QIcon(FILE_ICON_PATH) if FILE_ICON_PATH else QIcon(), title)
            name_item.setData(Qt.UserRole, nid)
            name_item.setToolTip(title)
            self.table.setItem(r, 0, name_item)
            self.table.setItem(r, 1, QTableWidgetItem(dt_text))

            btn = QToolButton(objectName="rowActionsBtn")
            if DOTS_ICON_PATH: btn.setIcon(QIcon(DOTS_ICON_PATH))
            else: btn.setText("⋮")
            btn.setAutoRaise(True); btn.setFixedSize(20, 20)
            btn.clicked.connect(lambda _=False, i=nid, tt=title, b=btn: self._row_actions(i, tt, b))
            self.table.setCellWidget(r, 2, btn)

    def _fill_grid(self, note_rows, folder_rows=None):
        """Populate the grid view with folders and notes."""
        self.grid.clear()
        folders = self._child_folders() if folder_rows is None else folder_rows
        for fid, name in folders:
            it = QListWidgetItem(QIcon(FOLDER_ICON_PATH) if FOLDER_ICON_PATH else QIcon(), name or "Folder")
            it.setData(Qt.UserRole, ("folder", fid, name))
            it.setToolTip(name or "Folder")
            self.grid.addItem(it)
        for nid, title, modified in note_rows:
            title = title or "Untitled"
            d, t = self._split_dt(modified)
            it = QListWidgetItem(QIcon(FILE_ICON_PATH) if FILE_ICON_PATH else QIcon(), f"{title}\n{d} {t}")
            it.setData(Qt.UserRole, ("note", nid, title))
            it.setToolTip(title)
            self.grid.addItem(it)

    def _update_empty_state(self, empty_notes: bool, has_child_folders: bool = False):
        """Show an empty state message when needed."""
        searching = bool((self.search_bar.text() or "").strip())
        if self.view_mode == "grid":
            effective_empty = (not has_child_folders) and empty_notes
            self.grid.setVisible(not effective_empty)
            self.table.setVisible(False)
            self.empty_label.setVisible(effective_empty)
            if effective_empty:
                if searching:
                    self.empty_label.setText("No notes found.")
                elif self.current_folder_id == -1:
                    self.empty_label.setText("All your notes are within folders.\nNo notes are uncategorized.")
                else:
                    self.empty_label.setText("No notes found.\nClick + to add a new note.")
            return

        self.table.setVisible(not empty_notes)
        self.grid.setVisible(False)
        self.empty_label.setVisible(empty_notes)
        if empty_notes:
            if searching:
                self.empty_label.setText("No notes found.")
            elif self.current_folder_id == -1:
                self.empty_label.setText("All your notes are within folders.\nNo notes are uncategorized.")
            else:
                self.empty_label.setText("No notes found.\nClick + to add a new note.")

    @staticmethod
    def _split_dt(ts):
        """Return (YYYY-MM-DD, HH:MM:SS) from various timestamp shapes."""
        if not ts: return ("", "")
        try:
            d, t = (ts.split("T", 1) if "T" in ts else ts.split(" ", 1))
            return (d, t[:8])
        except Exception:
            try:
                dt = datetime.fromisoformat(ts)
                return (dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M:%S"))
            except Exception:
                return (ts[:10], "")

    # ---------- interactions ----------
    def _on_sidebar_click(self, item: QListWidgetItem):
        """Handle clicks on sidebar rows."""
        data = item.data(Qt.UserRole)
        if not data: return
        kind = data[0]
        if kind == "note":
            if self.on_add_note_clicked: self.on_add_note_clicked(data[1])
        elif kind == "special":
            self.current_folder_id = None if data[1] == "all" else -1
            self.current_folder_name = None
            self._refilter_notes(); self._refresh_folder_row_styles()
        elif kind == "folder":
            self._on_folder_row_clicked(data[1], data[2])

    def _folder_context_menu(self, pos: QPoint):
        """Right-click menu on a folder row."""
        it = self.folder_list.itemAt(pos)
        if not it: return
        data = it.data(Qt.UserRole)
        if not data or data[0] != "folder": return
        fid, name = data[1], data[2]
        self._folder_edit_menu(fid, name, None)

    def _folder_edit_menu(self, folder_id, name, anchor_btn):
        """Context menu for folder actions."""
        m = QMenu(self); m.setObjectName("popupMenu")
        m.addAction("Rename", lambda: self._rename_folder(folder_id, name))
        m.addAction("Delete", lambda: self._delete_folder(folder_id, name))
        m.exec_(anchor_btn.mapToGlobal(anchor_btn.rect().bottomLeft()) if anchor_btn else self.cursor().pos())

    def _rename_folder(self, folder_id, old_name):
        """Rename a folder (limit 50 chars), scoped to user."""
        name, ok = QInputDialog.getText(self, "Rename Folder", "Folder name:", text=old_name or "")
        if not (ok and name.strip()): return
        new_name = name.strip()
        if len(new_name) > 50:
            QMessageBox.warning(self, "Name too long", "Folder name must be 50 characters or fewer.")
            return
        conn = self._db(); cur = conn.cursor()
        cur.execute("UPDATE folders SET name=? WHERE id=? AND user_id=?", (new_name, folder_id, self.user_id))
        conn.commit(); conn.close()
        QMessageBox.information(self, "Folder Renamed", f"You renamed the folder into '{new_name}'.")
        self._refresh_folders(); self._refilter_notes()

    def _delete_folder(self, folder_id, folder_name):
        """Delete a folder (and its descendants) and move its notes to Uncategorized."""
        if QMessageBox.question(
            self,
            "Delete Folder",
            f"Delete folder '{folder_name}'?\nAll notes inside (including subfolders) will move to Uncategorized.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        ) != QMessageBox.Yes:
            return

        # Rehome notes and delete the whole subtree for this user
        self._rehome_and_delete_folder_tree(folder_id)

        QMessageBox.information(self, "Folder Deleted", f"You deleted '{folder_name}' folder.")

        # Clean up UI state
        self._expanded_folders.discard(folder_id)
        if self.current_folder_id == folder_id:
            self.current_folder_id = None
            self.current_folder_name = None

        self._refresh_folders()
        self._refilter_notes()


    # ---------- add / import ----------
    def _add_subfolder(self, parent_id):
        """Create a new folder (nested if a folder is selected) for this user."""
        name, ok = QInputDialog.getText(self, "New Folder", "Folder name:")
        if not (ok and name.strip()): return
        conn = self._db(); cur = conn.cursor()
        cur.execute(
            "INSERT INTO folders(name, parent_id, user_id) VALUES(?, ?, ?)",
            (name.strip(), None if parent_id in (None, -1) else parent_id, self.user_id)
        )
        conn.commit(); conn.close()
        self._refresh_folders(); self._refilter_notes()

    def _add_note_here(self, folder_id):
        """Create a new note in the current folder (or uncategorized)."""
        target = None if folder_id in (None, -1) else folder_id
        if target is not None:
            exists, _ = self._folder_exists(target)
            if not exists:
                shown = self.current_folder_name or "Selected folder"
                QMessageBox.warning(self, "Folder Missing",
                                    f"You can’t add this to the folder '{shown}' because it no longer exists.")
                target = None
        conn = self._db(); cur = conn.cursor()
        cur.execute(
            "INSERT INTO notes(folder_id, title, content, user_id) VALUES(?,?,?,?)",
            (target, "Untitled", "", self.user_id)
        )
        nid = cur.lastrowid; conn.commit(); conn.close()

        self._refresh_folders()
        self._refilter_notes()

        if self.on_add_note_clicked:
            self.on_add_note_clicked(nid)

    def _import_note(self, folder_id):
        """Import a .txt file as a new note in the current folder."""
        path, _ = QFileDialog.getOpenFileName(self, "Import Note", "", "Text (*.txt)")
        if not path: return
        base = os.path.basename(path); title = os.path.splitext(base)[0]
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception as e:
            QMessageBox.critical(self, "Import", f"Failed to read TXT:\n{e}")
            return

        target = None if folder_id in (None, -1) else folder_id
        if target is not None:
            exists, _ = self._folder_exists(target)
            if not exists:
                shown = self.current_folder_name or "Selected folder"
                QMessageBox.warning(self, "Folder Missing",
                                    f"You can’t add this to the folder '{shown}' because it no longer exists.")
                target = None

        conn = self._db(); cur = conn.cursor()
        cur.execute(
            "INSERT INTO notes(folder_id, title, content, user_id) VALUES (?,?,?,?)",
            (target, title, content, self.user_id)
        )
        nid = cur.lastrowid; conn.commit(); conn.close()

        self._refresh_folders()
        self._refilter_notes()

        QMessageBox.information(self, "Imported", "Note added. Opening…")
        if self.on_add_note_clicked: self.on_add_note_clicked(nid)

    # ---------- table & grid actions ----------
    def _open_row_by_doubleclick(self, row, _col):
        """Open a note by double-clicking its row."""
        item = self.table.item(row, 0)
        if not item: return
        nid = item.data(Qt.UserRole)
        if nid and self.on_add_note_clicked: self.on_add_note_clicked(nid)

    def _row_actions(self, note_id, title, anchor_btn):
        """Context menu for a note row in table view."""
        m = QMenu(self); m.setObjectName("rowMenu")
        a_open   = m.addAction("Open")
        a_move   = m.addAction("Add to folder…")
        a_rename = m.addAction("Rename")
        a_delete = m.addAction("Delete")
        a_export_txt  = m.addAction("Export as TXT")
        act = m.exec_(anchor_btn.mapToGlobal(anchor_btn.rect().bottomLeft()))
        if not act: return
        if   act == a_open and self.on_add_note_clicked: self.on_add_note_clicked(note_id)
        elif act == a_move:   self._note_move_to_folder(note_id)
        elif act == a_rename: self._note_rename(note_id, title)
        elif act == a_delete: self._note_delete(note_id, title)
        elif act == a_export_txt: self._note_export(note_id, title)

    def _grid_open_item(self, item: QListWidgetItem):
        """Open folder or note from grid view by double-click."""
        data = item.data(Qt.UserRole)
        if not data: return
        if data[0] == "folder":
            self.current_folder_id, self.current_folder_name = data[1], data[2]
            self._refilter_notes()
        elif data[0] == "note" and self.on_add_note_clicked:
            self.on_add_note_clicked(data[1])

    def _grid_context_menu(self, pos):
        """Right-click menu for grid items (folders and notes)."""
        item = self.grid.itemAt(pos)
        if not item: return
        data = item.data(Qt.UserRole)
        if not data: return
        gpos = self.grid.viewport().mapToGlobal(pos)
        if data[0] == "folder":
            fid, name = data[1], data[2]
            m = QMenu(self); m.setObjectName("rowMenu")
            a_open   = m.addAction("Open")
            a_rename = m.addAction("Rename")
            a_del    = m.addAction("Delete")
            act = m.exec_(gpos)
            if   act == a_open:   self.current_folder_id, self.current_folder_name = fid, name; self._refilter_notes()
            elif act == a_rename: self._rename_folder(fid, name)
            elif act == a_del:    self._delete_folder(fid, name)
        else:
            nid, title = data[1], data[2]
            m = QMenu(self); m.setObjectName("rowMenu")
            a_open   = m.addAction("Open")
            a_move   = m.addAction("Add to folder…")
            a_rename = m.addAction("Rename")
            a_del    = m.addAction("Delete")
            a_export_txt  = m.addAction("Export as TXT")
            act = m.exec_(gpos)
            if   act == a_open and self.on_add_note_clicked: self.on_add_note_clicked(nid)
            elif act == a_move:   self._note_move_to_folder(nid)
            elif act == a_rename: self._note_rename(nid, title)
            elif act == a_del:    self._note_delete(nid, title)
            elif act == a_export_txt: self._note_export(nid, title)

    # ---------- note ops ----------
    def _note_move_to_folder(self, note_id):
        """Move a note into a chosen folder (this user)."""
        res = self._choose_folder_dialog()
        if res is None:
            return
        fid, fname = res
        exists, db_name = self._folder_exists(fid)
        if not exists:
            shown = fname or db_name or "Selected folder"
            QMessageBox.warning(self, "Folder Missing",
                                f"You can’t add this to the folder '{shown}' because it no longer exists.")
            return
        conn = self._db(); cur = conn.cursor()
        cur.execute("UPDATE notes SET folder_id=? WHERE id=? AND user_id=?", (fid, note_id, self.user_id))
        conn.commit(); conn.close()
        self._refresh_folders()
        self._refilter_notes()

    def _choose_folder_dialog(self):
        """Show a simple folder picker dialog and return (id, name) or None."""
        conn = self._db(); cur = conn.cursor()
        cur.execute("SELECT id, name, parent_id FROM folders WHERE user_id=?", (self.user_id,))
        rows = cur.fetchall(); conn.close()

        from collections import defaultdict
        tree = defaultdict(list)
        for fid, name, parent in rows: tree[parent].append((fid, name))

        flat = []
        def walk(parent=None, level=0):
            for fid, name in sorted(tree.get(parent, []), key=lambda t: t[1].lower()):
                flat.append((fid, name, ("    " * level) + (name or "")))
                walk(fid, level+1)
        walk(None)
        if not flat:
            QMessageBox.information(self, "Add to folder", "No folders available. Create a folder first.")
            return None

        labels = [label for _fid, _name, label in flat]
        choice, ok = QInputDialog.getItem(self, "Add to folder", "Choose folder:", labels, 0, False)
        if not ok: return None
        idx = labels.index(choice)
        fid, name, _ = flat[idx]
        return (fid, name)

    def _note_rename(self, note_id, old_title):
        """Rename a note (limit 50 chars), scoped to user."""
        name, ok = QInputDialog.getText(self, "Rename Note", "New title:", text=old_title or "")
        if not (ok and name.strip()): return
        new_title = name.strip()
        if len(new_title) > 50:
            QMessageBox.warning(self, "Title too long", "Note title must be 50 characters or fewer.")
            return
        conn = self._db(); cur = conn.cursor()
        cur.execute("UPDATE notes SET title=? WHERE id=? AND user_id=?", (new_title, note_id, self.user_id))
        conn.commit(); conn.close()
        QMessageBox.information(self, "Note Renamed", f"You renamed the note into '{new_title}'.")
        self._refresh_folders()
        self._refilter_notes()

    def _note_delete(self, note_id, title):
        """Delete a note (this user) and notify listeners to close any open editor tab."""
        shown = title or "Untitled"
        if QMessageBox.question(self, "Delete Note", f"Delete '{shown}'?",
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        conn = self._db(); cur = conn.cursor()
        cur.execute("DELETE FROM notes WHERE id=? AND user_id=?", (note_id, self.user_id))
        conn.commit(); conn.close()
        QMessageBox.information(self, "Note Deleted", f"You deleted '{shown}' note.")
        self._refresh_folders()
        self._refilter_notes()

        try:
            self.noteDeleted.emit(note_id)
        except Exception:
            pass
        cb = getattr(self, "on_note_deleted", None)
        if callable(cb):
            try:
                cb(note_id)
            except Exception:
                pass

    def _note_export(self, note_id, fallback_title):
        """Export a note as TXT only, enforcing ownership."""
        conn = self._db(); cur = conn.cursor()
        cur.execute("SELECT user_id, title, content FROM notes WHERE id=?", (note_id,))
        row = cur.fetchone(); conn.close()

        if not row or row[0] != self.user_id:
            QMessageBox.warning(self, "Access Denied", "You don't have permission to export this note.")
            return

        title = (row[1] or fallback_title or "Untitled")
        content = (row[2] or "")

        path, _ = QFileDialog.getSaveFileName(self, "Export TXT", f"{title}.txt", "Text Files (*.txt)")
        if not path: return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(title + "\n\n" + content)
            QMessageBox.information(self, "Export", "TXT file saved.")
        except Exception as e:
            QMessageBox.critical(self, "Export", f"Failed to save TXT:\n{e}")

    # ---------- navigation ----------
    def _go_home(self):
        """Go back to the home screen if a callback is provided."""
        if callable(getattr(self, "on_back_home", None)):
            self.on_back_home()

    # ---------- optional cleanup ----------
    def cleanup(self):
        """Call when closing the dashboard to release references (optional)."""
        try:
            self.folder_list.clear()
            self.table.setRowCount(0)
            self.grid.clear()
            self._expanded_folders.clear()
            self.current_folder_id = None
            self.current_folder_name = None
        except Exception as e:
            print(f"Error cleaning up dashboard: {e}")
