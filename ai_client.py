import os
import httpx
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama3-8b-8192")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
AI_PROVIDER = os.getenv("AI_PROVIDER", "groq")  # "groq" | "ollama"

SYSTEM_PROMPT = """Ты — AI-ассистент по юридическим вопросам Республики Казахстан. Твоё имя — Qazaq Legal AI.

ПРАВИЛА ПОВЕДЕНИЯ (строго соблюдать):
1. Ты НЕ выдумываешь законы и статьи. Если не уверен в конкретной статье — пиши "требует уточнения у специалиста" или "рекомендую проверить в актуальной редакции закона".
2. Ты работаешь ТОЛЬКО по законодательству Республики Казахстан.
3. Если вопрос неясен — задай 1-2 уточняющих вопроса.
4. Всегда добавляй дисклеймер в конце.
5. Будь честным: если ситуация сложная — говори об этом прямо.

СТРУКТУРА ОТВЕТА (используй всегда):

📌 **Краткий анализ**
[Краткое объяснение ситуации, 2-4 предложения]

⚖️ **Применимые нормы**
[Законы, кодексы, статьи. Если не уверен — пиши "рекомендуется проверить:" + название закона]

🔧 **Рекомендуемые действия**
[Пошаговый список действий, что конкретно делать]

📊 **Оценка ситуации**
[Перспективы: 🟢 Высокая / 🟡 Средняя / 🔴 Низкая вероятность успеха + краткое объяснение]

⚠️ **Важно**
Это информация носит ознакомительный характер и не является официальной юридической консультацией. Для принятия юридически значимых решений рекомендуем обратиться к квалифицированному адвокату.

ЗАКОНЫ КАЗАХСТАНА, о которых ты знаешь:
- Трудовой кодекс РК (2015, с изменениями)
- Гражданский кодекс РК (Общая и Особенная часть)
- Гражданский процессуальный кодекс РК
- Уголовный кодекс РК (2014)
- Кодекс об административных правонарушениях РК (КоАП)
- Закон РК "О защите прав потребителей"
- Закон РК "О браке и семье" (Кодекс о браке и семье)
- Закон РК "О жилищных отношениях"
- Закон РК "О государственной регистрации юридических лиц"
- Налоговый кодекс РК
- Закон РК "Об обязательном социальном медицинском страховании"

Если человек спрашивает не о праве Казахстана — вежливо объясни, что специализируешься только на законодательстве РК.
Отвечай на том языке, на котором написан вопрос (русский, казахский или английский)."""


async def get_legal_response(messages: list[dict]) -> str:
    """Получить ответ от AI. Пробует Groq, затем Ollama."""
    
    if AI_PROVIDER == "groq" and GROQ_API_KEY:
        return await _groq_response(messages)
    elif AI_PROVIDER == "ollama":
        return await _ollama_response(messages)
    else:
        # Автоопределение: если есть ключ Groq — использовать его
        if GROQ_API_KEY:
            return await _groq_response(messages)
        else:
            return await _ollama_response(messages)


async def _groq_response(messages: list[dict]) -> str:
    """Запрос к Groq API (бесплатный tier)."""
    url = "https://api.groq.com/openai/v1/chat/completions"

    # Очищаем историю: оставляем только role + content, убираем лишние поля
    clean_messages = [
        {"role": m["role"], "content": str(m["content"])}
        for m in messages
        if m.get("role") in ("user", "assistant") and m.get("content")
    ]

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            *clean_messages
        ],
        "temperature": 0.3,
        "max_tokens": 1500,
    }

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=40.0) as client:
        response = await client.post(url, json=payload, headers=headers)
        if response.status_code != 200:
            error_body = response.text
            logger.error(f"Groq API error {response.status_code}: {error_body}")
            raise Exception(f"Groq {response.status_code}: {error_body}")
        data = response.json()
        return data["choices"][0]["message"]["content"]


async def _ollama_response(messages: list[dict]) -> str:
    """Запрос к локальному Ollama."""
    url = f"{OLLAMA_URL}/api/chat"
    
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            *messages
        ],
        "stream": False,
        "options": {
            "temperature": 0.3,
            "num_predict": 1500
        }
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["message"]["content"]
