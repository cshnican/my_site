# Editing the preview

These files are the text of the site. The previous Hugo site is in `old_site/`.

After you edit, rebuild the pages:

```
python3 build.py
```

Run that from the project folder.

English lives in `content/en/`. Greek lives in `content/el/`. Each folder uses the same files.

| File | What it controls |
| --- | --- |
| `site.md` | Your name, position, photo, navigation, footer, and the links under the bio |
| `home.md` | The bio, interests, education, jobs, the note outside the lab, and media coverage |
| `research.md` | The research page. English only, until you add `content/el/research.md` and a Research link in `content/el/site.md` |
| `publications.md` | Every paper. A paper with `selected:` also appears under Selected papers on the homepage |
| `gallery.md` | The gallery page. `album: stars` shows every photo in `assets/media/albums/stars` |

Greek paper titles stay shared with `content/en/publications.md` until you add `content/el/publications.md`. Photo, CV, and PDF paths are written from the site root, such as `old_site/content/en/authors/admin/avatar.jpg`. The builder adds the extra `../` for pages in `el/`.

The language menu is the button labeled with the current language. English Research’s Greek choice opens the Greek homepage, because that page does not exist in Greek yet.

A new paper looks like this:

```
## 2026
title: Title of the paper
authors: **Chen** & Someone
venue: Name of the journal
pdf: https://example.com/paper.pdf
selected: efficiency
```

`selected` is optional. Leave it off and the paper stays on the Publications page only. Words after `selected:` are the homepage filters. The ones in use now are `efficiency`, `society`, and `comprehension`.

In gallery sections, `album: city` points at a folder of photos. A line like `IMG_2999.jpg: The Milky Way` sets that photo’s description. Add a place after a bar and it appears when someone hovers the photo and under the full-size preview: `IMG_2999.jpg: The Milky Way | Bar Harbor`. A place by itself is fine: `IMG_3137.jpg: | Cape Cod`. Photos without a line use the section heading.

A media item in `home.md` is a year, a linked title, and the outlet:

```
### 2026
[Title of the article](https://example.com/story)
Name of the outlet
```
