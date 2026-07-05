# CZSC 缠论量化分析平台

基于缠中说禅理论的 PyQt6 桌面端量化分析工具，支持 CSV 离线分析和通达信实时行情联动。

## 版本说明

| 版本 | 目录 | 功能 |
|------|------|------|
| V1.01 | `czsc_gui_v101/` | 基础版：CSV 数据加载 + CZSC 分型/笔分析 + pyqtgraph K线图 |
| V1.02 | `czsc_gui_v102/` | 进阶版：在 V1.01 基础上新增通达信原生K线联动 |

---

## 前置条件（必须先配置）

### 1. Python 环境

- **Python 3.9 或更高版本**（推荐 3.11+）
- Windows 系统（通达信仅支持 Windows）

### 2. 安装 czsc（最重要的一步）

czsc 是本项目的核心分析引擎，版本 0.10.12+ 使用 Rust 编译，**必须优先安装**：

```bash
pip install czsc>=0.10.12
```

**验证安装：**

```bash
python -c "from czsc import CZSC, RawBar, Freq, Direction; print('czsc 安装成功')"
```

> **注意：** czsc 的 `Mark` 枚举是 Rust 内置类型，无法直接 `from czsc import Mark`。本项目已通过 `core/czsc_engine.py` 中的 `_get_mark_type()` 动态获取，无需手动处理。

### 3. 安装其他依赖

```bash
pip install -r requirements.txt
```

或者逐个安装：

```bash
pip install PyQt6>=6.5.0
pip install pyqtgraph>=0.14.0
pip install pandas>=2.0.0
pip install numpy>=1.24.0
```

### 4. 通达信客户端（仅 V1.02 需要）

如果你只想使用 CSV 离线分析（V1.01），可以跳过这一步。

- 安装 [通达信金融终端](https://www.tdx.com.cn/)（64位版本）
- 确保 `PYPlugins/user/tqcenter.py` 和 `PYPlugins/TPythClient.dll` 存在
- 运行通达信客户端并保持打开状态

---

## 快速开始

### 启动 V1.01（CSV 离线模式）

```bash
cd czsc_gui_v101
python main.py
```

### 启动 V1.02（通达信联动模式）

```bash
cd czsc_gui_v102
python main.py
```

> 首次启动时 TDX 引擎不会自动连接，需要在"缠论结构分析"页面手动点击"连接通达信"。

---

## 使用指南

### V1.01 基础使用

1. **启动程序** — 运行 `czsc_gui_v101/main.py`，进入平台总览页面
2. **查看数据概况** — 首页展示 CSV 数据的统计摘要（K线数、时间范围、价格范围等）
3. **切换标的** — 右上角下拉框选择不同的股票代码（CSV 中包含的标的）
4. **缠论结构分析** — 左侧导航点击"缠论结构分析"，查看：
   - K线图上叠加的分型标记（黄色三角=顶分型，蓝色三角=底分型）
   - 笔的连线（红色=向上笔，绿色=向下笔）
   - 下方的分型列表和笔列表
5. **调节K线数量** — 拖动滑块控制显示的K线数量（50-500根）

### V1.02 通达信联动使用

V1.02 在 V1.01 的基础上增加了通达信数据源，操作流程：

1. **启动程序** — 运行 `czsc_gui_v102/main.py`
2. **进入缠论结构分析** — 左侧导航点击"缠论结构分析"
3. **切换到通达信数据源** — 页面顶部"数据源"下拉框选择"通达信实时"，展开 TDX 控制面板
4. **连接通达信** — 点击"连接通达信"按钮（首次连接需要 3-5 秒，状态栏会显示"连接中..."）
5. **设置参数**：
   - 代码：默认 `999999.SH`（上证指数），可改为任意股票代码
   - 周期：1m/5m/15m/30m/1h/1d
   - K线数量：50-500根
6. **获取数据** — 点击"获取数据"，从通达信拉取实时K线并自动执行 CZSC 分析
7. **推送到TDX** — 分析完成后，点击"推送到TDX"，将笔线和分型标记叠加到通达信原生K线图上
8. **跳转K线** — 点击"跳转K线"可直接在通达信客户端中打开对应股票的K线界面

#### 通达信公式配置（推送后需在TDX中创建指标公式）

在通达信公式管理器中，新建名为 `CZSC_TQ` 的技术指标公式，内容如下：

```
笔线:SIGNALS_TQ(1,1),COLORWHITE,LINETHICK2;
顶分型:SIGNALS_TQ(2,0),COLORYELLOW;
底分型:SIGNALS_TQ(3,0),COLORCYAN;
向上笔:SIGNALS_TQ(4,0),COLORRED,NODRAW;
向下笔:SIGNALS_TQ(5,0),COLORGREEN,NODRAW;
DRAWICON(向上笔>0, LOW*0.999, 1);
DRAWICON(向下笔>0, HIGH*1.001, 2);
```

将此公式应用到K线图上，推送数据后即可看到缠论分析叠加效果。

---

## 项目结构

```
czsc-gui/
├── README.md                  # 本文件
├── requirements.txt           # Python 依赖
├── .gitignore
├── data/
│   └── sh000001_1min_5d.csv   # 示例数据（上证指数1分钟K线，5个交易日）
├── czsc_gui_v101/             # V1.01 - CSV离线分析版
│   ├── main.py                # 主入口
│   ├── config.py              # 全局配置（颜色、窗口参数）
│   ├── core/
│   │   ├── czsc_engine.py     # CZSC 分析引擎封装
│   │   └── data_loader.py     # CSV 数据加载器
│   ├── views/
│   │   ├── overview.py        # 平台总览页面
│   │   └── structure.py       # 缠论结构分析页面
│   └── widgets/
│       └── kline_widget.py    # pyqtgraph K线图组件
├── czsc_gui_v102/             # V1.02 - 通达信联动版
│   ├── main.py                # 主入口（新增 TDX 引擎初始化）
│   ├── config.py              # 全局配置（新增 TDX 参数）
│   ├── core/
│   │   ├── czsc_engine.py     # CZSC 分析引擎（同 V1.01）
│   │   ├── data_loader.py     # CSV 数据加载（同 V1.01）
│   │   ├── tdx_engine.py      # [新] 通达信数据引擎
│   │   └── tdx_chart_push.py  # [新] CZSC→TDX 图表推送桥接
│   ├── views/
│   │   ├── overview.py        # 平台总览页面
│   │   └── structure.py       # 缠论结构分析（新增 TDX 控制面板）
│   └── widgets/
│       └── kline_widget.py    # pyqtgraph K线图组件
```

---

## 常见问题

### Q: czsc 安装失败怎么办？

czsc 0.10.12+ 使用 Rust 编译的 wheel，如果 pip 找不到对应版本：
- 确认 Python 版本 >= 3.9
- 尝试 `pip install czsc --pre` 安装预发布版
- 或从 [czsc GitHub](https://github.com/waditu/czsc) 源码编译

### Q: V1.02 连接通达信失败？

- 确认通达信客户端已启动并登录
- 检查通达信安装目录下的 `PYPlugins/user/tqcenter.py` 是否存在
- 首次连接需要 3-5 秒，请耐心等待
- 程序会通过 Windows 注册表自动查找通达信安装路径

### Q: 推送数据后通达信K线图没有显示缠论标记？

- 需要在通达信公式管理器中创建 `CZSC_TQ` 指标公式（见上方公式配置）
- 创建后将该公式应用到当前K线图

### Q: 数据文件在哪里？

示例数据 `data/sh000001_1min_5d.csv` 包含上证指数 1 分钟 K 线数据。你也可以准备自己的 CSV 文件，格式要求：

```
symbol, dt, open, high, low, close, vol, amount
```

---

## 技术栈

- **czsc 0.10.12+** — Rust 编译的缠论分析核心
- **PyQt6** — 桌面 GUI 框架
- **pyqtgraph** — 高性能 K 线图绘制
- **pandas** — 数据处理
- **tqcenter** — 通达信 DLL 通信接口（V1.02）
