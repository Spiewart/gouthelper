# GoutHelper Editorial Tips

## <span id="introduction">Introduction</span>

- We use [Markdown](https://www.markdownguide.org/basic-syntax/) for most of our text. It's nice because it's semantic and easy to edit (like this document).
- We do use a small amount of [HTML](#html) to assign attributes to text. This is because Markdown doesn't have a way to do this.

## <span id="html">HTML</span>

We prefer to use the most minimal amount of HTML possible to preserve readability and semantic meaning. Also, lots of HTML is difficult for non-programmers to understand. We use HTML for the following:

1. Adding a css id: `<span id="myid">text</span>`
2. Adding a css class: `<span class="myclass">text</span>`
3. Superscripting text (like this<sup>1</sup>): `<sup>1</sup>`

## <span id="internal-links">Internal Links</span>

### <span id="same-page-links">Same Page Links</span>

To link to a section on the same page, like [this](#same-page-links), use the following syntax:
`[link-text](#id-of-section)`

### <span id="different-page-links">Different Page Links</span>

To link to a different page on GoutHelper, like [this](/home/), use the following syntax:
`[link-text](/path/to/page/)`

### <span id="different-page-link-ids">Different Page Link IDs</span>

To link to a specific css id on a different page, like [this](/home/#different-page-link-id), use the following syntax:
`[link-text](/path/to/page/#id)`

## <span id="references">References</span>

References should be recorded in numerical order and indicated in the text by a superscript number (xxx) linked to the full reference id (#ref-xxx) at the bottom of the page: `[<sup>xxx</sup>](#ref-xxx)`[<sup>xxx</sup>](#ref-xxx). The reference list should be at the end of the document. There should be a span element without any text inside at the beginning of the reference to mark the id, i.e. `<span id="ref-xxx"></span>reference`.

<span id="ref-xxx"></span>Weasley, Potter, Mugglefood. Fake Reference. Journal of Enchanted Jellies. 2020. PMID: [12345678](https://link.springer.com/article/10.1007/s11882-012-0322-z)

If you add or remove a reference, you need to check all the others to preserve the correct order in the text. References should be formatted however is easiest to grab the citation, but should include at least the first author, title, journal, year, and PMID as possible. The PMID should be a link to the article on PubMed, such as `[23179866](https://link.springer.com/article/10.1007/s11882-012-0322-z)`. Make sure the link works before you commit your changes.
