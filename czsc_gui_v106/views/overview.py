"""平台总览页面"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout, QFrame
)
from PyQt6.QtCore import Qt
from config import COLORS, VERSION


class OverviewView(QWidget):
    """平台总览 - 显示数据摘要和模块导航"""

    def __init__(self, data_loader, parent=None):
        super().__init__(parent)
        self.data_loader = data_loader
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # 标题
        title = QLabel(f"CZSC 缠论量化分析平台 {VERSION}")
        title.setStyleSheet(f"""
            QLabel {{
                font-size: 24px;
                font-weight: bold;
                color: {COLORS['accent']};
                padding: 10px 0;
            }}
        """)
        layout.addWidget(title)

        subtitle = QLabel("基于缠中说禅理论的结构化量化分析工具")
        subtitle.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 14px; margin-bottom: 20px;")
        layout.addWidget(subtitle)

        # 数据摘要卡片
        self.stats_layout = QGridLayout()
        self.stats_layout.setSpacing(15)
        layout.addLayout(self.stats_layout)

        # 功能模块介绍
        modules_frame = QFrame()
        modules_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border-radius: 10px;
                padding: 15px;
            }}
        """)
        modules_layout = QVBoxLayout(modules_frame)

        mod_title = QLabel("功能模块")
        mod_title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {COLORS['accent']};")
        modules_layout.addWidget(mod_title)

        modules = [
            ("缠论结构分析", "自动识别分型、笔、线段，展示缠论核心结构"),
            ("K线图表可视化", "高性能交互式K线图，标注分型和笔"),
            ("信号系统", "信号-因子-事件-交易 四层递进分析体系"),
            ("权重回测", "基于持仓权重的连续变量回测引擎"),
            ("收益分析", "累计收益、日收益分布、月度收益热力图"),
            ("回撤分析", "最大回撤、回撤深度、恢复周期分析"),
            ("因子分析", "因子分层收益、IC/IR分析、特征收益"),
            ("相关性分析", "标的间相关性矩阵、滚动相关性"),
            ("价格敏感性", "策略对执行价格的敏感度评估"),
            ("统计分析", "年度统计、日期效应、正态性检验"),
            ("API速查手册", "核心类、函数、CLI命令快速参考"),
        ]

        grid = QGridLayout()
        grid.setSpacing(10)
        for i, (name, desc) in enumerate(modules):
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: {COLORS['bg']};
                    border-radius: 8px;
                    padding: 10px;
                    border: 1px solid {COLORS['sidebar_hover']};
                }}
                QFrame:hover {{
                    border-color: {COLORS['accent']};
                }}
            """)
            card_layout = QVBoxLayout(card)
            card_layout.setSpacing(4)

            name_label = QLabel(name)
            name_label.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {COLORS['text']};")
            card_layout.addWidget(name_label)

            desc_label = QLabel(desc)
            desc_label.setStyleSheet(f"font-size: 11px; color: {COLORS['text_dim']};")
            desc_label.setWordWrap(True)
            card_layout.addWidget(desc_label)

            grid.addWidget(card, i // 3, i % 3)

        modules_layout.addLayout(grid)
        layout.addWidget(modules_frame)

        layout.addStretch()

    def update_stats(self, df):
        """更新数据摘要"""
        # 清除旧的统计卡片
        while self.stats_layout.count():
            item = self.stats_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if df is None:
            return

        stats = self.data_loader.get_stats(df)

        for i, (key, value) in enumerate(stats.items()):
            card = self._make_stat_card(key, str(value))
            self.stats_layout.addWidget(card, 0, i)

    def _make_stat_card(self, title, value):
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border-radius: 8px;
                padding: 12px;
                min-width: 120px;
            }}
        """)
        layout = QVBoxLayout(card)
        layout.setSpacing(4)

        val_label = QLabel(value)
        val_label.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {COLORS['accent']};")
        layout.addWidget(val_label)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"font-size: 11px; color: {COLORS['text_dim']};")
        layout.addWidget(title_label)

        return card
