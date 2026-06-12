"""
society_lab v1.4_life (shadow3)
================================

Observation-only life layer for society_lab v1.4_1.
shadow3: life observation RNG streams are separated by purpose.

This file must live next to society_lab_v1_4_1.py, or the directory containing
society_lab_v1_4_1.py must be on PYTHONPATH.

Design rule:
Do not change world dynamics. Tea-house observations use a separate deterministic
RNG stream and write only to life_observations. They do not affect food, health,
trust, memory, support, births, deaths, proposals, project outcomes, or the main
ObservationLog.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from typing import Optional

from society_lab_v1_4_1 import SocietyLab


TEAS = (
    "sencha",
    "hojicha",
    "genmaicha",
    "black_tea",
    "barley_tea",
)

TEA_VESSELS = (
    "yunomi",
    "small_cup",
    "wooden_bowl",
)

VESSEL_CONDITIONS = (
    "plain",
    "plain",
    "plain",
    "plain",
    "chipped",
)

TEA_HOUSE_MOODS = (
    "quiet",
    "rainy",
    "windy",
    "warm",
)

# 世界側の空気。人物状態に依存しない。
WEATHER = (
    "clear",
    "overcast",
    "rain_on_roof",
    "dry_wind",
    "heavy_rain",
    "light_mist",
)

TIME_OF_DAY = (
    "cold_morning",
    "midday",
    "late_afternoon",
    "evening_steam",
)

FIRE_DETAIL = (
    "fire_going",
    "embers_only",
    "no_fire",
    "smoke_lingering",
)

# Object traces. No person, no intent, no causation.
OBJECT_TRACES = (
    "worn_threshold",
    "patched_roof",
    "stacked_firewood",
    "forgotten_cup",
    "muddy_footprints",
    "mended_basket",
    "cracked_vessel",
    "ash_pile",
)

TRACE_PLACES = (
    "tea_house",
    "storehouse",
    "well",
    "gate",
    "hearth",
    "path",
)

LIFE_PLACES = (
    "tea_house",
    "well",
    "storehouse",
    "hearth",
    "gate",
    "path",
)

AFFECT_OBJECTS = (
    "chipped_cup",
    "damp_sleeve",
    "warm_bowl",
    "old_cloth",
    "small_blanket",
    "cracked_ladle",
    "shared_umbrella",
    "burnt_rice_smell",
    "childs_wooden_spoon",
    "mended_sandal",
)

SCENTS_BY_PLACE = {
    "tea_house": (
        "boiled_barley",
        "smoke_in_cloth",
        "old_wood",
        "steam_from_cups",
    ),
    "well": (
        "wet_soil",
        "cold_stone",
        "rain_on_dust",
    ),
    "storehouse": (
        "old_straw",
        "dry_grain",
        "dust_in_sacks",
        "mended_rope",
    ),
    "hearth": (
        "ash_after_rain",
        "smoke_in_cloth",
        "burnt_rice_smell",
        "old_wood",
    ),
    "gate": (
        "wind_from_fields",
        "dry_grass",
        "rain_on_dust",
    ),
    "path": (
        "wet_soil",
        "dry_grass",
        "damp_straw",
        "wind_from_fields",
    ),
}

TOUCHES_BY_PLACE = {
    "tea_house": (
        "warm_bowl_in_hands",
        "rough_wood_against_palm",
        "straw_mat_under_knees",
        "steam_on_face",
    ),
    "well": (
        "cold_rope_in_hands",
        "wet_stone_under_fingers",
        "cold_mud_underfoot",
    ),
    "storehouse": (
        "rough_sackcloth",
        "small_splinter_in_palm",
        "dust_on_fingers",
    ),
    "hearth": (
        "warm_bowl_in_hands",
        "steam_on_face",
        "ash_on_sleeve",
        "straw_mat_under_knees",
    ),
    "gate": (
        "wind_on_neck",
        "rough_wood_against_palm",
        "small_stone_in_sandal",
    ),
    "path": (
        "cold_mud_underfoot",
        "wind_on_neck",
        "small_stone_in_sandal",
        "damp_sleeve_on_skin",
    ),
}

ANIMAL_PRESENCES = (
    "cat_near_doorway",
    "dog_sleeping_far_off",
    "birds_under_eaves",
    "cat_brushing_ankle",
)

# World gestures. No identified person. No cause given.
WORLD_GESTURES = (
    "someone_looked_up",
    "a_whisper_nearby",
    "eyes_from_doorway",
    "someone_stood_still",
    "nothing_moved",
    "nothing_moved",
)

# Distant social gestures. Two persons. No contact. No relationship stated.
# Only simultaneous presence + observable behaviour.
DISTANT_SOCIAL_GESTURES = (
    "laughed_at_the_same_time",
    "waved_from_a_distance",
    "looked_back_once",
    "smiled_toward_someone",
    "made_a_troubled_face_toward_someone",
    "almost_called_out",
    "waited_without_speaking",
)

# Conversation shadows. No quoted speech. No content beyond a trace category.
CONVERSATION_SHADOWS = (
    "a_few_words_exchanged",
    "shared_a_short_remark",
    "spoke_briefly",
    "commented_on_the_weather",
    "mentioned_the_road",
    "talked_near_the_fire",
    "said_almost_nothing",
)

MEMORY_SHADOWS = (
    "returned_after_brief_nearness",
    "paused_where_words_once_passed",
    "looked_toward_the_old_place",
    "stood_still_at_the_same_place",
    "left_before_speaking_again",
)

# Place-time shadows. No inner memory asserted.
# The person returned; the place had been seen before.
TIME_SHADOWS = (
    "returned_after_many_years",
    "old_place_under_same_weather",
    "path_found_again",
    "long_absence_at_the_place",
    "years_laid_thinly_over_the_place",
)

# Person gestures. No emotion named. No cause given.
# The gesture happened. That is all.
PERSON_GESTURES = (
    "looked_at_the_sky",
    "whispered_to_no_one",
    "looked_away",
    "stood_at_the_threshold",
    "sat_without_moving",
    "turned_back_once",
    "held_still_a_moment",
    "did_not_go_in",
    "watched_the_fire",
    "put_something_down_slowly",
)

# Gestures that are more likely when fear is elevated.
PERSON_GESTURES_FEAR = (
    "looked_away",
    "did_not_go_in",
    "stood_at_the_threshold",
    "held_still_a_moment",
    "turned_back_once",
)

# Gestures that are more likely near death or grief memory years.
PERSON_GESTURES_WEIGHT = (
    "looked_at_the_sky",
    "looked_at_the_sky",
    "whispered_to_no_one",
    "sat_without_moving",
    "put_something_down_slowly",
)

# Sounds. No source, no person, no direction given.
SOUNDS = (
    "wind_through_thatch",
    "distant_rain",
    "someone_grinding",
    "fire_crackling",
    "distant_axe",
    "wind_through_grass",
    "child_somewhere",
    "birds_before_rain",
    "dog_far_off",
    "rain_on_thatch",
    "silence",
    "water_moving",
    "wood_settling",
    "wood_splitting",
    "something_dropped",
    "footsteps_leaving",
    "nothing",
    "nothing",
    "nothing",
)


# Ambient scaffolding. These are observation-only cultural traces.
# They do not create relationships, trust, support, or main memories.
AMBIENT_OBJECTS = (
    "warm_blanket",
    "needle",
    "thread_spool",
    "loom",
    "wooden_box",
    "old_book",
    "borrowed_book",
    "basket",
    "lantern",
    "paper_lantern",
    "wind_bell",
    "water_bucket",
    "fan",
    "festival_mask",
    "drum_stick",
    "small_drum",
    "watermelon_slice",
    "shaved_ice_bowl",
)

AMBIENT_SCENTS = (
    "summer_grass",
    "festival_smoke",
    "river_water",
    "old_paper",
    "ink",
    "fresh_rice",
    "harvest_field",
    "wet_cloth",
    "wood_shavings",
    "loom_dust",
)

AMBIENT_SOUNDS = (
    "loom_clicking",
    "distant_drum",
    "festival_noise",
    "wind_bell_sound",
    "pages_turning",
    "needle_against_cloth",
    "frogs_at_night",
    "water_from_spring",
    "children_running",
)

AMBIENT_PLACES = (
    "spring",
    "rice_field",
    "weaving_house",
    "book_house",
    "festival_square",
    "river_bank",
    "bridge",
    "shade_tree",
    "engawa",
    "watch_hill",
)

SEASONS = (
    "early_summer",
    "midsummer",
    "late_summer",
    "harvest_time",
    "cold_rain",
    "first_frost",
)

CROWD_MOODS = (
    "many_people_gathered",
    "music_somewhere",
    "festival_preparation",
    "shared_waiting",
    "crowd_nearby",
)




SEASON_AMBIENT_PLACE_WEIGHTS = {
    "early_summer": {
        "spring": 3.0,
        "rice_field": 2.4,
        "river_bank": 1.8,
        "shade_tree": 1.6,
        "engawa": 1.2,
    },
    "midsummer": {
        "festival_square": 3.2,
        "engawa": 2.4,
        "spring": 2.0,
        "river_bank": 1.8,
        "shade_tree": 1.5,
    },
    "late_summer": {
        "festival_square": 2.4,
        "rice_field": 2.1,
        "engawa": 1.8,
        "river_bank": 1.4,
    },
    "harvest_time": {
        "rice_field": 3.4,
        "weaving_house": 1.8,
        "book_house": 1.5,
        "engawa": 1.2,
    },
    "cold_rain": {
        "book_house": 3.0,
        "weaving_house": 2.4,
        "engawa": 2.0,
        "spring": 0.8,
    },
    "first_frost": {
        "book_house": 2.6,
        "weaving_house": 2.2,
        "engawa": 1.8,
        "spring": 0.7,
    },
}

SEASON_DETAIL_WEIGHTS = {
    "midsummer": {
        "festival_square": {
            "objects": {
                "paper_lantern": 3.0,
                "small_drum": 2.4,
                "drum_stick": 2.0,
                "festival_mask": 2.0,
                "watermelon_slice": 2.6,
                "shaved_ice_bowl": 2.6,
            },
            "scents": {
                "festival_smoke": 2.8,
                "summer_grass": 2.4,
                "sweet_shaved_ice": 2.8,
            },
            "sounds": {
                "distant_drum": 3.0,
                "festival_noise": 2.8,
                "wind_bell_sound": 2.0,
            },
            "scenes": {
                "many_people_gathered": 2.4,
                "lanterns_before_evening": 2.8,
                "festival_preparation_nearby": 2.8,
            },
        },
        "engawa": {
            "objects": {"wind_bell": 3.0, "fan": 2.4, "tea_cup_nearby": 1.6},
            "scents": {"cool_evening_air": 2.6, "summer_insects": 2.2},
            "sounds": {"wind_bell_sound": 3.0, "summer_insects": 2.4},
            "scenes": {"cool_evening_at_the_edge": 2.8, "shade_on_old_wood": 2.0},
        },
    },
    "late_summer": {
        "festival_square": {
            "objects": {"paper_lantern": 2.4, "wind_bell": 2.2, "watermelon_slice": 2.0},
            "scents": {"summer_grass": 2.2, "festival_smoke": 1.8},
            "sounds": {"wind_bell_sound": 2.4, "distant_drum": 2.0},
            "scenes": {"lanterns_before_evening": 2.4, "festival_preparation_nearby": 2.0},
        },
        "rice_field": {
            "objects": {"rice_heads_bending": 2.6, "golden_field": 2.2},
            "scents": {"harvest_smell": 2.2, "fresh_rice": 2.0},
            "sounds": {"frogs_at_night": 2.0, "wind_through_rice": 2.2},
            "scenes": {"golden_field_under_clouds": 2.2, "field_water_reflecting_sky": 1.8},
        },
    },
    "harvest_time": {
        "rice_field": {
            "objects": {
                "golden_field": 3.2,
                "rice_heads_bending": 3.0,
                "sickle": 2.2,
                "hoe": 2.0,
            },
            "scents": {"harvest_smell": 3.0, "fresh_rice": 2.6},
            "sounds": {"wind_through_rice": 2.6, "frogs_at_night": 1.8},
            "scenes": {"golden_field_under_clouds": 3.0, "field_water_reflecting_sky": 2.0},
        },
        "weaving_house": {
            "objects": {"thread_spool": 2.4, "unfinished_cloth": 2.4, "loom": 2.0},
            "scents": {"loom_dust": 2.2, "dry_reed": 2.0},
            "sounds": {"loom_clicking": 2.6, "thread_pulled_tight": 2.0},
            "scenes": {"cloth_half_finished": 2.4, "threads_hung_to_dry": 2.2},
        },
    },
    "cold_rain": {
        "book_house": {
            "objects": {"old_book": 3.0, "worn_pages": 2.8, "copied_text": 2.0},
            "scents": {"ink_smell": 3.0, "old_paper": 2.8},
            "sounds": {"pages_turning": 3.0, "quiet_reading": 2.6},
            "scenes": {"quiet_reading_corner": 3.0, "books_stacked_low": 2.4},
        },
        "weaving_house": {
            "objects": {"loom": 2.4, "thread_spool": 2.6, "unfinished_cloth": 2.6},
            "scents": {"loom_dust": 2.8, "old_thread": 2.2},
            "sounds": {"loom_clicking": 2.8, "needle_against_cloth": 2.4},
            "scenes": {"cloth_half_finished": 2.4, "hands_worked_somewhere_nearby": 2.0},
        },
    },
    "first_frost": {
        "book_house": {
            "objects": {"old_book": 2.8, "worn_pages": 2.8},
            "scents": {"old_paper": 2.8, "ink_smell": 2.2},
            "sounds": {"pages_turning": 2.6, "quiet_reading": 2.4},
            "scenes": {"quiet_reading_corner": 2.8, "copied_pages_drying": 2.0},
        },
        "weaving_house": {
            "objects": {"folded_cloth": 2.6, "thread_spool": 2.4, "needle": 2.0},
            "scents": {"loom_dust": 2.4, "dry_reed": 2.2},
            "sounds": {"loom_clicking": 2.4, "needle_against_cloth": 2.2},
            "scenes": {"threads_hung_to_dry": 2.4, "cloth_half_finished": 2.2},
        },
    },
    "early_summer": {
        "spring": {
            "objects": {
                "cold_water": 3.0,
                "mossy_stone": 2.6,
                "water_reflection": 2.6,
                "fern_near_water": 2.4,
            },
            "scents": {"cold_stream": 2.6, "wet_moss": 2.6, "clean_stone": 2.0},
            "sounds": {"spring_water_sound": 3.0, "water_from_spring": 2.6},
            "scenes": {
                "water_reflection_under_leaves": 3.0,
                "ferns_bent_near_water": 2.6,
                "stone_pool_in_shade": 2.2,
            },
        },
        "rice_field": {
            "objects": {"green_shoots": 3.0, "muddy_water": 2.4},
            "scents": {"wet_soil": 2.6, "fresh_rice": 1.8},
            "sounds": {"water_in_field_rows": 2.4, "frogs_at_night": 2.2},
            "scenes": {"green_shoots_after_rain": 3.0, "field_water_reflecting_sky": 2.2},
        },
    },
}

AMBIENT_PLACE_DETAILS = {
    "book_house": {
        "objects": (
            "old_book",
            "copied_text",
            "borrowed_book",
            "worn_pages",
        ),
        "scents": (
            "ink_smell",
            "old_paper",
            "dry_wood",
        ),
        "sounds": (
            "pages_turning",
            "quiet_reading",
            "brush_on_paper",
        ),
        "scenes": (
            "quiet_reading_corner",
            "books_stacked_low",
            "copied_pages_drying",
        ),
    },
    "weaving_house": {
        "objects": (
            "loom",
            "thread_spool",
            "unfinished_cloth",
            "needle",
            "folded_cloth",
        ),
        "scents": (
            "loom_dust",
            "old_thread",
            "dry_reed",
        ),
        "sounds": (
            "loom_clicking",
            "needle_against_cloth",
            "thread_pulled_tight",
        ),
        "scenes": (
            "cloth_half_finished",
            "threads_hung_to_dry",
            "hands_worked_somewhere_nearby",
        ),
    },
    "spring": {
        "objects": (
            "cold_water",
            "mossy_stone",
            "water_reflection",
            "wet_stone",
            "fern_near_water",
        ),
        "scents": (
            "cold_stream",
            "wet_moss",
            "clean_stone",
        ),
        "sounds": (
            "spring_water_sound",
            "water_from_spring",
            "small_stream_over_stones",
        ),
        "scenes": (
            "water_reflection_under_leaves",
            "stone_pool_in_shade",
            "ferns_bent_near_water",
        ),
    },
    "rice_field": {
        "objects": (
            "green_shoots",
            "golden_field",
            "muddy_water",
            "sickle",
            "hoe",
            "rice_heads_bending",
        ),
        "scents": (
            "harvest_smell",
            "wet_soil",
            "fresh_rice",
        ),
        "sounds": (
            "frogs_at_night",
            "wind_through_rice",
            "water_in_field_rows",
        ),
        "scenes": (
            "golden_field_under_clouds",
            "green_shoots_after_rain",
            "field_water_reflecting_sky",
        ),
    },
    "festival_square": {
        "objects": (
            "paper_lantern",
            "wind_bell",
            "small_drum",
            "drum_stick",
            "festival_mask",
            "watermelon_slice",
            "shaved_ice_bowl",
        ),
        "scents": (
            "festival_smoke",
            "summer_grass",
            "sweet_shaved_ice",
        ),
        "sounds": (
            "distant_drum",
            "festival_noise",
            "wind_bell_sound",
        ),
        "scenes": (
            "many_people_gathered",
            "lanterns_before_evening",
            "festival_preparation_nearby",
        ),
    },
    "engawa": {
        "objects": (
            "fan",
            "wind_bell",
            "old_wood_floor",
            "damp_sleeve",
            "tea_cup_nearby",
        ),
        "scents": (
            "cool_evening_air",
            "old_wood",
            "summer_insects",
        ),
        "sounds": (
            "wind_bell_sound",
            "summer_insects",
            "someone_resting_in_shade",
        ),
        "scenes": (
            "shade_on_old_wood",
            "someone_resting_in_shade",
            "cool_evening_at_the_edge",
        ),
    },
}

PASSING_GREETINGS = (
    "nodded_once",
    "raised_a_hand_briefly",
    "said_a_short_greeting",
    "paused_before_passing",
    "made_room_on_the_path",
)


@dataclass(frozen=True)
class LifeObservation:
    year: int
    event_type: str
    persons: list[str]
    detail: str


class LifeObservedSocietyLab(SocietyLab):
    """v1.4_1 with zero-effect life observations.

    The base simulation is advanced first. After that, separate per-year life
    RNG streams may record tea-house details. The base class never reads these
    records.
    """

    memory_shadow_chance = 0.50
    life_contact_chance = 0.72
    passing_greeting_chance = 0.22
    life_contact_familiarity_weight = 0
    passing_greeting_familiarity_weight = 2
    distant_social_familiarity_weight = 2
    conversation_shadow_familiarity_weight = 4
    familiarity_mark_divisor = 4
    relation_potential_mark_divisor = 8
    relation_potential_passing_greeting_weight = 1.0
    relation_potential_distant_social_weight = 1.0
    relation_potential_conversation_shadow_weight = 3.0
    relation_potential_familiarity_shadow_weight = 2.0
    relation_potential_memory_shadow_weight = 4.0

    def __init__(
        self,
        seed: Optional[int] = None,
        verbose: bool = False,
        life_verbose: bool = False,
    ):
        super().__init__(seed=seed, verbose=verbose)
        self.life_verbose = life_verbose
        self.life_observations: list[LifeObservation] = []
        self.life_place_visits: dict[str, dict[str, int]] = {}
        self.life_pair_familiarity: dict[tuple[str, str], int] = {}
        self.life_pair_familiarity_marks: dict[tuple[str, str], int] = {}
        self.life_pair_familiarity_places: dict[tuple[str, str], dict[str, int]] = {}
        self.life_memory_shadow_marks: set[tuple[tuple[str, str], str, int]] = set()
        self.life_relation_potential: dict[tuple[str, str], float] = {}
        self.life_relation_potential_marks: dict[tuple[str, str], int] = {}
        self.life_relation_potential_sources: dict[tuple[str, str], dict[str, int]] = {}
        self.life_place_first_year: dict[tuple[str, str], int] = {}
        self.life_place_last_year: dict[tuple[str, str], int] = {}
        self.life_time_shadow_marks: set[tuple[str, str, int]] = set()
        self.life_current_season: str = SEASONS[0]

    def step(self) -> None:
        super().step()
        self._observe_life()

    def _life_rng(self, stream_name: str) -> random.Random:
        material = f"{self.seed}|{self.year}|life_observation|{stream_name}".encode()
        digest = hashlib.sha256(material).hexdigest()
        return random.Random(int(digest[:16], 16))

    def _year_weather(self, rng: random.Random) -> str:
        """その年の空気。人物状態に依存しない。"""
        return rng.choice(WEATHER)

    def _observe_life(self) -> None:
        if self.population == 0:
            return

        weather_rng = self._life_rng("weather")
        world_sense_rng = self._life_rng("world_sense")
        person_place_rng = self._life_rng("person_place")
        person_sense_rng = self._life_rng("person_sense")
        pair_social_rng = self._life_rng("pair_social")
        life_contact_rng = self._life_rng("life_contact")
        memory_shadow_rng = self._life_rng("memory_shadow")
        time_shadow_rng = self._life_rng("time_shadow")
        ambient_rng = self._life_rng("ambient_layers")
        ambient_place_rng = self._life_rng("ambient_place_details")

        # 世界側の空気をまず記録する（茶屋と独立）
        weather = self._year_weather(weather_rng)
        time_of_day = weather_rng.choice(TIME_OF_DAY)
        fire = weather_rng.choice(FIRE_DETAIL)
        sound = weather_rng.choice(SOUNDS)
        self._record_life(
            "weather",
            [],
            f"weather={weather}; time={time_of_day}; fire={fire}; sound={sound}",
        )

        # Sound: sourceless, ~55% of years. "nothing" weighted higher in SOUNDS.
        sound = world_sense_rng.choice(SOUNDS)
        if sound != "nothing":
            self._record_life(
                "sound",
                [],
                f"sound={sound}; weather={weather}",
            )

        # Object trace: independent of persons, appears ~40% of years
        if world_sense_rng.random() < 0.40:
            trace = world_sense_rng.choice(OBJECT_TRACES)
            place = world_sense_rng.choice(TRACE_PLACES)
            self._record_life(
                "trace",
                [],
                f"place={place}; trace={trace}; weather={weather}",
            )

        if world_sense_rng.random() < 0.35:
            place = self._choose_world_sense_place(weather, world_sense_rng)
            scent = world_sense_rng.choice(SCENTS_BY_PLACE[place])
            self._record_life(
                "scent",
                [],
                f"scent={scent}; place={place}; weather={weather}",
            )

        if world_sense_rng.random() < 0.18:
            gesture = world_sense_rng.choice(WORLD_GESTURES)
            if gesture != "nothing_moved":
                place = self._choose_world_sense_place(weather, world_sense_rng)
                self._record_life(
                    "world_gesture",
                    [],
                    f"gesture={gesture}; place={place}; weather={weather}",
                )

        self._observe_ambient_layers(ambient_rng, weather)
        self._observe_ambient_place_details(ambient_place_rng, weather)

        self._observe_people_in_places(
            person_place_rng,
            person_sense_rng,
            pair_social_rng,
            life_contact_rng,
            memory_shadow_rng,
            time_shadow_rng,
            weather,
        )

    def _observe_ambient_layers(self, rng: random.Random, weather: str) -> None:
        season = rng.choice(SEASONS)
        self.life_current_season = season
        self._record_life(
            "season",
            [],
            f"season={season}; weather={weather}",
        )

        if rng.random() < 0.65:
            place = rng.choice(AMBIENT_PLACES)
            obj = rng.choice(AMBIENT_OBJECTS)
            self._record_life(
                "ambient_object",
                [],
                f"object={obj}; place={place}; season={season}; weather={weather}",
            )

        if rng.random() < 0.45:
            place = rng.choice(AMBIENT_PLACES)
            scent = rng.choice(AMBIENT_SCENTS)
            self._record_life(
                "ambient_scent",
                [],
                f"scent={scent}; place={place}; season={season}; weather={weather}",
            )

        if rng.random() < 0.50:
            place = rng.choice(AMBIENT_PLACES)
            sound = rng.choice(AMBIENT_SOUNDS)
            self._record_life(
                "ambient_sound",
                [],
                f"sound={sound}; place={place}; season={season}; weather={weather}",
            )

        if rng.random() < 0.24:
            place = rng.choice(AMBIENT_PLACES)
            mood = rng.choice(CROWD_MOODS)
            self._record_life(
                "crowd_mood",
                [],
                f"mood={mood}; place={place}; season={season}; weather={weather}",
            )

    def _observe_ambient_place_details(self, rng: random.Random, weather: str) -> None:
        season = self.life_current_season
        place = self._choose_ambient_detail_place(season, rng)
        details = AMBIENT_PLACE_DETAILS[place]

        if rng.random() < 0.70:
            obj = self._choose_ambient_detail_value(season, place, "objects", rng)
            self._record_life(
                "ambient_place_object",
                [],
                f"place={place}; object={obj}; season={season}; weather={weather}",
            )

        if rng.random() < 0.52:
            scent = self._choose_ambient_detail_value(season, place, "scents", rng)
            self._record_life(
                "ambient_place_scent",
                [],
                f"place={place}; scent={scent}; season={season}; weather={weather}",
            )

        if rng.random() < 0.55:
            sound = self._choose_ambient_detail_value(season, place, "sounds", rng)
            self._record_life(
                "ambient_place_sound",
                [],
                f"place={place}; sound={sound}; season={season}; weather={weather}",
            )

        if rng.random() < 0.42:
            scene = self._choose_ambient_detail_value(season, place, "scenes", rng)
            self._record_life(
                "ambient_place_scene",
                [],
                f"place={place}; scene={scene}; season={season}; weather={weather}",
            )

    def _choose_ambient_detail_place(self, season: str, rng: random.Random) -> str:
        places = list(AMBIENT_PLACE_DETAILS)
        seasonal = SEASON_AMBIENT_PLACE_WEIGHTS.get(season, {})
        weights = [seasonal.get(place, 1.0) for place in places]
        return rng.choices(places, weights=weights, k=1)[0]

    def _choose_ambient_detail_value(
        self,
        season: str,
        place: str,
        category: str,
        rng: random.Random,
    ) -> str:
        values = list(AMBIENT_PLACE_DETAILS[place][category])
        seasonal = (
            SEASON_DETAIL_WEIGHTS
            .get(season, {})
            .get(place, {})
            .get(category, {})
        )
        weights = [seasonal.get(value, 1.0) for value in values]
        return rng.choices(values, weights=weights, k=1)[0]

    def _observe_people_in_places(
        self,
        place_rng: random.Random,
        sense_rng: random.Random,
        pair_rng: random.Random,
        contact_rng: random.Random,
        memory_rng: random.Random,
        time_rng: random.Random,
        weather: str,
    ) -> None:
        visitors = [
            person
            for person in self.alive_people
            if place_rng.random() < self._place_observation_chance(person, weather)
        ]
        if not visitors:
            if place_rng.random() >= 0.22:
                return
            visitors = [place_rng.choice(self.alive_people)]

        place_rng.shuffle(visitors)
        # Track place -> [person] for same_place_nearby detection
        place_this_year: dict[str, list] = {}
        for person in visitors[:6]:
            place = self._choose_life_place(person, weather, place_rng)
            self._record_place_presence(person, place, weather, time_rng)
            self._observe_memory_shadow(person, place, weather, memory_rng)
            self._observe_sense_detail(person, place, weather, sense_rng)
            if place == "tea_house":
                self._observe_tea_house_visit(person, weather, sense_rng)
            elif place == "hearth":
                self._observe_hearth(person, weather, sense_rng)
            elif place == "well":
                self._observe_well(person, weather, sense_rng)
            elif place == "storehouse":
                self._observe_storehouse(person, weather, sense_rng)
            place_this_year.setdefault(place, []).append(person)

        # same_place_nearby: record pairs who appeared at the same place this year
        # No interaction implied. No trust change. Just proximity.
        for place, persons_here in place_this_year.items():
            if len(persons_here) < 2:
                continue
            for i in range(len(persons_here)):
                for j in range(i + 1, len(persons_here)):
                    pa = persons_here[i]
                    pb = persons_here[j]
                    self._record_life(
                        "same_place_nearby",
                        [pa.id, pb.id],
                        f"{pa.name} and {pb.name} both near {place}; weather={weather}",
                    )
                    if contact_rng.random() < self.life_contact_chance:
                        self._record_life(
                            "life_contact",
                            [pa.id, pb.id],
                            f"{pa.name} and {pb.name}: shared a brief ordinary moment; place={place}; weather={weather}",
                        )
                        if self.life_contact_familiarity_weight:
                            self._note_familiarity_shadow(
                                pa,
                                pb,
                                place,
                                weather,
                                self.life_contact_familiarity_weight,
                                "life_contact",
                            )
                        if contact_rng.random() < self.passing_greeting_chance:
                            greeting = contact_rng.choice(PASSING_GREETINGS)
                            self._record_life(
                                "passing_greeting",
                                [pa.id, pb.id],
                                f"{pa.name} and {pb.name}: {greeting}; place={place}; weather={weather}",
                            )
                            self._note_relation_potential(
                                pa,
                                pb,
                                place,
                                weather,
                                self.relation_potential_passing_greeting_weight,
                                "passing_greeting",
                            )
                            if self.passing_greeting_familiarity_weight:
                                self._note_familiarity_shadow(
                                    pa,
                                    pb,
                                    place,
                                    weather,
                                    self.passing_greeting_familiarity_weight,
                                    "passing_greeting",
                                )
                    # distant_social: ~20% chance when two people are nearby.
                    # No contact. No relationship asserted. Just what was seen.
                    if pair_rng.random() < 0.20:
                        gesture = pair_rng.choice(DISTANT_SOCIAL_GESTURES)
                        self._record_life(
                            "distant_social",
                            [pa.id, pb.id],
                            f"{pa.name} and {pb.name}: {gesture}; place={place}; weather={weather}",
                        )
                        self._note_relation_potential(
                            pa,
                            pb,
                            place,
                            weather,
                            self.relation_potential_distant_social_weight,
                            "distant_social",
                        )
                        if self.distant_social_familiarity_weight:
                            self._note_familiarity_shadow(
                                pa,
                                pb,
                                place,
                                weather,
                                self.distant_social_familiarity_weight,
                                "distant_social",
                            )
                        if pair_rng.random() < 0.28:
                            shadow = pair_rng.choice(CONVERSATION_SHADOWS)
                            self._record_life(
                                "conversation_shadow",
                                [pa.id, pb.id],
                                f"{pa.name} and {pb.name}: {shadow}; place={place}; weather={weather}",
                            )
                            self._note_relation_potential(
                                pa,
                                pb,
                                place,
                                weather,
                                self.relation_potential_conversation_shadow_weight,
                                "conversation_shadow",
                            )
                            if self.conversation_shadow_familiarity_weight:
                                self._note_familiarity_shadow(
                                    pa,
                                    pb,
                                    place,
                                    weather,
                                    self.conversation_shadow_familiarity_weight,
                                    "conversation_shadow",
                                )


    def _note_relation_potential(
        self,
        left,
        right,
        place: str,
        weather: str,
        weight: float,
        source: str,
    ) -> None:
        self._note_relation_potential_by_ids(
            left.id,
            right.id,
            place,
            weather,
            weight,
            source,
        )

    def _note_relation_potential_by_ids(
        self,
        left_id: str,
        right_id: str,
        place: str,
        weather: str,
        weight: float,
        source: str,
    ) -> None:
        if weight <= 0:
            return
        pair = tuple(sorted((left_id, right_id)))
        potential = self.life_relation_potential.get(pair, 0.0) + weight
        self.life_relation_potential[pair] = potential
        sources = self.life_relation_potential_sources.setdefault(pair, {})
        sources[source] = sources.get(source, 0) + 1

        mark = int(potential // self.relation_potential_mark_divisor)
        last_mark = self.life_relation_potential_marks.get(pair, 0)
        if mark <= last_mark:
            return

        self.life_relation_potential_marks[pair] = mark
        source_text = ",".join(
            source_name
            for source_name, _count in sorted(
                sources.items(),
                key=lambda item: (-item[1], item[0]),
            )
        )
        self._record_life(
            "life_bridge_potential",
            [left_id, right_id],
            (
                f"potential={potential:.1f}; mark={mark}; source={source}; "
                f"sources={source_text}; place={place}; weather={weather}"
            ),
        )

    def _note_familiarity_shadow(
        self,
        left,
        right,
        place: str,
        weather: str,
        weight: int,
        source: str,
    ) -> None:
        pair = tuple(sorted((left.id, right.id)))
        score = self.life_pair_familiarity.get(pair, 0) + weight
        self.life_pair_familiarity[pair] = score

        last_mark = self.life_pair_familiarity_marks.get(pair, 0)
        mark = score // self.familiarity_mark_divisor
        if mark <= last_mark:
            return

        self.life_pair_familiarity_marks[pair] = mark
        place_years = self.life_pair_familiarity_places.setdefault(pair, {})
        place_years.setdefault(place, self.year)
        self._record_life(
            "familiarity_shadow",
            [left.id, right.id],
            (
                f"{left.name} and {right.name}: repeated brief nearness; "
                f"place={place}; weather={weather}; source={source}; score={score}"
            ),
        )
        self._note_relation_potential(
            left,
            right,
            place,
            weather,
            self.relation_potential_familiarity_shadow_weight,
            "familiarity_shadow",
        )

    def _observe_memory_shadow(self, person, place: str, weather: str, rng: random.Random) -> None:
        for pair, place_years in self.life_pair_familiarity_places.items():
            if person.id not in pair:
                continue
            prior_year = place_years.get(place)
            if prior_year is None or prior_year >= self.year:
                continue
            marker = (pair, place, self.year)
            if marker in self.life_memory_shadow_marks:
                continue
            if rng.random() >= self.memory_shadow_chance:
                continue

            other_id = pair[0] if pair[1] == person.id else pair[1]
            shadow = rng.choice(MEMORY_SHADOWS)
            score = self.life_pair_familiarity.get(pair, 0)
            self.life_memory_shadow_marks.add(marker)
            self._record_life(
                "memory_shadow",
                [person.id, other_id],
                (
                    f"{person.name}: {shadow}; place={place}; weather={weather}; "
                    f"prior_year={prior_year}; prior_score={score}"
                ),
            )
            self._note_relation_potential_by_ids(
                person.id,
                other_id,
                place,
                weather,
                self.relation_potential_memory_shadow_weight,
                "memory_shadow",
            )

    def _place_observation_chance(self, person, weather: str) -> float:
        chance = 0.045
        if person.age < 12 or person.age >= 65:
            chance += 0.018
        if person.hunger > 0.65:
            chance += 0.020
        if person.fear > 0.55:
            chance -= 0.018
        if self._is_rainy(weather):
            chance += 0.018
        return self._clamp(chance)

    def _choose_life_place(self, person, weather: str, rng: random.Random) -> str:
        weights = {
            "tea_house": 1.00,
            "well": 0.90,
            "storehouse": 0.75,
            "hearth": 0.70,
            "gate": 0.55,
            "path": 0.80,
        }

        if person.age < 12:
            weights["tea_house"] += 0.30
            weights["hearth"] += 0.35
            weights["gate"] -= 0.15
        elif person.age >= 65:
            weights["tea_house"] += 0.35
            weights["hearth"] += 0.45
            weights["path"] -= 0.20

        if person.hunger > 0.65:
            weights["storehouse"] += 0.55
            weights["well"] += 0.30
            weights["tea_house"] -= 0.25

        if person.fear > 0.55:
            weights["tea_house"] -= 0.35
            weights["gate"] -= 0.25
            weights["path"] += 0.25
            weights["well"] += 0.20

        if self._is_rainy(weather):
            weights["tea_house"] += 0.35
            weights["hearth"] += 0.30
            weights["storehouse"] += 0.20
            weights["gate"] -= 0.20
            weights["path"] -= 0.25

        places = list(weights)
        normalized = [max(0.05, weights[place]) for place in places]
        return rng.choices(places, weights=normalized, k=1)[0]

    def _choose_world_sense_place(self, weather: str, rng: random.Random) -> str:
        weights = {
            "tea_house": 1.0,
            "well": 0.8,
            "storehouse": 0.7,
            "hearth": 0.8,
            "gate": 0.6,
            "path": 0.8,
        }
        if self._is_rainy(weather):
            weights["tea_house"] += 0.25
            weights["hearth"] += 0.20
            weights["path"] += 0.15
            weights["gate"] -= 0.15
        places = list(weights)
        normalized = [max(0.05, weights[place]) for place in places]
        return rng.choices(places, weights=normalized, k=1)[0]

    def _record_place_presence(
        self,
        person,
        place: str,
        weather: str,
        rng: random.Random,
    ) -> None:
        place_key = (person.id, place)
        first_year = self.life_place_first_year.get(place_key)
        previous_year = self.life_place_last_year.get(place_key)
        if first_year is not None and previous_year is not None:
            self._observe_time_shadow(
                person,
                place,
                weather,
                first_year,
                previous_year,
                rng,
            )

        visits = self.life_place_visits.setdefault(person.id, {})
        visits[place] = visits.get(place, 0) + 1
        self.life_place_first_year.setdefault(place_key, self.year)
        self.life_place_last_year[place_key] = self.year
        self._record_life(
            "place_presence",
            [person.id],
            (
                f"{person.name} appeared at {place}; weather={weather}; "
                f"age={person.age}; hunger={person.hunger:.2f}; fear={person.fear:.2f}"
            ),
        )
        if visits[place] in {2, 4, 7}:
            self._record_life(
                "repeat_place",
                [person.id],
                f"{person.name} appeared at {place} again; count={visits[place]}",
            )

    def _observe_time_shadow(
        self,
        person,
        place: str,
        weather: str,
        first_year: int,
        previous_year: int,
        rng: random.Random,
    ) -> None:
        if previous_year >= self.year:
            return

        years_since_visit = self.year - previous_year
        place_age = self.year - first_year
        if years_since_visit < 4 and place_age < 12:
            return

        chance = 0.07
        if years_since_visit >= 8:
            chance += 0.09
        if place_age >= 20:
            chance += 0.07
        if person.age >= 65:
            chance += 0.04
        if rng.random() >= self._clamp(chance):
            return

        marker = (person.id, place, self.year)
        if marker in self.life_time_shadow_marks:
            return

        self.life_time_shadow_marks.add(marker)
        shadow = rng.choice(TIME_SHADOWS)
        self._record_life(
            "time_shadow",
            [person.id],
            (
                f"{person.name}: {shadow}; place={place}; weather={weather}; "
                f"first_year={first_year}; previous_year={previous_year}; "
                f"years_since_visit={years_since_visit}; place_age={place_age}"
            ),
        )

    def _observe_sense_detail(self, person, place: str, weather: str, rng: random.Random) -> None:
        if rng.random() < 0.34:
            scent = rng.choice(SCENTS_BY_PLACE[place])
            self._record_life(
                "scent",
                [person.id],
                f"{person.name}; scent={scent}; place={place}; weather={weather}",
            )
        if rng.random() < 0.30:
            touch = rng.choice(TOUCHES_BY_PLACE[place])
            self._record_life(
                "touch",
                [person.id],
                f"{person.name}; touch={touch}; place={place}; weather={weather}",
            )
        if rng.random() < 0.20:
            obj = rng.choice(AFFECT_OBJECTS)
            self._record_life(
                "affect_object",
                [person.id],
                f"{person.name}; object={obj}; place={place}; weather={weather}",
            )
        if rng.random() < 0.10:
            animal = rng.choice(ANIMAL_PRESENCES)
            self._record_life(
                "animal_presence",
                [person.id],
                f"{person.name}; animal={animal}; place={place}; weather={weather}",
            )
        # Gesture: ~18% chance. Fear-weighted or plain.
        # No emotion named. No cause stated.
        if rng.random() < 0.18:
            if person.fear > 0.55 and rng.random() < 0.55:
                gesture = rng.choice(PERSON_GESTURES_FEAR)
            elif rng.random() < 0.30:
                gesture = rng.choice(PERSON_GESTURES_WEIGHT)
            else:
                gesture = rng.choice(PERSON_GESTURES)
            self._record_life(
                "gesture",
                [person.id],
                f"{person.name} {gesture}; place={place}; weather={weather}",
            )

    def _observe_tea_house_visit(self, person, weather: str, rng: random.Random) -> None:
        if rng.random() < 0.72:
            tea = rng.choice(TEAS)
            vessel = rng.choice(TEA_VESSELS)
            condition = rng.choice(VESSEL_CONDITIONS)
            mood = rng.choice(TEA_HOUSE_MOODS)
            self._record_life(
                "tea_house",
                [person.id],
                (
                    f"{person.name} drank {tea} from {vessel}; "
                    f"vessel={condition}; room={mood}; weather={weather}"
                ),
            )
        if self._is_rainy(weather):
            self._record_life(
                "rainy_tea_house",
                [person.id],
                f"{person.name} stopped by the tea house on a rainy day; weather={weather}",
            )
        if person.age < 12 and rng.random() < 0.34:
            self._record_life(
                "child_bowl",
                [person.id],
                f"{person.name} held a tea bowl near the doorway; weather={weather}",
            )
        if person.age >= 65 and rng.random() < 0.42:
            self._record_life(
                "elder_sitting",
                [person.id],
                f"{person.name} sat quietly in the tea house; weather={weather}",
            )

    def _observe_hearth(self, person, weather: str, rng: random.Random) -> None:
        if rng.random() < 0.70:
            self._record_life(
                "brazier_presence",
                [person.id],
                f"{person.name} stayed near the brazier; weather={weather}",
            )
        if person.age >= 65 and rng.random() < 0.35:
            self._record_life(
                "elder_sitting",
                [person.id],
                f"{person.name} sat by the hearth; weather={weather}",
            )

    def _observe_well(self, person, weather: str, rng: random.Random) -> None:
        if rng.random() < 0.62:
            self._record_life(
                "well_water",
                [person.id],
                f"{person.name} drew water at the well; weather={weather}",
            )

    def _observe_storehouse(self, person, weather: str, rng: random.Random) -> None:
        if rng.random() < 0.58:
            self._record_life(
                "storehouse_bag",
                [person.id],
                f"{person.name} mended a sack near the storehouse; weather={weather}",
            )

    def _is_rainy(self, weather: str) -> bool:
        return weather in {"rain_on_roof", "heavy_rain", "light_mist"}

    def _record_life(self, event_type: str, persons: list[str], detail: str) -> None:
        observation = LifeObservation(self.year, event_type, persons, detail)
        self.life_observations.append(observation)
        if self.life_verbose:
            person_text = ", ".join(persons) if persons else "-"
            print(f"[Year {self.year:>3}] life:{event_type}: {person_text} | {detail}")

    def life_summary(self) -> dict[str, object]:
        tea_counts = {tea: 0 for tea in TEAS}
        weather_counts = {w: 0 for w in WEATHER}
        same_place_pair_counts: dict[tuple[str, str], int] = {}
        life_contact_pair_counts: dict[tuple[str, str], int] = {}
        passing_greeting_pair_counts: dict[tuple[str, str], int] = {}
        distant_social_pair_counts: dict[tuple[str, str], int] = {}
        conversation_shadow_pair_counts: dict[tuple[str, str], int] = {}
        familiarity_shadow_pair_counts: dict[tuple[str, str], int] = {}
        memory_shadow_pair_counts: dict[tuple[str, str], int] = {}
        life_bridge_potential_pair_counts: dict[tuple[str, str], int] = {}
        time_shadow_person_counts: dict[str, int] = {}
        for observation in self.life_observations:
            for tea in TEAS:
                if f"drank {tea} " in observation.detail:
                    tea_counts[tea] += 1
            if observation.event_type == "weather":
                for w in WEATHER:
                    if f"weather={w}" in observation.detail:
                        weather_counts[w] += 1
            if observation.event_type == "same_place_nearby":
                pair = tuple(sorted(observation.persons))
                same_place_pair_counts[pair] = same_place_pair_counts.get(pair, 0) + 1
            if observation.event_type == "life_contact":
                pair = tuple(sorted(observation.persons))
                life_contact_pair_counts[pair] = life_contact_pair_counts.get(pair, 0) + 1
            if observation.event_type == "passing_greeting":
                pair = tuple(sorted(observation.persons))
                passing_greeting_pair_counts[pair] = passing_greeting_pair_counts.get(pair, 0) + 1
            if observation.event_type == "distant_social":
                pair = tuple(sorted(observation.persons))
                distant_social_pair_counts[pair] = distant_social_pair_counts.get(pair, 0) + 1
            if observation.event_type == "conversation_shadow":
                pair = tuple(sorted(observation.persons))
                conversation_shadow_pair_counts[pair] = (
                    conversation_shadow_pair_counts.get(pair, 0) + 1
                )
            if observation.event_type == "familiarity_shadow":
                pair = tuple(sorted(observation.persons))
                familiarity_shadow_pair_counts[pair] = (
                    familiarity_shadow_pair_counts.get(pair, 0) + 1
                )
            if observation.event_type == "memory_shadow":
                pair = tuple(sorted(observation.persons))
                memory_shadow_pair_counts[pair] = memory_shadow_pair_counts.get(pair, 0) + 1
            if observation.event_type == "life_bridge_potential":
                pair = tuple(sorted(observation.persons))
                life_bridge_potential_pair_counts[pair] = (
                    life_bridge_potential_pair_counts.get(pair, 0) + 1
                )
            if observation.event_type == "time_shadow":
                for person_id in observation.persons:
                    time_shadow_person_counts[person_id] = (
                        time_shadow_person_counts.get(person_id, 0) + 1
                    )
        return {
            "life_observation_count": len(self.life_observations),
            "tea_house_count": sum(
                1
                for observation in self.life_observations
                if observation.event_type == "tea_house"
            ),
            "weather_count": sum(
                1
                for observation in self.life_observations
                if observation.event_type == "weather"
            ),
            "tea_counts": tea_counts,
            "weather_counts": weather_counts,
            "trace_count": sum(
                1
                for observation in self.life_observations
                if observation.event_type == "trace"
            ),
            "sound_count": sum(
                1
                for observation in self.life_observations
                if observation.event_type == "sound"
            ),
            "season_count": sum(
                1
                for observation in self.life_observations
                if observation.event_type == "season"
            ),
            "ambient_object_count": sum(
                1
                for observation in self.life_observations
                if observation.event_type == "ambient_object"
            ),
            "ambient_scent_count": sum(
                1
                for observation in self.life_observations
                if observation.event_type == "ambient_scent"
            ),
            "ambient_sound_count": sum(
                1
                for observation in self.life_observations
                if observation.event_type == "ambient_sound"
            ),
            "crowd_mood_count": sum(
                1
                for observation in self.life_observations
                if observation.event_type == "crowd_mood"
            ),
            "ambient_place_object_count": sum(
                1
                for observation in self.life_observations
                if observation.event_type == "ambient_place_object"
            ),
            "ambient_place_scent_count": sum(
                1
                for observation in self.life_observations
                if observation.event_type == "ambient_place_scent"
            ),
            "ambient_place_sound_count": sum(
                1
                for observation in self.life_observations
                if observation.event_type == "ambient_place_sound"
            ),
            "ambient_place_scene_count": sum(
                1
                for observation in self.life_observations
                if observation.event_type == "ambient_place_scene"
            ),
            "place_presence_count": sum(
                1
                for observation in self.life_observations
                if observation.event_type == "place_presence"
            ),
            "repeat_place_count": sum(
                1
                for observation in self.life_observations
                if observation.event_type == "repeat_place"
            ),
            "rainy_tea_house_count": sum(
                1
                for observation in self.life_observations
                if observation.event_type == "rainy_tea_house"
            ),
            "brazier_presence_count": sum(
                1
                for observation in self.life_observations
                if observation.event_type == "brazier_presence"
            ),
            "well_water_count": sum(
                1
                for observation in self.life_observations
                if observation.event_type == "well_water"
            ),
            "storehouse_bag_count": sum(
                1
                for observation in self.life_observations
                if observation.event_type == "storehouse_bag"
            ),
            "child_bowl_count": sum(
                1
                for observation in self.life_observations
                if observation.event_type == "child_bowl"
            ),
            "elder_sitting_count": sum(
                1
                for observation in self.life_observations
                if observation.event_type == "elder_sitting"
            ),
            "scent_count": sum(
                1
                for observation in self.life_observations
                if observation.event_type == "scent"
            ),
            "touch_count": sum(
                1
                for observation in self.life_observations
                if observation.event_type == "touch"
            ),
            "affect_object_count": sum(
                1
                for observation in self.life_observations
                if observation.event_type == "affect_object"
            ),
            "animal_presence_count": sum(
                1
                for observation in self.life_observations
                if observation.event_type == "animal_presence"
            ),
            "same_place_nearby_count": sum(
                1
                for observation in self.life_observations
                if observation.event_type == "same_place_nearby"
            ),
            "same_place_nearby_pair_counts": {
                f"{pair[0]}|{pair[1]}": count
                for pair, count in sorted(
                    same_place_pair_counts.items(),
                    key=lambda item: (-item[1], item[0]),
                )
            },
            "life_contact_count": sum(
                1
                for observation in self.life_observations
                if observation.event_type == "life_contact"
            ),
            "life_contact_pair_counts": {
                f"{pair[0]}|{pair[1]}": count
                for pair, count in sorted(
                    life_contact_pair_counts.items(),
                    key=lambda item: (-item[1], item[0]),
                )
            },
            "passing_greeting_count": sum(
                1
                for observation in self.life_observations
                if observation.event_type == "passing_greeting"
            ),
            "passing_greeting_pair_counts": {
                f"{pair[0]}|{pair[1]}": count
                for pair, count in sorted(
                    passing_greeting_pair_counts.items(),
                    key=lambda item: (-item[1], item[0]),
                )
            },
            "gesture_count": sum(
                1
                for observation in self.life_observations
                if observation.event_type == "gesture"
            ),
            "world_gesture_count": sum(
                1
                for observation in self.life_observations
                if observation.event_type == "world_gesture"
            ),
            "distant_social_count": sum(
                1
                for observation in self.life_observations
                if observation.event_type == "distant_social"
            ),
            "distant_social_pair_counts": {
                f"{pair[0]}|{pair[1]}": count
                for pair, count in sorted(
                    distant_social_pair_counts.items(),
                    key=lambda item: (-item[1], item[0]),
                )
            },
            "conversation_shadow_count": sum(
                1
                for observation in self.life_observations
                if observation.event_type == "conversation_shadow"
            ),
            "conversation_shadow_pair_counts": {
                f"{pair[0]}|{pair[1]}": count
                for pair, count in sorted(
                    conversation_shadow_pair_counts.items(),
                    key=lambda item: (-item[1], item[0]),
                )
            },
            "familiarity_shadow_count": sum(
                1
                for observation in self.life_observations
                if observation.event_type == "familiarity_shadow"
            ),
            "familiarity_shadow_pair_counts": {
                f"{pair[0]}|{pair[1]}": count
                for pair, count in sorted(
                    familiarity_shadow_pair_counts.items(),
                    key=lambda item: (-item[1], item[0]),
                )
            },
            "life_pair_familiarity_scores": {
                f"{pair[0]}|{pair[1]}": score
                for pair, score in sorted(
                    self.life_pair_familiarity.items(),
                    key=lambda item: (-item[1], item[0]),
                )
                if score >= 4
            },
            "memory_shadow_count": sum(
                1
                for observation in self.life_observations
                if observation.event_type == "memory_shadow"
            ),
            "memory_shadow_pair_counts": {
                f"{pair[0]}|{pair[1]}": count
                for pair, count in sorted(
                    memory_shadow_pair_counts.items(),
                    key=lambda item: (-item[1], item[0]),
                )
            },
            "life_bridge_potential_count": sum(
                1
                for observation in self.life_observations
                if observation.event_type == "life_bridge_potential"
            ),
            "life_bridge_potential_pair_counts": {
                f"{pair[0]}|{pair[1]}": count
                for pair, count in sorted(
                    life_bridge_potential_pair_counts.items(),
                    key=lambda item: (-item[1], item[0]),
                )
            },
            "life_relation_potential_scores": {
                f"{pair[0]}|{pair[1]}": round(score, 2)
                for pair, score in sorted(
                    self.life_relation_potential.items(),
                    key=lambda item: (-item[1], item[0]),
                )
                if score >= self.relation_potential_mark_divisor
            },
            "life_relation_potential_source_counts": {
                f"{pair[0]}|{pair[1]}": dict(
                    sorted(sources.items(), key=lambda item: (-item[1], item[0]))
                )
                for pair, sources in sorted(
                    self.life_relation_potential_sources.items(),
                    key=lambda item: (-sum(item[1].values()), item[0]),
                )
                if self.life_relation_potential.get(pair, 0.0)
                >= self.relation_potential_mark_divisor
            },
            "time_shadow_count": sum(
                1
                for observation in self.life_observations
                if observation.event_type == "time_shadow"
            ),
            "time_shadow_person_counts": {
                person_id: count
                for person_id, count in sorted(
                    time_shadow_person_counts.items(),
                    key=lambda item: (-item[1], item[0]),
                )
            },
        }


def main() -> None:
    sim = LifeObservedSocietyLab(seed=42, verbose=False, life_verbose=True)
    sim.run(years=80)
    print("\nSummary")
    for key, value in sim.summary().items():
        print(f"{key}: {value}")
    print("\nLife Summary")
    for key, value in sim.life_summary().items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
