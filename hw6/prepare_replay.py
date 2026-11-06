"""Create an isolated prompt-replay folder without copying application code."""

import argparse
from pathlib import Path
import shutil
import tempfile


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path-only", action="store_true")
    args = parser.parse_args()
    source = Path(__file__).resolve().parent
    target = Path(tempfile.mkdtemp(prefix="hw6-secure-notes-replay-"))
    project = target / "hw6"
    project.mkdir()
    for name in ("prompts.txt", "pyproject.toml", "uv.lock", ".gitignore"):
        shutil.copy2(source / name, project / name)
    (target / "REPLAY_INSTRUCTIONS.txt").write_text(
        "Open this folder as a fresh coding-agent workspace.\n"
        "Paste Prompt 1, then Prompt 2 from hw6/prompts.txt.\n"
        "No application source, templates, CSS, tests, database or key was copied.\n"
        "Run the newly generated code; do not substitute the original.\n",
        encoding="utf-8",
    )
    print(target)
    if not args.path_only:
        print("Fresh workspace created. Open it and use hw6/prompts.txt.")
        print("This prepares inputs; it does not run an AI agent or claim regeneration.")


if __name__ == "__main__":
    main()
