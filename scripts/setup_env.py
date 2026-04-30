from __future__ import annotations

import importlib
import os
import shutil
import subprocess
import sys
import venv
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
VENV_DIR = REPO_ROOT / ".venv"
REQUIREMENTS = REPO_ROOT / "requirements.txt"
PACKAGES = ("fastapi", "uvicorn", "gunicorn", "pydantic", "sqlalchemy", "psycopg2", "redis")
TMP_DIR = REPO_ROOT / ".tmp"
LOCAL_SITE = REPO_ROOT / ".python-packages"


TMP_DIR.mkdir(exist_ok=True)
os.environ["TMPDIR"] = str(TMP_DIR)
os.environ["TMP"] = str(TMP_DIR)
os.environ["TEMP"] = str(TMP_DIR)


def venv_python() -> Path:
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def selected_python() -> tuple[str, dict[str, str]]:
    env = os.environ.copy()

    if os.environ.get("VIRTUAL_ENV"):
        return sys.executable, env

    python_path = venv_python()
    if python_path.exists() and pip_available(str(python_path)):
        return str(python_path), env

    if VENV_DIR.exists():
        try:
            VENV_DIR.resolve().relative_to(REPO_ROOT.resolve())
        except ValueError as exc:
            raise RuntimeError(f"Refusing to remove venv outside repository: {VENV_DIR}")
        shutil.rmtree(VENV_DIR)

    try:
        venv.EnvBuilder(with_pip=True).create(VENV_DIR)
    except Exception as exc:
        print(f"Unable to create .venv with pip ({exc}). Falling back to repo-local package install.")
        if VENV_DIR.exists():
            shutil.rmtree(VENV_DIR, ignore_errors=True)
        LOCAL_SITE.mkdir(exist_ok=True)
        env["PYTHONPATH"] = prepend_pythonpath(str(LOCAL_SITE), env.get("PYTHONPATH"))
        return sys.executable, env

    return str(python_path), env


def prepend_pythonpath(path: str, current: str | None) -> str:
    if current:
        return path + os.pathsep + current
    return path


def pip_available(python: str) -> bool:
    return subprocess.call([python, "-m", "pip", "--version"], cwd=REPO_ROOT) == 0


def run(command: list[str], env: dict[str, str]) -> None:
    subprocess.check_call(command, cwd=REPO_ROOT, env=env)


def main() -> None:
    python, env = selected_python()

    if env.get("PYTHONPATH", "").split(os.pathsep)[0] == str(LOCAL_SITE):
        run([python, "-m", "pip", "install", "--upgrade", "pip", "--target", str(LOCAL_SITE)], env)
        run([python, "-m", "pip", "install", "--target", str(LOCAL_SITE), "-r", str(REQUIREMENTS)], env)
    else:
        run([python, "-m", "pip", "install", "--upgrade", "pip"], env)
        run([python, "-m", "pip", "install", "-r", str(REQUIREMENTS)], env)

    for package in PACKAGES:
        subprocess.check_call(
            [python, "-c", f"import importlib; importlib.import_module({package!r})"],
            cwd=REPO_ROOT,
            env=env,
        )

    print("Python dependencies installed and verified.")


if __name__ == "__main__":
    main()
