from aiogram import Router
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo

from config import get_current_webapp_url

router = Router()


def build_open_app_keyboard() -> InlineKeyboardMarkup:
    url = get_current_webapp_url().rstrip('/') + '?v=4'
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text='📱 Открыть Mini App', web_app=WebAppInfo(url=url))]
        ]
    )


@router.message(Command('app'))
async def open_app_command(message: Message):
    await message.answer('Открыть приложение:', reply_markup=build_open_app_keyboard())
