"""Build The Guybile website from content/*.md into dist/.

No dependencies beyond Python 3.9+.   python3 scripts/build.py
Output is plain static files: host dist/ anywhere (GitHub Pages, Netlify, ...).
"""
import hashlib
import html
import json
import os
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
SRC = ROOT / "src"
DIST = ROOT / "dist"

JS_VER = hashlib.sha256((Path(__file__).resolve().parent.parent / "src" / "app.js").read_bytes()).hexdigest()[:8]
CONFIG = json.loads((ROOT / "site.json").read_text())
# On GitHub Actions this is set automatically to "owner/repo".
REPO = os.environ.get("GITHUB_REPOSITORY") or CONFIG.get("repo", "")
BRANCH = CONFIG.get("branch", "main")

VERSE_LINE = re.compile(r"^(\d+):(\d+)\s+[—-]+\s+(.*)$")
TITLED = re.compile(r"^\*\*(.+?)\*\*\s+(.*)$")
BY = re.compile(r"\s+\[by\s+([^\]]{1,60})\]\s*$")
REF = re.compile(r"(?:<strong>)?Guybile (\d+):(\d+)(?:</strong>)?")


# ---------------------------------------------------------------- parsing

class ContentError(Exception):
    pass


def parse_file(path):
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    if not text.startswith("---\n"):
        raise ContentError(f"{path.name}: must start with a --- front-matter block")
    head, _, body = text[4:].partition("\n---\n")
    meta = {}
    for line in head.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip()
    if "title" not in meta:
        raise ContentError(f"{path.name}: front matter needs a title:")

    blocks, para = [], []

    def flush():
        if para:
            blocks.append({"type": "p", "md": " ".join(para)})
            para.clear()

    lines = body.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        s = line.strip()
        if not s:
            flush(); i += 1; continue
        if s.startswith("### ") or s.startswith("## "):
            flush(); blocks.append({"type": "h3", "text": s.lstrip("#").strip()}); i += 1; continue
        m = VERSE_LINE.match(s)
        if m:
            flush()
            ch, v, rest = int(m.group(1)), int(m.group(2)), m.group(3)
            by = BY.search(rest)
            if by:
                rest = rest[:by.start()].rstrip()
            b = {"type": "verse", "ch": ch, "v": v, "md": rest}
            if by:
                b["by"] = by.group(1).strip()
            t = TITLED.match(rest)
            if t:
                b["title"], b["md"] = t.group(1), t.group(2)
            blocks.append(b); i += 1; continue
        if re.match(r"^(-|\*|\d+\.)\s+", s):
            flush()
            ordered = bool(re.match(r"^\d+\.", s))
            items = []
            while i < len(lines) and re.match(r"^\s*(-|\*|\d+\.)\s+", lines[i]):
                items.append(re.sub(r"^\s*(-|\*|\d+\.)\s+", "", lines[i]).strip())
                i += 1
            blocks.append({"type": "list", "ordered": ordered, "items": items})
            continue
        if s.startswith("|"):
            flush()
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
                    rows.append(cells)
                i += 1
            blocks.append({"type": "table", "rows": rows})
            continue
        para.append(s)
        i += 1
    flush()
    return meta, blocks


def load_book():
    files = sorted(p for p in CONTENT.glob("*.md") if not p.name.startswith(("_", "README")))
    front, chapters, appendices = None, [], []
    for p in files:
        meta, blocks = parse_file(p)
        label = meta.get("label", "")
        sec = {"file": p.name, "title": meta["title"], "label": label, "blocks": blocks}
        m = re.match(r"Chapter (\d+)$", label)
        a = re.match(r"Appendix ([A-Z])$", label)
        if m:
            sec.update(kind="chapter", num=int(m.group(1)), slug=f"chapter-{m.group(1)}")
            for b in blocks:
                if b["type"] == "verse" and b["ch"] != sec["num"] and (b["ch"], b["v"]) != (69, 69):
                    print(f"  note: {p.name} has verse {b['ch']}:{b['v']} outside Chapter {sec['num']}")
            chapters.append(sec)
        elif a:
            sec.update(kind="appendix", num=a.group(1), slug=f"appendix-{a.group(1).lower()}")
            appendices.append(sec)
        elif "book" in meta:
            sec.update(kind="front", slug="index", book=meta["book"], tagline=meta.get("tagline", ""))
            front = sec
        else:
            raise ContentError(f"{p.name}: label: must be 'Chapter N' or 'Appendix X'")
    chapters.sort(key=lambda s: s["num"])
    nums = [c["num"] for c in chapters]
    if len(nums) != len(set(nums)):
        raise ContentError("two files claim the same chapter number")
    seen = {}
    for c in chapters:
        for b in c["blocks"]:
            if b["type"] == "verse":
                key = (b["ch"], b["v"])
                if key in seen:
                    raise ContentError(f"verse {key[0]}:{key[1]} appears twice ({seen[key]} and {c['file']})")
                seen[key] = c["file"]
    appendices.sort(key=lambda s: s["num"])
    return front, chapters, appendices


# ---------------------------------------------------------------- rendering

def esc(s):
    return html.escape(s, quote=True)


def md_inline(s, verse_index):
    s = html.escape(s, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?!\w)", r"<em>\1</em>", s)

    def ref(m):
        key = (int(m.group(1)), int(m.group(2)))
        slug = verse_index.get(key)
        if not slug:
            return m.group(0)
        return f'<a class="ref" href="{slug}.html#v{key[0]}-{key[1]}">Guybile {key[0]}:{key[1]}</a>'
    return REF.sub(ref, s)


def render_blocks(blocks, vi, chapter_num=None):
    out = []
    i = 0
    while i < len(blocks):
        b = blocks[i]
        t = b["type"]
        if t == "verse":
            vid = f"v{b['ch']}-{b['v']}"
            label = str(b["v"]) if b["ch"] == chapter_num else f"{b['ch']}:{b['v']}"
            body = md_inline(b["md"], vi)
            title = f'<span class="vt">{esc(b["title"])}</span> ' if b.get("title") else ""
            by = f' <span class="by">— {esc(b["by"])}</span>' if b.get("by") else ""
            out.append(
                f'<p class="v" id="{vid}" data-ref="{b["ch"]}:{b["v"]}">'
                f'<a class="num" href="#{vid}" aria-label="Verse {b["ch"]}:{b["v"]}">{label}</a>{title}{body}{by}</p>'
            )
        elif t == "p":
            # A run of 3+ wholly-italic paragraphs is liturgy (the Oath): set it apart.
            if _all_italic(b["md"]):
                j = i
                while j < len(blocks) and blocks[j]["type"] == "p" and _all_italic(blocks[j]["md"]):
                    j += 1
                if j - i >= 3:
                    lines = [f"<p>{md_inline(x['md'][1:-1], vi)}</p>" for x in blocks[i:j]]
                    if j < len(blocks) and blocks[j]["type"] == "p" and blocks[j]["md"].startswith("**"):
                        lines.append(f"<p>{md_inline(blocks[j]['md'], vi)}</p>")
                        j += 1
                    out.append('<div class="oath">' + "".join(lines) + "</div>")
                    i = j
                    continue
            cls = ' class="note"' if b["md"].startswith("*Note") else ""
            out.append(f"<p{cls}>{md_inline(b['md'], vi)}</p>")
        elif t == "h3":
            hid = re.sub(r"[^a-z0-9]+", "-", b["text"].lower()).strip("-")
            out.append(f'<h3 id="{hid}">{esc(b["text"])}</h3>')
        elif t == "list":
            tag = "ol" if b["ordered"] else "ul"
            out.append(f"<{tag}>" + "".join(f"<li>{md_inline(x, vi)}</li>" for x in b["items"]) + f"</{tag}>")
        elif t == "table":
            head, *rows = b["rows"]
            th = "".join(f"<th scope=\"col\">{md_inline(c, vi)}</th>" for c in head)
            body = ""
            for r in rows:
                body += "<tr>" + "".join(
                    f'<td data-h="{esc(head[k] if k < len(head) else "")}">{md_inline(c, vi)}</td>'
                    for k, c in enumerate(r)) + "</tr>"
            out.append(f'<table class="tbl"><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table>')
        i += 1
    return "\n".join(out)


def _all_italic(md):
    return md.startswith("*") and not md.startswith("**") and md.endswith("*") and md.count("*") == 2


ICONS = {
    "menu": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4 7h16M4 12h16M4 17h10"/></svg>',
    "search": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>',
    "close": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M6 6l12 12M18 6 6 18"/></svg>',
    "copy": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h8"/></svg>',
    "share": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 3v12M7 8l5-5 5 5"/><path d="M5 13v6a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-6"/></svg>',
    "save": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><path d="M6 3h12v18l-6-4-6 4z"/></svg>',
    "image": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-5-5L5 21"/></svg>',
    "listen": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><path d="M11 5 6 9H3v6h3l5 4z"/><path d="M15.5 8.5a5 5 0 0 1 0 7M18.5 5.5a9 9 0 0 1 0 13" stroke-linecap="round"/></svg>',
    "dice": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="4"/><circle cx="8" cy="8" r="1.3" fill="currentColor"/><circle cx="16" cy="16" r="1.3" fill="currentColor"/><circle cx="12" cy="12" r="1.3" fill="currentColor"/></svg>',
    "seal":'<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="32" cy="32" r="29"/><circle cx="32" cy="32" r="24" stroke-dasharray="2 3"/><path d="M41 24.5A11 11 0 1 0 43 34h-9" stroke-width="3" stroke-linecap="round"/></svg>',
}


def gc_tag():
    """GoatCounter visitor stats (no cookies). Set "goatcounter" in site.json to the site code."""
    code = CONFIG.get("goatcounter", "")
    return (f'\n<script data-goatcounter="https://{code}.goatcounter.com/count" async src="https://gc.zgo.at/count.js"></script>'
            if code else "")


def page(*, title, desc, body, css, where="", current="", toc_html="", canonical="", extra_head="", ld=""):
    full_title = "The Guybile" if not title else f"{title} · The Guybile"
    site_url = CONFIG.get("site_url", "").rstrip("/")
    canon = f'<link rel="canonical" href="{site_url}/{canonical}">' if site_url else ""
    og_img = f'<meta property="og:image" content="{site_url}/og.jpg">' if site_url else ""
    return f"""<!doctype html>
<html lang="en" data-theme="paper">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(full_title)}</title>
<meta name="description" content="{esc(desc)}">
<meta name="theme-color" content="#3a1f17">
<meta property="og:title" content="{esc(full_title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:type" content="{'website' if not title else 'article'}">
<meta property="og:site_name" content="The Guybile">{og_img}
{f'<meta property="og:url" content="{site_url}/{canonical}">' if site_url else ''}
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(full_title)}">
<meta name="twitter:description" content="{esc(desc)}">
{f'<meta name="twitter:image" content="{site_url}/og.jpg">' if site_url else ''}
{canon}{f'<script type="application/ld+json">{ld}</script>' if ld else ''}
<link rel="icon" href="icon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="icon-192.png">
<link rel="manifest" href="manifest.webmanifest">
<script>(function(){{try{{var d=document.documentElement,t=localStorage.getItem('g-theme'),z=localStorage.getItem('g-size');if(!t&&matchMedia('(prefers-color-scheme: dark)').matches)t='night';if(t)d.dataset.theme=t;if(z)d.dataset.size=z;}}catch(e){{}}}})()</script>
<style>{css}</style>{extra_head}
<script src="app.js?v={JS_VER}" defer></script>{gc_tag()}
</head>
<body>
<a class="skip" href="#main">Skip to text</a>
<header class="bar" id="bar">
  <button class="btn" id="open-toc" aria-label="Contents" aria-controls="toc" aria-expanded="false">{ICONS['menu']}</button>
  <a class="brand" href="index.html">The <b>Guybile</b></a>
  <div class="where">{esc(where)}</div>
  <a class="btn" href="search.html" aria-label="Search verses">{ICONS['search']}</a>
  <button class="btn" id="open-set" aria-label="Reading settings" aria-controls="settings" aria-expanded="false"><span style="font-family:var(--serif);font-size:1.1rem">Aa</span></button>
  <div class="progress" id="progress"></div>
</header>
<div class="scrim" id="scrim"></div>
<nav class="drawer" id="toc" aria-label="Contents" aria-hidden="true">
  <header><h2>Contents</h2><button class="btn" data-close aria-label="Close contents">{ICONS['close']}</button></header>
  {toc_html.replace(f'href="{current}.html"', f'href="{current}.html" aria-current="page"') if current else toc_html}
</nav>
<section class="sheet" id="settings" aria-label="Reading settings" aria-hidden="true">
  <h2>Reading settings <button class="btn" data-close aria-label="Close settings">{ICONS['close']}</button></h2>
  <p class="lbl">Page</p>
  <div class="row">
    <button class="seg t-paper" data-theme-set="paper">Paper</button>
    <button class="seg t-light" data-theme-set="light">Light</button>
    <button class="seg t-night" data-theme-set="night">Night</button>
  </div>
  <p class="lbl">Text size</p>
  <div class="row">
    <button class="seg" data-size-set="s" style="font-size:.8rem">A</button>
    <button class="seg" data-size-set="m" style="font-size:.95rem">A</button>
    <button class="seg" data-size-set="l" style="font-size:1.1rem">A</button>
    <button class="seg" data-size-set="xl" style="font-size:1.3rem">A</button>
  </div>
</section>
{body}
<div class="vact" id="vact" role="toolbar" aria-label="Verse actions">
  <button data-act="copy">{ICONS['copy']}Copy</button>
  <button data-act="save">{ICONS['save']}<span>Save</span></button>
  <button data-act="image">{ICONS['image']}Image</button>
  <button data-act="share">{ICONS['share']}Share</button>
</div>
<div class="toast" id="toast" role="status" aria-live="polite"></div>
</body>
</html>
"""


def footer():
    links = ['<a href="index.html">Home</a>', '<a href="search.html">Search</a>',
             '<a href="saved.html">Saved</a>', '<a href="credits.html">Authors</a>',
             '<a href="about.html">Why Guybile?</a>',
             '<button class="linkbtn" data-share-site>Share with thy bros</button>']
    if REPO:
        links += [f'<a href="{suggest_url()}">Suggest a verse</a>',
                  f'<a href="https://github.com/{REPO}">Source</a>']
    return (f'<footer class="foot">{" · ".join(links)}<br>'
            "The Guybile is humour and brotherhood, not medical, legal or financial advice.<br>"
            "If thou art in crisis, call thy local emergency number or a crisis line (988 in the US).</footer>")


def suggest_url(chapter_label=""):
    from urllib.parse import quote
    url = f"https://github.com/{REPO}/issues/new?template=new-verse.yml"
    if chapter_label:
        url += "&chapter=" + quote(chapter_label)
    return url


def toc(chapters, appendices):
    items = ['<ul class="toc">', '<li><a href="index.html"><span class="n">✦</span>The Preamble</a></li>',
             '<li class="sep">Chapters</li>']
    for c in chapters:
        items.append(f'<li><a href="{c["slug"]}.html"><span class="n">{c["num"]}</span>{esc(c["title"])}</a></li>')
    items.append('<li class="sep">Appendices</li>')
    for a in appendices:
        items.append(f'<li><a href="{a["slug"]}.html"><span class="n">{a["num"]}</span>{esc(a["title"])}</a></li>')
    items.append('<li class="sep">More</li>')
    items.append('<li><a href="saved.html"><span class="n">★</span>Saved verses</a></li>')
    items.append('<li><a href="credits.html"><span class="n">✎</span>The Authors</a></li>')
    items.append('<li><a href="about.html"><span class="n">i</span>Why \u201cGuybile\u201d?</a></li>')
    items.append('<li><a href="oath.html"><span class="n">❦</span>Swear in a brother</a></li>')
    items.append('<li><a href="quiz.html"><span class="n">?</span>Which law didst thou break?</a></li>')
    items.append('</ul>')
    return "".join(items)


def _ld(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def book_ld(front, chapters, total):
    url = CONFIG.get("site_url", "").rstrip("/")
    return _ld({
        "@context": "https://schema.org", "@type": "Book", "name": front["book"],
        "description": front["tagline"], "url": url + "/", "inLanguage": "en",
        "bookFormat": "https://schema.org/EBook", "isAccessibleForFree": True,
        "genre": ["Humor", "Self-help"], "numberOfPages": len(chapters),
        "hasPart": [{"@type": "Chapter", "name": c["title"], "position": c["num"],
                     "url": f"{url}/{c['slug']}.html"} for c in chapters],
    })


def chapter_ld(sec, front):
    url = CONFIG.get("site_url", "").rstrip("/")
    return _ld({
        "@context": "https://schema.org", "@type": "Chapter", "name": sec["title"],
        "position": str(sec["num"]), "url": f"{url}/{sec['slug']}.html",
        "isPartOf": {"@type": "Book", "name": front["book"], "url": url + "/"},
    })


def dropcap(html_):
    """Wrap the first letter of the first plain verse in a decorated capital."""
    return re.sub(r'(<p class="v"[^>]*><a class="num"[^>]*>[^<]*</a>)([A-Za-z])',
                  r'\1<span class="dc">\2</span>', html_, count=1)


def verse_count(sec):
    return sum(1 for b in sec["blocks"] if b["type"] == "verse")


def main():
    front, chapters, appendices = load_book()
    css = (SRC / "styles.css").read_text()
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    css = re.sub(r"\s+", " ", css)
    css = re.sub(r"\s*([{};,>])\s*", r"\1", css).strip()

    vi = {}
    for c in chapters:
        for b in c["blocks"]:
            if b["type"] == "verse":
                vi[(b["ch"], b["v"])] = c["slug"]

    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    toc_html = toc(chapters, appendices)
    seq = chapters + appendices
    pages = ["index.html", "search.html", "404.html"]

    # ---- chapter + appendix pages
    for idx, sec in enumerate(seq):
        prev_ = seq[idx - 1] if idx > 0 else None
        next_ = seq[idx + 1] if idx + 1 < len(seq) else None
        pv = (f'<a class="prev" href="{prev_["slug"]}.html"><small>← {esc(prev_["label"])}</small><span>{esc(prev_["title"])}</span></a>'
              if prev_ else '<a class="prev" href="index.html"><small>← Start</small><span>The Preamble</span></a>')
        nx = (f'<a class="next" href="{next_["slug"]}.html"><small>{esc(next_["label"])} →</small><span>{esc(next_["title"])}</span></a>'
              if next_ else '<a class="next" href="index.html"><small>Back to →</small><span>The beginning</span></a>')
        contrib = ""
        if REPO:
            contrib = (f'<p class="meta" style="text-align:center;margin-top:2.5rem">Got a verse for this chapter? '
                       f'<a href="{suggest_url(sec["label"] + " — " + sec["title"])}">Suggest one</a> · '
                       f'<a href="https://github.com/{REPO}/edit/{BRANCH}/content/{sec["file"]}">Edit on GitHub</a></p>')
        print_btn = (f'<button class="chip" onclick="print()">{ICONS["copy"]}<span>Print card</span></button>'
                     if sec["slug"] == "appendix-c" else "")
        n = verse_count(sec)
        sub = f'<div class="orn"><span>{n} verses</span></div>' if n else '<div class="orn"><span>✦</span></div>'
        body = f"""<main id="main" data-page="{sec['slug']}" data-label="{esc(sec['label'])}" data-title="{esc(sec['title'])}">
<article class="col">
  <header class="chead"><p class="kicker">{esc(sec['label'])}</p><h1>{esc(sec['title'])}</h1>{sub}
    <div class="tools"><button class="chip" id="listen" hidden>{ICONS['listen']}<span>Listen</span></button><button class="chip" id="share-page">{ICONS['share']}<span>Share chapter</span></button>{print_btn}</div></header>
  <div class="content verses">
{dropcap(render_blocks(sec['blocks'], vi, sec['num'] if sec['kind'] == 'chapter' else None))}
  </div>
  {contrib}
</article>
<nav class="pager" aria-label="Chapters">{pv}{nx}</nav>
</main>
{footer()}"""
        first = next((b["md"] for b in sec["blocks"] if b["type"] in ("verse", "p")), sec["title"])
        desc = re.sub(r"[*]", "", first)[:155]
        (DIST / f"{sec['slug']}.html").write_text(page(
            title=f"{sec['label']}: {sec['title']}", desc=desc, body=body, css=css,
            where=f"{sec['label']} · {sec['title']}", current=sec["slug"], toc_html=toc_html,
            canonical=f"{sec['slug']}.html", ld=chapter_ld(sec, front)))
        pages.append(f"{sec['slug']}.html")

    # ---- home
    def card(s):
        n = verse_count(s)
        small = f"<small>{n} verses</small>" if n else ""
        return f'<li><a href="{s["slug"]}.html"><span class="n">{s["num"]}</span><span class="t">{esc(s["title"])}{small}</span></a></li>'

    total = len(vi)
    home = f"""<main id="main" class="home" data-page="index">
<section class="cover">
  <div class="inner">
    <div class="seal">{ICONS['seal']}</div>
    <p class="kicker">{len(chapters)} chapters · {total} verses</p>
    <h1>{esc(front['book'])}</h1>
    <p class="tag">{esc(front['tagline'])}</p>
    <div class="cta">
      <a class="primary" href="{chapters[0]['slug']}.html">Begin at Chapter 1</a>
      <a class="ghost" id="continue" href="#" hidden>Continue reading</a>
      <a class="ghost" href="#contents" id="browse">Browse chapters</a>
    </div>
    <p class="bros"><button class="sharebros" data-share-site>{ICONS['share']}<span>Share with thy bros</span></button></p>
  </div>
</section>
<div style="padding:0 1.25rem">
<aside class="daily" id="daily" aria-live="polite">
  <p class="lbl">Verse of the day</p>
  <blockquote id="daily-text">&nbsp;</blockquote>
  <a id="daily-ref" href="#">&nbsp;</a>
  <div class="dact">
    <button class="chip" id="daily-random">{ICONS['dice']}<span>Another</span></button>
    <button class="chip" id="daily-image">{ICONS['image']}<span>Make image</span></button>
  </div>
</aside>
<figure class="frontis"><img src="art/frontispiece.webp" width="560" height="840" loading="lazy" decoding="async"
  alt="Engraving of four laughing friends at a feast table, raising tankards in a toast, one biting a slice of pizza">
  <figcaption>And on the seventh day, the boys ordered pizza.</figcaption></figure>
</div>
<div style="padding:0 1.25rem">
<article class="col content">
  <h2 class="sec" style="margin-top:2.75rem">{esc(front['title'])}</h2>
{render_blocks(front['blocks'], vi)}
</article>
<h2 class="sec" id="contents">The Chapters</h2>
<ul class="grid">{''.join(card(c) for c in chapters)}</ul>
<h2 class="sec">The Appendices</h2>
<ul class="grid">{''.join(card(a) for a in appendices)}</ul>
<h2 class="sec">For thy brothers</h2>
<ul class="more"><li><a href="oath.html"><b>Swear in a brother</b><span>Make a Sworn Brother certificate to share or print.</span></a></li>
<li><a href="quiz.html"><b>Which law didst thou break?</b><span>Five questions. One verse. No mercy.</span></a></li></ul>
<section class="why">
  <h2 class="sec">Why \u201cGuybile\u201d?</h2>
  <p>Guy + Bible. The Bro Code, written as scripture. Yes, it is spelled like <em>bile</em>, and yes, that is on purpose. <a href="about.html">Read why.</a></p>
</section>
<section class="join">
  <p class="kicker">The Guybile is never finished</p>
  <h2>Write the next verse</h2>
  <p>Got a law every brother should know? Suggest it. If it is accepted, it goes into the book with thy name on it.</p>
  <div class="cta">{f'<a class="primary" href="{suggest_url()}">Suggest a verse</a>' if REPO else ''}<a class="ghost" href="credits.html">Meet the authors</a><a class="ghost" href="saved.html">My saved verses</a></div>
</section>
</div>
</main>
{footer()}"""
    (DIST / "index.html").write_text(page(
        title="", desc=front["tagline"], body=home, css=css, current="index",
        toc_html=toc_html, canonical="", ld=book_ld(front, chapters, total)))

    # ---- saved verses (stored on the reader's device)
    saved = f"""<main id="main" data-page="saved"><div class="col">
<header class="chead"><p class="kicker">Thy collection</p><h1>Saved verses</h1><div class="orn"><span>✦</span></div></header>
<p class="meta" id="saved-count" style="text-align:center"></p>
<ul class="results" id="saved-list"></ul>
<p class="meta" id="saved-empty" hidden style="text-align:center">Nothing saved yet. Tap any verse, then <strong>Save</strong>. Saved verses stay on this device.</p>
</div></main>
{footer()}"""
    (DIST / "saved.html").write_text(page(title="Saved verses", desc="Thy saved verses from The Guybile.",
                                          body=saved, css=css, toc_html=toc_html, canonical="saved.html"))
    pages.append("saved.html")

    # ---- credits
    authors = {}
    for c in chapters:
        for b in c["blocks"]:
            if b["type"] == "verse" and b.get("by"):
                authors.setdefault(b["by"], []).append((b["ch"], b["v"], c["slug"]))
    if authors:
        rows = "".join(
            f'<li><strong>{esc(name)}</strong><br>' + ", ".join(
                f'<a class="ref" href="{slug}.html#v{ch}-{v}">Guybile {ch}:{v}</a>' for ch, v, slug in refs) + "</li>"
            for name, refs in sorted(authors.items(), key=lambda kv: (-len(kv[1]), kv[0].lower())))
        authors_html = f'<ul class="authors">{rows}</ul>'
    else:
        authors_html = '<p style="text-align:center"><em>No guest verses yet. Thine could be the first.</em></p>'
    suggest = (f'<p style="text-align:center"><a class="ref" href="{suggest_url()}">Suggest a verse</a></p>' if REPO else "")
    credits = f"""<main id="main" data-page="credits"><div class="col content">
<header class="chead"><p class="kicker">Written by the brothers</p><h1>The Authors</h1><div class="orn"><span>✦</span></div></header>
<p>The Guybile was begun by its first author and is written onward by every brother who lived a lesson and told the story afterwards. These are the brothers whose verses are now scripture.</p>
{authors_html}
{suggest}
</div></main>
{footer()}"""
    (DIST / "credits.html").write_text(page(title="The Authors", desc="The brothers who wrote The Guybile.",
                                            body=credits, css=css, toc_html=toc_html, canonical="credits.html"))
    pages.append("credits.html")

    # ---- search
    search = f"""<main id="main" data-page="search"><div class="col">
<header class="chead" style="padding-bottom:0"><p class="kicker">Search</p><h1>Find a verse</h1></header>
<div class="search"><label class="sr-only" for="q" style="position:absolute;left:-999px">Search verses</label>
<input id="q" type="search" placeholder="Try “group chat”, “money”, “gym”…" autocomplete="off" enterkeyhint="search"></div>
<p class="meta" id="count"></p>
<ul class="results" id="results"></ul>
</div></main>
{footer()}"""
    (DIST / "search.html").write_text(page(title="Search", desc="Search every verse of The Guybile.",
                                           body=search, css=css, toc_html=toc_html, canonical="search.html"))

    # ---- about: why Guybile
    about = f"""<main id="main" data-page="about"><div class="col content">
<header class="chead"><p class="kicker">The name</p><h1>Why \u201cGuybile\u201d?</h1><div class="orn"><span>Say it: guy-bile</span></div></header>
<p><strong>Guy + Bible.</strong> The Guybile is the Bro Code rewritten as scripture: the unwritten laws of brotherhood, friendship, food, money, love, plans and the group chat, in the voice of the old books.</p>
<p><strong>Why not just \u201cBible\u201d?</strong> Because the Bible already has a publisher, a few billion readers and a very good lawyer. This is a book for guys, and it should sound like one.</p>
<p><strong>Why the \u201ci\u201d, and why does it spell \u201cbile\u201d?</strong> Because it is meant to. Bile is bitter, and so is honest advice. The best verses here start as a joke and end as a truth that stings a little: <em>funny on the surface, true underneath</em>. A misplaced letter also suits a book about men and their plans: close enough to look right, wrong enough to be funny.</p>
<p><strong>Is it a religion?</strong> No. It borrows the voice of scripture for laughs and kindness, with no offence meant to any faith, and no one is asked to believe anything. Read a verse, argue with it, send it to a brother.</p>
<p><strong>Is it finished?</strong> Never. Anyone can add a verse, and the maintainer decides what goes in. <a href="{suggest_url()}">Write the next one.</a></p>
</div></main>
{footer()}"""
    (DIST / "about.html").write_text(page(title="Why Guybile?", desc="Guy + Bible. Why The Guybile is spelled the way it is.",
                                          body=about, css=css, toc_html=toc_html, canonical="about.html"))
    pages.append("about.html")

    # ---- oath certificate (drawn on the reader's device; names never leave it)
    oath = f"""<main id="main" data-page="oath"><div class="col">
<header class="chead"><p class="kicker">The Brother's Oath</p><h1>Swear in a brother</h1><div class="orn"><span>A certificate for thy brother</span></div></header>
<form class="form" id="oath-form" autocomplete="off">
  <label>Thy brother's name<input id="o-name" maxlength="40" required placeholder="e.g. Rahul"></label>
  <label>Sworn in by <small>(optional)</small><input id="o-by" maxlength="40" placeholder="Thy name"></label>
  <button class="primary" type="submit">Make the certificate</button>
  <p class="meta">Names stay on this device. Nothing is sent anywhere.</p>
</form>
<figure class="cert" id="cert" hidden><img id="cert-img" alt="Oath certificate"><div class="dact">
  <button class="chip" id="cert-share">{ICONS['share']}<span>Share</span></button>
  <button class="chip" id="cert-print" onclick="print()">{ICONS['copy']}<span>Print</span></button></div></figure>
</div></main>
{footer()}"""
    (DIST / "oath.html").write_text(page(title="Swear in a brother", desc="Make a Sworn Brother of the Guybile certificate for thy friend.",
                                         body=oath, css=css, toc_html=toc_html, canonical="oath.html"))
    pages.append("oath.html")

    # ---- quiz
    quiz_q = [
        ["A brother texts \u201cu up?\u201d at 2 a.m. Thou\u2026", [["Leavest him on read till morning", 13], ["Callest. It is a crisis or a story.", 1], ["Sendest a meme instead", 18], ["Askest if he hath eaten", 3]]],
        ["The plan was \u201c8 p.m. sharp.\u201d Thou arrivest\u2026", [["At 8:00, alone, and furious", 22], ["At 9:40, with snacks", 3], ["\u201cOn my way\u201d (still in the shower)", 2], ["Never. Cancelled at 7:58.", 21]]],
        ["Thy bank balance is best described as\u2026", [["A mystery I choose not to solve", 6], ["A gadget I did not need", 15], ["A road trip", 16], ["Fine. I have a spreadsheet.", 23]]],
        ["Most of thy screen time last week went to\u2026", [["The group chat", 13], ["Dating apps", 19], ["Games", 14], ["Doomscrolling", 18]]],
        ["When life goes wrong, thou\u2026", [["Hittest the gym", 9], ["Sayest \u201cI\u2019m fine\u201d for three months", 8], ["Callest a brother", 1], ["Apologisest and fixest it", 27]]],
    ]
    quiz = f"""<main id="main" data-page="quiz"><div class="col">
<header class="chead"><p class="kicker">Five questions</p><h1>Which law didst thou break?</h1><div class="orn"><span>Answer honestly. The Guybile knoweth.</span></div></header>
<div id="quiz" class="quiz"></div>
<script type="application/json" id="quiz-data">{_ld(quiz_q)}</script>
</div></main>
{footer()}"""
    (DIST / "quiz.html").write_text(page(title="Which law didst thou break?", desc="Five questions. One verse. Find the law of The Guybile thou hast broken.",
                                         body=quiz, css=css, toc_html=toc_html, canonical="quiz.html"))
    pages.append("quiz.html")

    (DIST / "404.html").write_text(page(title="Lost", desc="Page not found.", css=css, toc_html=toc_html, body=f"""
<main id="main" data-page="404"><div class="col content" style="text-align:center;padding-top:3rem">
<p class="kicker" style="font:700 .72rem var(--sans);letter-spacing:.22em;color:var(--gold)">404</p>
<h1>Thou art lost, brother.</h1><p>This page is five minutes away, which means it does not exist.</p>
<p><a class="ref" href="index.html">Return home</a></p></div></main>{footer()}"""))

    # ---- data for search + verse of the day
    verses = []
    for c in chapters:
        for b in c["blocks"]:
            if b["type"] == "verse":
                txt = re.sub(r"\*+", "", (b.get("title", "") + " " + b["md"]).strip())
                verses.append([f"{b['ch']}:{b['v']}", c["slug"], c["title"], txt])
    (DIST / "verses.json").write_text(json.dumps(verses, ensure_ascii=False, separators=(",", ":")))

    # ---- one tiny page per verse, so a shared link previews that verse's card
    #      (the card images themselves are drawn by scripts/verse_cards.py)
    vdir = DIST / "v"
    vdir.mkdir(exist_ok=True)
    base = CONFIG.get("site_url", "").rstrip("/")
    for ref, slug, ctitle, txt in verses:
        key = ref.replace(":", "-")
        target = f"{slug}.html#v{key}"
        title = f"Guybile {ref}"
        desc = esc(txt[:200])
        img = f"{base}/v/{key}.jpg" if base else f"{key}.jpg"
        (vdir / f"{key}.html").write_text(f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · The Guybile</title>
<meta name="description" content="{desc}">
<meta name="robots" content="noindex, follow">
<link rel="canonical" href="{base}/{target}">
<meta property="og:type" content="article"><meta property="og:site_name" content="The Guybile">
<meta property="og:title" content="{esc(title)} · {esc(ctitle)}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{base}/v/{key}.html">
<meta property="og:image" content="{img}"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="{img}">
<meta http-equiv="refresh" content="0; url=../{target}">
<script>location.replace("../{target}")</script>
<style>body{{font:1.2rem/1.6 Georgia,serif;background:#f5eedf;color:#2b241d;max-width:34rem;margin:4rem auto;padding:0 1.25rem}}a{{color:#9a2a1c}}</style>
</head><body><p>{esc(txt)}</p><p><a href="../{target}">{esc(title)} — read it in The Guybile</a></p></body></html>
""")

    # ---- static assets
    for f in ("app.js", "icon.svg", "icon-192.png", "icon-512.png", "og.jpg"):
        if (SRC / f).exists():
            shutil.copy(SRC / f, DIST / f)
    if (SRC / "art").is_dir():
        shutil.copytree(SRC / "art", DIST / "art")
    (DIST / "manifest.webmanifest").write_text(json.dumps({
        "name": "The Guybile", "short_name": "Guybile",
        "description": front["tagline"], "start_url": "./index.html", "scope": "./",
        "display": "standalone", "background_color": "#f5eedf", "theme_color": "#3a1f17",
        "icons": [{"src": "icon.svg", "sizes": "any", "type": "image/svg+xml"},
                  {"src": "icon-192.png", "sizes": "192x192", "type": "image/png"},
                  {"src": "icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"}],
    }, indent=1))

    # ---- service worker: precache everything, version = hash of all output
    assets = pages + [f"app.js?v={JS_VER}", "verses.json", "manifest.webmanifest", "icon.svg"]
    assets += [f for f in ("icon-192.png", "art/paper.webp", "art/fleuron.webp", "art/corner.webp", "art/cover.webp")
               if (DIST / f).exists()]
    h = hashlib.sha256()
    for a in sorted(assets):
        h.update((DIST / a.split("?")[0]).read_bytes())
    sw = (SRC / "sw.js").read_text().replace("__VERSION__", h.hexdigest()[:10]).replace(
        "__ASSETS__", json.dumps(["./"] + assets))
    (DIST / "sw.js").write_text(sw)
    (DIST / ".nojekyll").write_text("")
    site_url = CONFIG.get("site_url", "").rstrip("/")
    domain = re.sub(r"^https?://", "", site_url).split("/")[0]
    if domain and not domain.endswith("github.io"):
        (DIST / "CNAME").write_text(domain + "\n")
    if site_url:
        from datetime import date
        today = date.today().isoformat()
        urls = [u for u in pages if u not in ("404.html", "saved.html")]
        sm = "".join(
            f"<url><loc>{site_url}/{'' if u == 'index.html' else u}</loc><lastmod>{today}</lastmod>"
            f"<priority>{'1.0' if u == 'index.html' else '0.8' if u.startswith('chapter') else '0.5'}</priority></url>"
            for u in urls)
        (DIST / "sitemap.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{sm}</urlset>\n')
        (DIST / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {site_url}/sitemap.xml\n")
        llms = [f"# {front['book']}", "", f"> {front['tagline']}", "",
                "A free, open book of humorous and sincere advice for men, written as scripture (chapter:verse).",
                "Anyone can suggest verses. Each chapter is a plain HTML page.", "", "## Chapters", ""]
        llms += [f"- [{c['label']}: {c['title']}]({site_url}/{c['slug']}.html)" for c in chapters]
        llms += ["", "## Appendices", ""]
        llms += [f"- [{a['label']}: {a['title']}]({site_url}/{a['slug']}.html)" for a in appendices]
        (DIST / "llms.txt").write_text("\n".join(llms) + "\n")
    write_issue_form(chapters)

    size = sum(p.stat().st_size for p in DIST.iterdir() if p.is_file())
    print(f"Built {len(pages)} pages, {total} verses, {size/1024:.0f} KB -> dist/"
          + ("" if REPO else "  (set \"repo\" in site.json to show contribution links)"))


def write_issue_form(chapters):
    """Keep the "Suggest a verse" form's chapter list in step with content/."""
    opts = [f"Chapter {c['num']} — {c['title']}" for c in chapters] + ["A new topic (name it below)"]
    options = "\n".join(f"        - {json.dumps(o, ensure_ascii=False)}" for o in opts)
    form = f"""# Generated by scripts/build.py from content/. Edit the build script, not this file.
name: Suggest a verse
description: Add a verse to The Guybile. The maintainer reviews every one before it goes live.
title: "Verse: "
labels: ["verse"]
body:
  - type: markdown
    attributes:
      value: |
        Like a suggestion someone else made? Give it a 👍. The most-loved ones get read first.

        Write it like scripture: one or two sentences, funny on the surface, true underneath.
        Keep it kind. No names of real private people, nothing hateful, nothing that would hurt a brother who is already down.
  - type: dropdown
    id: chapter
    attributes:
      label: Chapter
      description: Where does it belong? Pick "A new topic" if none fit.
      options:
{options}
    validations:
      required: true
  - type: input
    id: topic
    attributes:
      label: New topic name
      description: Only if you picked "A new topic". For example "Pets", "Cooking for One", "Moving Abroad".
  - type: textarea
    id: verse
    attributes:
      label: Your verse
      description: Just the verse. The number is added for you.
      placeholder: "Thou shalt not reply 'k' to a paragraph."
    validations:
      required: true
  - type: input
    id: credit
    attributes:
      label: Credit (optional)
      description: Thy name or handle, shown under the verse and on the Authors page. Leave empty to stay anonymous.
  - type: checkboxes
    id: terms
    attributes:
      label: The fine print
      options:
        - label: I wrote this verse myself, and I am happy for it to be published in The Guybile under its licence.
          required: true
"""
    target = ROOT / ".github" / "ISSUE_TEMPLATE" / "new-verse.yml"
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists() or target.read_text() != form:
        target.write_text(form)


if __name__ == "__main__":
    try:
        main()
    except ContentError as e:
        raise SystemExit(f"Content error: {e}")
