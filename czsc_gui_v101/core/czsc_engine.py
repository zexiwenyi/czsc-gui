"""CZSC分析引擎封装"""
from czsc import CZSC, RawBar, Freq, Direction
import pandas as pd


def _get_mark_type():
    """动态获取Mark枚举类型（Rust内置，无法直接import）"""
    bars = []
    prices = [10, 11, 12, 11, 10, 9, 10, 11, 12, 13, 12, 11, 10, 11, 12, 13, 14, 13, 12, 11, 10, 9, 10, 11, 12, 13, 14, 15, 14, 13]
    for i, p in enumerate(prices):
        bars.append(RawBar(symbol='_T', dt=pd.Timestamp(f'2026-01-01 09:{30+i}'),
                           open=p-0.5, high=p+1, low=p-1, close=p,
                           vol=100, amount=10000, freq=Freq.F1))
    c = CZSC(bars)
    if c.fx_list:
        return type(c.fx_list[0].mark)
    return None


Mark = _get_mark_type()


class CzscEngine:
    """封装CZSC分析器，提供统一接口"""

    def __init__(self, df, freq=Freq.F1):
        self.df = df
        self.freq = freq
        self.czsc = None
        self._build()

    def _build(self):
        """构建CZSC分析对象"""
        bars = []
        for _, row in self.df.iterrows():
            bars.append(RawBar(
                symbol=str(row.get('symbol', '000001')),
                dt=pd.Timestamp(row['dt']),
                open=float(row['open']),
                high=float(row['high']),
                low=float(row['low']),
                close=float(row['close']),
                vol=int(row.get('vol', 0)),
                amount=float(row.get('amount', 0)),
                freq=self.freq
            ))
        self.czsc = CZSC(bars)

    @property
    def fx_list(self):
        return self.czsc.fx_list if self.czsc else []

    @property
    def bi_list(self):
        return self.czsc.bi_list if self.czsc else []

    @property
    def n_bars(self):
        return len(self.czsc.bars_raw) if self.czsc else 0

    def get_fx_data(self):
        """获取分型数据列表"""
        result = []
        for fx in self.fx_list:
            result.append({
                "时间": str(fx.dt),
                "类型": "顶分型" if fx.mark == Mark.G else "底分型",
                "价格": round(fx.fx, 2),
                "mark": fx.mark,
            })
        return result

    def get_bi_data(self):
        """获取笔数据列表"""
        result = []
        for i, bi in enumerate(self.bi_list):
            result.append({
                "序号": i,
                "方向": "向上" if bi.direction == Direction.Up else "向下",
                "起点时间": str(bi.sdt),
                "终点时间": str(bi.edt),
                "最高": round(bi.high, 2),
                "最低": round(bi.low, 2),
                "幅度": round(bi.high - bi.low, 2),
                "涨跌幅%": round(bi.change * 100, 2),
                "K线数": bi.length,
                "direction": bi.direction,
            })
        return result

    def get_bi_summary(self):
        """笔统计摘要"""
        bi_data = self.get_bi_data()
        if not bi_data:
            return {}

        up_count = sum(1 for b in bi_data if b['direction'] == Direction.Up)
        down_count = sum(1 for b in bi_data if b['direction'] == Direction.Down)
        amplitudes = [b['幅度'] for b in bi_data]

        return {
            "笔总数": len(bi_data),
            "向上笔": up_count,
            "向下笔": down_count,
            "平均幅度": round(sum(amplitudes) / len(amplitudes), 2),
            "最大幅度": round(max(amplitudes), 2),
            "最小幅度": round(min(amplitudes), 2),
        }

    def get_bar_data(self):
        """获取K线数据列表，用于绘图"""
        result = []
        for bar in self.czsc.bars_raw:
            result.append({
                "dt": bar.dt,
                "open": bar.open,
                "high": bar.high,
                "low": bar.low,
                "close": bar.close,
                "vol": bar.vol,
            })
        return result
