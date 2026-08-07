#!/usr/bin/env python3
"""DrillFeed v1.0 — 垂直深度阅读器"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog
import os, sys, json, sqlite3, threading, webbrowser, time, re, html, datetime
import urllib.request, xml.etree.ElementTree as ET, ssl
from urllib.parse import quote

APP_DIR = os.path.dirname(sys.executable) if getattr(sys,'frozen',False) else os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "drillfeed.db")

SSL_CTX = ssl.create_default_context(); SSL_CTX.check_hostname = False; SSL_CTX.verify_mode = ssl.CERT_NONE

PRESET_FEEDS = {
    "科技·前沿": [
        ("36氪", "https://36kr.com/feed"),
        ("IT之家", "https://www.ithome.com/rss/"),
        ("爱范儿", "https://www.ifanr.com/feed"),
        ("雷锋网", "https://www.leiphone.com/feed"),
        ("极客公园", "https://www.geekpark.net/rss"),
    ],
    "数码·工具": [
        ("少数派", "https://sspai.com/feed"),
        ("小众软件", "https://www.appinn.com/feed"),
    ],
    "极客·开源": [
        ("Solidot 奇客", "https://www.solidot.org/index.rss"),
        ("InfoQ 技术", "https://www.infoq.cn/feed"),
    ],
    "博客·观点": [
        ("阮一峰", "https://www.ruanyifeng.com/blog/atom.xml"),
        ("月光博客", "https://feed.williamlong.info/"),
    ],
    "商业·消费": [
        ("界面新闻", "https://a.jiemian.com/index.php?m=article&a=rss"),
        ("理想生活实验室", "https://www.toodaylab.com/feed"),
    ],
    "游戏·文化": [
        ("机核", "https://www.gcores.com/rss"),
    ],
    "财经·金融": [
        ("雪球热门", "https://xueqiu.com/hots/topic/rss"),
    ],
}

DISCLAIMER = """⚠️ 免责声明

1. 本工具仅供个人学习研究使用。内置 RSS 源内容版权归各网站所有，本工具仅作信息聚合，不持任何立场。
2. 使用者须自行遵守各网站的使用条款。下载、缓存、转发 RSS 内容产生的任何法律责任由使用者自行承担。
3. 本工具不采集、上传、分享任何用户数据。所有文章缓存于本地 SQLite 数据库。
4. 本软件按"原样"提供，不提供任何明示或暗示的担保，包括但不限于适销性、特定用途适用性。
5. 开发者不对因使用本软件导致的任何直接或间接损失承担责任。"""

# ======================= Database =======================
def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("""CREATE TABLE IF NOT EXISTS feeds(
        id INTEGER PRIMARY KEY, title TEXT, url TEXT UNIQUE, category TEXT,
        last_fetch TEXT, added_at TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS articles(
        id INTEGER PRIMARY KEY, feed_id INTEGER, title TEXT, link TEXT UNIQUE,
        author TEXT, published TEXT, summary TEXT, content TEXT,
        is_read INTEGER DEFAULT 0, is_bookmarked INTEGER DEFAULT 0,
        fetched_at TEXT, FOREIGN KEY(feed_id) REFERENCES feeds(id))""")
    return conn

# ======================= RSS Parser =======================
def fetch_feed(url, timeout=20):
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/rss+xml, application/atom+xml, application/xml, text/xml, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as r: raw = r.read()
    except: return []
    try: root = ET.fromstring(raw)
    except ET.ParseError:
        try: root = ET.fromstring(re.sub(b'&(?!amp;|lt;|gt;|quot;|apos;|#\\d+;)', b'&amp;', raw))
        except: return []
    articles = []
    try:
        for item in root.iter('item'):
            articles.append({
                'title': html.unescape((item.findtext('title','')[:200]).strip()),
                'link': (item.findtext('link','') or '').strip(),
                'summary': clean_html(item.findtext('description',''))[:500],
                'content': clean_html(item.findtext('{http://purl.org/rss/1.0/modules/content/}encoded','') or item.findtext('description',''))[:3000],
                'published': item.findtext('pubDate',''),
                'author': (item.findtext('{http://purl.org/dc/elements/1.1/}creator','') or item.findtext('author','')).strip(),
            })
    except: pass
    if not articles:
        try:
            ns_a = 'http://www.w3.org/2005/Atom'
            for entry in root.iter(f'{{{ns_a}}}entry'):
                link_el = entry.find(f'{{{ns_a}}}link')
                summary = entry.findtext(f'{{{ns_a}}}summary','')
                content_el = entry.find(f'{{{ns_a}}}content')
                author_el = entry.find(f'{{{ns_a}}}author')
                articles.append({
                    'title': html.unescape((entry.findtext(f'{{{ns_a}}}title','')[:200]).strip()),
                    'link': link_el.get('href','') if link_el is not None else '',
                    'summary': clean_html(summary)[:500],
                    'content': clean_html(content_el.text if content_el is not None and content_el.text else summary)[:3000],
                    'published': '',
                    'author': author_el.findtext(f'{{{ns_a}}}name','') if author_el is not None else '',
                })
        except: pass
    return articles

def clean_html(text):
    if not text: return ''
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL|re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL|re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    return re.sub(r'\s+', ' ', html.unescape(text)).strip()

# ======================= App =======================
class DrillFeed:
    def __init__(self):
        self.conn = init_db()
        self.root = tk.Tk()
        self.root.title("DrillFeed v1.0 - 永远的兰兰")
        self.root.geometry("1020x700")
        self.root.minsize(800, 500)
        self._apply_theme()
        self._build_menu()
        self._build_ui()
        imported = self._auto_import_if_empty()
        if imported:
            self.root.after_idle(self._refresh_all)
        else:
            self._load_feeds()
            self._load_articles()

    def _apply_theme(self):
        style = ttk.Style(); style.theme_use('clam')
        BG, BG2, FG = '#F5F5F5', '#E8E8E8', '#222'
        style.configure('.', background=BG, foreground=FG)
        style.configure('TFrame', background=BG)
        style.configure('TLabel', background=BG)
        style.configure('TButton', background=BG2, font=('Microsoft YaHei UI',9), padding=[8,3])
        style.configure('TLabelframe', background=BG)
        style.configure('TLabelframe.Label', background=BG)
        style.configure('Treeview', background='white', fieldbackground='white', rowheight=22)
        style.configure('Treeview.Heading', background=BG2, font=('Microsoft YaHei UI',9,'bold'))
        style.map('Treeview', background=[('selected','#B3D4FC')])
        style.map('TButton', background=[('active','#D0D0D0')])

    @staticmethod
    def _cbtn(parent, text, color, cmd, **kw):
        btn = tk.Button(parent, text=text, bg=color, fg='white', font=('Microsoft YaHei UI',9),
                        relief='flat', bd=0, padx=10, pady=3, cursor='hand2', command=cmd)
        btn.pack(**kw); return btn

    def _build_menu(self):
        menubar = tk.Menu(self.root)
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="使用说明", command=self._show_help)
        help_menu.add_command(label="免责声明", command=self._show_disclaimer)
        help_menu.add_separator()
        help_menu.add_command(label="关于 DrillFeed", command=self._show_about)
        menubar.add_cascade(label="帮助", menu=help_menu)
        self.root.config(menu=menubar)

    def _show_help(self):
        msg = """📖 DrillFeed 使用说明

1. 首次启动自动导入 9 个精选 RSS 源
2. 点击左侧源名或分类，右边显示文章列表
3. 点「⟳ 刷新」拉取最新文章（后台线程，不卡界面）
4. 🔍 搜索框输入关键词即搜即显
5. ⭐ 收藏重要文章，🌐 打开原文在浏览器
6. 点「+」手动添加任意 RSS 地址
7. 文章保留最近一周，过期自动不再显示
8. 底部状态栏实时显示操作结果"""
        messagebox.showinfo("使用说明", msg)

    def _show_disclaimer(self):
        messagebox.showinfo("免责声明", DISCLAIMER)

    def _show_about(self):
        messagebox.showinfo("关于 DrillFeed",
            "DrillFeed v1.0\n\n垂直深度阅读器 · 为研究者和极客打造\n\n"
            "Python 3 + tkinter + SQLite\nMIT License\n\n"
            "⚠️ 本工具仅供个人学习研究使用。\n"
            "内置 RSS 源版权归各网站所有。\n\n"
            "© 永远的兰兰")

    def _auto_import_if_empty(self):
        cnt = self.conn.execute("SELECT COUNT(*) FROM feeds").fetchone()[0]
        if cnt == 0:
            for cat, feeds in PRESET_FEEDS.items():
                for title, url in feeds:
                    try: self.conn.execute("INSERT OR IGNORE INTO feeds(title,url,category,added_at) VALUES(?,?,?,datetime('now'))", (title, url, cat))
                    except: pass
            self.conn.commit()
            c = self.conn.execute("SELECT COUNT(*) FROM feeds").fetchone()[0]
            self.status_var.set(f"首次启动 · 已导入 {c} 个源 · 正在拉取文章...")
            self._load_feeds()
            self.root.update()
            return True
        return False

    def _build_ui(self):
        # Status bar — pack FIRST so panels take space above it
        status_frame = tk.Frame(self.root, bg='#E0E0E0', height=24)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        status_frame.pack_propagate(False)
        self.status_var = tk.StringVar(value='就绪')
        self.status = tk.Label(status_frame, textvariable=self.status_var, anchor='w',
                               bg='#E0E0E0', fg='#555', font=('Microsoft YaHei UI',8), padx=8)
        self.status.pack(fill=tk.BOTH, expand=True)

        # Left panel
        left = ttk.Frame(self.root, width=240)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(4,2), pady=4)
        left.pack_propagate(False)
        ttk.Label(left, text="📡 订阅源", font=('Microsoft YaHei UI',11,'bold')).pack(anchor='w',pady=(4,2))
        bar = ttk.Frame(left); bar.pack(fill=tk.X)
        self._cbtn(bar, "＋ 添加", '#4CAF50', self._add_feed, side=tk.LEFT, padx=1)
        self._cbtn(bar, "－ 删除", '#F44336', self._remove_feed, side=tk.LEFT, padx=1)
        self._cbtn(bar, "⟳ 刷新", '#2196F3', self._refresh_all, side=tk.LEFT, padx=1)
        self._cbtn(bar, "📋 预设", '#FF9800', self._import_presets, side=tk.RIGHT, padx=1)
        treef = ttk.Frame(left); treef.pack(fill=tk.BOTH, expand=True, pady=4)
        self.feed_tree = ttk.Treeview(treef, columns=('title',), show='tree', height=20)
        self.feed_tree.heading('#0', text='分类/源'); self.feed_tree.column('#0', width=200)
        sb = ttk.Scrollbar(treef, orient=tk.VERTICAL, command=self.feed_tree.yview)
        self.feed_tree.configure(yscrollcommand=sb.set)
        self.feed_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True); sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.feed_tree.bind('<<TreeviewSelect>>', self._on_feed_select)

        # Right panel
        right = ttk.Frame(self.root)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(2,4), pady=4)

        top = ttk.Frame(right); top.pack(fill=tk.X, pady=(0,4))
        ttk.Label(top, text="🔍").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace_add('write', lambda *a: self._load_articles())
        ttk.Entry(top, textvariable=self.search_var, width=28).pack(side=tk.LEFT, padx=4)
        ttk.Label(top, text="  ").pack(side=tk.LEFT)
        self._cbtn(top, "⭐ 收藏", '#FFC107', lambda: self._toggle_bookmark(), side=tk.LEFT, padx=2)
        self._cbtn(top, "🌐 打开原文", '#2196F3', self._open_link, side=tk.LEFT, padx=2)
        self._cbtn(top, "📤 分享", '#E91E63', self._show_share_card, side=tk.LEFT, padx=2)
        self._cbtn(top, "✓ 已读", '#9E9E9E', self._mark_read, side=tk.LEFT, padx=2)
        self._cbtn(top, "未读", '#E91E63', lambda: self._load_articles(unread_only=True), side=tk.LEFT, padx=2)
        self._cbtn(top, "全部", '#607D8B', lambda: self._load_articles(), side=tk.LEFT, padx=2)
        ttk.Label(top, text="  📅").pack(side=tk.LEFT)
        self.date_var = tk.StringVar(value="全部")
        date_cb = ttk.Combobox(top, textvariable=self.date_var, values=["全部","今天","近3天","近7天","近30天"], state="readonly", width=7)
        date_cb.pack(side=tk.LEFT, padx=2)
        date_cb.bind("<<ComboboxSelected>>", lambda e: self._load_articles())

        art_f = ttk.Frame(right); art_f.pack(fill=tk.BOTH, expand=True)
        self.art_tree = ttk.Treeview(art_f, columns=('title','feed','date'), show='headings', height=12)
        self.art_tree.heading('title', text='标题'); self.art_tree.column('title', width=480)
        self.art_tree.heading('feed', text='来源'); self.art_tree.column('feed', width=120)
        self.art_tree.heading('date', text='日期'); self.art_tree.column('date', width=100, anchor='center')
        asb = ttk.Scrollbar(art_f, orient=tk.VERTICAL, command=self.art_tree.yview)
        self.art_tree.configure(yscrollcommand=asb.set)
        self.art_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True); asb.pack(side=tk.RIGHT, fill=tk.Y)
        self.art_tree.bind('<<TreeviewSelect>>', self._on_art_select)
        self.art_tree.bind('<Double-1>', lambda e: self._open_link())

        det_f = ttk.LabelFrame(right, text='文章详情', padding=4)
        det_f.pack(fill=tk.BOTH, expand=True, pady=(4,0))
        self.detail_title = ttk.Label(det_f, text='', font=('Microsoft YaHei UI',11,'bold'), wraplength=700)
        self.detail_title.pack(anchor='w', pady=(2,4))
        self.detail_text = scrolledtext.ScrolledText(det_f, font=('Microsoft YaHei UI',9),
            wrap=tk.WORD, bg='white', fg='#333', height=10, state=tk.DISABLED)
        self.detail_text.pack(fill=tk.BOTH, expand=True)

    # ===== Feed Management =====
    def _load_feeds(self):
        self.feed_tree.delete(*self.feed_tree.get_children())
        cats = {}
        for row in self.conn.execute("SELECT id,title,url,category FROM feeds ORDER BY category, title"):
            fid, title, url, cat = row
            cat_key = cat or '未分类'
            if cat_key not in cats: cats[cat_key] = []
            cats[cat_key].append((fid, title, url))
        if not cats:
            self.feed_tree.insert('', tk.END, text='📂 暂无源 · 点 📋 预设源导入')
            return
        for cat, feeds in cats.items():
            cid = self.feed_tree.insert('', tk.END, text=f'📂 {cat} ({len(feeds)})', values=('cat',cat))
            for fid, title, url in feeds:
                count = self.conn.execute("SELECT COUNT(*) FROM articles WHERE feed_id=? AND is_read=0",(fid,)).fetchone()[0]
                label = f'{title} ({count})' if count else title
                self.feed_tree.insert(cid, tk.END, text=label, values=(fid,url), tags=('feed',))

    def _add_feed(self):
        url = simpledialog.askstring('添加订阅', '输入 RSS/Atom 地址:')
        if not url: return
        t = threading.Thread(target=self._do_add_feed, args=(url,), daemon=True); t.start()

    def _do_add_feed(self, url):
        self.root.after(0, lambda: self.status_var.set(f'正在获取 {url[:60]}...'))
        articles = fetch_feed(url)
        if not articles:
            self.root.after(0, lambda: messagebox.showwarning('提示','无法解析该 RSS 源'))
            self.root.after(0, lambda: self.status_var.set('添加失败')); return
        feed_title = simpledialog.askstring('订阅标题', '为这个源起个名字:')
        if not feed_title: return
        cat = simpledialog.askstring('分类', '分类（如：科技·前沿）:', initialvalue='未分类')
        try:
            self.conn.execute("INSERT INTO feeds(title,url,category,added_at) VALUES(?,?,?,datetime('now'))", (feed_title, url, cat or '未分类'))
            fid = self.conn.execute("SELECT id FROM feeds WHERE url=?",(url,)).fetchone()[0]
            for a in articles:
                try: self.conn.execute("INSERT OR IGNORE INTO articles(feed_id,title,link,author,published,summary,content,fetched_at) VALUES(?,?,?,?,?,?,?,datetime('now'))",
                    (fid, a['title'], a['link'], a.get('author',''), a.get('published',''), a.get('summary',''), a.get('content','')))
                except: pass
            self.conn.commit()
            self.root.after(0, lambda: self.status_var.set(f'✅ {feed_title}: {len(articles)} 篇'))
            self.root.after(0, self._load_feeds); self.root.after(0, self._load_articles)
        except Exception as e: self.root.after(0, lambda: self.status_var.set(f'错误: {e}'))

    def _remove_feed(self):
        sel = self.feed_tree.selection()
        if not sel: return
        vals = self.feed_tree.item(sel[0], 'values')
        if vals[0] == 'cat': return
        if messagebox.askyesno('确认', '删除此订阅源及所有文章?'):
            self.conn.execute("DELETE FROM articles WHERE feed_id=?",(vals[0],))
            self.conn.execute("DELETE FROM feeds WHERE id=?",(vals[0],))
            self.conn.commit()
            self._load_feeds(); self._load_articles()

    def _refresh_all(self):
        feeds = list(self.conn.execute("SELECT id,url FROM feeds"))
        if not feeds:
            self.root.after(0, lambda: messagebox.showinfo('提示','请先添加订阅源或导入预设源'))
            return
        self.status_var.set(f'更新 {len(feeds)} 个源...'); self.root.update()
        def do_refresh():
            total = 0
            for fid, url in feeds:
                self.root.after(0, lambda u=url: self.status_var.set(f'更新中: {u[:60]}...'))
                arts = fetch_feed(url, timeout=25)
                for a in arts:
                    try: self.conn.execute("INSERT OR IGNORE INTO articles(feed_id,title,link,author,published,summary,content,fetched_at) VALUES(?,?,?,?,?,?,?,datetime('now'))",
                        (fid, a['title'], a['link'], a.get('author',''), a.get('published',''), a.get('summary',''), a.get('content','')))
                    except: pass
                total += len(arts)
            self.conn.execute("UPDATE feeds SET last_fetch=datetime('now')"); self.conn.commit()
            self.root.after(0, lambda: self.status_var.set(f'✅ 更新完成: {total} 篇新文章'))
            self.root.after(0, self._load_feeds); self.root.after(0, self._load_articles)
        t = threading.Thread(target=do_refresh, daemon=True); t.start()

    def _import_presets(self):
        cnt = 0
        for cat, feeds in PRESET_FEEDS.items():
            for title, url in feeds:
                try: self.conn.execute("INSERT OR IGNORE INTO feeds(title,url,category,added_at) VALUES(?,?,?,datetime('now'))", (title, url, cat)); cnt += 1
                except: pass
        self.conn.commit()
        self.status_var.set(f'✅ 已导入 {cnt} 个预设源')
        self._load_feeds()

    # ===== Articles (last 7 days) =====
    def _load_articles(self, unread_only=False):
        self.art_tree.delete(*self.art_tree.get_children())
        week_ago = (datetime.datetime.now() - datetime.timedelta(days=7)).strftime('%Y-%m-%d')
        q = """SELECT a.id,a.title,a.link,f.title,a.published,a.summary,a.is_read,a.is_bookmarked
               FROM articles a JOIN feeds f ON a.feed_id=f.id WHERE 1=1"""
        params = []
        dr = self.date_var.get()
        if unread_only: q += " AND a.is_read=0"
        kw = self.search_var.get().strip()
        if kw:
            q += " AND (a.title LIKE ? OR a.summary LIKE ?)"
            params.extend([f'%{kw}%', f'%{kw}%'])
        if dr != "全部":
            days = {"今天":0,"近3天":3,"近7天":7,"近30天":30}.get(dr, 7)
            cutoff = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime('%Y-%m-%d')
            if dr == "今天":
                q += " AND a.published LIKE ?"
                params.append(f'{cutoff}%')
            else:
                q += " AND a.published >= ?"
                params.append(cutoff)
        q += " ORDER BY COALESCE(a.published, a.fetched_at) DESC, a.id DESC LIMIT 300"
        rows = self.conn.execute(q, params).fetchall()
        for rid, title, link, feed_title, pub, summary, is_read, bookmarked in rows:
            prefix = '⭐ ' if bookmarked else ''
            prefix = '📖 '+prefix if not is_read else prefix
            title_disp = prefix + (title[:80] or '(无标题)')
            pub_disp = pub[:10] if pub else ''
            iid = self.art_tree.insert('', tk.END, values=(title_disp, feed_title, pub_disp))
        c = len(rows)
        kw_text = f' (搜索: {kw})' if kw else ''
        self.status_var.set(f'共 {c} 篇文章{kw_text}')

    def _on_feed_select(self, e):
        sel = self.feed_tree.selection()
        if not sel: return
        vals = self.feed_tree.item(sel[0], 'values')
        if vals[0] == 'cat': self._load_by_cat(vals[1])
        else: self._load_by_feed(vals[0])

    def _load_by_feed(self, fid):
        self.art_tree.delete(*self.art_tree.get_children())
        rows = self.conn.execute(
            "SELECT a.id,a.title,a.link,f.title,a.published,a.is_read,a.is_bookmarked FROM articles a JOIN feeds f ON a.feed_id=f.id WHERE a.feed_id=? ORDER BY COALESCE(a.published, a.fetched_at) DESC, a.id DESC LIMIT 200", (fid,)).fetchall()
        for rid, title, link, ft, pub, r, b in rows:
            p = '⭐ ' if b else ''; p = '📖 '+p if not r else p
            self.art_tree.insert('', tk.END, values=(p+(title or '(无)')[:80], ft, (pub or '')[:10]))

    def _load_by_cat(self, cat):
        self.art_tree.delete(*self.art_tree.get_children())
        rows = self.conn.execute(
            "SELECT a.id,a.title,a.link,f.title,a.published,a.is_read,a.is_bookmarked FROM articles a JOIN feeds f ON a.feed_id=f.id WHERE f.category=? ORDER BY COALESCE(a.published, a.fetched_at) DESC, a.id DESC LIMIT 200", (cat,)).fetchall()
        for rid, title, link, ft, pub, r, b in rows:
            p = '⭐ ' if b else ''; p = '📖 '+p if not r else p
            self.art_tree.insert('', tk.END, values=(p+(title or '(无)')[:80], ft, (pub or '')[:10]))

    def _on_art_select(self, e):
        sel = self.art_tree.selection()
        if not sel: return
        vals = self.art_tree.item(sel[0], 'values')
        title_key = vals[0].replace('📖 ','').replace('⭐ ','')
        row = self.conn.execute("SELECT a.title,a.author,a.published,a.summary,a.content,a.link,a.is_read,a.id FROM articles a WHERE a.title=? LIMIT 1", (title_key,)).fetchone()
        if not row: return
        title, author, pub, summary, content, link, is_read, aid = row
        body = content or summary or ""
        if len(body) < 20:
            body = "（摘要内容未加载）\n\n建议双击文章标题，在浏览器中打开原文阅读。"
        self.detail_text.config(state=tk.NORMAL); self.detail_text.delete('1.0', tk.END)
        self.detail_text.insert('1.0', f'作者: {author or "未知"}\n日期: {pub or "未知"}\n\n{body}')
        self.detail_text.config(state=tk.DISABLED)
        self.detail_title.config(text=title)
        if not is_read: self.conn.execute("UPDATE articles SET is_read=1 WHERE id=?",(aid,)); self.conn.commit()
        self.current_aid = aid

    def _open_link(self):
        sel = self.art_tree.selection()
        if not sel: return
        vals = self.art_tree.item(sel[0], 'values')
        title_key = vals[0].replace('📖 ','').replace('⭐ ','')
        row = self.conn.execute("SELECT link FROM articles WHERE title=? LIMIT 1",(title_key,)).fetchone()
        if row and row[0]: webbrowser.open(row[0])

    def _toggle_bookmark(self):
        sel = self.art_tree.selection()
        if not sel: return
        vals = self.art_tree.item(sel[0], 'values')
        title_key = vals[0].replace('📖 ','').replace('⭐ ','')
        row = self.conn.execute("SELECT id,is_bookmarked FROM articles WHERE title=? LIMIT 1",(title_key,)).fetchone()
        if row:
            self.conn.execute("UPDATE articles SET is_bookmarked=? WHERE id=?",(0 if row[1] else 1, row[0]))
            self.conn.commit(); self._load_articles()

    def _mark_read(self):
        sel = self.art_tree.selection()
        if not sel: return
        vals = self.art_tree.item(sel[0], 'values')
        title_key = vals[0].replace('📖 ','').replace('⭐ ','')
        self.conn.execute("UPDATE articles SET is_read=1 WHERE title=?",(title_key,))
        self.conn.commit(); self._load_articles()

    def _show_share_card(self):
        sel = self.art_tree.selection()
        if not sel: return
        vals = self.art_tree.item(sel[0], 'values')
        title_key = vals[0].replace('📖 ','').replace('⭐ ','')
        row = self.conn.execute("SELECT a.title,a.published,a.summary,a.link,f.title FROM articles a JOIN feeds f ON a.feed_id=f.id WHERE a.title=? LIMIT 1",(title_key,)).fetchone()
        if not row: return
        title, pub, summary, link, source = row
        pub_str = pub[:10] if pub else ''
        desc = (summary or '')[:200]
        text = f"📰 {title}\n\n📅 {pub_str}  |  来源: {source}\n\n{desc}\n\n🔗 {link}\n\n—— 来自 DrillFeed"
        # Popup window
        win = tk.Toplevel(self.root); win.title("分享卡片"); win.geometry("400x360")
        win.configure(bg='#fff')
        tk.Label(win, text="📰 分享卡片", font=('Microsoft YaHei UI',13,'bold'), bg='#fff', fg='#333').pack(pady=(12,4))
        card = tk.Text(win, font=('Microsoft YaHei UI',10), wrap=tk.WORD, bg='#FFFDE7', fg='#333',
                       relief='flat', padx=12, pady=12, height=12)
        card.insert('1.0', text); card.config(state=tk.DISABLED)
        card.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0,8))
        def cp():
            win.clipboard_clear(); win.clipboard_append(text)
            self.status_var.set('✅ 已复制分享卡片到剪贴板')
        tk.Button(win, text="📋 复制到剪贴板", bg='#E91E63', fg='white', font=('Microsoft YaHei UI',10),
                  relief='flat', padx=20, pady=6, cursor='hand2', command=cp).pack(pady=(0,10))


if __name__ == '__main__':
    DrillFeed().root.mainloop()
