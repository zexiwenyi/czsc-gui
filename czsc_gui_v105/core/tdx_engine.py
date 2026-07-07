"""TDX数据引擎 - 通过通达信tqcenter获取真实行情数据"""
import sys
import os
import winreg
import pandas as pd
import threading
import time


def _find_tdx_root():
    """从注册表查找通达信安装目录"""
    paths = [
        r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\通达信金融终端64',
        r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\通达信专业版',
        r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\通达信金融终端(量化模拟)',
        r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\通达信金融终端(测试)',
    ]
    for p in paths:
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, p)
            loc = winreg.QueryValueEx(key, 'InstallLocation')[0]
            winreg.CloseKey(key)
            return loc
        except FileNotFoundError:
            continue
    return None


class TdxEngine:
    """通达信数据引擎 - 封装tqcenter连接和数据获取"""

    def __init__(self):
        self._tq = None
        self._initialized = False
        self._tdx_root = None
        self._init_error = None
        self._init_thread = None

    @property
    def is_connected(self):
        return self._initialized and self._tq is not None

    @property
    def tdx_root(self):
        if self._tdx_root is None:
            self._tdx_root = _find_tdx_root()
        return self._tdx_root

    def initialize(self):
        """初始化通达信连接（可能需要几秒，建议在子线程调用）"""
        if self._initialized:
            return True

        root = self.tdx_root
        if not root:
            self._init_error = "未找到通达信安装目录"
            return False

        tq_user_path = os.path.join(root, 'PYPlugins', 'user')
        if not os.path.exists(os.path.join(tq_user_path, 'tqcenter.py')):
            self._init_error = f"tqcenter.py不存在: {tq_user_path}"
            return False

        try:
            if tq_user_path not in sys.path:
                sys.path.insert(0, tq_user_path)
            from tqcenter import tq
            self._tq = tq
            tq.initialize(__file__)
            self._initialized = True
            self._init_error = None
            return True
        except Exception as e:
            self._init_error = str(e)
            return False

    def initialize_async(self, callback=None):
        """异步初始化，避免阻塞GUI主线程"""
        def _do_init():
            success = self.initialize()
            if callback:
                callback(success, self._init_error)

        self._init_thread = threading.Thread(target=_do_init, daemon=True)
        self._init_thread.start()

    def close(self):
        """关闭连接"""
        if self._tq and self._initialized:
            try:
                self._tq.close()
            except Exception:
                pass
            self._initialized = False

    def get_kline(self, stock_code, period='1m', count=200, dividend_type='front'):
        """
        获取K线数据，返回与DataLoader兼容的DataFrame
        
        参数:
            stock_code: 股票代码，如 '999999.SH'
            period: K线周期 '1m'/'5m'/'15m'/'30m'/'1h'/'1d'
            count: K线数量
            dividend_type: 'none'/'front'/'back'
        
        返回:
            DataFrame，columns=[symbol, dt, open, high, low, close, vol, amount, freq]
        """
        if not self.is_connected:
            return None

        try:
            data = self._tq.get_market_data(
                field_list=['Open', 'High', 'Low', 'Close', 'Volume', 'Amount'],
                stock_list=[stock_code],
                period=period,
                count=count,
                dividend_type=dividend_type,
            )
        except Exception as e:
            print(f'[TdxEngine] get_market_data error: {e}')
            return None

        if not data or 'Close' not in data:
            return None

        # 提取单只股票数据
        close_df = data['Close']
        if stock_code not in close_df.columns:
            return None

        # 构建统一格式DataFrame
        idx = close_df.index
        n = len(idx)
        records = []
        for i in range(n):
            dt = idx[i]
            o = data.get('Open', pd.DataFrame())[stock_code].iloc[i] if 'Open' in data else 0
            h = data.get('High', pd.DataFrame())[stock_code].iloc[i] if 'High' in data else 0
            l = data.get('Low', pd.DataFrame())[stock_code].iloc[i] if 'Low' in data else 0
            c = close_df[stock_code].iloc[i]
            v = data.get('Volume', pd.DataFrame())[stock_code].iloc[i] if 'Volume' in data else 0
            a = data.get('Amount', pd.DataFrame())[stock_code].iloc[i] if 'Amount' in data else 0
            records.append({
                'symbol': stock_code,
                'dt': pd.Timestamp(dt),
                'open': float(o) if pd.notna(o) else 0,
                'high': float(h) if pd.notna(h) else 0,
                'low': float(l) if pd.notna(l) else 0,
                'close': float(c) if pd.notna(c) else 0,
                'vol': float(v) if pd.notna(v) else 0,
                'amount': float(a) if pd.notna(a) else 0,
                'freq': period,
            })

        df = pd.DataFrame(records)
        return df

    def get_snapshot(self, stock_code):
        """获取实时快照"""
        if not self.is_connected:
            return None
        try:
            return self._tq.get_market_snapshot(stock_code)
        except Exception:
            return None

    def send_bt_data(self, stock_code, time_list, data_list):
        """
        推送数据到通达信原生K线图（配合SIGNALS_TQ公式使用）
        
        参数:
            stock_code: 股票代码
            time_list: 时间列表 ['YYYYMMDDHHMMSS', ...]
            data_list: 二维列表，每行最多16个值
        
        返回:
            dict: 成功时 {'ErrorId': '0', ...}，失败时 {'ErrorId': 'xxx', 'error': '...'}
        """
        if not self.is_connected:
            return {'ErrorId': '-1', 'error': '通达信未连接'}
        try:
            count = len(time_list)
            result = self._tq.send_bt_data(
                stock_code=stock_code,
                time_list=time_list,
                data_list=data_list,
                count=count,
            )
            # tqcenter 失败时返回空 dict {}，需要补上错误标记
            if result is not None and not result:
                return {'ErrorId': '-2', 'error': 'TDX DLL返回空结果(可能股票代码无效或客户端异常)'}
            return result
        except Exception as e:
            err_msg = str(e)
            print(f'[TdxEngine] send_bt_data error: {err_msg}')
            return {'ErrorId': '-3', 'error': f'异常: {err_msg}'}

    def exec_to_tdx(self, url):
        """调用通达信客户端功能（如跳转到指定股票K线）"""
        if not self.is_connected:
            return None
        try:
            return self._tq.exec_to_tdx(url=url)
        except Exception as e:
            print(f'[TdxEngine] exec_to_tdx error: {e}')
            return None
