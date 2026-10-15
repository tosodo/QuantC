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
NOISE = "QuantC Noise-Area MNQ - PAPER TEST ONLY: Any alert() function call"


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


# --- latency ------------------------------------------------------------------
REAL_DEMO_1OCT = [  # real fires, 1 Oct 2026, exactly on bar close (0 s lag)
    ev(DEMO_BUY, "2026-10-01T17:18:00Z", "2026-10-01T17:21:00Z", {"action": "buy", "test": True}, "3"),
    ev(DEMO_BUY, "2026-10-01T19:48:00Z", "2026-10-01T19:51:00Z", {"action": "buy", "test": True}, "3"),
    ev(DEMO_BUY, "2026-10-02T01:09:00Z", "2026-10-02T01:12:00Z", {"action": "buy", "test": True}, "3"),
]


def test_live_feed_probes_pass():
    lat = checks.latency(REAL_DEMO_1OCT, None, T("2026-10-02T12:45:00Z"))
    assert lat["status"] == "PASS" and lat["median_lag_s"] == 0 and lat["probe_fires"] == 1  # 17:21 and 19:51 are >16 h old


def test_delayed_feed_fails():
    delayed = [ev(DEMO_BUY, "2026-09-22T10:00:00Z", "2026-09-22T10:13:00Z", {"test": True}, "3")]
    assert checks.latency(delayed, None, T("2026-09-22T12:45:00Z"))["status"] == "FAIL"


def test_freshness_alone_passes_when_probes_paused():
    ohlcv = {"bars": {"t": [1792021320, 1792021380]}}       # real, 14 Oct 23:42-23:43 UTC
    lat = checks.latency([], ohlcv, datetime.fromtimestamp(1792021385, timezone.utc))
    assert lat == {"median_lag_s": None, "probe_fires": 0, "freshness_s": 5,
                   "status": "PASS", "note": "B only"}


def test_stale_bars_fail_even_with_good_probes():
    ohlcv = {"bars": [{"t": 1792021380 - 660}]}
    lat = checks.latency(REAL_DEMO_1OCT, ohlcv, datetime.fromtimestamp(1792021385, timezone.utc))
    assert lat["status"] == "FAIL"


def test_no_evidence_is_fail_unknown():
    assert checks.latency([], None, T("2026-10-15T12:45:00Z"))["status"] == "FAIL_UNKNOWN"


def test_live_alert_fires_never_count_as_probes():
    e = ev(LIVE_OLD, "2026-10-14T13:45:00Z", "2026-10-14T14:15:00Z", {"action": "buy", "test": True})
    assert checks.probe_lags([e], T("2026-10-14T16:00:00Z")) == []


def test_noise_area_probe_uses_its_own_30m_resolution():
    e = ev(NOISE, "2026-10-14T19:30:00Z", "2026-10-14T20:00:00Z",
           {"action": "exit", "test": True}, "30")
    assert checks.probe_lags([e], T("2026-10-15T11:00:00Z")) == [0.0]


def test_monday_window_starts_sunday_6pm_et():
    friday = ev(DEMO_BUY, "2026-10-16T19:00:00Z", "2026-10-16T19:03:00Z", {"test": True}, "3")
    sunday = ev(DEMO_BUY, "2026-10-18T23:00:00Z", "2026-10-18T23:03:00Z", {"test": True}, "3")
    lags = checks.probe_lags([friday, sunday], T("2026-10-19T12:45:00Z"))
    assert lags == [0.0]


# --- verdict ------------------------------------------------------------------
GOOD_RISK = {"tripped": []}
FRESH = {"bars": {"t": [int(T("2026-10-19T12:44:00Z").timestamp())]}}


def test_go_before_open_ensures_active(tmp_path):
    out = checks.gonogo([alert(9, LIVE_NEW, False)], [], FRESH, T("2026-10-19T12:45:00Z"),
                        ops_dir=str(tmp_path), risk=GOOD_RISK)
    assert out["verdict"] == "GO" and out["action"] == {"do": "ensure_active", "alert_ids": [9]}


def test_risk_pause_file_is_no_go_and_stops(tmp_path):
    (tmp_path / "RISK_PAUSE").write_text("rule: R5_size\n")
    out = checks.gonogo([alert(9, LIVE_NEW, True)], [], FRESH, T("2026-10-19T12:45:00Z"),
                        ops_dir=str(tmp_path), risk=GOOD_RISK)
    assert out["verdict"] == "NO-GO" and out["action"]["do"] == "ensure_stopped"
    assert out["action"]["alert_ids"] == [9]


def test_hold_is_no_go(tmp_path):
    (tmp_path / "HOLD").write_text("user hold\n")
    out = checks.gonogo([alert(9, LIVE_NEW, False)], [], FRESH, T("2026-10-19T12:45:00Z"),
                        ops_dir=str(tmp_path), risk=GOOD_RISK)
    assert out["fails"] == ["hold"]


def test_never_touch_after_open(tmp_path):
    out = checks.gonogo([alert(9, LIVE_NEW, False)], [], FRESH, T("2026-10-19T13:31:00Z"),
                        ops_dir=str(tmp_path), risk=GOOD_RISK)
    assert out["action"]["do"] == "none"


def test_duplicates_stop_even_after_open(tmp_path):
    out = checks.gonogo([alert(1, LIVE_OLD, True), alert(2, LIVE_NEW, True)], [], FRESH,
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
