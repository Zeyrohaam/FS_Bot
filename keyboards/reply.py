from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def _main_menu_rows(is_admin: bool = False) -> list[list[KeyboardButton]]:
    keyboard = [
        [KeyboardButton(text="🛍️ Покупки"), KeyboardButton(text="🆘 Поддержка")],
        [KeyboardButton(text="🎁 Промокод"), KeyboardButton(text="👥 Рефералы")],
        [KeyboardButton(text="👤 Профиль")],
    ]
    if is_admin:
        keyboard.append([KeyboardButton(text="⚙️ Админ-панель")])
    return keyboard


def main_menu(is_admin: bool = False) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=_main_menu_rows(is_admin), resize_keyboard=True)


def menu_with_back(is_admin: bool = False) -> ReplyKeyboardMarkup:
    rows = _main_menu_rows(is_admin)
    rows.append([KeyboardButton(text="⬅️ Назад")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def purchases_menu(is_admin: bool = False) -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text="💰 Купить Stars"), KeyboardButton(text="👑 Купить Premium")],
        [KeyboardButton(text="💠 Купить TON"), KeyboardButton(text="🧮 Посчитать")],
        [KeyboardButton(text="⬅️ Назад")],
    ]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def support_category_menu(is_admin: bool = False) -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text="🛠️ Поддержка"), KeyboardButton(text="💡 Предложения")],
        [KeyboardButton(text="📣 Отзывы")],
        [KeyboardButton(text="⬅️ Назад")],
    ]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def back_only_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="⬅️ Назад")]], resize_keyboard=True)
