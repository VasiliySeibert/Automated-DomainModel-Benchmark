# LabTracker (reference) — Long, complex NLT with enum-heavy model

**NLT length:** 3197 chars, 571 words, 30 sentences


## Natural language text (excerpt)

```
The LabTracker software helps (i) doctors manage the requisition of tests and examinations for patients and (ii) patients book appointments for tests and examinations at a lab. For the remainder of this description, tests and examinations are used interchangeably. For a requisition, a doctor must provide their numeric practitioner number and signature for verification as well as their full name, their address, and their phone number. The signature is a digital signature, i.e., an image of the actual signature of the doctor. Furthermore, the doctor indicates the date from which the requisition is valid. The requisition must also show the patient’s information including their alpha-numeric health number, first name and last name, date of birth, address, and phone number. A doctor cannot prescribe a test for themselves but can prescribe tests to someone else who is a doctor. Several tests can be combined on one requisition but only if they belong to the same group of tests. For example, only blood tests can be combined on one requisition or only ultrasound examinations can be combined. It is not possible to have a blood test and an ultrasound examination on the same requisition. For e

[…truncated, total 3197 chars]
```


## Diagram summary

- 14 classes, 3 enums, 20 relationships

### Classes and their attributes

| Class | Abstract | Attributes (type) | L1 | L2 | L3 | L4 | absent |
|---|---|---|---|---|---|---|---|
| PersonRole | True | — | ✗ | ✗ | ✗ | ✓ | no |
| LabTracker | False | — | ✓ | ✓ | ✓ | ✓ | no |
| Person | False | — | ✗ | ✗ | ✗ | ✓ | no |
| Patient | False | — | ✓ | ✓ | ✓ | ✓ | no |
| Doctor | False | — | ✓ | ✓ | ✓ | ✓ | no |
| Requisition | False | — | ✓ | ✓ | ✓ | ✓ | no |
| TestResult | False | — | ✓ | ✓ | ✓ | ✓ | no |
| SpecificTest | False | — | ✓ | ✓ | ✓ | ✓ | no |
| Data | False | — | ✗ | ✗ | ✗ | ✓ | no |
| Appointment | False | — | ✓ | ✓ | ✓ | ✓ | no |
| BusinessHour | False | — | ✓ | ✓ | ✓ | ✓ | no |
| Lab | False | — | ✓ | ✓ | ✓ | ✓ | no |
| Test | False | — | ✓ | ✓ | ✓ | ✓ | no |
| TestType | False | — | ✓ | ✓ | ✓ | ✓ | no |

### Relationships

| Source | Type | Target | Card src | Card tgt | Label | src absent? | tgt absent? |
|---|---|---|---|---|---|---|---|
| PersonRole | inheritance | Patient | — | — | — | no | no |
| PersonRole | inheritance | Doctor | — | — | — | no | no |
| LabTracker | composition | Person | — | — | — | no | no |
| LabTracker | composition | PersonRole | — | — | — | no | no |
| LabTracker | composition | Requisition | — | — | — | no | no |
| LabTracker | composition | TestResult | — | — | — | no | no |
| LabTracker | composition | SpecificTest | — | — | — | no | no |
| LabTracker | composition | Appointment | — | — | — | no | no |
| LabTracker | composition | BusinessHour | — | — | — | no | no |
| LabTracker | composition | Lab | — | — | — | no | no |
| LabTracker | composition | Test | — | — | — | no | no |
| LabTracker | composition | TestType | — | — | — | no | no |
| Person | association | PersonRole | 1 | 0..2 | — | no | no |
| Requisition | association | SpecificTest | — | * | — | no | no |
| Appointment | association | Lab | 0..* | 1 | — | no | no |
| Doctor | association | Requisition | 1 | * | — | no | no |
| Test | association | SpecificTest | — | * | — | no | no |
| TestType | association | Test | — | * | — | no | no |
| TestResult | association | SpecificTest | 0..1 | * | — | no | no |
| Lab | association | BusinessHour | — | 7 | — | no | no |

## Lex-match — interesting cases


## Dependency-graph bindings (first 8)


### Class↔Relationship (best path per relationship)

| Source | Type | Target | # sentences | Best path | Hops |
|---|---|---|---|---|---|
| LabTracker | composition | Requisition | 1 | `lab selects make appointment for requisition` | 5 |
| LabTracker | composition | TestResult | 3 | `lab at tests` | 2 |
| LabTracker | composition | SpecificTest | 3 | `lab at tests` | 2 |
| LabTracker | composition | Appointment | 2 | `lab selects make appointment` | 3 |
| LabTracker | composition | BusinessHour | 3 | `lab address hours` | 2 |
| LabTracker | composition | Lab | 9 | `lab` | 0 |
| LabTracker | composition | Test | 3 | `lab at tests` | 2 |
| LabTracker | composition | TestType | 3 | `lab at tests` | 2 |
| Requisition | association | SpecificTest | 7 | `requisition of tests` | 2 |
| Appointment | association | Lab | 2 | `appointment make selects lab` | 3 |
| Doctor | association | Requisition | 4 | `doctors manage requisition` | 2 |
| Test | association | SpecificTest | 20 | `tests` | 0 |
| TestType | association | Test | 20 | `tests` | 0 |
| TestResult | association | SpecificTest | 20 | `tests` | 0 |
| Lab | association | BusinessHour | 3 | `lab address hours` | 2 |