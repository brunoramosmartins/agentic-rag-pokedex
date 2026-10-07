"""Question templates: one Cypher pattern per template, run against the graph.

The graph is the examiner (ADR-007): each template's query returns the raw
material of its questions — anchors, gold answers and what the gold answer is
derived from. ``examiner/generate.py`` turns rows into questions, attaches the
registry's covers and applies the filters (`docs/examiner.md`).

Every query that touches ``LEARNS`` filters ``r.version_group IN $scope``; the
graph keeps every version group, so a missing filter would draw gold answers
from groups the corpus does not contain. ``LEARNS_TEMPLATES`` lists those
queries for the scope tests.
"""

from __future__ import annotations

from dataclasses import dataclass

# --- S0: one hop, sufficient -------------------------------------------------

S0_HIDDEN_ABILITY = """
MATCH (p:Pokemon {is_default: true})-[:FORM_OF]->(s:Species)
MATCH (p)-[:HAS_ABILITY {hidden: true}]->(a:Ability)
RETURN s.id AS species, p.id AS pokemon, collect(DISTINCT a.id) AS abilities
ORDER BY species
"""

S0_MOVE_POWER = """
MATCH (m:Move) WHERE m.power IS NOT NULL
RETURN m.id AS move, m.power AS power ORDER BY move
"""

S0_MOVE_CATEGORY = """
MATCH (m:Move) WHERE m.category IS NOT NULL
RETURN m.id AS move, m.category AS category ORDER BY move
"""

S0_MOVE_TYPE = """
MATCH (m:Move)-[:OF_TYPE]->(t:Type)
RETURN m.id AS move, t.id AS type ORDER BY move
"""

S0_TYPE_EFFICACY = """
MATCH (a:Type)-[d:DAMAGE]->(b:Type)
RETURN a.id AS attacker, b.id AS defender, d.factor AS factor
ORDER BY attacker, defender
"""

# --- S1: missing hop (version-free) -----------------------------------------

S1_FINAL_FORM = """
MATCH (x:Species) WHERE ()-[:EVOLVES_FROM]->(x)
MATCH path = (f:Species)-[:EVOLVES_FROM*1..]->(x)
WHERE NOT ()-[:EVOLVES_FROM]->(f)
WITH x, collect(path) AS paths
WHERE size(paths) = 1
WITH x, [n IN reverse(nodes(paths[0])) | n.id] AS line
MATCH (xp:Pokemon {is_default: true})-[:FORM_OF]->(x)
MATCH (fp:Pokemon {is_default: true})-[:FORM_OF]->(:Species {id: line[-1]})
RETURN x.id AS anchor, xp.id AS anchor_pokemon, line, fp.id AS final_pokemon
ORDER BY anchor
"""
"""Anchors with exactly one final form, the line from anchor to final form.
Shared by S1-A1 (hidden ability) and S1-A2 (types) of the final form."""

S1_NEXT_FORM = """
MATCH (c:Species)-[:EVOLVES_FROM]->(x:Species)
WITH x, collect(c) AS cs WHERE size(cs) = 1
WITH x, cs[0] AS c
MATCH (xp:Pokemon {is_default: true})-[:FORM_OF]->(x)
MATCH (cp:Pokemon {is_default: true})-[:FORM_OF]->(c)
RETURN x.id AS anchor, xp.id AS anchor_pokemon, c.id AS next,
       cp.id AS next_pokemon
ORDER BY anchor
"""

S1_MOVE_VS_SPECIES = """
MATCH (m:Move)-[:OF_TYPE]->(mt:Type)
WHERE m.power IS NOT NULL AND m.id IN $moves
MATCH (p:Pokemon {is_default: true})-[:FORM_OF]->(s:Species)
MATCH (p)-[ht:HAS_TYPE]->(dt:Type)
MATCH (mt)-[d:DAMAGE]->(dt)
WITH m, mt, s, p, collect([ht.slot, dt.id, d.factor]) AS parts
RETURN m.id AS move, mt.id AS move_type, s.id AS species, p.id AS pokemon, parts
ORDER BY move, species
"""
"""A seeded sample of damaging moves (``$moves``) × species; ``parts`` is
[slot, defending type, factor] per type of the species."""

# --- S2 / S4: level-up learnsets in the version scope ------------------------

LEVEL_UP_LEARNSETS = """
MATCH (p:Pokemon {is_default: true})-[:FORM_OF]->(s:Species)
MATCH (p)-[r:LEARNS {method: 'level-up'}]->(m:Move)
WHERE r.version_group IN $scope
RETURN s.id AS species, p.id AS pokemon, m.id AS move,
       r.version_group AS version_group, r.level AS level
ORDER BY pokemon, version_group, level, move
"""
"""Every level-up row of a default entry in the scope; S2-A1, S2-A2, S2-B1,
S4-A1 and S4-B1 are conditions over these rows."""

# --- S3: truncated sets -------------------------------------------------------

TYPED_LEARNERS = """
MATCH (p:Pokemon {is_default: true})-[r:LEARNS {method: 'level-up'}]->(m:Move)
WHERE r.version_group IN $scope
MATCH (p)-[ht:HAS_TYPE]->(t:Type)
RETURN m.id AS move, r.version_group AS version_group, t.id AS type,
       p.id AS pokemon, ht.slot AS slot, r.level AS level
ORDER BY move, version_group, type, pokemon, level
"""
"""Level-up learners of each move in each scope group, one row per learner,
type and level; S3-A1 and S3-B1 group them by (move, group, type)."""

LEARNS_TEMPLATES = {
    "LEVEL_UP_LEARNSETS": LEVEL_UP_LEARNSETS,
    "TYPED_LEARNERS": TYPED_LEARNERS,
}
"""Queries over ``LEARNS``: each must filter the version group by ``$scope``."""


@dataclass(frozen=True)
class Template:
    """A question template.

    Attributes:
        id: Stable id, e.g. ``S1-A2``.
        stratum: ``S0`` … ``S4``.
        group: ``A`` (tuning-visible) or ``B`` (held out).
        query: Name of the Cypher constant it reads.
        answer: Kind of answer: ``ability``, ``number``, ``category``, ``type``,
            ``types``, ``factor``, ``level``, ``move``, ``species-set``.
    """

    id: str
    stratum: str
    group: str
    query: str
    answer: str


TEMPLATES: tuple[Template, ...] = (
    Template("S0-A1", "S0", "A", "S0_HIDDEN_ABILITY", "ability"),
    Template("S0-A2", "S0", "A", "S0_MOVE_POWER", "number"),
    Template("S0-A3", "S0", "A", "S0_MOVE_CATEGORY", "category"),
    Template("S0-A4", "S0", "A", "S0_MOVE_TYPE", "type"),
    Template("S0-B1", "S0", "B", "S0_TYPE_EFFICACY", "factor"),
    Template("S1-A1", "S1", "A", "S1_FINAL_FORM", "ability"),
    Template("S1-A2", "S1", "A", "S1_FINAL_FORM", "types"),
    Template("S1-A3", "S1", "A", "S1_NEXT_FORM", "ability"),
    Template("S1-B1", "S1", "B", "S1_MOVE_VS_SPECIES", "factor"),
    Template("S2-A1", "S2", "A", "LEVEL_UP_LEARNSETS", "level"),
    Template("S2-A2", "S2", "A", "LEVEL_UP_LEARNSETS", "move"),
    Template("S2-B1", "S2", "B", "LEVEL_UP_LEARNSETS", "move"),
    Template("S3-A1", "S3", "A", "TYPED_LEARNERS", "species-set"),
    Template("S3-B1", "S3", "B", "TYPED_LEARNERS", "species-set"),
    Template("S4-A1", "S4", "A", "LEVEL_UP_LEARNSETS", "level"),
    Template("S4-B1", "S4", "B", "LEVEL_UP_LEARNSETS", "move"),
)

BY_ID = {t.id: t for t in TEMPLATES}
QUERIES = {
    name: value
    for name, value in globals().items()
    if name.isupper() and isinstance(value, str) and "MATCH" in value
}
"""Every Cypher constant of this module, by name."""
