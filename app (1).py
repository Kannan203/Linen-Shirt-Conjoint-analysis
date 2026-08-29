from __future__ import annotations

import csv
import html
import json
import os
import random
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection


# -----------------------------------------------------------------------------
# App configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Sustainable Linen Shirt ACBC Survey",
    page_icon="👕",
    layout="centered",
    initial_sidebar_state="collapsed",
)

APP_SCHEMA_VERSION = "1.0"
CSV_PATH = Path(os.getenv("ACBC_CSV_PATH", "acbc_responses.csv"))
CSV_WRITE_LOCK = threading.Lock()

ATTRIBUTES: Dict[str, Dict[str, Any]] = {
    "Access Model": {
        "key": "access_model",
        "levels": [
            "Traditional Purchase",
            "SaaP Subscription",
            "Rent-to-Own",
        ],
    },
    "Hygiene Assurance": {
        "key": "hygiene_assurance",
        "levels": [
            "Standard Eco-Wash",
            "Medical-Grade Sanitized",
            "First-Hand Only",
        ],
    },
    "Digital Product Passport": {
        "key": "digital_product_passport",
        "levels": [
            "Basic Transparency",
            "Verified Impact",
            "EU Circularity Passport",
        ],
    },
    "Service Ecosystem": {
        "key": "service_ecosystem",
        "levels": [
            "DIY",
            "Drop-Off Network",
            "Premium Concierge",
        ],
    },
    "Price": {
        "key": "price",
        "levels": ["€69", "€89", "€119"],
    },
}

ATTRIBUTE_NAMES = list(ATTRIBUTES.keys())

AGE_BRACKETS = [
    "18–24",
    "25–34",
    "35–44",
    "45–54",
    "55–64",
    "65+",
    "Prefer not to say",
]

GERMAN_CITIES = [
    "Berlin",
    "Hamburg",
    "Munich (München)",
    "Cologne (Köln)",
    "Frankfurt am Main",
    "Stuttgart",
    "Düsseldorf",
    "Leipzig",
    "Dortmund",
    "Essen",
    "Bremen",
    "Dresden",
    "Hanover (Hannover)",
    "Nuremberg (Nürnberg)",
    "Duisburg",
    "Bochum",
    "Wuppertal",
    "Bielefeld",
    "Bonn",
    "Münster",
    "Karlsruhe",
    "Mannheim",
    "Augsburg",
    "Wiesbaden",
    "Gelsenkirchen",
    "Mönchengladbach",
    "Braunschweig",
    "Chemnitz",
    "Kiel",
    "Aachen",
    "Halle (Saale)",
    "Magdeburg",
    "Freiburg im Breisgau",
    "Krefeld",
    "Lübeck",
    "Oberhausen",
    "Erfurt",
    "Mainz",
    "Rostock",
    "Kassel",
    "Saarbrücken",
    "Potsdam",
    "Regensburg",
    "Heidelberg",
    "Other German city / municipality",
]

GENDER_OPTIONS = [
    "Woman",
    "Man",
    "Non-binary / diverse",
    "Another identity",
    "Prefer not to say",
]

LEVEL_DESCRIPTIONS: Dict[str, Dict[str, str]] = {
    "Access Model": {
        "Traditional Purchase": "Pay once and own the shirt immediately.",
        "SaaP Subscription": "Use the shirt through an ongoing Shirt-as-a-Product subscription.",
        "Rent-to-Own": "Make recurring payments that build toward ownership.",
    },
    "Hygiene Assurance": {
        "Standard Eco-Wash": "Routine low-impact professional cleaning.",
        "Medical-Grade Sanitized": "Enhanced validated sanitation between users or service cycles.",
        "First-Hand Only": "The garment has not previously been worn by another customer.",
    },
    "Digital Product Passport": {
        "Basic Transparency": "Core origin, material, and care information.",
        "Verified Impact": "Verified environmental and social impact information.",
        "EU Circularity Passport": "Expanded circularity, repair, reuse, and lifecycle traceability data.",
    },
    "Service Ecosystem": {
        "DIY": "You handle care, returns, repairs, and logistics yourself.",
        "Drop-Off Network": "Use participating local drop-off points for service and returns.",
        "Premium Concierge": "Door-to-door support for cleaning, repair, exchange, or returns.",
    },
    "Price": {
        "€69": "Lowest price point.",
        "€89": "Mid-range price point.",
        "€119": "Premium price point.",
    },
}


# -----------------------------------------------------------------------------
# Styling
# -----------------------------------------------------------------------------
def inject_css() -> None:
    st.markdown(
        """
        <style>
        .block-container {
            max-width: 900px;
            padding-top: 1rem;
            padding-bottom: 3rem;
        }

        h1, h2, h3 {
            letter-spacing: -0.02em;
        }

        .survey-kicker {
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            opacity: 0.65;
            margin-bottom: 0.25rem;
        }

        .phase-title {
            margin-top: 0;
        }

        .profile-card {
            border: 1px solid rgba(128, 128, 128, 0.28);
            border-radius: 16px;
            padding: 1rem;
            margin: 0.75rem 0 1rem 0;
            background: rgba(128, 128, 128, 0.045);
        }

        .profile-title {
            font-size: 1.05rem;
            font-weight: 700;
            margin-bottom: 0.75rem;
        }

        .profile-row {
            display: grid;
            grid-template-columns: minmax(130px, 0.9fr) minmax(0, 1.25fr);
            gap: 0.75rem;
            padding: 0.52rem 0;
            border-top: 1px solid rgba(128, 128, 128, 0.16);
        }

        .profile-row:first-of-type {
            border-top: none;
        }

        .attr-name {
            font-size: 0.82rem;
            opacity: 0.68;
        }

        .attr-level {
            font-weight: 650;
            line-height: 1.25;
        }

        .final-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 0.8rem;
            margin: 0.75rem 0 1rem 0;
        }

        .final-card {
            border: 1px solid rgba(128, 128, 128, 0.28);
            border-radius: 16px;
            padding: 0.9rem;
            background: rgba(128, 128, 128, 0.045);
            min-width: 0;
        }

        .final-card .profile-row {
            display: block;
            padding: 0.5rem 0;
        }

        .final-card .attr-level {
            margin-top: 0.12rem;
        }

        .muted-box {
            border-radius: 12px;
            padding: 0.85rem 1rem;
            background: rgba(128, 128, 128, 0.07);
            margin-bottom: 1rem;
        }

        div.stButton > button,
        div.stFormSubmitButton > button {
            width: 100%;
            min-height: 48px;
            border-radius: 12px;
            font-weight: 650;
        }

        div[data-testid="stSelectbox"] label,
        div[data-testid="stRadio"] label {
            font-weight: 600;
        }

        @media (max-width: 700px) {
            .block-container {
                padding-left: 0.85rem;
                padding-right: 0.85rem;
                padding-top: 0.7rem;
            }

            .profile-row {
                display: block;
            }

            .attr-level {
                margin-top: 0.15rem;
            }

            .final-grid {
                grid-template-columns: 1fr;
            }

            .profile-card,
            .final-card {
                border-radius: 14px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# -----------------------------------------------------------------------------
# Session-state helpers
# -----------------------------------------------------------------------------
def init_state() -> None:
    defaults: Dict[str, Any] = {
        "phase": 1,
        "respondent_id": str(uuid.uuid4()),
        "rng_seed": random.SystemRandom().randrange(1, 2**63),
        "demographics": {},
        "byo_anchor": None,
        "screening_profiles": [],
        "screening_index": 0,
        "screening_responses": [],
        "rejection_flags": {},
        "final_options": [],
        "final_choice": None,
        "submitted": False,
        "submission_payload": None,
        "csv_saved": False,
        "csv_save_error": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_downstream_from_byo() -> None:
    st.session_state.screening_profiles = []
    st.session_state.screening_index = 0
    st.session_state.screening_responses = []
    st.session_state.rejection_flags = {}
    st.session_state.final_options = []
    st.session_state.final_choice = None
    st.session_state.submitted = False
    st.session_state.submission_payload = None
    st.session_state.csv_saved = False
    st.session_state.csv_save_error = None


def profile_key(levels: Dict[str, str]) -> Tuple[str, ...]:
    return tuple(levels[attr] for attr in ATTRIBUTE_NAMES)


def changed_attributes(anchor: Dict[str, str], levels: Dict[str, str]) -> List[Dict[str, str]]:
    changes: List[Dict[str, str]] = []
    for attr in ATTRIBUTE_NAMES:
        if anchor[attr] != levels[attr]:
            changes.append(
                {
                    "attribute": attr,
                    "from": anchor[attr],
                    "to": levels[attr],
                }
            )
    return changes


# -----------------------------------------------------------------------------
# Adaptive profile generation
# -----------------------------------------------------------------------------
def generate_screening_profiles(anchor: Dict[str, str], seed: int) -> List[Dict[str, Any]]:
    """Generate exactly three unique profiles, each 1–2 attributes from BYO."""
    rng = random.Random(seed ^ 0x51A7C0BC)
    profiles: List[Dict[str, Any]] = []
    seen = {profile_key(anchor)}

    attempts = 0
    while len(profiles) < 3 and attempts < 500:
        attempts += 1
        n_changes = rng.choice([1, 2])
        attrs_to_change = rng.sample(ATTRIBUTE_NAMES, k=n_changes)
        levels = dict(anchor)

        for attr in attrs_to_change:
            alternatives = [
                level
                for level in ATTRIBUTES[attr]["levels"]
                if level != anchor[attr]
            ]
            levels[attr] = rng.choice(alternatives)

        key = profile_key(levels)
        if key in seen:
            continue

        seen.add(key)
        profiles.append(
            {
                "screening_profile_id": f"S{len(profiles) + 1}",
                "levels": levels,
                "changes_from_byo": changed_attributes(anchor, levels),
            }
        )

    if len(profiles) != 3:
        raise RuntimeError("Could not generate exactly three unique screening profiles.")

    return profiles


def update_rejection_flags(profile: Dict[str, Any]) -> None:
    """
    Track levels that are potential rejection drivers.

    If a rejected profile differs on two attributes, both changed levels are flagged as
    *potential* unacceptable criteria because the binary response alone cannot identify
    which one caused the rejection.
    """
    flags: Dict[str, Dict[str, int]] = st.session_state.rejection_flags

    for change in profile["changes_from_byo"]:
        attr = change["attribute"]
        rejected_level = change["to"]
        flags.setdefault(attr, {})
        flags[attr][rejected_level] = flags[attr].get(rejected_level, 0) + 1

    st.session_state.rejection_flags = flags


def generate_final_options(
    anchor: Dict[str, str],
    screening_profiles: List[Dict[str, Any]],
    screening_responses: List[Dict[str, Any]],
    rejection_flags: Dict[str, Dict[str, int]],
    seed: int,
) -> List[Dict[str, Any]]:
    """
    Keep every accepted screening profile. If fewer than three were accepted,
    create close variants until exactly three unique final options exist.
    """
    rng = random.Random(seed ^ 0x7F1A1C0B)

    response_by_id = {
        item["screening_profile_id"]: item for item in screening_responses
    }

    options: List[Dict[str, Any]] = []
    used_keys = set()

    for profile in screening_profiles:
        response = response_by_id.get(profile["screening_profile_id"])
        if response and response["decision"] == "Yes, Acceptable":
            key = profile_key(profile["levels"])
            if key not in used_keys:
                used_keys.add(key)
                options.append(
                    {
                        "levels": dict(profile["levels"]),
                        "source": "accepted_screening_profile",
                        "source_profile_id": profile["screening_profile_id"],
                    }
                )

    rejected_keys = {
        profile_key(profile["levels"])
        for profile in screening_profiles
        if response_by_id.get(profile["screening_profile_id"], {}).get("decision")
        == "No, Unacceptable"
    }

    # Build variants around the BYO anchor and accepted alternatives. Avoid known
    # rejected profiles and, when possible, avoid levels already implicated in rejection.
    base_profiles = [dict(anchor)] + [dict(option["levels"]) for option in options]

    attempts = 0
    while len(options) < 3 and attempts < 1000:
        attempts += 1
        base = dict(rng.choice(base_profiles))

        # Close variants are normally one attribute away; two changes are used only
        # later if necessary to guarantee uniqueness.
        n_changes = 1 if attempts <= 700 else 2
        attrs_to_change = rng.sample(ATTRIBUTE_NAMES, k=n_changes)
        candidate = dict(base)

        for attr in attrs_to_change:
            alternatives = [
                level
                for level in ATTRIBUTES[attr]["levels"]
                if level != candidate[attr]
            ]

            non_flagged = [
                level
                for level in alternatives
                if rejection_flags.get(attr, {}).get(level, 0) == 0
            ]
            pool = non_flagged or alternatives
            candidate[attr] = rng.choice(pool)

        key = profile_key(candidate)
        if key in used_keys or key in rejected_keys:
            continue

        used_keys.add(key)
        options.append(
            {
                "levels": candidate,
                "source": "generated_close_variant",
                "source_profile_id": None,
            }
        )
        base_profiles.append(dict(candidate))

    if len(options) < 3:
        # Deterministic safety fallback. There are 3^5 = 243 possible profiles, so this
        # should only execute if future attribute definitions become unusually constrained.
        for attr in ATTRIBUTE_NAMES:
            for level in ATTRIBUTES[attr]["levels"]:
                candidate = dict(anchor)
                candidate[attr] = level
                key = profile_key(candidate)
                if key == profile_key(anchor) or key in used_keys or key in rejected_keys:
                    continue
                used_keys.add(key)
                options.append(
                    {
                        "levels": candidate,
                        "source": "generated_close_variant_fallback",
                        "source_profile_id": None,
                    }
                )
                if len(options) == 3:
                    break
            if len(options) == 3:
                break

    if len(options) != 3:
        raise RuntimeError("Could not construct exactly three final tournament options.")

    # Randomize display position to avoid systematically placing accepted profiles first.
    rng.shuffle(options)
    for idx, option in enumerate(options):
        option["final_option_id"] = f"F{idx + 1}"
        option["display_label"] = f"Option {chr(65 + idx)}"

    return options


# -----------------------------------------------------------------------------
# Rendering helpers
# -----------------------------------------------------------------------------
def render_progress() -> None:
    phase = int(st.session_state.phase)

    if st.session_state.submitted:
        progress = 1.0
        label = "Survey complete"
    elif phase == 1:
        progress = 0.08
        label = "Phase 1 of 4 · Welcome & demographics"
    elif phase == 2:
        progress = 0.24
        label = "Phase 2 of 4 · Build your own"
    elif phase == 3:
        idx = int(st.session_state.screening_index)
        progress = 0.34 + (idx / 3.0) * 0.36
        label = f"Phase 3 of 4 · Smart screening · Profile {idx + 1} of 3"
    else:
        progress = 0.86
        label = "Phase 4 of 4 · Final choice"

    st.caption(label)
    st.progress(min(max(progress, 0.0), 1.0))


def profile_card_html(title: str, levels: Dict[str, str], css_class: str = "profile-card") -> str:
    rows = []
    for attr in ATTRIBUTE_NAMES:
        rows.append(
            "<div class='profile-row'>"
            f"<div class='attr-name'>{html.escape(attr)}</div>"
            f"<div class='attr-level'>{html.escape(levels[attr])}</div>"
            "</div>"
        )

    return (
        f"<div class='{css_class}'>"
        f"<div class='profile-title'>{html.escape(title)}</div>"
        + "".join(rows)
        + "</div>"
    )


def render_final_cards(options: List[Dict[str, Any]]) -> None:
    cards = []
    for option in options:
        cards.append(
            profile_card_html(
                option["display_label"],
                option["levels"],
                css_class="final-card",
            )
        )

    st.markdown(
        "<div class='final-grid'>" + "".join(cards) + "</div>",
        unsafe_allow_html=True,
    )


def render_byo_summary(anchor: Dict[str, str]) -> None:
    st.markdown(profile_card_html("Your preferred configuration", anchor), unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# Data compilation and persistence
# -----------------------------------------------------------------------------
def compile_submission_row() -> Dict[str, str]:
    demographics = st.session_state.demographics
    anchor = st.session_state.byo_anchor
    screening_responses = st.session_state.screening_responses
    final_options = st.session_state.final_options
    final_choice = st.session_state.final_choice

    row: Dict[str, str] = {
        "schema_version": APP_SCHEMA_VERSION,
        "respondent_id": st.session_state.respondent_id,
        "submitted_at_utc": datetime.now(timezone.utc).isoformat(),
        "age_bracket": demographics.get("age_bracket", ""),
        "city_germany": demographics.get("city", ""),
        "gender": demographics.get("gender", ""),
    }

    for attr in ATTRIBUTE_NAMES:
        key = ATTRIBUTES[attr]["key"]
        row[f"byo_{key}"] = anchor[attr]

    for idx in range(3):
        response = screening_responses[idx]
        prefix = f"screening_{idx + 1}"
        row[f"{prefix}_profile_id"] = response["screening_profile_id"]
        row[f"{prefix}_decision"] = response["decision"]
        row[f"{prefix}_profile_json"] = json.dumps(
            response["levels"], ensure_ascii=False, sort_keys=True
        )
        row[f"{prefix}_changes_from_byo_json"] = json.dumps(
            response["changes_from_byo"], ensure_ascii=False, sort_keys=True
        )

    row["potential_unacceptable_flags_json"] = json.dumps(
        st.session_state.rejection_flags,
        ensure_ascii=False,
        sort_keys=True,
    )

    for idx, option in enumerate(final_options, start=1):
        prefix = f"final_option_{idx}"
        row[f"{prefix}_id"] = option["final_option_id"]
        row[f"{prefix}_display_label"] = option["display_label"]
        row[f"{prefix}_source"] = option["source"]
        row[f"{prefix}_source_profile_id"] = option.get("source_profile_id") or ""
        row[f"{prefix}_profile_json"] = json.dumps(
            option["levels"], ensure_ascii=False, sort_keys=True
        )

    row["final_choice_id"] = final_choice["choice_id"]
    row["final_choice_label"] = final_choice["choice_label"]
    row["final_choice_profile_json"] = json.dumps(
        final_choice.get("levels"), ensure_ascii=False, sort_keys=True
    )

    return row


def append_row_to_csv_once(row: Dict[str, str], path: Path) -> bool:
    """
    Append exactly once per respondent_id for the current CSV schema.

    The in-process lock prevents concurrent Streamlit threads from interleaving writes.
    For multi-instance deployments, replace local CSV persistence with a transactional
    database or object store. The on-screen JSON payload remains available regardless.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(row.keys())

    with CSV_WRITE_LOCK:
        if path.exists() and path.stat().st_size > 0:
            with path.open("r", newline="", encoding="utf-8") as existing:
                reader = csv.DictReader(existing)
                if reader.fieldnames != fieldnames:
                    raise RuntimeError(
                        "Existing CSV schema does not match the current survey schema. "
                        "Use a new ACBC_CSV_PATH or migrate the file."
                    )
                for existing_row in reader:
                    if existing_row.get("respondent_id") == row["respondent_id"]:
                        return False

        file_is_empty = not path.exists() or path.stat().st_size == 0
        with path.open("a", newline="", encoding="utf-8") as output:
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            if file_is_empty:
                writer.writeheader()
            writer.writerow(row)
            output.flush()
            os.fsync(output.fileno())

    return True


def payload_json(row: Dict[str, str]) -> str:
    """Return a readable structured payload rather than a CSV-shaped JSON object."""
    structured = {
        "schema_version": row["schema_version"],
        "respondent_id": row["respondent_id"],
        "submitted_at_utc": row["submitted_at_utc"],
        "demographics": st.session_state.demographics,
        "byo_anchor": st.session_state.byo_anchor,
        "screening": st.session_state.screening_responses,
        "potential_unacceptable_flags": st.session_state.rejection_flags,
        "final_tournament_options": st.session_state.final_options,
        "final_choice": st.session_state.final_choice,
    }
    return json.dumps(structured, ensure_ascii=False, indent=2)


# -----------------------------------------------------------------------------
# Phase screens
# -----------------------------------------------------------------------------
def phase_1_demographics() -> None:
    st.markdown("<div class='survey-kicker'>Sustainable linen shirt study</div>", unsafe_allow_html=True)
    st.title("Help us design a better circular clothing offer")
    st.write(
        "This adaptive survey asks you to build your preferred linen shirt offer, "
        "react to a few alternatives, and make one final choice."
    )

    st.markdown(
        "<div class='muted-box'>Estimated task: four short phases. "
        "Please answer based on what you would realistically consider for yourself in Germany.</div>",
        unsafe_allow_html=True,
    )

    existing = st.session_state.demographics

    with st.form("demographics_form", clear_on_submit=False):
        age = st.selectbox(
            "Age bracket",
            AGE_BRACKETS,
            index=AGE_BRACKETS.index(existing["age_bracket"])
            if existing.get("age_bracket") in AGE_BRACKETS
            else None,
            placeholder="Select your age bracket",
        )
        city = st.selectbox(
            "City in Germany",
            GERMAN_CITIES,
            index=GERMAN_CITIES.index(existing["city"])
            if existing.get("city") in GERMAN_CITIES
            else None,
            placeholder="Select your city",
        )
        gender = st.selectbox(
            "Gender",
            GENDER_OPTIONS,
            index=GENDER_OPTIONS.index(existing["gender"])
            if existing.get("gender") in GENDER_OPTIONS
            else None,
            placeholder="Select an option",
        )

        submitted = st.form_submit_button("Continue to Build-Your-Own", type="primary")

    if submitted:
        if age is None or city is None or gender is None:
            st.error("Please complete all three demographic fields before continuing.")
            return

        st.session_state.demographics = {
            "age_bracket": age,
            "city": city,
            "gender": gender,
        }
        st.session_state.phase = 2
        st.rerun()


def phase_2_byo() -> None:
    st.markdown("<div class='survey-kicker'>Build-Your-Own</div>", unsafe_allow_html=True)
    st.header("Configure your preferred linen shirt offer")
    st.write("Choose the one level you most prefer for each attribute.")

    existing = st.session_state.byo_anchor or {}

    with st.form("byo_form", clear_on_submit=False):
        selections: Dict[str, str] = {}

        for attr in ATTRIBUTE_NAMES:
            levels = ATTRIBUTES[attr]["levels"]
            current = existing.get(attr)
            selection = st.selectbox(
                attr,
                levels,
                index=levels.index(current) if current in levels else None,
                placeholder=f"Choose {attr.lower()}",
                key=f"byo_widget_{ATTRIBUTES[attr]['key']}",
            )
            selections[attr] = selection

            if selection:
                st.caption(LEVEL_DESCRIPTIONS[attr][selection])

        submitted = st.form_submit_button("Lock in my preferred configuration", type="primary")

    if submitted:
        if any(value is None for value in selections.values()):
            st.error("Please select one level for all five attributes.")
            return

        st.session_state.byo_anchor = dict(selections)
        reset_downstream_from_byo()
        st.session_state.screening_profiles = generate_screening_profiles(
            st.session_state.byo_anchor,
            st.session_state.rng_seed,
        )
        st.session_state.phase = 3
        st.rerun()


def phase_3_screening() -> None:
    anchor = st.session_state.byo_anchor
    profiles = st.session_state.screening_profiles
    idx = int(st.session_state.screening_index)

    if not anchor or len(profiles) != 3:
        st.error("The BYO anchor or screening profiles are missing. Returning to Phase 2.")
        st.session_state.phase = 2
        st.rerun()

    profile = profiles[idx]

    st.markdown("<div class='survey-kicker'>Smart Screening</div>", unsafe_allow_html=True)
    st.header(f"Alternative {idx + 1} of 3")
    st.write("Compare this offer with what you configured. Would you realistically consider it?")

    st.markdown(
        profile_card_html("Alternative product profile", profile["levels"]),
        unsafe_allow_html=True,
    )

    with st.form(f"screening_form_{idx}", clear_on_submit=False):
        decision = st.radio(
            "Would you consider this option?",
            ["Yes, Acceptable", "No, Unacceptable"],
            index=None,
            horizontal=True,
            key=f"screening_decision_{idx}",
        )
        submitted = st.form_submit_button("Save answer & continue", type="primary")

    if submitted:
        if decision is None:
            st.error("Please choose Acceptable or Unacceptable.")
            return

        response = {
            "screening_profile_id": profile["screening_profile_id"],
            "levels": dict(profile["levels"]),
            "changes_from_byo": list(profile["changes_from_byo"]),
            "decision": decision,
        }
        st.session_state.screening_responses.append(response)

        if decision == "No, Unacceptable":
            update_rejection_flags(profile)

        if idx < 2:
            st.session_state.screening_index = idx + 1
            st.rerun()

        st.session_state.final_options = generate_final_options(
            anchor=st.session_state.byo_anchor,
            screening_profiles=st.session_state.screening_profiles,
            screening_responses=st.session_state.screening_responses,
            rejection_flags=st.session_state.rejection_flags,
            seed=st.session_state.rng_seed,
        )
        st.session_state.phase = 4
        st.rerun()


def phase_4_tournament() -> None:
    options = st.session_state.final_options

    if len(options) != 3:
        st.error("Final options are missing. Reconstructing them from your screening answers.")
        st.session_state.final_options = generate_final_options(
            anchor=st.session_state.byo_anchor,
            screening_profiles=st.session_state.screening_profiles,
            screening_responses=st.session_state.screening_responses,
            rejection_flags=st.session_state.rejection_flags,
            seed=st.session_state.rng_seed,
        )
        options = st.session_state.final_options

    if st.session_state.submitted:
        render_completion()
        return

    st.markdown("<div class='survey-kicker'>Choice Tournament</div>", unsafe_allow_html=True)
    st.header("Choose the one offer you would prefer most")
    st.write(
        "Review the three options below. If none is acceptable overall, select “None of these options”."
    )

    render_final_cards(options)

    label_to_option = {option["display_label"]: option for option in options}
    choice_labels = [option["display_label"] for option in options] + ["None of these options"]

    with st.form("final_choice_form", clear_on_submit=False):
        choice_label = st.radio(
            "Final selection",
            choice_labels,
            index=None,
            key="final_choice_widget",
        )
        submitted = st.form_submit_button("Submit Survey", type="primary")

    if submitted:
        if choice_label is None:
            st.error("Please select one final option, including “None of these options” if appropriate.")
            return

        if choice_label == "None of these options":
            st.session_state.final_choice = {
                "choice_id": "NONE",
                "choice_label": choice_label,
                "levels": None,
            }
        else:
            selected = label_to_option[choice_label]
            st.session_state.final_choice = {
                "choice_id": selected["final_option_id"],
                "choice_label": selected["display_label"],
                "levels": dict(selected["levels"]),
            }

        row = compile_submission_row()
        st.session_state.submission_payload = payload_json(row)

        try:
            wrote_new_row = append_row_to_csv_once(row, CSV_PATH)
            st.session_state.csv_saved = True
            st.session_state.csv_save_error = None
            st.session_state.csv_write_status = (
                "saved" if wrote_new_row else "already_saved"
            )
        except Exception as exc:  # Payload remains available even if disk persistence fails.
            st.session_state.csv_saved = False
            st.session_state.csv_save_error = str(exc)
            st.session_state.csv_write_status = "failed"

        try:
            st.cache_data.clear()
            st.cache_resource.clear()
            #Establish background API bridge using your Secrets credentials
            conn = st.connection("gsheets", type=GSheetsConnection)
            client = conn.client._client  
            
            #Target your LC Survey Spreadsheet
            sheet_url = "https://docs.google.com/spreadsheets/d/1oAp7Wn1nwj1zJJFb2pNOouylM3GFVATvYlHb3tTNo7A/edit?gid=0#gid=0"
            spreadsheet = client.open_by_url(sheet_url)
            worksheet = spreadsheet.worksheet("Sheet1")
            
            # Robust data formatting block
            # Maps row content correctly whether compile_submission_row() returns a dict, list, or Series
            if isinstance(row, dict):
                row_to_append = [str(val) for val in row.values()]
            elif isinstance(row, (list, tuple)):
                row_to_append = [str(val) for val in row]
            elif hasattr(row, 'tolist'): # For numpy/pandas structures
                row_to_append = [str(val) for val in row.tolist()]
            else:
                row_to_append = [str(row)]
                
            # Execute direct API call using standard user entry interpretation
            worksheet.append_row(row_to_append, value_input_option="USER_ENTERED")
            
            # Display a confirmation message in the sidebar for debugging purposes
            st.sidebar.success("Database Sync Status: Success")
            
        except Exception as sheet_exc:
            # Displays the exact network or API error in the sidebar if it fails
            st.sidebar.error(f"Google Sheet Export Failed: {str(sheet_exc)}")
            # Log the error tracking details directly back into your session state
            st.session_state.csv_save_error = f"Google Sheet API Error: {str(sheet_exc)}"

        st.session_state.submitted = True
        st.rerun()


def render_completion() -> None:
    st.success("Thank you — your survey response has been compiled successfully.")

    if st.session_state.csv_saved:
        st.caption("The response was recorded in the configured CSV data store for this app instance.")
    else:
        st.warning(
            "The app could not write to its CSV data store. Your complete response is still available below for copying."
        )
        if st.session_state.csv_save_error:
            with st.expander("Storage error details"):
                st.code(st.session_state.csv_save_error)

    st.text_area(
        "Copy Data Payload",
        value=st.session_state.submission_payload or "",
        height=360,
        disabled=False,
        key="copy_data_payload",
    )

    st.caption(
        "For multi-server production deployments, point ACBC_CSV_PATH to suitable persistent storage "
        "or replace the local CSV writer with a transactional database."
    )


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
def main() -> None:
    inject_css()
    init_state()
    render_progress()

    phase = int(st.session_state.phase)

    if phase == 1:
        phase_1_demographics()
    elif phase == 2:
        phase_2_byo()
    elif phase == 3:
        phase_3_screening()
    elif phase == 4:
        phase_4_tournament()
    else:
        st.session_state.phase = 1
        st.rerun()


if __name__ == "__main__":
    main()
