# 金策智算 fork 维护版

本仓库是从原始项目 [ScottZt/jin-ce-zhi-suan](https://github.com/ScottZt/jin-ce-zhi-suan) fork 而来，用于本地学习、验证、整理和二次维护。

请先明确这个关系：

- 原始项目：`ScottZt/jin-ce-zhi-suan`
- 原作者/上游仓库：<https://github.com/ScottZt/jin-ce-zhi-suan>
- 本仓库：基于上游项目的 fork，不代表上游官方发布渠道
- 原始版权、授权限制、免责声明以仓库内 [LICENSE](./LICENSE) 和上游项目说明为准

本 README 描述的是当前 fork 的运行方式和维护状态。涉及项目来源、授权、商业使用、投资风险等事项时，应优先阅读并遵守 `LICENSE`。

## 项目定位

金策智算是一个面向 A 股量化研究和回测验证的本地工具项目。项目使用“三省六部”的命名方式组织量化流程，把行情数据、策略信号、风控审核、执行撮合、资金核算和结果报告分层处理。

当前 fork 主要关注：

- 梳理项目结构和文档入口
- 补充数据源配置说明
- 保持本地可运行、可验证
- 将 Python 依赖管理迁移到 `pyproject.toml + uv.lock`
- 保留上游项目主体功能和命名体系

本项目只适合学习、研究、回测和工程验证，不提供投资建议，不承诺收益，不应作为实盘交易依据。

## 当前 fork 的主要差异

相对上游项目，当前 fork 已做过这些维护性调整：

- 依赖管理改为 `uv`：以 [pyproject.toml](./pyproject.toml) 和 [uv.lock](./uv.lock) 为准
- `requirements.txt` 保留为旧环境兼容入口
- 文档按主题整理到 `docs/` 子目录
- 增加数据源配置指南和项目分层说明
- 启动脚本、部署脚本和桌面打包脚本优先适配 `uv`

如果你需要和上游保持一致，应定期对比上游仓库变更，再决定是否合并。

## 快速开始

### 1. 环境要求

- Python `>=3.10,<3.14`
- 推荐安装 `uv`
- macOS / Linux / Windows 均可本地运行

安装依赖：

```bash
uv sync
```

如果需要运行测试：

```bash
uv sync --group dev
```

没有 `uv` 时，可临时使用兼容方式：

```bash
python -m pip install -r requirements.txt
```

### 2. 配置私密参数

不要把 token、密码、API key 写进 `config.json`。建议新建 `config.private.json`，或通过环境变量 `CONFIG_PRIVATE_PATH` 指向私密配置文件。

示例：

```json
{
  "data_provider": {
    "tushare_token": "你的 tushare token",
    "default_api_key": "你的自定义 API key",
    "mysql_password": "你的 MySQL 密码",
    "postgres_password": "你的 PostgreSQL 密码",
    "llm_api_key": "你的 LLM API key"
  }
}
```

配置读取优先级：

```text
环境变量 > config.private.json / CONFIG_PRIVATE_PATH > config.json
```

### 3. 启动 Web 面板

```bash
uv run python server.py
```

指定端口：

```bash
uv run python server.py --port 8001
```

常用脚本：

```bash
bash "scripts/linux&macOS系统启动.sh"
scripts/win一键启动.bat
```

默认访问地址由 `config.json` 的 `system.server_port`、环境变量 `SERVER_PORT` 或命令行参数决定。

## 数据源

当前 fork 默认主行情源是 `tdx`。也支持以下数据源：

- `tdx`：通达信本地数据或网络节点
- `akshare`：AkShare 免费数据源
- `tushare`：TuShare，需要 token
- `mysql`：自建 MySQL 历史行情库
- `postgresql`：自建 PostgreSQL 历史行情库
- `duckdb`：本地 DuckDB 历史行情库
- `default`：自备 HTTP API

数据源详细配置见：

- [数据源配置指南](./docs/data/数据源配置指南.md)
- [历史数据源表结构](./docs/data/历史数据源表结构.sql)
- [DATA_PROVIDER_README](./docs/data/DATA_PROVIDER_README.md)

关于通达信数据需要特别注意：

- 本地模式依赖通达信客户端已经下载好的 `vipdoc` 数据
- 网络节点模式可通过 `mootdx` / `pytdx` 访问行情节点
- 本项目不会自动替你把通达信客户端的本地历史数据下载完整

## 项目结构

```text
.
├── server.py                    # FastAPI Web 服务入口
├── main.py                      # 本地回测入口
├── run_backtest.py              # 命令行回测入口
├── run_live.py                  # 实盘监控入口
├── dashboard.html               # Web 面板页面
├── config.json                  # 默认配置，避免放密钥
├── pyproject.toml               # uv / Python 项目依赖定义
├── uv.lock                      # uv 锁文件
├── requirements.txt             # 旧环境兼容依赖文件
├── src/
│   ├── core/                    # 三省主流程：数据、策略、风控、执行
│   ├── ministries/              # 六部职能模块：资金、绩效、撮合等
│   ├── strategies/              # 内置策略和自定义策略管理
│   ├── strategy_intent/         # 策略意图解析与生成
│   ├── tdx/                     # 通达信公式、终端桥接相关能力
│   └── utils/                   # 配置、数据源、指标、同步工具
├── scripts/                     # 启动、部署、诊断、批量任务脚本
├── data/                        # 本地数据、报告、策略结果
├── docs/                        # 项目文档
└── tests/                       # 单元测试
```

更详细的分层说明见 [项目结构与分层说明](./docs/architecture/项目结构与分层说明.md)。

## 文档入口

- [文档目录](./docs/README.md)
- [API 文档](./docs/api/API_DOCS.md)
- [数据源配置指南](./docs/data/数据源配置指南.md)
- [批量回测操作指南](./docs/guides/批量回测操作指南.md)
- [全局回测与实盘监控基线模板](./docs/guides/全局回测与实盘监控基线模板.md)
- [事件驱动多 Agent 策略进化](./docs/evolution/新功能说明_事件驱动多Agent策略进化.md)
- [通达信 BLK 组合回测](./docs/features/新功能说明_通达信_BLK_组合回测.md)

## 常用命令

安装或同步依赖：

```bash
uv sync
```

运行 Web 面板：

```bash
uv run python server.py
```

运行命令行回测：

```bash
uv run python run_backtest.py --stock 600000.SH --start 2024-01-01 --end 2024-12-31
```

运行单元测试：

```bash
uv run pytest tests/unit -q
```

桌面端打包：

```bash
uv sync --extra desktop-build
bash scripts/build_desktop.sh
```

## 维护说明

### 依赖管理

当前以 `pyproject.toml` 和 `uv.lock` 为准：

- 新依赖应先加入 `pyproject.toml`
- 修改依赖后执行 `uv lock`
- 本地环境同步执行 `uv sync`
- `requirements.txt` 只作为兼容旧脚本和无 uv 环境的兜底

### 上游同步

如果本仓库需要跟进原始项目变更，可以添加上游 remote：

```bash
git remote add upstream https://github.com/ScottZt/jin-ce-zhi-suan.git
git fetch upstream
```

合并前建议先查看差异，避免覆盖本 fork 已整理的配置、文档和依赖管理改动。

## 测试状态

最近一次依赖迁移后的本地验证：

- `uv lock` 通过
- `uv sync` 通过
- `uv lock --check` 通过
- `uv run python -m py_compile ...` 通过
- `uv run python -c "import server"` 通过
- `uv run pytest tests/unit -q` 可执行；当前存在 1 个与 TDX 连通性预期相关的业务断言失败

失败项不是依赖迁移引入的锁文件或导入问题，而是测试期望“无本地 TDX 目录时报错”，当前实现会走网络节点并返回成功。

## 授权与免责声明

本项目沿用原项目的授权和免责声明。简要说明：

- 仅用于个人学习、学术研究、本地非商业用途
- 未经书面授权，不得用于商业销售、托管服务、SaaS、二次包装销售或盈利部署
- 本项目不提供证券投资咨询服务
- 回测结果、策略信号、指标和报告不构成投资建议
- 使用者自行承担数据、交易、合规和法律风险

完整条款请阅读 [LICENSE](./LICENSE)。涉及原项目版权和授权解释时，请以上游项目与许可证原文为准。
