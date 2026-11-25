"""Add an accepted verse suggestion (a GitHub issue made from the
"Suggest a verse" form) to the right chapter file.

Run by .github/workflows/accept-verse.yml when the maintainer labels an
issue `accepted`. The issue body is untrusted text, so it only ever goes
into a Markdown file (the site builder escapes all HTML) and is read
from an environment variable, never from the command line.

Local use:  ISSUE_BODY="$(cat body.md)" ISSUE_NUMBER=12 python3 scripts/add_verse.py
"""
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
NEW_TOPIC = "A new topic (name it below)"


def fields(body):
    """Parse an issue-form body: '### Heading\\n\\nvalue' sections."""
    out, key = {}, None
    for line in body.replace("\r\n", "\n").split("\n"):
        m = re.match(r"^### (.+)$", line)
        if m:
            key = m.group(1).strip()
            out[key] = []
        elif key:
            out[key].append(line)
    return {k: "\n".join(v).strip() for k, v in out.items()}


def clean(text):
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"^(Guybile\s+)?\d+:\d+\s*[—-]+\s*", "", text)  # drop a ref they typed
    text = text.replace("<", "‹").replace(">", "›")
    if len(text) > 600:
        raise SystemExit("Verse is longer than 600 characters; trim it in the issue first.")
    if not text:
        raise SystemExit("The verse field is empty.")
    return text


def chapter_files():
    found = {}
    for p in CONTENT.glob("*.md"):
        m = re.search(r"^label:\s*Chapter (\d+)\s*$", p.read_text(encoding="utf-8"), re.M)
        if m:
            found[int(m.group(1))] = p
    return found


def main():
    body = os.environ.get("ISSUE_BODY", "")
    issue = os.environ.get("ISSUE_NUMBER", "")
    f = fields(body)
    chapter = f.get("Chapter", "")
    verse = clean(f.get("Your verse", ""))
    credit = f.get("Credit (optional)", "").strip()
    if credit in ("_No response_", "None"):
        credit = ""
    files = chapter_files()

    if chapter.startswith(NEW_TOPIC) or chapter == NEW_TOPIC:
        topic = re.sub(r"\s+", " ", f.get("New topic name", "")).strip()
        if not topic or topic == "_No response_":
            raise SystemExit("New topic chosen but 'New topic name' is empty.")
        num = max(files) + 1
        slug = re.sub(r"[^a-z0-9]+", "-", topic.lower().replace("'", "")).strip("-")[:40]
        title = topic if topic.lower().startswith("the ") else f"The Laws of {topic}"
        path = CONTENT / f"{num:02d}-{slug}.md"
        path.write_text(f"---\nlabel: Chapter {num}\ntitle: {title}\n---\n\n", encoding="utf-8")
    else:
        m = re.match(r"Chapter (\d+)", chapter)
        if not m or int(m.group(1)) not in files:
            raise SystemExit(f"Could not find the chapter: {chapter!r}")
        num, path = int(m.group(1)), files[int(m.group(1))]

    text = path.read_text(encoding="utf-8")
    used = [int(v) for v in re.findall(rf"^{num}:(\d+)\s", text, re.M)]
    nxt = max(used, default=0) + 1
    line = f"{num}:{nxt} — {verse}"
    credit = re.sub(r"[\[\]<>*_`|]", "", credit).strip()[:40]
    if credit:
        line += f" [by {credit}]"
    path.write_text(text.rstrip("\n") + "\n\n" + line + "\n", encoding="utf-8")

    summary = f"Guybile {num}:{nxt} added to {path.name}"
    if credit:
        summary += f" (credit: {credit})"
    print(summary)
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as fh:
            fh.write(f"ref={num}:{nxt}\nfile={path.name}\n")
            safe_credit = re.sub(r"[^\w .@-]", "", credit)[:60]
            fh.write(f"credit={safe_credit}\n")
            fh.write(f"issue={issue}\n")


if __name__ == "__main__":
    sys.exit(main())
