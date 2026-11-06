from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    modules = [
        'config',
        'database',
        'main',
        'handlers.games',
        'handlers.payments',
        'miniapp.miniapp_backend',
    ]

    for name in modules:
        try:
            importlib.import_module(name)
            print(f'OK {name}')
        except Exception as exc:  # pragma: no cover
            print(f'FAIL {name}: {exc}')


if __name__ == '__main__':
    main()
