# NLP Analysis — Summary

## 1. Per-dataset overview

| dataset       |   n |   words_mean |   words_med |   sents_mean |   classes_mean |   attrs_mean |   rels_mean |   rels_median |
|:--------------|----:|-------------:|------------:|-------------:|---------------:|-------------:|------------:|--------------:|
| data_source_3 |  45 |       315.82 |         300 |        19.91 |           9.42 |        12.87 |       11.11 |            10 |
| kaiser        |  45 |       315.82 |         300 |        19.91 |           9.44 |        13    |       11.91 |            11 |
| reference     |   8 |       422.88 |         428 |        26.5  |          14.38 |        10.25 |       21.62 |            20 |

## 2. Mean relationship-type counts per record

| dataset       |   n_rels_association |   n_rels_aggregation |   n_rels_inheritance |   n_rels_composition |   n_rels_dependency |   n_rels_total |   n_rels_bound |   n_rels_directed |   n_rels_association_class |
|:--------------|---------------------:|---------------------:|---------------------:|---------------------:|--------------------:|---------------:|---------------:|------------------:|---------------------------:|
| data_source_3 |                 6.95 |                 1.25 |                 3.64 |                  5.4 |               nan   |          11.11 |           8.67 |              4.8  |                       1.18 |
| kaiser        |                 6.87 |                 1.2  |                 3.64 |                  4   |                 2.4 |          11.91 |           8.82 |              4.73 |                     nan    |
| reference     |                10.88 |               nan    |                 4.86 |                 10.4 |               nan   |          21.62 |          14.12 |            nan    |                     nan    |

## 3. Multiplicity coverage

| dataset       |   n_relationships |   n_rels_with_card |   pct_with_card |
|:--------------|------------------:|-------------------:|----------------:|
| data_source_3 |             11.11 |               8.31 |           74.8  |
| kaiser        |             11.91 |               8.33 |           69.94 |
| reference     |             21.62 |              13.62 |           63    |

## 4. Lexical coverage (mean per record, %)

L1=direct, L2=lemma/plural, L3=camelCase-split, L4=WordNet synonym, absent=none.

| dataset       |   cov_classes_L1 |   cov_classes_L2 |   cov_classes_L3 |   cov_classes_L4 |   cov_classes_absent |   cov_attrs_L1 |   cov_attrs_L2 |   cov_attrs_L3 |   cov_attrs_L4 |   cov_attrs_absent |   cov_enum_absent |   cov_rel_src_absent |   cov_rel_tgt_absent |
|:--------------|-----------------:|-----------------:|-----------------:|-----------------:|---------------------:|---------------:|---------------:|---------------:|---------------:|-------------------:|------------------:|---------------------:|---------------------:|
| data_source_3 |            87.77 |            93.46 |            87.77 |            94.2  |                 4.83 |          78.73 |          82.18 |          78.73 |          84.85 |               9.44 |              7.22 |                 4.54 |                 4.54 |
| kaiser        |            87.77 |            93.46 |            87.77 |            94.2  |                 4.83 |          78.62 |          82.07 |          78.62 |          84.77 |               9.55 |              5.95 |                 5.29 |                 5.29 |
| reference     |            87.09 |            87.78 |            87.09 |            89.79 |                 7.66 |          44.93 |          49.09 |          44.93 |          50.9  |              10.22 |             21.95 |                12.16 |                12.16 |

## 5. Dependency-graph binding (mean per record)

| dataset       |   pct_attrs_bound |   pct_rels_bound |   avg_hop_class_attr |   avg_hop_rel |
|:--------------|------------------:|-----------------:|---------------------:|--------------:|
| data_source_3 |            67.934 |           79.53  |                2.15  |         1.762 |
| kaiser        |            67.824 |           75.398 |                2.139 |         1.854 |
| reference     |            43.12  |           65.274 |                1.33  |         1.465 |

## 6. Cross-dataset: kaiser vs data_source_3 (same 45 NLTs)

|       |   jaccard_classes |   jaccard_attributes |   jaccard_rels |
|:------|------------------:|---------------------:|---------------:|
| count |            45     |               45     |         45     |
| mean  |             0.994 |                0.992 |          0.924 |
| std   |             0.028 |                0.038 |          0.11  |
| min   |             0.833 |                0.79  |          0.5   |
| 25%   |             1     |                1     |          0.889 |
| 50%   |             1     |                1     |          1     |
| 75%   |             1     |                1     |          1     |
| max   |             1     |                1     |          1     |

Records with imperfect class Jaccard:

|    | id                                | only_in_kaiser_classes   | only_in_data_source_3_classes   |
|---:|:----------------------------------|:-------------------------|:--------------------------------|
|  5 | BusTransportationManagementSystem | shift                    | nan                             |
| 14 | FilmSet                           | nan                      | n1                              |

Records with the lowest relationship Jaccard:

|    | id                 |   kaiser_n_rels |   data_source_3_n_rels |   jaccard_rels |
|---:|:-------------------|----------------:|-----------------------:|---------------:|
| 37 | StudentAppointment |               8 |                      6 |         0.5    |
| 31 | ProjectManagement  |              10 |                      8 |         0.6    |
| 34 | Sightseeing        |               8 |                      7 |         0.75   |
|  7 | CelO               |              14 |                     11 |         0.7692 |
| 43 | University         |              10 |                      9 |         0.8    |
