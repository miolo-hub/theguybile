# The Guybile

*The Bro Code, rewritten as scripture. Funny on the surface, true underneath.*

This repository is the book and the website. The 29 chapters and 3 appendices live as plain text in [`content/`](content). Anyone can suggest new verses (see [CONTRIBUTING.md](CONTRIBUTING.md)), and merged changes go live automatically.

## The website

- Prebuilt static pages, one per chapter. There is no framework and no web fonts, and each page is about 7 KB over the wire.
- It works on phones, tablets and desktops. Tables turn into cards on small screens, and verse numbers move into the margin on wide ones.
- Three page styles (Paper, Light and Night) and four text sizes. The reader's choice is remembered.
- Tap a verse to copy it or share a link to it. Every verse has its own address, for example `chapter-1.html#v1-5`.
- Search, a verse of the day, and "Continue reading" from where you left off.
- It works offline after the first visit, and it can be installed to the home screen.

## Build it locally

You only need Python 3.9 or newer.

```bash
python3 scripts/build.py
```

```bash
python3 -m http.server 8417 --directory dist
```

Then open http://localhost:8417.

## Put it online (one-time setup)

1. Create a **public** repository on GitHub and push this folder to `main`.
2. In the repository, go to **Settings → Pages → Build and deployment** and set **Source** to **GitHub Actions**.
3. In **Settings → Actions → General → Workflow permissions**, tick **Allow GitHub Actions to create and approve pull requests**.
4. In **Issues → Labels**, create two labels: `verse` and `accepted`.
5. Optional: set `site_url` in [`site.json`](site.json) to the final address (for example `https://yourname.github.io/the-guybile`) so link previews look right.

From then on, every merge to `main` updates the site.

## Files

| Path | What it is |
|---|---|
| `content/*.md` | The book. One file per chapter or appendix. |
| `scripts/build.py` | Turns `content/` into the website in `dist/`. It also keeps the suggestion form's chapter list up to date. |
| `scripts/add_verse.py` | Adds an accepted suggestion to its chapter. The bot runs it. |
| `src/` | Styles, reader script, offline worker and icons. |
| `.github/` | The suggestion form and the build, deploy and accept workflows. |
