"""CZSC分析结果推送到通达信原生K线图

通过 send_bt_data + SIGNALS_TQ 公式，将笔线、分型标记叠加显示在通达信K线图上。

SIGNALS_TQ 通道分配:
  ID=1: 笔线价格（连接笔的起终点价格）
  ID=2: 顶分型标记（顶分型价格，无则0）
  ID=3: 底分型标记（底分型价格，无则0）
  ID=4: 向上笔起点标记（1=起点，0=无）
  ID=5: 向下笔起点标记（1=起点，0=无）

通达信公式管理器中需创建名为 CZSC_TQ 的技术指标公式（画线指标）：
  BIX:SIGNALS_TQ(1,1),COLORWHITE,LINETHICK2;
  FB:SIGNALS_TQ(2,0),COLORYELLOW;
  DB:SIGNALS_TQ(3,0),COLORCYAN;
  SB:SIGNALS_TQ(4,0),COLORRED,NODRAW;
  XB:SIGNALS_TQ(5,0),COLORGREEN,NODRAW;
  DRAWICON(SB>0, LOW*0.999, 1);
  DRAWICON(XB>0, HIGH*1.001, 2);
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
        (time_list, data_list, diag) 或 None
        diag: 诊断信息 dict
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
    n_fx_matched = 0
    if fx_list:
        for fx in fx_list:
            idx = _find_nearest_idx(dt_list, fx.dt)
            if idx is not None:
                n_fx_matched += 1
                if fx.mark == Mark.G:
                    ch2_top_fx[idx] = fx.fx
                else:
                    ch3_bot_fx[idx] = fx.fx

    # === 填充笔线和笔标记 ===
    n_bi_matched = 0
    if bi_list:
        for bi in bi_list:
            try:
                si = _find_nearest_idx(dt_list, bi.sdt)
                ei = _find_nearest_idx(dt_list, bi.edt)
                if si is None or ei is None:
                    continue

                n_bi_matched += 1
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

    # === 诊断信息 ===
    diag = {
        'n_bars': n,
        'n_bi_total': len(bi_list) if bi_list else 0,
        'n_bi_matched': n_bi_matched,
        'n_fx_total': len(fx_list) if fx_list else 0,
        'n_fx_matched': n_fx_matched,
        'n_bi_line_nonzero': sum(1 for v in ch1_bi_price if v != 0),
        'n_top_fx_nonzero': sum(1 for v in ch2_top_fx if v != 0),
        'n_bot_fx_nonzero': sum(1 for v in ch3_bot_fx if v != 0),
        'n_up_bi_markers': sum(1 for v in ch4_up_bi if v != 0),
        'n_down_bi_markers': sum(1 for v in ch5_down_bi if v != 0),
        'time_first': time_list[0] if time_list else '',
        'time_last': time_list[-1] if time_list else '',
    }

    # 打印诊断日志
    print(f"[Push] 数据诊断: {diag}")

    return time_list, data_list, diag


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

    time_list, data_list, diag = result

    # 数据质量检查
    if diag['n_bi_line_nonzero'] == 0:
        return False, (
            f"数据异常: 笔线通道全为0 (匹配{diag['n_bi_matched']}/{diag['n_bi_total']}笔)。"
            f"时间范围: {diag['time_first']}~{diag['time_last']}"
        )

    resp = tdx_engine.send_bt_data(stock_code, time_list, data_list)

    if resp and resp.get('ErrorId') == '0':
        # 构建详细成功消息
        msg = (
            f"已推送 {diag['n_bars']} 根K线 | "
            f"笔线{diag['n_bi_line_nonzero']}点 "
            f"顶{diag['n_top_fx_nonzero']} 底{diag['n_bot_fx_nonzero']} | "
            f"{diag['time_first'][:8]}~{diag['time_last'][:8]}"
        )
        print(f"[Push] 成功: {msg}")

        # 推送成功后，刷新通达信K线图表
        # 通过重新导航到同一股票和周期，强制TDX重新加载图表以显示SIGNALS_TQ数据
        try:
            import time as _time
            _time.sleep(0.3)  # 短暂等待DLL完成数据写入
            # 重新导航到当前股票，强制图表刷新
            tdx_engine.exec_to_tdx(f"http://www.treeid/ZSCP?code={stock_code}")
            _time.sleep(0.2)
            period = '1m'  # 默认1分钟，实际由调用方控制
            period_map = {'1m': '0', '5m': '1', '15m': '2', '30m': '3', '1h': '4', '1d': '5'}
            p = period_map.get(period, '0')
            tdx_engine.exec_to_tdx(f"http://www.treeid/KLINE?code={stock_code}&period={p}")
            print(f"[Push] 已发送刷新指令到通达信")
        except Exception as e:
            print(f"[Push] 刷新通达信失败(不影响推送): {e}")

        return True, msg
    else:
        error_id = resp.get('ErrorId', '?') if resp else 'None'
        error_msg = resp.get('error', '') if resp else '响应为空'
        detail = f"推送失败 (ErrorId={error_id})"
        if error_msg:
            detail += f" {error_msg}"
        detail += f" | 数据: {diag['n_bars']}K线 {diag['n_bi_matched']}笔 {diag['n_fx_matched']}分型"
        return False, detail


def push_to_tdx_with_period(tdx_engine, stock_code, bar_data, bi_list, fx_list, period='1m'):
    """
    带周期参数的推送（推送成功后刷新到正确周期）

    参数:
        tdx_engine: TdxEngine 实例
        stock_code: 股票代码
        bar_data: K线数据
        bi_list: 笔列表
        fx_list: 分型列表
        period: K线周期 '1m'/'5m'/'15m'/'30m'/'1h'/'1d'

    返回:
        (success: bool, message: str)
    """
    if not tdx_engine or not tdx_engine.is_connected:
        return False, "通达信未连接"

    result = build_bt_payload(bar_data, bi_list, fx_list)
    if result is None:
        return False, "无数据可推送"

    time_list, data_list, diag = result

    # 数据质量检查
    if diag['n_bi_line_nonzero'] == 0:
        return False, (
            f"数据异常: 笔线通道全为0 (匹配{diag['n_bi_matched']}/{diag['n_bi_total']}笔)。"
            f"时间范围: {diag['time_first']}~{diag['time_last']}"
        )

    resp = tdx_engine.send_bt_data(stock_code, time_list, data_list)

    if resp and resp.get('ErrorId') == '0':
        msg = (
            f"已推送 {diag['n_bars']} 根K线 | "
            f"笔线{diag['n_bi_line_nonzero']}点 "
            f"顶{diag['n_top_fx_nonzero']} 底{diag['n_bot_fx_nonzero']} | "
            f"{diag['time_first'][:8]}~{diag['time_last'][:8]}"
        )
        print(f"[Push] 成功: {msg}")

        # 推送成功后，刷新通达信K线图表（使用正确周期）
        try:
            import time as _time
            _time.sleep(0.3)
            tdx_engine.exec_to_tdx(f"http://www.treeid/ZSCP?code={stock_code}")
            _time.sleep(0.2)
            period_map = {'1m': '0', '5m': '1', '15m': '2', '30m': '3', '1h': '4', '1d': '5'}
            p = period_map.get(period, '0')
            tdx_engine.exec_to_tdx(f"http://www.treeid/KLINE?code={stock_code}&period={p}")
            print(f"[Push] 已发送刷新指令到通达信 (period={period})")
        except Exception as e:
            print(f"[Push] 刷新通达信失败(不影响推送): {e}")

        return True, msg
    else:
        error_id = resp.get('ErrorId', '?') if resp else 'None'
        error_msg = resp.get('error', '') if resp else '响应为空'
        detail = f"推送失败 (ErrorId={error_id})"
        if error_msg:
            detail += f" {error_msg}"
        detail += f" | 数据: {diag['n_bars']}K线 {diag['n_bi_matched']}笔 {diag['n_fx_matched']}分型"
        return False, detail


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
