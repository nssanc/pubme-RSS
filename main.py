import feedparser
from deep_translator import GoogleTranslator
import time
from datetime import datetime
import os
import pytz
import json
import re

# ================= 配置区 =================
RSS_URLS = [
    # 在这里填入你的链接
    "https://pubmed.ncbi.nlm.nih.gov/rss/search/1p9j2Ia0knTignEE7vvWNCOPD-p8oHaBJk6HqSr1JJOMQoMsn2/?limit=100&utm_campaign=pubmed-2&fc=20260103012326",
    "https://pubmed.ncbi.nlm.nih.gov/rss/search/1PQPGz2gzLgNzuaNos66c7B3c89tbZUZXKYTEvBxn0Ttaa8QdR/?limit=100&utm_campaign=pubmed-2&fc=20260103012404",
    "https://pubmed.ncbi.nlm.nih.gov/rss/search/14OzJS8GjXZKNRRzPCpEeeWNsNMgy1WIuhFrUouU5lu4ZC2kX-/?limit=100&utm_campaign=pubmed-2&fc=20260103014642",
]
# =========================================

def process_text_structure(text):
    """
    对原始文本进行清洗和结构化处理：
    1. 去除 HTML 标签
    2. 识别 Background, Methods, Results, Conclusion 等关键词并加粗换行
    3. 提取 Keywords
    """
    if not text:
        return "", "", ""

    # 1. 基础清洗：去除 HTML 标签，将 <p>, <br> 转为换行
    text = text.replace("<b>", "").replace("</b>", "") # 去除原有加粗，后面统一处理
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'<p>', '\n', text)
    text = re.sub(r'</p>', '\n', text)
    text = re.sub(r'<.*?>', '', text) # 去除剩余所有 HTML 标签

    # 2. 提取 Keywords (通常在最后)
    keywords = ""
    keywords_match = re.search(r'(Keywords?:|Key words?:)(.*)', text, re.IGNORECASE | re.DOTALL)
    if keywords_match:
        keywords = keywords_match.group(2).strip()
        # 从正文中移除关键词部分，避免重复
        text = text[:keywords_match.start()]

    # 3. 去除版权信息 (Copyright ...)
    text = re.sub(r'Copyright ©.*', '', text, flags=re.IGNORECASE)

    # 4. 结构化分段 (给英文原文添加格式)
    # 常见的段落标题
    headers = [
        "Abstract", "Background and purpose", "Background", "Objective", "Purpose",
        "Materials and methods", "Methods", "Design",
        "Results", "Findings",
        "Conclusion", "Conclusions", "Discussion"
    ]
    
    structured_text = text.strip()
    # 为每个标题添加换行和标记，方便后续阅读
    for header in headers:
        # 使用正则查找单词边界，避免匹配到单词中间，比如 "Pre-methods"
        pattern = re.compile(r'(^|\n|\.\s)\s*(' + re.escape(header) + r')\s*[:\.]', re.IGNORECASE)
        structured_text = pattern.sub(r'\n\n🟢 \2: ', structured_text)

    return structured_text, keywords

def fetch_and_generate():
    output_dir = "docs"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    translator = GoogleTranslator(source='auto', target='zh-CN')
    
    all_feeds_data = {}
    
    print(f"准备抓取 {len(RSS_URLS)} 个订阅源...")

    for url in RSS_URLS:
        try:
            print(f"正在连接: {url[:40]}...")
            feed = feedparser.parse(url)
            feed_title = feed.feed.get('title', '未命名订阅源').replace("PubMed ", "")
            
            entries_data = []
            total_entries = len(feed.entries)
            
            print(f"--> [{feed_title}] 发现 {total_entries} 篇文章，开始处理...")

            for i, entry in enumerate(feed.entries):
                # 1. 标题处理
                title_en = entry.title
                try:
                    title_zh = translator.translate(title_en)
                except:
                    title_zh = title_en

                # 2. 摘要与关键词处理
                raw_description = entry.get('description', '')
                
                # 预处理：分离摘要正文和关键词，并进行结构化标记
                abstract_en_structured, keywords_en = process_text_structure(raw_description)
                
                # 3. 翻译摘要
                # 注意：为了保留结构，我们按换行符拆分翻译，然后再拼回去，
                # 这样可以防止翻译软件把 "Results:" 这种标题给吃掉或合并。
                abstract_zh_lines = []
                if abstract_en_structured:
                    # 简单截断防止过长
                    if len(abstract_en_structured) > 4500:
                        abstract_en_structured = abstract_en_structured[:4500] + "...(原文过长截断)"
                    
                    try:
                        # 整体翻译可能丢失格式，尝试直接翻译
                        # 小技巧：将自定义标记 🟢 替换为特殊字符，翻译后再换回来，或者直接翻译
                        # 这里为了稳定，直接翻译整段，但因为我们在英文中加了 \n\n，Google 翻译通常会保留换行
                        abstract_zh = translator.translate(abstract_en_structured)
                        
                        # 美化中文排版：将英文的结构词对应优化（如果翻译成功的话）
                        # 如果 Google 翻译把 "🟢 Results:" 翻译成了 "🟢 结果："，我们就能利用它
                        abstract_zh = abstract_zh.replace("🟢", "\n\n**") # 加粗标记起始
                        abstract_zh = abstract_zh.replace("：", "：** ")   # 加粗标记结束（中文冒号）
                        abstract_zh = abstract_zh.replace(":", ":** ")     # 加粗标记结束（英文冒号）
                        
                        # 兜底：如果翻译丢失了换行，强制分段
                        key_map = {
                            "背景": "Background", "方法": "Methods", "结果": "Results", "结论": "Conclusion"
                        }
                        for ch_key, en_key in key_map.items():
                             if f"{ch_key}" in abstract_zh and "**" not in abstract_zh:
                                  abstract_zh = abstract_zh.replace(ch_key, f"\n\n**{ch_key}**")

                    except Exception as e:
                        print(f"翻译摘要出错: {e}")
                        abstract_zh = "翻译服务暂时不可用，请查看右侧原文。"
                else:
                    abstract_zh = "暂无摘要"

                # 4. 翻译关键词
                keywords_zh = ""
                if keywords_en:
                    try:
                        keywords_zh = translator.translate(keywords_en)
                    except:
                        keywords_zh = keywords_en

                # 5. 作者处理 (RSS description 有时包含作者，feedparser 有时能单独提取)
                authors = entry.get('author', 'No authors listed')

                entries_data.append({
                    "id": i,
                    "title_en": title_en,
                    "title_zh": title_zh,
                    "authors": authors,
                    "abstract_en": abstract_en_structured.replace("🟢", ""), # 英文原文展示时去掉辅助符
                    "abstract_zh": abstract_zh, # 中文带 markdown 格式
                    "keywords_en": keywords_en,
                    "keywords_zh": keywords_zh,
                    "link": entry.link,
                    "date": entry.get('published', '')[:16]
                })
                
                time.sleep(0.2) 
            
            all_feeds_data[feed_title] = entries_data
            
        except Exception as e:
            print(f"抓取 {url} 失败: {e}")

    # 生成 JSON
    json_data = json.dumps(all_feeds_data, ensure_ascii=False)
    tz = pytz.timezone('Asia/Shanghai')
    update_time = datetime.now(tz).strftime("%Y-%m-%d %H:%M")

    # ================= HTML 模板 =================
    html_content = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PubMed 深度阅读 - {update_time}</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
        <style>
            body {{ height: 100vh; overflow: hidden; }}
            /* 隐藏滚动条但保留功能 */
            .scrollbar-hide::-webkit-scrollbar {{ display: none; }}
            ::-webkit-scrollbar {{ width: 6px; }}
            ::-webkit-scrollbar-track {{ background: #f1f1f1; }}
            ::-webkit-scrollbar-thumb {{ background: #cbd5e1; border-radius: 3px; }}
            .prose strong {{ color: #1e40af; font-weight: 800; display: block; margin-top: 1em; margin-bottom: 0.2em; }}
            .prose p {{ margin-bottom: 0.5em; text-align: justify; }}
        </style>
    </head>
    <body class="bg-gray-100 flex flex-col" x-data="app()">
        
        <header class="bg-white border-b border-gray-200 h-14 flex items-center justify-between px-6 shadow-sm z-10 shrink-0">
            <div class="flex items-center gap-4">
                <div class="font-bold text-xl text-blue-800 flex items-center gap-2">
                    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"></path></svg>
                    PubMed DeepReader
                </div>
                <div class="text-xs text-gray-400 mt-1">更新: {update_time}</div>
            </div>
            <div class="flex items-center gap-2">
                <select x-model="currentFeed" @change="selectFeed()" class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block p-2">
                    <template x-for="feedName in Object.keys(feeds)" :key="feedName">
                        <option :value="feedName" x-text="feedName"></option>
                    </template>
                </select>
            </div>
        </header>

        <div class="flex flex-1 overflow-hidden">
            <aside class="w-1/3 max-w-md bg-white border-r border-gray-200 flex flex-col overflow-y-auto">
                <template x-for="paper in currentPapers" :key="paper.id">
                    <div @click="currentPaper = paper" 
                         :class="currentPaper.id === paper.id ? 'bg-blue-50 border-l-4 border-blue-600' : 'border-l-4 border-transparent hover:bg-gray-50'"
                         class="p-4 border-b border-gray-100 cursor-pointer transition duration-150">
                        <h3 class="text-sm font-bold text-gray-800 line-clamp-2 leading-snug" x-text="paper.title_zh"></h3>
                        <p class="text-xs text-gray-500 mt-1 truncate" x-text="paper.title_en"></p>
                    </div>
                </template>
            </aside>

            <main class="flex-1 bg-gray-50 overflow-y-auto p-6">
                <template x-if="currentPaper">
                    <div class="max-w-5xl mx-auto bg-white rounded-xl shadow-sm p-8 min-h-[90vh]">
                        
                        <div class="border-b border-gray-100 pb-6 mb-6">
                            <h1 class="text-2xl font-bold text-gray-900 mb-2 leading-tight" x-text="currentPaper.title_zh"></h1>
                            <h2 class="text-lg text-gray-500 font-medium mb-4" x-text="currentPaper.title_en"></h2>
                            
                            <div class="flex flex-wrap gap-4 text-xs text-gray-500 bg-gray-50 p-3 rounded-lg">
                                <span class="flex items-center">📅 <span class="ml-1" x-text="currentPaper.date"></span></span>
                                <span class="flex items-center">👥 <span class="ml-1" x-text="currentPaper.authors"></span></span>
                                <a :href="currentPaper.link" target="_blank" class="text-blue-600 hover:underline font-bold ml-auto">
                                    🔗 View on PubMed
                                </a>
                            </div>
                        </div>

                        <template x-if="currentPaper.keywords_zh">
                            <div class="mb-6">
                                <span class="text-xs font-bold text-blue-600 uppercase tracking-wide">Keywords</span>
                                <div class="mt-1 text-sm text-gray-700 italic">
                                    <span x-text="currentPaper.keywords_zh"></span>
                                    <span class="text-gray-400 mx-2">/</span>
                                    <span class="text-gray-400" x-text="currentPaper.keywords_en"></span>
                                </div>
                            </div>
                        </template>

                        <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
                            <div>
                                <h3 class="font-bold text-gray-900 text-lg mb-3 flex items-center">
                                    <span class="w-1 h-6 bg-blue-600 mr-2 rounded"></span> 中文摘要
                                </h3>
                                <div class="prose prose-sm prose-blue text-gray-800 leading-relaxed bg-blue-50/50 p-5 rounded-lg border border-blue-100" 
                                     x-html="marked.parse(currentPaper.abstract_zh)"></div>
                            </div>

                            <div>
                                <h3 class="font-bold text-gray-400 text-lg mb-3 flex items-center">
                                    <span class="w-1 h-6 bg-gray-300 mr-2 rounded"></span> Abstract
                                </h3>
                                <div class="prose prose-sm text-gray-600 leading-relaxed whitespace-pre-wrap p-5" 
                                     x-html="currentPaper.abstract_en.replace(/🟢 /g, '').replace(/(\w+:)/g, '<strong>$1</strong>')"></div>
                            </div>
                        </div>

                    </div>
                </template>
            </main>
        </div>

        <script>
            function app() {{
                return {{
                    feeds: {json_data},
                    currentFeed: '',
                    currentPapers: [],
                    currentPaper: null,
                    init() {{
                        const feedNames = Object.keys(this.feeds);
                        if (feedNames.length > 0) {{
                            this.currentFeed = feedNames[0];
                            this.selectFeed();
                        }}
                    }},
                    selectFeed() {{
                        this.currentPapers = this.feeds[this.currentFeed];
                        this.currentPaper = this.currentPapers.length > 0 ? this.currentPapers[0] : null;
                        document.querySelector('aside').scrollTop = 0;
                    }}
                }}
            }}
        </script>
    </body>
    </html>
    """

    with open(os.path.join(output_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(html_content)
    
    archive_name = f"archive_{datetime.now(tz).strftime('%Y%m%d')}.html"
    with open(os.path.join(output_dir, archive_name), "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print("HTML 生成完毕！")

if __name__ == "__main__":
    fetch_and_generate()
