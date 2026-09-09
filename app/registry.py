from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProgramMeta:
    slug: str  # our API's program key, also the WP CPT rest_base for guides where equal
    guides_cpt: str  # WP custom-post-type rest_base holding this program's funding guides
    guides_taxonomy: str  # program-specific taxonomy used to type/categorize its guides
    code: str
    name: str
    period: str | None


# 2021-2027 operational programs run by MIPE, each with its own "ghiduri_*"
# (funding-guide) custom post type in the mfe.gov.ro WordPress REST API,
# plus a catch-all "ghiduri-ms" type for guides not tied to one program.
PROGRAMS: dict[str, ProgramMeta] = {
    "pocidif": ProgramMeta(
        slug="pocidif",
        guides_cpt="ghiduri_pocidif",
        guides_taxonomy="tip_ghid_pocidif",
        code="PoCIDIF",
        name="Programul Creștere Inteligentă, Digitalizare și Instrumente Financiare",
        period="2021-2027",
    ),
    "peos": ProgramMeta(
        slug="peos",
        guides_cpt="ghiduri_peos",
        guides_taxonomy="tip_ghid_peo",
        code="PEO",
        name="Programul Educație și Ocupare",
        period="2021-2027",
    ),
    "pids": ProgramMeta(
        slug="pids",
        guides_cpt="ghiduri_pids",
        guides_taxonomy="tip_ghid_pids",
        code="PIDS",
        name="Programul Incluziune și Demnitate Socială",
        period="2021-2027",
    ),
    "poats": ProgramMeta(
        slug="poats",
        guides_cpt="ghiduri_poat",
        guides_taxonomy="tip_ghid_poat",
        code="POAT",
        name="Programul Asistență Tehnică",
        period="2021-2027",
    ),
    "ptj": ProgramMeta(
        slug="ptj",
        guides_cpt="ghiduri_ptj",
        guides_taxonomy="tip_ghiduri_ptj",
        code="PTJ",
        name="Programul Tranziție Justă",
        period="2021-2027",
    ),
    "pdds": ProgramMeta(
        slug="pdds",
        guides_cpt="ghiduri_pdd",
        guides_taxonomy="tip_ghid_pdd",
        code="PDDTJ",
        name="Programul Dezvoltare Durabilă și Tranziție Justă",
        period="2021-2027",
    ),
    "ghiduri-ms": ProgramMeta(
        slug="ghiduri-ms",
        guides_cpt="ghiduri-ms",
        guides_taxonomy="ghid",
        code="MS",
        name="Ghiduri generale de finanțare (instrumente financiare)",
        period=None,
    ),
}

# Taxonomies shared across (most) guide post types, resolvable via
# GET /wp/v2/<taxonomy>/<term_id> on mfe.gov.ro.
SHARED_TAXONOMIES = ("ghid", "regiune")

# Only registered against the "ghiduri-ms" catch-all guide type.
MS_ONLY_TAXONOMIES = ("prioritate", "obiectiv")

ALL_TAXONOMIES = {
    "ghid",
    "regiune",
    "prioritate",
    "obiectiv",
    "tip_ghid_pocidif",
    "tip_ghid_poat",
    "tip_ghid_peo",
    "tip_ghid_pids",
    "tip_ghid_pdd",
    "tip_ghiduri_ptj",
}


def taxonomies_for_program(program: str) -> tuple[str, ...]:
    meta = PROGRAMS[program]
    if program == "ghiduri-ms":
        return SHARED_TAXONOMIES + MS_ONLY_TAXONOMIES
    return SHARED_TAXONOMIES + (meta.guides_taxonomy,)
