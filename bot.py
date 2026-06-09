import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
from ai_client import get_legal_response
from keyboards import get_main_keyboard, get_feedback_keyboard
from file_parser import extract_text_from_bytes

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

user_sessions: dict[int, list] = {}

WELCOME_TEXT = """
⚖️ *Добро пожаловать в Qazaq Legal AI*

Я — AI-ассистент по юридическим вопросам Казахстана.

Я могу помочь разобраться в:
• 📋 Трудовых спорах и правах работника
• 🏠 Жилищных и имущественных вопросах
• 💼 Договорных отношениях
• 👨‍👩‍👧 Семейном праве и алиментах
• 🚗 ДТП и административных нарушениях
• 🏦 Защите прав потребителей
• 📑 Регистрации бизнеса и ИП

*Напишите вопрос или прикрепите договор (PDF или DOCX) для анализа.*

⚠️ _Все ответы носят информационный характер и не являются официальной юридической консультацией._
"""

def _init_session(user_id: int):
    if user_id not in user_sessions:
        user_sessions[user_id] = []

async def _ask_ai(message: Message, user_id: int, user_text: str):
    """Отправить запрос к AI и ответить пользователю."""
    await bot.send_chat_action(message.chat.id, "typing")
    user_sessions[user_id].append({"role": "user", "content": user_text})
    if len(user_sessions[user_id]) > 10:
        user_sessions[user_id] = user_sessions[user_id][-10:]
    try:
        response = await get_legal_response(user_sessions[user_id])
        user_sessions[user_id].append({"role": "assistant", "content": response})
        if len(response) > 4000:
            parts = [response[i:i+4000] for i in range(0, len(response), 4000)]
            for i, part in enumerate(parts):
                kb = get_feedback_keyboard() if i == len(parts) - 1 else None
                await message.answer(part, parse_mode="Markdown", reply_markup=kb)
        else:
            await message.answer(response, parse_mode="Markdown", reply_markup=get_feedback_keyboard())
    except Exception as e:
        logger.error(f"AI error: {e}")
        await message.answer(
            "⚠️ Ошибка при обработке запроса. Попробуйте ещё раз или /new для нового диалога.",
            reply_markup=get_main_keyboard()
        )

@dp.message(CommandStart())
async def cmd_start(message: Message):
    user_sessions[message.from_user.id] = []
    await message.answer(WELCOME_TEXT, parse_mode="Markdown", reply_markup=get_main_keyboard())

@dp.message(Command("new"))
async def cmd_new(message: Message):
    user_sessions[message.from_user.id] = []
    await message.answer("🔄 *Новый диалог начат.*\n\nЗадайте ваш юридический вопрос.", parse_mode="Markdown", reply_markup=get_main_keyboard())

@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer("""
📌 *Команды бота:*

/start — Начать работу
/new — Новый диалог
/help — Справка
/examples — Примеры вопросов

📎 *Анализ документов:*
Просто прикрепите файл PDF или DOCX — бот прочитает и проанализирует договор.

💡 *Совет:* После отправки файла можно задать уточняющий вопрос, например: _"Есть ли в этом договоре риски для меня?"_
""", parse_mode="Markdown")

@dp.message(Command("examples"))
async def cmd_examples(message: Message):
    await message.answer("""
💬 *Примеры вопросов:*

1️⃣ "Работодатель не выплатил зарплату 2 месяца. Что делать?"
2️⃣ "Сосед залил квартиру, ущерб 500 000 тенге. Могу взыскать?"
3️⃣ "Хочу уволиться, но не отдают трудовую. Законно?"
4️⃣ "Купил телефон, через неделю сломался, отказывают в возврате."
5️⃣ "Как открыть ИП в Казахстане?"

📎 *Или прикрепите договор PDF/DOCX — я его проанализирую.*
""", parse_mode="Markdown")

@dp.message(F.text == "📋 Примеры вопросов")
async def btn_examples(message: Message):
    await cmd_examples(message)

@dp.message(F.text == "🔄 Новый диалог")
async def btn_new(message: Message):
    await cmd_new(message)

@dp.message(F.text == "ℹ️ О боте")
async def btn_about(message: Message):
    await message.answer("""
⚖️ *Qazaq Legal AI — AI-ассистент*

*Версия:* 1.1
*Законодательство:* Республика Казахстан

*Что умеет:*
✅ Анализировать юридические ситуации
✅ Читать и анализировать PDF и DOCX договоры
✅ Ссылаться на законы РК
✅ Давать рекомендации по шагам
✅ Оценивать перспективы дела

*Чего НЕ делает:*
❌ Не заменяет адвоката
❌ Не даёт официальных заключений

*Форматы документов:* PDF, DOCX (до 20 МБ)
""", parse_mode="Markdown")

# ── ОБРАБОТКА ДОКУМЕНТОВ (PDF и DOCX) ──
@dp.message(F.document)
async def handle_document(message: Message):
    user_id = message.from_user.id
    _init_session(user_id)

    doc = message.document
    filename = doc.file_name or "document"
    fname_lower = filename.lower()

    # Проверяем формат
    if not (fname_lower.endswith(".pdf") or fname_lower.endswith(".docx")):
        await message.answer(
            "⚠️ Поддерживаются только файлы *PDF* и *DOCX*.\n\nПожалуйста, прикрепите договор в одном из этих форматов.",
            parse_mode="Markdown"
        )
        return

    # Проверяем размер (20 МБ)
    if doc.file_size and doc.file_size > 20 * 1024 * 1024:
        await message.answer("⚠️ Файл слишком большой. Максимальный размер — 20 МБ.")
        return

    await message.answer(f"📄 Получен файл: *{filename}*\nЧитаю документ...", parse_mode="Markdown")
    await bot.send_chat_action(message.chat.id, "typing")

    try:
        # Скачиваем файл
        file = await bot.get_file(doc.file_id)
        file_bytes = await bot.download_file(file.file_path)
        content = file_bytes.read() if hasattr(file_bytes, 'read') else bytes(file_bytes)

        # Извлекаем текст
        extracted_text = await extract_text_from_bytes(content, filename)

        if extracted_text.startswith("[Ошибка") or extracted_text.startswith("[Файл"):
            await message.answer(f"⚠️ {extracted_text}")
            return

        word_count = len(extracted_text.split())
        await message.answer(
            f"✅ Документ прочитан ({word_count} слов).\n\n🔍 *Анализирую содержимое...*",
            parse_mode="Markdown"
        )
        await bot.send_chat_action(message.chat.id, "typing")

        # Формируем запрос к AI — с подсказкой о типе анализа
        caption = message.caption or ""
        if caption:
            ai_prompt = f"Пользователь прислал документ '{filename}' и написал: «{caption}»\n\nСОДЕРЖИМОЕ ДОКУМЕНТА:\n{extracted_text}"
        else:
            ai_prompt = (
                f"Пользователь прислал документ '{filename}' для юридического анализа.\n\n"
                f"СОДЕРЖИМОЕ ДОКУМЕНТА:\n{extracted_text}\n\n"
                f"Проведи детальный юридический анализ этого документа: "
                f"определи тип документа, выяви потенциальные риски и невыгодные условия, "
                f"укажи на пункты которые требуют внимания, и дай рекомендации."
            )

        await _ask_ai(message, user_id, ai_prompt)

    except Exception as e:
        logger.error(f"Document handling error: {e}")
        await message.answer(
            "⚠️ Не удалось обработать файл. Убедитесь что файл не защищён паролем и попробуйте снова.",
            reply_markup=get_main_keyboard()
        )

# ── ОБРАБОТКА ТЕКСТОВЫХ ВОПРОСОВ ──
@dp.message(F.text)
async def handle_question(message: Message):
    user_id = message.from_user.id
    _init_session(user_id)
    await _ask_ai(message, user_id, message.text.strip())

@dp.callback_query(F.data.startswith("feedback_"))
async def handle_feedback(callback: types.CallbackQuery):
    feedback = callback.data.split("_")[1]
    if feedback == "helpful":
        await callback.answer("✅ Спасибо! Рад помочь.", show_alert=False)
    else:
        await callback.answer("📝 Спасибо! Попробуйте уточнить вопрос.", show_alert=False)
    await callback.message.edit_reply_markup(reply_markup=None)

async def main():
    logger.info("🚀 Qazaq Legal AI Bot v1.1 запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
