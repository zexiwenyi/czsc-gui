"""数据加载模块 - 从CSV加载K线数据"""
import pandas as pd
import numpy as np
import os
from config import DEFAULT_CSV, DATA_DIR


class DataLoader:
    """K线数据加载器"""

    def __init__(self):
        self._cache = {}

    def load_csv(self, path=None):
        """加载CSV数据，返回DataFrame"""
        if path is None:
            path = DEFAULT_CSV

        if path in self._cache:
            return self._cache[path]

        if not os.path.exists(path):
            return None

        df = pd.read_csv(path, encoding='utf-8-sig')
        df['dt'] = pd.to_datetime(df['dt'])

        for col in ['open', 'high', 'low', 'close', 'vol', 'amount']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        self._cache[path] = df
        return df

    def get_symbols(self, df):
        """获取标的列表"""
        if df is None:
            return []
        if 'symbol' in df.columns:
            return sorted([str(s) for s in df['symbol'].unique().tolist()])
        return []

    def filter_symbol(self, df, symbol, n_bars=None):
        """按标的过滤数据"""
        if df is None:
            return None
        if 'symbol' in df.columns:
            # 兼容 int/string 类型的 symbol
            try:
                sym_val = type(df['symbol'].iloc[0])(symbol)
            except (ValueError, TypeError):
                sym_val = symbol
            df = df[df['symbol'] == sym_val].copy()
        if n_bars:
            df = df.head(n_bars)
        return df.reset_index(drop=True)

    def get_stats(self, df):
        """获取数据摘要统计"""
        if df is None or len(df) == 0:
            return {}
        return {
            "总K线数": len(df),
            "时间范围": f"{df['dt'].min().strftime('%m-%d %H:%M')} ~ {df['dt'].max().strftime('%m-%d %H:%M')}",
            "价格范围": f"{df['close'].min():.2f} ~ {df['close'].max():.2f}",
            "交易日数": df['dt'].dt.date.nunique(),
            "总成交量": f"{df['vol'].sum():,.0f}" if 'vol' in df.columns else "N/A",
        }
