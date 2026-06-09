from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Главная клавиатура."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📋 Примеры вопросов"),
                KeyboardButton(text="🔄 Новый диалог"),
            ],
            [
                KeyboardButton(text="ℹ️ О боте"),
            ]
        ],
        resize_keyboard=True,
        input_field_placeholder="Опишите вашу юридическую ситуацию..."
    )
    return keyboard


def get_feedback_keyboard() -> InlineKeyboardMarkup:
    """Кнопки обратной связи после ответа."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Полезно", callback_data="feedback_helpful"),
                InlineKeyboardButton(text="🔄 Уточнить", callback_data="feedback_refine"),
            ]
        ]
    )
    return keyboard
