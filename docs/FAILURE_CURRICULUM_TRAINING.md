# Failure-Curriculum Training

This guide explains the current supervised failure-curriculum adapter-training
workflow at a practical operator level. It is not an automatic training system
and does not grant deployment or production authority.

## Purpose

Failure-curriculum training turns known ZTH failure cases into supervised
training and evaluation evidence. The goal is to measure whether a small model
or adapter improves on a bounded behavior, especially structured-output
reliability.

## What this workflow is for

- Preparing compact failure examples from reviewed evidence.
- Training or evaluating an adapter against a narrow output contract.
- Comparing base-vs-adapter behavior on held-out validation cases.
- Preserving measured results for operator review.

## What this workflow is not for

- Unattended model training or deployment.
- Automatic model promotion, routing, or role assignment.
- Claims of general intelligence or autonomous project understanding.
- Publishing private logs, endpoint details, secrets, or raw local paths.

## Prerequisites

- A reviewed failure curriculum with accepted examples.
- A local training/evaluation environment selected by the operator.
- A base model and adapter recipe recorded in reviewable files.
- A held-out validation set that was not used as training material.

## Dataset shape

The useful shape is simple:

- an input packet or prompt;
- the expected constrained output;
- metadata explaining the failure mode or contract being tested;
- a split between training examples and held-out validation examples.

Do not treat raw transcripts as canonical training data without review. Remove
or generalize private paths, credentials, hostnames, endpoint URLs, and raw
operator-specific identifiers before committing durable summaries.

## Training recipe summary

The current proven local milestone used Qwen3-1.7B with a LoRA rank-8 adapter.
The successful run used non-thinking mode and avoided NaN/nonfinite collapse.

The recipe is evidence for a bounded supervised workflow. It does not mean ZTH
trains models automatically or that the adapter should be deployed without
operator review.

## Evaluation metrics

The current reports track mechanical structured-output behavior:

- JSON validity;
- top-level key match;
- exact match against the expected constrained output.

The proven held-out validation result improved:

| Metric | Base | Adapter |
|---|---:|---:|
| JSON validity | 18/36 | 36/36 |
| Top-level key match | 17/36 | 31/36 |
| Exact match | 3/36 | 10/36 |

These numbers show measurable structured-output behavior improvement on the
recorded validation split. They do not prove production readiness.

## Evidence to preserve

Preserve compact, sanitized summaries of:

- dataset split counts;
- model and adapter identifiers;
- training recipe parameters such as LoRA rank;
- nonfinite/NaN status;
- held-out validation metrics;
- remaining failure modes;
- commands or scripts used, with private values replaced by placeholders.

Raw logs and local run directories should stay private unless they have been
reviewed and sanitized for publication.

## Safety boundaries

- Adapters remain evidence for supervised review, not authorities.
- Metrics do not promote, approve, route, rank, or assign a model.
- Passing validation is evidence, not deployment permission.
- Operators retain disclosure, publication, deployment, and lifecycle authority.

## Current proven milestone

Qwen3-1.7B with a LoRA rank-8 failure-curriculum adapter produced a measured
held-out validation improvement in non-thinking mode:

- JSON validity improved from 18/36 to 36/36.
- Top-level key match improved from 17/36 to 31/36.
- Exact match improved from 3/36 to 10/36.
- The run avoided NaN/nonfinite collapse.

The result proves a bounded improvement in structured-output behavior under a
supervised workflow. It does not prove broad autonomous capability.

## Next recommended iteration

Keep the next iteration small:

1. Add a few reviewed failure examples for the remaining semantic-drift cases.
2. Re-run the same held-out validation split.
3. Add a second held-out split before making stronger claims.
4. Preserve a compact public report only after sanitization and operator review.
