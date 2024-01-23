# About Flare Calculator

---

- [Basics](#basics)
- [Likelihood](#likelihood)
- [Prevalence](#prevalence)
- [Interpretation](#interpretation)
- [Diagnostic Rule](#diagnosticrule)

---

## <span id="basics">Basics</span>

The Flare Calculator is meant to help patients and providers estimate how likely it is
that a given Flare's symptoms are from gout. It is NOT a diagnostic tool, but intended to be used
in conjunction with a provider's clinical judgement. It should help reassure providers that
they are on the right track when thinking about gout, prompt them to seek more information
when it is needed, or to consider alternative diagnoses if the symptoms and other supporting
data don't fit.

---

## <span id="likelihood">Likelihood</span>

Likelihood is GoutHelper's estimation of how likely it is that
the Flare reported is due to gout. **This is not a fully evidence-based
or quantiative determination**. The likelihood is based on the evidence-based
[Diagnostic Rule](#diagnosticrule) for gout that GoutHelper expands upon
by gathering additional information that experienced providers would consider when
evaluating a potential gout flare.

The potential [Likelihoods](#likelihoods) are: **Unlikely**</strong>, **Equivocal**,
and **Likely**.

The Likelihoods are derived from the Diagnostic Rule's Prevalences and cross-referenced with additional factors about the Flare that increase or decrease the chances that it is gout. For example, if a Flare were medium prevalence (31.2%) by the Diagnostic Rule, but the patient the Flare was reported as diagnosed by a clinican with joint aspiration and crystal analysis showing monosodium urate, then the likelihood would be **Likely**. Conversely, if the Flare were high prevalence (80.4%) by the Diagnostic Rule, but the Flare was reported as being in a health pre-menopausal woman, then the likelihood would be **Equivocal**.

---

## <span id="prevalence">Prevalence</span>

Prevalence is a quantitative, evidence-based outcome developed with 2 prospective studies from
European medical centers.

The potential [Prevalences](#prevalences) are: **Low** (2.2%), **Medium** (31.2%), and **High** (80.4%).

GoutHelper's opinion of this work is that it is really cool and helpful. There are a few caveats to their use however. First,
these studies only looked at patients who had sudden onset pain in a single joint. Thus, extrapolating this to
patients with pain in more than one joint or pain that came on gradually is not supported by the evidence. Second,
they didn't include other factors into their final model that are very important practical considerations when clinicians evaluate
a patient with gout. This is why GoutHelper gathers additional information about the Flare and integrates
that with the [Diagnostic Rule](#diagnosticrule) to provide a [Likelihood](#likelihood).

---

## <span id="interpretation">Interpretation</span>

#### <span id="likelihoods">**Likelihoods**</span>

- **Unlikely**: gout is not very likely, consider other causes of joint pain
- **Equivocal**: indeterminate for gout, gather more information, consider other causes, and consider referral to a rheumatologist
- **Likely**: gout is very likely, consider treatment for gout

#### <span id="prevalences">**Prevalences**</span>

- **Low**: 2.2% prevalence of gout in a similar population
- **Medium**: 31.2% prevalence of gout in a similar population
- **High**: 80.4% prevalence of gout in a similar population

---

## <span id="diagnosticrule">Diagnostic Rule</span>

The diagnostic rule is based on really cool work from Dr. Janssens et al. in the Netherlands published in 2010[<sup>1</sup>](#ref-1) and 2015[<sup>2</sup>](#ref-2)</a>.

In 2010 Dr. Janssens' group recruited a large Dutch cohort (n=390) with sudden onset arthritis (pain) in a single joint. They used statistical modeling to determine which factors were most predictive of gout and refined their model into a simple diagnostic rule to stratify participants into three groups by prevalence of gout. Each patient had a joint aspiration as part of the study to confirm or refute the diagnosis, as this is the gold-standard procedure to diagnose gout.

The factors that comprised the final simplified diagnostic rule model were weighted according to their importance and are:

- Male sex
- Previous patient-reported arthritis attack
- Symptom onset in 1 day or less<
- Pain in the great toe (1st MTP)
- Hypertension or cardiovascular disease defined as angina, myocardial infarction, congestive heart failure, stroke or transient ischemic attack, or peripheral vascular disease
- Uric acid > 5.88 mg/dL (350 µmol/L)

In 2015 their group then validated their diagnostic rule in a different population of Dutch patients who were being seen in a
rheumatology referral center. These patients were all suspected as having prior gout flares. The positive predictive value
of a score >= 8 was 0.87, meaning gout was highly likely but that there were still alternative but not a complete certainty.
The negative predictive value of a score <=4 was 0.95, meaning gout could be ruled out with a high degree of probability.

---

## <span id="references">References</span>

1. <span id="ref-1"></span> Janssens HJEM, Fransen J, van de Lisdonk EH, van Riel PLCM, van Weel C, Janssen M. A Diagnostic Rule for Acute Gouty Arthritis in Primary Care Without Joint Fluid Analysis. Arch Intern Med. 2010;170(13):1120–1126. [doi:10.1001/archinternmed.2010.196](https://jamanetwork.com/journals/jamainternalmedicine/article-abstract/225738)
2. <span id="ref-2"></span> Laura B. E. Kienhorst, Hein J. E. M. Janssens, Jaap Fransen, Matthijs Janssen, The validation of a diagnostic rule for gout without joint fluid analysis: a prospective study, Rheumatology, Volume 54, Issue 4, April 2015. PMID:[25231179](https://doi.org/10.1093/rheumatology/keu378)
