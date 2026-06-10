"""项目启动依赖自检与自动安装工具。"""

from __future__ import annotations

import importlib.metadata
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.9/3.10
    tomllib = None  # type: ignore[assignment]

# 使用环境变量避免同一进程重复执行依赖检查。
_BOOTSTRAP_DONE_ENV = "JZ_DEPENDENCY_BOOTSTRAP_DONE"
# 提供手动关闭开关，便于离线排障或定制启动流程。
_BOOTSTRAP_ENABLED_ENV = "JZ_AUTO_INSTALL_DEPS"
# 简单提取 PEP 508/requirements 包名，兼容常见版本约束写法。
_REQUIREMENT_NAME_PATTERN = re.compile(r"^\s*([A-Za-z0-9_.\-]+)")


def _normalize_distribution_name(name: str) -> str:
    """统一包名格式，减少大小写和分隔符差异带来的误判。"""
    return str(name or "").strip().lower().replace("_", "-")


def _project_root_from_current_file() -> Path:
    """基于当前文件位置推导项目根目录。"""
    return Path(__file__).resolve().parents[2]


def _extract_requirement_name(requirement_line: str) -> str:
    """从一条依赖声明中提取发行包名。"""
    line = str(requirement_line or "").strip()

    # 跳过空行、注释和 include/editable 等扩展语法。
    if not line or line.startswith("#") or line.startswith("-"):
        return ""

    # 去掉环境标记，例如 "package; python_version >= '3.9'"。
    line = line.split(";", 1)[0].strip()
    if not line:
        return ""

    match = _REQUIREMENT_NAME_PATTERN.match(line)
    if not match:
        return ""

    return _normalize_distribution_name(match.group(1))


def _read_requirement_names_from_lines(requirement_lines: List[str]) -> List[str]:
    """从多条依赖声明中提取去重后的包名列表。"""
    requirement_names: List[str] = []
    seen_names = set()

    for raw_line in requirement_lines:
        normalized_name = _extract_requirement_name(raw_line)
        if normalized_name and normalized_name not in seen_names:
            seen_names.add(normalized_name)
            requirement_names.append(normalized_name)

    return requirement_names


def _read_requirement_names(requirements_path: Path) -> List[str]:
    """从 requirements.txt 中提取包名列表。"""
    return _read_requirement_names_from_lines(
        requirements_path.read_text(encoding="utf-8").splitlines()
    )


def _read_project_dependencies_without_tomllib(pyproject_path: Path) -> List[str]:
    """在 Python 3.9/3.10 无 tomllib 时，提取 [project].dependencies。"""
    dependency_lines: List[str] = []
    in_project_section = False
    in_dependencies_array = False

    for raw_line in pyproject_path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue

        if stripped.startswith("[") and stripped.endswith("]"):
            in_project_section = stripped == "[project]"
            in_dependencies_array = False
            continue

        if not in_project_section:
            continue

        if not in_dependencies_array:
            if not stripped.startswith("dependencies") or "=" not in stripped:
                continue
            in_dependencies_array = True

        dependency_lines.extend(re.findall(r'"([^"]+)"', stripped))
        dependency_lines.extend(re.findall(r"'([^']+)'", stripped))

        if "]" in stripped:
            in_dependencies_array = False

    return _read_requirement_names_from_lines(dependency_lines)


def _read_pyproject_dependency_names(pyproject_path: Path) -> List[str]:
    """从 pyproject.toml 的 [project].dependencies 中提取运行依赖包名。"""
    if tomllib is None:
        return _read_project_dependencies_without_tomllib(pyproject_path)

    with pyproject_path.open("rb") as f:
        pyproject_data = tomllib.load(f)

    project_data = pyproject_data.get("project", {})
    dependencies = project_data.get("dependencies", [])
    if not isinstance(dependencies, list):
        return []

    return _read_requirement_names_from_lines([str(item) for item in dependencies])


def _find_missing_requirements(requirement_names: List[str]) -> List[str]:
    """找出当前解释器环境中缺失的依赖包。"""
    missing_names: List[str] = []

    for requirement_name in requirement_names:
        try:
            importlib.metadata.distribution(requirement_name)
        except importlib.metadata.PackageNotFoundError:
            missing_names.append(requirement_name)

    return missing_names


def _ensure_pip_available(python_executable: str, project_root: Path) -> None:
    """确保当前解释器具备 pip，缺失时尝试自动补齐。"""
    pip_check = subprocess.run(
        [python_executable, "-m", "pip", "--version"],
        cwd=str(project_root),
        capture_output=True,
        text=True,
        check=False,
    )
    if pip_check.returncode == 0:
        return

    print("[bootstrap] pip 不可用，正在尝试通过 ensurepip 自动安装...")
    ensurepip_result = subprocess.run(
        [python_executable, "-m", "ensurepip", "--upgrade"],
        cwd=str(project_root),
        check=False,
    )
    if ensurepip_result.returncode != 0:
        raise RuntimeError("当前 Python 环境缺少 pip，且 ensurepip 自动修复失败。")


def _is_current_project_venv(python_executable: str, project_root: Path) -> bool:
    """判断当前解释器是否来自项目默认 .venv。"""
    try:
        python_path = Path(python_executable).resolve()
        project_venv = (project_root / ".venv").resolve()
        return python_path.is_relative_to(project_venv)
    except Exception:
        return False


def _install_with_uv_sync(python_executable: str, project_root: Path) -> bool:
    """在当前解释器属于项目 .venv 时，用 uv sync 同步依赖。"""
    uv_executable = shutil.which("uv")
    if not uv_executable:
        return False

    if not _is_current_project_venv(python_executable, project_root):
        return False

    print("[bootstrap] 正在使用 uv sync 同步 pyproject.toml / uv.lock ...")
    sync_result = subprocess.run(
        [uv_executable, "sync"],
        cwd=str(project_root),
        check=False,
    )
    if sync_result.returncode != 0:
        raise RuntimeError(
            "uv 依赖同步失败，请手动执行 `uv sync` 后重试。"
        )
    return True


def ensure_project_dependencies(project_root: str | Path | None = None) -> None:
    """在项目启动前强制检查依赖，缺失时自动安装。"""
    if os.environ.get(_BOOTSTRAP_DONE_ENV) == "1":
        return

    # 冻结打包环境的依赖通常已随程序分发，不在运行时执行 pip。
    if getattr(sys, "frozen", False):
        os.environ[_BOOTSTRAP_DONE_ENV] = "1"
        return

    if str(os.environ.get(_BOOTSTRAP_ENABLED_ENV, "1")).strip().lower() in {"0", "false", "off"}:
        os.environ[_BOOTSTRAP_DONE_ENV] = "1"
        return

    resolved_project_root = Path(project_root) if project_root else _project_root_from_current_file()
    pyproject_path = resolved_project_root / "pyproject.toml"
    requirements_path = resolved_project_root / "requirements.txt"

    dependency_source = ""
    requirement_names: List[str] = []
    if pyproject_path.exists():
        dependency_source = "pyproject.toml"
        requirement_names = _read_pyproject_dependency_names(pyproject_path)

    if not requirement_names and requirements_path.exists():
        dependency_source = "requirements.txt"
        requirement_names = _read_requirement_names(requirements_path)

    if not requirement_names:
        os.environ[_BOOTSTRAP_DONE_ENV] = "1"
        return

    missing_names = _find_missing_requirements(requirement_names)
    if not missing_names:
        os.environ[_BOOTSTRAP_DONE_ENV] = "1"
        return

    python_executable = sys.executable or "python"
    print(f"[bootstrap] 检测到缺失依赖: {', '.join(missing_names)}")

    if dependency_source == "pyproject.toml" and _install_with_uv_sync(
        python_executable, resolved_project_root
    ):
        remaining_missing_names = _find_missing_requirements(requirement_names)
        if remaining_missing_names:
            raise RuntimeError(
                "uv sync 后当前解释器仍缺失依赖: {}。请确认使用 `uv run python server.py` "
                "或项目 .venv 中的 Python 启动。".format(", ".join(remaining_missing_names))
            )

        print("[bootstrap] 依赖检查完成，pyproject 运行依赖均已就绪。")
        os.environ[_BOOTSTRAP_DONE_ENV] = "1"
        return

    if not requirements_path.exists():
        raise RuntimeError(
            "当前解释器缺失依赖，且无法在当前进程内自动同步 uv 环境。"
            "请执行 `uv sync` 后使用 `uv run python server.py` 启动。"
        )

    print(f"[bootstrap] 正在使用 {python_executable} 自动安装 requirements.txt ...")

    _ensure_pip_available(python_executable, resolved_project_root)

    install_result = subprocess.run(
        [python_executable, "-m", "pip", "install", "-r", str(requirements_path)],
        cwd=str(resolved_project_root),
        check=False,
    )
    if install_result.returncode != 0:
        raise RuntimeError(
            "依赖自动安装失败，请手动执行 `python -m pip install -r requirements.txt` 后重试。"
        )

    remaining_missing_names = _find_missing_requirements(requirement_names)
    if remaining_missing_names:
        raise RuntimeError(
            "依赖安装后仍存在缺失包: {}".format(", ".join(remaining_missing_names))
        )

    print("[bootstrap] 依赖检查完成，所有 requirements 依赖均已就绪。")
    os.environ[_BOOTSTRAP_DONE_ENV] = "1"
