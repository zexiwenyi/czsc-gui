"""CZSC分析结果推送到通达信原生K线图

通过 send_bt_data + SIGNALS_TQ 公式，将笔线、分型标记叠加显示在通达信K线图上。

SIGNALS_TQ 通道分配:
  ID=1: 笔线价格（连接笔的起终点价格）
  ID=2: 顶分型标记（顶分型价格，无则0）
  ID=3: 底分型标记（底分型价格，无则0）
  ID=4: 向上笔起点标记（1=起点，0=无）
  ID=5: 向下笔起点标记（1=起点，0=无）

通达信公式管理器中需创建名为 CZSC_TQ 的技术指标公式：
  笔线:SIGNALS_TQ(1,1),COLORWHITE,LINETHICK2;
  顶标记:SIGNALS_TQ(2,0),COLORYELLOW;
  底标记:SIGNALS_TQ(3,0),COLORCYAN;
  向上笔:SIGNALS_TQ(4,0),COLORRED,NODRAW;
  向下笔:SIGNALS_TQ(5,0),COLORGREEN,NODRAW;
  DRAWICON(向上笔>0, LOW*0.999, 1);
  DRAWICON(向下笔>0, HIGH*1.001, 2);
"""
import pandas as pd
from czsc import Direction
from core.czsc_engine import Mark


def build_bt_payload(bar_data, bi_list, fx_list):
    """
    将CZSC分析结果编码为 send_bt_data 所需的 time_list 和 data_list
    
    参数:
        bar_data: list of dict {dt, open, high, low, close, vol}
        bi_list: CZSC BI objects
        fx_list: CZSC FX objects
    
    返回:
        (time_list, data_list) 或 None
    """
    if not bar_data:
        return None

    n = len(bar_data)
    dt_list = [b['dt'] for b in bar_data]

    # 初始化5个通道，全为0
    ch1_bi_price = [0.0] * n      # 笔线价格
    ch2_top_fx = [0.0] * n       # 顶分型
    ch3_bot_fx = [0.0] * n       # 底分型
    ch4_up_bi = [0.0] * n        # 向上笔起点
    ch5_down_bi = [0.0] * n      # 向下笔起点

    # === 填充分型标记 ===
    if fx_list:
        for fx in fx_list:
            idx = _find_nearest_idx(dt_list, fx.dt)
            if idx is not None:
                if fx.mark == Mark.G:
                    ch2_top_fx[idx] = fx.fx
                else:
                    ch3_bot_fx[idx] = fx.fx

    # === 填充笔线和笔标记 ===
    if bi_list:
        for bi in bi_list:
            try:
                si = _find_nearest_idx(dt_list, bi.sdt)
                ei = _find_nearest_idx(dt_list, bi.edt)
                if si is None or ei is None:
                    continue

                start_price = bi.fx_a.fx
                end_price = bi.fx_b.fx

                # 笔线：线性插值连接起终点
                if ei > si:
                    for j in range(si, ei + 1):
                        ratio = (j - si) / (ei - si)
                        ch1_bi_price[j] = start_price + ratio * (end_price - start_price)

                # 笔起点标记
                if bi.direction == Direction.Up:
                    ch4_up_bi[si] = 1
                else:
                    ch5_down_bi[si] = 1

            except Exception:
                continue

    # === 构建 time_list 和 data_list ===
    time_list = []
    data_list = []
    for i in range(n):
        dt = pd.Timestamp(dt_list[i])
        time_str = dt.strftime('%Y%m%d%H%M%S')
        time_list.append(time_str)
        data_list.append([
            f"{ch1_bi_price[i]:.2f}",
            f"{ch2_top_fx[i]:.2f}",
            f"{ch3_bot_fx[i]:.2f}",
            str(int(ch4_up_bi[i])),
            str(int(ch5_down_bi[i])),
        ])

    return time_list, data_list


def push_to_tdx(tdx_engine, stock_code, bar_data, bi_list, fx_list):
    """
    一站式推送：编码数据 + 发送到通达信
    
    参数:
        tdx_engine: TdxEngine 实例
        stock_code: 股票代码
        bar_data: K线数据
        bi_list: 笔列表
        fx_list: 分型列表
    
    返回:
        (success: bool, message: str)
    """
    if not tdx_engine or not tdx_engine.is_connected:
        return False, "通达信未连接"

    result = build_bt_payload(bar_data, bi_list, fx_list)
    if result is None:
        return False, "无数据可推送"

    time_list, data_list = result
    resp = tdx_engine.send_bt_data(stock_code, time_list, data_list)

    if resp and resp.get('ErrorId') == '0':
        return True, f"已推送 {len(time_list)} 根K线的分析数据到通达信"
    else:
        error_id = resp.get('ErrorId', '?') if resp else 'None'
        return False, f"推送失败 (ErrorId={error_id})"


def _find_nearest_idx(dt_list, target_dt):
    """找到最接近目标时间的索引"""
    target = pd.Timestamp(target_dt)
    min_diff = None
    best_idx = None
    for i, dt in enumerate(dt_list):
        diff = abs((pd.Timestamp(dt) - target).total_seconds())
        if min_diff is None or diff < min_diff:
            min_diff = diff
            best_idx = i
    return best_idx
