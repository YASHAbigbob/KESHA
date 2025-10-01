from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from utils.logger import logger


def get_main_keyboard():
    """Создает основную клавиатуру с кнопками"""
    keyboard = [
        [KeyboardButton("/help"), KeyboardButton("/счета")],
        [KeyboardButton("/сверь"), KeyboardButton("/дай")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    logger.info(f"Пользователь {user.id} ({user.full_name}) запустил бота")

    welcome_text = """
🤖 Добро пожаловать в бота-бухгалтера Кешу!

Я помогу вам вести учет финансов по разным счетам.

📋 Основные команды:
/start - начать работу
/help - помощь
/добавь - создать новый счет
/удали - удалить счет  
/счета - показать все счета
/дай - показать балансы
/сверь - архивация истории

💡 Текстовые команды:
Кеша, сверено - архивировать историю
сверено - сокращенный вариант

💡 Пример использования:
/добавь руб
/руб 100+50*2 Зарплата
/дай руб
/сверь руб

✨ Особенности:
- Названия счетов могут содержать пробелы
- Поддерживаются сложные математические выражения
- История операций с архивацией

Удачи в учете! 📊
    """

    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_keyboard()
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    user = update.effective_user
    logger.info(f"Пользователь {user.id} запросил помощь")

    help_text = """
📋 **Справка по командам:**

💡 **Для быстрого доступа ко всем командам введите /** 

💼 **Управление счетами:**
/добавь [название] - создать счет (можно несколько слов)
/удали [название] - удалить счет
/счета - список всех счетов

💳 **Операции:**
/[счет] [сумма] [комментарий] - добавить операцию
Пример: /руб 100+50*2 Зарплата
Пример: /банковская карта 1500 Покупка продуктов

📊 **Просмотр:**
/дай - балансы по всем счетам
/дай [счет] - выписка по счету

🔄 **Сверка:**
/сверь - выбор счета для сверки
/сверь [счет] - сверка конкретного счета

⚡ **Быстрый старт:**
1. /добавь руб
2. /руб 100+50*2 Первая операция
3. /дай
4. /сверь руб - архивировать историю

   """

    await update.message.reply_text(
        help_text,
        reply_markup=get_main_keyboard()
    )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logger.error(f"Ошибка при обработке update {update}: {context.error}")

    if update and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ Произошла ошибка. Попробуйте еще раз или обратитесь к разработчику.",
            reply_markup=get_main_keyboard()
        )