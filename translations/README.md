# Translations

The Guybile belongs in every language a brother speaks. Translations live here, one folder per language.

## Offer to translate

Open an issue with the **Translate The Guybile** form: [Translate it](../../../issues/new?template=translation.yml). Pick a language and what thou wilt translate, and the maintainer will reply.

## How a translation is stored

Make a folder named with the [language code](https://en.wikipedia.org/wiki/List_of_ISO_639_language_codes), for example `translations/hi/` for Hindi or `translations/te/` for Telugu. Copy a chapter file from [`content/`](../content) into it with the same file name, and translate the text. Keep the format exactly:

```
---
label: अध्याय 1
title: भाईचारे के नियम
---

1:1 — Verse text in thy language.
```

- Keep the verse numbers (`1:1 —`) unchanged, so every verse still lines up with the original.
- Keep `**bold**`, `*italic*` and `[by Name]` as they are.
- Translate the jokes, not only the words.

## What happens next

The website currently shows English only. Translations merged here will appear on the site once the language switcher is built. Everything is checked by the same automatic build as the English text.

If thou art unsure, translate the Preamble as a sample and open the issue. A small start is a good start.
