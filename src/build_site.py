# -*- coding: utf-8 -*-
"""把《计科学习路径_完整版.md》构建成单文件网页 index.html"""
import re, html, pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
MD = (ROOT / "计科学习路径_完整版.md").read_text(encoding="utf-8")
TPL = (HERE / "site_template.html").read_text(encoding="utf-8")

# ---------------- 行内转换 ----------------
def inline(s: str) -> str:
    s = html.escape(s, quote=False)
    codes = []
    def keep(m):
        codes.append(m.group(1)); return f"\x00{len(codes)-1}\x00"
    s = re.sub(r"`([^`]+)`", keep, s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2" target="_blank" rel="noopener">\1</a>', s)
    s = re.sub(r"\x00(\d+)\x00", lambda m: f"<code>{codes[int(m.group(1))]}</code>", s)
    return s

CK = [0]  # 复选框全局序号(文档顺序,稳定)

def ck_button(text: str) -> str:
    CK[0] += 1
    return (f'<button class="ck" role="checkbox" aria-checked="false" data-ck="ck-{CK[0]}">'
            f'<span class="box"></span><span class="txt">{inline(text)}</span></button>')

BLOCK_START = re.compile(r"^(```|>|\||- |\d+\. |###|---)")

# ---------------- 块级转换 ----------------
def blocks(lines):
    out, i, n = [], 0, len(lines)
    while i < n:
        line = lines[i]
        if not line.strip():
            i += 1; continue
        if line.startswith("```"):                       # 代码块
            j = i + 1; buf = []
            while j < n and not lines[j].startswith("```"):
                buf.append(lines[j]); j += 1
            out.append(f'<pre class="code"><code>{html.escape(chr(10).join(buf))}</code></pre>')
            i = j + 1; continue
        if line.startswith(">"):                          # 引用块
            buf = []
            while i < n and lines[i].startswith(">"):
                buf.append(lines[i].lstrip(">").strip()); i += 1
            inner = []
            for b in buf:
                if not b: continue
                if b.startswith("- "): inner.append(f"<li>{inline(b[2:])}</li>")
                else: inner.append(f"<p>{inline(b)}</p>")
            out.append('<blockquote class="quote">' + "".join(inner) + "</blockquote>")
            continue
        if line.startswith("|"):                          # 表格
            rows = []
            while i < n and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")]); i += 1
            if len(rows) >= 2 and set("".join(rows[1])) <= set("-: "):
                head, body = rows[0], rows[2:]
            else:
                head, body = None, rows
            t = '<table class="tbl">'
            if head:
                t += "<thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr></thead>"
            t += "<tbody>" + "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in body) + "</tbody></table>"
            out.append(t); continue
        m = re.match(r"^- \[( |x)\] (.*)", line)          # 复选框列表
        if m:
            items = []
            while i < n:
                m2 = re.match(r"^- \[( |x)\] (.*)", lines[i])
                if not m2: break
                items.append(m2.group(2)); i += 1
            out.append('<ul class="cblist">' + "".join(f"<li>{ck_button(t)}</li>" for t in items) + "</ul>")
            continue
        m = re.match(r"^(\d+)\. \[( |x)\] (.*)", line)    # 有序复选框
        if m:
            items = []
            while i < n:
                m2 = re.match(r"^(\d+)\. \[( |x)\] (.*)", lines[i])
                if not m2: break
                items.append(m2.group(3)); i += 1
            out.append('<ol class="cblist">' + "".join(f"<li>{ck_button(t)}</li>" for t in items) + "</ol>")
            continue
        m = re.match(r"^(\d+)\. (.*)", line)              # 有序列表
        if m:
            items = []
            while i < n:
                m2 = re.match(r"^(\d+)\. (.*)", lines[i])
                if not m2 or re.match(r"^(\d+)\. \[", lines[i]): break
                items.append(m2.group(2)); i += 1
            out.append('<ol class="blist">' + "".join(f"<li>{inline(t)}</li>" for t in items) + "</ol>")
            continue
        if line.startswith("- "):                         # 无序列表
            items = []
            while i < n and lines[i].startswith("- ") and not re.match(r"^- \[", lines[i]):
                items.append(lines[i][2:]); i += 1
            out.append('<ul class="blist">' + "".join(f"<li>{inline(t)}</li>" for t in items) + "</ul>")
            continue
        if re.match(r"^-{3,}$", line):
            out.append('<hr class="rule">'); i += 1; continue
        if line.startswith("###"):
            out.append(f'<h3 class="h3">{inline(line.lstrip("#").strip())}</h3>'); i += 1; continue
        # 普通段落(连续非空行合并,<br> 分行)
        buf = [line]; i += 1
        while i < n and lines[i].strip() and not BLOCK_START.match(lines[i]):
            buf.append(lines[i]); i += 1
        text = "<br>".join(inline(b) for b in buf)
        cls = "p"
        if re.match(r"^\*\*(坑|红线)", buf[0]): cls = "lead lead-pit"
        elif re.match(r"^\*\*(过关标准|过关信号)", buf[0]): cls = "lead lead-pass"
        elif re.match(r"^\*\*[^*]+[:：]?\*\*", buf[0]): cls = "lead lead-label"
        if re.match(r"^\*\*Q\d", buf[0]): cls += " faq-q"
        out.append(f'<p class="{cls}">{text}</p>')
    return "".join(out)

# ---------------- 切分章节(代码块内不切) ----------------
lines = MD.split("\n")
sections, cur_title, cur_body, fence = [], None, [], False
front = []
for ln in lines:
    if ln.startswith("```"):
        fence = not fence
    if not fence and re.match(r"^## ", ln):
        if cur_title is not None:
            sections.append((cur_title, cur_body))
        cur_title, cur_body = ln[3:].strip(), []
    elif cur_title is not None:
        cur_body.append(ln)
    else:
        front.append(ln)
sections.append((cur_title, cur_body))

# 前置材料:H1 去掉,目录表去掉,保留「使用说明」引用块
fl = []
in_toc = False
for ln in front:
    if re.match(r"^# ", ln):
        continue
    if ln.strip() == "**目录**":
        in_toc = True; continue
    if in_toc:
        if re.match(r"^-{3,}$", ln):
            in_toc = False
        continue
    fl.append(ln)
howto_html = blocks(fl)

# ---------------- 章节元数据 ----------------
EN = {
 "sec-0":"OVERVIEW · PARALLEL STRATEGY",
 "sec-1":"TRACK 01 — C++ · STARTER",
 "sec-2":"TRACK 02 — DATA STRUCTURES & ALGORITHMS",
 "sec-3":"TRACK 03 — MATHEMATICS ×3",
 "sec-4":"TRACK 04 — COMPUTE · OS · NETWORK",
 "sec-5":"TRACK 05 — LINUX · GIT · TOOLCHAIN",
 "sec-6":"TRACK 06 — PYTHON SPRINT",
 "sec-7":"TRACK 07 — ENGLISH",
 "sec-8":"TRACK 08 — SPECIALIZATION ×6",
 "sec-9":"TRACK 09 — POSTGRAD EXAM",
 "sec-10":"TRACK 10 — PROJECT LADDER",
 "sec-aa":"APPENDIX A — LEARNING METHOD",
 "sec-ab":"APPENDIX B — AI TEAMMATE MANUAL",
 "sec-ac":"APPENDIX C — ENVIRONMENT CHECKLIST",
 "sec-ad":"APPENDIX D — PITFALL LIST",
 "sec-idx":"RESOURCE INDEX",
}
DECO = ["ht", "hatch", "ring", "sq"]

def sec_id(title):
    m = re.match(r"^(\d+)\.", title)
    if m: return f"sec-{int(m.group(1))}"
    m = re.match(r"^附录([A-D])", title)
    if m: return "sec-a" + m.group(1).lower()
    return "sec-idx"

def nav_zh(title):
    t = re.sub(r"^[0-9]+\.\s*", "", title)
    t = re.sub(r"【.*?】|\(.*?\)|（.*?）", "", t)
    return t

# ---------------- 生成导航 ----------------
nav_defs = [("sec-0","00","总览"),("sec-1","01","C++"),("sec-2","02","数据结构"),
            ("sec-3","03","数学"),("sec-4","04","系统三课"),("sec-5","05","Linux·Git"),
            ("sec-6","06","Python"),("sec-7","07","英语"),("sec-8","08","专精"),
            ("sec-9","09","考研"),("sec-10","10","项目"),("sec-aa","A–D","附录"),("sec-idx","IDX","索引")]
nav = "".join(f'<a href="#{i}"><span class="n">{n}</span>{z}</a>' for i, n, z in nav_defs)

# ---------------- 生成正文 ----------------
def header(num, zh, en):
    return (f'<header class="shead"><div class="snum">{num}</div>'
            f'<div class="stitle"><h2>{html.escape(zh)}</h2><p class="en">{en}</p></div>'
            f'<div class="sline"></div></header>')

parts, di = [], 0
for title, body in sections:
    sid = sec_id(title)
    m = re.match(r"^(\d+)\.\s*(.*)", title)
    if m:
        num, zh = f"{int(m.group(1)):02d}", m.group(2)
    else:
        m2 = re.match(r"^附录([A-D])\s*(.*)", title)
        if m2: num, zh = m2.group(1), f"附录{m2.group(1)} · {m2.group(2)}"
        else:  num, zh = "IDX", re.sub(r"^附[:：]\s*", "", title)
    content = blocks(body)
    deco = DECO[di % len(DECO)]; di += 1
    parts.append(f'<section class="sec" id="{sid}" data-deco="{deco}">'
                 f'{header(num, zh, EN.get(sid, ""))}<div class="sbody">{content}</div></section>')
    if sid == "sec-10":  # 底座完工 → 附录之间插一条跑马灯
        parts.append('<div class="marquee" aria-hidden="true"><div class="mq">'
                     '<span>里程碑自测总表 — 全部打勾 = 底座完工<b>✦</b>PROJECTS → GITHUB<i>→</i>复试讲稿 = README<b>✦</b></span>'
                     '<span>里程碑自测总表 — 全部打勾 = 底座完工<b>✦</b>PROJECTS → GITHUB<i>→</i>复试讲稿 = README<b>✦</b></span>'
                     '</div></div>')

content_html = "".join(parts)

# ---------------- HERO & FOOTER ----------------
hero = """
<section class="hero" id="top">
  <svg class="orbit" viewBox="0 0 1400 700" fill="none" aria-hidden="true">
    <defs>
      <pattern id="hatch" width="7" height="7" patternTransform="rotate(45)" patternUnits="userSpaceOnUse">
        <line x1="0" y1="0" x2="0" y2="7" stroke="#101014" stroke-width="1.3"/></pattern>
      <pattern id="htn" width="8" height="8" patternUnits="userSpaceOnUse">
        <circle cx="2" cy="2" r="1.5" fill="#101014"/></pattern>
    </defs>
    <g class="spin1" opacity=".38" stroke="#101014">
      <ellipse cx="700" cy="350" rx="560" ry="190" transform="rotate(-11 700 350)"/>
      <ellipse cx="700" cy="350" rx="440" ry="150" transform="rotate(9 700 350)"/>
      <circle cx="700" cy="350" r="295" stroke-dasharray="2 7"/>
    </g>
    <g class="spin2" opacity=".28" stroke="#101014">
      <ellipse cx="700" cy="350" rx="620" ry="240" transform="rotate(24 700 350)"/>
    </g>
    <g fill="#101014" opacity=".55">
      <circle cx="210" cy="180" r="2"/><circle cx="420" cy="90" r="2"/><circle cx="880" cy="140" r="2"/>
      <circle cx="1150" cy="330" r="2"/><circle cx="520" cy="620" r="2"/><circle cx="940" cy="600" r="2"/>
      <circle cx="130" cy="480" r="2"/><circle cx="1330" cy="560" r="2"/><circle cx="760" cy="40" r="2"/>
    </g>
    <g fill="#1d33ff">
      <circle cx="180" cy="120" r="7"/><circle cx="985" cy="88" r="6"/><circle cx="1245" cy="242" r="8"/>
      <circle cx="320" cy="522" r="6"/><circle cx="1122" cy="562" r="7"/><circle cx="700" cy="58" r="5"/>
      <circle cx="58" cy="362" r="6"/><circle cx="1358" cy="432" r="5"/><circle cx="540" cy="345" r="5"/>
    </g>
    <g stroke="#1d33ff" fill="none">
      <circle cx="1245" cy="242" r="15"/><circle cx="320" cy="522" r="13"/><circle cx="180" cy="120" r="14"/>
    </g>
    <rect x="940" y="380" width="54" height="54" fill="#1d33ff"/>
    <rect x="150" y="420" width="20" height="20" fill="#101014"/>
    <rect x="1268" y="118" width="34" height="34" stroke="#101014" fill="none"/>
    <rect x="652" y="298" width="40" height="40" fill="url(#htn)" opacity=".55"/>
    <rect x="84" y="86" width="150" height="92" fill="url(#hatch)" opacity=".4"/>
    <rect x="1150" y="470" width="130" height="80" fill="url(#hatch)" opacity=".3"/>
  </svg>
  <div class="ht1" aria-hidden="true"></div>
  <div class="ha1" aria-hidden="true"></div>
  <span class="sq sq1" aria-hidden="true"></span><span class="sq sq2" aria-hidden="true"></span>
  <span class="sq sq3" aria-hidden="true"></span><span class="sq sq4" aria-hidden="true"></span>
  <span class="sq sq5" aria-hidden="true"></span>
  <svg class="tw" style="right:18%;top:24%" width="26" height="26" viewBox="-13 -13 26 26" aria-hidden="true">
    <path d="M0-12 L2.6-2.6 L12 0 L2.6 2.6 L0 12 L-2.6 2.6 L-12 0 L-2.6-2.6 Z" fill="#1d33ff"/></svg>
  <svg class="tw" style="left:16%;top:60%;animation-delay:1.2s" width="18" height="18" viewBox="-13 -13 26 26" aria-hidden="true">
    <path d="M0-12 L2.6-2.6 L12 0 L2.6 2.6 L0 12 L-2.6 2.6 L-12 0 L-2.6-2.6 Z" fill="#101014"/></svg>
  <svg class="tw" style="right:32%;bottom:18%;animation-delay:2.1s" width="20" height="20" viewBox="-13 -13 26 26" aria-hidden="true">
    <path d="M0-12 L2.6-2.6 L12 0 L2.6 2.6 L0 12 L-2.6 2.6 L-12 0 L-2.6-2.6 Z" fill="#e5352b"/></svg>

  <p class="kicker">Complete Learning Path — V2.0 · 2026 · 考研深造路线</p>
  <h1 class="display">
    <span class="row"><i class="ghost" aria-hidden="true">COMPUTER</i><span class="t-blue">COMPUTER</span></span>
    <span class="row"><span class="t-line">SCIENCE</span><span class="zh">完整学习路径</span></span>
    <span class="refl" aria-hidden="true">COMPUTER SCIENCE</span>
  </h1>
  <p class="sub">复合型<span class="dot">·</span>抗替代<span class="dot">·</span>可长期进化 — <b>C++ 首发,考研回收</b></p>
  <div class="cta">
    <a class="btn" href="#sec-0">进入路径</a>
    <span class="hint">PROGRESS SAVED LOCALLY<br>打勾进度自动保存在本机浏览器</span>
  </div>
  <div class="scrolldown">SCROLL</div>
</section>
<div class="marquee" aria-hidden="true"><div class="mq">
  <span>理解 + 动手才算学过<b>✦</b>YOU CAN'T LEARN BY WATCHING<i>→</i>达标就翻篇,不达标不硬走<b>✦</b>DON'T HOARD COURSES<i>→</i>别囤课 — 收藏夹不是学习路径<b>✦</b>代码必须亲手敲<b>✦</b>TYPE IT YOURSELF<i>→</i></span>
  <span>理解 + 动手才算学过<b>✦</b>YOU CAN'T LEARN BY WATCHING<i>→</i>达标就翻篇,不达标不硬走<b>✦</b>DON'T HOARD COURSES<i>→</i>别囤课 — 收藏夹不是学习路径<b>✦</b>代码必须亲手敲<b>✦</b>TYPE IT YOURSELF<i>→</i></span>
</div></div>
"""

footer = """
<footer class="foot">
  <div class="fin" aria-hidden="true">FIN</div>
  <div class="fin-refl" aria-hidden="true">FIN</div>
  <p class="fp">本页由《计科学习路径_完整版.md》v2.0 构建生成 · 单文件离线可用<br>
  进度数据仅存储于本机浏览器(localStorage)· 资源以官方平台为准</p>
  <a href="#top">BACK TO TOP ↑</a>
</footer>
"""

howto = ('<section class="sec" id="howto" data-deco="hatch">'
         + header("§", "使用说明", "HOW TO USE THIS PATH")
         + f'<div class="sbody">{howto_html}</div></section>')

out = (TPL.replace("<!--NAV-->", nav)
          .replace("<!--HERO-->", hero)
          .replace("<!--HOWTO-->", howto)
          .replace("<!--CONTENT-->", content_html)
          .replace("<!--FOOTER-->", footer))

dest = ROOT / "index.html"
dest.write_text(out, encoding="utf-8")
print(f"OK -> {dest}")
print(f"sections={len(sections)}  checkboxes={CK[0]}  size={dest.stat().st_size:,} bytes")
