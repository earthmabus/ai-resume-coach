from __future__ import annotations

import sys

from lambdas.api import handler as _implementation

sys.modules[__name__] = _implementation
