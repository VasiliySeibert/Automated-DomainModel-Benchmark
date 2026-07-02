# AirTravel (kaiser) — Mid-length, classic NLT-for-class-diagram textbook example

**NLT length:** 1476 chars, 247 words, 20 sentences


## Natural language text (excerpt)

```
The name, type, year of manufacture, and date of the next inspection are stored for aircraft. An aircraft performs several flights, the flight number and date of which are stored. 
Several passengers take part in a flight, and their names and passport numbers are stored. A passenger can take part in several flights. The (personalized) ticket for each flight is stored in the form of the ticket number and price. In addition, it is stored whether an upgrade is desired. 
Passenger aircraft are special aircraft used exclusively for the transport of passengers. The number of seats on these aircraft is also stored. 
A passenger aircraft can have several seat categories. The designation of each category is stored, whether or not it offers an entertainment program, and how many seats there are in this category. Each ticket is for a specific seat category.
Each aircraft can be part of an airline, whose name is stored. 
An airline employs several flight attendants and pilots. The name, date of employment, and whether the flight attendant is a chief steward or stewardess are stored for flight attendants. The name, date of employment, and license are stored for pilots.
Several flight attendants

[…truncated, total 1476 chars]
```


## Diagram summary

- 12 classes, 0 enums, 18 relationships

### Classes and their attributes

| Class | Abstract | Attributes (type) | L1 | L2 | L3 | L4 | absent |
|---|---|---|---|---|---|---|---|
| Airline | False | Name (String) | ✓ | ✓ | ✓ | ✓ | no |
| Employee | False | Nmae (String), StartDate (Date) | ✗ | ✗ | ✗ | ✗ | **YES** |
| Airport | False | Name (String), Address (String), RunwayCount (Int) | ✓ | ✓ | ✓ | ✓ | no |
| FlightAttendant | False | Purser (Boolean) | ✓ | ✓ | ✓ | ✓ | no |
| Airplane | False | Name (String), Type (String), ConstructionYear (Date), NextInspection (Date) | ✗ | ✗ | ✗ | ✗ | **YES** |
| Flight | False | FlightNumber (String) | ✓ | ✓ | ✓ | ✓ | no |
| Pilot | False | License (String) | ✓ | ✓ | ✓ | ✓ | no |
| PassengerPlane | False | Seats (Int) | ✓ | ✓ | ✓ | ✓ | no |
| FlightExecution | False | Date (Date) | ✓ | ✓ | ✓ | ✓ | no |
| SeatCategory | False | Description (String), Enterainment (Boolean), SeatCount (Int) | ✓ | ✓ | ✓ | ✓ | no |
| Passenger | False | Name (String), PassportNumber (String) | ✓ | ✓ | ✓ | ✓ | no |
| Ticket | False | TicketId (String), Price (Float), Upgrade (Boolean) | ✓ | ✓ | ✓ | ✓ | no |

### Relationships

| Source | Type | Target | Card src | Card tgt | Label | src absent? | tgt absent? |
|---|---|---|---|---|---|---|---|
| Airline | association | Employee | 0..1 | 0..* | — | no | **YES** |
| Airline | aggregation | Airplane | 0..1 | 0..* | — | no | **YES** |
| Airplane | association | Airport | 0..* | 0..1 | — | **YES** | no |
| Airplane | association | FlightExecution | 0..1 | 0..* | — | **YES** | no |
| Airport | association | Flight | 0..1 | 0..* | Source | no | no |
| Airport | association | Flight | 0..1 | 0..* | Destination | no | no |
| Flight | association | FlightExecution | 0..1 | 0..* | — | no | no |
| FlightExecution | association | FlightAttendant | 0..* | 0..* | — | no | no |
| FlightExecution | association | Pilot | 0..* | 0..1 | Captain | no | no |
| FlightExecution | association | Pilot | 0..* | 0..2 | Co-pilot | no | no |
| FlightExecution | association | Passenger | 0..* | 0..* | — | no | no |
| Employee | inheritance | FlightAttendant | — | — | — | **YES** | no |
| Employee | inheritance | Pilot | — | — | — | **YES** | no |
| Airplane | inheritance | PassengerPlane | — | — | — | **YES** | no |
| PassengerPlane | composition | SeatCategory | 0..1 | 0..* | — | no | no |
| SeatCategory | association | Ticket | 0..1 | 0..* | — | no | no |
| FlightExecution | dependency | Ticket | — | — | — | no | no |
| FlightExecution | dependency | Passenger | — | — | — | no | no |

## Lex-match — interesting cases


Classes that are **lexically absent** in the NLT (no L1, L2, L3 or L4 match):

- `Employee` — sentence indices with token hits: []
- `Airplane` — sentence indices with token hits: []

Attributes that are **lexically absent** in the NLT:

- `Employee.Nmae` (type: String) — sentence indices: []
- `FlightAttendant.Purser` (type: Boolean) — sentence indices: []
- `SeatCategory.Description` (type: String) — sentence indices: []
- `SeatCategory.Enterainment` (type: Boolean) — sentence indices: []

## Dependency-graph bindings (first 8)


### Class↔Attribute

| Class | Attribute | Sentence | Path | Hops |
|---|---|---|---|---|
| Airline | Name | #167 | `airline stored name` | 2 |
| Airline | Name | #167 | `airline stored name` | 2 |
| Airline | Name | #167 | `airline stored name` | 2 |
| Airline | FlightNumber | #182 | `airline employs attendants flight` | 3 |
| Airline | Name | #167 | `airline stored name` | 2 |
| Airport | Name | #259 | `airports for stored name` | 3 |
| Airport | Name | #259 | `airports for stored name` | 3 |
| Airport | Address | #259 | `airports for stored name address` | 4 |

### Class↔Relationship (best path per relationship)

| Source | Type | Target | # sentences | Best path | Hops |
|---|---|---|---|---|---|
| Airport | association | Flight | 1 | `airport has flight` | 2 |
| Airport | association | Flight | 1 | `airport has flight` | 2 |
| Flight | association | FlightExecution | 8 | `flights` | 0 |
| FlightExecution | association | FlightAttendant | 8 | `flights` | 0 |
| FlightExecution | association | Pilot | 1 | `flight attendants pilots` | 2 |
| FlightExecution | association | Pilot | 1 | `flight attendants pilots` | 2 |
| FlightExecution | association | Passenger | 2 | `flight in take passengers` | 3 |
| PassengerPlane | composition | SeatCategory | 1 | `passenger aircraft have categories` | 3 |
| SeatCategory | association | Ticket | 1 | `category for is ticket` | 3 |
| FlightExecution | dependency | Ticket | 1 | `flight for ticket` | 2 |
| FlightExecution | dependency | Passenger | 2 | `flight in take passengers` | 3 |