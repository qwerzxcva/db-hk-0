# db-hk-0 — 港股日K数据仓

港股通标的 (~2072 只) 日K前复权数据, GitHub Actions 定时回补。

## 数据源
| 数据 | 来源 | 说明 |
|---|---|---|
| 日K (qfq) | 腾讯 `https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=hk{code},day,,,320,qfq` | 每次返回最近 320 根, 滚动窗口, 覆盖 ~16个月/次; 长史靠多轮回补拼接有限 (腾讯不带 end 参数翻页时港股最多 320 根)。恒指成分与热门票全史另走原 A股仓同款接口方式 |
| 标的名单 | 东财 datacenter-web `RPT_MUTUAL_HOLD` (MUTUAL_TYPE=003, HOLD_DATE=2026-09-30 快照) | 南向持仓覆盖 2072 只 ≈ 港股通标的池 (实际港股通 ~550 只为沪深两个名单, 此处为其并集上界, 含少量曾入选已剔除票) |
| 新浪备选 | `Market_Center.getHKStockData?node=qbgg_hk` | 全港 2815 只列表可用; 日K `CN_MarketData.getKLineData` 对 hk 前缀支持有限, 未启用 |

## 目录
- `symbols.json` — 标的名单 (含来源标注)
- `hk_worker.py` — worker: `python hk_worker.py [batch=300]`, 断点 `_done.txt`
- `wh/hk_daily/<year>.parquet` — 字段: symbol(hk######), date, open, close, high, low, volume
- `.github/workflows/backfill.yml` — 每 60 分钟跑一批 300 只, ~7 小时一整轮

## 样票验证 (2026-10-15)
| 票 | 收盘 | 行数(320日窗口) |
|---|---|---|
| hk00700 腾讯控股 | 417.80 | 320 |
| hk00005 汇丰控股 | 147.90 | 320 |
| hk03690 美团-W | 75.45 | 320 |

## 覆盖率
- 每只票每轮拉最近 320 个交易日 (qfq); 全史回补受限于腾讯接口窗口, 逐步积累。
- 字段来源: 腾讯 fqkline (前复权价, 成交量股数)。
