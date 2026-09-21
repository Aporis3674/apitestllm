import tomllib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HEADER = (
    "# Generated from [project] dependencies in pyproject.toml.\n"
    "# Regenerate with: ./scripts/export-requirements.sh\n"
)


def main() -> None:
    pyproject = PROJECT_ROOT / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    deps = data["project"]["dependencies"]

    out = PROJECT_ROOT / "requirements.txt"
    out.write_text(HEADER + "\n".join(deps) + "\n", encoding="utf-8")

    print("requirements.txt regenerated from pyproject.toml:")
    print("\n".join(deps))


if __name__ == "__main__":
    main()
