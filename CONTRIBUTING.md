# Adding to The Guybile

The Guybile is never finished. Anyone can suggest a verse, and the maintainer reviews every one before it goes live.

## The easy way: no coding needed

1. Open the site and press **Suggest a verse**. You can also go to **Issues → New issue → Suggest a verse** on GitHub.
2. Pick a chapter, or pick "A new topic" and name it.
3. Write the verse and submit.

You need a free GitHub account. The maintainer will review your verse. If it's accepted, it appears on the site with the next number in its chapter.

## The direct way: edit a chapter

Every chapter is a plain text file in [`content/`](content). Press **Edit on GitHub** at the bottom of any chapter page, or open a file here. Then:

1. Add your verse at the end of the chapter, or where it fits, with the next free number:

   ```
   7:19 — Thou shalt not reply "k" to a paragraph.
   ```

2. Press **Propose changes**. GitHub opens a pull request for you.

The site is rebuilt from these files, and the build checks your change automatically. It fails if two verses share a number, so you'll know before anything breaks.

## How a chapter file looks

```
---
label: Chapter 7
title: The Laws of Women, Love and Respect
---

An optional opening paragraph.

### An optional sub-heading

7:1 — The verse text. **Bold** and *italic* work.
7:2 — **A titled verse.** Text after the bold title.
```

- Add `[by Thy Name]` at the end of a verse to be credited under it and on the Authors page.
- `Guybile 3:2` written inside any text becomes a link to that verse.
- `- item` and `1. item` make lists, and `| a | b |` lines make a table.
- To start a new chapter, add a file named with the next number (for example `30-pets.md`) and use `label: Chapter 30`.

## What makes a good verse

- **Funny on the surface, true underneath.** The best verses start as a joke and end as advice.
- **Scripture voice.** "Thou shalt", "a brother", "blessed is". Keep it to one to three sentences.
- **Kind.** Roast the situation, not a group of people. Nothing hateful, and no real private people by name.
- **Safe.** Health, crisis or money verses point people to real help. They never replace it.

## Vote for the best

Browse the [open suggestions](../../issues?q=is%3Aopen+label%3Averse) and give the good ones a 👍. Sort by "Most reactions" to see the favourites.

## For the maintainer

- **Accept a suggestion:** add the `accepted` label to the issue. A bot opens a pull request that adds the verse with the right number. Polish the wording there if needed, then **Merge**. The site updates in about a minute.
- **Reject a suggestion:** close the issue with a kind word.
- **Pull requests from people:** review the change, then merge. Every pull request is built automatically first.
