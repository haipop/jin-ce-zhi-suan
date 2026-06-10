# DataProvider 封装说明

本文说明 `src/utils` 下行情 Provider 的当前实现边界。更完整的配置说明见 `docs/data/数据源配置指南.md`。

## 当前支持的数据源

`DataFactory` 和回测/实盘运行层当前支持以下 `source`：

| source | Provider | 说明 |
| --- | --- | --- |
| `tdx` | `TdxProvider` | 通达信本地 `vipdoc` 或 TDX 网络节点。当前 `config.json` 默认值。 |
| `akshare` | `AkshareProvider` | 免费网络源，无密钥，依赖 AkShare 可用性。 |
| `tushare` | `TushareProvider` | TuShare Pro，需要 `tushare_token`。 |
| `mysql` | `MysqlProvider` | 直连 MySQL 行情库。 |
| `postgresql` | `PostgresProvider` | 直连 PostgreSQL 行情库。 |
| `duckdb` | `DuckDbProvider` | 读取本地 DuckDB 行情库。 |
| `default` | `DataProvider` | 自备 HTTP 行情 API。 |

## 核心文件

- `src/utils/data_factory.py`：独立工厂入口。
- `src/utils/data_provider.py`：默认 HTTP API Provider。
- `src/utils/tushare_provider.py`：TuShare 数据源。
- `src/utils/akshare_provider.py`：AkShare 数据源。
- `src/utils/mysql_provider.py`：MySQL 数据源。
- `src/utils/postgres_provider.py`：PostgreSQL 数据源。
- `src/utils/duckdb_provider.py`：DuckDB 数据源。
- `src/utils/tdx_provider.py`：通达信数据源。

运行层也会直接构建 Provider：

- 回测：`src/core/backtest_cabinet.py`
- 实盘：`src/core/live_cabinet.py`
- 历史同步：`src/utils/history_sync_service.py`
- 配置中心连通性检查：`server.py`

## 依赖库

完整依赖以 `requirements.txt` 为准。独立使用 Provider 时常见依赖包括：

```bash
pip install pandas numpy requests tushare akshare pymysql psycopg2-binary duckdb pytdx
```

## 快速上手

```python
from datetime import datetime, timedelta

from src.utils.data_factory import DataFactory

factory = DataFactory(source="tdx")
provider = factory.get_provider()

code = "600519.SH"
end_time = datetime.now()
start_time = end_time - timedelta(days=5)

df = provider.fetch_minute_data(code, start_time, end_time)
print(df.head())

tick = provider.get_latest_bar(code)
print(tick)
```

使用 TuShare 时需要显式传 token，或通过项目配置读取：

```python
factory = DataFactory(source="tushare", tushare_token="YOUR_TUSHARE_TOKEN")
provider = factory.get_provider()
```

数据库、TDX、default API 的连接参数主要从 `config.json` / `config.private.json` 读取，不建议在业务代码里硬编码。

## Provider 接口约定

### `fetch_minute_data(code, start_time, end_time)`

获取指定时间段的历史分钟级 K 线数据。

- `code`：股票代码，如 `600036.SH`。
- `start_time`：开始时间，`datetime`。
- `end_time`：结束时间，`datetime`。
- 返回：`pandas.DataFrame`，至少应能归一化出 `dt/open/high/low/close/vol/amount`。

### `get_latest_bar(code)`

获取指定股票最新行情。

- `code`：股票代码。
- 返回：`dict`，至少包含 `dt/open/high/low/close/vol/amount` 中的行情字段。

### `check_connectivity(code)`

部分 Provider 实现了连通性检查，配置中心会优先调用该方法。

- 返回：`(ok, message)`。
- 如果 Provider 未实现该方法，服务端会使用轻量行情请求做兜底检查。

## 注意事项

- `DataFactory` 是轻量入口；项目主流程更常通过 `BacktestCabinet`、`LiveCabinet` 和 `HistoryDiffSyncService` 构建 Provider。
- `tdx` 不会自动下载本地 `vipdoc` 文件；本地模式依赖通达信已经下载好的数据，网络节点模式则从 TDX 节点读取。
- 数据库类 Provider 的表名配置为 `data_provider.mysql_table_*`、`data_provider.postgres_table_*`、`data_provider.duckdb_table_*`。
- 私密字段不要写入公共文档或仓库，放到 `config.private.json` 或 `CONFIG_PRIVATE_PATH` 指向的文件。
