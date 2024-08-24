from django.utils.safestring import mark_safe


def get_link_febuxostat_cv_risk():
    """Get the citation in HTML-safe format for the phase 4 follow-up study of CV
    events in febuxostat vs allopurinol users."""

    return mark_safe(
        "White WB, Saag KG, Becker MA, Borer JS, Gorelick PB, Whelton A, Hunt B, Castillo M, Gunawardhana L; CARES \
Investigators. Cardiovascular Safety of Febuxostat or Allopurinol in Patients with Gout. <cite>N Engl J Med</cite>. \
2018 Mar 29;378(13):1200-1210. doi: 10.1056/NEJMoa1710895. Epub 2018 Mar 12. PMID: \
<a target='_next' href='https://pubmed.ncbi.nlm.nih.gov/29527974/'>29527974</a>."
    )


def get_link_gouty_arthropathy():
    return mark_safe("https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8745871/")


def get_citation_gouty_arthropathy():
    """Get the citation for the gouty arthropathy review."""
    return mark_safe(
        "Weaver JS, Vina ER, Munk PL, Klauser AS, Elifritz JM, Taljanovic MS. Gouty Arthropathy: Review of Clinical "
        "Manifestations and Treatment, with Emphasis on Imaging. J Clin Med. 2021 Dec 29;11(1):166. "
        "doi: 10.3390/jcm11010166. PMID: "
        f"<a target='_next' href={get_link_gouty_arthropathy()}>35011907</a>."
    )


def get_link_tophi_gout_education_society():
    return mark_safe("https://gouteducation.org/education/gout-pictures/")


def get_citation_tophi_gout_education_society():
    return mark_safe(
        f"<a target='_blank' href={get_link_tophi_gout_education_society()}>"
        "examples</a> courtesy of the Gout Education Society"
    )
