# BusTransportationManagementSystem (kaiser) — Fielded NLT with explicit BTMS acronym

**NLT length:** 1835 chars, 345 words, 17 sentences


## Natural language text (excerpt)

```
A city is using the Bus Transportation Management System (BTMS) to simplify the day-to-day activities related to the city’s public bus system.
The BTMS keeps track of a driver’s name and automatically assigns a unique ID to each driver. A bus route is identified by a unique number that is determined by city staff, while a bus is identified by its unique licence plate. The highest possible number for a bus route is 9999, while a licence plate number may be up to 10 characters long, inclusive. For up to a year in advance, city staff assigns buses to routes. Several buses may be assigned to a route per day. Each bus serves at the most one route per day but may be assigned to different routes on different days. Similarly, for up to a year in advance, city staff posts the schedule for its bus drivers. For each route, there is a morning shift, an afternoon shift, and a night shift. A driver is assigned by city staff to a shift for a particular bus on a particular day. The BTMS offers city staff great flexibility, i.e., there are no restrictions in terms of how many shifts a bus driver has per day. It is even possible to assign a bus driver to two shifts at the same time.
The current vers

[…truncated, total 1835 chars]
```


## Diagram summary

- 6 classes, 0 enums, 4 relationships

### Classes and their attributes

| Class | Abstract | Attributes (type) | L1 | L2 | L3 | L4 | absent |
|---|---|---|---|---|---|---|---|
| Shift | False | — | ✓ | ✓ | ✓ | ✓ | no |
| BusVehicle | False | LicencePlate (String), InRepairShop (Boolean) | ✓ | ✓ | ✓ | ✓ | no |
| Route | False | Number (Int) | ✓ | ✓ | ✓ | ✓ | no |
| RouteAssignment | False | Date (Date) | ✓ | ✓ | ✓ | ✓ | no |
| Driver | False | Name (String), Id (String), OnSickLeave (Boolean) | ✓ | ✓ | ✓ | ✓ | no |
| DriverSchedule | False | Shift (Shift) | ✓ | ✓ | ✓ | ✓ | no |

### Relationships

| Source | Type | Target | Card src | Card tgt | Label | src absent? | tgt absent? |
|---|---|---|---|---|---|---|---|
| BusVehicle | association | RouteAssignment | 1 | 0..* | — | no | no |
| Route | association | RouteAssignment | 1 | 0..* | — | no | no |
| Driver | association | DriverSchedule | 1 | 0..* | — | no | no |
| RouteAssignment | association | DriverSchedule | 1 | 0..* | — | no | no |

## Lex-match — interesting cases


Attributes that are **lexically absent** in the NLT:

- `RouteAssignment.Date` (type: Date) — sentence indices: []

## Dependency-graph bindings (first 8)


### Class↔Attribute

| Class | Attribute | Sentence | Path | Hops |
|---|---|---|---|---|
| Shift | InRepairShop | #208 | `shifts has of terms in` | 4 |
| Shift | Number | #326 | `shifts shows for number` | 3 |
| Shift | Name | #326 | `shifts IDs names` | 2 |
| Shift | Id | #326 | `shifts IDs` | 1 |
| Shift | OnSickLeave | #189 | `shift on` | 1 |
| Shift | Shift | #170 | `shift` | 0 |
| BusVehicle | LicencePlate | #50 | `bus identified by plate` | 3 |
| BusVehicle | InRepairShop | #279 | `bus is in` | 2 |

### Class↔Relationship (best path per relationship)

| Source | Type | Target | # sentences | Best path | Hops |
|---|---|---|---|---|---|
| BusVehicle | association | RouteAssignment | 7 | `bus route` | 1 |
| Route | association | RouteAssignment | 8 | `route` | 0 |
| Driver | association | DriverSchedule | 10 | `driver` | 0 |
| RouteAssignment | association | DriverSchedule | 1 | `route to assigned scheduled` | 3 |