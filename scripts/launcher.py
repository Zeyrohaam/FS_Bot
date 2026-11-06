from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import socket
import ssl
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
VAR_DIR = BASE_DIR / 'var'
LOGS_DIR = VAR_DIR / 'logs'
RUNTIME_DIR = VAR_DIR / 'runtime'
BIN_DIR = VAR_DIR / 'bin'
PID_FILE = RUNTIME_DIR / 'pids.json'
URL_FILE = VAR_DIR / 'cloudflare_quick_url.txt'
VENV_DIR = BASE_DIR / '.venv'
REQ_FILE = BASE_DIR / 'requirements.txt'
REQ_STAMP = RUNTIME_DIR / 'requirements.sha256'
CONFIG_FILE = BASE_DIR / 'config.py'

for path in (LOGS_DIR, RUNTIME_DIR, BIN_DIR):
    path.mkdir(exist_ok=True)


def info(msg: str) -> None:
    print(f'[START] {msg}', flush=True)


def warn(msg: str) -> None:
    print(f'[WARN] {msg}', flush=True)


def fail(msg: str, code: int = 1) -> None:
    print(f'[ERROR] {msg}', flush=True)
    sys.exit(code)


def read_config_values() -> dict:
    values = {}
    if not CONFIG_FILE.exists():
        return values
    text = CONFIG_FILE.read_text(encoding='utf-8', errors='ignore')
    for key in ('BOT_TOKEN', 'CLOUDFLARE_MODE', 'BACKEND_PORT', 'BACKEND_HOST'):
        m = re.search(rf'^{key}\s*=\s*(.+)$', text, flags=re.M)
        if m:
            values[key] = m.group(1).strip()
    return values


def ensure_token_present(py_exe: Path) -> None:
    try:
        result = subprocess.run(
            [
                str(py_exe),
                '-c',
                (
                    'import json; '
                    'from config import TOKEN, APP_MODE; '
                    'print(json.dumps({"has_token": bool(TOKEN), "mode": APP_MODE}))'
                ),
            ],
            capture_output=True,
            text=True,
            cwd=str(BASE_DIR),
            check=True,
        )
        payload = json.loads((result.stdout or '{}').strip() or '{}')
    except Exception:
        fail('Не удалось прочитать TOKEN из config.py. Проверь синтаксис config.py.')
        return

    if not payload.get('has_token'):
        mode = payload.get('mode') or 'test'
        if mode == 'test':
            fail('APP_MODE=test, но токен тестового режима пустой. Заполни TEST_ARCHITECTURE["bot_token"] или .env.')
        fail('APP_MODE=prod, но токен продового режима пустой. Заполни PROD_ARCHITECTURE["bot_token"] или .env.')


def sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def run(cmd, check=True, env=None):
    info(' '.join(map(str, cmd)))
    return subprocess.run(cmd, check=check, cwd=str(BASE_DIR), env=env)


def read_runtime_token(py_exe: Path) -> str:
    try:
        result = subprocess.run(
            [str(py_exe), '-c', 'from config import TOKEN; print(TOKEN or "")'],
            capture_output=True,
            text=True,
            cwd=str(BASE_DIR),
            check=True,
        )
        return result.stdout.strip()
    except Exception:
        return ''


def read_config_bot_username(py_exe: Path) -> str:
    try:
        result = subprocess.run(
            [str(py_exe), '-c', 'from config import BOT_USERNAME; print(BOT_USERNAME or "")'],
            capture_output=True,
            text=True,
            cwd=str(BASE_DIR),
            check=True,
        )
        username = result.stdout.strip()
        if username and not username.startswith('@'):
            username = f'@{username}'
        return username
    except Exception:
        return ''


def fetch_bot_identity(token: str) -> tuple[str, str, int] | None:
    if not token:
        return None

    def parse_identity(payload: dict) -> tuple[str, str, int] | None:
        if not payload.get('ok'):
            return None
        result = payload.get('result') or {}
        name = str(result.get('first_name') or '').strip() or '(без имени)'
        username_raw = str(result.get('username') or '').strip()
        username = f'@{username_raw}' if username_raw else '(без username)'
        bot_id = int(result.get('id') or 0)
        return name, username, bot_id

    last_error = None
    for _ in range(3):
        url = f'https://api.telegram.org/bot{token}/getMe'
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                data = json.loads(resp.read().decode('utf-8', errors='ignore'))
            identity = parse_identity(data)
            if not identity:
                last_error = f"Telegram API ответил ok={data.get('ok')}"
                time.sleep(0.6)
                continue
            return identity
        except Exception as exc:
            last_error = str(exc)
            ssl_failed = isinstance(exc, ssl.SSLCertVerificationError) or 'CERTIFICATE_VERIFY_FAILED' in last_error
            if not ssl_failed:
                time.sleep(0.6)
                continue
            try:
                # Fallback only for startup identity log in environments with custom/self-signed TLS interception.
                insecure_ctx = ssl._create_unverified_context()
                with urllib.request.urlopen(url, timeout=10, context=insecure_ctx) as resp:
                    data = json.loads(resp.read().decode('utf-8', errors='ignore'))
                identity = parse_identity(data)
                if identity:
                    warn('Identity получен с TLS fallback без проверки сертификата (только для стартового лога).')
                    return identity
            except Exception as fallback_exc:
                last_error = f'{exc}; fallback failed: {fallback_exc}'
            time.sleep(0.6)
    if last_error:
        if '401' in last_error or 'Unauthorized' in last_error:
            fail('Токен бота недействителен (Telegram 401: Unauthorized). Получи новый токен в @BotFather и укажи его в .env (TEST_TOKEN или BOT_TOKEN).')
        warn(f'Не удалось получить identity через getMe: {last_error}')
    return None


def is_valid_venv(py_exe: Path) -> bool:
    if not py_exe.exists():
        return False
    try:
        result = subprocess.run(
            [str(py_exe), '-c', 'import sys; print(sys.prefix)'],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.returncode == 0
    except Exception:
        return False


def pick_python_launcher() -> list[str]:
    # На Windows пробуем py с версией, на Unix (Mac/Linux) пробуем python3 сначала
    if os.name == 'nt':
        candidates = [
            ['py', '-3.12'],
            ['py', '-3.11'],
            ['py', '-3.10'],
            ['python'],
        ]
    else:
        # На Mac/Linux: python3 в приоритете
        candidates = [
            ['python3.12'],
            ['python3.11'],
            ['python3.10'],
            ['python3'],
            ['python'],
        ]
    
    for cmd in candidates:
        try:
            result = subprocess.run(cmd + ['-V'], capture_output=True, text=True)
            if result.returncode == 0:
                return cmd
        except FileNotFoundError:
            continue
    fail('Python не найден. Установи Python 3.10 или выше и добавь его в PATH.')


def ensure_venv() -> Path:
    py_launcher = pick_python_launcher()
    py_exe = (VENV_DIR / 'Scripts' / 'python.exe') if os.name == 'nt' else (VENV_DIR / 'bin' / 'python')
    if py_exe.exists() and is_valid_venv(py_exe):
        return py_exe
    if VENV_DIR.exists():
        info('Найдено повреждённое .venv, удаляю и создаю заново')
        shutil.rmtree(VENV_DIR, ignore_errors=True)
    info('Создаю виртуальное окружение .venv')
    run(py_launcher + ['-m', 'venv', str(VENV_DIR)])
    if not py_exe.exists() or not is_valid_venv(py_exe):
        fail('Не удалось создать .venv')
    return py_exe


def parse_requirements() -> list[str]:
    packages: list[str] = []
    if not REQ_FILE.exists():
        return packages
    for line in REQ_FILE.read_text(encoding='utf-8', errors='ignore').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        match = re.match(r'^([A-Za-z0-9_.+-]+)', line)
        if match:
            packages.append(match.group(1))
    return packages


def is_package_installed(py_exe: Path, package_name: str) -> bool:
    result = subprocess.run([str(py_exe), '-m', 'pip', 'show', package_name], capture_output=True)
    return result.returncode == 0


def ensure_requirements(py_exe: Path) -> None:
    current_hash = sha256_of_file(REQ_FILE)
    old_hash = REQ_STAMP.read_text(encoding='utf-8').strip() if REQ_STAMP.exists() else ''
    needs_install = old_hash != current_hash
    if not needs_install:
        for package in parse_requirements():
            if not is_package_installed(py_exe, package):
                warn(f'Пакет {package} не найден в окружении, переустанавливаю зависимости')
                needs_install = True
                break
    if not needs_install:
        info('Зависимости уже установлены')
        return
    info('Обновляю pip')
    run([str(py_exe), '-m', 'pip', 'install', '--upgrade', 'pip'])
    info('Устанавливаю зависимости')
    run([str(py_exe), '-m', 'pip', 'install', '-r', str(REQ_FILE)])
    REQ_STAMP.write_text(current_hash, encoding='utf-8')


def ensure_cloudflared() -> Path:
    local = BIN_DIR / ('cloudflared.exe' if os.name == 'nt' else 'cloudflared')
    if local.exists():
        return local
    path_cmd = shutil.which('cloudflared')
    if path_cmd:
        return Path(path_cmd)
    info('cloudflared не найден. Скачиваю автоматически...')
    url = ('https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe' if os.name == 'nt' else 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64')
    try:
        urllib.request.urlretrieve(url, local)
    except Exception as exc:
        fail(f'Не удалось скачать cloudflared автоматически: {exc}')
    return local


def load_pids() -> dict:
    if not PID_FILE.exists():
        return {}
    try:
        return json.loads(PID_FILE.read_text(encoding='utf-8'))
    except Exception:
        return {}


def save_pids(data: dict) -> None:
    PID_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def kill_pid(pid: int) -> None:
    try:
        if os.name == 'nt':
            subprocess.run(['taskkill', '/PID', str(pid), '/T', '/F'], capture_output=True)
        else:
            os.kill(pid, 15)
    except Exception:
        pass


def stop_previous() -> None:
    pids = load_pids()
    for name, pid in pids.items():
        try:
            pid_int = int(pid)
        except Exception:
            continue
        if pid_int > 0:
            info(f'Останавливаю прошлый процесс: {name} ({pid_int})')
            kill_pid(pid_int)
    save_pids({})


def tail_text(path: Path, max_chars: int = 4000) -> str:
    try:
        data = path.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        return ''
    data = data.strip()
    if len(data) <= max_chars:
        return data
    return data[-max_chars:]


def is_port_in_use(host: str, port: int) -> bool:
    check_host = '127.0.0.1' if host in {'0.0.0.0', '::', ''} else host
    with socket.socket() as sock:
        sock.settimeout(0.5)
        try:
            sock.connect((check_host, port))
            return True
        except Exception:
            return False


def wait_for_port(host: str, port: int, timeout: int = 30, log_file: Path | None = None, proc: subprocess.Popen | None = None) -> None:
    check_host = '127.0.0.1' if host in {'0.0.0.0', '::', ''} else host
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc and proc.poll() is not None:
            if log_file and log_file.exists():
                excerpt = tail_text(log_file)
                if excerpt:
                    print('\n----- backend.log -----', flush=True)
                    print(excerpt, flush=True)
                    print('----- end backend.log -----\n', flush=True)
            fail(f'Backend завершился с кодом {proc.returncode} до открытия порта. См. backend.log выше.')
        with socket.socket() as sock:
            sock.settimeout(1.0)
            try:
                sock.connect((check_host, port))
                return
            except Exception:
                time.sleep(0.5)
    if log_file and log_file.exists():
        excerpt = tail_text(log_file)
        if excerpt:
            print('\n----- backend.log -----', flush=True)
            print(excerpt, flush=True)
            print('----- end backend.log -----\n', flush=True)
    fail(f'Backend не открыл порт {host}:{port} за {timeout} сек.')


def start_process(cmd: list[str], log_file: Path, title: str, new_console: bool = False) -> subprocess.Popen:
    creationflags = 0
    startupinfo = None
    if os.name == 'nt' and new_console:
        creationflags = subprocess.CREATE_NEW_CONSOLE
    with log_file.open('ab') as out:
        # Using inherited handle requires opening separately without context closing too early
        pass
    out = log_file.open('ab')
    proc = subprocess.Popen(
        cmd,
        cwd=str(BASE_DIR),
        stdout=out,
        stderr=subprocess.STDOUT,
        creationflags=creationflags,
    )
    proc._log_handle = out  # keep alive
    info(f'{title} PID={proc.pid}')
    return proc


def get_backend_config() -> tuple[str, int]:
    host = '127.0.0.1'
    port = 8090
    if CONFIG_FILE.exists():
        text = CONFIG_FILE.read_text(encoding='utf-8', errors='ignore')
        m = re.search(r"^BACKEND_HOST\s*=\s*['\"]([^'\"]+)['\"]", text, flags=re.M)
        if m:
            host = m.group(1).strip()
        m = re.search(r'^BACKEND_PORT\s*=\s*(\d+)', text, flags=re.M)
        if m:
            port = int(m.group(1))
    return host, port


def capture_quick_tunnel_url(log_file: Path, proc: subprocess.Popen | None = None, timeout: int = 60) -> str | None:
    deadline = time.time() + timeout
    pattern = re.compile(r'https://(?!(?:api|www|developers|blog)\.)[a-zA-Z0-9\-]+\.trycloudflare\.com', re.IGNORECASE)
    last_size = 0
    while time.time() < deadline:
        if log_file.exists():
            data = log_file.read_text(encoding='utf-8', errors='ignore')
            for match in pattern.finditer(data):
                candidate = match.group(0).rstrip('/')
                if 'api.trycloudflare.com' not in candidate.lower():
                    return candidate
            if len(data) != last_size:
                last_size = len(data)
        if proc and proc.poll() is not None:
            return None
        time.sleep(1)
    return None


def main() -> None:
    os.chdir(BASE_DIR)
    py_exe = ensure_venv()
    ensure_token_present(py_exe)
    ensure_requirements(py_exe)
    cloudflared = ensure_cloudflared()
    stop_previous()

    host, port = get_backend_config()
    if is_port_in_use(host, port):
        fail(f'Порт {host}:{port} уже занят другим процессом на сервере! Смените BACKEND_PORT в config.py или .env.')

    URL_FILE.write_text('', encoding='utf-8')

    backend_log = LOGS_DIR / 'backend.log'
    bot_log = LOGS_DIR / 'bot.log'
    cloudflared_log = LOGS_DIR / 'cloudflared.log'
    for log in (backend_log, bot_log, cloudflared_log):
        log.write_text('', encoding='utf-8')

    info('Запускаю backend')
    backend = start_process([str(py_exe), '-m', 'miniapp'], backend_log, 'Backend')
    wait_for_port(host, port, timeout=40, log_file=backend_log, proc=backend)

    info('Запускаю Cloudflare Quick Tunnel')
    cloud = None
    url = None
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        if attempt > 1:
            warn(f'Повторная попытка запуска Quick Tunnel ({attempt}/{max_attempts})...')
            time.sleep(2)
        cloudflared_log.write_text('', encoding='utf-8')
        target_host = '127.0.0.1' if host in {'0.0.0.0', '::', ''} else host
        cloud = start_process([str(cloudflared), 'tunnel', '--url', f'http://{target_host}:{port}'], cloudflared_log, 'Cloudflared')
        url = capture_quick_tunnel_url(cloudflared_log, proc=cloud, timeout=60)
        if url:
            break
        try:
            cloud.terminate()
            cloud.wait(timeout=3)
        except Exception:
            try:
                cloud.kill()
            except Exception:
                pass

    if not url or not cloud or cloud.poll() is not None:
        if cloudflared_log.exists():
            excerpt = tail_text(cloudflared_log)
            if excerpt:
                print('\n----- cloudflared.log -----', flush=True)
                print(excerpt, flush=True)
                print('----- end cloudflared.log -----\n', flush=True)
        fail('Не удалось получить валидный trycloudflare URL. Проверь логи выше или запусти ещё раз.')

    URL_FILE.write_text(url, encoding='utf-8')
    info(f'Quick Tunnel URL: {url}')

    runtime_token = read_runtime_token(py_exe)
    bot_identity = fetch_bot_identity(runtime_token)
    if bot_identity:
        bot_name, bot_username, bot_id = bot_identity
    else:
        bot_name = '(имя недоступно)'
        bot_username = read_config_bot_username(py_exe) or '(без username)'
        bot_id = 0

    info(f'Запускается бот: name={bot_name}, username={bot_username}, id={bot_id}')

    info('Запускаю бота')
    bot = start_process([str(py_exe), 'main.py'], bot_log, 'Bot', new_console=True)

    save_pids({'backend': backend.pid, 'cloudflared': cloud.pid, 'bot': bot.pid})

    print('\n=== ГОТОВО ===', flush=True)
    print(f'Mini App URL: {url}/webapp', flush=True)
    print(f'Адрес API для админ-приложения: {url}', flush=True)
    print('Если бот уже открыт в Telegram, закрой и открой Mini App заново.', flush=True)
    print('Логи:', flush=True)
    print(f'  backend    -> {backend_log}', flush=True)
    print(f'  cloudflared-> {cloudflared_log}', flush=True)
    print(f'  bot        -> {bot_log}', flush=True)
    print('Для остановки всех процессов запусти STOP_ALL.bat', flush=True)


if __name__ == '__main__':
    main()
