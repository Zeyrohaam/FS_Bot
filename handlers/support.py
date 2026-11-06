from datetime import datetime

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from config import ADMIN_IDS, SUPPORT_USERNAME
from keyboards.reply import menu_with_back, support_category_menu
from database import db
from utils.helpers import register_user_if_needed

router = Router()


class SupportStates(StatesGroup):
    waiting_suggestion = State()


async def support_menu(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✉️ Написать в поддержку", url=f"https://t.me/{SUPPORT_USERNAME.lstrip('@')}")]
    ])
    await message.answer(
        "🛠️ <b>Поддержка</b>\n\n"
        "Если у вас возник вопрос или проблема — наша команда готова помочь!\n\n"
        "<i>Нажмите кнопку ниже, чтобы написать нам напрямую</i>",
        parse_mode="HTML",
        reply_markup=keyboard,
    )


async def suggestion_menu(message: Message, state: FSMContext):
    await state.set_state(SupportStates.waiting_suggestion)
    await message.answer(
        "💡 <b>Предложение по магазину</b>\n\n"
        "Напишите свою идею одним сообщением — она будет отправлена администрации на рассмотрение.\n\n"
        "<i>Ваше мнение важно для нас!</i>",
        parse_mode="HTML",
        reply_markup=menu_with_back(message.from_user.id in ADMIN_IDS),
    )


@router.message(SupportStates.waiting_suggestion)
async def receive_suggestion(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if text == "⬅️ Назад":
        await state.clear()
        await message.answer(
            "💬 <b>Раздел поддержки</b>\n\n"
            "🛠️ Поддержка — связаться с командой\n"
            "💡 Предложения — идеи по магазину\n"
            "📣 Отзывы — смотреть и оставлять отзывы\n\n"
            "<i>Выберите нужный раздел</i>",
            parse_mode="HTML",
            reply_markup=support_category_menu(message.from_user.id in ADMIN_IDS),
        )
        return
    if not text:
        await message.answer(
            "❌ <b>Отправьте предложение текстом</b>\n\n"
            "<i>Предложение должно быть в одном сообщении</i>",
            parse_mode="HTML",
        )
        return

    register_user_if_needed(message.from_user.id, message.from_user.username)
    suggestion = {
        "id": db.suggestion_id_counter,
        "user_id": message.from_user.id,
        "username": message.from_user.username or "unknown",
        "text": text,
        "status": "pending",
        "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
    }
    db.suggestions.append(suggestion)
    db.suggestion_id_counter += 1
    db.save_data()
    await state.clear()

    import html as html_lib
    safe_text = html_lib.escape(text, quote=False)
    safe_username = html_lib.escape(suggestion['username'], quote=False)

    for admin_id in ADMIN_IDS:
        try:
            await message.bot.send_message(
                admin_id,
                f"💡 <b>Новое предложение</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n\n"
                f"#️⃣ ID: #{suggestion['id']}\n"
                f"👤 Пользователь: @{safe_username} (<code>{suggestion['user_id']}</code>)\n"
                f"📅 Дата: {suggestion['date']}\n\n"
                f"📝 <b>Текст:</b>\n{safe_text}",
                parse_mode="HTML",
            )
        except Exception:
            pass

    await message.answer(
        f"✅ <b>Предложение отправлено!</b>\n\n"
        f"Администрация рассмотрит его в ближайшее время.\n\n"
        f"<i>Ваше предложение:</i>\n{safe_text}",
        parse_mode="HTML",
    )
