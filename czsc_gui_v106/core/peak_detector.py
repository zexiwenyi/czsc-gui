"""基于 scipy.signal 的波段高低点检测"""
import numpy as np
from scipy.signal import find_peaks


class PeakDetector:
    """使用 find_peaks 检测K线数据中的局部高低点，识别上涨/下跌段"""

    def __init__(self, bar_data, distance=10, prominence=None):
        """
        bar_data: list of dict with keys: dt, high, low, close
        distance: 相邻峰/谷之间的最小距离（K线根数）
        prominence: 峰/谷的突出度阈值，None则自动计算
        """
        self.bar_data = bar_data
        self.distance = distance
        self.prominence = prominence
        self.highs = []  # [(index, price, dt), ...]
        self.lows = []
        self.segments = []  # [{'start_idx', 'end_idx', 'start_price', 'end_price', 'direction', 'start_dt', 'end_dt'}, ...]
        self._detect()

    def _detect(self):
        if len(self.bar_data) < 3:
            return

        highs_arr = np.array([b['high'] for b in self.bar_data])
        lows_arr = np.array([b['low'] for b in self.bar_data])

        # Detect peaks (local highs)
        peak_kwargs = {'distance': self.distance}
        if self.prominence is not None:
            peak_kwargs['prominence'] = self.prominence

        peak_indices, peak_props = find_peaks(highs_arr, **peak_kwargs)
        valley_indices, valley_props = find_peaks(-lows_arr, **peak_kwargs)

        # Store highs and lows
        for idx in peak_indices:
            self.highs.append({
                'index': int(idx),
                'price': float(highs_arr[idx]),
                'dt': self.bar_data[idx]['dt']
            })

        for idx in valley_indices:
            self.lows.append({
                'index': int(idx),
                'price': float(lows_arr[idx]),
                'dt': self.bar_data[idx]['dt']
            })

        # Merge and sort all turning points
        all_points = []
        for h in self.highs:
            all_points.append({**h, 'type': 'high'})
        for l in self.lows:
            all_points.append({**l, 'type': 'low'})
        all_points.sort(key=lambda x: x['index'])

        # Build segments between consecutive turning points
        for i in range(len(all_points) - 1):
            p1 = all_points[i]
            p2 = all_points[i + 1]
            if p1['type'] == 'low' and p2['type'] == 'high':
                direction = 'up'
            elif p1['type'] == 'high' and p2['type'] == 'low':
                direction = 'down'
            else:
                continue

            self.segments.append({
                'start_idx': p1['index'],
                'end_idx': p2['index'],
                'start_price': p1['price'],
                'end_price': p2['price'],
                'start_dt': p1['dt'],
                'end_dt': p2['dt'],
                'direction': direction,
                'amplitude': round(abs(p2['price'] - p1['price']), 2),
            })

    def get_summary(self):
        """统计摘要"""
        up_segs = [s for s in self.segments if s['direction'] == 'up']
        down_segs = [s for s in self.segments if s['direction'] == 'down']
        amplitudes = [s['amplitude'] for s in self.segments] if self.segments else [0]
        return {
            'total_segments': len(self.segments),
            'up_segments': len(up_segs),
            'down_segments': len(down_segs),
            'peaks': len(self.highs),
            'valleys': len(self.lows),
            'avg_amplitude': round(sum(amplitudes) / len(amplitudes), 2) if amplitudes else 0,
            'max_amplitude': round(max(amplitudes), 2) if amplitudes else 0,
        }
