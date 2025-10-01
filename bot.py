# bot.py - ОБНОВЛЕННАЯ ВЕРСИЯ
import os
import sys
import re
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram import Update, BotCommand
from telegram import ReplyKeyboardMarkup, KeyboardButton

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import BOT_TOKEN
from utils.logger import logger
from handlers.start_help import start_command, help_command, error_handler
from handlers.accounts import add_account_command, delete_account_command, list_accounts_command
from handlers.operations import handle_operation
from handlers.balance import show_balance_command
from handlers.callbacks import get_callback_handler
from handlers.reconciliation import reconcile_command, get_reconciliation_handlers
from core import create_tables
from export_to_excel import cleanup_old_exports


async def setup_commands(application):
    """Установка списка команд с подсказками для меню"""
    commands = [
        BotCommand("start", "Запустить бота"),
        BotCommand("help", "Показать справку по командам"),
        BotCommand("list", "/счета - Показать все счета"),
        BotCommand("balance", "/дай - Показать балансы и выписки"),
        BotCommand("reconcile", "/сверь - Архивировать историю операций")
    ]
    await application.bot.set_my_commands(commands)


def get_main_keyboard():
    """Создает основную клавиатуру с кнопками"""
    keyboard = [
        [KeyboardButton("/help"), KeyboardButton("/list")],
        [KeyboardButton("/reconcile"), KeyboardButton("/balance")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


async def start_with_keyboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start с клавиатурой"""
    user = update.effective_user
    logger.info(f"Пользователь {user.id} ({user.full_name}, @{user.username}) запустил бота")

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
- В группах видно кто создал счет или операцию

Удачи в учете! 📊
    """

    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_keyboard()
    )


def main():
    try:
        logger.info("Запуск бота-бухгалтера...")

        # Создаем таблицы БД (если их нет) - ВАЖНО: вызов create_tables() ДОЛЖЕН БЫТЬ ЗДЕСЬ
        logger.info("Создание/обновление таблиц базы данных...")
        create_tables()  # Эта функция теперь создает таблицы с колонками username
        logger.info("Таблицы базы данных успешно созданы/обновлены")

        # Очищаем старые файлы экспорта при запуске
        logger.info("Очистка старых файлов экспорта...")
        cleanup_old_exports()
        logger.info("Очистка файлов экспорта завершена")

        # Создаем приложение
        application = Application.builder().token(BOT_TOKEN).build()

        # Настраиваем команды бота с подсказками
        application.post_init = setup_commands

        # Добавляем обработчики команд
        application.add_handler(CommandHandler("start", start_with_keyboard))
        application.add_handler(CommandHandler("help", help_command))

        # Добавляем обработчики для кириллических команд через MessageHandler
        application.add_handler(MessageHandler(filters.Regex(r'^/добавь\s+'), add_account_command))
        application.add_handler(MessageHandler(filters.Regex(r'^/удали\s+'), delete_account_command))
        application.add_handler(MessageHandler(filters.Regex(r'^/счета$'), list_accounts_command))
        application.add_handler(MessageHandler(filters.Regex(r'^/дай'), show_balance_command))
        application.add_handler(MessageHandler(filters.Regex(r'^/сверь'), reconcile_command))

        # Обработчик для текстовых команд сверки (для обратной совместимости)
        application.add_handler(MessageHandler(
            filters.Regex(r'^(Кеша,\s*сверено|сверено)'),
            reconcile_command
        ))

        # Обработчик для финансовых операций
        application.add_handler(MessageHandler(
            filters.TEXT & filters.Regex(r'^/[a-zA-Zа-яА-Я0-9_].*'),
            handle_operation
        ))

        # Добавляем обработчики callback'ов
        application.add_handler(get_callback_handler())

        # Добавляем обработчики для сверки
        for handler in get_reconciliation_handlers():
            application.add_handler(handler)

        # Добавляем обработчик ошибок
        application.add_error_handler(error_handler)

        logger.info("Бот успешно инициализирован. Запускаем polling...")

        # Запускаем бота
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )

    except Exception as e:
        logger.critical(f"Критическая ошибка при запуске бота: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()