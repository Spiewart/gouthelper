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
