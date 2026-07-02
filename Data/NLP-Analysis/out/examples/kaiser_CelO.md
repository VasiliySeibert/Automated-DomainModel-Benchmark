# CelO (kaiser) — Domain model with multiple inheritance and roles

**NLT length:** 2766 chars, 481 words, 23 sentences


## Natural language text (excerpt)

```
Celebrations Organization System 
The CelO application helps families and groups of friends to organize birthday celebrations and other events. Organizers can keep track of which tasks have been completed and who attends. Attendees can indicate what they are bringing to the event. 
For a small event, there is typically one organizer, but larger events require several organizers. An organizer provides their first and last name, their email address (which is also used as their username), their postal address, their phone number, and their password. Furthermore, an organizer indicates the kind of event that needs to be planned by selecting from a list of events (e.g., birthday party, graduation party…) or creating a new kind of event. The start date/time and end date/time of the event must be specified as well as the occasion and location of the event. The location can again be selected from a list, or a new one can be created by specifying the name of the location and its address. An organizer then invites the attendees by entering their first and last names as well as their email addresses. Sometimes, an organizer is only managing the event but not attending the event. Sometimes, an

[…truncated, total 2766 chars]
```


## Diagram summary

- 10 classes, 2 enums, 14 relationships

### Classes and their attributes

| Class | Abstract | Attributes (type) | L1 | L2 | L3 | L4 | absent |
|---|---|---|---|---|---|---|---|
| Person | False | LastName (String), FirstName (String), EmailAddress (String), Password (String) | ✗ | ✗ | ✗ | ✗ | **YES** |
| PersonRole | True | — | ✗ | ✗ | ✗ | ✓ | no |
| Organizer | False | Address (String), PhoneNumber (String) | ✓ | ✓ | ✓ | ✓ | no |
| Attendee | False | — | ✓ | ✓ | ✓ | ✓ | no |
| TaskStatus | False | status (CompletionStatus) | ✓ | ✓ | ✓ | ✓ | no |
| Registration | False | Status (AttendeeStatus) | ✗ | ✗ | ✗ | ✗ | **YES** |
| CheckListTask | False | Description (String) | ✓ | ✓ | ✓ | ✓ | no |
| Location | False | Name (String), Address (String) | ✓ | ✓ | ✓ | ✓ | no |
| Event | False | Occasion (String), StartTime (Date), EndTime (Date) | ✓ | ✓ | ✓ | ✓ | no |
| EventType | False | Name (String) | ✓ | ✓ | ✓ | ✓ | no |

### Relationships

| Source | Type | Target | Card src | Card tgt | Label | src absent? | tgt absent? |
|---|---|---|---|---|---|---|---|
| PersonRole | inheritance | Organizer | — | — | — | no | no |
| PersonRole | inheritance | Attendee | — | — | — | no | no |
| Person | association | PersonRole | 1 | 0..2 | — | **YES** | no |
| Organizer | association | Event | 1..* | * | — | no | no |
| Attendee | association | TaskStatus | 0..1 | * | — | no | no |
| Attendee | association | Event | * | * | — | no | no |
| Attendee | dependency | Registration | — | — | — | no | **YES** |
| Attendee | dependency | Event | — | — | — | no | no |
| Event | association | CheckListTask | * | * | — | no | no |
| Event | dependency | TaskStatus | — | — | — | no | no |
| Event | dependency | CheckListTask | — | — | — | no | no |
| Location | association | Event | 1 | * | — | no | no |
| EventType | association | Event | 1 | * | — | no | no |
| EventType | association | CheckListTask | 1 | * | — | no | no |

## Lex-match — interesting cases


Classes that are **lexically absent** in the NLT (no L1, L2, L3 or L4 match):

- `Person` — sentence indices with token hits: []
- `Registration` — sentence indices with token hits: []

Attributes that are **lexically absent** in the NLT:

- `CheckListTask.Description` (type: String) — sentence indices: []

## Dependency-graph bindings (first 8)


### Class↔Attribute

| Class | Attribute | Sentence | Path | Hops |
|---|---|---|---|---|
| Organizer | LastName | #65 | `organizer provides name` | 2 |
| Organizer | FirstName | #65 | `organizer provides name` | 2 |
| Organizer | EmailAddress | #65 | `organizer provides name address` | 3 |
| Organizer | Address | #65 | `organizer provides name address` | 3 |
| Organizer | PhoneNumber | #65 | `organizer provides name address number` | 4 |
| Organizer | status | #303 | `organizer view status` | 2 |
| Organizer | Status | #303 | `organizer view status` | 2 |
| Organizer | Name | #65 | `organizer provides name` | 2 |

### Class↔Relationship (best path per relationship)

| Source | Type | Target | # sentences | Best path | Hops |
|---|---|---|---|---|---|
| Organizer | association | Event | 8 | `organizers require events` | 2 |
| Attendee | association | TaskStatus | 4 | `attendees accomplish task` | 2 |
| Attendee | association | Event | 6 | `attendee indicate attend event` | 3 |
| Attendee | dependency | Event | 6 | `attendee indicate attend event` | 3 |
| Event | association | CheckListTask | 3 | `events of list` | 2 |
| Event | dependency | TaskStatus | 2 | `event of status` | 2 |
| Event | dependency | CheckListTask | 3 | `events of list` | 2 |
| Location | association | Event | 1 | `location occasion of event` | 3 |
| EventType | association | Event | 15 | `events` | 0 |
| EventType | association | CheckListTask | 3 | `events of list` | 2 |