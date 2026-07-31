#!/usr/bin/env python3
"""Manual socket-driven verification for Cmd+[ / Cmd+] global workspace history.

Run against a tagged build:
  CMUX_SOCKET_PATH=/tmp/cmux-debug-cbrk.sock python3 tests_v2/verify_cbrk_manual.py

NOT a CI test; evidence script for the feat-cmd-bracket-workspace-history PR.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cmux import cmux  # noqa: E402


def selected_ws(c):
    rows = c.list_workspaces()
    for _idx, wsid, title, selected in rows:
        if selected:
            return wsid, title
    return None, None


def main():
    c = cmux()
    c.connect()
    assert c.ping(), "socket ping failed"
    c.activate_app()
    time.sleep(0.3)

    base_ws, base_title = selected_ws(c)
    print(f"start: selected={base_ws} ({base_title!r})")

    # Create three workspaces; each create+select records focus history.
    created = []
    for i in range(3):
        wsid = c.new_workspace()
        c.select_workspace(wsid)
        c.rename_workspace(f"cbrk-ws{i+1}", wsid)
        created.append(wsid)
        time.sleep(0.2)
    print(f"created: {created}")

    # Walk focus between them so history is ws1 -> ws2 -> ws3.
    for wsid in created:
        c.select_workspace(wsid)
        time.sleep(0.15)

    cur, _ = selected_ws(c)
    assert cur == created[2], f"expected focus on ws3, got {cur}"
    print("focus on ws3, driving cmd+[ back...")

    trail_back = []
    for _ in range(4):
        c.simulate_shortcut("cmd+[")
        time.sleep(0.35)
        cur, title = selected_ws(c)
        trail_back.append((cur, title))
        print(f"  cmd+[ -> {cur} ({title!r})")

    print("driving cmd+] forward...")
    trail_fwd = []
    for _ in range(4):
        c.simulate_shortcut("cmd+]")
        time.sleep(0.35)
        cur, title = selected_ws(c)
        trail_fwd.append((cur, title))
        print(f"  cmd+] -> {cur} ({title!r})")

    back_ids = [w for w, _ in trail_back]
    fwd_ids = [w for w, _ in trail_fwd]

    ok_back = back_ids[0] == created[1] and back_ids[1] == created[0]
    ok_fwd = created[1] in fwd_ids and created[2] in fwd_ids
    print(f"back walk crosses workspaces: {ok_back}")
    print(f"forward walk crosses workspaces: {ok_fwd}")

    # Closed-workspace skip: focus ws3, close ws2, then back should skip to ws1.
    c.select_workspace(created[2])
    time.sleep(0.2)
    c._call("workspace.close", {"workspace_id": created[1], "force": True})
    time.sleep(0.4)
    c.simulate_shortcut("cmd+[")
    time.sleep(0.35)
    cur, title = selected_ws(c)
    skip_ok = cur != created[1]
    print(f"after closing ws2, cmd+[ lands on {cur} ({title!r}); skipped closed ws: {skip_ok}")

    print("PASS" if (ok_back and ok_fwd and skip_ok) else "FAIL")
    return 0 if (ok_back and ok_fwd and skip_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
