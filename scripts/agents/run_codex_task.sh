#!/usr/bin/env bash
# Launch one Codex subagent for a task card, with explicit, recorded settings.
#
# Usage:
#   scripts/agents/run_codex_task.sh TASK_ID MODEL EFFORT SANDBOX NETWORK PROMPT_FILE [WORKDIR]
#     MODEL    gpt-6-astra | gpt-6.1-sol | gpt-6.1-terra
#     EFFORT   low | medium | high | xhigh | max   ("ultra" is refused: it auto-delegates,
#              so the model/settings actually used become unrecordable)
#     SANDBOX  workspace-write | read-only
#     NETWORK  on | off   (outbound network for shell commands + live web search)
#     WORKDIR  optional; default = git worktree ../PET2MOF_worktrees/TASK_ID on branch task/TASK_ID
#
# Isolation (AGENTS.md §Secrets, work order §10.2):
#   * --ignore-user-config: the owner's ~/.codex/config.toml (full-access sandbox, plugins)
#     is NOT loaded; every setting is passed explicitly here.
#   * The codex process is started with `env -i` (only HOME, PATH, LANG, TERM) and
#     shell_environment_policy.inherit=core, so no project secrets reach tool processes.
#   * The worktree is created from a commit: untracked files such as .env are never present.
#   * LIMITATION: the macOS seatbelt sandbox restricts writes, not reads, of the same user.
#     It is NOT a hard boundary for files readable by this user. Recorded in docs/security.md.
set -euo pipefail

TASK_ID=${1:?task id}; MODEL=${2:?model}; EFFORT=${3:?effort}
SANDBOX=${4:?sandbox}; NETWORK=${5:?network}; PROMPT_FILE=${6:?prompt file}
WORKDIR=${7:-}

case "$MODEL" in gpt-6-astra|gpt-6.1-sol|gpt-6.1-terra) ;; *) echo "model not allowed: $MODEL" >&2; exit 2;; esac
case "$EFFORT" in low|medium|high|xhigh|max) ;; *) echo "effort not allowed: $EFFORT" >&2; exit 2;; esac
case "$SANDBOX" in workspace-write|read-only) ;; *) echo "sandbox not allowed: $SANDBOX" >&2; exit 2;; esac
case "$NETWORK" in on|off) ;; *) echo "network must be on|off" >&2; exit 2;; esac

REPO=$(git -C "$(dirname "$0")/../.." rev-parse --show-toplevel)
LOGDIR="$REPO/private/agent_logs"; mkdir -p "$LOGDIR"
PROMPT_ABS=$(cd "$(dirname "$PROMPT_FILE")" && pwd)/$(basename "$PROMPT_FILE")

if [[ -z "$WORKDIR" ]]; then
  WORKDIR="$(dirname "$REPO")/PET2MOF_worktrees/$TASK_ID"
  if [[ ! -d "$WORKDIR" ]]; then
    git -C "$REPO" worktree add -q -b "task/$TASK_ID" "$WORKDIR" HEAD
  fi
fi
if [[ -e "$WORKDIR/.env" ]]; then echo "refusing: .env present in $WORKDIR" >&2; exit 3; fi

NET_ARGS=(-c "sandbox_workspace_write.network_access=false" -c 'web_search="disabled"')
if [[ "$NETWORK" == on ]]; then
  NET_ARGS=(-c "sandbox_workspace_write.network_access=true" -c 'web_search="live"')
fi

STAMP=$(date -u +%Y%m%dT%H%M%SZ)
META="$LOGDIR/$TASK_ID.$STAMP.meta.json"
cat > "$META" <<EOF
{"task_id":"$TASK_ID","requested_model":"$MODEL","requested_effort":"$EFFORT",
 "sandbox":"$SANDBOX","network":"$NETWORK","workdir":"$WORKDIR",
 "prompt_sha256":"$(shasum -a 256 "$PROMPT_ABS" | cut -d' ' -f1)",
 "codex_version":"$(codex --version 2>/dev/null)","started_utc":"$STAMP"}
EOF

set +e
env -i HOME="$HOME" PATH="$PATH" LANG="${LANG:-en_US.UTF-8}" TERM=dumb \
  codex exec --ignore-user-config --skip-git-repo-check \
    -m "$MODEL" -c "model_reasoning_effort=\"$EFFORT\"" \
    -s "$SANDBOX" -c 'approval_policy="never"' \
    -c 'shell_environment_policy.inherit="core"' \
    "${NET_ARGS[@]}" \
    -C "$WORKDIR" --json \
    -o "$LOGDIR/$TASK_ID.$STAMP.last.md" \
    - < "$PROMPT_ABS" > "$LOGDIR/$TASK_ID.$STAMP.events.jsonl" 2> "$LOGDIR/$TASK_ID.$STAMP.stderr.log"
RC=$?
set -e
USAGE=$(grep '"turn.completed"' "$LOGDIR/$TASK_ID.$STAMP.events.jsonl" | tail -1 | sed -E 's/.*"usage":(\{[^}]*\}).*/\1/')
[[ -z "$USAGE" ]] && USAGE=null
THREAD=$(grep -o '"thread_id":"[^"]*"' "$LOGDIR/$TASK_ID.$STAMP.events.jsonl" | head -1 | cut -d'"' -f4)
echo "{\"task_id\":\"$TASK_ID\",\"exit_code\":$RC,\"thread_id\":\"$THREAD\",\"usage\":$USAGE,\"finished_utc\":\"$(date -u +%Y%m%dT%H%M%SZ)\",\"actual_model_disclosed\":false}" > "$LOGDIR/$TASK_ID.$STAMP.exit.json"
echo "task=$TASK_ID rc=$RC workdir=$WORKDIR log=$LOGDIR/$TASK_ID.$STAMP.*"
exit $RC
