from __future__ import annotations

from sims4mcp.models import (
    SaveFile,
    Household,
    HouseholdFunds,
    Sim,
    SimAge,
    SimGender,
    Moodlet,
    Career,
    Skill,
    Relationship,
)


def test_sim_defaults() -> None:
    sim = Sim(id=1, first_name="Jane", last_name="Doe")
    assert sim.id == 1
    assert sim.first_name == "Jane"
    assert sim.last_name == "Doe"
    assert sim.age is None
    assert sim.gender is None
    assert sim.traits == []
    assert sim.moodlets == []
    assert sim.skills == []
    assert sim.relationships == []
    assert sim.money == 0.0
    assert not sim.is_death


def test_sim_with_full_data() -> None:
    sim = Sim(
        id=42,
        first_name="Bob",
        last_name="Builder",
        age=SimAge.ADULT,
        gender=SimGender.MALE,
        traits=["Active", "Creative"],
        career=Career(name="Architect", level=5),
        skills=[Skill(name="Handiness", level=7)],
        money=15000.0,
    )
    assert sim.age == SimAge.ADULT
    assert sim.gender == SimGender.MALE
    assert "Active" in sim.traits
    assert sim.career is not None
    assert sim.career.name == "Architect"
    assert sim.skills[0].level == 7
    assert sim.money == 15000.0


def test_sim_age_enum_values() -> None:
    assert list(SimAge) == [
        SimAge.BABY,
        SimAge.TODDLER,
        SimAge.CHILD,
        SimAge.TEEN,
        SimAge.YOUNG_ADULT,
        SimAge.ADULT,
        SimAge.ELDER,
    ]


def test_household_with_sims() -> None:
    sim1 = Sim(id=1, first_name="Alice", last_name="Smith")
    sim2 = Sim(id=2, first_name="Bob", last_name="Smith")
    hh = Household(id=10, name="Smith Residence", funds=HouseholdFunds(2500.0), sims=[sim1, sim2])
    assert len(hh.sims) == 2
    assert hh.funds is not None
    assert hh.funds.simoleons == 2500.0


def test_savefile_sims_property() -> None:
    sim1 = Sim(id=1, first_name="A", last_name="B")
    sim2 = Sim(id=2, first_name="C", last_name="D")
    hh1 = Household(id=10, name="HH1", sims=[sim1])
    hh2 = Household(id=20, name="HH2", sims=[sim2])
    sf = SaveFile(path="/fake/path", name="test", households=[hh1, hh2])
    assert len(sf.sims) == 2
    assert sf.sims[0].first_name == "A"
    assert sf.sims[1].first_name == "C"


def test_moodlet() -> None:
    m = Moodlet(id=123, name="Happy", decay=10)
    assert m.name == "Happy"
    assert m.decay == 10


def test_relationship() -> None:
    r = Relationship(sim_id=2, sim_name="Bob", friendship=75.0, romance=20.0)
    assert r.friendship == 75.0
    assert r.romance == 20.0
