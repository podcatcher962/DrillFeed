# DrillFeed v1.1

> 开源 RSS 阅读器 — 桌面版 + Web版 / Open-source RSS Reader — Desktop + Web

[中文](#中文) | [English](#english)

---

## 中文

### 简介

DrillFeed 是一款开源 RSS 阅读器。**两个版本**：Windows 桌面版完整功能（自动抓取、朗读、SQLite 缓存），**Web 版浏览器打开即用**（受 CORS 限制，部分源需代理加载）。

### 🚀 两个版本

| 版本 | 适用平台 | RSS 加载 | 文件 |
|------|------|------|------|
| 💻 **桌面版** | Windows (.exe) | 直连（无限制） | DrillFeed.exe (13MB) |
| 🌐 **Web 版** | 浏览器通用 | 代理 + CORS | drillfeed.html (单文件) |

Web 版通过 rss2json / allorigins / corsproxy 三层代理加载 RSS，浏览器沙箱导致部分源可能无法加载（属浏览器安全限制，桌面版无此问题）。

### 功能

- 📰 **15 个内置源** + 5 个分类 — 科技/数字/技术/社会/投资
- 📋 **自定义添加** — 支持任意 RSS/Atom URL
- 🔍 **分类浏览** — 目录树展开/折叠
- 📖 **内容预览** — 文章摘要+链接
- 🎧 **朗读** (桌面版) — TTS 中文朗读
- 🔄 **自动更新** (桌面版) — SQLite 本地缓存
- 📖 **帮助/免责/关于** · 🌐 **中文界面** · 💻 **桌面版快速下载**

### 免责声明

1. 本工具仅供个人学习研究使用。RSS 内容版权归源站所有。
2. Web 版通过第三方代理获取数据，源数据原样呈现。
3. 本软件按原样（AS-IS）提供。
4. 使用者须遵守所在地法律法规。

### 技术

- 桌面版：Python 3 + tkinter + SQLite，单文件 13MB
- Web 版：纯 HTML + CSS + JS，单文件无依赖

### 关于

GitHub: https://github.com/podcatcher962/DrillFeed
© 永远的兰兰

---

## English

### Overview

DrillFeed is an open-source RSS reader. **Two editions**: Windows desktop with SQLite cache + TTS, **Web version** with browser proxy loading.

### 🚀 Two Editions

| Edition | Platforms | RSS Loading | File |
|------|------|------|------|
| 💻 **Desktop** | Windows (.exe) | Direct (no limit) | DrillFeed.exe (13MB) |
| 🌐 **Web** | Any browser | Proxy + CORS | drillfeed.html (single file) |

Web uses 3-layer proxy (rss2json/allorigins/corsproxy). Some feeds may not load due to browser CORS sandbox — desktop version has no such limit.

### Features

- 📰 **15 built-in sources** × 5 categories — Tech/Digital/Blog/Social/Finance
- 📋 **Custom sources** — any RSS/Atom URL
- 🔍 **Category browse** — collapsible tree
- 📖 **Content preview** — article summary + link
- 🎧 **TTS reading** (desktop) — Chinese text-to-speech
- 🔄 **Auto-update** (desktop) — SQLite local cache
- 📖 **Help/Disclaimer/About** · 🌐 **Chinese UI** · 💻 **Desktop download**

### Disclaimer

1. Personal study/research use only. RSS copyright belongs to source websites.
2. Web version loads via third-party proxies. Content presented as-is.
3. Provided AS-IS without warranty.
4. Users must comply with local laws.

### Tech

- Desktop: Python 3 + tkinter + SQLite, single-file 13MB
- Web: Pure HTML + CSS + JS, single-file

### About

GitHub: https://github.com/podcatcher962/DrillFeed
© 永远的兰兰 / forever-chitanda
