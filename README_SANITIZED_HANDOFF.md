# Workflow Optimization Handoff — Sanitized

This package contains only the reusable Interpretable Context Methodology workflow material and lightweight local-agent tooling extracted from the original project archive.

## What is included

- Workflow documents for context distillation, shared-link capture, development-agent operation, and local-agent orchestration.
- Prompt templates for extraction, local-agent tasking, reporting, and resource reporting.
- Lightweight validation/harness utilities used to make agent work auditable.
- A README for the agent-run folder convention.

## What was intentionally removed

- Git history and object database.
- `node_modules`, Electron binaries, build outputs, package caches, and other dependency/vendor material.
- Historical nested ZIP archives.
- Raw ChatGPT exports, local terminal logs, session transcripts, and full run artifacts.
- Product-specific app source that is not necessary for sharing the workflow optimization method.
- Personal identifiers, email addresses, private LAN IPs, local machine paths, and author metadata.

## Safe-use notes

Treat this as a workflow pattern, not as canonical project history. The original project-specific names were generalized, and local endpoints were replaced with placeholders such as `http://<LAN_HOST>:8080`.

Before handing this to another system, keep it zipped and avoid adding raw logs, `.git`, `.env`, `node_modules`, or exported chat transcripts back into it.
