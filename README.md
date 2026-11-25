# The Guybile

*The Bro Code, rewritten as scripture. Funny on the surface, true underneath.*

The official home of The Guybile is **[theguybile.com](https://theguybile.com)**. This repository holds its book and website source. The 29 chapters and 3 appendices live as plain text in [`content/`](content). Anyone can suggest new verses (see [CONTRIBUTING.md](CONTRIBUTING.md)), and merged changes go live on theguybile.com automatically.

This repository is open for contributions, not for re-hosting. Please don't publish copies of the site elsewhere; send verses here instead.

## The website

- Prebuilt static pages, one per chapter. There is no framework and no web fonts, and each page is about 7 KB over the wire.
- It works on phones, tablets and desktops. Tables turn into cards on small screens, and verse numbers move into the margin on wide ones.
- Three page styles (Paper, Light and Night) and four text sizes. The reader's choice is remembered.
- Tap a verse to copy it or share a link to it. Every verse has its own address, for example `chapter-1.html#v1-5`.
- Search, a verse of the day, and "Continue reading" from where you left off.
- It works offline after the first visit, and it can be installed to the home screen.

## Preview your change locally

Optional. You only need Python 3.9 or newer.

```bash
python3 scripts/build.py
```

```bash
python3 -m http.server 8417 --directory dist
```

Then open http://localhost:8417.

## Files

| Path | What it is |
|---|---|
| `content/*.md` | The book. One file per chapter or appendix. |
| `scripts/build.py` | Turns `content/` into the website in `dist/`. It also keeps the suggestion form's chapter list up to date. |
| `scripts/add_verse.py` | Adds an accepted suggestion to its chapter. The bot runs it. |
| `src/` | Styles, reader script, offline worker and icons. |
| `.github/` | The suggestion form and the build, deploy and accept workflows. |
