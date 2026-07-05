# CZSC 缠论量化分析平台

基于缠中说禅理论的 PyQt6 量化分析工具，支持 CSV 加载或通达信实时数据。

## 版本说明

| 版本 | 目录 | 说明 |
|------|------|------|
| V1.01 | `czsc_gui_v101/` | 基础版：CSV 数据加载 + CZSC 分型/笔分析 + pyqtgraph K线图 |
| V1.02 | `czsc_gui_v102/` | 进阶版：在 V1.01 基础上新增通达信原生K线集成 |
| V1.03 | `czsc_gui_v103/` | 对比版：在 V1.02 基础上新增 scipy.signal 波段检测对比 |

---

## 前置条件（必须首先配置）

### 1. Python 环境

- **Python 3.9 或更高版本**（推荐 3.11+）
- Windows 系统（通达信仅支持 Windows）

### 2. 安装 czsc（必须第一步）

czsc 是本项目的核心分析库，版本 0.10.12+ 使用 Rust 编译，**请务必先安装**：

```bash
pip install czsc>=0.10.12
```

**验证安装：**

```bash
python -c "import czsc; print(czsc.__version__)"
```

### 3. 安装其他依赖

```bash
pip install -r requirements.txt
```

### 4. 通达信客户端（仅V1.02/V1.03通达信功能需要）

- 安装通达信客户端（如 `i:\new_tdx64\`）
- 确保 `PYPlugins/user/tqcenter.py` 存在
- 启动通达信并保持运行

---

## 快速开始

### V1.01（CSV数据 + 基础CZSC分析）

```bash
cd czsc_gui_v101
python main.py
```

1. 在「缠论结构分析」页面查看 CZSC 分型/笔标注
2. K线图支持缩放、拖拽

### V1.02（通达信原生K线集成）

```bash
cd czsc_gui_v102
python main.py
```

1. 切换到「通达信实时」数据源
2. 点击「连接通达信」→「获取数据」
3. 可将CZSC分析结果推送到通达信原生K线图

### V1.03（scipy波段检测对比）

```bash
cd czsc_gui_v103
python main.py
```

1. 在「缠论结构分析」页面加载数据
2. 调整「波段对比」面板的 distance 和 prominence 参数
3. 点击「分析对比」，同时查看 CZSC 缠论笔 和 scipy 波段标注
4. 统计区显示两种方法的对比数据

---

## 使用指南

### CSV 数据模式

1. 准备 CSV 文件，包含列：`dt, open, high, low, close, vol`
2. 放入 `data/` 目录
3. 启动程序，在「平台总览」选择标的

### 通达信实时模式（V1.02+）

1. 启动通达信客户端
2. 在GUI中选择「通达信实时」数据源
3. 输入股票代码（如 `999999.SH` 上证指数）
4. 选择K线周期（1m/5m/15m/30m/1h/1d）
5. 点击「连接通达信」→「获取数据」

### scipy 波段对比（V1.03）

**distance 参数：** 相邻峰/谷之间的最小K线根数，数值越大捕捉的波段越大。

**prominence 参数：** 峰/谷的突出度阈值，要求波峰/谷足够突出，过滤噪音。

**对比要点：**
- CZSC 缠论：基于分型→笔→线段的严格递归结构
- scipy 波段：基于局部极值的统计方法，更灵活但需调参

---

## 通达信公式（推送到原生K线时需要）

在通达信「公式管理器」中新建公式 `CZSC_TQ`：

```
{CZSC缠论标注}
DRAWTEXT_REL(1,1,0,'CZSC_TQ'),COLORWHITE;
```

---

## 项目结构

```
czsc-gui/
├── czsc_gui_v101/          # V1.01 基础版
│   ├── main.py             # 主入口
│   ├── config.py           # 全局配置
│   ├── core/
│   │   ├── data_loader.py  # CSV数据加载
│   │   └── czsc_engine.py  # CZSC分析引擎
│   ├── views/
│   │   ├── overview.py     # 平台总览
│   │   └── structure.py    # 缠论结构分析
│   └── widgets/
│       └── kline_widget.py # K线图组件
├── czsc_gui_v102/          # V1.02 通达信版
│   └── (同V1.01结构 + tdx_engine/tdx_chart_push)
├── czsc_gui_v103/          # V1.03 对比版
│   └── (同V1.02结构 + peak_detector)
├── data/                   # CSV数据文件
├── requirements.txt        # Python依赖
└── README.md
```

---

## 常见问题

**Q: czsc 安装失败？**
A: 确保 Python 版本 ≥ 3.9，尝试 `pip install --upgrade pip` 后重试。

**Q: 通达信连接失败？**
A: 确保通达信客户端已启动，且 `tqcenter.py` 在正确路径。

**Q: scipy 波段结果太多/太少？**
A: 调整 distance 参数（增大=更少波段，减小=更多波段），或设置 prominence 过滤噪音。

**Q: Mark/Direction 枚举报错？**
A: czsc 0.10.12 使用 Rust 编译，Mark 不能直接 import，程序内部已处理。

---

## 技术栈

- **czsc** 0.10.12+ — 缠论分析核心（Rust编译）
- **PyQt6** — GUI框架
- **pyqtgraph** — 高性能K线图表
- **scipy** — 信号处理/波段检测
- **pandas/numpy** — 数据处理
- **tqcenter** — 通达信DLL通信接口
