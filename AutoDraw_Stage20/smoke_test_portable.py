from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PORTABLE_ROOT = ROOT / "release" / "AutoDrawPortable"
EXECUTABLE = PORTABLE_ROOT / "AutoDraw.exe"
STARTUP_GRACE_SECONDS = 10
SHUTDOWN_TIMEOUT_SECONDS = 3


def validate_portable_layout() -> None:
    if not EXECUTABLE.is_file():
        raise RuntimeError(f"Не найден EXE portable-сборки: {EXECUTABLE}")
    if not (PORTABLE_ROOT / "README.txt").is_file():
        raise RuntimeError("В portable-сборке отсутствует README.txt.")
    if not (PORTABLE_ROOT / "build_info.json").is_file():
        raise RuntimeError("В portable-сборке отсутствует build_info.json.")
    required_data_directories = (
        "profiles",
        "palettes",
        "projects",
        "results",
        "logs",
        "runtime",
    )
    for relative_path in required_data_directories:
        if not (PORTABLE_ROOT / "data" / relative_path).is_dir():
            raise RuntimeError(f"Отсутствует каталог пользовательских данных: data/{relative_path}")


def smoke_test_executable() -> None:
    validate_portable_layout()
    print(f"Проверяю запуск: {EXECUTABLE}", flush=True)
    process = subprocess.Popen(
        [str(EXECUTABLE)],
        cwd=PORTABLE_ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        exit_code = process.wait(timeout=STARTUP_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        # A windowed app should remain alive until closed. This catches many
        # immediate import/DLL/startup failures without GUI automation.
        print(
            f"Процесс приложения оставался активным {STARTUP_GRACE_SECONDS} секунд.",
            flush=True,
        )
    else:
        raise RuntimeError(
            "AutoDraw.exe завершился сразу после запуска "
            f"(код выхода {exit_code}); возможен сбой инициализации."
        )
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=SHUTDOWN_TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=SHUTDOWN_TIMEOUT_SECONDS)
    print("Portable layout и smoke-test запуска пройдены.", flush=True)


def main() -> int:
    if sys.platform != "win32":
        print("Smoke-test portable EXE выполняется только на Windows.", file=sys.stderr)
        return 2
    try:
        smoke_test_executable()
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"Smoke-test не пройден: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
