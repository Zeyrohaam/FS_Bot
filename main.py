import asyncio
import logging
import os
import subprocess
from pathlib import Path

from aiogram import BaseMiddleware, Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramConflictError
from aiogram.types import CallbackQuery, Message, TelegramObject

from config import ADMIN_IDS, TOKEN, ensure_required_settings, load_managed_settings, get_current_webapp_url
from database import db
from handlers import admin, calculator, miniapp, payments, reviews, support, user


BASE_DIR = Path(__file__).resolve().parent
LOCK_PATH = BASE_DIR / 'var' / 'runtime' / 'bot.lock'


def is_process_running(pid: int) -> bool:
    if pid <= 0:
        return False

    if os.name == 'nt':
        try:
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                return False
            output = (result.stdout or "").strip()
            return bool(output and str(pid) in output)
        except Exception:
            return False

    try:
        os.kill(pid, 0)
        return True
    except PermissionError:
        return True
    except ProcessLookupError:
        return False
    except OSError:
        return False


def acquire_runtime_lock(lock_path: Path | None = None) -> bool:
    lock_path = lock_path or LOCK_PATH
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    if lock_path.exists():
        try:
            content = lock_path.read_text(encoding='utf-8').strip()
            if content.isdigit():
                existing_pid = int(content)
                if existing_pid != os.getpid() and is_process_running(existing_pid):
                    return False
        except Exception:
            pass
        try:
            lock_path.unlink(missing_ok=True)
        except Exception:
            pass

    try:
        with lock_path.open('x', encoding='utf-8') as handle:
            handle.write(str(os.getpid()))
        return True
    except FileExistsError:
        return False


def release_runtime_lock(lock_path: Path | None = None) -> None:
    lock_path = lock_path or LOCK_PATH
    try:
        lock_path.unlink(missing_ok=True)
    except Exception:
        pass


async def watch_runtime_settings():
    while True:
        try:
            load_managed_settings()
        except Exception as exc:
            logging.warning('Не удалось обновить runtime-настройки: %s', exc)
        await asyncio.sleep(2)


class BanCheckMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler,
        event: TelegramObject,
        data: dict,
    ):
        user_obj = data.get('event_from_user')
        if user_obj:
            admin_set = set(int(x) for x in ADMIN_IDS if str(x).isdigit())
            if int(user_obj.id) not in admin_set:
                db.refresh()
                if db.is_user_banned(user_obj.id):
                    if isinstance(event, Message):
                        await event.answer("⛔️ <b>Ваш аккаунт заблокирован администратором.</b>")
                    elif isinstance(event, CallbackQuery):
                        await event.answer("⛔️ Ваш аккаунт заблокирован администратором.", show_alert=True)
                    return
        return await handler(event, data)


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    ensure_required_settings()

    if not acquire_runtime_lock():
        logging.error("Бот уже запущен. Второй экземпляр остановлен.")
        raise SystemExit(1)

    watcher_task = None
    try:
        bot = Bot(TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        me = await bot.get_me()
        bot_username = f"@{me.username}" if me.username else "(без username)"
        logging.info("Запускается бот: name=%s, username=%s, id=%s", me.full_name, bot_username, me.id)

        current_webapp = get_current_webapp_url()
        if current_webapp and current_webapp.startswith("https://") and "api.trycloudflare.com" not in current_webapp:
            try:
                from aiogram.types import MenuButtonWebApp, WebAppInfo
                await bot.set_chat_menu_button(
                    menu_button=MenuButtonWebApp(text="📱 Mini App", web_app=WebAppInfo(url=current_webapp))
                )
                logging.info("Меню-кнопка Web App обновлена: %s", current_webapp)
            except Exception as exc:
                logging.warning("Не удалось обновить MenuButtonWebApp: %s", exc)

        dp = Dispatcher()

        ban_middleware = BanCheckMiddleware()
        dp.message.outer_middleware(ban_middleware)
        dp.callback_query.outer_middleware(ban_middleware)

        dp.include_router(admin.router)
        dp.include_router(calculator.router)
        dp.include_router(reviews.router)
        dp.include_router(payments.router)
        dp.include_router(miniapp.router)
        dp.include_router(support.router)
        dp.include_router(user.router)

        watcher_task = asyncio.create_task(watch_runtime_settings())
        logging.info("Бот запущен")
        await dp.start_polling(bot)
    except TelegramConflictError as exc:
        logging.error("Конфликт polling: %s", exc)
        raise SystemExit(1) from exc
    finally:
        if watcher_task is not None:
            watcher_task.cancel()
            await asyncio.gather(watcher_task, return_exceptions=True)
        release_runtime_lock()


if __name__ == "__main__":
    asyncio.run(main())
