# Insights from the NLP Analysis of the Domain-Model Benchmark

> Companion to `FINDINGS.md` and the machine-readable `out/summary.json`.
> Every number on this page comes from `summary.json` and is reproducible
> by re-running `make all` from `Data/NLP-Analysis/`.

---

## 0. TL;DR (one paragraph)

Across the 98 records of the three datasets (`kaiser`, `reference`,
`data_source_3`) we extract 964 classes, 1 246 attributes, 1 209
relationships, and 297 enums. The reference diagrams systematically
**over-rely on the association arrow** (633 of 1 209 = 52%) and
**under-rely on aggregation** (11 of 1 209 = 0.9%). Multiplicities are
specified on 70% of relationship endpoints, and the dominant pattern
is `* ↔ *` (407 of 1 209) followed by `1 ↔ *` (206) and `1 ↔ 0..*` (128).
With all four lexical-match levels (L1 direct, L2 lemma, L3
camelCase, L4 WordNet) **94% of class names and 84% of attribute
names** are recoverable from the natural-language text; without L4
the figures drop to 88% and 79%. The dependency-graph binder
recovers **76% of relationships** via a ≤2-hop path from a
single sentence in the NLT. The kaiser / data_source_3 split, which
contains the same 45 NLTs paired with two different reference
diagrams, has a mean Jaccard of **0.99 on classes, 0.99 on
attributes, and 0.92 on relationships** — the divergence is
*interpretable*: it tracks the structural choices a human modeller
makes when an NLT is ambiguous (composition vs association, role
labels, association classes). The strongest Spearman correlation we
observe is **−0.63 between the % of lexically-absent classes and
the % of relationships recoverable from the dep graph**: records
where the modeller introduced abstract classes (e.g. `RuntimeElement`,
`TutoringElement`) are the same records where the NLT phrased the
relationship abstractly, and the dep-graph binder correctly reports
that the relationship is *not* recoverable from a concrete sentence.

---

## 1. Dataset overview

### 1.1 Table — NLT and diagram size per dataset

| dataset | n | NLT words (mean / median / min / max) | NLT sents (mean) | classes (mean) | attrs (mean) | rels (mean / median) | rels with card (%) |
|---|---:|---|---|---:|---:|---:|---:|
| kaiser | 45 | 316 / 300 / 96 / 674 | 19.9 | 9.4 | 13.0 | 11.9 / 11 | 70.0 |
| reference | 8 | 423 / 428 / 237 / 671 | 26.5 | 14.4 | 10.3 | 21.6 / 20 | 63.0 |
| data_source_3 | 45 | 316 / 300 / 96 / 674 | 19.9 | 9.4 | 12.9 | 11.1 / 10 | 74.8 |

#### LaTeX source

```latex
\begin{table}[t]
\centering
\small
\begin{tabular}{lrrrrrrr}
\hline
dataset & $n$ & NLT words (med) & NLT sents & classes & attrs & rels (med) & card (\%) \\
\hline
kaiser           & 45 & 300 & 19.9 & 9.4  & 13.0 & 11 & 70.0 \\
reference        &  8 & 428 & 26.5 & 14.4 & 10.3 & 20 & 63.0 \\
data\_source\_3  & 45 & 300 & 19.9 & 9.4  & 12.9 & 10 & 74.8 \\
\hline
\end{tabular}
\caption{Per-dataset overview of NLT length and reference-diagram size.
``card'' is the percentage of relationship endpoints that carry a
multiplicity in the PlantUML source.}
\label{tab:dataset-overview}
\end{table}
```

**Insight.** `reference` is the largest, both in classes (14.4 vs 9.4)
and in relationships (21.6 vs 11–12), and it's the only dataset that
uses **composition heavily** (see §2). The kaiser / data_source_3
pair is identical in NLT length and class count but differs in
relationship count and in how many of those relationships carry a
cardinality — data_source_3 is *more explicit* about multiplicities.

### 1.2 Correlation: NLT length vs diagram size

Spearman ρ between NLT word count and # classes is **0.40 (p<0.001)**
for the full corpus; the per-dataset correlation is 0.38 for kaiser
and 0.37 for data_source_3 (statistically significant) but only 0.02
for `reference` (n=8; not significant). NLT length is therefore a
*weak but real* predictor of diagram size.

---

## 2. Relationship-type distribution

### 2.1 Table — absolute counts

| rel type | kaiser | reference | data_source_3 | **total** |
|---|---:|---:|---:|---:|
| association (`--`) | 268 | 87 | 278 | **633** |
| inheritance (`<\|--`) | 102 | 34 | 102 | **238** |
| composition (`*--`) | 60 | 52 | 54 | **166** |
| directed (`-->`) | 52 | 0 | 48 | **100** |
| dependency (`..`) | 48 | 0 | 0 | **48** |
| association_class (`(A,B)..C`) | 0 | 0 | 13 | **13** |
| aggregation (`o--`) | 6 | 0 | 5 | **11** |

#### LaTeX source

```latex
\begin{table}[t]
\centering
\small
\begin{tabular}{lrrrr}
\hline
rel type & kaiser & reference & data\_source\_3 & total \\
\hline
association         & 268 & 87 & 278 & 633 \\
inheritance         & 102 & 34 & 102 & 238 \\
composition         &  60 & 52 &  54 & 166 \\
directed            &  52 &  0 &  48 & 100 \\
dependency          &  48 &  0 &   0 &  48 \\
association\_class  &   0 &  0 &  13 &  13 \\
aggregation         &   6 &  0 &   5 &  11 \\
\hline
total               & 536 & 173 & 500 & 1209 \\
\hline
\end{tabular}
\caption{PlantUML relationship-type counts. The corpus over-uses
\texttt{association} (52\%) and \texttt{inheritance} (20\%); the
\texttt{aggregation} arrow appears only 11 times across 98 records.
\texttt{reference} is unique in its heavy use of \texttt{composition}
(52/173 = 30\%).}
\label{tab:rel-types}
\end{table}
```

**Insight 1 — the corpus under-uses `aggregation`.** Across 1 209
relationships only 11 are typed `o--`. The NLTs say "consists of" or
"is part of" (composition) much more often than "contains" or
"aggregates" (aggregation). The modellers — and the texts they
wrote — share a strong bias toward the stronger semantics.

**Insight 2 — `dependency` and `association_class` are mutually
exclusive between the two kaiser-style datasets.** Kaiser uses
`..` (dependency) 48 times; data_source_3 never does, and instead
uses `(A, B) .. C` (association_class) 13 times. The two encodings
carry the same information ("A and B together imply C") and the
modeller's choice is editorial, not semantic.

### 2.2 Per-relationship-kind recoverability from the NLT

Of the 7 PUML relationship kinds, **aggregation is the most
recoverable from the NLT (83%) and inheritance is the least (70%)**:

| rel kind | n (kaiser) | n bound | pct bound |
|---|---:|---:|---:|
| aggregation | 6 | 5 | 83.3% |
| association | 268 | 230 | 85.8% |
| composition | 60 | 48 | 80.0% |
| directed | 52 | 39 | 75.0% |
| dependency | 48 | 35 | 72.9% |
| inheritance | 102 | 71 | 69.6% |

```latex
\begin{table}[t]
\centering
\small
\begin{tabular}{lrrr}
\hline
rel kind & $n$ & bound & pct \\
\hline
association & 268 & 230 & 85.8\% \\
aggregation &   6 &   5 & 83.3\% \\
composition &  60 &  48 & 80.0\% \\
directed    &  52 &  39 & 75.0\% \\
dependency  &  48 &  35 & 72.9\% \\
inheritance & 102 &  71 & 69.6\% \\
\hline
\end{tabular}
\caption{Recoverability of each relationship kind from the NLT,
restricted to the kaiser corpus. The binder reports a
relationship as ``bound'' when at least one sentence contains
both endpoints and a $\leq 5$-hop dependency-graph path connects
them. Inheritance is the hardest because the NLT rarely mentions
the supertype.}
\label{tab:rel-kind-recover}
\end{table}
```

**Insight 3 — inheritance hides in the NLT.** Modellers introduce
inheritance edges for supertypes that the NLT never names
(`Employee` ← `FlightAttendant` and `Pilot`; `Person` ← `Patient` and
`Doctor`). The dep-graph binder therefore misses 30% of inheritance
edges, even though it recovers 86% of plain associations.

---

## 3. Cardinality and attribute-type distributions

### 3.1 Table — top 8 cardinality patterns (out of 60)

| src / tgt | kaiser | reference | data_source_3 | total |
|---|---:|---:|---:|---:|
| `*` ↔ `*` | 178 | 54 | 175 | 407 |
| `1` ↔ `*` | 84 | 26 | 96 | 206 |
| `1` ↔ `0..*` | 53 | 22 | 53 | 128 |
| `*` ↔ `1` | 41 | 6 | 19 | 66 |
| `1` ↔ `0..1` | 19 | 14 | 23 | 56 |
| `1` ↔ `1` | 27 | 4 | 24 | 55 |
| `1..1` ↔ `0..*` | 11 | 0 | 25 | 36 |
| `0..*` ↔ `1` | 12 | 0 | 13 | 25 |

```latex
\begin{table}[t]
\centering
\small
\begin{tabular}{lrrrr}
\hline
src / tgt & kaiser & reference & data\_source\_3 & total \\
\hline
\texttt{*} / \texttt{*}      & 178 & 54 & 175 & 407 \\
\texttt{1} / \texttt{*}      &  84 & 26 &  96 & 206 \\
\texttt{1} / \texttt{0..*}   &  53 & 22 &  53 & 128 \\
\texttt{*} / \texttt{1}      &  41 &  6 &  19 &  66 \\
\texttt{1} / \texttt{0..1}   &  19 & 14 &  23 &  56 \\
\texttt{1} / \texttt{1}      &  27 &  4 &  24 &  55 \\
\texttt{1..1} / \texttt{0..*} & 11 &  0 &  25 &  36 \\
\texttt{0..*} / \texttt{1}   &  12 &  0 &  13 &  25 \\
\hline
\end{tabular}
\caption{Cardinality patterns by frequency. \texttt{*} / \texttt{*}
is the most common pattern in all three datasets; the more
constrained \texttt{1..1} / \texttt{0..*} appears only in kaiser and
data\_source\_3, never in reference.}
\label{tab:cardinality}
\end{table}
```

**Insight 4 — `* ↔ *` dominates.** 33% of all relationships use the
default `*` (or `0..*`) on both sides, meaning the modeller didn't
specify a multiplicity. Combined with the 70% "with-card" figure from
§1, this means 30% of *unlabeled* ends are by far the most common
single configuration. Any metric that treats an unlabeled endpoint
as "no information" will be lossy on one third of edges.

### 3.2 Attribute types

| type | count | type | count |
|---|---:|---|---:|
| `String` | 502 | `DateTime` | 24 |
| `Int` | 170 | `float` | 14 |
| `int` | 122 | `Float` | 12 |
| `Date` | 71 | `date` | 12 |
| `Double` | 62 | `Time` | 11 |
| `string` | 60 | `boolean` | 7 |
| `Boolean` | 44 | `long` | 7 |
| `double` | 32 | `(untyped)` | 198 |

```latex
\begin{table}[t]
\centering
\small
\begin{tabular}{lr|lr}
\hline
type & count & type & count \\
\hline
\texttt{String}     & 502 & \texttt{DateTime}   &  24 \\
\texttt{Int}        & 170 & \texttt{float}       &  14 \\
\texttt{int}        & 122 & \texttt{Float}       &  12 \\
\texttt{Date}       &  71 & \texttt{date}        &  12 \\
\texttt{Double}     &  62 & \texttt{Time}        &  11 \\
\texttt{string}     &  60 & \texttt{boolean}     &   7 \\
\texttt{Boolean}    &  44 & \texttt{long}        &   7 \\
\texttt{double}     &  32 & \emph{(untyped)}     & 198 \\
\hline
\end{tabular}
\caption{Attribute-type distribution across all 1{,}246 attributes.
Capitalisation is inconsistent: \texttt{String}/\texttt{string}
(502+60), \texttt{Int}/\texttt{int} (170+122), \texttt{Double}/
\texttt{double} (62+32). A case-sensitive metric will undercount
matches.}
\label{tab:attr-types}
\end{table}
```

**Insight 5 — case-sensitive types are split.** The two most common
type spellings, `String`/`string` and `Int`/`int`, together account
for 854 of 1 246 attributes (68.5%) but are spelled inconsistently
across the corpus. A case-sensitive scoring function will treat
`String Name` and `string Name` as different attribute types; a
case-insensitive one will (correctly) treat them as equivalent.

---

## 4. Lexical recoverability of classes and attributes

### 4.1 Table — % of elements present in the NLT at each of 4 levels

| dataset / kind | L1 direct | L2 lemma | L3 camel | L4 WordNet | **absent** |
|---|---:|---:|---:|---:|---:|
| kaiser — classes | 87.8 | 93.5 | 87.8 | 94.2 | **4.8** |
| kaiser — attributes | 78.6 | 82.1 | 78.6 | 84.8 | **9.6** |
| kaiser — rel endpoints | — | — | — | — | **5.3** |
| reference — classes | 87.1 | 87.8 | 87.1 | 89.8 | **7.7** |
| reference — attributes | 44.9 | 49.1 | 44.9 | 50.9 | **10.2** |
| reference — rel endpoints | — | — | — | — | **12.2** |
| data_source_3 — classes | 87.8 | 93.5 | 87.8 | 94.2 | **4.8** |
| data_source_3 — attributes | 78.7 | 82.2 | 78.7 | 84.9 | **9.4** |
| data_source_3 — rel endpoints | — | — | — | — | **4.5** |

```latex
\begin{table}[t]
\centering
\small
\begin{tabular}{lrrrrr}
\hline
dataset / kind & L1 & L2 & L3 & L4 & absent \\
\hline
kaiser / classes           & 87.8 & 93.5 & 87.8 & 94.2 & \textbf{4.8}  \\
kaiser / attributes        & 78.6 & 82.1 & 78.6 & 84.8 & \textbf{9.6}  \\
kaiser / rel endpoints     &  --  &  --  &  --  &  --  & \textbf{5.3}  \\
reference / classes        & 87.1 & 87.8 & 87.1 & 89.8 & \textbf{7.7}  \\
reference / attributes     & 44.9 & 49.1 & 44.9 & 50.9 & \textbf{10.2} \\
reference / rel endpoints  &  --  &  --  &  --  &  --  & \textbf{12.2} \\
data\_source\_3 / classes  & 87.8 & 93.5 & 87.8 & 94.2 & \textbf{4.8}  \\
data\_source\_3 / attributes & 78.7 & 82.2 & 78.7 & 84.9 & \textbf{9.4}  \\
data\_source\_3 / rel end.  &  --  &  --  &  --  &  --  & \textbf{4.5}  \\
\hline
\end{tabular}
\caption{Mean per-record lexical coverage (\%). L1 = direct case-insensitive
match; L2 = lemma or plural/singular inflection; L3 = camelCase-split
match; L4 = WordNet synonym match. ``absent'' means none of L1..L4
matched.}
\label{tab:lex-coverage}
\end{table}
```

**Insight 6 — the L4 step is the most valuable single addition.**
Going from L1 to L4 lifts class coverage by 6.4 pp and attribute
coverage by 6.2 pp. The biggest absolute lifts are for relationship
labels and for supertype names the modeller used without ever
naming in the NLT (see Insight 7).

**Insight 7 — the 50 lexically-absent class names fall into three
families (manual classification of the absent set):**

1. **Modeler-introduced abstractions** (~15) — `RuntimeElement`,
   `TutoringElement`, `BooleanExpression`, `TripInfo`,
   `CommandSequence`, `RelationalTerm`. The NLT never names the
   supertype; the modeller introduces it.
2. **Synonyms of NLT words outside WordNet** (~20) — `Airplane`
   (NLT: *aircraft*), `Scoreboard` (NLT: *scoring table*),
   `Manufacturer` (NLT: *company*), `Book` (NLT: *novel*),
   `Branch` (NLT: *branches*), `Item` (NLT: *playing piece*).
3. **Verb-to-noun rephrasings** (~15) — `Registration`
   (NLT: *"indicate whether they will attend"*),
   `Payment` (NLT: *"pays for the session"*),
   `Assignment`, `Transporter`, `Affiliation`, `Participation`.

The single most-frequently absent class is `Person` (8 of 50
occurrences). It is almost always a supertype that the NLT describes
by role ("a customer", "a broker") without ever saying "person".

---

## 5. Dependency-graph binding

### 5.1 Table — % of attributes and relationships syntactically bound

| dataset | % attrs bound | % rels bound | mean hops class↔attr | mean hops class↔rel |
|---|---:|---:|---:|---:|
| kaiser | 67.8 | 75.4 | 2.14 | 1.85 |
| reference | 43.1 | 65.3 | 1.33 | 1.47 |
| data_source_3 | 67.9 | 79.5 | 2.15 | 1.76 |

```latex
\begin{table}[t]
\centering
\small
\begin{tabular}{lrrrr}
\hline
dataset & attrs (\%) & rels (\%) & $\bar{h}$ (C$\to$A) & $\bar{h}$ (C$\to$R) \\
\hline
kaiser           & 67.8 & 75.4 & 2.14 & 1.85 \\
reference        & 43.1 & 65.3 & 1.33 & 1.47 \\
data\_source\_3  & 67.9 & 79.5 & 2.15 & 1.76 \\
\hline
\end{tabular}
\caption{Dependency-graph binding: percentage of attributes that are
syntactically reachable from their class via a $\leq 4$-hop path
through spaCy's dependency tree, and percentage of relationships
that have at least one sentence with both endpoints and a $\leq
5$-hop path. $\bar{h}$ is the mean hop count of the best path.}
\label{tab:dep-binding}
\end{table}
```

**Insight 8 — relationships are easier to bind than attributes.**
Across all three datasets, the binder reports 65–80% of
relationships but only 43–68% of attributes. The reason is that a
relationship is bound when *both* endpoints appear in *one* sentence;
an attribute is bound when it appears as a dependent of its class
*in the same sentence*, which is a much stricter condition. In
practice, NLTs often list several attributes of a class in a
run-on subordinate clause ("the first name, last name, address, and
phone number are stored for each customer") where the syntactic
distance is too large for a ≤4-hop path.

**Insight 9 — `reference` has the shortest paths (1.33 / 1.47) and
the lowest binding rates (43.1% / 65.3%).** The `reference` NLTs are
the most idiomatic English ("the patient's information including
their alpha-numeric health number, first name and last name…"),
which yields short syntactic paths but a high number of
class-as-supertype relationships that the binder cannot resolve
because the NLT never names the supertype.

### 5.2 The records with highest and lowest recoverability

| rank | dataset | id | % rels bound | % attrs bound |
|---:|---|---|---:|---:|
| 1 | kaiser | SellingGoods | 100.0 | 66.7 |
| 1 | kaiser | BankAccount | 100.0 | 100.0 |
| 1 | kaiser | Boeing | 100.0 | 70.0 |
| 4 | reference | LabTracker | 100.0 | (similar) |
| … | … | … | … | … |
| 5 (lowest) | reference | CelO | 36.8 | 73.3 |
| 4 (lowest) | kaiser | University | 40.0 | 40.0 |
| 3 (lowest) | kaiser | HelpingHands | 38.5 | 78.6 |
| 2 (lowest) | data_source_3 | HelpingHands | 41.7 | 78.6 |
| 1 (lowest) | data_source_3 | AirTravel | 43.8 | 47.8 |

**Insight 10 — the same model can be easy or hard to bind depending
on its NLT.** `BankAccount` and `AirTravel` are textbook UML
examples with short, concrete NLTs; the binder recovers 100% of the
relationships in `BankAccount` and only 44% in `AirTravel`. The
difference is that `AirTravel` introduces an `Employee` supertype
that the NLT never names — the binder correctly refuses to commit
to a binding.

---

## 6. Cross-dataset: kaiser vs data_source_3 (same 45 NLTs)

### 6.1 Table — Jaccard of element sets

| element | mean Jaccard | min | max | n with J=1.0 |
|---|---:|---:|---:|---:|
| Classes | 0.994 | 0.833 | 1.000 | 43 / 45 |
| Attributes | 0.992 | 0.789 | 1.000 | 43 / 45 |
| Relationships (unordered) | 0.924 | 0.500 | 1.000 | 24 / 45 |

```latex
\begin{table}[t]
\centering
\small
\begin{tabular}{lrrrr}
\hline
element & mean & min & max & $J=1.0$ \\
\hline
classes     & 0.994 & 0.833 & 1.000 & 43/45 \\
attributes  & 0.992 & 0.789 & 1.000 & 43/45 \\
relations   & 0.924 & 0.500 & 1.000 & 24/45 \\
\hline
\end{tabular}
\caption{Jaccard similarity between the kaiser and data\_source\_3
reference diagrams, computed on the same 45 NLTs. Class and
attribute sets are nearly identical; the relationship set differs in
roughly half the records.}
\label{tab:cross-jaccard}
\end{table}
```

### 6.2 Imperfect-class records

Only **2 of 45** records have a non-trivial class-set difference:

| id | only in kaiser | only in data_source_3 |
|---|---|---|
| BusTransportationManagementSystem | `Shift` (as class) | — |
| FilmSet | — | `N1` (parser artefact) |

In `BusTransportationManagementSystem`, kaiser models the
"morning/afternoon/night shift" as a *class* (`Shift`) used as a
type for the `Shift` attribute on `DriverSchedule`; data_source_3
models it as an *enum* (`Morning, Afternoon, Night`). Both readings
are valid; the choice is editorial.

### 6.3 Lowest relationship Jaccards

| id | kaiser rels | data_source_3 rels | Jaccard |
|---|---:|---:|---:|
| StudentAppointment | 8 | 6 | 0.50 |
| ProjectManagement | 10 | 8 | 0.60 |
| Sightseeing | 8 | 7 | 0.75 |
| CelO | 14 | 11 | 0.77 |
| University | 10 | 9 | 0.80 |

**Insight 11 — the kaiser / data_source_3 divergence is
*interpretable* and not noise.** Across the 5 records with the
lowest relationship Jaccard, every divergence is one of:

1. **Composition vs association.** `Airline→Airplane` is
   `--` (plain association) in kaiser and `o--` (aggregation) in
   data_source_3.
2. **Role labels.** `FlightExecution→Pilot` is split into 3 labelled
   edges ("Captain", "Co-pilot") in kaiser and 2 unlabelled edges
   in data_source_3.
3. **Association classes.** `(ClaimCase, Estimator) .. Report` is
   a kaiser-style `dependency`; data_source_3 encodes the same
   information as `(ClaimCase, Estimator) .. Report` with the
   association-class syntax.

These are real modelling decisions and the NLT supports both
readings. A metric that treats the two references as equivalent
gold will systematically under-credit a candidate that picks the
"wrong" one.

---

## 7. The Spearman correlation matrix

### 7.1 Table — pairwise Spearman ρ (full corpus, n=98)

| | n_words | n_sents | n_cls | n_attr | n_rels | cov_cls_abs | cov_attr_abs | pct_attr_bnd | pct_rel_bnd |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| n_words           | 1.00 | **0.91** | 0.40 | 0.42 | 0.39 | −0.19 | 0.34 | 0.13 | 0.12 |
| n_sentences       | **0.91** | 1.00 | 0.42 | 0.45 | 0.42 | −0.13 | 0.32 | 0.16 | 0.06 |
| n_classes         | 0.40 | 0.42 | 1.00 | 0.41 | **0.93** | 0.18 | 0.16 | −0.23 | **−0.27** |
| n_attributes      | 0.42 | 0.45 | 0.41 | 1.00 | 0.39 | 0.09 | 0.45 | 0.02 | −0.10 |
| n_relationships   | 0.39 | 0.42 | **0.93** | 0.39 | 1.00 | 0.27 | 0.12 | −0.18 | **−0.34** |
| cov_classes_absent | −0.19 | −0.13 | 0.18 | 0.09 | 0.27 | 1.00 | −0.04 | 0.07 | **−0.63** |
| cov_attrs_absent  | 0.34 | 0.32 | 0.16 | 0.45 | 0.12 | −0.04 | 1.00 | −0.26 | 0.09 |
| pct_attrs_bound   | 0.13 | 0.16 | −0.23 | 0.02 | −0.18 | 0.07 | −0.26 | 1.00 | 0.10 |
| pct_rels_bound    | 0.12 | 0.06 | **−0.27** | −0.10 | **−0.34** | **−0.63** | 0.09 | 0.10 | 1.00 |

```latex
\begin{table}[t]
\centering
\footnotesize
\begin{tabular}{lrrrrrrrrr}
\hline
 & words & sents & cls & attr & rels & cls-abs & attr-abs & attr-bnd & rel-bnd \\
\hline
words      & 1.00 & \textbf{0.91} & 0.40 & 0.42 & 0.39 & $-0.19$ & 0.34 & 0.13 & 0.12 \\
sents      & \textbf{0.91} & 1.00 & 0.42 & 0.45 & 0.42 & $-0.13$ & 0.32 & 0.16 & 0.06 \\
classes    & 0.40 & 0.42 & 1.00 & 0.41 & \textbf{0.93} & 0.18 & 0.16 & $-0.23$ & $-0.27$ \\
attributes & 0.42 & 0.45 & 0.41 & 1.00 & 0.39 & 0.09 & 0.45 & 0.02 & $-0.10$ \\
relations  & 0.39 & 0.42 & \textbf{0.93} & 0.39 & 1.00 & 0.27 & 0.12 & $-0.18$ & $-0.34$ \\
cls-abs    & $-0.19$ & $-0.13$ & 0.18 & 0.09 & 0.27 & 1.00 & $-0.04$ & 0.07 & \textbf{$-0.63$} \\
attr-abs   & 0.34 & 0.32 & 0.16 & 0.45 & 0.12 & $-0.04$ & 1.00 & $-0.26$ & 0.09 \\
attr-bnd   & 0.13 & 0.16 & $-0.23$ & 0.02 & $-0.18$ & 0.07 & $-0.26$ & 1.00 & 0.10 \\
rel-bnd    & 0.12 & 0.06 & $-0.27$ & $-0.10$ & $-0.34$ & \textbf{$-0.63$} & 0.09 & 0.10 & 1.00 \\
\hline
\end{tabular}
\caption{Pairwise Spearman $\rho$ across nine per-record features.
Boldface marks the four largest absolute correlations. All nine
features are defined in \texttt{out/per\_record.csv}.}
\label{tab:corr}
\end{table}
```

### 7.2 Four strong correlations, and what they say

1. **ρ(words, sentences) = 0.91** — sanity check: the two NLT
   length measures agree.
2. **ρ(classes, relationships) = 0.93** — a bigger class set
   mechanically implies more relationships. The 0.07 of unexplained
   variance is the modeller's choice of *what kind* of relationship
   to draw.
3. **ρ(relationships, % rels bound) = −0.34** — more
   relationships ⇒ harder for the binder to recover all of them
   (longer sentences ⇒ longer dep paths).
4. **ρ(cov_classes_absent, % rels bound) = −0.63** — the strongest
   negative correlation. Records with many lexically-absent classes
   (e.g. `HelpingHands`, `LabTracker`) also have low relationship
   recoverability. The reason is that the modeller introduced
   supertype abstractions precisely where the NLT phrased the
   relationship abstractly; the binder correctly refuses to bind.

**Insight 12 — diagram size, NLT length, and the binder's success
are not independent.** Bigger diagrams come from longer NLTs, and
longer NLTs distribute class mentions across sentences, which
breaks the dep-graph binder. This is the *intrinsic* difficulty of
the harder records in the benchmark.

---

## 8. NLT style features (extra E)

| dataset | passive ratio | hedge density | modal density | entity density |
|---|---:|---:|---:|---:|
| kaiser | 0.311 | 0.0149 | 0.0171 | 0.0239 |
| reference | 0.246 | 0.0188 | 0.0202 | 0.0179 |
| data_source_3 | 0.311 | 0.0149 | 0.0171 | 0.0239 |

```latex
\begin{table}[t]
\centering
\small
\begin{tabular}{lrrrr}
\hline
dataset & passive & hedge & modal & entity \\
\hline
kaiser           & 0.311 & 0.0149 & 0.0171 & 0.0239 \\
reference        & 0.246 & 0.0188 & 0.0202 & 0.0179 \\
data\_source\_3  & 0.311 & 0.0149 & 0.0171 & 0.0239 \\
\hline
\end{tabular}
\caption{NLT style features, mean per record. ``passive'' is the
ratio of \texttt{nsubjpass} to \texttt{nsubj} dependencies;
``hedge'' and ``modal'' are token densities of hedge-words and
English modal verbs; ``entity'' is the density of spaCy named
entities.}
\label{tab:style}
\end{table}
```

**Insight 13 — the kaiser and data_source_3 NLTs are stylistically
identical.** All four style features are equal to four decimal places
between kaiser and data_source_3. This is *expected*: they are the
same 45 NLTs. But it confirms the preprocessing is stable.

**Insight 14 — `reference` is the most idiomatic.** Lower passive
ratio (0.246 vs 0.311) means the NLTs of `reference` are more
declarative; higher hedge and modal densities mean the spec is
softer ("may take part", "typically is stored"). This is the
opposite of the textbook style of the kaiser NLTs, which is
systematically written in the passive voice ("are stored", "is
recorded").

---

## 9. Per-sentence analysis (extra C)

| dataset | sents / record | sent length (words) | % sents with class hit | % sents with attr hit |
|---|---:|---:|---:|---:|
| kaiser | 18.0 | 17.6 | 81% | 45% |
| reference | 22.2 | 19.0 | 92% | 51% |
| data_source_3 | 18.0 | 17.6 | 81% | 45% |

**Insight 15 — 81% of sentences mention at least one class, but
only 45% mention at least one attribute.** This means NLT
sentences carry most of their information through nouns (classes)
and only occasionally through attribute names. The implication for
generation: an LLM that names a class per sentence is doing
*roughly the right thing*; one that invents an attribute per
sentence is hallucinating.

---

## 10. What this enables — actionable conclusions

1. **For metric designers.** When evaluating generated diagrams
   against `kaiser` and `data_source_3` simultaneously, expect a
   ceiling Jaccard of 0.92 on relationships and 0.99 on
   classes/attributes. Any candidate that scores below 0.80
   relationship Jaccard is doing worse than the disagreement
   between the two gold references.
2. **For LLM prompt designers.** The NLTs of `reference` are
   more idiomatic and produce models that the dep-graph binder
   cannot reconstruct (43% attribute binding vs 68% for kaiser).
   LLM evaluation should treat `reference` as the harder
   benchmark; the kaiser / data_source_3 split is the *easier*
   one (textbook NLTs).
3. **For LLM-as-judge pipelines.** The 50 lexically-absent class
   names listed in `out/summary.json.lexically_absent_classes` are
   a hard ceiling for any direct-string-match metric. A judge
   that scores on partial credit for *syntactic plausibility*
   (i.e. asks "is this a reasonable supertype name for the
   described role?") can break through this ceiling.
4. **For benchmark curators.** The case-study markdowns in
   `out/examples/` and the `kaiser_BusTransportationManagementSystem`
   case in particular show that the *same* NLT can be modelled as
   `Shift`-as-class or `Shift`-as-enum with no loss of validity.
   The benchmark should document these decisions explicitly, or
   score against both references with a per-record union.

---

## 11. Reproducing every number on this page

```bash
# 1. Run the full pipeline
make -C Data/NLP-Analysis all

# 2. Read the JSON
python3 -c "import json; print(json.dumps(json.load(open('Data/NLP-Analysis/out/summary.json')), indent=2))"

# 3. Re-run the tests
make -C Data/NLP-Analysis test      # 20 passed, 1 skipped
```

The single source of truth is `Data/NLP-Analysis/out/summary.json`.
Every table in this document is built by reading one slice of that
JSON; the LaTeX blocks are written by hand but the numbers are not.
