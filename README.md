# FL-paper-update-tracker

This project is a part of [Awesome-FL](https://github.com/youngfish42/Awesome-FL).  ![Stars](https://img.shields.io/github/stars/youngfish42/Awesome-FL.svg?color=orange)

An automated paper tracking bot for **Federated Learning** research. It periodically queries the [DBLP API](https://dblp.org/faq/How+to+use+the+dblp+search+API.html) for new publications across 40+ top-tier conferences and journals, deduplicates entries by their electronic edition (`ee`) field **and by title**, and automatically opens GitHub Issues to notify subscribers.

## Features

- **Broad Coverage**: Monitors 40+ leading venues in AI, ML, CV, NLP, Systems, Security, and more.
- **Smart Deduplication**: Uses the `ee` (electronic edition) field and the `title` field to eliminate duplicate records caused by minor author-name variations or multiple URLs for the same paper in DBLP.
- **Year-Based Filtering**: Only tracks papers published within the last 3 years and the next 1 year (e.g., 2023–2027 when running in 2026).
- **Auto-Notification**: Creates nicely formatted GitHub Issues daily via GitHub Actions.
- **Automatic Abstract Fetching**: Newly discovered papers automatically retrieve abstracts from Crossref, Semantic Scholar, and arXiv (in that order) to enrich the cache.
- **Automatic Chinese Translation**: Successfully retrieved abstracts are automatically translated into Chinese via Qwen-MT-plus and stored as `abstract_cn`.

## Extending to Other Research Domains

This tracker is not limited to Federated Learning. The domain keyword is controlled by a single field in `config.yaml`:

```yaml
dblp:
  keyword: federate          # <-- change this to any research term
  queries:
    - "venue:IJCAI:"
    - "venue:ICML:"
    # ... adjust venue list as needed
```

To switch to a new domain (e.g., *diffusion models*, *LLM*, *reinforcement learning*):

1. **Change the keyword** — edit `config.yaml` → `dblp.keyword`.
2. **Adjust the venue list** — keep, add, or remove entries under `dblp.queries`.
3. **Update category mappings** — edit `scripts/convert_cache_to_md.py` so that venue names and categories match your new domain.
4. **Reset the cache** — delete or rename `cached/dblp.yaml` so the next run treats every paper as new.

No other code changes are required.

## Supported Conferences & Journals

**AI & Machine Learning** — IJCAI, AAAI, AISTATS, ALT, AI, NeurIPS, ICML, ICLR, COLT, UAI, Machine Learning, JMLR, IEEE TPAMI

**Data Mining, Information Retrieval & Web** — KDD, WSDM, SIGIR, WWW

**Computer Vision & Multimedia** — CVPR, ICCV, ECCV, ACM MM, IJCV

**Natural Language Processing** — ACL, NAACL-HLT, EMNLP, COLING

**Security & Privacy** — IEEE S&P, CCS, USENIX Security, NDSS

**Systems, Architecture & Databases** — OSDI, SOSP, ISCA, MLSys, EuroSys, SIGMOD, ICDE, VLDB, ACM TOCS, ACM TOS

**Networking** — SIGCOMM, INFOCOM, MobiCom, NSDI

**Other Related Venues** — DAC, IEEE TPDS, IEEE TCAD, IEEE TC, ICSE, FOCS, STOC

> The venue list can be customized. For details, see [TECHNICAL.md](TECHNICAL.md).

## How to Get Notifications

### Watch the Main Repository 🚀
Click **Watch** on [Awesome-FL](https://github.com/youngfish42/Awesome-FL) to receive updates on new papers and major changes.

### Track Individual Issues (Optional)
Watch this repository if you want real-time alerts on paper submissions.

Note: Issues will be closed once merged into the main repo.

## Technical Details

For installation, configuration, workflow mechanics, and local development, please refer to [TECHNICAL.md](TECHNICAL.md).

## Thanks

This repository is based on [dblp-watcher](https://github.com/beiyuouo/dblp-watcher/). We use [DBLP API](https://dblp.org/faq/How+to+use+the+dblp+search+API.html) to search papers and construct a paper update tracker for federated learning.

---

# FL-paper-update-tracker（中文版）

本项目是 [Awesome-FL](https://github.com/youngfish42/Awesome-FL) 的配套子项目。

一个面向 **联邦学习** 研究的自动化论文追踪机器人。它定期通过 [DBLP API](https://dblp.org/faq/How+to+use+the+dblp+search+API.html) 查询 40 余个顶级会议与期刊的新发表论文，通过 `ee`（电子版链接）和 `title`（标题）字段智能去重，并自动创建 GitHub Issue 通知订阅者。

## 功能特性

- **覆盖广泛**：持续监控人工智能、机器学习、计算机视觉、自然语言处理、系统、安全等领域的 40+ 顶级学术会议与期刊。
- **智能去重**：利用 `ee`（电子版链接）和 `title`（标题）字段消除 DBLP 中因作者名称微差异或同一论文多版本链接导致的重复记录。
- **年份过滤**：仅追踪近三年及未来一年内发表的论文（例如 2026 年运行时，保留 2023–2027 年的论文）。
- **自动通知**：通过 GitHub Actions 每日自动生成格式化的 GitHub Issue。
- **自动获取摘要**：新发现的论文会自动从 Crossref、Semantic Scholar 和 arXiv 依次查询并补充摘要，以丰富缓存数据。
- **自动中文翻译**：成功获取的英文摘要会自动通过 Qwen-MT-plus 翻译为中文，存储为 `abstract_cn` 字段。

## 扩展到其他研究领域

本追踪器不限于联邦学习。领域关键词由 `config.yaml` 中的单个字段控制：

```yaml
dblp:
  keyword: federate          # <-- 修改此字段即可切换研究领域
  queries:
    - "venue:IJCAI:"
    - "venue:ICML:"
    # ... 按需增删会议/期刊
```

切换到新领域（例如 *扩散模型*、*大语言模型*、*强化学习*）的步骤：

1. **修改关键词** — 编辑 `config.yaml` → `dblp.keyword`。
2. **调整会议/期刊列表** — 在 `dblp.queries` 中保留、添加或删除条目。
3. **更新类别映射** — 编辑 `scripts/convert_cache_to_md.py`，使其 venue 名称与类别匹配新领域。
4. **重置缓存** — 删除或重命名 `cached/dblp.yaml`，下次运行将重新抓取全部论文。

无需修改其他代码。

## 支持的会议与期刊

**人工智能与机器学习** — IJCAI、AAAI、AISTATS、ALT、AI、NeurIPS、ICML、ICLR、COLT、UAI、Machine Learning、JMLR、IEEE TPAMI

**数据挖掘、信息检索与网络** — KDD、WSDM、SIGIR、WWW

**计算机视觉与多媒体** — CVPR、ICCV、ECCV、ACM MM、IJCV

**自然语言处理** — ACL、NAACL-HLT、EMNLP、COLING

**安全与隐私** — IEEE S&P、CCS、USENIX Security、NDSS

**系统、体系结构与数据库** — OSDI、SOSP、ISCA、MLSys、EuroSys、SIGMOD、ICDE、VLDB、ACM TOCS、ACM TOS

**计算机网络** — SIGCOMM、INFOCOM、MobiCom、NSDI

**其他相关领域** — DAC、IEEE TPDS、IEEE TCAD、IEEE TC、ICSE、FOCS、STOC

> 追踪列表支持自定义，详情请见 [TECHNICAL.md](TECHNICAL.md)。

## 如何获取通知

### 关注主仓库 🚀
点击 [Awesome-FL](https://github.com/youngfish42/Awesome-FL) 的 **Watch** 按钮，以接收新论文和重要更新的通知。

### 关注本仓库的 Issue（可选）
如果你希望获得论文提交的实时提醒，可以 Watch 本仓库。

注意：Issue 会在论文合并到主仓库后关闭。

## 技术细节

有关安装部署、配置文件、工作流程机制及本地开发说明，请参阅 [TECHNICAL.md](TECHNICAL.md)。

## 致谢

本仓库基于 [dblp-watcher](https://github.com/beiyuouo/dblp-watcher/) 构建。我们使用 [DBLP API](https://dblp.org/faq/How+to+use+the+dblp+search+API.html) 检索论文，并构建了面向联邦学习的论文更新追踪器。
