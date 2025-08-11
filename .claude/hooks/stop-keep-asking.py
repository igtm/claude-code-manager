#!/usr/bin/env python3
import json, sys, os, io
from pathlib import Path

STATE_FILE = Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())) / ".claude" / "manager_state.json"

MAX_ASK = 3
DONE_TOKEN = "CLAUDE_MANAGER_DONE"


def load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(s):
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(s, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def transcript_has_done(path: str, token: str) -> bool:
    if not path:
        return False
    try:
        p = os.path.expanduser(path)
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if token in line:
                    return True
    except Exception:
        return False
    return False


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        # invalid input, do nothing
        sys.exit(0)

    sid = data.get("session_id") or ""
    transcript_path = data.get("transcript_path") or ""

    # If DONE token already present, allow stop
    if transcript_has_done(transcript_path, DONE_TOKEN):
        print(json.dumps({"continue": True, "suppressOutput": True}, ensure_ascii=False))
        return

    # Count per-session asks
    state = load_state()
    key = f"{sid}:asks"
    cnt = int(state.get(key, 0))
    if cnt < MAX_ASK:
        state[key] = cnt + 1
        save_state(state)
        print(json.dumps({
            "decision": "block",
            "reason": f"続けて。実装が終了し終わっていたら、{DONE_TOKEN}と返して。",
            "suppressOutput": True
        }, ensure_ascii=False))
        return

    # Max reached: allow stop
    print(json.dumps({"continue": True, "suppressOutput": True}, ensure_ascii=False))

if __name__ == "__main__":
    main()
