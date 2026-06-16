"""Phase 1 eval tests — pure metric math on fake vectors (offline, no model)."""

import numpy as np

from chat.eval import calibrate, coverage_sims, group_records, recall_mrr


def test_group_records_dedupes_by_pmid():
    chunks = [
        {"pmid": "1", "question": "qA"},
        {"pmid": "1", "question": "qA-other"},  # later question ignored
        {"pmid": "2", "question": "qB"},
    ]
    recs = group_records(chunks)
    assert recs == [{"pmid": "1", "question": "qA"}, {"pmid": "2", "question": "qB"}]


def test_recall_mrr():
    ranked = [["1", "9", "8"], ["7", "2", "3"], ["5", "6", "4"]]
    gold = ["1", "2", "9"]  # rank 1, rank 2, absent
    recall, mrr = recall_mrr(ranked, gold, k=3)
    assert recall == 2 / 3                      # first two hit within top-3
    assert abs(mrr - (1.0 + 0.5 + 0.0) / 3) < 1e-9


def _one_hot(i, dim=4):
    v = [0.0] * dim
    v[i] = 1.0
    return v


def test_coverage_sims_excludes_own_pmid():
    # Two records; each question aligns with its own pmid's chunk.
    question_vecs = [_one_hot(0), _one_hot(1)]
    chunk_vecs = [_one_hot(0), _one_hot(1), _one_hot(2)]
    owners = ["A", "B", "B"]
    record_pmids = ["A", "B"]
    covered, uncovered = coverage_sims(question_vecs, chunk_vecs, owners, record_pmids)
    # Record A: covered hits its own chunk (sim 1); uncovered (B's chunks) is orthogonal (0).
    assert covered[0] == 1.0 and uncovered[0] == 0.0
    # Record B: covered 1; uncovered excludes both B chunks, leaving A's -> 0.
    assert covered[1] == 1.0 and uncovered[1] == 0.0


def test_calibrate_separates_distributions():
    covered = np.array([0.8, 0.9, 0.85])
    uncovered = np.array([0.2, 0.3, 0.25])
    cal = calibrate(covered, uncovered)
    # Perfectly separable -> J = 1.0 and threshold sits at/above the uncovered max
    # but no higher than the covered min, so all covered accepted, none uncovered.
    assert cal["j"] == 1.0
    assert cal["covered_accept"] == 1.0
    assert cal["uncovered_accept"] == 0.0
    assert 0.3 < cal["threshold"] <= 0.8


def test_calibrate_tie_breaks_higher():
    # Identical distributions -> any threshold gives J=0; prefer the highest.
    covered = np.array([0.5, 0.6])
    uncovered = np.array([0.5, 0.6])
    cal = calibrate(covered, uncovered)
    assert cal["threshold"] == 0.6
