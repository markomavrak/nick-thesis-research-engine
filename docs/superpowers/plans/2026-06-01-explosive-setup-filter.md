# Explosive Setup Filter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Filter daily research output to stocks with both high thesis fit and multiple concrete near-term leg-up reasons.

**Architecture:** Add setup metadata to ranked candidates, compute setup score/reasons in the analyzer from live signals and inferred catalysts, then gate the daily digest on both base score and setup score. Keep provider interfaces unchanged except optional candidate near-term signals.

**Tech Stack:** Python dataclasses, unittest, existing Resend/GitHub Actions flow.

---

### Task 1: Analyzer Setup Metadata

**Files:**
- Modify: `src/nick_engine/models.py`
- Modify: `src/nick_engine/analyzer.py`
- Test: `tests/test_analyzer.py`

- [ ] Add `near_term_signals` to `CandidateCompany`.
- [ ] Add `setup_score` and `setup_reasons` to `RankedCandidate`.
- [ ] Write failing tests proving candidates with multiple catalysts, small-cap torque, and fresh signals outrank/gate candidates without near-term reasons.
- [ ] Implement `_setup_profile(company, rotation)` to return score and reasons.
- [ ] Run `PYTHONPATH=src python3 -m unittest tests.test_analyzer -v`.

### Task 2: Daily Digest Gate And Copy

**Files:**
- Modify: `src/nick_engine/daily_digest.py`
- Test: `tests/test_daily_digest.py`

- [ ] Add `MIN_EXPLOSIVE_SETUP_SCORE = 60` and `MIN_NEAR_TERM_REASONS = 2`.
- [ ] Filter digest candidates by base score, setup score, and reason count.
- [ ] Add a `Why it could move soon` paragraph to text/HTML output.
- [ ] Assert the digest output includes setup reasons and no candidates below the setup gate.
- [ ] Run `PYTHONPATH=src python3 -m unittest tests.test_daily_digest -v`.

### Task 3: Live Provider Signals

**Files:**
- Modify: `src/nick_engine/live_provider.py`
- Test: `tests/test_live_provider.py`

- [ ] Populate `near_term_signals` from positive relative strength, volume expansion, latest SEC filing, and recent news.
- [ ] Assert fake live data enriches a candidate with multiple near-term signals.
- [ ] Run `PYTHONPATH=src python3 -m unittest tests.test_live_provider -v`.

### Task 4: Final Verification

**Files:**
- All touched files

- [ ] Run `PYTHONPATH=src python3 -m unittest discover -s tests -v`.
- [ ] Generate a sample digest and verify subject/html/text omit forbidden branding and include near-term setup reasons.
- [ ] Push changed files to GitHub.
