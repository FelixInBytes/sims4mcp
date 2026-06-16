from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class SimAge(StrEnum):
    BABY = "baby"
    TODDLER = "toddler"
    CHILD = "child"
    TEEN = "teen"
    YOUNG_ADULT = "young_adult"
    ADULT = "adult"
    ELDER = "elder"


class SimGender(StrEnum):
    MALE = "male"
    FEMALE = "female"


@dataclass
class Moodlet:
    id: int
    name: str
    decay: int | None = None


@dataclass
class Career:
    name: str
    level: int = 1
    track: str | None = None


@dataclass
class Skill:
    name: str
    level: int = 1


@dataclass
class Relationship:
    sim_id: int
    sim_name: str
    friendship: float = 0.0
    romance: float = 0.0


@dataclass
class HouseholdFunds:
    simoleons: float = 0.0


@dataclass
class Sim:
    id: int
    first_name: str
    last_name: str
    age: SimAge | None = None
    gender: SimGender | None = None
    traits: list[str] = field(default_factory=list)
    moodlets: list[Moodlet] = field(default_factory=list)
    career: Career | None = None
    skills: list[Skill] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)
    money: float = 0.0
    household_id: int | None = None
    is_death: bool = False
    death_type: str | None = None


@dataclass
class Household:
    id: int
    name: str
    funds: HouseholdFunds | None = None
    sims: list[Sim] = field(default_factory=list)


@dataclass
class SaveFile:
    path: Path
    name: str
    households: list[Household] = field(default_factory=list)

    @property
    def sims(self) -> list[Sim]:
        return [sim for hh in self.households for sim in hh.sims]
