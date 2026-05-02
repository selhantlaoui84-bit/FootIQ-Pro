from datetime import datetime, timezone

_matches = []
_teams = []
_predictions = []
_last_refresh_at = None
_source = "mock"
_storage = "memory"


def get_matches():
    return _matches


def set_matches(matches):
    global _last_refresh_at, _matches
    _matches = matches
    _last_refresh_at = datetime.now(timezone.utc).isoformat()


def get_teams():
    return _teams


def set_teams(teams):
    global _last_refresh_at, _teams
    _teams = teams
    _last_refresh_at = datetime.now(timezone.utc).isoformat()


def get_predictions():
    return _predictions


def set_predictions(predictions):
    global _last_refresh_at, _predictions
    _predictions = predictions
    _last_refresh_at = datetime.now(timezone.utc).isoformat()


def set_source(source: str):
    global _source
    _source = source


def set_storage(storage: str):
    global _storage
    _storage = storage


def get_refresh_status():
    return {
        "source": _source,
        "storage": _storage,
        "matches_imported": len(_matches),
        "teams_imported": len(_teams),
        "predictions_imported": len(_predictions),
        "last_refresh_at": _last_refresh_at,
    }
