"""One-time import: convert the Claude Docs XML export (content/_import/source.xml)
into one Markdown file per chapter under content/.

After the import, the Markdown files are the source of truth: contributors
edit them directly, so do not re-run this unless you mean to overwrite them.
  python3 scripts/export_doc.py
"""
import html
import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "content" / "_import" / "source.xml"
OUT = ROOT / "content"

CHAPTER_RE = re.compile(r"^(Chapter (\d+)|Appendix ([A-Z]))\s+—\s+(.*)$")


def inline(el):
    """Return inline HTML for a paragraph's <text> children."""
    out = []
    for t in el.iter("text"):
        for node in [t] + list(t):
            if node is t:
                if t.text:
                    out.append(html.escape(t.text, quote=False))
                continue
            inner = html.escape("".join(node.itertext()), quote=False)
            if node.tag == "bold":
                out.append(f"<strong>{inner}</strong>")
            elif node.tag == "italic":
                out.append(f"<em>{inner}</em>")
            else:
                out.append(inner)
            if node.tail:
                out.append(html.escape(node.tail, quote=False))
    return "".join(out)


def plain(el):
    return "".join(el.itertext()).strip()


VERSE_HTML_RE = re.compile(r"^<strong>\s*Guybile (\d+):(\d+)\s*</strong>\s*—\s*")
# Chapter 12 style: "**Guybile 12:1 — The Hunters.** text"
TITLED_VERSE_RE = re.compile(r"^<strong>\s*Guybile (\d+):(\d+)\s*—\s*([^<]*?)\s*</strong>\s*")


def verse_of(p):
    """If paragraph is a verse ("**Guybile c:v** — text"), return (c, v, html, title).

    The doc sometimes splits the bold label into several runs, so adjacent
    <strong> runs are merged before matching.
    """
    h = inline(p).replace("</strong><strong>", "")
    m = VERSE_HTML_RE.match(h)
    if m:
        return int(m.group(1)), int(m.group(2)), h[m.end():], None
    m = TITLED_VERSE_RE.match(h)
    if m:
        return int(m.group(1)), int(m.group(2)), h[m.end():], m.group(3)
    return None


def block_of(el):
    if el.tag == "paragraph":
        level = el.get("heading")
        if level:
            return {"type": f"h{level}", "text": plain(el)}
        v = verse_of(el)
        if v:
            b = {"type": "verse", "ch": v[0], "v": v[1], "html": v[2]}
            if v[3]:
                b["title"] = v[3]
            return b
        h = inline(el).replace("</strong><strong>", "").strip()
        return {"type": "p", "html": h} if h else None
    if el.tag == "list":
        items = [inline(li) for li in el.findall("listItem")]
        return {"type": "list", "ordered": el.get("kind") == "ordered", "items": items}
    if el.tag == "table":
        rows = []
        for row in el.findall("row"):
            rows.append([
                {"html": inline(c), "header": c.get("header") == "true"}
                for c in row.findall("cell")
            ])
        return {"type": "table", "rows": rows}
    if el.tag == "horizontalRule":
        return None
    return None


def main():
    root = ET.parse(SRC).getroot()
    children = list(root)

    book = {"title": plain(children[0]), "tagline": plain(children[1]), "sections": []}
    current = None

    for el in children[2:]:
        if el.tag == "paragraph" and el.get("heading") == "2":
            title = plain(el)
            m = CHAPTER_RE.match(title)
            if m and m.group(2):
                num = int(m.group(2))
                current = {"slug": f"chapter-{num}", "kind": "chapter", "num": num,
                           "label": f"Chapter {num}", "title": m.group(4), "blocks": []}
            elif m and m.group(3):
                letter = m.group(3)
                current = {"slug": f"appendix-{letter.lower()}", "kind": "appendix",
                           "num": letter, "label": f"Appendix {letter}",
                           "title": m.group(4), "blocks": []}
            else:
                slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
                current = {"slug": slug, "kind": "front", "num": None, "label": "",
                           "title": title, "blocks": []}
            book["sections"].append(current)
            continue
        if current is None:
            continue  # byline (date + author mention): not part of the book
        b = block_of(el)
        if b:
            current["blocks"].append(b)

    write_markdown(book)


def to_md(h):
    h = h.replace("<strong>", "**").replace("</strong>", "**")
    h = h.replace("<em>", "*").replace("</em>", "*")
    return html.unescape(h).strip()


TITLE_SLUG = re.compile(r"[^a-z0-9]+")


def file_name(sec):
    words = sec["title"].lower().replace("'", "")
    words = re.sub(r"^the (laws|law) of ", "", words)
    words = re.sub(r"^the ", "", words)
    short = TITLE_SLUG.sub("-", words).strip("-")[:40].rstrip("-")
    if sec["kind"] == "chapter":
        return f"{sec['num']:02d}-{short}.md"
    if sec["kind"] == "appendix":
        return f"{sec['num'].lower()}-{short}.md"
    return f"00-{short}.md"


def write_markdown(book):
    count = 0
    for sec in book["sections"]:
        lines = ["---"]
        if sec["kind"] == "front":
            lines += [f"book: {book['title']}", f"tagline: {book['tagline']}"]
        else:
            lines.append(f"label: {sec['label']}")
        lines += [f"title: {sec['title']}", "---", ""]
        for b in sec["blocks"]:
            t = b["type"]
            if t == "verse":
                count += 1
                title = f"**{b['title']}** " if b.get("title") else ""
                lines.append(f"{b['ch']}:{b['v']} — {title}{to_md(b['html'])}")
                lines.append("")
            elif t == "p":
                lines += [to_md(b["html"]), ""]
            elif t in ("h3", "h4"):
                lines += [f"### {b['text']}", ""]
            elif t == "list":
                for i, item in enumerate(b["items"], 1):
                    lines.append(f"{i}. {to_md(item)}" if b["ordered"] else f"- {to_md(item)}")
                lines.append("")
            elif t == "table":
                for r, row in enumerate(b["rows"]):
                    lines.append("| " + " | ".join(to_md(c["html"]) for c in row) + " |")
                    if r == 0:
                        lines.append("|" + "---|" * len(row))
                lines.append("")
        (OUT / file_name(sec)).write_text("\n".join(lines).rstrip() + "\n")
    print(f"{len(book['sections'])} files, {count} verses -> content/")

if __name__ == "__main__":
    main()
