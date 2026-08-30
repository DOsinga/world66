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
borrows that location's hero image and map position — it has no photo or coordinates of its own.

## Frontmatter

```yaml
---
title: 5 Blogs to Read Before Tbilisi
type: bloglist
score: 8.0
snippet: A Tbilisi native, an Australian who moved there, and a slow-moving archive of
  Georgian village life — the people who have already done the reading
blogs:
  - name: Wander-Lush
    url: https://wander-lush.org/
    author: Emily Lush
    note: The most thorough English-language guides to Georgia anywhere, written by an
      Australian who lived in Tbilisi. Start with her neighbourhood walks, then her
      wine-region itineraries.
---
```

- **`title`** — put the count in it ("5 Blogs to Read Before Tbilisi"). Readers want the length
  before they click.
- **`blogs`** — 5–8 entries, in the order they should be read. `name`, `url` and `note` are all
  required; `author` is optional and only worth adding when the person is the reason to read it.
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

If you can only find four blogs worth the reader's time, ship four and say so in the body text.
Padding a list with SEO listicles is worse than a short list.

## Contacts and outreach

Every blog on every list must have a row in [`tools/blog_outreach.csv`](tools/blog_outreach.csv):

```
city,list_path,blog_name,blog_url,contact_type,contact,emailed
```

`contact_type` is `email` or `form`; `contact` is the address or the contact-page URL. The
`emailed` column is for tracking who has been told they're featured.

Contacts live in that file rather than in the page frontmatter so that addresses aren't rendered
into the published page. The linter's `bloglist_contacts` check fails if a featured blog has no
row, so the two can't drift apart.

## Don't

- Don't add a blog you haven't loaded and read.
- Don't write a note that would fit any blog about that country.
- Don't list a site because it ranks well — that's how you end up with five copies of the same
  listicle.
- Don't add `image:` to a bloglist.
- Don't put a bloglist in a section subdirectory; it goes flat in the location's own folder.
