from __future__ import annotations

from pathlib import Path

import tools
import tools.build


ROOT = Path(__file__).resolve().parents[2]


def test_repository_tooling_package_wins_import_resolution():
    """Prevent an installed ``tools`` package from shadowing this repository."""
    assert Path(tools.__file__).resolve() == (ROOT / "tools" / "__init__.py")
    assert Path(tools.build.__file__).resolve() == (
        ROOT / "tools" / "build" / "__init__.py"
    )
