"""
CZSC 缠论量化分析平台 - 主入口
"""
import sys
import os

# 确保项目路径在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QStackedWidget, QComboBox, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QIcon

from config import COLORS, WINDOW_TITLE, WINDOW_WIDTH, WINDOW_HEIGHT, SIDEBAR_WIDTH, VERSION
from core.data_loader import DataLoader
from core.tdx_engine import TdxEngine
from views.overview import OverviewView
from views.structure import StructureView


class Sidebar(QFrame):
    """左侧导航栏"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(SIDEBAR_WIDTH)
        self.setStyleSheet(f"""
            Sidebar {{
                background-color: {COLORS['sidebar']};
                border: none;
            }}
        """)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 15, 0, 15)
        self.layout.setSpacing(2)

        # Logo
        logo = QLabel(f"  CZSC 缠论平台\n  {VERSION}")
        logo.setStyleSheet(f"""
            font-size: 16px;
            font-weight: bold;
            color: {COLORS['accent']};
            padding: 10px 15px 15px 15px;
            line-height: 1.3;
        """)
        self.layout.addWidget(logo)

        # 分割线
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background-color: {COLORS['sidebar_hover']}; max-height: 1px; margin: 5px 15px;")
        self.layout.addWidget(sep)

        # 导航按钮列表
        self.buttons = []
        self._current_index = 0

    def add_item(self, icon_text, label, callback):
        btn = QPushButton(f"  {icon_text}  {label}")
        btn.setFixedHeight(40)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(self._btn_style(False))
        btn.clicked.connect(lambda: self._on_click(len(self.buttons), callback))
        self.buttons.append(btn)
        self.layout.addWidget(btn)
        return btn

    def add_spacer(self):
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background-color: {COLORS['sidebar_hover']}; max-height: 1px; margin: 8px 15px;")
        self.layout.addWidget(sep)

    def _on_click(self, index, callback):
        self._current_index = index
        self._refresh_styles()
        callback()

    def _refresh_styles(self):
        for i, btn in enumerate(self.buttons):
            btn.setStyleSheet(self._btn_style(i == self._current_index))

    def _btn_style(self, active):
        bg = COLORS['sidebar_active'] if active else 'transparent'
        text_color = COLORS['accent'] if active else COLORS['text']
        border = f"3px solid {COLORS['accent']}" if active else "3px solid transparent"
        return f"""
            QPushButton {{
                text-align: left;
                padding-left: 15px;
                border: none;
                border-left: {border};
                background-color: {bg};
                color: {text_color};
                font-size: 13px;
                border-radius: 0;
            }}
            QPushButton:hover {{
                background-color: {COLORS['sidebar_hover']};
                color: {COLORS['text']};
            }}
        """


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(WINDOW_TITLE)
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setStyleSheet(f"background-color: {COLORS['bg']};")

        # 数据加载器
        self.data_loader = DataLoader()
        self.df = None
        self.symbols = []

        # 通达信引擎（异步初始化，不阻塞GUI）
        self.tdx_engine = TdxEngine()

        self._init_ui()
        self._load_data()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 左侧导航
        self.sidebar = Sidebar()

        # 右侧内容区
        content_area = QWidget()
        content_area.setStyleSheet(f"background-color: {COLORS['bg']};")
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # 顶部工具栏
        toolbar = QFrame()
        toolbar.setFixedHeight(50)
        toolbar.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['sidebar']};
                border-bottom: 1px solid {COLORS['sidebar_hover']};
            }}
        """)
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(20, 5, 20, 5)

        self.page_title = QLabel("平台总览")
        self.page_title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {COLORS['text']};")
        tb_layout.addWidget(self.page_title)

        tb_layout.addStretch()

        # 标的选择
        tb_layout.addWidget(self._make_label("标的:"))
        self.symbol_combo = QComboBox()
        self.symbol_combo.setFixedWidth(150)
        self.symbol_combo.setStyleSheet(self._combo_style())
        self.symbol_combo.currentTextChanged.connect(self._on_symbol_changed)
        tb_layout.addWidget(self.symbol_combo)

        # 刷新按钮
        refresh_btn = QPushButton("刷新数据")
        refresh_btn.setFixedWidth(80)
        refresh_btn.setFixedHeight(30)
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent']};
                color: {COLORS['bg']};
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 12px;
            }}
            QPushButton:hover {{ opacity: 0.8; }}
        """)
        refresh_btn.clicked.connect(self._on_refresh)
        tb_layout.addWidget(refresh_btn)

        content_layout.addWidget(toolbar)

        # 页面堆栈
        self.stack = QStackedWidget()
        content_layout.addWidget(self.stack)

        # 创建页面
        self.overview = OverviewView(self.data_loader)
        self.stack.addWidget(self.overview)

        self.structure = StructureView(self.data_loader, self.tdx_engine)
        self.stack.addWidget(self.structure)

        # 添加占位页面
        for name in ["K线图表", "信号系统", "权重回测", "收益分析", "回撤分析",
                      "因子分析", "相关性分析", "价格敏感性", "统计分析", "API手册"]:
            placeholder = self._make_placeholder(name)
            self.stack.addWidget(placeholder)

        # 组装布局
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(content_area)

        # 添加导航项
        self.sidebar.add_item("🏠", "平台总览", lambda: self._switch_page(0, "平台总览"))
        self.sidebar.add_item("📊", "缠论结构分析", lambda: self._switch_page(1, "缠论结构分析"))
        self.sidebar.add_item("📈", "K线图表可视化", lambda: self._switch_page(2, "K线图表可视化"))
        self.sidebar.add_spacer()
        self.sidebar.add_item("🔔", "信号系统", lambda: self._switch_page(3, "信号系统"))
        self.sidebar.add_item("⚖️", "权重回测", lambda: self._switch_page(4, "权重回测"))
        self.sidebar.add_item("💰", "收益分析", lambda: self._switch_page(5, "收益分析"))
        self.sidebar.add_item("📉", "回撤分析", lambda: self._switch_page(6, "回撤分析"))
        self.sidebar.add_spacer()
        self.sidebar.add_item("🔬", "因子分析", lambda: self._switch_page(7, "因子分析"))
        self.sidebar.add_item("🔗", "相关性分析", lambda: self._switch_page(8, "相关性分析"))
        self.sidebar.add_item("🎯", "价格敏感性", lambda: self._switch_page(9, "价格敏感性"))
        self.sidebar.add_item("📐", "统计分析", lambda: self._switch_page(10, "统计分析"))
        self.sidebar.add_spacer()
        self.sidebar.add_item("📚", "API速查手册", lambda: self._switch_page(11, "API速查手册"))

    def _load_data(self):
        """加载数据"""
        self.df = self.data_loader.load_csv()
        if self.df is not None:
            self.symbols = self.data_loader.get_symbols(self.df)
            self.symbol_combo.clear()
            self.symbol_combo.addItems(self.symbols)
            self.overview.update_stats(self.df)
            self._on_symbol_changed(self.symbol_combo.currentText())

    def _switch_page(self, index, title):
        """切换页面"""
        self.stack.setCurrentIndex(index)
        self.page_title.setText(title)

        # 切换到缠论结构分析时更新数据
        if index == 1 and self.df is not None:
            symbol = self.symbol_combo.currentText()
            self.structure.update_data(self.df, symbol)

    def _on_symbol_changed(self, symbol):
        """标的切换"""
        if not symbol or self.df is None:
            return
        self.overview.update_stats(
            self.data_loader.filter_symbol(self.df, symbol)
        )
        # 如果在缠论分析页面，也更新
        if self.stack.currentIndex() == 1:
            self.structure.update_data(self.df, symbol)

    def _on_refresh(self):
        """刷新数据"""
        self.data_loader._cache.clear()
        self._load_data()

    def closeEvent(self, event):
        """关闭时清理资源"""
        if self.tdx_engine:
            self.tdx_engine.close()
        super().closeEvent(event)

    def _make_placeholder(self, name):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label = QLabel(f"{name}\n（功能开发中...）")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(f"""
            font-size: 24px;
            color: {COLORS['text_dim']};
        """)
        layout.addWidget(label)
        return w

    def _make_label(self, text):
        label = QLabel(text)
        label.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 13px;")
        return label

    def _combo_style(self):
        return f"""
            QComboBox {{
                background-color: {COLORS['surface']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['sidebar_hover']};
                border-radius: 5px;
                padding: 5px 10px;
                font-size: 13px;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS['surface']};
                color: {COLORS['text']};
                selection-background-color: {COLORS['sidebar_hover']};
                border: none;
            }}
        """


def main():
    app = QApplication(sys.argv)

    # 设置全局字体
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)

    # 设置深色主题
    app.setStyleSheet(f"""
        * {{
            background-color: {COLORS['bg']};
            color: {COLORS['text']};
        }}
        QScrollBar:vertical {{
            background: {COLORS['sidebar']};
            width: 8px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical {{
            background: {COLORS['sidebar_hover']};
            border-radius: 4px;
            min-height: 20px;
        }}
    """)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
