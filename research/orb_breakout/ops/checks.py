"""Deterministic checks for the MES v2 routines (GO_NO_GO.md, CLOSE_ROUTINE.md).

The routines fetch data with the TradingView MCP and save each result as a
JSON file. This script turns those files into the verdict, so the decision
is the same every time and is covered by tests (tests/test_checks.py).
Claude still runs the MCP calls and takes the action the output names.

    python3 ops/checks.py gonogo --alerts alerts.json \
        [--ohlcv mes.json] [--now 2026-10-15T12:45:00Z] [--ops-dir DIR]
    python3 ops/checks.py close --alerts alerts.json --log log.json \
        --shadow shadow.json --date 2026-10-15 [--morning-fresh-s N]
    python3 ops/checks.py watch --alerts alerts.json --log log.json \
        [--now ...] [--ops-dir DIR]          # 9:50 ET read-only watch (WATCH.md)

alerts.json = mcp-tv-list-alerts, log.json = mcp-tv-get-alerts-log (2 days),
mes.json = mcp-tv-get-ohlcv CME_MINI:MES1! 1m (rows or columns),
shadow.json = shadow_day.py output. Each command prints one JSON object.
"""
import argparse
import csv
import json
import os
import re
import sys
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
ET = ZoneInfo("America/New_York")

LIVE_NAME = "QuantC ORB Long MES v2 (validated) - Ghost (Accessible)"
GUARD_DEPLOYED = "2026-09-26"   # alerts created on/after this run the stale-data guard
MAX_FRESHNESS_S = 120           # check 2: age of the newest MES 1m bar
EXPIRY_WARN_DAYS = 10
LATE_FIRE_S = 90                # close check item 6
TICK = 0.25


def ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def iso(d):
    return d.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def msg(event):
    try:
        return json.loads(event.get("message") or "{}")
    except ValueError:
        return {}


def is_live(name):
    return (name or "").startswith(LIVE_NAME)


def qty_from_name(name):
    """TradingView appends the script's inputs to the alert name, e.g.
    '... (Accessible) (2, 625, 90, ...)'. The first input is qty."""
    m = re.match(re.escape(LIVE_NAME) + r"\s*\((\d+)\s*,", name or "")
    return int(m.group(1)) if m else None


# --------------------------------------------------------------------------
# go/no-go check 3 + 4: the live alert
# --------------------------------------------------------------------------
def audit_alerts(alerts, now):
    live = [a for a in alerts if is_live(a.get("name"))]
    active = [a for a in live if a.get("active")]
    out = {"live_alerts": len(live), "active_ids": [a["alert_id"] for a in active]}
    if len(active) > 1:
        out.update(status="FAIL_URGENT", reason="duplicate_active_live_alerts")
        return out
    if not live:
        out.update(status="FAIL", reason="no_live_alert")
        return out
    # the one to judge: the active one, else the newest
    a = active[0] if active else max(live, key=lambda x: x.get("create_time", ""))
    qty = qty_from_name(a["name"])
    exp = ts(a["expiration"]) if a.get("expiration") else None
    close_today = datetime.combine(now.astimezone(ET).date(), time(16, 0), ET)
    out.update(alert_id=a["alert_id"], active=bool(a.get("active")), qty=qty,
               guard_version=a.get("create_time", "")[:10] >= GUARD_DEPLOYED,
               expiry=iso(exp)[:10] if exp else None,
               days_to_expiry=round((exp - now).total_seconds() / 86400, 1) if exp else None)
    if len(live) > 1:
        out["note"] = f"{len(live)} alerts carry the live name (one active at most)"
    if qty != 1:
        # Pre-trade size gate: R5 only catches a wrong size after a trade.
        out.update(status="FAIL", reason=f"qty_{qty}_in_alert_inputs")
    elif not out["guard_version"]:
        # A pre-guard build trades on a delayed feed with nothing to stop it.
        out.update(status="FAIL", reason="no_stale_data_guard")
    elif exp is not None and exp < close_today:
        out.update(status="FAIL", reason="expires_before_close")
    elif exp is not None and (exp - now) <= timedelta(days=EXPIRY_WARN_DAYS):
        out.update(status="WARN", reason="expires_within_10_days")
    else:
        out["status"] = "PASS"
    return out


# --------------------------------------------------------------------------
# go/no-go check 2: data latency (bar freshness; the DEMO probes were retired
# in D-018 - the live script's stale guard measures lag on every entry)
# --------------------------------------------------------------------------
def last_bar_open(ohlcv):
    bars = ohlcv.get("bars")
    if isinstance(bars, dict):
        return max(bars["t"]) if bars.get("t") else None
    if isinstance(bars, list) and bars:
        return max(b["t"] for b in bars)
    return None


def latency(ohlcv, now):
    t = last_bar_open(ohlcv) if ohlcv else None
    fresh = round(now.timestamp() - t) if t is not None else None
    if fresh is None:
        status = "FAIL_UNKNOWN"
    else:
        status = "FAIL" if fresh > MAX_FRESHNESS_S else "PASS"
    return {"freshness_s": fresh, "status": status}


# --------------------------------------------------------------------------
# go/no-go verdict
# --------------------------------------------------------------------------
def risk_state(asof, ops_dir=HERE):
    sys.path.insert(0, HERE)            # risk_state.py sits next to this file
    import risk_state as rs
    return rs.evaluate(asof, ops_dir)


def gonogo(alerts, ohlcv, now, ops_dir=HERE, risk=None):
    asof = now.astimezone(ET).date().isoformat()
    hold = os.path.exists(os.path.join(ops_dir, "HOLD"))
    pause = os.path.exists(os.path.join(ops_dir, "RISK_PAUSE"))
    risk = risk if risk is not None else risk_state(asof, ops_dir)
    lat = latency(ohlcv, now)
    alert = audit_alerts(alerts, now)

    fails = []
    if hold:
        fails.append("hold")
    if pause or risk.get("tripped"):
        fails.append("risk_pause")
    if lat["status"] != "PASS":
        fails.append("latency_" + lat["status"].lower())
    if alert["status"] not in ("PASS", "WARN"):
        fails.append("alert_" + alert.get("reason", alert["status"].lower()))
    verdict = "GO" if not fails else "NO-GO"
    warn = ["alert_" + alert.get("reason", "warn")] if alert["status"] == "WARN" else []

    after_open = now.astimezone(ET).time() >= time(9, 30)
    if alert["status"] == "FAIL_URGENT":
        action = {"do": "stop", "alert_ids": alert["active_ids"], "urgent": True}
    elif after_open:
        action = {"do": "none", "why": "after 9:30 ET - never touch the alert"}
    elif verdict == "GO":
        action = {"do": "ensure_active", "alert_ids": [alert["alert_id"]]}
    else:
        action = {"do": "ensure_stopped", "alert_ids": alert["active_ids"]}

    return {"date": asof, "verdict": verdict, "fails": fails, "warn": warn,
            "action": action, "latency": lat, "alert": alert, "hold": hold, "risk_pause_file": pause,
            "risk": risk}


# --------------------------------------------------------------------------
# close routine section 2: reconcile live fires with the shadow replay
# --------------------------------------------------------------------------
def et_hhmm(d):
    return d.astimezone(ET).strftime("%H:%M")


def plus_1min(hhmm):
    h, m = map(int, hhmm.split(":"))
    return (datetime(2000, 1, 1, h, m) + timedelta(minutes=1)).strftime("%H:%M")


def reconcile(events, shadow, day, alert_active, morning_fresh_s=None):
    todays = [e for e in events if is_live(e.get("name"))
              and ts(e["fired_at"]).astimezone(ET).date().isoformat() == day]
    todays.sort(key=lambda e: e["fired_at"])
    buys = [(e, msg(e)) for e in todays if msg(e).get("action") == "buy"]
    exits = [(e, msg(e)) for e in todays if msg(e).get("action") == "exit"]
    shadow_entry = shadow.get("state") in ("entry", "open")

    def lag(e, m):
        return (ts(e["fired_at"]) - ts(m["time"])).total_seconds() if m.get("time") else None

    flags, notes = [], []
    if buys:
        last_buy = buys[-1][0]["fired_at"]
        if not any(e["fired_at"] > last_buy for e, _ in exits):
            flags.append("URGENT_possibly_in_position")
            if shadow.get("exit_reason") == "stop":
                notes.append("shadow says stopped out - still confirm flat in Tradovate")
    if len(buys) > 1 or len({e["tv_alert_id"] for e in todays}) > 1:
        flags.append("URGENT_duplicate_orders")

    buy = buys[0] if buys else None
    if shadow_entry and not buy:
        if alert_active and morning_fresh_s is not None and morning_fresh_s > LATE_FIRE_S:
            notes.append("entry missed - stale guard most likely blocked it (expected)")
            status = "stale_skip"
        elif alert_active:
            flags.append("missed_entry")
            status = "missed"
        else:
            status = "shadow"
    elif buy:
        status = "live"
        e, m = buy
        if not shadow_entry:
            flags.append("unexpected_entry")
        else:
            if abs(float(m.get("price", 0)) - shadow["entry"]) > TICK + 1e-9:
                flags.append("unexpected_entry_price")
            if m.get("time") and et_hhmm(ts(m["time"])) != plus_1min(shadow["entry_bar_open_et"]):
                flags.append("entry_bar_mismatch")
    else:
        status = shadow.get("state", "no_breakout")

    for e, m in exits:
        if shadow.get("exit_reason") == "stop":
            notes.append("flat-account exit after the Ghost stop (Phase 1 D)")
            break
        want = shadow.get("exit_reason")
        if want and (m.get("reason") != want or
                     (m.get("time") and shadow.get("exit_bar_open_et") and
                      et_hhmm(ts(m["time"])) != plus_1min(shadow["exit_bar_open_et"]))):
            flags.append("exit_mismatch")
        break

    buy_lag = lag(*buy) if buy else None
    exit_lag = lag(*exits[0]) if exits else None
    for x in (buy_lag, exit_lag):
        if x is not None and x > LATE_FIRE_S:
            flags.append("late_fire")
            break
    if any(m.get("test") is True for _, m in buys + exits):
        flags.append("test_mode")
    qty = buy[1].get("qty") if buy else None
    if qty is not None and str(qty) != "1":
        flags.append(f"size_qty{qty}")

    return {"date": day, "status": status, "flags": flags, "notes": notes,
            "buy_lag_s": buy_lag, "exit_lag_s": exit_lag,
            "qty": qty, "live_buys": len(buys), "live_exits": len(exits)}


# --------------------------------------------------------------------------
# 9:50 ET watch (WATCH.md): read-only, never touches an alert
# --------------------------------------------------------------------------
def morning_verdict(day, ops_dir=HERE):
    """Today's verdict from golive_log.csv, or None when 8:45 logged nothing."""
    path = os.path.join(ops_dir, "golive_log.csv")
    if not os.path.exists(path):
        return None
    with open(path, newline="") as f:
        rows = [r for r in csv.DictReader(f) if r.get("date") == day]
    return rows[-1]["verdict"] if rows else None


def watch(alerts, events, now, ops_dir=HERE, verdict=False):
    day = now.astimezone(ET).date().isoformat()
    if verdict is False:
        verdict = morning_verdict(day, ops_dir)
    hold = os.path.exists(os.path.join(ops_dir, "HOLD"))
    pause = os.path.exists(os.path.join(ops_dir, "RISK_PAUSE"))
    live = [a for a in alerts if is_live(a.get("name"))]
    active = [a for a in live if a.get("active")]
    todays = [e for e in events if is_live(e.get("name"))
              and ts(e["fired_at"]).astimezone(ET).date().isoformat() == day]
    buys = [msg(e) for e in todays if msg(e).get("action") == "buy"]
    exits = [msg(e) for e in todays if msg(e).get("action") == "exit"]
    sources = {e.get("tv_alert_id") for e in todays}

    urgent, warn = [], []
    if len(active) > 1 or len(sources) > 1 or len(buys) > 1:
        urgent.append("duplicate_orders_possible")
    if active and verdict != "GO":
        # covers NO-GO, SKIP and a missing 8:45 row
        urgent.append("alert_active_on_" + ("no_verdict" if verdict is None
                                            else verdict.lower().replace("-", "")) + "_day")
    if active and (hold or pause):
        urgent.append("alert_active_during_" + ("hold" if hold else "risk_pause"))
    for a in active:
        q = qty_from_name(a["name"])
        if q != 1:
            urgent.append(f"active_alert_qty_{q}")
        if a.get("create_time", "")[:10] < GUARD_DEPLOYED:
            urgent.append("active_alert_has_no_stale_guard")
    if buys and verdict != "GO":
        urgent.append("live_entry_on_" + ("no_verdict" if verdict is None
                                          else verdict.lower().replace("-", "")) + "_day")
    for m in buys:
        if m.get("qty") is not None and str(m["qty"]) != "1":
            urgent.append(f"live_entry_qty_{m['qty']}")
    if any(m.get("test") is True for m in buys + exits):
        warn.append("live_alert_in_test_mode")
    if verdict == "GO" and not active:
        warn.append("alert_inactive_on_go_day")

    urgent = list(dict.fromkeys(urgent))
    status = "URGENT" if urgent else "WARN" if warn else "OK"
    return {"date": day, "checked_at": iso(now), "verdict_845": verdict,
            "status": status, "urgent": urgent, "warn": warn,
            "active_ids": [a["alert_id"] for a in active],
            "live_buys": len(buys), "live_exits": len(exits),
            "notify": bool(urgent),
            "action": {"do": "none",
                       "why": "read-only: stopping mid-session can orphan an open trade's exit"}}


# --------------------------------------------------------------------------
def load(path):
    with open(path) as f:
        data = json.load(f)
    return data


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("gonogo")
    g.add_argument("--alerts", required=True)
    g.add_argument("--ohlcv")
    g.add_argument("--now")
    g.add_argument("--ops-dir", default=HERE,
                   help="where the state lives (HOLD, RISK_PAUSE, journal.csv ...): the "
                        "working-branch checkout, when this script was copied from main")
    c = sub.add_parser("close")
    c.add_argument("--alerts", required=True)
    c.add_argument("--log", required=True)
    c.add_argument("--shadow", required=True)
    c.add_argument("--date", required=True)
    c.add_argument("--morning-fresh-s", type=float)
    w = sub.add_parser("watch")
    w.add_argument("--alerts", required=True)
    w.add_argument("--log", required=True)
    w.add_argument("--now")
    w.add_argument("--ops-dir", default=HERE)
    a = ap.parse_args(argv)

    alerts = load(a.alerts).get("alerts", [])
    events = load(a.log).get("events", []) if a.cmd != "gonogo" else []
    if a.cmd == "gonogo":
        now = ts(a.now) if a.now else datetime.now(timezone.utc)
        ohlcv = load(a.ohlcv) if a.ohlcv else None
        out = gonogo(alerts, ohlcv, now, ops_dir=a.ops_dir)
    elif a.cmd == "watch":
        now = ts(a.now) if a.now else datetime.now(timezone.utc)
        out = watch(alerts, events, now, ops_dir=a.ops_dir)
    else:
        live = [x for x in alerts if is_live(x.get("name"))]
        active = any(x.get("active") for x in live)
        out = reconcile(events, load(a.shadow), a.date, active, a.morning_fresh_s)
        out["alert_active"] = active if live else "missing"
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
