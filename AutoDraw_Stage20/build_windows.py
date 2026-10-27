from __future__ import annotations

import json
import os
import platform
import shutil
import struct
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BUILD_ROOT = ROOT / ".build_unified"
DIST_ROOT = BUILD_ROOT / "pyinstaller_dist"
WORK_ROOT = BUILD_ROOT / "pyinstaller_work"
SPEC_ROOT = BUILD_ROOT / "specs"
RELEASE_ROOT = ROOT / "release"
PORTABLE_NAME = "AutoDrawPortable"
FINAL_ROOT = RELEASE_ROOT / PORTABLE_NAME
STAGING_ROOT = RELEASE_ROOT / f".{PORTABLE_NAME}_staging"
BACKUP_ROOT = RELEASE_ROOT / f".{PORTABLE_NAME}_previous_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
FEATURE_MANIFEST_PATH = ROOT / "app_features.json"


class BuildError(RuntimeError):
    pass


def run_checked(command: list[str], *, cwd: Path) -> None:
    print("\n> " + subprocess.list2cmdline(command), flush=True)
    completed = subprocess.run(command, cwd=cwd, check=False)
    if completed.returncode != 0:
        raise BuildError(f"Команда завершилась с кодом {completed.returncode}: {command!r}")


def run_pyinstaller(
    *, name: str, script_dir: Path, script_name: str,
    dist_parent: Path, work_path: Path, spec_path: Path,
    extra_args: list[str] | None = None,
) -> Path:
    script_path = script_dir / script_name
    if not script_path.is_file():
        raise BuildError(f"Не найден скрипт приложения: {script_path}")
    for directory in (dist_parent, work_path, spec_path):
        directory.mkdir(parents=True, exist_ok=True)

    command = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean", "--onedir", "--windowed",
        "--name", name,
        "--distpath", str(dist_parent),
        "--workpath", str(work_path),
        "--specpath", str(spec_path),
    ]
    if extra_args:
        command.extend(extra_args)
    command.append(script_name)
    run_checked(command, cwd=script_dir)

    app_dir = dist_parent / name
    executable = app_dir / f"{name}.exe"
    if not executable.is_file():
        raise BuildError(f"PyInstaller не создал ожидаемый EXE: {executable}")
    return app_dir


def copy_directory_contents(source: Path, destination: Path) -> None:
    if not source.is_dir():
        raise BuildError(f"Не найдена папка сборки PyInstaller: {source}")
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination, dirs_exist_ok=True)


def copy_source_user_data(source_root: Path, staging: Path) -> None:
    """Seed the first packaged build from the source tree's optional data folder."""
    source_data = source_root / "data"
    new_data = staging / "data"
    if source_data.is_dir():
        print(f"Добавляю начальные данные из исходной папки: {source_data}", flush=True)
        # This checked-in calibration belongs to one 1920x1080 desktop and
        # has absolute screen coordinates. It is useful as a benchmark fixture,
        # but must not be installed as a default profile on another PC.
        screen_specific_profile = (
            source_data / "palettes" / "profiles" / "Browser_palette.autodraw-palette.json"
        )
        excluded_profile_directory = screen_specific_profile.parent.resolve()

        def ignore_screen_specific_profile(directory: str, names: list[str]) -> set[str]:
            if (
                Path(directory).resolve() == excluded_profile_directory
                and screen_specific_profile.name in names
            ):
                print(
                    "Не включаю экранный benchmark-профиль палитры в новую portable-сборку.",
                    flush=True,
                )
                return {screen_specific_profile.name}
            return set()

        shutil.copytree(
            source_data,
            new_data,
            dirs_exist_ok=True,
            ignore=ignore_screen_specific_profile,
        )


def copy_existing_user_data(old_release: Path, staging: Path) -> None:
    """Preserve user data from an existing portable distribution on rebuild."""
    old_data = old_release / "data"
    new_data = staging / "data"
    if old_data.is_dir():
        print(f"Сохраняю данные предыдущей сборки: {old_data}", flush=True)
        # Copy after source seed so the existing portable data wins on conflicts.
        shutil.copytree(old_data, new_data, dirs_exist_ok=True)


def create_data_layout(portable_root: Path) -> None:
    for name in ("profiles", "palettes", "projects", "results", "logs", "runtime"):
        (portable_root / "data" / name).mkdir(parents=True, exist_ok=True)
    (portable_root / "data" / "palettes" / "profiles").mkdir(parents=True, exist_ok=True)
    (portable_root / "data" / "results" / "palette_conversions").mkdir(parents=True, exist_ok=True)
    (portable_root / "data" / "results" / "color_scanline_plans").mkdir(parents=True, exist_ok=True)
    (portable_root / "data" / "results" / "paint_limit_tests").mkdir(parents=True, exist_ok=True)


def replace_release(staging: Path, final: Path, backup: Path) -> None:
    """Swap the built folder into place; retain the old build if the swap fails."""
    moved_old = False
    try:
        if final.exists():
            final.rename(backup)
            moved_old = True
        staging.rename(final)
    except OSError as exc:
        if moved_old and backup.exists() and not final.exists():
            try:
                backup.rename(final)
            except OSError:
                pass
        raise BuildError(
            "Не удалось обновить папку portable-сборки. Закройте AutoDraw, "
            f"проверьте доступ к папке release. Исходная ошибка: {exc}"
        ) from exc
    if backup.exists():
        try:
            shutil.rmtree(backup)
        except OSError as exc:
            print(f"Предупреждение: старая сборка осталась в {backup}: {exc}", flush=True)


def load_feature_manifest(path: Path = FEATURE_MANIFEST_PATH) -> list[str]:
    """Load the single declared feature list embedded in generated build_info.json."""
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BuildError(f"Не удалось прочитать manifest функций {path}: {exc}") from exc

    if not isinstance(document, dict) or document.get("schema_version") != 1:
        raise BuildError("Manifest функций должен иметь schema_version=1.")
    features = document.get("features")
    if (
        not isinstance(features, list)
        or not features
        or any(not isinstance(item, str) or not item.strip() for item in features)
    ):
        raise BuildError("Поле features в manifest должно быть непустым списком строк.")
    if len(features) != len(set(features)):
        raise BuildError("Manifest функций содержит повторяющиеся идентификаторы.")
    return list(features)


def main() -> int:
    if os.name != "nt":
        print(
            "Ошибка: Windows EXE необходимо собирать на Windows. "
            "PyInstaller не является кросс-компилятором из Linux/macOS.",
            file=sys.stderr,
        )
        return 2
    if sys.version_info < (3, 11) or sys.version_info >= (3, 14):
        print("Ошибка: используйте Python 3.11, 3.12 или 3.13 x64 для сборки.", file=sys.stderr)
        return 2
    if struct.calcsize("P") != 8:
        print("Ошибка: используйте 64-битный Python для сборки.", file=sys.stderr)
        return 2
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("Не установлен PyInstaller. Выполните build_windows.bat.", file=sys.stderr)
        return 2

    try:
        if STAGING_ROOT.exists():
            shutil.rmtree(STAGING_ROOT)
        if BUILD_ROOT.exists():
            for path in (DIST_ROOT, WORK_ROOT, SPEC_ROOT):
                if path.exists():
                    shutil.rmtree(path)

        prep_src = ROOT / "source" / "preparation"
        exec_src = ROOT / "source" / "executor"
        collect_args = [
            "--paths", str(prep_src),
            "--paths", str(exec_src),
            "--collect-all", "PIL",
            "--collect-all", "numpy",
            "--collect-all", "cv2",
            "--collect-all", "pyautogui",
            "--collect-all", "pynput",
            "--hidden-import", "pynput.keyboard._win32",
            "--hidden-import", "pynput.mouse._win32",
        ]
        app_dist = run_pyinstaller(
            name="AutoDraw",
            script_dir=ROOT,
            script_name="integrated_app.py",
            dist_parent=DIST_ROOT,
            work_path=WORK_ROOT / "autodraw",
            spec_path=SPEC_ROOT / "autodraw",
            extra_args=collect_args,
        )

        STAGING_ROOT.mkdir(parents=True, exist_ok=True)
        # A single PyInstaller onedir app: one EXE plus its private _internal folder.
        copy_directory_contents(app_dist, STAGING_ROOT)
        shutil.copy2(ROOT / "README.txt", STAGING_ROOT / "README.txt")
        copy_source_user_data(ROOT, STAGING_ROOT)
        copy_existing_user_data(FINAL_ROOT, STAGING_ROOT)
        create_data_layout(STAGING_ROOT)

        metadata = {
            "product": "AutoDraw",
            "version": "1.8.3",
            "format": "portable-onedir-unified",
            "built_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "python_version": sys.version.split()[0],
            "architecture": platform.machine(),
            "pyinstaller_version": __import__("PyInstaller").__version__,
            "data_directory": "data",
            "interface": "single-window-tabs",
            "executable": "AutoDraw.exe",
            "features": load_feature_manifest(),
        }
        (STAGING_ROOT / "build_info.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

        RELEASE_ROOT.mkdir(parents=True, exist_ok=True)
        replace_release(STAGING_ROOT, FINAL_ROOT, BACKUP_ROOT)
        print("\nЕдиная сборка AutoDraw создана успешно:")
        print(f"  Запуск: {FINAL_ROOT / 'AutoDraw.exe'}")
        print(f"  Данные: {FINAL_ROOT / 'data'}")
        print("Весь процесс подготовки и исполнения находится в одном окне.")
        print("Переносите всю папку AutoDrawPortable, а не отдельный EXE.")
        return 0
    except (BuildError, OSError, subprocess.SubprocessError) as exc:
        print(f"\nСборка не завершена: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
