好的，我来整理完整的项目总结文档。这份文档将涵盖项目背景、架构设计、工程规范和目录结构，适合作为项目归档和交接文档。

---

## 项目总结文档

```markdown
# 数字化专家助手 - 项目总结文档

> 最后更新：2026-07-02
> 版本：v1.0.0

---

## 一、项目背景

### 1.1 项目目标

构建一个基于 **RAG（检索增强生成）** 架构的智能问答系统，为数字化项目实施交付团队提供 **7×24 小时** 的专家知识服务。

系统通过企业微信作为交互入口，用户以自然语言提问，系统自动识别问题领域，从知识库中检索相关文档，由大模型生成专业、可溯源的回答。

### 1.2 核心价值

| 价值点 | 说明 |
|--------|------|
| **知识沉淀** | 将分散在个人电脑、共享盘中的项目文档集中管理，形成结构化知识库 |
| **智能问答** | 7×24 小时在线，自动回答项目管理、采购合规、技术交付等领域的专业问题 |
| **知识溯源** | 每个回答都标注文档来源，支持点击查看原文，确保结果可验证、可追溯 |
| **降本增效** | 减少重复性咨询，释放专家精力，加速新人上手 |

### 1.3 七个专家领域

| 专家名称 | 英文标识 | 覆盖领域 |
|----------|---------|----------|
| 项目管理专家 | `project_mgmt` | 项目章程、WBS、风险识别、进度计划、变更管理 |
| 采购合规专家 | `procurement` | 采购流程、招投标法规、合同审核、合规风险 |
| 开发交付专家 | `dev_delivery` | 技术方案、代码规范、部署架构、测试验收 |
| 产品设计专家 | `product_design` | 用户需求、PRD、交互设计、用户体验 |
| 业务专家 | `business` | 行业方案、业务流程、客户案例、价值评估 |
| 系统运维专家 | `system_mgmt` | 监控告警、故障排查、运维自动化、应急预案 |
| 系统运维专家（别名） | `maintenance` | 运维保障、参数调优、系统安装 |

---

## 二、系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                     用户交互层（企业微信）                       │
│   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│   │ 单聊对话 │ │ 群聊@机器人│ │ 图文消息 │ │ 网页详情 │       │
│   └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     应用层（FastAPI 服务）                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    路由 & 中间件层                        │  │
│  │  /wecom/callback  │  /health  │  /answer/{id}  │ /docs │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                     消息处理层                           │  │
│  │  接收消息 → 解密 → 意图识别 → 异步处理 → 主动推送        │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    Agent 调度层                          │  │
│  │  路由引擎 → 7个专家Agent → Prompt 构造                  │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────────┐
│   推理引擎层     │ │   向量检索引擎   │ │   存储层            │
│   DeepSeek API  │ │   Qdrant       │ │  腾讯云 COS         │
│   (大模型推理)  │ │   (语义检索)    │ │  (文档存储)         │
└─────────────────┘ └─────────────────┘ └─────────────────────┘
```

### 2.2 数据存储

| 存储组件 | 用途 | 数据内容 |
|----------|------|----------|
| **腾讯云 COS** | 文档原始存储 | Word/Excel/PDF/PPT/TXT 等知识库文件 |
| **Qdrant 向量库** | 语义检索 | 文档切片后的向量 + 元数据 |
| **file_index.json** | 文件索引 | 文档名 → COS 路径的映射关系 |

### 2.3 COS 目录结构

```
knowledge_base/
├── 01-项目管理/
│   ├── 项目章程模板.docx
│   └── WBS分解指南.pdf
├── 02-采购合规/
│   ├── 合规八条宣贯材料V3.pdf
│   └── 项目合规风险点梳理1.0.xlsx
├── 03-开发交付/
│   └── ...
├── 04-产品设计/
│   └── ...
├── 05-业务知识/
│   └── ...
└── 06-运维保障/
    ├── 02-mysql 参数调优.pdf
    ├── 04-redis 参数调优.pdf
    └── 13-应急管理规范.docx
```

### 2.4 知识入库流程

```
┌─────────────────────────────────────────────────────────────────┐
│                        文档入库流程                             │
├─────────────────────────────────────────────────────────────────┤
│  1. PMO 上传文档到 COS（按目录分类）                            │
│         ↓                                                     │
│  2. 执行同步脚本：python src/scripts/sync_cos.py               │
│         ↓                                                     │
│  3. 脚本扫描 COS 目录，比对 file_index.json 识别变更            │
│         ↓                                                     │
│  4. 解析文档内容（支持 docx/pdf/pptx/xlsx/txt）                │
│         ↓                                                     │
│  5. 文本切片（chunk_size=500, overlap=50）                     │
│         ↓                                                     │
│  6. Embedding 向量化（BAAI/bge-base-zh-v1.5）                 │
│         ↓                                                     │
│  7. 存入 Qdrant 对应集合                                       │
│         ↓                                                     │
│  8. 更新 file_index.json                                       │
└─────────────────────────────────────────────────────────────────┘
```

### 2.5 用户问答流程

```
┌─────────────────────────────────────────────────────────────────┐
│                        问答交互流程                             │
├─────────────────────────────────────────────────────────────────┤
│  用户在企微发送消息                                              │
│         ↓                                                     │
│  企业微信回调 → 解密消息 → 提取用户问题                           │
│         ↓                                                     │
│  立即回复 "📥 已收到..."（异步处理）                             │
│         ↓                                                     │
│  意图识别 → 路由到对应专家                                      │
│         ↓                                                     │
│  RAG 检索：从 Qdrant 检索相关文档片段                           │
│         ↓                                                     │
│  构建 Prompt：System Prompt + 检索上下文 + 文档名列表 + 用户问题  │
│         ↓                                                     │
│  调用 DeepSeek API 生成回复                                     │
│         ↓                                                     │
│  判断回复长度：≤1200字符 → 文本消息；>1200字符 → 图文消息+详情页  │
│         ↓                                                     │
│  通过企业微信 API 主动推送回复                                   │
└─────────────────────────────────────────────────────────────────┘
```

### 2.6 超链接生成策略

系统支持 8 种文档名匹配策略，确保大模型返回的文档名能正确匹配到 COS 中的文档：

| 策略 | 大模型返回 | 索引中文档 | 匹配方式 |
|------|-----------|-----------|----------|
| 1. 精确匹配 | `13-应急管理规范.docx` | `13-应急管理规范.docx` | 完全一致 |
| 2. 去扩展名 | `13-应急管理规范` | `13-应急管理规范.docx` | 去掉 .docx |
| 3. 去掉编号前缀 | `应急管理规范V1.1` | `13-应急管理规范V1.1.docx` | 去掉 `13-` |
| 4. 去掉版本号 | `13-应急管理规范` | `13-应急管理规范V1.1.docx` | 去掉 `V1.1` |
| 5. 包含关系 | `应急管理规范` | `13-应急管理规范V1.1.docx` | 包含关系 |
| 6. 去掉中文括号 | `应急管理规范(正式版)` | `13-应急管理规范V1.1.docx` | 去掉括号 |
| 7. 提取纯名称 | `4、安全十条` | `06-安全十条.pdf` | 提取 `安全十条` |
| 8. 反向包含 | `运维应急管理规范` | `13-应急管理规范.docx` | 索引名包含核心词 |

---

## 三、工程实现

### 3.1 技术栈

| 分类 | 技术 | 版本 |
|------|------|------|
| Web 框架 | FastAPI + Uvicorn | FastAPI 0.115.6 |
| 大模型 | DeepSeek API | deepseek-v4-pro |
| 向量数据库 | Qdrant | 1.18.2 |
| Embedding | sentence-transformers | BAAI/bge-base-zh-v1.5 |
| 对象存储 | 腾讯云 COS | SDK v5 |
| 文本切片 | LangChain | 0.3.15 |
| 进程管理 | Gunicorn + systemd | Gunicorn 26.0.0 |

### 3.2 代码分支管理

#### 分支策略

```
wedrive-sync (开发/测试分支)
    │
    ├── 日常开发在此分支进行
    ├── 测试环境部署 → /opt/digital-expert/
    │
    └── 测试通过后 → 合并到 main
                         │
                         ▼
main (生产分支)
    │
    └── 生产环境部署 → /opt/digital-expert-pro/
```

#### 分支操作规范

| 操作 | 命令 |
|------|------|
| 日常开发 | `git checkout wedrive-sync` |
| 提交代码 | `git add . && git commit -m "描述" && git push origin wedrive-sync` |
| 测试通过合并 | `git checkout main && git merge --no-ff wedrive-sync -m "描述" && git push origin main` |
| 生产拉取 | `cd /opt/digital-expert-pro && git checkout main && git pull origin main` |

### 3.3 部署架构（双环境隔离）

```
┌─────────────────────────────────────────────────────────────────┐
│                      服务器 (腾讯云)                            │
├─────────────────────────────────────────────────────────────────┤
│  /opt/digital-expert/             测试环境 (wedrive-sync)      │
│  ├── 端口: 8005                                               │
│  ├── 域名: wecom.infohub.com.cn                               │
│  └── 企微: A企业（测试应用）                                   │
│                                                               │
│  /opt/digital-expert-pro/         生产环境 (main)              │
│  ├── 端口: 8006                                               │
│  ├── 域名: wecom.ds.cn                                         │
│  └── 企微: B企业（正式应用）                                   │
├─────────────────────────────────────────────────────────────────┤
│  共用组件: Qdrant (6333) ｜ COS (知识库文档)                   │
└─────────────────────────────────────────────────────────────────┘
```

### 3.4 服务管理

#### 方式一：nohup 手动启动（开发/调试）

```bash
# 测试环境
cd /opt/digital-expert && source venv/bin/activate
nohup uvicorn src.main:app --host 0.0.0.0 --port 8005 > logs/uvicorn.out 2>&1 &

# 生产环境
cd /opt/digital-expert-pro && source venv/bin/activate
nohup uvicorn src.main:app --host 0.0.0.0 --port 8006 > logs/uvicorn.out 2>&1 &
```

#### 方式二：systemd 服务（生产环境推荐）

```bash
# 启动
sudo systemctl start digital-expert-test   # 测试
sudo systemctl start digital-expert-prod   # 生产

# 状态
sudo systemctl status digital-expert-test
sudo systemctl status digital-expert-prod

# 日志
sudo journalctl -u digital-expert-test -f
sudo journalctl -u digital-expert-prod -f
```

### 3.5 日志管理

日志统一存放在各环境的 `logs/` 目录下：

| 日志文件 | 内容 | 轮转策略 |
|----------|------|----------|
| `digital_expert.log` | 应用业务日志 | 每天轮转，保留30天 |
| `digital_expert_error.log` | ERROR 级别日志 | 每天轮转，保留30天 |
| `digital_expert_access.log` | API 访问日志 | 每天轮转，保留7天 |
| `uvicorn.out` | Uvicorn 启动输出 | 手动管理 |

---

## 四、目录结构

### 4.1 测试环境（/opt/digital-expert/）

```
/opt/digital-expert/
├── src/
│   ├── agents/                    # Agent 模块
│   │   ├── __init__.py
│   │   ├── agents.py              # 7个专家 Agent 类定义
│   │   ├── base.py                # Agent 基类
│   │   ├── prompts.py             # 各专家 System Prompt
│   │   └── router.py              # 意图识别 + 路由引擎
│   │
│   ├── alert/                     # 告警模块
│   │   └── wecom_alert.py         # 企业微信告警通知
│   │
│   ├── core/                      # 核心业务逻辑
│   │   ├── __init__.py
│   │   └── chat_service.py        # 聊天服务（RAG + DeepSeek 整合）
│   │
│   ├── knowledge/                 # 知识库管理
│   │   ├── __init__.py
│   │   ├── folder_mapping.py      # COS目录 → Qdrant集合 映射
│   │   ├── index.py               # file_index.json 读写
│   │   ├── parser.py              # 文档解析（docx/pdf/pptx/xlsx/txt）
│   │   └── sync_cos.py            # COS → Qdrant 同步逻辑
│   │
│   ├── rag/                       # RAG 检索模块
│   │   ├── __init__.py
│   │   ├── ingest.py              # 文档入库（切片 + 向量化 + 写入Qdrant）
│   │   └── retriever.py           # 向量检索 + 来源生成
│   │
│   ├── scripts/                   # 命令行脚本
│   │   ├── create_wedrive_space.py
│   │   ├── health_check.py        # 健康检查（cron 定时）
│   │   ├── init_cos_dirs.py
│   │   ├── set_space_permission.py
│   │   ├── sync_cos.py            # 知识库同步入口
│   │   └── sync_wedrive.py
│   │
│   ├── utils/                     # 工具函数
│   │   ├── __init__.py
│   │   ├── config.py              # 环境变量读取（多环境支持）
│   │   ├── cos_api.py             # 腾讯云 COS SDK 封装
│   │   └── logger.py              # 日志配置
│   │
│   ├── wecom/                     # 企业微信集成
│   │   ├── __init__.py
│   │   ├── crypto.py              # 消息加解密
│   │   ├── handler.py             # 消息处理器（接收 + 回复）
│   │   └── sender.py              # 主动消息发送
│   │
│   └── main.py                    # FastAPI 应用入口
│
├── venv/                          # Python 虚拟环境
├── data/
│   └── file_index.json            # 文件索引（自动生成，不提交 Git）
├── logs/                          # 日志目录
├── .env                           # 环境变量配置（不提交 Git）
├── .env.example                   # 环境变量模板
├── requirements.txt               # Python 依赖
├── deploy.sh                      # 部署脚本
└── README.md
```

### 4.2 生产环境（/opt/digital-expert-pro/）

与测试环境目录结构相同，区别在于：

| 项目 | 测试环境 | 生产环境 |
|------|---------|----------|
| 路径 | `/opt/digital-expert/` | `/opt/digital-expert-pro/` |
| 分支 | `wedrive-sync` | `main` |
| 端口 | 8005 | 8006 |
| 域名 | `wecom.infohub.com.cn` | `wecom.ds.cn` |

---

## 五、环境变量说明

### 5.1 核心配置项

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `ACTIVE_ENV` | 当前环境 | `test` / `production` |
| `WECOM_{ENV}_CORP_ID` | 企业微信 CorpID | `wwxxxxx` |
| `WECOM_{ENV}_AGENT_ID` | 应用 AgentID | `1000001` |
| `WECOM_{ENV}_SECRET` | 应用 Secret | `xxxxx` |
| `WECOM_{ENV}_TOKEN` | 回调 Token | `xxxxx` |
| `WECOM_{ENV}_ENCODING_AES_KEY` | 回调加密 Key | 43位ASCII字符 |
| `WECOM_{ENV}_CALLBACK_DOMAIN` | 回调域名 | `wecom.ds.cn` |
| `DEEPSEEK_API_KEY` | DeepSeek API Key | `sk-xxxxx` |
| `QDRANT_HOST` | Qdrant 地址 | `localhost` |
| `QDRANT_PORT` | Qdrant 端口 | `6333` |
| `COS_SECRET_ID` | COS 密钥 ID | `AKIDxxxxx` |
| `COS_BUCKET` | COS 存储桶 | `bucket-1234567890` |
| `SERVER_PORT_{ENV}` | 服务端口 | `8005` / `8006` |

### 5.2 环境变量读取机制

`config.py` 根据 `ACTIVE_ENV` 自动添加后缀：

- `ACTIVE_ENV=test` → `WECOM_TEST_CORP_ID`
- `ACTIVE_ENV=production` → `WECOM_PROD_CORP_ID`

---

## 六、部署检查清单

| 步骤 | 操作 | 状态 |
|------|------|------|
| 1 | DNS 解析配置（wecom.ds.cn → 服务器IP） | ☐ |
| 2 | Caddy 反向代理配置 | ☐ |
| 3 | `.env` 文件配置（测试/生产各自独立） | ☐ |
| 4 | 代码拉取（测试 wedrive-sync / 生产 main） | ☐ |
| 5 | 虚拟环境创建 + 依赖安装 | ☐ |
| 6 | 知识库同步 `python src/scripts/sync_cos.py` | ☐ |
| 7 | 服务启动测试 `uvicorn src.main:app` | ☐ |
| 8 | systemd 服务配置 | ☐ |
| 9 | 企业微信回调配置 | ☐ |
| 10 | 消息收发测试 | ☐ |

---

## 七、常用运维命令

### 7.1 服务管理

```bash
# 测试环境
sudo systemctl start digital-expert-test
sudo systemctl stop digital-expert-test
sudo systemctl restart digital-expert-test
sudo systemctl status digital-expert-test

# 生产环境
sudo systemctl start digital-expert-prod
sudo systemctl stop digital-expert-prod
sudo systemctl restart digital-expert-prod
sudo systemctl status digital-expert-prod
```

### 7.2 日志查看

```bash
# systemd 日志
sudo journalctl -u digital-expert-test -f
sudo journalctl -u digital-expert-prod -f

# 业务日志
tail -f /opt/digital-expert/logs/digital_expert.log
tail -f /opt/digital-expert-pro/logs/digital_expert.log

# 访问日志
tail -f /opt/digital-expert/logs/digital_expert_access.log
```

### 7.3 知识库同步

```bash
cd /opt/digital-expert
source venv/bin/activate
export HF_ENDPOINT=https://hf-mirror.com
python src/scripts/sync_cos.py
```

### 7.4 健康检查

```bash
curl http://localhost:8005/health
curl http://localhost:8006/health
```

---

## 八、版本历史

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v1.0.0 | 2026-07-02 | 初始版本，完成双环境部署、7个专家、RAG检索、企微集成 |

---

*本文档随项目代码一起维护，如有更新请同步修改。*
```

---

## 保存到 Git

```bash
cd /opt/digital-expert
cat > DOCUMENTATION.md << 'EOF'
# 将上面的完整文档内容粘贴到这里
EOF

git add DOCUMENTATION.md
git commit -m "docs: 添加项目总结文档"
git push origin wedrive-sync

# 合并到 main
git checkout main
git merge wedrive-sync
git push origin main

# 同步到生产
cd /opt/digital-expert-pro
git pull origin main
```

文档已完整整理，涵盖了项目背景、架构设计、工程规范和目录结构四大板块。你可以根据实际需要调整或补充。
