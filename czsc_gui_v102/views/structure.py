"""缠论结构分析页面 V1.02 - 集成通达信原生K线"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QSplitter, QFrame, QComboBox,
    QSlider, QLineEdit, QPushButton, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from config import COLORS, KLINE_COLORS, TDX_DEFAULT_STOCK, TDX_DEFAULT_PERIOD, TDX_DEFAULT_COUNT, TDX_PERIODS
from core.czsc_engine import CzscEngine
from widgets.kline_widget import KlineWidget
from czsc import Freq


class _TdxWorker(QObject):
    """TDX异步操作信号桥接"""
    connected = pyqtSignal(bool, str)    # (success, message)
    data_ready = pyqtSignal(object, str) # (df, message)
    pushed = pyqtSignal(bool, str)       # (success, message)


class StructureView(QWidget):
    """缠论结构分析 - 分型/笔/K线图 + 通达信原生图表联动"""

    def __init__(self, data_loader, tdx_engine=None, parent=None):
        super().__init__(parent)
        self.data_loader = data_loader
        self.tdx_engine = tdx_engine
        self.engine = None
        self._worker = _TdxWorker()
        self._worker.connected.connect(self._on_tdx_connected)
        self._worker.data_ready.connect(self._on_tdx_data_ready)
        self._worker.pushed.connect(self._on_tdx_pushed)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(10)

        # === 顶部：标题 + 数据源切换 ===
        header = QHBoxLayout()
        title = QLabel("缠论结构分析")
        title.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {COLORS['accent']};")
        header.addWidget(title)
        header.addStretch()

        # 数据源切换
        header.addWidget(self._lbl("数据源:"))
        self.source_combo = QComboBox()
        self.source_combo.addItems(["CSV文件", "通达信实时"])
        self.source_combo.setFixedWidth(110)
        self.source_combo.setStyleSheet(self._combo_style())
        self.source_combo.currentIndexChanged.connect(self._on_source_changed)
        header.addWidget(self.source_combo)

        # K线数量
        header.addWidget(self._lbl("K线:"))
        self.bar_slider = QSlider(Qt.Orientation.Horizontal)
        self.bar_slider.setRange(50, 500)
        self.bar_slider.setValue(TDX_DEFAULT_COUNT)
        self.bar_slider.setFixedWidth(120)
        self.bar_label = QLabel(str(TDX_DEFAULT_COUNT))
        self.bar_label.setStyleSheet(f"color: {COLORS['text_dim']};")
        self.bar_slider.valueChanged.connect(lambda v: self.bar_label.setText(str(v)))
        header.addWidget(self.bar_slider)
        header.addWidget(self.bar_label)
        layout.addLayout(header)

        # === 通达信控制面板 ===
        self.tdx_panel = self._build_tdx_panel()
        layout.addWidget(self.tdx_panel)

        # === 统计摘要 ===
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

        # === 主内容区 ===
        splitter = QSplitter(Qt.Orientation.Vertical)

        # K线图（pyqtgraph备用）
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

    # ---- 通达信控制面板 ----
    def _build_tdx_panel(self):
        panel = QFrame()
        panel.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border-radius: 8px;
                padding: 6px;
            }}
        """)
        row = QHBoxLayout(panel)
        row.setContentsMargins(12, 6, 12, 6)
        row.setSpacing(10)

        # 股票代码
        row.addWidget(self._lbl("代码:"))
        self.stock_input = QLineEdit(TDX_DEFAULT_STOCK)
        self.stock_input.setFixedWidth(120)
        self.stock_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS['bg']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['sidebar_hover']};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 13px;
            }}
        """)
        row.addWidget(self.stock_input)

        # K线周期
        row.addWidget(self._lbl("周期:"))
        self.period_combo = QComboBox()
        self.period_combo.addItems(TDX_PERIODS)
        self.period_combo.setCurrentText(TDX_DEFAULT_PERIOD)
        self.period_combo.setFixedWidth(80)
        self.period_combo.setStyleSheet(self._combo_style())
        row.addWidget(self.period_combo)

        # 分隔
        row.addSpacing(10)

        # 连接TDX按钮
        self.connect_btn = QPushButton("连接通达信")
        self.connect_btn.setFixedSize(100, 30)
        self.connect_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.connect_btn.setStyleSheet(self._btn_style(COLORS['accent']))
        self.connect_btn.clicked.connect(self._on_connect_tdx)
        row.addWidget(self.connect_btn)

        # 获取数据按钮
        self.fetch_btn = QPushButton("获取数据")
        self.fetch_btn.setFixedSize(80, 30)
        self.fetch_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.fetch_btn.setStyleSheet(self._btn_style(COLORS['yellow']))
        self.fetch_btn.clicked.connect(self._on_fetch_tdx)
        self.fetch_btn.setEnabled(False)
        row.addWidget(self.fetch_btn)

        # 推送到TDX按钮
        self.push_btn = QPushButton("推送到TDX")
        self.push_btn.setFixedSize(100, 30)
        self.push_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.push_btn.setStyleSheet(self._btn_style(COLORS['green']))
        self.push_btn.clicked.connect(self._on_push_tdx)
        self.push_btn.setEnabled(False)
        row.addWidget(self.push_btn)

        # 跳转TDX按钮
        self.jump_btn = QPushButton("跳转K线")
        self.jump_btn.setFixedSize(80, 30)
        self.jump_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.jump_btn.setStyleSheet(self._btn_style(COLORS['text_dim']))
        self.jump_btn.clicked.connect(self._on_jump_tdx)
        self.jump_btn.setEnabled(False)
        row.addWidget(self.jump_btn)

        # 状态标签
        row.addStretch()
        self.tdx_status = QLabel("未连接")
        self.tdx_status.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 12px;")
        row.addWidget(self.tdx_status)

        # 初始隐藏（CSV模式时不显示TDX面板）
        panel.setVisible(False)
        return panel

    # ---- 事件处理 ----
    def _on_source_changed(self, index):
        """切换数据源"""
        is_tdx = index == 1
        self.tdx_panel.setVisible(is_tdx)
        if is_tdx and self.tdx_engine and self.tdx_engine.is_connected:
            self.tdx_status.setText("已连接")
            self.tdx_status.setStyleSheet(f"color: {COLORS['green']}; font-size: 12px;")

    def _on_connect_tdx(self):
        """连接通达信"""
        if not self.tdx_engine:
            self.tdx_status.setText("引擎不可用")
            self.tdx_status.setStyleSheet(f"color: {COLORS['red']}; font-size: 12px;")
            return

        if self.tdx_engine.is_connected:
            self.tdx_status.setText("已连接")
            self.tdx_status.setStyleSheet(f"color: {COLORS['green']}; font-size: 12px;")
            self.fetch_btn.setEnabled(True)
            self.push_btn.setEnabled(True)
            self.jump_btn.setEnabled(True)
            return

        self.connect_btn.setEnabled(False)
        self.tdx_status.setText("连接中...")
        self.tdx_status.setStyleSheet(f"color: {COLORS['yellow']}; font-size: 12px;")

        import threading
        def _do():
            ok = self.tdx_engine.initialize()
            msg = "连接成功" if ok else (self.tdx_engine._init_error or "连接失败")
            self._worker.connected.emit(ok, msg)

        threading.Thread(target=_do, daemon=True).start()

    def _on_tdx_connected(self, ok, msg):
        """连接结果回调"""
        self.connect_btn.setEnabled(True)
        if ok:
            self.tdx_status.setText("已连接")
            self.tdx_status.setStyleSheet(f"color: {COLORS['green']}; font-size: 12px;")
            self.fetch_btn.setEnabled(True)
            self.push_btn.setEnabled(True)
            self.jump_btn.setEnabled(True)
        else:
            self.tdx_status.setText(f"失败: {msg}")
            self.tdx_status.setStyleSheet(f"color: {COLORS['red']}; font-size: 12px;")

    def _on_fetch_tdx(self):
        """从通达信获取K线数据并做CZSC分析"""
        if not self.tdx_engine or not self.tdx_engine.is_connected:
            return

        stock_code = self.stock_input.text().strip()
        period = self.period_combo.currentText()
        count = self.bar_slider.value()

        if not stock_code:
            return

        self.tdx_status.setText("获取数据中...")
        self.tdx_status.setStyleSheet(f"color: {COLORS['yellow']}; font-size: 12px;")
        self.fetch_btn.setEnabled(False)

        import threading
        def _do():
            df = self.tdx_engine.get_kline(stock_code, period, count)
            msg = f"获取 {len(df)} 根K线" if df is not None else "获取失败"
            self._worker.data_ready.emit(df, msg)

        threading.Thread(target=_do, daemon=True).start()

    def _on_tdx_data_ready(self, df, msg):
        """数据获取完成"""
        self.fetch_btn.setEnabled(True)
        if df is None or len(df) == 0:
            self.tdx_status.setText("无数据")
            self.tdx_status.setStyleSheet(f"color: {COLORS['red']}; font-size: 12px;")
            return

        self.tdx_status.setText(f"{msg} | 分析中...")

        # 映射周期到Freq
        freq_map = {
            '1m': Freq.F1, '5m': Freq.F5, '15m': Freq.F15,
            '30m': Freq.F30, '1h': Freq.F60, '1d': Freq.D,
        }
        period = self.period_combo.currentText()
        freq = freq_map.get(period, Freq.F1)

        # CZSC分析
        self.engine = CzscEngine(df, freq=freq)
        self._update_stats()

        # 更新本地K线图
        bar_data = self.engine.get_bar_data()
        self.kline_widget.plot(
            bar_data,
            bi_list=self.engine.bi_list,
            fx_list=self.engine.fx_list
        )

        # 更新表格
        fx_data = self.engine.get_fx_data()
        self._fill_fx_table(fx_data)
        bi_data = self.engine.get_bi_data()
        self._fill_bi_table(bi_data)

        stock_code = self.stock_input.text().strip()
        n_bi = len(self.engine.bi_list)
        n_fx = len(self.engine.fx_list)
        self.tdx_status.setText(f"{msg} | {n_bi}笔 {n_fx}分型")
        self.tdx_status.setStyleSheet(f"color: {COLORS['green']}; font-size: 12px;")
        self.push_btn.setEnabled(True)

    def _on_push_tdx(self):
        """推送CZSC分析结果到通达信原生K线"""
        if not self.tdx_engine or not self.tdx_engine.is_connected:
            return
        if not self.engine:
            self.tdx_status.setText("先获取数据")
            return

        stock_code = self.stock_input.text().strip()
        bar_data = self.engine.get_bar_data()

        from core.tdx_chart_push import push_to_tdx
        self.push_btn.setEnabled(False)
        self.tdx_status.setText("推送中...")
        self.tdx_status.setStyleSheet(f"color: {COLORS['yellow']}; font-size: 12px;")

        import threading
        def _do():
            ok, msg = push_to_tdx(
                self.tdx_engine, stock_code,
                bar_data, self.engine.bi_list, self.engine.fx_list
            )
            self._worker.pushed.emit(ok, msg)

        threading.Thread(target=_do, daemon=True).start()

    def _on_tdx_pushed(self, ok, msg):
        """推送结果回调"""
        self.push_btn.setEnabled(True)
        if ok:
            self.tdx_status.setText(msg)
            self.tdx_status.setStyleSheet(f"color: {COLORS['green']}; font-size: 12px;")
        else:
            self.tdx_status.setText(f"推送失败: {msg}")
            self.tdx_status.setStyleSheet(f"color: {COLORS['red']}; font-size: 12px;")

    def _on_jump_tdx(self):
        """跳转通达信K线界面"""
        if not self.tdx_engine or not self.tdx_engine.is_connected:
            return
        stock_code = self.stock_input.text().strip()
        if not stock_code:
            return
        # 通达信跳转URL格式
        period = self.period_combo.currentText()
        period_map = {'1m': '0', '5m': '1', '15m': '2', '30m': '3', '1h': '4', '1d': '5'}
        p = period_map.get(period, '0')
        url = f"tdx://open?func=KLine&code={stock_code}&period={p}"
        self.tdx_engine.exec_to_tdx(url)

    # ---- CSV数据更新（保留V1.01兼容） ----
    def update_data(self, df, symbol):
        """CSV模式更新分析数据"""
        if df is None:
            return

        n_bars = self.bar_slider.value()
        filtered = self.data_loader.filter_symbol(df, symbol, n_bars)
        if filtered is None or len(filtered) == 0:
            return

        self.engine = CzscEngine(filtered, freq=Freq.F1)
        self._update_stats()

        bar_data = self.engine.get_bar_data()
        self.kline_widget.plot(
            bar_data,
            bi_list=self.engine.bi_list,
            fx_list=self.engine.fx_list
        )

        fx_data = self.engine.get_fx_data()
        self._fill_fx_table(fx_data)
        bi_data = self.engine.get_bi_data()
        self._fill_bi_table(bi_data)

    # ---- 统计摘要 ----
    def _update_stats(self):
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

    # ---- 表格填充 ----
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

    # ---- 样式辅助 ----
    def _lbl(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 13px;")
        return lbl

    def _btn_style(self, color):
        return f"""
            QPushButton {{
                background-color: {color};
                color: {COLORS['bg']};
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 12px;
            }}
            QPushButton:hover {{ opacity: 0.85; }}
            QPushButton:disabled {{
                background-color: {COLORS['sidebar_hover']};
                color: {COLORS['text_dim']};
            }}
        """

    def _combo_style(self):
        return f"""
            QComboBox {{
                background-color: {COLORS['surface']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['sidebar_hover']};
                border-radius: 5px;
                padding: 4px 8px;
                font-size: 13px;
            }}
            QComboBox::drop-down {{ border: none; width: 20px; }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS['surface']};
                color: {COLORS['text']};
                selection-background-color: {COLORS['sidebar_hover']};
                border: none;
            }}
        """

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
