#!/usr/bin/env python3
"""Stop hook: reminds the main Claude session to write a log entry before exiting.

Outputs JSON {"decision": "block", "reason": "..."} once if no log was written yet.
Approves on the second call (lock file) so there's no infinite loop.
"""
import sys
import json
import os
from datetime import date


def main():
    payload = json.load(sys.stdin)
    transcript_path = payload.get("transcript_path", "")

    if not transcript_path or not os.path.exists(transcript_path):
        print(json.dumps({"decision": "approve"}))
        return

    # Only block once per transcript to avoid infinite loops
    lock = f"/tmp/study-stop-{os.path.basename(transcript_path)}.blocked"
    if os.path.exists(lock):
        print(json.dumps({"decision": "approve"}))
        return

    # Check if any Write/Edit to logs/ already happened this session
    wrote_log = False
    with open(transcript_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
                if event.get("type") == "tool_use" and event.get("name") in ("Write", "Edit"):
                    path = event.get("input", {}).get("file_path", "")
                    if "/logs/" in path:
                        wrote_log = True
                        break
            except (json.JSONDecodeError, KeyError):
                pass

    if wrote_log:
        print(json.dumps({"decision": "approve"}))
        return

    # Block once and remind
    open(lock, "w").close()
    today = date.today().isoformat()
    log_path = f"/home/felix/Code/Misc/study/logs/{today}.md"
    print(json.dumps({
        "decision": "block",
        "reason": (
            f"Before exiting: check if a session log entry is owed and write it to {log_path}. "
            "Log-worthy: skill ran, repo files modified, wiki/todo/scripts/AGENTS.md edited, "
            "Query Protocol knowledge captured. Not log-worthy: single memory answer, trivial chitchat. "
            "Format: ## Session N — <Type> (HH:MM) with Files/Change/Why fields for changes, "
            "or skill-specific format for skill sessions. "
            "If nothing is log-worthy, you may exit without writing."
        ),
    }))


if __name__ == "__main__":
    main()
