

---

# 🧬 PubMed Daily DeepReader

> **零成本、全自动的医学文献情报站**
> 🚀 **核心优势**：利用 **PubMed API** 抓取完整的结构化摘要（背景/方法/结果/结论），告别 RSS 的“残缺”信息，提供精准的中英对照阅读体验，并支持自定义域名访问。

## 📖 简介 (Introduction)

**PubMed Daily DeepReader** 是一个为医学科研人员打造的自动化文献追踪工具。

传统的 RSS 订阅往往只提供被截断的纯文本摘要，阅读体验极差。本项目通过 **Biopython** 直接调用 **PubMed Entrez API**，下载论文的原始 XML 数据，精准提取并分离 `Background`、`Methods`、`Results`、`Conclusion` 等段落，结合机器翻译生成排版精美的中文日报。

整个系统运行在 **GitHub Actions** 上，无需服务器，完全免费。

---

## 🔗 在线访问

> **每日更新地址**: [https://fclynmedical.de5.net](https://www.google.com/search?q=https://fclynmedical.de5.net)

---

## ✨ 核心功能 (Key Features)

* **🔍 API 深度抓取**：不仅仅是 RSS 搬运工。系统利用 PMID 调用 API 获取官方结构化数据，确保摘要完整、分段清晰。
* **🇨🇳 智能中英对照**：
* **结构化翻译**：自动识别段落标签（如 **RESULTS**），强制加粗换行，避免翻译引擎混淆结构。
* **左右分栏**：左侧目录快速筛选，右侧详情深度阅读。
* **关键词提取**：自动获取并翻译 MeSH 关键词。


* **🌐 自定义域名支持**：内置 CNAME 自动生成逻辑，完美适配 Cloudflare 托管域名，防止部署后配置丢失。
* **📂 便捷订阅管理**：无需修改代码，只需编辑 `feeds.txt` 文本文件即可增删订阅源。
* **⚡ 全自动运行**：
* 📅 **每日定时**：北京时间每天早上 08:00 自动抓取更新。
* 🔄 **即时触发**：修改订阅列表后立即自动重新生成。



---

## 🚀 日常使用指南

### 如何添加或删除订阅？

你不需要懂编程，只需要像写记事本一样操作：

1. 在 GitHub 仓库中打开 **`feeds.txt`** 文件。
2. 点击右上角的 **✏️ (Edit)** 按钮。
3. 粘贴你的 PubMed RSS 链接（一行一个）。
* *提示：在 PubMed 搜索关键词 -> Create RSS -> 复制 XML 链接。*


4. 点击下方的 **Commit changes** 保存。
5. **等待约 1-2 分钟**，GitHub Actions 会自动运行，网页随即更新。

---

## 🛠️ 部署与维护 (Deployment)

如果您是 Fork 本项目自行搭建，请参考以下配置：

### 1. 基础设置

* **权限配置**：进入 `Settings` -> `Actions` -> `General`，在 `Workflow permissions` 中勾选 **Read and write permissions**。
* **Pages 设置**：进入 `Settings` -> `Pages`，Source 选择 `Deploy from a branch`，分支选 `main`，文件夹选 `/docs`。

### 2. 代码配置 (`main.py`)

为了确保系统稳定运行，请修改 `main.py` 顶部的配置区：

```python
# 1. 填入你的真实邮箱，防止被 PubMed API 封锁 IP
Entrez.email = "你的邮箱@example.com"

# 2. 填入你的自定义域名（如果不需要自定义域名，留空即可）
CUSTOM_DOMAIN = "你的域名.com"

```

### 3. 自定义域名配置 (Cloudflare)

如果你使用了 Cloudflare，请注意：

1. **DNS 设置**：添加 `CNAME` 记录，Name 填前缀（如 `paper`），Target 填 `你的用户名.github.io`。
2. **首次验证**：在 Cloudflare 将代理状态（小云朵）设为 **灰色 (DNS Only)**，等待 GitHub `Settings` -> `Pages` 显示 "DNS check successful" 后，再开启 **橙色 (Proxied)**。
3. **SSL 设置**：Cloudflare 的 SSL/TLS 模式必须选为 **Full** 或 **Full (Strict)**。

---

## 🤖 自动化原理

本系统的工作流如下：

1. **Trigger**: 每天定时 (Cron) 或 检测到 `feeds.txt` 变动 (Push)。
2. **Fetch RSS**: Python 读取订阅列表，获取最新文章的 ID (PMID)。
3. **Fetch API**: 使用 `Biopython` 向 NCBI Entrez API 批量请求 XML 数据。
4. **Parse & Translate**:
* 解析 XML 中的 `Label` 属性 (如 `Label="METHODS"`)。
* 调用 `Google Translator` 进行分段翻译。
* 组装 Markdown 格式文本。


5. **Auto CNAME**: 如果配置了域名，自动在输出目录生成 `CNAME` 文件。
6. **Deploy**: 自动将生成的网页推送到 `docs/` 目录，GitHub Pages 自动展示。

---

## ❓ 常见问题 (FAQ)

#### Q: 修改了 `feeds.txt` 但网页没变？

**A:** 请检查 Actions 页面。如果显示绿色对号，可能是浏览器缓存。请强制刷新页面 (Ctrl+F5) 或稍等几分钟 Cloudflare 缓存更新。

#### Q: 为什么 Actions 提示 "InvalidDNSError"？

**A:** 这是 GitHub Pages 首次验证域名时的常见错误。请去 Cloudflare 暂时关闭代理（变灰云），去 GitHub Pages 设置里重新保存域名，验证通过后再开代理。

#### Q: 文章太老没有摘要？

**A:** 结构化摘要依赖 PubMed 数据库收录。如果 API 返回空数据，系统会自动回退到 RSS 提供的简短描述。

---

## ⚠️ 免责声明

* 本项目仅供科研学术交流使用。
* 中文翻译由机器生成，准确性仅供参考，临床决策请务必以英文原文为准。
* 请遵守 NCBI/PubMed 的 [使用条款](https://www.ncbi.nlm.nih.gov/home/about/policies/)。

---

*Made with ❤️ by nssanc*
