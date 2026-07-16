from __future__ import annotations

import sys

from lambdas.outbox_publisher import handler as _implementation

sys.modules[__name__] = _implementation
