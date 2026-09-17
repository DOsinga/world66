# Bloglists

A bloglist is a `type: bloglist` page: a short, curated set of **outside blogs** worth reading
about one place. It's the only content type on the site that points off it. Everything else —
POIs, sections, locations, lists — names pages in `content/`; a bloglist names other people's
websites, because for a lot of destinations the best writing that exists is somebody's blog.

It answers a question a guidebook can't: *who is actually writing well about this place right
now?*

A bloglist lives flat in the directory of the place it belongs to, alongside the POIs:

```
content/europe/georgia/tbilisi/blogs_to_read_before_tbilisi.md
```

The location page then shows a "Blogs Worth Reading" callout linking to it, and the bloglist
borrows that location's hero image — it has no photo of its own. It renders no sidebar and no
map: nothing on a page of outbound links sits on one, so the text takes the full width.

## Frontmatter

```yaml
---
title: 5 Blogs to Read Before Tbilisi
type: bloglist
score: 8.0
snippet: A Tbilisi native, an Australian who moved there, and a slow-moving archive of
  Georgian village life — the people who have already done the reading
blogs:
  - name: The 25 Best Things to Do in Tbilisi, Georgia
    url: https://wander-lush.org/things-to-do-in-tbilisi-georgia/
    blog: Wander-Lush
    author: Emily Lush
    note: The most thorough English-language guide to the city anywhere, written by an
      Australian who lived there. Every walk has a map and an honest note on how long it
      really takes.
---
```

- **`title`** — put the count in it ("5 Blogs to Read Before Tbilisi"). Readers want the length
  before they click.
- **`blogs`** — 5–8 entries, in the order they should be read. `name`, `url` and `note` are all
  required; `author` is optional and only worth adding when the person is the reason to read it.
- **`url`** — link to **the piece about this place**, not to the site's front door. A reader who
  clicks should land on the writing you are recommending, not on whatever the blog published last
  week.
- **`name`** — the **title of that page**, taken from the page itself. Normalise SEO shouting
  ("QUÉ VER EN SAN PEDRO" → "Qué ver en San Pedro") and drop the trailing site name that many
  `<title>` tags carry, but do not invent a title of your own. The card shows the domain
  underneath, so the blog is still identifiable.
- **`blog`** — the name of the publication, now that `name` is an article title. Used when a POI
  credits the list (below); add it to every entry.
- **`note`** — one or two sentences on *what this blog gives you that the others don't*. Name the
  specific thing: the post to start with, the beat they own, the thing they're honest about.
  "A great travel blog about Georgia" is not a note.
- **`score`** — the usual 1.0–10.0 scale, used to order multiple bloglists on a location page.
- No `image` — it borrows the parent location's.
- Body text: two short paragraphs in the usual voice (see [STYLE.md](STYLE.md)). The first says
  what this city's coverage is actually like; the second names the throughline.

## The bar for including a blog

**It has to be alive and it has to be real.** Before a blog goes on a list:

1. **Load the URL and read the site.** A 200 response is not enough — parked domains and expired
   sites return 200 all the time. One of the candidates for the George Town list was a Namecheap
   parking page.
2. **Check it actually covers the place.** A well-known Malaysia blog with no Penang section does
   not belong on a George Town list. Say so in the note if it's country-wide rather than local.
3. **Write the note from what the blog says about itself**, not from what you assume. If you can't
   establish who writes it or what it covers, leave it off.
4. **Prefer people over publishers.** Independent blogs, small local magazines and one-person
   sites are the point. Tour-operator content marketing is not — if a genuinely good piece is on
   an operator's blog, say plainly in the note that that's what it is.
5. **No affiliate deals, no exchanges.** Blogs are listed because they're good. Nobody pays and
   nobody is asked for anything.
6. **One list per blog.** A blog that covers a whole region belongs on the one list where it is
   strongest, not on all of them. Emily Lush writes about Albania and Armenia as well as Georgia,
   but she lived in Tbilisi, so Wander-Lush is a Tbilisi entry and nowhere else. Repeating a blog
   makes every list it appears on look like the same list.

If you can only find four blogs worth the reader's time, ship four and say so in the body text.
Padding a list with SEO listicles is worse than a short list.

## Crediting a bloglist from a POI

When a bloglist is where a POI came from, credit it with a **tag**: add the bloglist's slug to the
POI's `tags:`. The tag renders as a link carrying the bloglist's title, so the POI points at the
list without an outbound link in its body and without a sentence of throat-clearing on the section
page.

```yaml
# content/southamerica/chile/sanpedrodeatacama/termas_de_puritama.md
tags:
  - things_to_do
  - sight
  - blogs_for_san_pedro_and_the_atacama
```

The chip reads **"Listed by Wander-Lush"** and links straight at that entry, highlighting it on
arrival. Which blog gets named is worked out rather than written down twice: whichever entry's
`url` also appears in the POI's `sources:` is the one that listed it. So record the source as you
normally would and the credit follows —

```yaml
sources:
  - https://wander-lush.org/things-to-do-in-tbilisi-georgia/
```

If no source matches, the chip falls back to the list's own title.

The tag only resolves for a POI in the **same directory** as the bloglist — anywhere else it
renders as a dead plain chip, so leave it off and let `sources:` carry the provenance instead.

## Contacts and outreach

Every blog on every list must have a row in [`tools/blog_outreach.csv`](tools/blog_outreach.csv):

```
city,list_path,blog_name,blog_url,contact_type,contact,emailed
```

`contact_type` is `email` or `form`; `contact` is the address or the contact-page URL. The
`emailed` column is for tracking who has been told they're featured. `blog_url` must match the
page's `url:` exactly — that is the key the check joins on — while `blog_name` stays the name of
the blog rather than the article title, because that is what you write the email to.

Contacts live in that file rather than in the page frontmatter so that addresses aren't rendered
into the published page. The linter's `bloglist_contacts` check fails if a featured blog has no
row, so the two can't drift apart.

## Don't

- Don't add a blog you haven't loaded and read.
- Don't write a note that would fit any blog about that country.
- Don't list a site because it ranks well — that's how you end up with five copies of the same
  listicle.
- Don't add `image:` or coordinates to a bloglist.
- Don't link an entry to a site's home page when a specific piece is what you mean.
- Don't feature the same blog on two lists.
- Don't forget the count in the title when entries are added or removed.
- Don't put a bloglist in a section subdirectory; it goes flat in the location's own folder.
