# 数据库设计说明（使用 `patent_id` 文本作为主键）

## 总体概述

本数据库用于存储从 SerpApi 获取到的**专利及其相关信息**。与传统做法不同的是，这里**将 `patent_id`（如 `"US20180044418A1"`）用作主键**，而非额外的自增整数 ID。这样所有子表在引用专利时也会存储 `patent_id` 字段，查询和理解更直观。

1. **数据库引擎**: 以 **SQLite** 作为示例（在 MySQL、PostgreSQL 等环境下也只需小改）。  
2. **数据来源**: 通常是 JSON(L) 文件，每条记录包含 `{"patent_id": ..., "data": {...}}` 的结构。  
3. **核心思想**:
   - 主表 `patents` 中，使用 `patent_id` (TEXT) 作为 **Primary Key**。  
   - 各子表以 `patent_id` (TEXT) 作外键进行关联，与主表保持一对多的结构。  
   - 若插入相同 `patent_id`，会触发唯一约束异常（或可用 `INSERT OR IGNORE` 处理重复）。

---

## 1. 专利主表：`patents`

存放最核心、最常查询的专利数据，以文本主键 `patent_id` 标识。

| 字段名             | 类型       | 说明                                                                          |
|-------------------|-----------|------------------------------------------------------------------------------|
| `patent_id`       | TEXT PK   | 文本主键，直接使用 JSON 顶层的 `patent_id` (如 `US20180044418A1`)           |
| `title`           | TEXT      | 专利标题                                                                      |
| `type`            | TEXT      | 专利类型（如 `"patent"`）                                                     |
| `pdf_link`        | TEXT      | 专利 PDF 链接（如来自 SerpApi 的 `pdf`）                                      |
| `publication_number` | TEXT   | 公开号（如 `US20180044418A1`）                                               |
| `country`         | TEXT      | 国家/地区（如 `"United States"`）                                             |
| `application_number` | TEXT   | 申请号                                                                        |
| `priority_date`   | DATETIME  | 优先日（字符串如 `"2016-05-23"` 转为 `YYYY-MM-DD 00:00:00`）                   |
| `filing_date`     | DATETIME  | 申请日                                                                        |
| `publication_date`| DATETIME  | 公告日/公开日                                                                 |
| `prior_art_date`  | DATETIME  | **现有技术基准日**（如果存在）                                                |
| `family_id`       | TEXT      | 家族 ID（若 JSON 中有该字段）                                                 |
| `abstract`        | TEXT      | 摘要                                                                           |
| `description_link`| TEXT      | 详细说明链接                                                                  |


---

## 2. 发明人表：`inventors`

记录专利的发明人列表。

| 字段名         | 类型       | 说明                                                           |
|----------------|-----------|----------------------------------------------------------------|
| `id`           | INTEGER PK AUTOINCREMENT | 自增主键                                                 |
| `patent_id`    | TEXT NOT NULL | 外键，引用 `patents(patent_id)`                              |
| `inventor_name`| TEXT      | 发明人姓名（`data["inventors"][*].name`）                        |
| `link`         | TEXT      | 发明人查询链接（可选）                                           |
| `serpapi_link` | TEXT      | SerpApi 发明人链接（可选）                                     |

**说明**  
- 对应 JSON 中的 `data["inventors"]`。  
- 可以通过 `patent_id` 查看具体对应哪条专利。

---

## 3. 受让人表：`assignees`

记录每条专利的受让人（申请权人/专利权人）。

| 字段名    | 类型       | 说明                                     |
|-----------|-----------|-----------------------------------------|
| `id`      | INTEGER PK AUTOINCREMENT | 自增主键                    |
| `patent_id` | TEXT NOT NULL | 外键，`patents(patent_id)`           |
| `name`    | TEXT       | 受让人名称（如 `"Merck Sharp & Dohme LLC"`） |

---

## 4. 关键字表：`prior_art_keywords`

记录现有技术关键词。

| 字段名       | 类型                         | 说明                                   |
|--------------|-----------------------------|---------------------------------------|
| `id`         | INTEGER PK AUTOINCREMENT    | 自增主键                              |
| `patent_id`  | TEXT NOT NULL              | 外键                                  |
| `keyword`    | TEXT                       | 关键词（如 `"cancer"`, `"tumor"`）      |

---

## 5. 事件表：`events`

存储专利事件（申请、公开、转让等）。

| 字段名         | 类型       | 说明                                                         |
|----------------|-----------|-------------------------------------------------------------|
| `id`           | INTEGER PK AUTOINCREMENT | 自增主键                                            |
| `patent_id`    | TEXT NOT NULL | 外键                                                     |
| `event_date`   | DATETIME   | 事件日期                                                  |
| `title`        | TEXT       | 事件标题（如 `"Application filed by..."`）                 |
| `type`         | TEXT       | 事件类型（`"filed"`, `"publication"`, `"legal-status"`, etc.）|
| `critical`     | INTEGER(0/1)| 是否关键事件                                              |
| `assignee_search` | TEXT   | 若事件中有受让人信息                                        |
| `description`  | TEXT       | 若是数组则拼接存储                                         |

---

## 6. 外部链接表：`external_links`

| 字段名       | 类型                        | 说明                                                   |
|--------------|----------------------------|-------------------------------------------------------|
| `id`         | INTEGER PK AUTOINCREMENT   | 自增主键                                              |
| `patent_id`  | TEXT NOT NULL             | 外键                                                  |
| `text`       | TEXT                       | 链接名称，如 `"USPTO"`                                 |
| `link`       | TEXT                       | URL                                                   |

---

## 7. 图片表：`images`

| 字段名       | 类型                         | 说明               |
|--------------|-----------------------------|--------------------|
| `id`         | INTEGER PK AUTOINCREMENT    | 自增主键           |
| `patent_id`  | TEXT NOT NULL              | 外键               |
| `image_url`  | TEXT                        | 图片链接           |

---

## 8. 分类表：`classifications`

| 字段名       | 类型                        | 说明                                        |
|--------------|----------------------------|--------------------------------------------|
| `id`         | INTEGER PK AUTOINCREMENT   | 自增主键                                   |
| `patent_id`  | TEXT NOT NULL             | 外键                                       |
| `code`       | TEXT                       | 分类代码（如 `"C07K16/2818"`）             |
| `description`| TEXT                       | 分类描述                                   |
| `leaf`       | INTEGER(0/1)               | 是否叶节点                                 |
| `first_code` | INTEGER(0/1)               | JSON 中 `first_code`                      |
| `is_cpc`     | INTEGER(0/1)               | 是否 CPC                                   |
| `additional` | INTEGER(0/1)               | 是否额外分类（`additional`）                |

---

## 9. 权利要求表：`claims`

| 字段名      | 类型                         | 说明                 |
|-------------|-----------------------------|----------------------|
| `id`        | INTEGER PK AUTOINCREMENT    | 自增主键             |
| `patent_id` | TEXT NOT NULL              | 外键                 |
| `claim_no`  | INTEGER                     | 权利要求序号         |
| `claim_txt` | TEXT                        | 权利要求内容         |

---

## 10. 优先权申请表：`applications_claiming_priority`

| 字段名                       | 类型       | 说明                                              |
|-----------------------------|-----------|--------------------------------------------------|
| `id`                        | INTEGER PK AUTOINCREMENT | 自增主键                       |
| `patent_id`                 | TEXT NOT NULL | 外键                              |
| `application_number`        | TEXT       | 申请号                           |
| `priority_date`             | DATETIME   | 优先日                           |
| `filing_date`               | DATETIME   | 申请日                           |
| `representative_publication`| TEXT       | 代表性公开号                     |
| `primary_language`          | TEXT       | 语言（如 `"en"`）                |
| `title`                     | TEXT       | 标题                              |

---

## 11. 世界范围专利申请表：`worldwide_applications`

| 字段名          | 类型                         | 说明                                                 |
|-----------------|-----------------------------|------------------------------------------------------|
| `id`            | INTEGER PK AUTOINCREMENT    | 自增主键                                             |
| `patent_id`     | TEXT NOT NULL              | 外键                                                 |
| `year`          | INTEGER                     | 年份（如 `2016`）                                    |
| `application_number` | TEXT                 | 申请号                                               |
| `country_code`  | TEXT                       | 国家/地区代码（`US`, `WO`等）                         |
| `document_id`   | TEXT                       | 文档 ID                                              |
| `filing_date`   | DATETIME                   | 申请日                                               |
| `legal_status`  | TEXT                       | 法律状态（如 `"Active"`）                             |
| `legal_status_cat` | TEXT                   | 法律状态分类（`"active"`, `"not_active"`, 等）        |
| `this_app`      | INTEGER(0/1)               | JSON 中的 `this_app`                                 |

---

## 12. 专利引用表：`patent_citations`

| 字段名            | 类型                      | 说明                                          |
|-------------------|---------------------------|----------------------------------------------|
| `id`              | INTEGER PK AUTOINCREMENT  | 自增主键                                     |
| `patent_id`       | TEXT NOT NULL            | 外键（引用主表 `patents(patent_id)`）         |
| `is_family_to_family` | INTEGER(0/1)         | family-to-family 引用                         |
| `publication_number`  | TEXT                 | 被引专利公开号                                 |
| `primary_language`    | TEXT                 | 语言                                          |
| `examiner_cited`      | INTEGER(0/1)         | 是否审查员引用                                |
| `priority_date`       | DATETIME             | 被引专利优先日                                |
| `publication_date`    | DATETIME             | 被引专利公开号日期                            |
| `assignee_original`   | TEXT                 | 原始受让人名称                                |
| `title`               | TEXT                 | 被引专利标题                                  |
| `serpapi_link`        | TEXT                 | 相关链接                                      |
| `patent_id_ref`       | TEXT                 | 被引专利的 ID，如 `patent/WO2015035112A1/en` |

---

## 13. 被引用表：`cited_by`

| 字段名            | 类型                      | 说明                                                  |
|-------------------|---------------------------|------------------------------------------------------|
| `id`              | INTEGER PK AUTOINCREMENT  | 自增主键                                             |
| `patent_id`       | TEXT NOT NULL            | 外键                                                 |
| `is_family_to_family` | INTEGER(0/1)         | 是否 family-to-family                                |
| `publication_number`  | TEXT                 | 引用本专利的专利公开号                               |
| `primary_language`    | TEXT                 | 主要语言                                             |
| `examiner_cited`      | INTEGER(0/1)         | 是否审查员引用                                       |
| `priority_date`       | DATETIME             | 优先日                                               |
| `publication_date`    | DATETIME             | 公告日期                                             |
| `assignee_original`   | TEXT                 | 原始受让人                                           |
| `title`               | TEXT                 | 标题                                                 |
| `serpapi_link`        | TEXT                 | 链接                                                 |
| `patent_id_ref`       | TEXT                 | 引用方专利 ID                                        |

---

## 14. 法律事件表：`legal_events`

| 字段名           | 类型                      | 说明                        |
|------------------|---------------------------|----------------------------|
| `id`             | INTEGER PK AUTOINCREMENT  | 自增主键                   |
| `patent_id`      | TEXT NOT NULL            | 外键                       |
| `date`           | DATETIME                 | 事件日期                   |
| `code`           | TEXT                     | 事件代码 (如 `AS`/`STPP`)   |
| `title`          | TEXT                     | 事件标题（如 `"Assignment"`）|
| `attributes_json`| TEXT                     | 属性 JSON（如 `attributes`） |

---

## 15. 化合物表：`concepts`

| 字段名     | 类型                         | 说明                                          |
|------------|-----------------------------|----------------------------------------------|
| `id`       | INTEGER PK AUTOINCREMENT    | 自增主键                                     |
| `patent_id`| TEXT NOT NULL              | 外键                                         |
| `concept_id` | TEXT                     | `data["concepts"]["match"][*].id`            |
| `domain`   | TEXT                        | 领域（如 `"Diseases"`）                      |
| `name`     | TEXT                        | 概念名称（如 `"Neoplasm"`）                   |
| `similarity`| REAL                       | 相似度                                       |
| `sections` | TEXT                        | 多段位置用 `";"` 拼接，如 `["title","claims"]`|
| `count`    | INTEGER                     | 出现次数                                     |
| `inchi_key`| TEXT                        | 化合物 InChI Key                             |
| `smiles`   | TEXT                        | SMILES                                        |

---

## 16. 子申请表：`child_applications`

记录子/继续申请数据。

| 字段名          | 类型                         | 说明                                        |
|-----------------|-----------------------------|--------------------------------------------|
| `id`            | INTEGER PK AUTOINCREMENT    | 自增主键                                   |
| `patent_id`     | TEXT NOT NULL              | 外键                                       |
| `application_number` | TEXT                   | 申请号                                      |
| `relation_type` | TEXT                        | 如 `"Continuation"`                         |
| `representative_publication` | TEXT           | 代表性公开号                               |
| `primary_language` | TEXT                     | 语言                                       |
| `priority_date` | DATETIME                    | 优先日                                     |
| `filing_date`   | DATETIME                    | 申请日                                     |
| `title`         | TEXT                        | 标题                                       |

---

## 17. 父申请表：`parent_applications`

| 字段名          | 类型                         | 说明                                         |
|-----------------|-----------------------------|---------------------------------------------|
| `id`            | INTEGER PK AUTOINCREMENT    | 自增主键                                    |
| `patent_id`     | TEXT NOT NULL              | 外键                                        |
| `application_number` | TEXT                   | 申请号                                      |
| `relation_type` | TEXT                        | 关系类型（如 `"Continuation"`）              |
| `representative_publication` | TEXT           | 代表性公开号                                |
| `primary_language` | TEXT                     | 语言                                        |
| `priority_date` | DATETIME                    | 优先日                                      |
| `filing_date`   | DATETIME                    | 申请日                                      |
| `title`         | TEXT                        | 标题                                        |

---

## 18. 优先权申请表：`priority_applications`

| 字段名                   | 类型                         | 说明                                        |
|--------------------------|-----------------------------|--------------------------------------------|
| `id`                     | INTEGER PK AUTOINCREMENT    | 自增主键                                   |
| `patent_id`             | TEXT NOT NULL              | 外键                                       |
| `application_number`     | TEXT                       | 申请号                                     |
| `representative_publication` | TEXT                  | 代表性公开号                                |
| `primary_language`       | TEXT                       | 语言                                       |
| `priority_date`          | DATETIME                  | 优先日                                     |
| `filing_date`            | DATETIME                  | 申请日                                     |
| `title`                  | TEXT                       | 标题                                       |

---

## 19. 非专利引证表：`non_patent_citations`

| 字段名        | 类型                         | 说明                                  |
|---------------|-----------------------------|--------------------------------------|
| `id`          | INTEGER PK AUTOINCREMENT    | 自增主键                             |
| `patent_id`   | TEXT NOT NULL              | 外键                                 |
| `citation_title` | TEXT                    | 引用文献标题                         |
| `examiner_cited` | INTEGER(0/1)            | 是否审查员引用                       |

---

## 20. 相似文档表：`similar_documents`

| 字段名          | 类型                         | 说明                                      |
|-----------------|-----------------------------|------------------------------------------|
| `id`            | INTEGER PK AUTOINCREMENT    | 自增主键                                 |
| `patent_id`     | TEXT NOT NULL              | 外键                                     |
| `is_patent`     | INTEGER(0/1)               | 是否专利                                 |
| `doc_patent_id` | TEXT                       | 如果是专利，这里存其 ID (如 `patent/US11734097B1/en`) |
| `serpapi_link`  | TEXT                       | SerpApi 链接                              |
| `publication_number` | TEXT                  | 公开/公开号                               |
| `primary_language`   | TEXT                  | 语言                                     |
| `publication_date`   | DATETIME              | 公布日期                                 |
| `title`              | TEXT                  | 标题                                     |

---

## 错误日志表：`error_logs`

| 字段名       | 类型                      | 说明                           |
|--------------|--------------------------|--------------------------------|
| `id`         | INTEGER PK AUTOINCREMENT | 自增主键                        |
| `error_message` | TEXT                  | 异常描述                        |
| `stack_trace`   | TEXT                  | 异常追溯栈                      |
| `created_at`    | DATETIME             | 记录插入时间                    |

---

## 数据流与插入逻辑

1. **读取 JSONL**：  
   - 每行形如 `{"patent_id": ..., "data": {...}}`。  
2. **插入主表**：  
   - 使用 `patent_id` (TEXT) 作为**主键**插入 `patents` 表。  
   - 如果相同 `patent_id` 重复插入，则违反主键约束（可改 `INSERT OR IGNORE` 视需求）。  
3. **插入子表**：  
   - 每个子表均有 `patent_id TEXT NOT NULL` + 外键 `REFERENCES patents(patent_id)`.  
   - 将 `patent_id` 传给对应的插入函数，**不再**需要 numeric ID。  
4. **查询时**：  
   - 直接在子表里查看 `patent_id` 就能识别专利文本 ID；若要关联获取其他专利字段（如 `title`），可做 `JOIN patents ON child_table.patent_id = patents.patent_id`。  

---

## 参考与扩展

- 若后续需要 **“插入或更新”** 同一个 `patent_id`，可使用 `INSERT OR REPLACE` 或 `UPSERT` 机制；  
- 若有性能需求，可在 `patent_id` 上建立索引（但它已是 PK 亦默认有索引）；  
- 如果 `patent_id` 存在更新场景（patent_id 可能会变化），要注意可能需维护引用关系。

---

**结论**：文档里最主要的改变就是把所有子表的“外键 `patent_id`”由原先 INTEGER 替换为 **TEXT** 并指出这是**引用 `patents(patent_id)`**，主表的主键为 `patent_id TEXT PRIMARY KEY`，不再有自增 `id`。