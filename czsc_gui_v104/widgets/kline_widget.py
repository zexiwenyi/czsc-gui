"""K线图组件 - 使用pyqtgraph绘制高性能K线图"""
import pyqtgraph as pg
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import Qt
from config import KLINE_COLORS


class KlineWidget(QWidget):
    """K线图+成交量+缠论标注组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 创建图形布局，上方K线，下方成交量
        self.graphics_layout = pg.GraphicsLayoutWidget()
        self.graphics_layout.setBackground(pg.mkColor("#1e1e2e"))

        # K线图区域
        self.kline_plot = self.graphics_layout.addPlot(row=0, col=0, title="")
        self.kline_plot.setLabel('left', '价格')
        self.kline_plot.showGrid(x=False, y=True, alpha=0.15)
        self.kline_plot.getAxis('left').setPen(pg.mkColor("#a6adc8"))
        self.kline_plot.getAxis('bottom').setPen(pg.mkColor("#a6adc8"))
        self.kline_plot.getAxis('left').setTextPen(pg.mkColor("#a6adc8"))
        self.kline_plot.getAxis('bottom').setTextPen(pg.mkColor("#a6adc8"))

        # 成交量区域
        self.vol_plot = self.graphics_layout.addPlot(row=1, col=0, title="")
        self.vol_plot.setLabel('left', '成交量')
        self.vol_plot.setMaximumHeight(120)
        self.vol_plot.showGrid(x=False, y=True, alpha=0.1)
        self.vol_plot.getAxis('left').setPen(pg.mkColor("#a6adc8"))
        self.vol_plot.getAxis('bottom').setPen(pg.mkColor("#a6adc8"))
        self.vol_plot.getAxis('left').setTextPen(pg.mkColor("#a6adc8"))
        self.vol_plot.getAxis('bottom').setTextPen(pg.mkColor("#a6adc8"))

        # 联动X轴
        self.vol_plot.setXLink(self.kline_plot)

        layout.addWidget(self.graphics_layout)

    def plot(self, bar_data, bi_list=None, fx_list=None):
        """
        绘制K线图
        bar_data: list of dict {dt, open, high, low, close, vol}
        bi_list: CZSC BI objects
        fx_list: CZSC FX objects
        """
        self.kline_plot.clear()
        self.vol_plot.clear()

        if not bar_data:
            return

        n = len(bar_data)
        x = list(range(n))

        opens = [b['open'] for b in bar_data]
        highs = [b['high'] for b in bar_data]
        lows = [b['low'] for b in bar_data]
        closes = [b['close'] for b in bar_data]
        vols = [b['vol'] for b in bar_data]

        # 绘制K线（蜡烛图）
        up_color = pg.mkColor(KLINE_COLORS["up"])
        down_color = pg.mkColor(KLINE_COLORS["down"])

        # 影线（高-低）
        for i in range(n):
            color = up_color if closes[i] >= opens[i] else down_color
            # 上下影线
            self.kline_plot.addItem(
                pg.InfiniteLine(pos=0, angle=90, pen=pg.mkPen(color, width=1),
                                movable=False) if False else
                pg.PlotCurveItem([x[i], x[i]], [lows[i], highs[i]],
                                 pen=pg.mkPen(color, width=1))
            )

        # 实体部分
        up_mask = [i for i in range(n) if closes[i] >= opens[i]]
        down_mask = [i for i in range(n) if closes[i] < opens[i]]

        # 上涨实体（空心/实心红）
        bar_width = 0.6
        for i in up_mask:
            body_low = opens[i]
            body_high = closes[i]
            if body_high - body_low < 0.001:
                body_high = body_low + 0.001
            self.kline_plot.addItem(
                pg.QtWidgets.QGraphicsRectWidget(0, 0, 0, 0) if False else
                _make_bar_rect(x[i], body_low, body_high, bar_width, up_color, filled=True)
            )

        for i in down_mask:
            body_low = closes[i]
            body_high = opens[i]
            if body_high - body_low < 0.001:
                body_high = body_low + 0.001
            self.kline_plot.addItem(
                _make_bar_rect(x[i], body_low, body_high, bar_width, down_color, filled=True)
            )

        # 成交量柱状图
        for i in range(n):
            color = up_color if closes[i] >= opens[i] else down_color
            self.vol_plot.addItem(
                _make_bar_rect(x[i], 0, vols[i], bar_width, color, filled=True)
            )

        # 设置X轴刻度为时间
        if bar_data:
            tick_spacing = max(1, n // 20)
            ticks = [(i, bar_data[i]['dt'].strftime('%m-%d %H:%M'))
                     for i in range(0, n, tick_spacing)]
            ax = self.kline_plot.getAxis('bottom')
            ax.setTicks([ticks])
            ax2 = self.vol_plot.getAxis('bottom')
            ax2.setTicks([ticks])

        # 绘制笔
        if bi_list:
            self._draw_bi(bi_list, bar_data)

        # 绘制分型标记
        if fx_list:
            self._draw_fx(fx_list, bar_data)

    def plot_comparison(self, bar_data, czsc_bi_list, czsc_fx_list,
                        peak_highs, peak_lows, peak_segments):
        """
        对比绘制：同时显示CZSC缠论标注 + scipy波段高低点
        bar_data: list of dict {dt, open, high, low, close, vol}
        czsc_bi_list: CZSC BI objects
        czsc_fx_list: CZSC FX objects
        peak_highs: list of dict {index, price, dt} from PeakDetector
        peak_lows: list of dict {index, price, dt} from PeakDetector
        peak_segments: list of dict {start_idx, end_idx, start_price, end_price, direction, ...}
        """
        # 先绘制基础K线 + CZSC标注
        self.plot(bar_data, bi_list=czsc_bi_list, fx_list=czsc_fx_list)

        if not bar_data:
            return

        # scipy 波段高点标记 - 亮橙色 #ff9800，较大的倒三角
        if peak_highs:
            hx = [h['index'] for h in peak_highs]
            hy = [h['price'] for h in peak_highs]
            scatter_highs = pg.ScatterPlotItem(
                hx, hy, size=14, symbol='t',
                brush=pg.mkColor("#ff9800"),
                pen=pg.mkPen(pg.mkColor("#ff9800"), width=2)
            )
            self.kline_plot.addItem(scatter_highs)

        # scipy 波段低点标记 - 亮紫色 #ce93d8，较大的正三角
        if peak_lows:
            lx = [l['index'] for l in peak_lows]
            ly = [l['price'] for l in peak_lows]
            scatter_lows = pg.ScatterPlotItem(
                lx, ly, size=14, symbol='t1',
                brush=pg.mkColor("#ce93d8"),
                pen=pg.mkPen(pg.mkColor("#ce93d8"), width=2)
            )
            self.kline_plot.addItem(scatter_lows)

        # scipy 波段连接线 - 虚线样式
        if peak_segments:
            for seg in peak_segments:
                si = seg['start_idx']
                ei = seg['end_idx']
                sp = seg['start_price']
                ep = seg['end_price']
                if seg['direction'] == 'up':
                    color = pg.mkColor("#ff9800")
                else:
                    color = pg.mkColor("#ce93d8")
                # 虚线样式: dash pattern
                pen = pg.mkPen(color, width=2, style=Qt.PenStyle.DashLine)
                self.kline_plot.plot([si, ei], [sp, ep], pen=pen)

    def _draw_bi(self, bi_list, bar_data):
        """绘制缠论笔"""
        if not bi_list or not bar_data:
            return

        dt_list = [b['dt'] for b in bar_data]

        for bi in bi_list:
            # 找笔的起终点在bar_data中的索引
            try:
                sdt = bi.sdt
                edt = bi.edt
                si = _find_nearest_idx(dt_list, sdt)
                ei = _find_nearest_idx(dt_list, edt)

                color = KLINE_COLORS["bi_up"] if str(bi.direction) in ('向上', 'Direction.Up') else KLINE_COLORS["bi_down"]
                pen = pg.mkPen(pg.mkColor(color), width=2)
                self.kline_plot.plot([si, ei], [bi.fx_a.fx, bi.fx_b.fx], pen=pen)
            except Exception:
                continue

    def _draw_fx(self, fx_list, bar_data):
        """绘制分型标记"""
        if not fx_list or not bar_data:
            return

        dt_list = [b['dt'] for b in bar_data]

        top_x, top_y = [], []
        bot_x, bot_y = [], []

        for fx in fx_list:
            try:
                idx = _find_nearest_idx(dt_list, fx.dt)
                if str(fx.mark) in ('顶分型', 'Mark.G'):
                    top_x.append(idx)
                    top_y.append(fx.fx)
                else:
                    bot_x.append(idx)
                    bot_y.append(fx.fx)
            except Exception:
                continue

        if top_x:
            scatter_top = pg.ScatterPlotItem(
                top_x, top_y, size=8, symbol='t',
                brush=pg.mkColor(KLINE_COLORS["fx_top"]),
                pen=pg.mkPen(pg.mkColor(KLINE_COLORS["fx_top"]), width=1)
            )
            self.kline_plot.addItem(scatter_top)

        if bot_x:
            scatter_bot = pg.ScatterPlotItem(
                bot_x, bot_y, size=8, symbol='t1',
                brush=pg.mkColor(KLINE_COLORS["fx_bottom"]),
                pen=pg.mkPen(pg.mkColor(KLINE_COLORS["fx_bottom"]), width=1)
            )
            self.kline_plot.addItem(scatter_bot)


def _make_bar_rect(x, y_low, y_high, width, color, filled=True):
    """创建一个矩形BarItem"""
    rect = pg.QtWidgets.QGraphicsRectItem(
        x - width / 2, y_low, width, y_high - y_low
    )
    if filled:
        rect.setBrush(pg.mkBrush(color))
    else:
        rect.setBrush(pg.mkBrush(None))
    rect.setPen(pg.mkPen(color))
    return rect


def _find_nearest_idx(dt_list, target_dt):
    """找到最接近目标时间的索引"""
    import pandas as pd
    target = pd.Timestamp(target_dt)
    min_diff = None
    best_idx = 0
    for i, dt in enumerate(dt_list):
        diff = abs((pd.Timestamp(dt) - target).total_seconds())
        if min_diff is None or diff < min_diff:
            min_diff = diff
            best_idx = i
    return best_idx
