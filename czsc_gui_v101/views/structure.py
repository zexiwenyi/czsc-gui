"""缠论结构分析页面"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QSplitter, QFrame, QComboBox, QSlider
)
from PyQt6.QtCore import Qt
from config import COLORS, KLINE_COLORS
from core.czsc_engine import CzscEngine
from widgets.kline_widget import KlineWidget
from czsc import Freq


class StructureView(QWidget):
    """缠论结构分析 - 分型/笔/K线图"""

    def __init__(self, data_loader, parent=None):
        super().__init__(parent)
        self.data_loader = data_loader
        self.engine = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(10)

        # 标题行
        header = QHBoxLayout()
        title = QLabel("缠论结构分析")
        title.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {COLORS['accent']};")
        header.addWidget(title)
        header.addStretch()

        # K线数量选择
        header.addWidget(QLabel("K线数量:"))
        self.bar_slider = QSlider(Qt.Orientation.Horizontal)
        self.bar_slider.setRange(50, 500)
        self.bar_slider.setValue(200)
        self.bar_slider.setFixedWidth(150)
        self.bar_label = QLabel("200")
        self.bar_label.setStyleSheet(f"color: {COLORS['text_dim']};")
        self.bar_slider.valueChanged.connect(lambda v: self.bar_label.setText(str(v)))
        header.addWidget(self.bar_slider)
        header.addWidget(self.bar_label)
        layout.addLayout(header)

        # 统计摘要
        self.stats_frame = QFrame()
        self.stats_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border-radius: 8px;
                padding: 8px;
            }}
        """)
        self.stats_layout = QHBoxLayout(self.stats_frame)
        self.stats_layout.setSpacing(20)
        layout.addWidget(self.stats_frame)

        # 主内容区：上方K线图，下方数据表
        splitter = QSplitter(Qt.Orientation.Vertical)

        # K线图
        self.kline_widget = KlineWidget()
        splitter.addWidget(self.kline_widget)

        # 下方：分型表 + 笔表
        table_splitter = QSplitter(Qt.Orientation.Horizontal)

        # 分型表
        fx_frame = QFrame()
        fx_layout = QVBoxLayout(fx_frame)
        fx_title = QLabel("分型列表")
        fx_title.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {COLORS['text']};")
        fx_layout.addWidget(fx_title)

        self.fx_table = QTableWidget()
        self.fx_table.setColumnCount(3)
        self.fx_table.setHorizontalHeaderLabels(["时间", "类型", "价格"])
        self.fx_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.fx_table.setStyleSheet(self._table_style())
        fx_layout.addWidget(self.fx_table)
        table_splitter.addWidget(fx_frame)

        # 笔表
        bi_frame = QFrame()
        bi_layout = QVBoxLayout(bi_frame)
        bi_title = QLabel("笔列表")
        bi_title.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {COLORS['text']};")
        bi_layout.addWidget(bi_title)

        self.bi_table = QTableWidget()
        self.bi_table.setColumnCount(7)
        self.bi_table.setHorizontalHeaderLabels(["序号", "方向", "起点", "终点", "最高", "最低", "幅度"])
        self.bi_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.bi_table.setStyleSheet(self._table_style())
        bi_layout.addWidget(self.bi_table)
        table_splitter.addWidget(bi_frame)

        splitter.addWidget(table_splitter)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter, stretch=1)

    def update_data(self, df, symbol):
        """更新分析数据"""
        if df is None:
            return

        n_bars = self.bar_slider.value()
        filtered = self.data_loader.filter_symbol(df, symbol, n_bars)
        if filtered is None or len(filtered) == 0:
            return

        # 构建CZSC引擎
        self.engine = CzscEngine(filtered, freq=Freq.F1)

        # 更新统计摘要
        self._update_stats()

        # 更新K线图
        bar_data = self.engine.get_bar_data()
        self.kline_widget.plot(
            bar_data,
            bi_list=self.engine.bi_list,
            fx_list=self.engine.fx_list
        )

        # 更新分型表
        fx_data = self.engine.get_fx_data()
        self._fill_fx_table(fx_data)

        # 更新笔表
        bi_data = self.engine.get_bi_data()
        self._fill_bi_table(bi_data)

    def _update_stats(self):
        # 清除旧统计
        while self.stats_layout.count():
            item = self.stats_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        summary = self.engine.get_bi_summary()
        items = [
            ("K线数", str(self.engine.n_bars)),
            ("分型数", str(len(self.engine.fx_list))),
            ("笔数", str(summary.get("笔总数", 0))),
            ("向上笔", str(summary.get("向上笔", 0))),
            ("向下笔", str(summary.get("向下笔", 0))),
            ("平均幅度", str(summary.get("平均幅度", 0))),
            ("最大幅度", str(summary.get("最大幅度", 0))),
        ]
        for label, value in items:
            w = QLabel(f"<b style='color:{COLORS['accent']}'>{value}</b>  <span style='color:{COLORS['text_dim']}'>{label}</span>")
            w.setStyleSheet(f"font-size: 13px;")
            self.stats_layout.addWidget(w)

        self.stats_layout.addStretch()

    def _fill_fx_table(self, fx_data):
        self.fx_table.setRowCount(len(fx_data))
        for i, fx in enumerate(fx_data):
            self.fx_table.setItem(i, 0, QTableWidgetItem(fx["时间"][:16]))
            type_item = QTableWidgetItem(fx["类型"])
            if "顶" in fx["类型"]:
                type_item.setForeground(Qt.GlobalColor.red)
            else:
                type_item.setForeground(Qt.GlobalColor.cyan)
            self.fx_table.setItem(i, 1, type_item)
            self.fx_table.setItem(i, 2, QTableWidgetItem(str(fx["价格"])))

    def _fill_bi_table(self, bi_data):
        self.bi_table.setRowCount(len(bi_data))
        for i, bi in enumerate(bi_data):
            self.bi_table.setItem(i, 0, QTableWidgetItem(str(bi["序号"])))
            dir_item = QTableWidgetItem(bi["方向"])
            if bi["方向"] == "向上":
                dir_item.setForeground(Qt.GlobalColor.red)
            else:
                dir_item.setForeground(Qt.GlobalColor.darkCyan)
            self.bi_table.setItem(i, 1, dir_item)
            self.bi_table.setItem(i, 2, QTableWidgetItem(bi["起点时间"][:16]))
            self.bi_table.setItem(i, 3, QTableWidgetItem(bi["终点时间"][:16]))
            self.bi_table.setItem(i, 4, QTableWidgetItem(str(bi["最高"])))
            self.bi_table.setItem(i, 5, QTableWidgetItem(str(bi["最低"])))
            self.bi_table.setItem(i, 6, QTableWidgetItem(str(bi["幅度"])))

    def _table_style(self):
        return f"""
            QTableWidget {{
                background-color: {COLORS['surface']};
                color: {COLORS['text']};
                border: none;
                border-radius: 6px;
                gridline-color: {COLORS['sidebar_hover']};
            }}
            QHeaderView::section {{
                background-color: {COLORS['sidebar']};
                color: {COLORS['text_dim']};
                padding: 6px;
                border: none;
                font-weight: bold;
            }}
        """
