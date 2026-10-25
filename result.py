from dataclasses import dataclass, field
from typing import Literal


@dataclass
class ModuleResult:
    name: str                      # e.g. "alpha", "buckets"
    value: float | dict | None     # the headline number or small dict
    status: Literal["good", "fair", "weak", "na"]
    reading: str                   # one plain-English sentence for the page
    details: dict = field(default_factory=dict)   # tables and extras for the Analyst view
