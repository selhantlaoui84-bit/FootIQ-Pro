CURRENT_MODEL_VERSION = "elo-poisson-calibrated-v1"
PREVIOUS_MODEL_VERSION = "elo-poisson-v1"


def get_current_model_version() -> str:
    return CURRENT_MODEL_VERSION


def get_previous_model_version() -> str:
    return PREVIOUS_MODEL_VERSION


def get_model_metadata() -> dict:
    return {
        "current_model_version": CURRENT_MODEL_VERSION,
        "previous_model_version": PREVIOUS_MODEL_VERSION,
        "family": "elo_poisson",
        "calibration": True,
        "description": "Calibrated Elo + Poisson model with conservative probability smoothing.",
    }
