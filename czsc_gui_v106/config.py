"""CZSC GUI 全局配置"""
import os

# 版本号
VERSION = "V1.06"

# 项目路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "data")

# 默认数据文件（CSV备用）
DEFAULT_CSV = os.path.join(DATA_DIR, "sh000001_1min_5d.csv")

# 通达信默认参数
TDX_DEFAULT_STOCK = "999999.SH"   # 上证指数
TDX_DEFAULT_PERIOD = "1m"          # 1分钟
TDX_DEFAULT_COUNT = 200            # K线数量
TDX_PERIODS = ["1m", "5m", "15m", "30m", "1h", "1d"]

# 窗口配置
WINDOW_TITLE = f"CZSC 缠论量化分析平台 {VERSION}"
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 900
SIDEBAR_WIDTH = 220

# 颜色主题
COLORS = {
    "bg": "#1e1e2e",
    "sidebar": "#181825",
    "sidebar_hover": "#313244",
    "sidebar_active": "#45475a",
    "text": "#cdd6f4",
    "text_dim": "#a6adc8",
    "accent": "#89b4fa",
    "red": "#f38ba8",
    "green": "#a6e3a1",
    "yellow": "#f9e2af",
    "surface": "#313244",
}

# K线图颜色
KLINE_COLORS = {
    "up": "#ef5350",       # 上涨红色
    "down": "#26a69a",     # 下跌绿色
    "bi_up": "#f38ba8",    # 向上笔
    "bi_down": "#a6e3a1",  # 向下笔
    "fx_top": "#f9e2af",   # 顶分型
    "fx_bottom": "#89b4fa", # 底分型
}
