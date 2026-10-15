"""risk_state.evaluate on small hand-built journals."""
import csv

import risk_state as rs

COLS = ["date", "gonogo", "alert_active", "status", "range_high", "range_low",
        "down_break_first", "entry", "entry_time", "exit", "exit_time", "exit_reason",
        "signal_pnl", "buy_lag_s", "exit_lag_s", "qty", "lucid_pnl", "slippage", "flags", "notes"]


def write(d, journal, account=(("2026-10-01", 100000, 97000),), resumes=()):
    with open(d / "journal.csv", "w", newline="") as f:
        w = csv.DictWriter(f, COLS)
        w.writeheader()
        for r in journal:
            w.writerow({c: r.get(c, "") for c in COLS})
    with open(d / "account.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "balance", "min_balance", "source"])
        for a in account:
            w.writerow([*a, "test"])
    with open(d / "resumes.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "rules", "buffer_at_resume", "note"])
        for x in resumes:
            w.writerow(x)


def live(date, pnl, reason="session_close", qty="1", lucid="", slip=""):
    return {"date": date, "status": "live", "signal_pnl": pnl, "exit_reason": reason,
            "qty": qty, "lucid_pnl": lucid, "slippage": slip}


def test_clean_state(tmp_path):
    write(tmp_path, [live("2026-10-05", 100)])
    s = rs.evaluate("2026-10-06", str(tmp_path))
    # +$95 estimated (signal - $5) is a new high, so the trailing floor rises with it
    assert s["tripped"] == [] and s["balance"] == 100095.0 and s["buffer"] == 3000.0
    assert s["buffer_estimated"] is True


def test_shadow_rows_never_count(tmp_path):
    write(tmp_path, [{"date": "2026-10-05", "status": "shadow", "signal_pnl": -625,
                      "exit_reason": "stop", "qty": "2"}] * 3)
    assert rs.evaluate("2026-10-06", str(tmp_path))["tripped"] == []


def test_r1_two_stops_and_resume_looks_forward(tmp_path):
    rows = [live("2026-10-05", -625, "stop"), live("2026-10-06", -625, "stop")]
    write(tmp_path, rows)
    assert "R1_consecutive_stops" in rs.evaluate("2026-10-06", str(tmp_path))["tripped"]
    write(tmp_path, rows, resumes=[("2026-10-07", "R1", 1700, "test")])
    assert "R1_consecutive_stops" not in rs.evaluate("2026-10-07", str(tmp_path))["tripped"]


def test_r2_weekly_loss_only_this_week(tmp_path):
    write(tmp_path, [live("2026-10-09", -950, "time_exit_90min"),
                     live("2026-10-13", -450, "time_exit_90min")],
          account=(("2026-10-01", 104000, 101000),))
    s = rs.evaluate("2026-10-14", str(tmp_path))
    assert s["week_live_pnl"] == -455.0 and "R2_weekly_loss" not in s["tripped"]


def test_r3_buffer_from_snapshot(tmp_path):
    write(tmp_path, [live("2026-10-05", -100, lucid="-100")],
          account=(("2026-10-01", 99000, 97000),))
    s = rs.evaluate("2026-10-06", str(tmp_path))
    assert s["buffer"] == 1900.0 and "R3_buffer" in s["tripped"]


def test_trailing_floor_rises_with_new_high(tmp_path):
    write(tmp_path, [live("2026-10-05", 600, lucid="600")])
    s = rs.evaluate("2026-10-06", str(tmp_path))
    assert s["min_balance"] == 97600.0 and s["buffer"] == 3000.0


def test_floor_locks_at_100100(tmp_path):
    write(tmp_path, [live("2026-10-05", 4000, lucid="4000"), live("2026-10-06", -500, lucid="-500")])
    s = rs.evaluate("2026-10-07", str(tmp_path))
    assert s["floor_locked"] is True and s["min_balance"] == 100100.0 and s["buffer"] == 3400.0


def test_r4_needs_ten_trades(tmp_path):
    rows = [live(f"2026-10-{d:02d}", 10, lucid="4", slip="-6") for d in range(1, 10)]
    write(tmp_path, rows)
    assert "R4_slippage" not in rs.evaluate("2026-10-12", str(tmp_path))["tripped"]
    write(tmp_path, rows + [live("2026-10-12", 10, lucid="4", slip="-6")])
    assert "R4_slippage" in rs.evaluate("2026-10-12", str(tmp_path))["tripped"]


def test_r5_size_and_resume(tmp_path):
    rows = [live("2026-09-30", -8.75, qty="2")]
    write(tmp_path, rows)
    assert rs.evaluate("2026-10-01", str(tmp_path))["tripped"] == ["R5_size"]
    write(tmp_path, rows, resumes=[("2026-10-16", "R5", 2700, "guard alert at qty 1")])
    assert rs.evaluate("2026-10-19", str(tmp_path))["tripped"] == []


def test_real_journal_still_r5():
    s = rs.evaluate("2026-10-14")
    assert "R5_size" in s["tripped"]   # the 30 Sep and 2 Oct qty-2 buys
