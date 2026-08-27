#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
target_root="${1:-${HOME}/.config/anythingllm-desktop/storage/plugins}"

mkdir -p "${target_root}"

for skill in historian_evidence historian_query; do
  src="${repo_root}/integrations/anythingllm/skills/${skill}"
  dst="${target_root}/${skill}"
  rm -rf "${dst}"
  mkdir -p "${dst}"
  cp -a "${src}/." "${dst}/"
done

echo "Synced AnythingLLM skills to ${target_root}"
