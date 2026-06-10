# 文档目录索引

本文档说明 `docs/` 下的分类方式。新增文档时优先放入对应分类目录，避免继续堆在根目录。

## 分类目录

| 目录 | 用途 | 当前文档 |
| --- | --- | --- |
| `architecture/` | 项目结构、分层逻辑、模块边界、分包关系 | `项目结构与分层说明.md` |
| `api/` | HTTP API、接口参数、调用示例 | `API_DOCS.md` |
| `data/` | 数据源配置、历史库表结构、数据 Provider 说明 | `数据源配置指南.md`、`DATA_PROVIDER_README.md`、`历史数据源表结构.sql` |
| `guides/` | 面向使用者的操作指南和模板 | `批量回测操作指南.md`、`全局回测与实盘监控基线模板.md` |
| `evolution/` | 策略进化、多 Agent、基因运行持久化 | `新功能说明_事件驱动多Agent策略进化.md`、`evolution_gene_runs.sql` |
| `features/` | 具体功能专题说明 | `新功能说明_通达信_BLK_组合回测.md` |
| `operations/` | 仓库、发布、运维类流程 | `双库推送指南.md` |
| `superpowers/` | 历史计划和设计规格归档 | `plans/`、`specs/` |

## 放置规则

- 架构、目录职责、模块依赖边界放到 `architecture/`。
- 数据源、数据库表结构、同步链路配置放到 `data/`。
- API 说明统一放到 `api/`，避免散落在功能说明中。
- 面向用户执行步骤的文档放到 `guides/`。
- 策略进化相关设计、说明、SQL 放到 `evolution/`。
- 单个功能的发布说明或专题说明放到 `features/`。
- Git、远端仓库、发布流程、环境运维放到 `operations/`。
- `superpowers/` 是历史计划与设计归档，除修正路径引用外不参与日常文档重排。
