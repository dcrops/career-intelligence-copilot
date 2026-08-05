"""Deterministic technology aliases for catalogue matching (FR-014 M2).

Aliases expand matching only. They do **not** invent evidence: a hit still requires
a catalogue entry with candidate_authoritative provenance for Class A support.
"""

from __future__ import annotations

from career_intelligence.truth_validation.normalise import normalise_object_key

# Groups of equivalent labels. First entry is the preferred display when merging.
_ALIAS_GROUPS: tuple[tuple[str, ...], ...] = (
    ("javascript", "js", "ecmascript"),
    ("typescript", "ts"),
    ("node.js", "nodejs", "node"),
    ("vue.js", "vuejs", "vue"),
    ("react.js", "reactjs", "react"),
    ("next.js", "nextjs"),
    ("nuxt.js", "nuxtjs", "nuxt"),
    ("c#", "csharp", "c sharp"),
    ("c++", "cpp", "cplusplus"),
    ("postgresql", "postgres", "psql"),
    ("kubernetes", "k8s"),
    ("fastapi", "fast api"),
    ("scikit-learn", "sklearn", "scikit learn"),
    ("github actions", "gh actions"),
)

# Well-known technology labels used to expand the scan lexicon for leakage detection.
# Presence here does **not** authorize candidate capability.
WELL_KNOWN_TECHNOLOGY_LABELS: tuple[str, ...] = (
    "Python",
    "FastAPI",
    "TypeScript",
    "JavaScript",
    "Vue",
    "Vue.js",
    "React",
    "Angular",
    "Node.js",
    "Java",
    "Kotlin",
    "Swift",
    "Go",
    "Rust",
    "Ruby",
    "PHP",
    "C#",
    "C++",
    "Scala",
    "Django",
    "Flask",
    "Spring",
    "PostgreSQL",
    "MySQL",
    "MongoDB",
    "Redis",
    "Docker",
    "Kubernetes",
    "AWS",
    "Azure",
    "GCP",
    "TensorFlow",
    "PyTorch",
    "LangChain",
    "OpenAI",
)


def alias_keys_for(label: str) -> frozenset[str]:
    """Return the full alias key set containing ``label``, or just its own key."""
    key = normalise_object_key(label)
    if not key:
        return frozenset()
    for group in _ALIAS_GROUPS:
        keys = {normalise_object_key(item) for item in group}
        if key in keys:
            return frozenset(keys)
    return frozenset({key})


def expand_alias_labels(label: str) -> tuple[str, ...]:
    """Return human labels in the alias group for ``label`` (for entry.aliases)."""
    key = normalise_object_key(label)
    for group in _ALIAS_GROUPS:
        keys = {normalise_object_key(item) for item in group}
        if key in keys:
            return group
    return (label,)
