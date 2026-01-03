import feedparser
from deep_translator import GoogleTranslator
import time
from datetime import datetime
import os
import pytz # 用于处理时区

# ================= 配置区 =================
# 替换为你的 RSS 链接
RSS_URL = "https://pubmed.ncbi.nlm.nih.gov/rss/search/1ja5LcHs8vLHfyzb6ucfIkAnufnMdEDDy3oqFgiefpewqXFYZO/?limit=100&utm_campaign=pubmed-2&fc=20260103010444"
# =========================================

def fetch_and_generate():
    # 确保输出目录存在
    output_dir = "docs"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print("正在连接 PubMed...")
    feed = feedparser.parse(RSS_URL)
    translator = GoogleTranslator(source='auto', target='zh-CN')
    
    papers = []
    total = len(feed.entries)
    
    for index, entry in enumerate(feed.entries):
        print(f"处理中 [{index+1}/{total}]: {entry.title[:20]}...")
        try:
            title_zh = translator.translate(entry.title)
            # 简单清洗摘要 HTML 标签
            abstract_clean = entry.description.replace('<p>', '').replace('</p>', '').replace('<b>', '').replace('</b>', '')
            # 截取前3000字符防止API报错
            abstract_zh = translator.translate(abstract_clean[:3000])
            time.sleep(0.5) # 防止请求过快
        except Exception as e:
            print(f"翻译错误: {e}")
            title_zh = "翻译失败"
            abstract_zh = "暂无摘要或翻译失败"

        papers.append({
            "title_en": entry.title,
            "title_zh": title_zh,
            "abstract_en": entry.description,
            "abstract_zh": abstract_zh,
            "link": entry.link,
            "date": entry.published
        })

    # 获取北京时间
    tz = pytz.timezone('Asia/Shanghai')
    today_str = datetime.now(tz).strftime("%Y-%m-%d")
    
    # HTML 模板
    html = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PubMed 日报 - {today_str}</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>.abstract-en {{ display: none; }} .active {{ display: block; }}</style>
    </head>
    <body class="bg-slate-50 min-h-screen py-8">
        <div class="max-w-4xl mx-auto px-4">
            <h1 class="text-3xl font-bold text-center text-slate-800 mb-2">PubMed 每日文献速递</h1>
            <p class="text-center text-slate-500 mb-8">{today_str} | 共 {len(papers)} 篇</p>
            <div class="space-y-6">
    """
    
    for p in papers:
        html += f"""
        <div class="bg-white p-6 rounded-xl shadow-sm border border-slate-100">
            <h2 class="text-lg font-bold text-slate-800 mb-1">{p['title_zh']}</h2>
            <p class="text-sm text-slate-500 mb-3">{p['title_en']}</p>
            <div class="text-slate-700 text-sm leading-relaxed bg-blue-50 p-4 rounded-lg mb-3">
                {p['abstract_zh']}
            </div>
            <div class="flex justify-between items-center mt-4">
                <button onclick="this.parentElement.nextElementSibling.classList.toggle('active')" class="text-blue-600 text-xs font-medium hover:underline">
                    显示/隐藏 英文原文
                </button>
                <a href="{p['link']}" target="_blank" class="text-white bg-blue-600 hover:bg-blue-700 px-3 py-1 rounded text-xs">原文链接</a>
            </div>
            <div class="abstract-en mt-2 text-xs text-slate-400 bg-slate-50 p-3 rounded">
                {p['abstract_en']}
            </div>
        </div>
        """
    
    html += "</div></div></body></html>"

    # 保存为 index.html (主页) 和 日期存档.html
    with open(os.path.join(output_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    with open(os.path.join(output_dir, f"paper_{today_str}.html"), "w", encoding="utf-8") as f:
        f.write(html)

if __name__ == "__main__":
    fetch_and_generate()