# reconciliation.py - ОБНОВЛЕННАЯ ВЕРСИЯ С USERNAME
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes, CallbackQueryHandler
from utils.logger import logger
from crud import (
    get_user_accounts, get_account_transactions, create_reconciliation,
    archive_all_transactions, get_last_reconciliation, get_account_balance, ensure_chat_exists
)
from datetime import datetime


def get_main_keyboard():
    """Создает основную клавиатуру с кнопками"""
    keyboard = [
        [KeyboardButton("/help"), KeyboardButton("/счета")],
        [KeyboardButton("/сверь"), KeyboardButton("/дай")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def reconcile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды сверки с поддержкой username"""
    user = update.effective_user
    user_id = user.id
    username = user.username or user.full_name  # Получаем username
    chat_id = update.effective_chat.id
    text = update.message.text

    logger.info(f"Пользователь {user_id} ({username}) запросил сверку: {text}")

    try:
        accounts = get_user_accounts(user_id, chat_id)

        if not accounts:
            await update.message.reply_text(
                "💼 У вас пока нет счетов для сверки.\n\n"
                "Создайте первый счет командой `/добавь руб`",
                reply_markup=get_main_keyboard()
            )
            return

        # Извлекаем название счета из текста команды
        account_name = extract_account_name(text)

        # Если указан конкретный счет
        if account_name:
            target_account = None
            for account in accounts:
                # УЛУЧШЕННЫЙ ПОИСК - нормализуем строки
                account_name_normalized = account['account_name'].lower().strip().replace(' ', '')
                specific_name_normalized = account_name.lower().strip().replace(' ', '')

                if account_name_normalized == specific_name_normalized:
                    target_account = account
                    break

            if target_account:
                await perform_reconciliation(update, target_account, chat_id, username)
                return
            else:
                await update.message.reply_text(
                    f"❌ Счет '{account_name}' не найден.",
                    reply_markup=get_main_keyboard()
                )
                # Продолжаем показываем кнопки для выбора

        # Если счет не указан или не найден - показываем выбор счета
        await show_account_selection(update, accounts, chat_id, username)

    except Exception as e:
        logger.error(f"Ошибка при обработке команды сверки для пользователя {user_id} ({username}): {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при выполнении сверки.",
            reply_markup=get_main_keyboard()
        )


def extract_account_name(text):
    """Извлекает название счета из текста команды"""
    text_lower = text.lower().strip()

    # Для команды /сверь
    if text_lower.startswith('/сверь'):
        account_part = text[6:].strip()
        return account_part if account_part else None

    # Для старых текстовых команд (обратная совместимость)
    elif text_lower.startswith('кеша, сверено'):
        account_part = text[13:].strip()
        return account_part if account_part else None
    elif text_lower.startswith('сверено'):
        account_part = text[7:].strip()
        return account_part if account_part else None

    return None


async def show_account_selection(update, accounts, chat_id, username):
    """Показывает выбор счета для сверки"""
    keyboard_buttons = []
    for account in accounts:
        # Используем единую функцию расчета баланса
        balance = get_account_balance(account['account_id'])

        # Получаем последнюю сверку
        last_recon = get_last_reconciliation(account['account_id'])
        balance_info = f": {balance:.2f}"
        if last_recon:
            balance_info += f" (с прошлой сверки: {last_recon['balance']:.2f})"
        else:
            balance_info += " (первая сверка)"

        button_text = f"{account['account_name']}{balance_info}"
        keyboard_buttons.append([
            InlineKeyboardButton(button_text, callback_data=f"reconcile_{account['account_id']}")
        ])

    # Добавляем кнопку для всех счетов
    keyboard_buttons.append([
        InlineKeyboardButton("🔄 Свернуть ВСЕ счета", callback_data="reconcile_all")
    ])

    reply_markup = InlineKeyboardMarkup(keyboard_buttons)

    await update.message.reply_text(
        "📊 **Выберите счет для сверки:**\n\n"
        "Сверка архивирует все текущие операции и создает точку контроля баланса.\n"
        "После сверки история операций начнется заново.",
        reply_markup=reply_markup
    )


async def perform_reconciliation(update, account, chat_id, username, all_accounts=False):
    """Выполнение сверки для счета с поддержкой username"""
    try:
        if all_accounts:
            # Сверка всех счетов
            user_id = update.effective_user.id
            accounts = get_user_accounts(user_id, chat_id)
            results = []

            for acc in accounts:
                result = reconcile_single_account(acc, chat_id, user_id, username)
                results.append(result)

            # Формируем итоговое сообщение
            success_count = sum(1 for r in results if r['success'])
            total_archived = sum(r['archived_count'] for r in results if r['success'])

            response = f"🔄 **Сверка всех счетов завершена**\n\n"
            response += f"✅ Успешно: {success_count}/{len(accounts)} счетов\n"
            response += f"📋 Архивировано: {total_archived} операций\n"
            response += f"👤 Выполнил: @{username}\n\n" if username else f"👤 Выполнил: {username}\n\n"

            for result in results:
                status = "✅" if result['success'] else "❌"
                response += f"{status} {result['account_name']}: {result['message']}\n"

            if update.callback_query:
                await update.callback_query.edit_message_text(response)
            else:
                await update.message.reply_text(response, reply_markup=get_main_keyboard())

        else:
            # Сверка одного счета
            result = reconcile_single_account(account, chat_id, update.effective_user.id, username)

            response = f"📊 **Сверка счета '{account['account_name']}'**\n\n"
            if result['success']:
                response += f"✅ {result['message']}\n"
                response += f"📋 Архивировано операций: {result['archived_count']}\n"
                response += f"💰 Баланс на момент сверки: {result['balance']:.2f}\n"
                response += f"👤 Выполнил: @{username}\n" if username else f"👤 Выполнил: {username}\n"

                # Форматируем дату
                date_str = result['date']
                if isinstance(date_str, str):
                    date_str = date_str[:16]
                else:
                    date_str = date_str.strftime('%d.%m.%Y %H:%M')

                response += f"📅 Дата сверки: {date_str}"
            else:
                response += f"❌ {result['message']}"

            if update.callback_query:
                await update.callback_query.edit_message_text(response)
            else:
                await update.message.reply_text(response, reply_markup=get_main_keyboard())

    except Exception as e:
        logger.error(f"Ошибка при выполнении сверки: {e}")
        error_msg = "❌ Произошла ошибка при выполнении сверки."
        if update.callback_query:
            await update.callback_query.edit_message_text(error_msg)
        else:
            await update.message.reply_text(error_msg, reply_markup=get_main_keyboard())


def reconcile_single_account(account, chat_id, user_id=None, username=None):
    """Сверка одного счета с сохранением username"""
    try:
        balance_before = get_account_balance(account['account_id'])

        if balance_before == 0 and not get_account_transactions(account['account_id']):
            return {
                'success': False,
                'account_name': account['account_name'],
                'message': "Нет операций для сверки",
                'archived_count': 0,
                'balance': balance_before,
                'date': datetime.now()
            }

        archived_count = archive_all_transactions(account['account_id'])

        # Создаем запись о сверке С USERNAME
        recon_date = datetime.now()
        create_reconciliation(
            account['account_id'],
            chat_id,
            balance_before,
            recon_date,
            user_id,
            username  # Передаем username
        )

        logger.info(f"Сверка счета {account['account_name']} пользователем {username}: архивировано {archived_count} операций, баланс {balance_before}")

        return {
            'success': True,
            'account_name': account['account_name'],
            'message': "Сверка выполнена успешно",
            'archived_count': archived_count,
            'balance': balance_before,
            'date': recon_date
        }
    except Exception as e:
        logger.error(f"Ошибка при сверке счета {account['account_id']}: {e}")
        return {
            'success': False,
            'account_name': account['account_name'],
            'message': f"Ошибка: {str(e)}",
            'archived_count': 0,
            'balance': 0,
            'date': datetime.now()
        }


async def handle_reconciliation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик callback'ов для сверки с поддержкой username"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    username = query.from_user.username or query.from_user.full_name
    chat_id = update.effective_chat.id
    data = query.data

    if data == "reconcile_all":
        # Сверка всех счетов
        await perform_reconciliation(update, None, chat_id, username, all_accounts=True)

    elif data.startswith("reconcile_"):
        # Сверка конкретного счета
        account_id = int(data.split("_")[1])
        accounts = get_user_accounts(user_id, chat_id)
        account = next((acc for acc in accounts if acc['account_id'] == account_id), None)

        if account:
            await perform_reconciliation(update, account, chat_id, username)
        else:
            await query.edit_message_text("❌ Счет не найден")


def get_reconciliation_handlers():
    """Возвращает обработчики для сверки"""
    return [
        CallbackQueryHandler(handle_reconciliation_callback, pattern="^reconcile_")
    ]