"""
Unit tests for the pure helpers in ``apps/maintenance/agent_assist_views.py``.

Source file under test: apps/maintenance/agent_assist_views.py

Covers the skill digest + scoring machinery that feeds the agent-assist chat:
  - _format_skill              — verbose single-line format
  - _format_skill_compact      — token-efficient compact format
  - _score_skill               — multi-signal relevance scoring
  - _skills_digest             — top-N digest (with/without message)
  - skills_digest_for_message  — scored & ranked digest
  - _get_cached_skills         — 5-minute in-memory cache

These tests hit the database (via MaintenanceSkill.objects.create) but do not
touch Claude or the HTTP layer.
"""
import pytest

from apps.maintenance.agent_assist_views import (
    _format_skill,
    _format_skill_compact,
    _get_cached_skills,
    _score_skill,
    _skills_digest,
    _skills_cache,
    skills_digest_for_message,
)
from apps.maintenance.models import MaintenanceSkill

pytestmark = [pytest.mark.unit, pytest.mark.green, pytest.mark.django_db]


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def _clear_skills_cache():
    """The module-level cache is shared across tests — clear between each."""
    _skills_cache["objects"] = None
    _skills_cache["objects_expires"] = 0.0
    yield
    _skills_cache["objects"] = None
    _skills_cache["objects_expires"] = 0.0


def _make_skill(
    name="Leaking tap",
    trade="plumbing",
    symptom_phrases=None,
    steps=None,
    is_active=True,
):
    return MaintenanceSkill.objects.create(
        name=name,
        trade=trade,
        symptom_phrases=symptom_phrases or [],
        steps=steps or [],
        is_active=is_active,
    )


# ─────────────────────────────────────────────────────────────────────────────
# _format_skill (verbose)
# ─────────────────────────────────────────────────────────────────────────────
class TestFormatSkill:
    def test_formats_bare_skill(self):
        skill = _make_skill(name="Leaky tap", trade="plumbing")
        out = _format_skill(skill)
        assert out == "- [plumbing] Leaky tap"

    def test_includes_symptoms_when_present(self):
        skill = _make_skill(
            name="Leaky tap",
            trade="plumbing",
            symptom_phrases=["drip drip", "water under sink"],
        )
        out = _format_skill(skill)
        assert "Symptoms: drip drip, water under sink" in out

    def test_caps_symptoms_at_five(self):
        symptoms = [f"symptom-{i}" for i in range(10)]
        skill = _make_skill(symptom_phrases=symptoms)
        out = _format_skill(skill)
        # Only first five should appear
        assert "symptom-0" in out
        assert "symptom-4" in out
        assert "symptom-5" not in out

    def test_includes_steps_when_present(self):
        skill = _make_skill(steps=["shut water", "replace washer", "test"])
        out = _format_skill(skill)
        assert "Steps: shut water; replace washer; test" in out

    def test_caps_steps_at_five(self):
        steps = [f"step-{i}" for i in range(10)]
        skill = _make_skill(steps=steps)
        out = _format_skill(skill)
        assert "step-0" in out and "step-4" in out
        assert "step-5" not in out


# ─────────────────────────────────────────────────────────────────────────────
# _format_skill_compact (token-efficient)
# ─────────────────────────────────────────────────────────────────────────────
class TestFormatSkillCompact:
    def test_bare_skill_has_no_signs_or_do(self):
        skill = _make_skill(name="Leaky tap", trade="plumbing")
        out = _format_skill_compact(skill)
        assert out == "[plumbing] Leaky tap"

    def test_caps_symptoms_at_three(self):
        symptoms = ["symA", "symB", "symC", "symD", "symE"]
        skill = _make_skill(name="Xylo", symptom_phrases=symptoms)
        out = _format_skill_compact(skill)
        assert "Signs: symA, symB, symC" in out
        assert "symD" not in out and "symE" not in out

    def test_caps_steps_at_three(self):
        steps = ["stepOne", "stepTwo", "stepThree", "stepFour"]
        skill = _make_skill(name="Xylo", steps=steps)
        out = _format_skill_compact(skill)
        assert "Do: stepOne; stepTwo; stepThree" in out
        assert "stepFour" not in out

    def test_separator_between_sections(self):
        skill = _make_skill(
            name="Leaky tap",
            symptom_phrases=["dripping"],
            steps=["shut water"],
        )
        out = _format_skill_compact(skill)
        assert out.count(" | ") == 2  # header | signs | do

    def test_compact_is_shorter_than_verbose(self):
        """Sanity check: compact form really is more compact."""
        skill = _make_skill(
            name="A really long skill name for testing",
            symptom_phrases=[f"symptom phrase {i}" for i in range(5)],
            steps=[f"resolution step {i}" for i in range(5)],
        )
        assert len(_format_skill_compact(skill)) < len(_format_skill(skill))


# ─────────────────────────────────────────────────────────────────────────────
# _score_skill — multi-signal relevance scoring
# ─────────────────────────────────────────────────────────────────────────────
class TestScoreSkill:
    def test_irrelevant_message_scores_zero(self):
        skill = _make_skill(
            name="Leaky tap",
            trade="plumbing",
            symptom_phrases=["water dripping from pipe"],
        )
        assert _score_skill(skill, "the roof needs repainting") == 0.0

    def test_category_match_boosts_score(self):
        skill = _make_skill(name="Leaky tap", trade="plumbing")
        without_cat = _score_skill(skill, "help")
        with_cat = _score_skill(skill, "help", category="plumbing")
        assert with_cat - without_cat == pytest.approx(5.0)

    def test_category_match_is_case_insensitive(self):
        skill = _make_skill(trade="plumbing")
        assert _score_skill(skill, "help", category="PLUMBING") >= 5.0

    def test_exact_symptom_phrase_match_adds_three(self):
        skill = _make_skill(
            name="Leaky tap",
            trade="plumbing",
            symptom_phrases=["dripping water"],
        )
        score = _score_skill(skill, "there is dripping water under my sink")
        # symptom match (3.0) + possible word overlap
        assert score >= 3.0

    def test_skill_name_substring_match_adds_four(self):
        skill = _make_skill(name="Leaky tap", trade="plumbing")
        score = _score_skill(skill, "how do I fix a leaky tap please?")
        assert score >= 4.0

    def test_trade_mention_adds_one(self):
        skill = _make_skill(name="Some random skill", trade="plumbing")
        score = _score_skill(skill, "I need a plumbing specialist")
        # Trade match (1.0) — note "plumbing" is not in STOP_WORDS so it
        # also picks up word overlap from "specialist" etc., but the
        # minimum must be at least 1.0
        assert score >= 1.0

    def test_word_level_overlap_from_symptoms(self):
        """Partial word-level match from symptom phrases should add points."""
        skill = _make_skill(
            name="Geyser",
            trade="plumbing",
            symptom_phrases=["no hot water"],
        )
        # "hot" and "water" both overlap
        score = _score_skill(skill, "we have no hot water in the bathroom")
        assert score > 0

    def test_stop_words_are_ignored(self):
        """Stop words like 'the' should not contribute to score."""
        skill = _make_skill(
            name="Geyser",
            trade="plumbing",
            symptom_phrases=["and the of"],  # all stop words
        )
        score = _score_skill(skill, "the and of in")
        # No meaningful overlap — should score zero
        assert score == 0.0

    def test_higher_ranked_skill_beats_lower(self):
        """Skill with direct name + symptom match should beat bare skill."""
        direct = _make_skill(
            name="Leaky kitchen tap",
            trade="plumbing",
            symptom_phrases=["dripping tap"],
        )
        other = _make_skill(
            name="Roof inspection",
            trade="roofing",
            symptom_phrases=["tile cracked"],
        )
        msg = "my leaky kitchen tap is dripping tap water"
        assert _score_skill(direct, msg) > _score_skill(other, msg)


# ─────────────────────────────────────────────────────────────────────────────
# _get_cached_skills
# ─────────────────────────────────────────────────────────────────────────────
class TestGetCachedSkills:
    def test_returns_only_active_skills(self):
        _make_skill(name="Active 1", is_active=True)
        _make_skill(name="Active 2", is_active=True)
        _make_skill(name="Inactive", is_active=False)
        skills = _get_cached_skills()
        names = [s.name for s in skills]
        assert "Active 1" in names
        assert "Active 2" in names
        assert "Inactive" not in names

    def test_returns_cached_value_on_second_call(self):
        _make_skill(name="First")
        first = _get_cached_skills()
        # Adding a new row AFTER cache fills should NOT be seen
        _make_skill(name="Second")
        second = _get_cached_skills()
        assert first is second  # identity — same list object
        assert "Second" not in [s.name for s in second]

    def test_sorted_by_trade_then_name(self):
        _make_skill(name="Zeta", trade="plumbing")
        _make_skill(name="Alpha", trade="plumbing")
        _make_skill(name="Beta", trade="electrical")
        skills = _get_cached_skills()
        ordered = [(s.trade, s.name) for s in skills]
        # electrical comes before plumbing; alpha before zeta
        assert ordered == [
            ("electrical", "Beta"),
            ("plumbing", "Alpha"),
            ("plumbing", "Zeta"),
        ]


# ─────────────────────────────────────────────────────────────────────────────
# skills_digest_for_message (scored & ranked)
# ─────────────────────────────────────────────────────────────────────────────
class TestSkillsDigestForMessage:
    def test_returns_placeholder_when_no_skills(self):
        out = skills_digest_for_message("anything")
        assert "No active skills" in out

    def test_ranks_most_relevant_first(self):
        _make_skill(
            name="Leaky tap",
            trade="plumbing",
            symptom_phrases=["dripping water"],
        )
        _make_skill(
            name="Roof inspection",
            trade="roofing",
            symptom_phrases=["tiles cracked"],
        )
        out = skills_digest_for_message("my tap is dripping water")
        lines = out.strip().splitlines()
        assert lines[0].startswith("[plumbing] Leaky tap")

    def test_respects_max_skills_limit(self):
        for i in range(10):
            _make_skill(
                name=f"Plumbing issue {i}",
                trade="plumbing",
                symptom_phrases=[f"plumbing issue {i}"],
            )
        out = skills_digest_for_message("plumbing issue", max_skills=3)
        assert len(out.strip().splitlines()) == 3

    def test_falls_back_to_general_when_no_matches(self):
        _make_skill(name="General check", trade="general")
        _make_skill(name="Geyser repair", trade="plumbing")
        # Use a message with no overlap and no stop-word collisions
        out = skills_digest_for_message("xyz qqq zzz")
        # Should fall back — must contain SOME output, not the empty placeholder
        assert "No active skills" not in out
        assert out.strip() != ""

    def test_category_filter_promotes_matching_trade(self):
        plumb = _make_skill(name="Plumbing fix", trade="plumbing")
        roof = _make_skill(name="Roof fix", trade="roofing")
        out = skills_digest_for_message("help me", category="plumbing")
        first_line = out.strip().splitlines()[0]
        assert "plumbing" in first_line.lower()


# ─────────────────────────────────────────────────────────────────────────────
# _skills_digest (top-level entry)
# ─────────────────────────────────────────────────────────────────────────────
class TestSkillsDigest:
    def test_empty_db_returns_placeholder(self):
        assert "No active skills" in _skills_digest()

    def test_no_message_returns_diverse_trade_sample(self):
        # 3 plumbing, 3 electrical, 3 roofing
        for i in range(3):
            _make_skill(name=f"Plumb-{i}", trade="plumbing")
            _make_skill(name=f"Elec-{i}", trade="electrical")
            _make_skill(name=f"Roof-{i}", trade="roofing")
        out = _skills_digest(message="", limit=8)
        trades = {line.split("]")[0].lstrip("[") for line in out.splitlines()}
        # Must include at least 2 different trades (diversity cap of 2 per trade)
        assert len(trades) >= 2
        # Max 2 per trade enforced
        plumbing_count = sum(1 for line in out.splitlines() if "[plumbing]" in line)
        assert plumbing_count <= 2

    def test_with_message_delegates_to_scored_digest(self):
        _make_skill(
            name="Leaky tap",
            trade="plumbing",
            symptom_phrases=["dripping water"],
        )
        _make_skill(name="Roof inspection", trade="roofing")
        out = _skills_digest(message="dripping water", limit=8)
        assert "Leaky tap" in out

    def test_diversity_mode_respects_limit(self):
        for i in range(10):
            _make_skill(name=f"Skill-{i}", trade="plumbing")
        out = _skills_digest(message="", limit=2)
        assert len(out.splitlines()) <= 2
