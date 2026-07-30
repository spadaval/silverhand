# Silverhand Documentation

This directory contains the durable project record. The repository
[README](../README.md) is the short entry point; this index explains which
document has authority when notes disagree.

## Read order

1. [Design contract](design.md) — accepted product, geometry, fit, and
   manufacturing decisions.
2. [Current status](status.md) — scene authority, active milestone, known
   defects, evidence, and immediate work.
3. [Validation contract](validation.md) — promotion gates and required
   evidence.
4. [Glossary](glossary.md) — authoritative terminology and result language.
5. [History](history.md) — rejected approaches and lessons that must not be
   repeated.

## Approach records

[Approaches](approaches/README.md) capture methods that have enough evidence to
guide future implementation but do not necessarily represent approved
production geometry.

Current records:

- [Regional clearance deformation](approaches/regional-clearance-deformation.md)
  — why deep cutter collisions should first be treated as bounded corrections
  to the shared fit field.
- [V28 authored wearable panels](approaches/v28-authored-wearable-panels.md)
  — the active coarse-panel strategy for the broad C9/C20 wearer-side failure.

## Supporting documentation

- [Experiment notebook](../experiments/README.md) — lightweight qualitative
  goals, observations, learnings, and links to local checkpoint evidence.
- [Scripts](../scripts/README.md) — Blender and host-tool execution.
- [Validation reviews](../validation_reviews/README.md) — qualitative review
  records retained in Git.
- [Current exports](../exports/current/README.md) — production-export policy.
- [Evidence exports](../exports/evidence/README.md) — non-production proof
  artifacts.

## Document roles

| Document type | Contains | Must not contain |
|---|---|---|
| Design contract | accepted durable decisions | live task progress |
| Status | current facts and next work | obsolete experiments in full |
| Validation contract | reusable gates and evidence requirements | one-off results |
| Glossary | stable meanings | design arguments |
| History | rejected methods and retained lessons | active authority |
| Approach record | evidence-backed method, bounds, and continuation plan | unqualified promotion claims |
| Experiment note | goals, approach, observations, learnings, and evidence links | mandatory schemas or automatic approval |

Generated reports and renders remain under `_validation/`. Local Blender
experiments and binary checkpoints remain under ignored `blender_files/`.
Lightweight qualitative notes live under `experiments/`. None of these
locations replaces the concise durable record in this directory.
