"""checks.py against real alert-log entries (2 and 14 Oct 2026) and edge cases."""
import json
from datetime import datetime, timezone

import pytest

import checks

LIVE_OLD = ("QuantC ORB Long MES v2 (validated) - Ghost (Accessible) "
            "(2, 625, 90, 300, Top Right, 20, Large, 3): Any alert() function call")
LIVE_NEW = ("QuantC ORB Long MES v2 (validated) - Ghost (Accessible) "
            "(1, 625, 90, 300, 90, Top Right, 20, Large, 3): Any alert() function call")
DEMO_BUY = "QC Trend DEMO test BUY (dry run)"


def T(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def alert(aid, name, active, created="2026-10-10T00:00:00Z", exp="2026-12-31T00:00:00Z"):
    return {"alert_id": aid, "name": name, "active": active,
            "create_time": created, "expiration": exp}


def ev(name, bar, fired, message, res="1", aid=1):
    return {"name": name, "bar_time": bar, "fired_at": fired, "resolution": res,
            "message": json.dumps(message), "tv_alert_id": aid}


# --- alert audit ------------------------------------------------------------
def test_qty_parsed_from_real_alert_name():
    assert checks.qty_from_name(LIVE_OLD) == 2
    assert checks.qty_from_name(LIVE_NEW) == 1
    assert checks.qty_from_name(DEMO_BUY) is None


def test_old_qty2_alert_fails_pretrade_size_gate():
    a = checks.audit_alerts([alert(5571966155, LIVE_OLD, False, "2026-09-09T14:02:51Z",
                                   "2026-11-25T07:16:34Z")], T("2026-10-15T12:45:00Z"))
    assert a["status"] == "FAIL" and a["reason"] == "qty_2_in_alert_inputs"
    assert a["guard_version"] is False


def test_guard_alert_at_qty1_passes():
    a = checks.audit_alerts([alert(9, LIVE_NEW, False, "2026-10-16T21:00:00Z")],
                            T("2026-10-19T12:45:00Z"))
    assert a["status"] == "PASS" and a["guard_version"] is True and a["qty"] == 1


def test_pre_guard_build_at_qty1_still_fails():
    old_qty1 = LIVE_OLD.replace("(2, 625", "(1, 625")
    a = checks.audit_alerts([alert(5571966155, old_qty1, False, "2026-09-09T14:02:51Z")],
                            T("2026-10-15T12:45:00Z"))
    assert a["status"] == "FAIL" and a["reason"] == "no_stale_data_guard"


def test_two_active_live_alerts_is_urgent():
    a = checks.audit_alerts([alert(1, LIVE_OLD, True), alert(2, LIVE_NEW, True)],
                            T("2026-10-15T12:45:00Z"))
    assert a["status"] == "FAIL_URGENT" and sorted(a["active_ids"]) == [1, 2]


def test_expiry_warn_and_fail():
    now = T("2026-10-15T12:45:00Z")
    warn = checks.audit_alerts([alert(1, LIVE_NEW, True, exp="2026-10-20T00:00:00Z")], now)
    assert warn["status"] == "WARN"
    fail = checks.audit_alerts([alert(1, LIVE_NEW, True, exp="2026-10-15T15:00:00Z")], now)
    assert fail["status"] == "FAIL" and fail["reason"] == "expires_before_close"


def test_missing_live_alert():
    assert checks.audit_alerts([alert(1, DEMO_BUY, True)], T("2026-10-15T12:45:00Z"))["reason"] \
        == "no_live_alert"


# --- latency (bar freshness) --------------------------------------------------
def test_fresh_bars_pass():
    ohlcv = {"bars": {"t": [1792021320, 1792021380]}}       # real, 14 Oct 23:42-23:43 UTC
    lat = checks.latency(ohlcv, datetime.fromtimestamp(1792021385, timezone.utc))
    assert lat == {"freshness_s": 5, "status": "PASS"}


def test_delayed_feed_fails():
    ohlcv = {"bars": [{"t": 1792021380 - 660}]}             # ~11 min old: the Sep 2026 delayed feed
    lat = checks.latency(ohlcv, datetime.fromtimestamp(1792021385, timezone.utc))
    assert lat["status"] == "FAIL" and lat["freshness_s"] == 665


def test_no_evidence_is_fail_unknown():
    assert checks.latency(None, T("2026-10-15T12:45:00Z"))["status"] == "FAIL_UNKNOWN"
    assert checks.latency({"bars": []}, T("2026-10-15T12:45:00Z"))["status"] == "FAIL_UNKNOWN"


# --- verdict ------------------------------------------------------------------
GOOD_RISK = {"tripped": []}
FRESH = {"bars": {"t": [int(T("2026-10-19T12:44:00Z").timestamp())]}}


def test_go_before_open_ensures_active(tmp_path):
    out = checks.gonogo([alert(9, LIVE_NEW, False)], FRESH, T("2026-10-19T12:45:00Z"),
                        ops_dir=str(tmp_path), risk=GOOD_RISK)
    assert out["verdict"] == "GO" and out["action"] == {"do": "ensure_active", "alert_ids": [9]}


def test_risk_pause_file_is_no_go_and_stops(tmp_path):
    (tmp_path / "RISK_PAUSE").write_text("rule: R5_size\n")
    out = checks.gonogo([alert(9, LIVE_NEW, True)], FRESH, T("2026-10-19T12:45:00Z"),
                        ops_dir=str(tmp_path), risk=GOOD_RISK)
    assert out["verdict"] == "NO-GO" and out["action"]["do"] == "ensure_stopped"
    assert out["action"]["alert_ids"] == [9]


def test_hold_is_no_go(tmp_path):
    (tmp_path / "HOLD").write_text("user hold\n")
    out = checks.gonogo([alert(9, LIVE_NEW, False)], FRESH, T("2026-10-19T12:45:00Z"),
                        ops_dir=str(tmp_path), risk=GOOD_RISK)
    assert out["fails"] == ["hold"]


def test_retired_probes_have_no_effect(tmp_path):
    # The DEMO probes left on the account on 15 Oct (silent, expiring) change nothing.
    now = T("2026-10-15T12:45:00Z")
    probes = [dict(alert(5662914432, "QC Trend DEMO test SELL (dry run)", True,
                         exp="2026-10-21T15:11:10Z"), last_fire_time="2026-10-02T15:09:00Z")]
    fresh = {"bars": {"t": [int(T("2026-10-15T12:44:30Z").timestamp())]}}
    out = checks.gonogo([alert(9, LIVE_NEW, False)] + probes, fresh, now,
                        ops_dir=str(tmp_path), risk=GOOD_RISK)
    assert out["verdict"] == "GO" and out["warn"] == []


def test_expiring_live_alert_warns_but_goes(tmp_path):
    out = checks.gonogo([alert(9, LIVE_NEW, False, exp="2026-10-25T00:00:00Z")], FRESH,
                        T("2026-10-19T12:45:00Z"), ops_dir=str(tmp_path), risk=GOOD_RISK)
    assert out["verdict"] == "GO" and out["warn"] == ["alert_expires_within_10_days"]


def test_stale_bars_are_no_go(tmp_path):
    stale = {"bars": {"t": [int(T("2026-10-19T12:34:00Z").timestamp())]}}
    out = checks.gonogo([alert(9, LIVE_NEW, True)], stale, T("2026-10-19T12:45:00Z"),
                        ops_dir=str(tmp_path), risk=GOOD_RISK)
    assert out["fails"] == ["latency_fail"] and out["action"]["do"] == "ensure_stopped"


def test_never_touch_after_open(tmp_path):
    out = checks.gonogo([alert(9, LIVE_NEW, False)], FRESH, T("2026-10-19T13:31:00Z"),
                        ops_dir=str(tmp_path), risk=GOOD_RISK)
    assert out["action"]["do"] == "none"


def test_duplicates_stop_even_after_open(tmp_path):
    out = checks.gonogo([alert(1, LIVE_OLD, True), alert(2, LIVE_NEW, True)], FRESH,
                        T("2026-10-19T14:00:00Z"), ops_dir=str(tmp_path), risk=GOOD_RISK)
    assert out["action"]["do"] == "stop" and out["action"]["urgent"] is True


# --- close reconcile ----------------------------------------------------------
BUY_2OCT = ev(LIVE_OLD, "2026-10-02T13:45:00Z", "2026-10-02T13:46:00Z",
              {"action": "buy", "price": 7801.75, "qty": 2, "sl": 7676.75,
               "time": "2026-10-02T13:46:00Z"}, aid=5571966155)
EXIT_2OCT = ev(LIVE_OLD, "2026-10-02T15:15:00Z", "2026-10-02T15:16:00Z",
               {"action": "exit", "reason": "time_exit_90min", "time": "2026-10-02T15:16:00Z"},
               aid=5571966155)
SHADOW_2OCT = {"state": "entry", "entry": 7801.75, "entry_bar_open_et": "09:45",
               "exit": 7769, "exit_bar_open_et": "11:15", "exit_reason": "time_exit_90min"}


def test_real_2oct_live_trade_flags_size_only():
    r = checks.reconcile([BUY_2OCT, EXIT_2OCT], SHADOW_2OCT, "2026-10-02", True)
    assert r["status"] == "live" and r["flags"] == ["size_qty2"]
    assert r["buy_lag_s"] == 0 and r["exit_lag_s"] == 0


def test_buy_without_exit_is_urgent():
    r = checks.reconcile([BUY_2OCT], SHADOW_2OCT, "2026-10-02", True)
    assert r["flags"][0] == "URGENT_possibly_in_position"


def test_missed_entry_vs_stale_skip_vs_shadow():
    assert checks.reconcile([], SHADOW_2OCT, "2026-10-02", True)["status"] == "missed"
    assert checks.reconcile([], SHADOW_2OCT, "2026-10-02", True, 600)["status"] == "stale_skip"
    assert checks.reconcile([], SHADOW_2OCT, "2026-10-02", False)["status"] == "shadow"


def test_exit_mismatch_and_late_fire():
    late = ev(LIVE_NEW, "2026-10-02T15:15:00Z", "2026-10-02T15:18:00Z",
              {"action": "exit", "reason": "session_close", "time": "2026-10-02T15:16:00Z"})
    buy1 = ev(LIVE_NEW, "2026-10-02T13:45:00Z", "2026-10-02T13:46:00Z",
              {"action": "buy", "price": 7801.75, "qty": 1, "time": "2026-10-02T13:46:00Z"})
    r = checks.reconcile([buy1, late], SHADOW_2OCT, "2026-10-02", True)
    assert "exit_mismatch" in r["flags"] and "late_fire" in r["flags"]


def test_stop_then_exit_is_flat_account_note_not_mismatch():
    shadow = dict(SHADOW_2OCT, exit_reason="stop", exit=7676.75)
    r = checks.reconcile([BUY_2OCT, EXIT_2OCT], shadow, "2026-10-02", True)
    assert "exit_mismatch" not in r["flags"] and any("Phase 1 D" in n for n in r["notes"])


def test_duplicate_buys_urgent_and_test_mode():
    b2 = dict(BUY_2OCT, fired_at="2026-10-02T13:47:00Z", tv_alert_id=7)
    t = json.loads(b2["message"]); t["test"] = True; b2["message"] = json.dumps(t)
    r = checks.reconcile([BUY_2OCT, b2, EXIT_2OCT], SHADOW_2OCT, "2026-10-02", True)
    assert "URGENT_duplicate_orders" in r["flags"] and "test_mode" in r["flags"]


def test_unexpected_entry():
    r = checks.reconcile([BUY_2OCT, EXIT_2OCT], {"state": "no_breakout"}, "2026-10-02", True)
    assert "unexpected_entry" in r["flags"]


def test_cli_roundtrip(tmp_path, capsys):
    (tmp_path / "a.json").write_text(json.dumps({"alerts": [alert(5571966155, LIVE_OLD, True)]}))
    (tmp_path / "l.json").write_text(json.dumps({"events": [BUY_2OCT, EXIT_2OCT]}))
    (tmp_path / "s.json").write_text(json.dumps(SHADOW_2OCT))
    assert checks.main(["close", "--alerts", str(tmp_path / "a.json"), "--log",
                        str(tmp_path / "l.json"), "--shadow", str(tmp_path / "s.json"),
                        "--date", "2026-10-02"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "live" and out["alert_active"] is True


# --- 9:50 watch -------------------------------------------------------------
NOW_950 = T("2026-10-15T13:50:00Z")
GUARDED = alert(9001, LIVE_NEW, True, "2026-10-15T00:00:00Z")


def buy_today(qty=1, aid=9001):
    return ev(LIVE_NEW, "2026-10-15T13:45:00Z", "2026-10-15T13:46:01Z",
              {"action": "buy", "price": 7850, "qty": qty, "sl": 7725,
               "time": "2026-10-15T13:46:00Z"}, aid=aid)


def test_watch_quiet_on_go_day_with_guarded_alert(tmp_path):
    r = checks.watch([GUARDED], [buy_today()], NOW_950, ops_dir=str(tmp_path), verdict="GO")
    assert r["status"] == "OK" and not r["notify"] and r["action"]["do"] == "none"


def test_watch_urgent_when_alert_active_on_nogo_day(tmp_path):
    r = checks.watch([GUARDED], [], NOW_950, ops_dir=str(tmp_path), verdict="NO-GO")
    assert r["urgent"] == ["alert_active_on_nogo_day"] and r["notify"]


def test_watch_reads_verdict_from_log_and_missing_row_is_urgent(tmp_path):
    log = tmp_path / "golive_log.csv"
    log.write_text("date,verdict\n2026-10-14,NO-GO\n")
    r = checks.watch([GUARDED], [], NOW_950, ops_dir=str(tmp_path))
    assert r["verdict_845"] is None and "alert_active_on_no_verdict_day" in r["urgent"]
    log.write_text("date,verdict\n2026-10-15,GO\n")
    assert checks.watch([GUARDED], [], NOW_950, ops_dir=str(tmp_path))["status"] == "OK"


def test_watch_replays_2oct_reactivation(tmp_path):
    # 2 Oct: risk pause on, the old qty-2 alert reactivated and traded
    (tmp_path / "RISK_PAUSE").write_text("R5")
    old = alert(5571966155, LIVE_OLD, True, "2026-09-09T14:02:51Z")
    r = checks.watch([old], [BUY_2OCT], T("2026-10-02T13:50:00Z"),
                     ops_dir=str(tmp_path), verdict="NO-GO")
    for f in ("alert_active_on_nogo_day", "alert_active_during_risk_pause",
              "active_alert_qty_2", "active_alert_has_no_stale_guard",
              "live_entry_on_nogo_day", "live_entry_qty_2"):
        assert f in r["urgent"]


def test_watch_duplicates_and_inactive_go_day(tmp_path):
    r = checks.watch([GUARDED, dict(GUARDED, alert_id=9002)], [], NOW_950,
                     ops_dir=str(tmp_path), verdict="GO")
    assert "duplicate_orders_possible" in r["urgent"]
    r = checks.watch([dict(GUARDED, active=False)], [], NOW_950,
                     ops_dir=str(tmp_path), verdict="GO")
    assert r["status"] == "WARN" and r["warn"] == ["alert_inactive_on_go_day"]


def test_watch_ignores_yesterdays_fires_and_inactive_nogo_is_ok(tmp_path):
    r = checks.watch([dict(GUARDED, active=False)], [BUY_2OCT], NOW_950,
                     ops_dir=str(tmp_path), verdict="NO-GO")
    assert r["status"] == "OK" and r["live_buys"] == 0


def test_watch_cli(tmp_path, capsys):
    (tmp_path / "a.json").write_text(json.dumps({"alerts": [GUARDED]}))
    (tmp_path / "l.json").write_text(json.dumps({"events": []}))
    (tmp_path / "golive_log.csv").write_text("date,verdict\n2026-10-15,NO-GO\n")
    assert checks.main(["watch", "--alerts", str(tmp_path / "a.json"), "--log",
                        str(tmp_path / "l.json"), "--now", "2026-10-15T13:50:00Z",
                        "--ops-dir", str(tmp_path)]) == 0
    assert json.loads(capsys.readouterr().out)["notify"] is True
