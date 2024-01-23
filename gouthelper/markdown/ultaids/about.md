# UltAid

---

- [About](#about)
- [Methodology](#methodology)
- [Potential Problems](#potentialproblems)
- [References](#references)

---

## <span id="about">About</span>

UltAid is a decision aid tool that determines the optimal choice of urate-lowering therapy for a patient. It is intended for use in patients with gout who are starting urate-lowering therapy ([ULT](/treatments/about/ult/)), but also provides information about the recommended dose titration. Each UltAid will make a recommendation as well as provide the options for alternative therapies if there are any. If, given a patient's characteristics, there is no clear recommendation, a UltAid will default to recommending the patient see a rheumatologist.

UltAid does not provide information about whether or not urate-lowering therapy is appropriate for a patient. For that, create a [ULT](/ults/create/).

---

## <span id="methodology">Methodology</span>

There are 2 good options and 1 less good option for urate-lowering therapy.

1. Allopurinol is first line.
2. Febuxostat is medically equivalent, but costs more and comes with a few warnings.
3. Probenecid is 3rd line and not used a lot anymore.

UltAids review a patient's information and picks the best one. They are meant to be used by providers and/or patients. They are not meant to replace a provider's judgement.
The patient's age, ethnicity, gender, and medical history are the variables used to make the determination. There are very few patients who can't be figured out in this way, but there are a few exceptions that are not covered by UltAids.

UltAid recommendations are generally based on the 2020 American College of Rheumatology Guidelines
for the Management of Gout[<sup>1</sup>](#ref-1). However, these guidelines do not cover all edge cases and there is tribal (rheumatology tribe) knowledge integrated into UltAids that is not in the guidelines.

---

## <span id="potentialproblems">Potential Problems</span>

1. While rare, some patients are not able to tolerate allopurinol or febuxostat. Ironically, those patients are most likely to have advanced chronic kidney disease (CKD) making probenecid a poor choice. In these cases, a rheumatologist and/or pharmacist can somtimes de-sensitive an individual to allopurinol or febuxostat. This should be done under close supervision by a human.

2. Febuxostat was associated with an increased risk cardiovascular death and death from any cause, relative to allopurinol, in randomized controlled trials[<sup>2</sup>](#ref-2). It is not uncommon for an individual with a history of cardiovascular disease to require febuxostat because allopurinol is off the table for one reason or another (lab abnormalities, rash, other adverse reaction, etc.) GoutHelper is of the opinion that patients should be aware of the potential increased risk of cardiovascular events associated with febuxostat when making a decision about starting urate-lowering therapy with febuxostat. This association has also been debated [<sup>3</sup>](#ref-3).

---

## <span id="references">References</span>

1. <span id="ref-1"></span>FitzGerald JD, Dalbeth N, Mikuls T, Brignardello-Petersen R, Guyatt G, Abeles AM, Gelber AC, Harrold LR, Khanna D, King C, Levy G, Libbey C, Mount D, Pillinger MH, Rosenthal A, Singh JA, Sims JE, Smith BJ, Wenger NS, Bae SS, Danve A, Khanna PP, Kim SC, Lenert A, Poon S, Qasim A, Sehra ST, Sharma TSK, Toprover M, Turgunbaev M, Zeng L, Zhang MA, Turner AS, Neogi T. 2020 American College of Rheumatology Guideline for the Management of Gout. Arthritis Care Res (Hoboken). 2020 Jun;72(6):744-760. doi: 10.1002/acr.24180. Epub 2020 May 11. Erratum in: Arthritis Care Res (Hoboken). 2020 Aug;72(8):1187. Erratum in: Arthritis Care Res (Hoboken). 2021 Mar;73(3):458. PMID: [32391934](https://pubmed.ncbi.nlm.nih.gov/32391934/).

2. <span id="ref-2"></span>White, William B., et al. "Cardiovascular safety of febuxostat or allopurinol in patients with gout." New England Journal of Medicine 378.13 (2018): 1200-1210. PMID: [29527974](https://doi.org/10.1056/nejmoa1710895)

3. <span id="ref-3"></span>Mackenzie IS, Ford I, Nuki G, Hallas J, Hawkey CJ, Webster J, Ralston SH, Walters M, Robertson M, De Caterina R, Findlay E, Perez-Ruiz F, McMurray JJV, MacDonald TM; FAST Study Group. Long-term cardiovascular safety of febuxostat compared with allopurinol in patients with gout (FAST): a multicentre, prospective, randomised, open-label, non-inferiority trial. Lancet. 2020 Nov 28;396(10264):1745-1757. doi: 10.1016/S0140-6736(20)32234-0. Epub 2020 Nov 9. PMID: [33181081](<https://doi.org/10.1016/s0140-6736(20)32234-0>).
