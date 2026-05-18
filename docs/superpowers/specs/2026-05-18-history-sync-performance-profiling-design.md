# History Sync Performance Profiling Design

## 1. Background

当前增量同步链路已经具备以下能力：

- 运行时配置合并
- 多数据源抓取
- direct_db 目标库批量判重
- DuckDB 串行写线程
- 按股票检查点恢复
- 运行中状态快照与最终运行记录

在这条链路上，用户观察到“执行一次增量同步，越到后面越慢”。从当前实现判断，这种现象可能来自以下几类原因：

- 前半段并发先完成快股票，尾段只剩慢股票，形成长尾
- 目标库 existing keys 预取耗时偏高
- DuckDB 单写线程形成排队等待
- 某些数据源在大范围窗口下抓取更慢
- 进度按股票粒度更新，掩盖了内部阶段仍在推进

现有日志只能看到：

- 股票总进度
- 单股票总耗时
- 目标库批量判重总耗时
- writer flush 批次和队列峰值

这些信息仍不足以稳定回答“到底慢在源抓取、判重、排队还是落盘”。因此本设计引入一版最小侵入式性能剖析方案。

## 2. Goals And Non-Goals

### 2.1 Goals

- 在不改变同步业务行为的前提下，为现有链路增加阶段级性能可观测性
- 同时将性能信息输出到日志、运行中状态接口、最终 report/record
- 支持快速识别以下瓶颈：
  - 源数据构建慢
  - 目标库判重慢
  - DuckDB writer 排队等待慢
  - DuckDB 实际落盘慢
  - chunk 长尾明显
- 保持与现有 summary、code_report、table_report 结构兼容
- 保持对 API、MySQL、PostgreSQL、DuckDB 4 类写入路径的统一口径

### 2.2 Non-Goals

- 不修改现有同步接口的请求结构
- 不调整并发算法、判重算法和写入算法
- 不新增数据库表、CSV 明细文件或外部 tracing 组件
- 不实现自动优化策略，例如自动降并发、自动拆 chunk、自动调 writer 参数
- 不改动回测引擎、策略基类和策略执行逻辑

## 3. Design Principles

- 只加观测，不改行为
- 聚合优先，避免把运行记录撑爆
- 状态接口返回“够看问题”的指标，而不是全量诊断明细
- 所有耗时字段统一使用秒，字段后缀统一为 `_elapsed_sec`
- 对不适用的路径统一填 `0.0`，避免前端和调用方做复杂判空

## 4. Approach Selection

本次采用以下方案：

- 轻量埋点方案

核心思路如下：

- 在 `chunk`、`code`、`table`、`writer flush` 四个层级补耗时统计
- 在 `summary` 中保留聚合指标
- 在 `code_report` 和 `table_report` 中保留与当前股票直接相关的阶段耗时
- 在日志中保留关键节点的耗时输出
- 在运行中状态接口中保留轻量聚合统计和最近慢股票

未采用方案如下：

- 全量逐事件明细落盘：信息最全，但 reports 膨胀过快
- 接入专用 tracing 系统：过重，不符合当前 MVP
- 先做自动调优再补观测：风险高，无法先证明瓶颈位置

## 5. Scope Of Instrumentation

### 5.1 Chunk Level

目标是识别“是不是某些 chunk 的预取和处理特别慢”。

新增统计项：

- `existing_keys_prefetch_elapsed_sec`
- `chunk_elapsed_sec`
- `chunk_codes`
- `chunk_index`
- `chunk_total`

接入位置：

- `_prefetch_existing_keys_for_chunk()`
- `_run_sync_impl()` 的 `for chunk_index, code_chunk in enumerate(...)` 循环

### 5.2 Code Level

目标是识别“是不是尾段只剩慢股票”。

新增统计项：

- `code_elapsed_sec`
- `source_build_elapsed_sec`
- `tables_elapsed_sec`

接入位置：

- `_process_code_sync()`

### 5.3 Table Level

目标是区分“判重慢、排队慢、落盘慢”。

新增统计项：

- `existing_keys_count`
- `dedup_elapsed_sec`
- `write_wait_elapsed_sec`
- `write_exec_elapsed_sec`

说明：

- `dedup_elapsed_sec` 指单表从拿到 existing keys 到计算出 `missing_df` 的时间
- `write_wait_elapsed_sec` 指提交写入任务后等待结果返回的时间
- `write_exec_elapsed_sec` 指真正执行写入所消耗的时间

接入位置：

- `_process_code_sync()`
- `_submit_duckdb_write_task()`
- `DuckDbSerialWriter._flush_bucket()`

### 5.4 Writer Level

目标是确认 DuckDB writer 是否形成单点瓶颈。

新增统计项：

- `writer_total_flush_rows`
- `writer_last_flush_elapsed_sec`
- `writer_max_flush_elapsed_sec`

已有统计项继续保留：

- `writer_flush_batches`
- `writer_flushed_codes`
- `writer_queue_peak_size`

接入位置：

- `DuckDbSerialWriter._flush_bucket()`
- `_run_sync_impl()` 收尾与运行中 summary 更新

## 6. Data Model Changes

### 6.1 Summary

在当前 `summary` 基础上新增以下字段：

- `total_source_build_elapsed_sec`
- `total_existing_keys_prefetch_elapsed_sec`
- `total_dedup_elapsed_sec`
- `total_write_wait_elapsed_sec`
- `total_write_exec_elapsed_sec`
- `max_code_elapsed_sec`
- `max_chunk_elapsed_sec`
- `writer_total_flush_rows`
- `writer_last_flush_elapsed_sec`
- `writer_max_flush_elapsed_sec`
- `slow_codes_topn`

字段说明：

- `total_source_build_elapsed_sec`：所有股票源数据构建耗时累计
- `total_existing_keys_prefetch_elapsed_sec`：所有 chunk 目标库判重预取耗时累计
- `total_dedup_elapsed_sec`：所有表的缺失行判定耗时累计
- `total_write_wait_elapsed_sec`：所有表等待写线程或同步写接口返回的累计耗时
- `total_write_exec_elapsed_sec`：所有表实际执行写入的累计耗时
- `max_code_elapsed_sec`：单只股票最大总耗时
- `max_chunk_elapsed_sec`：单个 chunk 最大总耗时
- `slow_codes_topn`：最近维护的慢股票 Top N 列表

### 6.2 Code Report

在现有 `code_report` 基础上新增：

- `code_elapsed_sec`
- `source_build_elapsed_sec`
- `tables_elapsed_sec`

### 6.3 Table Report

在现有 `table_report` 基础上新增：

- `existing_keys_count`
- `dedup_elapsed_sec`
- `write_wait_elapsed_sec`
- `write_exec_elapsed_sec`

### 6.4 Slow Codes TopN

`slow_codes_topn` 结构定义为：

```json
[
  {
    "code": "000001.SZ",
    "code_elapsed_sec": 12.34,
    "source_rows": 3200,
    "missing_rows": 800
  }
]
```

约束如下：

- 仅保留 Top 10
- 以 `code_elapsed_sec` 倒序维护
- 只保存轻量字段，避免重复嵌套全量 `code_report`

## 7. Runtime Output Strategy

### 7.1 Logs

日志新增以下内容：

- chunk 判重开始与完成时输出：
  - `chunk_index`
  - `chunk_total`
  - `chunk_codes`
  - `existing_keys_prefetch_elapsed_sec`
- 每只股票完成时输出：
  - `code_elapsed_sec`
  - `source_build_elapsed_sec`
  - `tables_elapsed_sec`
- 慢股票告警增加：
  - `write_wait_elapsed_sec`
  - `write_exec_elapsed_sec`
- writer flush 日志输出：
  - `table`
  - `interval`
  - `task_count`
  - `flush_rows`
  - `flush_elapsed_sec`

### 7.2 Active Status

运行中状态接口保留以下内容：

- summary 聚合统计
- `slow_codes_topn`
- 现有 `code_reports`

不放入以下内容：

- 全量 chunk 历史明细
- 全量 writer flush 明细

原因：

- 状态接口是高频轮询入口，明细过多会拉高内存和序列化成本

### 7.3 Final Report And Record

最终 report/record 保留：

- 全量 `code_reports`
- 聚合后的新增 summary 字段
- `slow_codes_topn`

不新增单独诊断文件，继续沿用现有 `record_*.json` 与 `detail_*.csv` 体系。

## 8. Detailed Integration Points

### 8.1 `_prefetch_existing_keys_for_chunk()`

新增逻辑：

- 记录函数开始时间
- 完成后返回结果前计算 `existing_keys_prefetch_elapsed_sec`
- 将耗时写入 chunk 级临时结果，供 `_run_sync_impl()` 汇总

说明：

- 当前该函数只返回 `existing_keys_by_table`
- 首版建议返回：
  - `existing_keys_by_table`
  - `chunk_profile`

如果不想改返回结构，也可以在 `_run_sync_impl()` 外围单独计时。推荐后者，改动更小。

### 8.2 `_process_code_sync()`

新增逻辑：

- 统计 `source_build_elapsed_sec`
- 统计每张表的 `dedup_elapsed_sec`
- 统计每张表的 `write_wait_elapsed_sec`
- 统计每张表的 `write_exec_elapsed_sec`
- 汇总得到 `tables_elapsed_sec`
- 返回 `code_elapsed_sec`

### 8.3 `_submit_duckdb_write_task()`

新增逻辑：

- 在提交后、等待 future 前后记录等待耗时
- 将 writer 返回的执行耗时透传给表级 report

返回结构从当前：

```json
{
  "code": "000001.SZ",
  "table": "dat_1mins",
  "written_rows": 100
}
```

扩展为：

```json
{
  "code": "000001.SZ",
  "table": "dat_1mins",
  "written_rows": 100,
  "write_exec_elapsed_sec": 0.42
}
```

### 8.4 `DuckDbSerialWriter._flush_bucket()`

新增逻辑：

- 记录单次 flush 的开始和结束时间
- 统计本次 flush 的总行数
- 更新 writer 累计统计字段
- 将 `write_exec_elapsed_sec` 回写到本批次各任务结果中

注意：

- 单次 flush 的执行耗时是批次级数据
- 首版允许把同一批次耗时平均或整体透传给该批次任务
- 为了保持简单，建议直接把整批 flush 耗时透传给每个任务
- 后续若要更精细，可再拆分为任务占比时间

### 8.5 `_append_code_report_to_summary()`

新增逻辑：

- 汇总各表级耗时到 summary
- 更新 `max_code_elapsed_sec`
- 维护 `slow_codes_topn`

### 8.6 `_run_sync_impl()`

新增逻辑：

- 在 chunk 循环外统计 chunk 总耗时
- 汇总 chunk 预取耗时
- 汇总 `max_chunk_elapsed_sec`
- 每次处理完股票后把 writer 新增聚合字段同步到当前 summary

## 9. Compatibility Rules

- 所有新增字段都应为可选增强，不影响旧调用方读取现有字段
- 非 DuckDB 路径的 `writer_*` 新字段统一为 `0` 或 `0.0`
- 非 direct_db 路径的 `existing_keys_prefetch` 聚合耗时仍然允许记录
- API 写入路径没有单独 writer，`write_wait_elapsed_sec` 与 `write_exec_elapsed_sec` 可以统一以调用 `_push_rows()` 的总耗时表达

## 10. Error Handling

- 埋点失败不能影响同步主流程
- 只允许使用 `time.perf_counter()` 等轻量操作，不引入新依赖
- 若某个耗时统计值异常，回退到 `0.0`
- writer 返回结构向后兼容，缺少 `write_exec_elapsed_sec` 时按 `0.0` 处理

## 11. Testing Strategy

本次不追求新增大量低价值测试，而是补最关键的回归覆盖。

建议新增或更新以下测试：

- `HistoryDiffSyncService._process_code_sync()`：
  - 返回 `source_build_elapsed_sec`
  - 返回表级 `dedup_elapsed_sec`
  - 返回表级 `write_wait_elapsed_sec`
  - 返回表级 `write_exec_elapsed_sec`
- `DuckDbSerialWriter`：
  - flush 后能回传 `write_exec_elapsed_sec`
  - 能累积 `writer_total_flush_rows`
  - 能更新 `writer_max_flush_elapsed_sec`
- summary 聚合：
  - 能正确汇总新增耗时字段
  - 能维护 `slow_codes_topn`

手工验证重点如下：

- 日志能直观看到 chunk、code、writer 三层耗时
- status 接口返回的 `active_report` 中包含新增 summary 聚合字段
- 最终 `record_*.json` 中可看到新增 summary 字段和 code/table 耗时字段

## 12. Risks

- 如果把过多明细塞进 `code_reports`，最终 record 文件会变大
- 把整批 flush 耗时回写给每个任务会有一定统计放大，但对首版定位问题足够
- 由于当前进度按股票粒度更新，尾段“体感变慢”仍可能存在，只是现在可以被解释清楚

## 13. Implementation Boundary

本设计首版只修改以下文件：

- `src/utils/history_sync_service.py`

如无必要，不修改：

- `src/utils/duckdb_provider.py`
- 配置文件结构
- 前端页面与 API 路由

## 14. Expected Outcome

完成后，一轮增量同步至少可以清晰回答以下问题：

- 哪个 chunk 最慢
- 哪只股票最慢
- 是源数据构建慢、判重慢、排队慢还是落盘慢
- DuckDB writer 是否成为尾部瓶颈
- 当前“越到后面越慢”是长尾正常现象，还是某一阶段真实退化

这为后续第二阶段优化提供稳定依据，例如：

- keyset pagination 替代 `OFFSET`
- 按表或按股票重新分配 chunk
- 调整 DuckDB writer 批次参数
- 按瓶颈类型做自动化调优
