from datetime import datetime

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram import Bot

from config import REVIEWS_CHANNEL, ADMIN_IDS
from keyboards.reply import menu_with_back, support_category_menu
from database import db
from utils.helpers import register_user_if_needed

router = Router()


class ReviewStates(StatesGroup):
    waiting_text = State()


async def show_reviews_menu(message: Message):
    user = message.from_user
    user_info = register_user_if_needed(user.id, user.username)

    keyboard_rows = [
        [InlineKeyboardButton(text="📊 Смотреть отзывы", url=f"https://t.me/{REVIEWS_CHANNEL.lstrip('@')}")]
    ]
    if user_info.get("total_stars", 0) > 0 or user.id in ADMIN_IDS:
        keyboard_rows.append([InlineKeyboardButton(text="✍️ Оставить отзыв", callback_data="leave_review")])

    await message.answer(
        f"💬 <b>Отзывы клиентов</b>\n\n"
        f"Все отзывы публикуются в нашем канале:\n"
        f"📢 {REVIEWS_CHANNEL}\n\n"
        f"<i>Оставить отзыв могут пользователи, совершившие покупку</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_rows),
    )


@router.callback_query(F.data == "leave_review")
async def start_review(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ReviewStates.waiting_text)
    await callback.message.answer(
        "✍️ <b>Написать отзыв</b>\n\n"
        "Расскажите о вашем опыте с Freaking Stars — ваш отзыв поможет другим покупателям!\n\n"
        "<i>Напишите коротко и по делу</i>",
        parse_mode="HTML",
        reply_markup=menu_with_back(callback.from_user.id in ADMIN_IDS),
    )
    await callback.answer()


@router.message(ReviewStates.waiting_text)
async def process_review(message: Message, state: FSMContext, bot: Bot):
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
            "❌ <b>Отзыв не может быть пустым</b>\n\n"
            "<i>Напишите что-нибудь о вашем опыте</i>",
            parse_mode="HTML",
        )
        return

    user = message.from_user
    import html as html_lib
    import re
    # Strip HTML tags and escape HTML entities
    cleaned_text = re.sub(r'<[^>]*>', '', text).strip()
    safe_text = html_lib.escape(cleaned_text, quote=True)
    if len(safe_text) > 500:
        safe_text = safe_text[:500]

    db.reviews.append({
        "user_id": user.id,
        "text": safe_text,
        "date": datetime.now().strftime("%d.%m.%Y"),
    })
    if str(user.id) in db.users:
        db.users[str(user.id)]["has_review"] = True
    db.save_data()

    safe_name = html_lib.escape(user.full_name or "Покупатель", quote=False)

    await bot.send_message(
        REVIEWS_CHANNEL,
        f"⭐️ <b>Новый отзыв</b>\n\n"
        f"{safe_text}\n\n"
        f"— <i>{safe_name}</i>",
        parse_mode="HTML",
    )

    await state.clear()
    await message.answer(
        "✅ <b>Спасибо за отзыв!</b>\n\n"
        "<i>Ваш отзыв опубликован в нашем канале</i> 💬",
        parse_mode="HTML",
    )
