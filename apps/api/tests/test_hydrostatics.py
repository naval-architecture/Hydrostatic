"""
Regression test using a box-barge fixture (L=10, B=4, H=3), where every
hydrostatic property can be hand-derived exactly. This is the ground-truth
check for the slicing/capping/coefficient pipeline — run this whenever the
core math changes.

Box positioned: AP at X=0, FP at X=10 (Lpp=10), centerline at Y=0
(Y in [-2, 2]), Baseline at Z=0 (Z in [0, 3]).
"""
import trimesh
import pytest

from app.core.hydrostatics import calculate_hydrostatics_at_draft


@pytest.fixture
def box_barge() -> trimesh.Trimesh:
    L, B, H = 10.0, 4.0, 3.0
    box = trimesh.creation.box(extents=[L, B, H])
    # trimesh.creation.box is centered at origin; translate to our convention
    box.apply_translation([L / 2, 0.0, H / 2])
    assert box.is_watertight
    return box


def test_box_barge_at_half_draft(box_barge):
    draft = 2.0
    result = calculate_hydrostatics_at_draft(
        hull=box_barge,
        draft=draft,
        ap_x=0.0,
        fp_x=10.0,
        midship_x=5.0,
        density=1.025,
    )

    assert result is not None

    # Exact hand-derived values for a rectangular box at T=2
    assert result.volume == pytest.approx(10.0 * 4.0 * 2.0, rel=1e-3)   # 80.0
    assert result.displacement == pytest.approx(80.0 * 1.025, rel=1e-3)
    assert result.lcb == pytest.approx(5.0, abs=1e-2)     # midship
    assert result.vcb == pytest.approx(1.0, abs=1e-2)     # half of draft
    assert result.lcf == pytest.approx(5.0, abs=1e-2)
    assert result.aw == pytest.approx(40.0, rel=1e-3)      # L * B
    assert result.bwl == pytest.approx(4.0, rel=1e-3)
    assert result.am == pytest.approx(8.0, rel=1e-3)       # B * T

    # A rectangular box is the degenerate case where every coefficient = 1.0
    assert result.cb == pytest.approx(1.0, rel=1e-2)
    assert result.cm == pytest.approx(1.0, rel=1e-2)
    assert result.cp == pytest.approx(1.0, rel=1e-2)
    assert result.cw == pytest.approx(1.0, rel=1e-2)
    assert result.cp_consistency_flag is False


def test_draft_below_keel_returns_none(box_barge):
    result = calculate_hydrostatics_at_draft(
        hull=box_barge, draft=-0.5, ap_x=0.0, fp_x=10.0, midship_x=5.0, density=1.025,
    )
    assert result is None


def test_draft_above_deck_returns_none_gracefully(box_barge):
    # Above the hull's full molded depth there is no waterplane intersection
    # at all -- Aw/LCF/Bwl are undefined in that case. Returning None (rather
    # than raising, or silently fabricating a "full volume" result) is the
    # correct behavior: a draft beyond the modeled hull depth is a modeling
    # input error, not a valid loading condition.
    result = calculate_hydrostatics_at_draft(
        hull=box_barge, draft=3.5, ap_x=0.0, fp_x=10.0, midship_x=5.0, density=1.025,
    )
    assert result is None


def test_draft_near_full_depth(box_barge):
    draft = 2.99
    result = calculate_hydrostatics_at_draft(
        hull=box_barge, draft=draft, ap_x=0.0, fp_x=10.0, midship_x=5.0, density=1.025,
    )
    assert result is not None
    assert result.volume == pytest.approx(10.0 * 4.0 * draft, rel=1e-3)
