"""Deterministic checks for the MES v2 routines (GO_NO_GO.md, CLOSE_ROUTINE.md).

The routines fetch data with the TradingView MCP and save each result as a
JSON file. This script turns those files into the verdict, so the decision
is the same every time and is covered by tests (tests/test_checks.py).
Claude still runs the MCP calls and takes the action the output names.

    python3 ops/checks.py gonogo --alerts alerts.json --log log.json \
        [--ohlcv mes.json] [--now 2026-10-15T12:45:00Z] [--ops-dir DIR]
    python3 ops/checks.py close --alerts alerts.json --log log.json \
        --shadow shadow.json --date 2026-10-15

alerts.json = mcp-tv-list-alerts, log.json = mcp-tv-get-alerts-log (2 days),
mes.json = mcp-tv-get-ohlcv CME_MINI:MES1! 1m (rows or columns),
shadow.json = shadow_day.py output. Each command prints one JSON object.
"""
import argparse
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
PROBE_WINDOW_H = 16
MAX_PROBE_LAG_S = 120           # check 2A: median probe lag
MAX_FRESHNESS_S = 120           # check 2B: age of the newest MES 1m bar
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
# go/no-go check 2: data latency
# --------------------------------------------------------------------------
def probe_window_start(now):
    n = now.astimezone(ET)
    if n.weekday() == 0:   # Monday: since Sunday's 6pm ET reopen
        sun = n.date() - timedelta(days=1)
        return datetime.combine(sun, time(18, 0), ET)
    return now - timedelta(hours=PROBE_WINDOW_H)


def is_probe(e):
    name = e.get("name") or ""
    if is_live(name):
        return False
    return "DEMO" in name or "PAPER TEST ONLY" in name or msg(e).get("test") is True


def probe_lags(events, now):
    start = probe_window_start(now)
    lags = []
    for e in events:
        if not is_probe(e) or not str(e.get("resolution", "")).isdigit():
            continue
        fired = ts(e["fired_at"])
        if not (start <= fired <= now):
            continue
        bar_close = ts(e["bar_time"]) + timedelta(minutes=int(e["resolution"]))
        lags.append((fired - bar_close).total_seconds())
    return sorted(lags)


def median(xs):
    n = len(xs)
    if not n:
        return None
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def last_bar_open(ohlcv):
    bars = ohlcv.get("bars")
    if isinstance(bars, dict):
        return max(bars["t"]) if bars.get("t") else None
    if isinstance(bars, list) and bars:
        return max(b["t"] for b in bars)
    return None


def latency(events, ohlcv, now):
    lags = probe_lags(events, now)
    med = median(lags)
    t = last_bar_open(ohlcv) if ohlcv else None
    fresh = round(now.timestamp() - t) if t is not None else None
    out = {"median_lag_s": med, "probe_fires": len(lags), "freshness_s": fresh}
    a_bad = med is not None and med > MAX_PROBE_LAG_S
    b_bad = fresh is not None and fresh > MAX_FRESHNESS_S
    if a_bad or b_bad:
        out["status"] = "FAIL"
    elif med is None and fresh is None:
        out["status"] = "FAIL_UNKNOWN"
    else:
        out["status"] = "PASS"
        if med is None:
            out["note"] = "B only"
    return out


# --------------------------------------------------------------------------
# go/no-go verdict
# --------------------------------------------------------------------------
def risk_state(asof, ops_dir=HERE):
    sys.path.insert(0, HERE)            # risk_state.py sits next to this file
    import risk_state as rs
    return rs.evaluate(asof, ops_dir)


def gonogo(alerts, events, ohlcv, now, ops_dir=HERE, risk=None):
    asof = now.astimezone(ET).date().isoformat()
    hold = os.path.exists(os.path.join(ops_dir, "HOLD"))
    pause = os.path.exists(os.path.join(ops_dir, "RISK_PAUSE"))
    risk = risk if risk is not None else risk_state(asof, ops_dir)
    lat = latency(events, ohlcv, now)
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

    after_open = now.astimezone(ET).time() >= time(9, 30)
    if alert["status"] == "FAIL_URGENT":
        action = {"do": "stop", "alert_ids": alert["active_ids"], "urgent": True}
    elif after_open:
        action = {"do": "none", "why": "after 9:30 ET - never touch the alert"}
    elif verdict == "GO":
        action = {"do": "ensure_active", "alert_ids": [alert["alert_id"]]}
    else:
        action = {"do": "ensure_stopped", "alert_ids": alert["active_ids"]}

    return {"date": asof, "verdict": verdict, "fails": fails, "action": action,
            "latency": lat, "alert": alert, "hold": hold, "risk_pause_file": pause,
            "risk": risk}


# --------------------------------------------------------------------------
# close routine section 2: reconcile live fires with the shadow replay
# --------------------------------------------------------------------------
def et_hhmm(d):
    return d.astimezone(ET).strftime("%H:%M")


def plus_1min(hhmm):
    h, m = map(int, hhmm.split(":"))
    return (datetime(2000, 1, 1, h, m) + timedelta(minutes=1)).strftime("%H:%M")


def reconcile(events, shadow, day, alert_active, morning_lag_s=None):
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
        if alert_active and morning_lag_s is not None and morning_lag_s > LATE_FIRE_S:
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
    g.add_argument("--log", required=True)
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
    c.add_argument("--morning-lag-s", type=float)
    a = ap.parse_args(argv)

    alerts = load(a.alerts).get("alerts", [])
    events = load(a.log).get("events", [])
    if a.cmd == "gonogo":
        now = ts(a.now) if a.now else datetime.now(timezone.utc)
        ohlcv = load(a.ohlcv) if a.ohlcv else None
        out = gonogo(alerts, events, ohlcv, now, ops_dir=a.ops_dir)
    else:
        live = [x for x in alerts if is_live(x.get("name"))]
        active = any(x.get("active") for x in live)
        out = reconcile(events, load(a.shadow), a.date, active, a.morning_lag_s)
        out["alert_active"] = active if live else "missing"
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
