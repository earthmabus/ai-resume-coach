from __future__ import annotations

import sys

from lambdas.worker import handler as _implementation

sys.modules[__name__] = _implementation
