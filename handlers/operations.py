# operations.py - ОБНОВЛЕННАЯ ВЕРСИЯ С USERNAME
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from telegram.error import TimedOut, NetworkError
from utils.logger import logger
from crud import get_user_accounts, create_transaction, get_account_transactions, get_account_balance, ensure_chat_exists
from calc import def_calc
from datetime import datetime
import asyncio


def get_main_keyboard():
    """Создает основную клавиатуру с кнопками"""
    keyboard = [
        [KeyboardButton("/help"), KeyboardButton("/счета")],
        [KeyboardButton("/сверь"), KeyboardButton("/дай")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


async def handle_operation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик финансовых операций с поддержкой username"""
    user = update.effective_user
    user_id = user.id
    username = user.username or user.full_name  # Получаем username
    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type

    # Убедимся, что чат существует
    ensure_chat_exists(chat_id, chat_type, update.effective_chat.title)

    if not update.message.text:
        return

    # Получаем текст команды (убираем первый /)
    command_text = update.message.text[1:].strip()

    try:
        # Получаем все счета пользователя для поиска
        accounts = get_user_accounts(user_id, chat_id)
        if not accounts:
            # Если нет счетов, это не операция
            return

        # Сортируем счета по длине названия (от длинного к короткому)
        accounts_sorted = sorted(accounts, key=lambda x: len(x['account_name']), reverse=True)

        target_account = None
        expression = ""
        comment = ""

        # Ищем подходящий счет
        for account in accounts_sorted:
            account_name_lower = account['account_name'].lower()
            command_text_lower = command_text.lower()

            # Проверяем, начинается ли команда с названия счета
            if command_text_lower.startswith(account_name_lower + ' '):
                target_account = account
                remaining_text = command_text[len(account['account_name']):].strip()
                break

        # Если не нашли длинное совпадение, пробуем найти по первому слову
        if not target_account:
            first_word = command_text.split()[0].lower() if command_text.split() else ""
            for account in accounts:
                account_first_word = account['account_name'].split()[0].lower() if account['account_name'].split() else ""
                if account_first_word == first_word:
                    target_account = account
                    remaining_text = ' '.join(command_text.split()[1:])
                    break

        if not target_account:
            # Если это не операция, а неизвестная команда - игнорируем
            return

        # Разбираем оставшийся текст на выражение и комментарий
        parts = remaining_text.split(maxsplit=1)
        if len(parts) >= 1:
            expression = parts[0].strip()
            if len(parts) > 1:
                comment = parts[1].strip()

        logger.info(f"Пользователь {user_id} ({username}) добавляет операцию: {target_account['account_name']} {expression} {comment}")

        # Проверяем выражение
        if not expression:
            await update.message.reply_text(
                f"❌ Укажите сумму операции. Например:\n"
                f"`/{target_account['account_name']} 100+50*2 Комментарий`\n"
                f"💡 Для деления используйте знак `:`",
                reply_markup=get_main_keyboard()
            )
            return

        # Вычисляем сумму с помощью калькулятора Кати с учетом разрядности счета
        logger.info(f"Вычисляем выражение: {expression} с разрядностью {target_account['precision']}")
        result = def_calc(expression, target_account['precision'])
        logger.info(f"Результат вычисления: {result}")

        if "Ошибка" in result:
            await update.message.reply_text(
                f"❌ {result}",
                reply_markup=get_main_keyboard()
            )
            return

        try:
            amount = float(result)
        except ValueError as e:
            logger.error(f"Ошибка преобразования результата {result} в float: {e}")
            await update.message.reply_text(
                "❌ Не удалось вычислить сумму операции.",
                reply_markup=get_main_keyboard()
            )
            return

        # Создаем транзакцию С USERNAME
        transaction_id = create_transaction(
            target_account['account_id'],
            chat_id,
            amount,
            datetime.now(),
            comment,
            user_id,
            username  # Передаем username
        )

        # Используем единую функцию расчета баланса
        balance = get_account_balance(target_account['account_id'])

        logger.info(f"Пользователь {user_id} ({username}) добавил операцию: {target_account['account_name']} {amount}")

        # Форматируем ответ с учетом разрядности
        amount_str = f"+{amount:.{target_account['precision']}f}" if amount >= 0 else f"{amount:.{target_account['precision']}f}"
        balance_str = f"{balance:.{target_account['precision']}f}"

        response = f"✅ Запомнил. {amount_str}\n"
        response += f"Баланс: {balance_str} {target_account['account_name']}"

        if comment:
            response += f"\n💬 {comment}"

        # В группах показываем кто добавил операцию
        if chat_type != "private":
            response += f"\n👤 @{username}" if user.username else f"\n👤 {user.full_name}"

        # Создаем кнопку "Откатить"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Откатить", callback_data=f"cancel_{transaction_id}")]
        ])

        # Пытаемся отправить с кнопкой, при ошибке - без кнопки
        try:
            await update.message.reply_text(response, reply_markup=keyboard)
        except (TimedOut, NetworkError) as e:
            logger.warning(f"Таймаут при отправке кнопки, отправляем без кнопки: {e}")
            await update.message.reply_text(
                response + "\n\n⚠️ Кнопка отката временно недоступна",
                reply_markup=get_main_keyboard()
            )
        except Exception as e:
            logger.error(f"Ошибка при отправке кнопки: {e}")
            await update.message.reply_text(
                response,
                reply_markup=get_main_keyboard()
            )

    except Exception as e:
        logger.error(f"Ошибка при добавлении операции для пользователя {user_id} ({username}): {e}", exc_info=True)
        await update.message.reply_text(
            "❌ Произошла ошибка при добавлении операции.",
            reply_markup=get_main_keyboard()
        )