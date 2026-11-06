from aiogram import F
from aiogram.types import CallbackQuery, Message

from .common import _build_games_menu, _get_user_data, router


async def show_games_menu(message: Message):
    _get_user_data(message.from_user.id, message.from_user.username)
    await message.answer("🎮 Игры\n\nВыберите игру:", reply_markup=_build_games_menu())


@router.callback_query(F.data == "games_no_balance")
async def games_no_balance(callback: CallbackQuery):
    await callback.answer("Сначала пополните любой баланс", show_alert=True)
