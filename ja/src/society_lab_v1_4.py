"""
society_lab v1.4
================

Minimal agent-based society lab.

Design rule:
Do not encode religion, caste, authority, or heresy as state variables.
Only record observable behavior, then detect emergent patterns afterward.

v1.4 adds a very weak bridge from interpretation to behavior:
recent interpretations nudge project choice and proposal support by about 3%.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional


NAMES = [
    "アルン", "ミラ", "カイ", "セナ", "ルト", "ファラ",
    "タロ", "イシュ", "ノア", "エリン", "ゾル", "ハナ",
    "レン", "シオン", "ユラ", "ギル", "メイ", "ダン",
    "ヴァル", "ティア", "オルン", "ケイ", "リオ", "サナ",
]

ACTIONS = (
    "store_food",
    "ask_help",
    "share_memory",
    "reassure",
    "withdraw",
    "dig_well",
    "hunt_group",
    "hold_ritual",
    "move_camp",
)

PROJECT_ACTIONS = (
    "store_food",
    "dig_well",
    "hunt_group",
    "hold_ritual",
    "move_camp",
)


@dataclass
class Memory:
    event: str
    year: int
    intensity: float
    decay_rate: float = 0.02
    source: str = "self"
    generation: int = 0
    interpretation: str = "none"

    def decay(self) -> None:
        self.intensity = max(0.0, self.intensity * (1.0 - self.decay_rate))


@dataclass
class Person:
    id: str
    name: str
    age: int
    charisma: float
    food_skill: float
    sex: str
    voice_weight: float = 0.0
    interpretation_bias: dict[str, float] = field(default_factory=dict)
    hunger: float = 0.0
    health: float = 1.0
    fear: float = 0.0
    action: str = "store_food"
    trust: dict[str, float] = field(default_factory=dict)
    memories: list[Memory] = field(default_factory=list)
    alive: bool = True

    def consumption(self) -> float:
        return 0.6 if self.age < 15 else 1.0

    def can_give_birth(self) -> bool:
        return (
            self.alive
            and self.sex == "f"
            and 18 <= self.age <= 42
            and self.health >= 0.55
            and self.hunger <= 0.70
        )

    def top_trusted(self, n: int = 2) -> list[str]:
        return [
            person_id
            for person_id, _ in sorted(
                self.trust.items(),
                key=lambda item: item[1],
                reverse=True,
            )[:n]
        ]

    def remember(self, memory: Memory) -> None:
        self.memories.append(memory)

    def strongest_memory(self) -> Optional[Memory]:
        if not self.memories:
            return None
        return max(self.memories, key=lambda memory: memory.intensity)


@dataclass
class FoodSystem:
    stock: float
    capacity: float


@dataclass
class Problem:
    type: str
    year: int
    severity: float


@dataclass
class Proposal:
    proposer_id: str
    action: str
    target_problem: str
    support_ids: list[str] = field(default_factory=list)


@dataclass
class Observation:
    year: int
    event_type: str
    persons: list[str]
    detail: str


class ObservationLog:
    def __init__(self, verbose: bool = False):
        self.entries: list[Observation] = []
        self.verbose = verbose

    def record(self, year: int, event_type: str, persons: list[str], detail: str) -> None:
        self.entries.append(Observation(year, event_type, persons, detail))
        if self.verbose:
            person_text = ", ".join(persons) if persons else "-"
            print(f"[Year {year:>3}] {event_type}: {person_text} | {detail}")

    def count(self, event_type: str) -> int:
        return sum(1 for entry in self.entries if entry.event_type == event_type)


class SocietyLab:
    def __init__(self, seed: Optional[int] = None, verbose: bool = False):
        self.rng = random.Random(seed)
        self.seed = seed
        self.year = 0
        self.log = ObservationLog(verbose=verbose)
        self.last_detection: dict[tuple[str, str], int] = {}
        self.current_problems: list[Problem] = []
        self.current_proposals: list[Proposal] = []
        self.proposal_support_by_person: dict[str, int] = {}
        self.project_success_by_person: dict[str, int] = {}
        self.project_failure_by_person: dict[str, int] = {}
        self.interpretation_action_nudge_count = 0
        self.interpretation_support_nudge_count = 0
        self.ritual_success_count = 0

        initial_pop = self.rng.randint(20, 40)
        self.age_profile = self.rng.choice(["young", "balanced", "old"])
        self.charisma_profile = self.rng.choice(["no_leader", "normal", "strong_founder"])
        self.people = self._create_people(initial_pop)
        self.next_person_index = len(self.people)
        self.food = FoodSystem(
            stock=initial_pop * self.rng.uniform(2.0, 6.0),
            capacity=initial_pop * self.rng.uniform(1.05, 1.45),
        )
        self.initial_population = initial_pop
        self.initial_food_stock = self.food.stock
        self.initial_food_capacity = self.food.capacity
        self._initialize_trust_network()

    @property
    def alive_people(self) -> list[Person]:
        return [person for person in self.people if person.alive]

    @property
    def population(self) -> int:
        return len(self.alive_people)

    def _create_people(self, n: int) -> list[Person]:
        people = []
        for index in range(n):
            if self.age_profile == "young":
                age = self.rng.randint(5, 35)
            elif self.age_profile == "old":
                age = self.rng.randint(25, 65)
            else:
                age = self.rng.randint(8, 55)

            if self.charisma_profile == "no_leader":
                charisma = self.rng.uniform(0.05, 0.55)
            elif self.charisma_profile == "strong_founder" and index == 0:
                charisma = self.rng.uniform(0.88, 1.0)
            else:
                charisma = self.rng.betavariate(2.0, 5.0)

            people.append(
                Person(
                    id=f"p{index:03d}",
                    name=self.rng.choice(NAMES),
                    age=age,
                    charisma=charisma,
                    food_skill=self.rng.uniform(0.2, 1.0),
                    sex=self.rng.choice(["f", "m"]),
                    interpretation_bias=self._new_interpretation_bias(),
                    action=self.rng.choice(ACTIONS),
                )
            )
        return people

    def _new_interpretation_bias(self) -> dict[str, float]:
        return {
            "spiritual": self._clamp(0.10 + self.rng.uniform(-0.05, 0.05)),
            "practical": self._clamp(0.10 + self.rng.uniform(-0.05, 0.05)),
            "blame": self._clamp(0.10 + self.rng.uniform(-0.05, 0.05)),
        }

    def _initialize_trust_network(self) -> None:
        ids = [person.id for person in self.people]
        for person in self.people:
            others = [person_id for person_id in ids if person_id != person.id]
            connection_count = min(len(others), self.rng.randint(3, 6))
            for other_id in self.rng.sample(others, connection_count):
                other = self._person(other_id)
                age_gap = abs(person.age - other.age)
                proximity = max(0.0, 1.0 - age_gap / 70.0)
                value = 0.25 + proximity * 0.35 + self.rng.uniform(0.0, 0.35)
                person.trust[other_id] = self._clamp(value)

    def _person(self, person_id: str) -> Person:
        for person in self.people:
            if person.id == person_id:
                return person
        raise KeyError(person_id)

    def _clamp(self, value: float) -> float:
        return max(0.0, min(1.0, value))

    def _assign_interpretation(self, person: Person, event: str) -> str:
        context = {
            "spiritual": person.interpretation_bias.get("spiritual", 0.0),
            "practical": person.interpretation_bias.get("practical", 0.0),
            "blame": person.interpretation_bias.get("blame", 0.0),
        }
        context["spiritual"] += person.fear * 0.08
        if event in {"food_shortage", "death"} or event.startswith("project_failure"):
            context["blame"] += min(0.10, self.log.count("problem_detected") * 0.004)
        if event.startswith("project_success"):
            context["practical"] += 0.04
        if "hold_ritual" in event:
            context["spiritual"] += 0.04

        total = sum(context.values())
        if total < 0.25:
            return "none"
        interpretations = list(context.keys())
        weights = [context[key] for key in interpretations]
        return self.rng.choices(interpretations, weights=weights)[0]

    def _update_bias_from_experience(self, person: Person, interpretation: str) -> None:
        if interpretation == "none":
            return
        person.interpretation_bias[interpretation] = min(
            1.0,
            person.interpretation_bias.get(interpretation, 0.0) + 0.015,
        )

    def _make_memory(
        self,
        person: Person,
        event: str,
        intensity: float,
        source: str = "self",
        generation: int = 0,
        decay_rate: float = 0.02,
    ) -> Memory:
        interpretation = self._assign_interpretation(person, event)
        self._update_bias_from_experience(person, interpretation)
        return Memory(
            event=event,
            year=self.year,
            intensity=self._clamp(intensity),
            decay_rate=decay_rate,
            source=source,
            generation=generation,
            interpretation=interpretation,
        )

    def run(self, years: int = 80) -> None:
        for _ in range(years):
            if self.population == 0:
                break
            self.step()

    def step(self) -> None:
        self.year += 1
        self.current_problems = []
        self.current_proposals = []
        self._resource_phase()
        self._problem_phase()
        self._council_phase()
        self._dialogue_phase()
        self._action_phase()
        self._update_phase()
        self._generation_phase()
        self._detect_patterns()

    def _resource_phase(self) -> None:
        alive = self.alive_people
        adult_workers = sum(
            1 for person in alive
            if person.age >= 15 and person.health >= 0.45 and person.hunger < 0.85
        )
        youth_helpers = sum(
            1 for person in alive
            if 10 <= person.age < 15 and person.health >= 0.50
        )
        harvest_factor = self.rng.uniform(0.8, 1.15)
        if self.rng.random() < 0.07:
            harvest_factor = self.rng.uniform(0.25, 0.55)
        labor_capacity = adult_workers * 1.25 + youth_helpers * 0.25
        production_capacity = min(
            self.food.capacity * 1.35,
            max(self.food.capacity * 0.75, labor_capacity),
        )
        produced = production_capacity * harvest_factor
        consumed = sum(person.consumption() for person in alive)
        self.food.stock *= 0.96
        self.food.stock += produced - consumed

        if self.food.stock >= 0:
            for person in alive:
                person.hunger = self._clamp(person.hunger * 0.82)
            return

        shortage = abs(self.food.stock)
        self.food.stock = 0.0
        intensity = self._clamp(shortage / max(1.0, len(alive)))
        affected = self.rng.sample(alive, max(1, int(len(alive) * min(0.8, 0.25 + intensity))))
        self.log.record(
            self.year,
            "crisis",
            [person.id for person in affected],
            f"food shortage intensity={intensity:.2f}",
        )
        self._add_problem("food_shortage", intensity)
        for person in affected:
            person.hunger = self._clamp(person.hunger + 0.25 + intensity * 0.45)
            person.fear = self._clamp(person.fear + 0.18 + intensity * 0.40)
            person.remember(
                self._make_memory(
                    person,
                    event="food_shortage",
                    intensity=0.45 + intensity * 0.55,
                )
            )
            if person.fear >= 0.6:
                self.log.record(
                    self.year,
                    "fear_spike",
                    [person.id],
                    f"{person.name} fear={person.fear:.2f}",
                )

    def _problem_phase(self) -> None:
        if self.rng.random() < 0.10:
            self._add_problem("water_shortage", self.rng.uniform(0.25, 0.80))
        if self.rng.random() < 0.06:
            self._add_problem("storage_damage", self.rng.uniform(0.20, 0.65))

    def _add_problem(self, problem_type: str, severity: float) -> None:
        if any(problem.type == problem_type for problem in self.current_problems):
            return
        problem = Problem(problem_type, self.year, self._clamp(severity))
        self.current_problems.append(problem)
        self.log.record(
            self.year,
            "problem_detected",
            [],
            f"{problem.type} severity={problem.severity:.2f}",
        )

    def _council_phase(self) -> None:
        if not self.current_problems and self._avg("fear") < 0.35:
            return

        problems = self.current_problems or [
            Problem("general_anxiety", self.year, self._avg("fear"))
        ]
        self.log.record(
            self.year,
            "council_formed",
            [],
            f"council_formed: problems={','.join(problem.type for problem in problems)}",
        )

        for problem in problems:
            proposals = self._make_proposals(problem)
            self.current_proposals.extend(proposals)
            for proposal in proposals:
                proposer = self._person(proposal.proposer_id)
                spoke_at_crisis = problem.severity >= 0.45 or self._avg("fear") >= 0.35
                if proposer.fear > 0.5 and spoke_at_crisis:
                    proposer.voice_weight = self._clamp(proposer.voice_weight + 0.02)
                self.log.record(
                    self.year,
                    "proposal_made",
                    [proposal.proposer_id],
                    (
                        f"{proposer.name} proposed {proposal.action} "
                        f"for {proposal.target_problem}"
                    ),
                )
            self._support_proposals(problem, proposals)
            self._detect_faction_pattern(problem, proposals)
            for proposal in proposals:
                threshold = max(4, int(self.population * 0.22))
                if len(proposal.support_ids) >= threshold:
                    self._execute_project(problem, proposal)

    def _make_proposals(self, problem: Problem) -> list[Proposal]:
        adults = [person for person in self.alive_people if person.age >= 15]
        if not adults:
            return []
        candidates = sorted(
            adults,
            key=lambda person: self._proposal_score(person),
            reverse=True,
        )
        proposal_count = min(len(candidates), self.rng.randint(1, 3))
        selected = self.rng.sample(candidates[: min(len(candidates), 8)], proposal_count)
        proposals = []
        used_actions: set[str] = set()
        for proposer in selected:
            action = self._choose_project_action(problem, proposer, used_actions)
            used_actions.add(action)
            proposals.append(
                Proposal(
                    proposer_id=proposer.id,
                    action=action,
                    target_problem=problem.type,
                )
            )
        return proposals

    def _proposal_score(self, person: Person) -> float:
        incoming_trust = self._incoming_trust(person.id)
        return (
            person.charisma * 0.35
            + person.food_skill * 0.25
            + incoming_trust * 0.26
            + person.voice_weight * 0.04
            + person.fear * 0.10
        )

    def _incoming_trust(self, person_id: str) -> float:
        values = [
            person.trust[person_id]
            for person in self.alive_people
            if person_id in person.trust
        ]
        return sum(values) / len(values) if values else 0.0

    def _choose_project_action(
        self, problem: Problem, proposer: Person, used_actions: set[str]
    ) -> str:
        if problem.type == "food_shortage":
            weighted = [
                ("store_food", 4),
                ("hunt_group", 4),
                ("move_camp", 2),
                ("hold_ritual", 1),
            ]
        elif problem.type == "water_shortage":
            weighted = [
                ("dig_well", 5),
                ("move_camp", 3),
                ("hold_ritual", 2),
                ("store_food", 1),
            ]
        elif problem.type == "storage_damage":
            weighted = [
                ("store_food", 5),
                ("hunt_group", 2),
                ("hold_ritual", 1),
                ("move_camp", 1),
            ]
        else:
            weighted = [
                ("hold_ritual", 3),
                ("store_food", 2),
                ("dig_well", 1),
                ("hunt_group", 1),
                ("move_camp", 1),
            ]
        actions = [action for action, _ in weighted]
        weights = [weight for action, weight in weighted]
        interpretation = self._recent_interpretation_for_problem(proposer, problem)
        if interpretation != "none":
            adjusted = []
            nudged = False
            for action, weight in zip(actions, weights):
                bonus = self._interpretation_action_nudge(interpretation, action)
                adjusted.append(weight * (1.0 + bonus))
                nudged = nudged or bonus > 0.0
            weights = adjusted
            if nudged:
                self.interpretation_action_nudge_count += 1
        if proposer.charisma > 0.75:
            weights = [
                weight + (2 if action == "hold_ritual" else 0)
                for action, weight in zip(actions, weights)
            ]
        for _ in range(6):
            action = self.rng.choices(actions, weights=weights)[0]
            if action not in used_actions:
                return action
        return self.rng.choice(PROJECT_ACTIONS)

    def _support_proposals(self, problem: Problem, proposals: list[Proposal]) -> None:
        if not proposals:
            return
        for person in self.alive_people:
            if person.age < 10:
                continue
            scored = []
            for proposal in proposals:
                proposer = self._person(proposal.proposer_id)
                trust = person.trust.get(proposer.id, 0.15)
                score = (
                    trust * 0.43
                    + proposer.charisma * 0.24
                    + proposer.voice_weight * 0.08
                    + self._project_relevance(problem, proposal, proposer) * 0.20
                    + person.fear * 0.10
                    + self.rng.uniform(-0.08, 0.08)
                )
                support_nudge = self._interpretation_support_nudge(
                    person, problem, proposal, proposer
                )
                score += support_nudge
                scored.append((score, proposal, support_nudge))
            score, proposal, support_nudge = max(scored, key=lambda item: item[0])
            if support_nudge != 0.0:
                self.interpretation_support_nudge_count += 1
            support_chance = self._clamp(0.12 + score * 0.42 + person.fear * 0.15)
            if self.rng.random() > support_chance:
                continue
            proposal.support_ids.append(person.id)
            self.proposal_support_by_person[proposal.proposer_id] = (
                self.proposal_support_by_person.get(proposal.proposer_id, 0) + 1
            )
            self.log.record(
                self.year,
                "proposal_supported",
                [person.id, proposal.proposer_id],
                f"{person.name} supported {proposal.action}",
            )

    def _project_relevance(
        self, problem: Problem, proposal: Proposal, proposer: Person
    ) -> float:
        if proposal.action in {"store_food", "hunt_group"}:
            return proposer.food_skill
        if proposal.action == "dig_well":
            return (proposer.food_skill + proposer.charisma) / 2
        if proposal.action == "hold_ritual":
            return proposer.charisma
        if proposal.action == "move_camp":
            return (proposer.health + proposer.charisma) / 2
        return 0.4

    def _recent_interpretation_for_problem(
        self, person: Person, problem: Problem
    ) -> str:
        matching = [
            memory
            for memory in person.memories
            if memory.interpretation != "none"
            and memory.intensity >= 0.20
            and self._memory_matches_problem(memory, problem)
        ]
        if not matching:
            return self._dominant_interpretation_bias(person)
        strongest = max(matching, key=lambda memory: memory.intensity)
        return strongest.interpretation

    def _memory_matches_problem(self, memory: Memory, problem: Problem) -> bool:
        if memory.event == problem.type:
            return True
        if problem.type == "general_anxiety":
            return memory.event in {"food_shortage", "death"} or memory.event.startswith(
                "project_failure"
            )
        return False

    def _dominant_interpretation_bias(self, person: Person) -> str:
        if not person.interpretation_bias:
            return "none"
        dominant = max(person.interpretation_bias, key=person.interpretation_bias.get)
        if person.interpretation_bias.get(dominant, 0.0) < 0.16:
            return "none"
        return dominant

    def _interpretation_action_nudge(self, interpretation: str, action: str) -> float:
        practical_actions = {"store_food", "dig_well", "hunt_group"}
        if interpretation == "spiritual" and action == "hold_ritual":
            return 0.03
        if interpretation == "practical" and action in practical_actions:
            return 0.03
        if interpretation == "blame" and action == "move_camp":
            return 0.03
        return 0.0

    def _interpretation_support_nudge(
        self,
        person: Person,
        problem: Problem,
        proposal: Proposal,
        proposer: Person,
    ) -> float:
        interpretation = self._recent_interpretation_for_problem(person, problem)
        if interpretation == "none":
            return 0.0
        if interpretation in {"spiritual", "practical"}:
            return self._interpretation_action_nudge(interpretation, proposal.action)
        if interpretation == "blame":
            if proposer.voice_weight >= 0.08:
                return -0.03
            return 0.03
        return 0.0

    def _execute_project(self, problem: Problem, proposal: Proposal) -> None:
        proposer = self._person(proposal.proposer_id)
        supporters = [
            self._person(person_id)
            for person_id in proposal.support_ids
            if self._person(person_id).alive
        ]
        if not supporters:
            return
        self.log.record(
            self.year,
            "project_started",
            [proposal.proposer_id] + proposal.support_ids,
            (
                f"project_started: {proposal.action} for {problem.type} "
                f"supporters={len(supporters)}"
            ),
        )

        support_factor = len(supporters) / max(1, self.population)
        avg_health = sum(person.health for person in supporters) / len(supporters)
        skill = self._project_relevance(problem, proposal, proposer)
        success_chance = self._clamp(
            0.12
            + support_factor * 0.38
            + skill * 0.25
            + avg_health * 0.22
            - problem.severity * 0.20
            + self.rng.uniform(-0.12, 0.12)
        )
        success = self.rng.random() < success_chance
        event = "project_success" if success else "project_failure"
        self.log.record(
            self.year,
            event,
            [proposal.proposer_id] + proposal.support_ids,
            (
                f"{event}: {proposal.action} for {problem.type} "
                f"chance={success_chance:.2f}"
            ),
        )
        if success:
            self.project_success_by_person[proposal.proposer_id] = (
                self.project_success_by_person.get(proposal.proposer_id, 0) + 1
            )
            proposer.voice_weight = self._clamp(proposer.voice_weight + 0.04)
            if proposal.action == "hold_ritual":
                self.ritual_success_count += 1
            self._apply_project_success(problem, proposal, proposer, supporters)
        else:
            self.project_failure_by_person[proposal.proposer_id] = (
                self.project_failure_by_person.get(proposal.proposer_id, 0) + 1
            )
            self._apply_project_failure(problem, proposal, proposer, supporters)
        self._detect_project_authority(proposer)

    def _apply_project_success(
        self,
        problem: Problem,
        proposal: Proposal,
        proposer: Person,
        supporters: list[Person],
    ) -> None:
        for supporter in supporters:
            self._adjust_trust(supporter, proposer.id, 0.055)
            supporter.fear = self._clamp(supporter.fear - 0.10)
            supporter.hunger = self._clamp(supporter.hunger - 0.08)
            supporter.remember(
                self._make_memory(
                    supporter,
                    event=f"project_success:{proposal.action}",
                    intensity=0.55 + self.rng.uniform(0.0, 0.25),
                )
            )
        for left in supporters[:12]:
            for right in self.rng.sample(supporters, min(3, len(supporters))):
                if left.id != right.id:
                    self._adjust_trust(left, right.id, 0.012)
        if proposal.action in {"store_food", "hunt_group"}:
            self.food.stock += len(supporters) * self.rng.uniform(0.25, 0.65)
        elif proposal.action == "dig_well":
            self.food.capacity *= 1.0 + min(0.08, 0.01 + len(supporters) / 900)
        elif proposal.action == "hold_ritual":
            for supporter in supporters:
                supporter.fear = self._clamp(supporter.fear - 0.08)
        elif proposal.action == "move_camp":
            self.food.stock *= 0.85
            for supporter in supporters:
                supporter.hunger = self._clamp(supporter.hunger - 0.12)

    def _apply_project_failure(
        self,
        problem: Problem,
        proposal: Proposal,
        proposer: Person,
        supporters: list[Person],
    ) -> None:
        for supporter in supporters:
            self._adjust_trust(supporter, proposer.id, -0.045)
            supporter.fear = self._clamp(supporter.fear + 0.08 + problem.severity * 0.08)
            supporter.remember(
                self._make_memory(
                    supporter,
                    event=f"project_failure:{proposal.action}",
                    intensity=0.45 + problem.severity * 0.35,
                )
            )

    def _detect_project_authority(self, proposer: Person) -> None:
        successes = self.project_success_by_person.get(proposer.id, 0)
        supports = self.proposal_support_by_person.get(proposer.id, 0)
        if successes >= 3 or (
            successes >= 2 and supports >= max(18, int(self.population * 0.65))
        ):
            if self._can_detect("authority_pattern", proposer.id, cooldown=4):
                self.log.record(
                    self.year,
                    "authority_pattern",
                    [proposer.id],
                    (
                        f"authority_pattern: {proposer.name} repeated support/success "
                        f"successes={successes} supports={supports}"
                    ),
                )

    def _detect_faction_pattern(
        self, problem: Problem, proposals: list[Proposal]
    ) -> None:
        viable = [
            proposal for proposal in proposals
            if len(proposal.support_ids) >= max(4, int(self.population * 0.22))
        ]
        if len(viable) < 2:
            return
        sizes = sorted((len(proposal.support_ids) for proposal in viable), reverse=True)
        if sizes[1] >= sizes[0] * 0.55:
            key = f"{problem.type}:{'-'.join(str(size) for size in sizes[:3])}"
            if self._can_detect("faction_pattern", key, cooldown=5):
                self.log.record(
                    self.year,
                    "faction_pattern",
                    [],
                    f"faction_pattern: {problem.type} support groups {sizes[:3]}",
                )

    def _dialogue_phase(self) -> None:
        for speaker in self.alive_people:
            memory = speaker.strongest_memory()
            if memory is None:
                continue
            share_probability = (
                0.05
                + memory.intensity * 0.18
                + speaker.fear * 0.15
                + (0.12 if speaker.action == "share_memory" else 0.0)
            )
            if memory.generation >= 4:
                share_probability *= 0.55
            if self.rng.random() > min(0.55, share_probability):
                continue
            listener_count = 2 if self.rng.random() < 0.10 + speaker.fear * 0.20 else 1
            listeners = [
                self._person(person_id)
                for person_id in speaker.top_trusted(listener_count)
                if self._person(person_id).alive
            ]
            for listener in listeners:
                distorted = self._distort_memory(memory, speaker, listener)
                listener.remember(distorted)
                self.log.record(
                    self.year,
                    "memory_shared",
                    [speaker.id, listener.id],
                    (
                        f"{speaker.name} told {listener.name} about "
                        f"{distorted.event} intensity={distorted.intensity:.2f} "
                        f"generation={distorted.generation}"
                    ),
                )
                self._adjust_trust(listener, speaker.id, 0.012)

    def _distort_memory(self, memory: Memory, speaker: Person, listener: Person) -> Memory:
        noise_scale = self.rng.uniform(0.10, 0.20)
        noise = self.rng.uniform(-noise_scale, noise_scale)
        fear_bias = speaker.fear * 0.10
        generation_bias = memory.generation * self.rng.uniform(-0.04, 0.06)
        interpretation = memory.interpretation
        if interpretation != "none" and self.rng.random() < 0.12:
            interpretation = self._assign_interpretation(listener, memory.event)
        return Memory(
            event=memory.event,
            year=memory.year,
            intensity=self._clamp(memory.intensity * (1.0 + noise) + fear_bias + generation_bias),
            decay_rate=memory.decay_rate,
            source=speaker.id,
            generation=memory.generation + 1,
            interpretation=interpretation,
        )

    def _action_phase(self) -> None:
        copied_by: dict[str, int] = {}
        for person in self.alive_people:
            if person.fear < 0.7 or not person.trust:
                self._choose_independent_action(person)
                continue
            target_id = person.top_trusted(1)[0]
            target = self._person(target_id)
            if not target.alive:
                continue
            old_action = person.action
            person.action = target.action
            copied_by[target.id] = copied_by.get(target.id, 0) + 1
            self._adjust_trust(person, target.id, 0.025)
            self.log.record(
                self.year,
                "behavior_copied",
                [person.id, target.id],
                f"{person.name} copied {target.name}: {old_action} -> {person.action}",
            )

        for target_id, count in copied_by.items():
            if count >= 3:
                target = self._person(target_id)
                if self._can_detect("authority_pattern", target_id, cooldown=3):
                    self.log.record(
                        self.year,
                        "authority_pattern",
                        [target_id],
                        f"authority_pattern: {target.name} copied by {count} persons",
                    )

    def _choose_independent_action(self, person: Person) -> None:
        everyday_actions = (
            "store_food",
            "ask_help",
            "share_memory",
            "reassure",
            "withdraw",
        )
        if person.hunger > 0.65:
            weights = [45, 25, 10, 5, 15]
        elif person.fear > 0.45:
            weights = [20, 20, 25, 20, 15]
        else:
            weights = [20, 15, 25, 25, 15]
        person.action = self.rng.choices(everyday_actions, weights=weights)[0]

    def _update_phase(self) -> None:
        for person in self.alive_people:
            person.age += 1
            person.voice_weight = self._clamp(person.voice_weight * 0.97)
            person.fear = self._clamp(person.fear * 0.86)
            if person.hunger > 0.75:
                person.health = self._clamp(person.health - 0.045 * person.hunger)
            else:
                person.health = self._clamp(person.health + 0.02)
            person.hunger = self._clamp(person.hunger * 0.92)

            for memory in person.memories:
                memory.decay()
            person.memories = [
                memory for memory in person.memories
                if memory.intensity >= 0.05
            ]

            age_risk = max(0.0, (person.age - 76) / 95.0)
            health_risk = max(0.0, 0.25 - person.health) * 0.22
            if self.rng.random() < age_risk + health_risk:
                person.alive = False
                self.log.record(
                    self.year,
                    "death",
                    [person.id],
                    f"{person.name} died age={person.age} health={person.health:.2f}",
                )
                for other in self.alive_people:
                    if person.id in other.trust:
                        other.remember(
                            self._make_memory(
                                other,
                                event="death",
                                intensity=0.35 + other.trust[person.id] * 0.45,
                            )
                        )

    def _generation_phase(self) -> None:
        adults = [person for person in self.alive_people if person.age >= 18]
        candidates = [person for person in self.alive_people if person.can_give_birth()]
        if len(adults) < 2 or not candidates:
            return

        food_per_person = self.food.stock / max(1, self.population)
        food_factor = min(1.25, max(0.25, food_per_person / 3.0))
        fear_factor = max(0.35, 1.0 - self._avg("fear") * 0.75)
        population_factor = max(0.05, 1.0 - max(0, self.population - 35) / 45.0)

        birth_count = 0
        for parent in candidates:
            # Rough pre-modern annual birth probability per adult woman.
            chance = 0.075 * food_factor * fear_factor * population_factor
            if self.rng.random() > min(0.14, chance):
                continue
            child = self._create_child(parent)
            self.people.append(child)
            birth_count += 1
            self.log.record(
                self.year,
                "birth",
                [parent.id, child.id],
                f"{parent.name} had a child: {child.name}",
            )

        if birth_count:
            self.food.stock = max(0.0, self.food.stock - birth_count * 0.4)

    def _create_child(self, parent: Person) -> Person:
        child = Person(
            id=f"p{self.next_person_index:03d}",
            name=self.rng.choice(NAMES),
            age=0,
            charisma=self.rng.betavariate(2.0, 5.0),
            food_skill=self.rng.uniform(0.2, 1.0),
            sex=self.rng.choice(["f", "m"]),
            interpretation_bias=self._new_interpretation_bias(),
            action="ask_help",
        )
        self.next_person_index += 1

        child.trust[parent.id] = 0.85
        parent.trust[child.id] = 0.85
        for person_id in parent.top_trusted(2):
            if person_id == child.id or not self._person(person_id).alive:
                continue
            child.trust[person_id] = self.rng.uniform(0.35, 0.55)
            self._person(person_id).trust[child.id] = self.rng.uniform(0.20, 0.45)

        return child

    def _adjust_trust(self, person: Person, other_id: str, delta: float) -> None:
        before = person.trust.get(other_id, 0.0)
        after = self._clamp(before + delta)
        person.trust[other_id] = after
        if abs(after - before) >= 0.08:
            self.log.record(
                self.year,
                "trust_changed",
                [person.id, other_id],
                f"trust {before:.2f} -> {after:.2f}",
            )

    def _detect_patterns(self) -> None:
        self._detect_shared_narrative()
        self._detect_network_split()
        self._detect_narrative_divergence()
        self._detect_interpretation_divergence()
        self._detect_interpretation_convergence()
        self._detect_ritualization_pattern()

    def _can_detect(self, event_type: str, key: str, cooldown: int = 5) -> bool:
        detection_key = (event_type, key)
        last_year = self.last_detection.get(detection_key)
        if last_year is not None and self.year - last_year < cooldown:
            return False
        self.last_detection[detection_key] = self.year
        return True

    def _detect_shared_narrative(self) -> None:
        event_to_people: dict[str, list[tuple[Person, float]]] = {}
        for person in self.alive_people:
            strongest_by_event: dict[str, float] = {}
            for memory in person.memories:
                strongest_by_event[memory.event] = max(
                    strongest_by_event.get(memory.event, 0.0),
                    memory.intensity,
                )
            for event, intensity in strongest_by_event.items():
                if intensity >= 0.30:
                    event_to_people.setdefault(event, []).append((person, intensity))

        for event, holders in event_to_people.items():
            threshold = max(6, int(self.population * 0.35))
            if len(holders) < threshold:
                continue
            avg_intensity = sum(intensity for _, intensity in holders) / len(holders)
            if self._can_detect("shared_narrative", event, cooldown=5):
                self.log.record(
                    self.year,
                    "shared_narrative",
                    [person.id for person, _ in holders],
                    (
                        f"shared_narrative detected: {event}, "
                        f"{len(holders)} persons, avg_intensity {avg_intensity:.2f}"
                    ),
                )

    def _detect_network_split(self) -> None:
        people = self.alive_people
        if len(people) < 8:
            return
        ids = {person.id for person in people}
        neighbors = {person.id: set() for person in people}
        for person in people:
            for other_id, trust in person.trust.items():
                if other_id in ids and trust >= 0.55:
                    neighbors[person.id].add(other_id)
                    neighbors[other_id].add(person.id)

        clusters = []
        seen: set[str] = set()
        for person_id in ids:
            if person_id in seen:
                continue
            stack = [person_id]
            seen.add(person_id)
            cluster = []
            while stack:
                current = stack.pop()
                cluster.append(current)
                for other_id in neighbors[current]:
                    if other_id not in seen:
                        seen.add(other_id)
                        stack.append(other_id)
            clusters.append(cluster)

        major_clusters = sorted(
            [cluster for cluster in clusters if len(cluster) >= 4],
            key=len,
            reverse=True,
        )
        if len(major_clusters) >= 2:
            sizes = [len(cluster) for cluster in major_clusters[:4]]
            cluster_key = "-".join(str(size) for size in sizes)
            if self._can_detect("network_split", cluster_key, cooldown=5):
                self.log.record(
                    self.year,
                    "network_split",
                    [],
                    f"network_split detected: cluster sizes {sizes}",
                )

    def _detect_narrative_divergence(self) -> None:
        intensities_by_event: dict[str, list[float]] = {}
        for person in self.alive_people:
            for memory in person.memories:
                if memory.intensity >= 0.20:
                    intensities_by_event.setdefault(memory.event, []).append(memory.intensity)

        for event, intensities in intensities_by_event.items():
            if len(intensities) < 8:
                continue
            low = [value for value in intensities if value <= 0.40]
            high = [value for value in intensities if value >= 0.70]
            if len(low) >= 3 and len(high) >= 3:
                low_avg = sum(low) / len(low)
                high_avg = sum(high) / len(high)
                if self._can_detect("narrative_divergence", event, cooldown=5):
                    self.log.record(
                        self.year,
                        "narrative_divergence",
                        [],
                        (
                            f"narrative_divergence: {event}, "
                            f"versions {low_avg:.2f} vs {high_avg:.2f}"
                        ),
                    )

    def _detect_ritualization_pattern(self) -> None:
        if self.ritual_success_count < 2:
            return
        holders = []
        spiritual_holders = 0
        for person in self.alive_people:
            ritual_memories = [
                memory for memory in person.memories
                if memory.event == "project_success:hold_ritual"
                and memory.intensity >= 0.25
            ]
            if ritual_memories:
                holders.append(person)
                if any(memory.interpretation == "spiritual" for memory in ritual_memories):
                    spiritual_holders += 1
        if len(holders) < max(5, int(self.population * 0.20)):
            return
        if self._can_detect("ritualization_pattern", "hold_ritual", cooldown=8):
            spiritual_rate = spiritual_holders / max(1, len(holders))
            self.log.record(
                self.year,
                "ritualization_pattern",
                [person.id for person in holders],
                (
                    f"ritualization_pattern: hold_ritual success memory "
                    f"held by {len(holders)} persons spiritual_rate={spiritual_rate:.2f}"
                ),
            )

    def _detect_interpretation_divergence(self) -> None:
        event_to_interpretations: dict[str, dict[str, int]] = {}
        for person in self.alive_people:
            seen_by_event: set[tuple[str, str]] = set()
            for memory in person.memories:
                if memory.intensity < 0.25 or memory.interpretation == "none":
                    continue
                key = (memory.event, memory.interpretation)
                if key in seen_by_event:
                    continue
                seen_by_event.add(key)
                counter = event_to_interpretations.setdefault(memory.event, {})
                counter[memory.interpretation] = counter.get(memory.interpretation, 0) + 1

        for event, counter in event_to_interpretations.items():
            threshold = max(10, int(self.population * 0.40))
            active = {
                interpretation: count
                for interpretation, count in counter.items()
                if count >= threshold
            }
            if len(active) >= 3 and self._can_detect(
                "interpretation_divergence", event, cooldown=5
            ):
                self.log.record(
                    self.year,
                    "interpretation_divergence",
                    [],
                    f"interpretation_divergence: {event} -> {active}",
                )

    def _detect_interpretation_convergence(self) -> None:
        if self.population == 0:
            return
        bias_totals = {
            "spiritual": 0.0,
            "practical": 0.0,
            "blame": 0.0,
        }
        for person in self.alive_people:
            for key in bias_totals:
                bias_totals[key] += person.interpretation_bias.get(key, 0.0)
        dominant = max(bias_totals, key=lambda key: bias_totals[key])
        dominant_avg = bias_totals[dominant] / self.population
        if dominant_avg >= 0.35 and self._can_detect(
            "interpretation_convergence", dominant, cooldown=8
        ):
            self.log.record(
                self.year,
                "interpretation_convergence",
                [],
                f"interpretation_convergence: {dominant} avg_bias={dominant_avg:.3f}",
            )

    def summary(self) -> dict[str, object]:
        return {
            "seed": self.seed,
            "years": self.year,
            "initial_population": self.initial_population,
            "final_population": self.population,
            "age_profile": self.age_profile,
            "charisma_profile": self.charisma_profile,
            "initial_food_stock": round(self.initial_food_stock, 3),
            "initial_food_capacity": round(self.initial_food_capacity, 3),
            "final_food_stock": round(self.food.stock, 3),
            "avg_fear": round(self._avg("fear"), 3),
            "avg_hunger": round(self._avg("hunger"), 3),
            "avg_voice_weight": round(self._avg("voice_weight"), 3),
            "max_voice_weight": round(self._max("voice_weight"), 3),
            "crisis_count": self.log.count("crisis"),
            "problem_count": self.log.count("problem_detected"),
            "council_count": self.log.count("council_formed"),
            "proposal_count": self.log.count("proposal_made"),
            "project_success_count": self.log.count("project_success"),
            "project_failure_count": self.log.count("project_failure"),
            "shared_narrative_count": self.log.count("shared_narrative"),
            "authority_pattern_count": self.log.count("authority_pattern"),
            "faction_pattern_count": self.log.count("faction_pattern"),
            "ritualization_pattern_count": self.log.count("ritualization_pattern"),
            "network_split_count": self.log.count("network_split"),
            "narrative_divergence_count": self.log.count("narrative_divergence"),
            "interpretation_divergence_count": self.log.count("interpretation_divergence"),
            "interpretation_convergence_count": self.log.count("interpretation_convergence"),
            "interpretation_action_nudge_count": self.interpretation_action_nudge_count,
            "interpretation_support_nudge_count": self.interpretation_support_nudge_count,
            "avg_bias_spiritual": round(self._avg_bias("spiritual"), 4),
            "avg_bias_practical": round(self._avg_bias("practical"), 4),
            "avg_bias_blame": round(self._avg_bias("blame"), 4),
            "death_count": self.log.count("death"),
            "birth_count": self.log.count("birth"),
            "memory_shared_count": self.log.count("memory_shared"),
            "behavior_copied_count": self.log.count("behavior_copied"),
        }

    def _avg(self, attr: str) -> float:
        people = self.alive_people
        if not people:
            return 0.0
        return sum(getattr(person, attr) for person in people) / len(people)

    def _max(self, attr: str) -> float:
        people = self.alive_people
        if not people:
            return 0.0
        return max(getattr(person, attr) for person in people)

    def _avg_bias(self, key: str) -> float:
        people = self.alive_people
        if not people:
            return 0.0
        return sum(person.interpretation_bias.get(key, 0.0) for person in people) / len(people)


def main() -> None:
    sim = SocietyLab(seed=42, verbose=True)
    sim.run(years=80)
    print("\nSummary")
    for key, value in sim.summary().items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
