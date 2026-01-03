import feedparser
from deep_translator import GoogleTranslator
import time
from datetime import datetime
import os
import pytz
import json

# ================= 配置区 =================
# 在这里放入你的所有订阅链接
RSS_URLS = [
    "https://pubmed.ncbi.nlm.nih.gov/rss/search/1p9j2Ia0knTignEE7vvWNCOPD-p8oHaBJk6HqSr1JJOMQoMsn2/?limit=100&utm_campaign=pubmed-2&fc=20260103012326",
    "https://pubmed.ncbi.nlm.nih.gov/rss/search/1PQPGz2gzLgNzuaNos66c7B3c89tbZUZXKYTEvBxn0Ttaa8QdR/?limit=100&utm_campaign=pubmed-2&fc=20260103012404",
    # 你可以继续添加更多...
]
# =========================================

def clean_html(raw_html):
    """简单的 HTML 清洗，保留段落感但去除冗余标签"""
    if not raw_html:
        return ""
    text = raw_html.replace("<p>", "").replace("</p>", "\n\n")
    text = text.replace("<b>", "**").replace("</b>", "**") # 保留加粗标记
    return text

def fetch_and_generate():
    output_dir = "docs"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    translator = GoogleTranslator(source='auto', target='zh-CN')
    
    # 数据结构： { "Feed名称": [文章列表], ... }
    all_feeds_data = {}
    
    print(f"准备抓取 {len(RSS_URLS)} 个订阅源...")

    for url in RSS_URLS:
        try:
            print(f"正在连接: {url[:40]}...")
            feed = feedparser.parse(url)
            
            # 自动获取 Feed 名称 (例如 "PubMed: Covid-19")
            feed_title = feed.feed.get('title', '未命名订阅源')
            # 去掉原本标题里的 "PubMed " 前缀，让显示更简洁
            feed_title = feed_title.replace("PubMed ", "")
            
            entries_data = []
            total_entries = len(feed.entries)
            
            print(f"--> [{feed_title}] 发现 {total_entries} 篇文章，开始处理...")

            for i, entry in enumerate(feed.entries):
                # 翻译标题
                try:
                    title_zh = translator.translate(entry.title)
                except:
                    title_zh = entry.title # 翻译失败用原文

                # 处理摘要：PubMed RSS 的 description 就是摘要
                raw_abstract = entry.get('description', '无摘要')
                # 提取作者信息 (RSS里通常在 description 之前或者是单独字段，这里尝试提取)
                authors = entry.get('author', '未知作者')
                
                # 翻译摘要 (分段处理防止过长)
                clean_abstract = clean_html(raw_abstract)
                try:
                    # 限制翻译长度，防止超时
                    abstract_zh = translator.translate(clean_abstract[:4000])
                    time.sleep(0.2) # 稍微防封
                except:
                    abstract_zh = "翻译服务暂时不可用，请阅读原文。"

                entries_data.append({
                    "id": i,
                    "title_en": entry.title,
                    "title_zh": title_zh,
                    "authors": authors,
                    "abstract_en": clean_abstract,
                    "abstract_zh": abstract_zh,
                    "link": entry.link,
                    "date": entry.get('published', '')[:16] # 只取日期部分
                })
            
            all_feeds_data[feed_title] = entries_data
            
        except Exception as e:
            print(f"抓取 {url} 失败: {e}")

    # 将数据序列化为 JSON 字符串，嵌入 HTML
    json_data = json.dumps(all_feeds_data, ensure_ascii=False)
    
    # 获取生成时间
    tz = pytz.timezone('Asia/Shanghai')
    update_time = datetime.now(tz).strftime("%Y-%m-%d %H:%M")

    # ================= HTML 模板 (使用 Alpine.js 实现交互) =================
    html_content = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PubMed 阅读器 - {update_time}</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
        <style>
            body {{ height: 100vh; overflow: hidden; }}
            .scrollbar-hide::-webkit-scrollbar {{ display: none; }}
            /* 自定义滚动条样式 */
            ::-webkit-scrollbar {{ width: 6px; }}
            ::-webkit-scrollbar-track {{ background: #f1f1f1; }}
            ::-webkit-scrollbar-thumb {{ background: #cbd5e1; border-radius: 3px; }}
            ::-webkit-scrollbar-thumb:hover {{ background: #94a3b8; }}
        </style>
    </head>
    <body class="bg-gray-100 flex flex-col" x-data="app()">
        
        <header class="bg-white border-b border-gray-200 h-14 flex items-center justify-between px-6 shadow-sm z-10 shrink-0">
            <div class="flex items-center gap-4">
                <div class="font-bold text-xl text-blue-700">PubMed Reader</div>
                <div class="text-xs text-gray-400 mt-1">更新于: {update_time}</div>
            </div>
            
            <div class="flex items-center gap-2">
                <span class="text-sm text-gray-600">当前订阅:</span>
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
                        <div class="flex justify-between items-center mt-2">
                            <span class="text-xs text-blue-500 bg-blue-50 px-2 py-0.5 rounded" x-text="paper.date"></span>
                        </div>
                    </div>
                </template>
            </aside>

            <main class="flex-1 bg-gray-50 overflow-y-auto p-8">
                <template x-if="currentPaper">
                    <div class="max-w-4xl mx-auto bg-white rounded-xl shadow-sm p-8 min-h-[80vh]">
                        <h1 class="text-2xl font-bold text-gray-900 mb-2 leading-tight" x-text="currentPaper.title_zh"></h1>
                        <h2 class="text-lg text-gray-500 mb-4 font-medium" x-text="currentPaper.title_en"></h2>
                        
                        <div class="flex flex-wrap gap-4 text-sm text-gray-500 border-b border-gray-100 pb-6 mb-6">
                            <span>📅 <span x-text="currentPaper.date"></span></span>
                            <span>✍️ <span x-text="currentPaper.authors"></span></span>
                            <a :href="currentPaper.link" target="_blank" class="text-blue-600 hover:underline flex items-center">
                                🔗 去 PubMed 查看原文
                            </a>
                        </div>

                        <div class="mb-8">
                            <h3 class="font-bold text-gray-900 text-lg mb-3 flex items-center">
                                <span class="w-1 h-6 bg-blue-600 mr-2 rounded"></span> 中文摘要
                            </h3>
                            <div class="text-gray-800 leading-relaxed text-justify whitespace-pre-wrap text-base bg-slate-50 p-5 rounded-lg border border-slate-100" x-text="currentPaper.abstract_zh"></div>
                        </div>

                        <div>
                            <button @click="showOriginal = !showOriginal" class="text-sm text-gray-400 hover:text-blue-600 mb-2 flex items-center gap-1">
                                <span x-text="showOriginal ? '▼ 收起英文原文' : '▶ 展开英文原文'"></span>
                            </button>
                            <div x-show="showOriginal" x-transition class="text-sm text-gray-500 leading-relaxed whitespace-pre-wrap bg-gray-50 p-4 rounded border border-gray-100" x-text="currentPaper.abstract_en"></div>
                        </div>
                    </div>
                </template>
                
                <template x-if="!currentPaper">
                    <div class="h-full flex flex-col items-center justify-center text-gray-400">
                        <svg class="w-16 h-16 mb-4 opacity-20" fill="currentColor" viewBox="0 0 20 20"><path d="M9 4.804A7.968 7.968 0 005.5 4c-1.255 0-2.443.29-3.5.804v10A7.969 7.969 0 015.5 14c1.669 0 3.218.51 4.5 1.385A7.962 7.962 0 0114.5 14c1.255 0 2.443.29 3.5.804v-10A7.968 7.968 0 0014.5 4c-1.255 0-2.443.29-3.5.804V12a1 1 0 11-2 0V4.804z"/></svg>
                        <p>请在左侧点击一篇文章开始阅读</p>
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
                    showOriginal: false,

                    init() {{
                        const feedNames = Object.keys(this.feeds);
                        if (feedNames.length > 0) {{
                            this.currentFeed = feedNames[0];
                            this.selectFeed();
                        }}
                    }},

                    selectFeed() {{
                        this.currentPapers = this.feeds[this.currentFeed];
                        if (this.currentPapers.length > 0) {{
                            this.currentPaper = this.currentPapers[0]; // 默认选中第一篇
                        }} else {{
                            this.currentPaper = null;
                        }}
                        // 滚动回顶部
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
    
    # 同时也保存一份带日期的存档
    archive_name = f"archive_{datetime.now(tz).strftime('%Y%m%d')}.html"
    with open(os.path.join(output_dir, archive_name), "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print("HTML 生成完毕！")

if __name__ == "__main__":
    fetch_and_generate()
