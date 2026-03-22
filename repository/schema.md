# 向量存储与元数据设计（Chroma）

本文描述企业级 AI 助手在 **Chroma** 中的逻辑划分：**按业务域拆分为多个 Collection（集合）**，每个集合内以 **Document（片段）** 为向量检索单元，**Metadata** 存放可过滤、可展示的结构化信息。

> 说明：Chroma 中「表」对应 **Collection**；一条可检索记录对应 **一条 Document**（含一段用于 embedding 的文本 + metadata）。若原文较长，需先 **切分 Chunk**，每条 Chunk 一条 Document。

---

## 设计原则（结合业务）

| 原则 | 说明 |
|------|------|
| 业务分域 | 与产品能力一致：C++ 头文件、Bug、培训/设计文档、行政制度，**分 Collection**，避免检索时跨域噪声。 |
| 可溯源 | 每条记录能回到 **源文件 / Bug 单号 / 制度文件名**，便于人工核对与合规。 |
| 向量内容 | **被 embedding 的文本**应与用户提问语义一致：说明类、描述类、条款正文；纯主键、日期等放 metadata，不必强行拼进向量（除非要做关键词级混合检索）。 |
| 层级文档 | 培训、设计、行政等多为 **长文档**，采用 **父子 Chunk 索引**，支持「先定位章节再精读」与上下文扩展。 |

---

## 通用约定（各 Collection 建议共用）

以下字段可在各集合的 metadata 中按需出现，便于统一管道与权限扩展：

| 字段 | 类型建议 | 必填 | 说明 |
|------|----------|------|------|
| `doc_id` | string | 建议 | 业务侧稳定文档 ID（同一文件多 Chunk 共享）。 |
| `chunk_id` | string | 建议 | 全局或集合内唯一，**主键级**检索用。 |
| `parent_chunk_id` | string \| null | 否 | 父片段 ID；根节点为 `null`。 |
| `chunk_index` | int | 否 | 同一文档内顺序（0,1,2…）。 |
| `title` / `topic` | string | 否 | 文档或章节标题，便于展示。 |
| `record_date` | string (ISO-8601 日期) | 否 | 文件版本日、发布日或入库日。 |
| `updated_at` | string (ISO-8601) | 否 | 本条记录最后更新时间。 |

权限、密级若后续需要，可增加 `tenant_id`、`classification` 等，与网关统一校验。

---

## 1. Collection：`cpp_headers`（C++ 头文件符号 / API）

**业务目标**：仅基于 **头文件** 做语义检索（声明、注释），不涉及 `.cpp` 实现，支撑「找 API、找声明」。

**向量文本建议**：符号的 **声明摘要 + 注释/文档块**（若有）；可附带命名空间、模板参数等可读片段。

| 字段 | 类型建议 | 必填 | 说明 |
|------|----------|------|------|
| `file_name` | string | **是** | 头文件路径或文件名（与仓库一致）。 |
| `symbol_name` | string | **是** | 函数名 / 类名 / 宏名等检索主键。 |
| `symbol_kind` | string | 建议 | 如 `function`、`class`、`enum`、`typedef`、`macro`。 |
| `signature` | string | 否 | 完整声明行，便于区分重载。 |
| `doc_year_month` | string | 否 | `YYYY-MM`，来自文件或提交；无则空。 |

**设计说明**：

- 「方法的描述」若指导出向量：实际入库时即 **本条 Document 的 document 文本**（或 `page_content`），metadata 存上述结构化字段。
- 同一符号若在多个头文件出现（转发声明等），可用 `chunk_id` + `file_name` + `symbol_name` 区分，避免误合并。

---

## 2. Collection：`bugs`（缺陷与回归相关）

**业务目标**：相似 Bug 检索、根因与修复路径参考、回归测试描述匹配。

**向量文本建议**：**测试描述**、**开发/分析描述** 可分别建 **两条 Document**（共享 `bug_id`），metadata 用 `text_role: test | dev` 区分；或合并为一条并在正文内用标题分段（实现更简单，检索粒度略粗）。

| 字段 | 类型建议 | 必填 | 说明 |
|------|----------|------|------|
| `bug_id` | string | **是** | 与缺陷系统一致的主键。 |
| `created_at` | string | 建议 | 提出时间。 |
| `resolved_at` | string \| null | 否 | 未解决则为 `null`。 |
| `status` | string | 建议 | 如 `open`、`resolved`、`closed`。 |
| `component` / `module` | string | 否 | 模块，过滤用。 |
| `root_cause` | string | 否 | **问题定性**（分类标签或短句，可检索可过滤）。 |
| `related_bug_ids` | string (JSON 数组) | 否 | 关联 Bug ID 列表。 |
| `text_role` | string | 若拆条 | `test` / `dev` / `merged`，标识本条向量对应哪段描述。 |

**设计说明**：

- 若 Jira 等系统已有附件或长评论，可只索引摘要字段，避免噪声。
- 关联 Bug 除存 ID 列表外，可在图数据库或关系库维护边；向量库以 **metadata 可查** 为最低要求。

---

## 3. Collection：`knowledge_docs`（培训资料 + 开发/设计文档）

**业务目标**：非结构化知识检索（培训、技术设计、会议/PPT 转写等），与行政制度分域。

**结构**：**父子 Chunk**。

| 字段 | 类型建议 | 必填 | 说明 |
|------|----------|------|------|
| `file_name` 或 `topic` | string | **至少其一** | 文件名或课程/文档主题。 |
| `record_date` | string | 建议 | 版本或发布日期。 |
| `parent_chunk_id` | string \| null | 建议 | 父片段；根为 `null`。 |
| `domain` | string | 建议 | `training`（培训） / `design`（设计）等，**同一 Collection 内用 metadata 区分**即可，也可拆成两个 Collection（按数据量与权限决定）。 |
| `section_title` | string | 否 | 当前 Chunk 对应小节标题，增强展示与重排。 |

**向量文本建议**：该 Chunk 的 **正文片段**（保持段落完整，避免半句）。

**设计说明**：

- 父子索引用于 **扩展上下文**（父节点摘要 + 子节点细节）与 **按文档浏览**；`chunk_index` 保证顺序。
- PPT/会议纪要可先按页或按话题切分，再挂到 `topic` 下。

---

## 4. Collection：`policies`（行政条例与组织信息）

**业务目标**：制度条款、办事流程、权责说明的语义检索。

**结构**：与 `knowledge_docs` 相同，**父子 Chunk**（章—节—条）。

| 字段 | 类型建议 | 必填 | 说明 |
|------|----------|------|------|
| `file_name` 或 `topic` | string | **至少其一** | 制度名称或通知主题。 |
| `record_date` | string | 建议 | 发布或修订日期，**回答中常需「以最新为准」**。 |
| `parent_chunk_id` | string \| null | 建议 | 父片段 ID；根为 `null`。 |
| `issuer` | string | 否 | 发布部门（如人力资源部、行政部）。 |
| `clause_id` | string | 否 | 条、款、项编号（若有）。 |
| `section_title` | string | 否 | 条款/小节标题（可与正文分离存放，便于展示与重排）。 |

**向量文本建议**：**条款正文**；标题可作为首句或写入 `section_title` metadata。

**设计说明**：

- 行政类对 **时效与版本** 敏感，**`record_date` + `source_uri`** 强烈建议必填其一或双填。
- 与 `knowledge_docs` 分 Collection，减少检索串域（如用户问「年假」时不混入无关技术文档）。

---

## Collection 命名小结

| Collection 名称 | 对应业务 |
|-------------------|----------|
| `cpp_headers` | C++ 头文件 API / 符号 |
| `bugs` | Bug 与回归相关描述 |
| `knowledge_docs` | 培训 + 开发/设计（可用 `domain` 区分） |
| `policies` | 行政条例与组织信息 |

命名可按环境加前缀，如 `prod_cpp_headers`。

---

## 与后续实现的衔接

- **Repository 层**：封装各 Collection 的写入、查询接口；metadata 字段与本文对齐，便于 **Pydantic / TypedDict** 在代码中固化。
- **Knowledge / 索引任务**：负责切分、embedding、写入；**Memory** 负责会话与多轮，**不替代**本文的存储 schema。
- **演进**：新增数据域时，优先 **新 Collection** 或 **新 `domain` 枚举**，避免单集合无限膨胀导致检索质量下降。

### 持久化目录（代码约定）

- Chroma ``PersistentClient`` 的本地数据默认落在 **`repository/chroma_db/`**（与代码包同级、单独子目录），由 ``repository/paths.py`` 中的 ``DEFAULT_CHROMA_PERSIST_DIR`` 定义。
- ``ChromaRepository()`` 不传参时使用上述路径；也可显式传入其它目录（如测试用临时目录）。
- ``repository/.gitignore`` 已忽略 ``chroma_db/``，避免向量库二进制文件进入版本库。
- 对应模型与 CRUD：``repository/models.py``、``repository/chroma_crud.py``、``repository/collections.py``。
- C++ 头文件语料解析与 BGE 入库：``repository/CppHeader/``（``parser.py`` 解析 ``RAG-corpus/Bugs``，``indexer.py`` 使用 ``BAAI/bge-large-zh-v1.5`` 写入 ``cpp_headers``；metadata 使用 ``CppHeaderMetadata``）。

---

## 修订记录（文档层）

- 润色表述，统一 Chroma 术语与业务对齐。
- 补全 Bug 状态、符号类型、父子 Chunk 通用字段、行政时效与发布方等，支撑检索过滤与合规展示。
