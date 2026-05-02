from __future__ import annotations


def normalize_probabilities(probabilities: dict | None) -> dict:
    if not isinstance(probabilities, dict):
        return {"home": 42, "draw": 28, "away": 30}

    raw_values = []
    for key in ("home", "draw", "away"):
        try:
            raw_values.append(max(0.0, float(probabilities.get(key, 0) or 0)))
        except (TypeError, ValueError):
            raw_values.append(0.0)

    total = sum(raw_values)
    if total <= 0:
        return {"home": 42, "draw": 28, "away": 30}

    scaled = [value / total * 100 for value in raw_values]
    ints = [int(value) for value in scaled]
    remainder = 100 - sum(ints)
    order = sorted(range(3), key=lambda index: scaled[index] - ints[index], reverse=True)

    for index in order[:remainder]:
        ints[index] += 1

    return {"home": ints[0], "draw": ints[1], "away": ints[2]}


def derive_calibration_profile(backtest_report: dict | None) -> dict:
    report = backtest_report if isinstance(backtest_report, dict) else {}
    sample_size = int(report.get("evaluated_matches", 0) or 0)
    brier_score = float(report.get("average_brier_score", 0) or 0)
    calibration_score = int(report.get("calibration_score", 0) or 0)

    if sample_size < 30:
        return {
            "sample_size": sample_size,
            "overconfidence_factor": 0.1,
            "draw_adjustment": 2,
            "confidence_penalty": 5,
            "brier_score": brier_score,
            "calibration_score": calibration_score,
        }

    overconfidence_factor = 0.08
    draw_adjustment = 1
    confidence_penalty = 3

    if brier_score >= 0.72:
        overconfidence_factor += 0.08
        confidence_penalty += 5
    elif brier_score >= 0.58:
        overconfidence_factor += 0.04
        confidence_penalty += 3

    if calibration_score and calibration_score < 55:
        overconfidence_factor += 0.05
        draw_adjustment += 2
        confidence_penalty += 5
    elif calibration_score and calibration_score < 70:
        overconfidence_factor += 0.03
        draw_adjustment += 1
        confidence_penalty += 3

    return {
        "sample_size": sample_size,
        "overconfidence_factor": min(0.22, max(0.04, round(overconfidence_factor, 3))),
        "draw_adjustment": min(5, max(0, draw_adjustment)),
        "confidence_penalty": min(14, max(2, confidence_penalty)),
        "brier_score": brier_score,
        "calibration_score": calibration_score,
    }


def calibrate_probabilities(probabilities: dict | None, calibration_profile: dict | None = None) -> dict:
    calibrated = normalize_probabilities(probabilities)
    profile = calibration_profile or derive_calibration_profile(None)
    overconfidence_factor = float(profile.get("overconfidence_factor", 0.1) or 0.1)
    draw_adjustment = int(profile.get("draw_adjustment", 2) or 0)
    max_key = max(calibrated, key=calibrated.get)
    max_probability = calibrated[max_key]

    if max_probability > 60:
        reduction = round((max_probability - 60) * overconfidence_factor)
        if reduction > 0:
            calibrated[max_key] -= reduction
            calibrated["draw"] += max(1, reduction // 2)
            other_key = next(key for key in ("home", "away") if key != max_key) if max_key != "draw" else "home"
            calibrated[other_key] += reduction - max(1, reduction // 2)

    spread = max(calibrated.values()) - sorted(calibrated.values(), reverse=True)[1]
    if spread < 12 and draw_adjustment > 0:
        favorite = max(calibrated, key=calibrated.get)
        if favorite != "draw" and calibrated[favorite] > draw_adjustment:
            calibrated[favorite] -= draw_adjustment
            calibrated["draw"] += draw_adjustment

    return normalize_probabilities(calibrated)
