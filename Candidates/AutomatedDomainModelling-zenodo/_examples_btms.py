"""Build the BTMS example JSON for one-shot / two-shot strategies.

The BTMS (Bus Transportation Management System) row from the original
zenodo models.csv — verbatim spec + reference model in the zenodo
text format.
"""
import json
from pathlib import Path


BTMS_SPEC = """A city is using the Bus Transportation Management System (BTMS) to simplify the day-to-day activities related to the city public bus system.

The BTMS keeps track of a driver name and automatically assigns a unique ID to each driver. A bus route is identified by a unique number that is determined by city staff, while a bus is identified by its unique licence plate. The highest possible number for a bus route is 9999, while a licence plate number may be up to 10 characters long, inclusive. For up to a year in advance, city staff assigns buses to routes. Several buses may be assigned to a route per day. Each bus serves at the most one route per day but may be assigned to different routes on different days. Similarly, for up to a year in advance, city staff posts the schedule for its bus drivers. For each route, there is a morning shift, an afternoon shift, and a night shift. A driver is assigned by city staff to a shift for a particular bus on a particular day. The BTMS offers city staff great flexibility, i.e., there are no restrictions in terms of how many shifts a bus driver has per day. It is even possible to assign a bus driver to two shifts at the same time.

The current version of BTMS does not support the information of bus drivers or buses to be updated only adding and deleting is supported. However, BTMS does support indicating whether a bus driver is on sick leave and whether a bus is in the repair shop. If that is the case, the driver cannot be scheduled or the bus cannot be assigned to a route. For a given day, an overview shows for each route number the licence plate number of each assigned bus, the entered shifts and the IDs and names of the assigned drivers. If a driver is currently sick or a bus is in the repair shop, the driver or bus, respectively, is highlighted in the overview."""


BTMS_MODEL = """Enumeration:
Shift(morning, afternoon, night)
Classes:
BTMS()
BusVehicle(string licencePlate, boolean inRepairShop)
Route(int number)
RouteAssignment(Date date)
Driver(string name, string id, boolean onSickLeave)
DriverSchedule(Shift shit)

Relationships:
1 BTMS contain * BusVehicle
1 BTMS contain * Route
1 BTMS contain * RouteAssignment
1 BTMS contain * Drivers
1 BTMS contain * DriverSchedule

* RouteAssignment associate 1 BusVehicle
* RouteAssignment associate 1 Route

* DriverSchedule associate 1 Driver
* DriverSchedule associate 1 RouteAssignment"""


def write_btms_json(target: Path) -> None:
    """Write a one-element examples.json containing the BTMS example."""
    target.write_text(
        json.dumps(
            {"examples": [{"id": "BTMS", "nlt": BTMS_SPEC, "model": BTMS_MODEL}]},
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )