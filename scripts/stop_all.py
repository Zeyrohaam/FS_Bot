from __future__ import annotations
import json
import os
import signal
import subprocess
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PID_FILE = BASE_DIR / 'var' / 'runtime' / 'pids.json'
URL_FILE = BASE_DIR / 'var' / 'cloudflare_quick_url.txt'


def load_pids() -> dict:
    if not PID_FILE.exists():
        return {}
    try:
        data = json.loads(PID_FILE.read_text(encoding='utf-8'))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def is_process_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == 'nt':
        check = subprocess.run(
            ['tasklist', '/FI', f'PID eq {pid}'],
            capture_output=True,
            text=True,
        )
        return str(pid) in (check.stdout or '')
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def stop_pid(pid: int) -> bool:
    if pid <= 0:
        return False

    if os.name == 'nt':
        result = subprocess.run(
            ['taskkill', '/PID', str(pid), '/T', '/F'],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0 or not is_process_alive(pid)

    # На Unix сначала мягко останавливаем SIGTERM, потом дожимаем SIGKILL.
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return True
    except PermissionError:
        return False

    for _ in range(20):
        if not is_process_alive(pid):
            return True
        time.sleep(0.1)

    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        return True
    except PermissionError:
        return False

    for _ in range(20):
        if not is_process_alive(pid):
            return True
        time.sleep(0.1)

    return not is_process_alive(pid)


def main() -> None:
    data = load_pids()
    if not data:
        print('PID-файл пустой или отсутствует.')

    for name, pid in data.items():
        try:
            pid_int = int(pid)
        except Exception:
            print(f'Некорректный PID у {name}: {pid}')
            continue

        if stop_pid(pid_int):
            print(f'Остановлен {name}: {pid_int}')
        else:
            print(f'Не удалось остановить {name}: {pid_int}')

    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    URL_FILE.parent.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text('{}', encoding='utf-8')
    URL_FILE.write_text('', encoding='utf-8')
    print('Готово.')


if __name__ == '__main__':
    main()
