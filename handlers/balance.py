# balance.py - ОБНОВЛЕННАЯ ВЕРСИЯ
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from utils.logger import logger
from crud import get_user_accounts, get_account_transactions, get_account_balance, ensure_chat_exists, get_account
import os


def get_main_keyboard():
    """Создает основную клавиатуру с кнопками"""
    keyboard = [
        [KeyboardButton("/help"), KeyboardButton("/счета")],
        [KeyboardButton("/сверь"), KeyboardButton("/дай")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def show_balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /дай с улучшенной обработкой ошибок"""
    user = update.effective_user
    user_id = user.id
    chat_id = update.effective_chat.id

    try:
        logger.info(f"Пользователь {user_id} запросил баланс")

        # Получаем весь текст после команды
        if update.message.text:
            command_parts = update.message.text.split()
            if len(command_parts) > 1:
                specific_account_name = ' '.join(command_parts[1:]).strip().lower()
            else:
                specific_account_name = None
        else:
            specific_account_name = None

        # Получаем счета пользователя В ЭТОМ ЧАТЕ
        accounts = get_user_accounts(user_id, chat_id)
        logger.info(f"Найдено счетов: {len(accounts)}")

        if not accounts:
            await update.message.reply_text(
                "💼 У вас пока нет счетов.\n\n"
                "Создайте первый счет командой `/добавь руб`",
                reply_markup=get_main_keyboard()
            )
            return

        if specific_account_name:
            # Показываем баланс и историю по конкретному счету
            target_account = None
            for account in accounts:
                # УЛУЧШЕННЫЙ ПОИСК - нормализуем строки
                account_name_normalized = account['account_name'].lower().strip().replace(' ', '')
                specific_name_normalized = specific_account_name.lower().strip().replace(' ', '')

                if account_name_normalized == specific_name_normalized:
                    target_account = account
                    break

            if not target_account:
                await update.message.reply_text(
                    f"❌ Счет '{specific_account_name}' не найден.",
                    reply_markup=get_main_keyboard()
                )
                return

            # Используем единую функцию расчета баланса
            balance = get_account_balance(target_account['account_id'])
            transactions = get_account_transactions(target_account['account_id'])

            # Форматируем с учетом разрядности
            precision = target_account.get('precision', 2)
            response = f"💳 Счет: {target_account['account_name']}\n"
            response += f"💰 Баланс: {balance:.{precision}f}\n\n"

            if transactions:
                response += "📋 Последние операции:\n"
                for t in transactions[-5:]:  # Последние 5 операций
                    try:
                        if t.get('amount') is not None:
                            amount = float(t['amount'])
                            amount_str = f"+{amount:.{precision}f}" if amount >= 0 else f"{amount:.{precision}f}"
                            date_str = t['date'][:16] if 'date' in t and t['date'] else "неизвестно"
                            comment = t.get('comment', '') or ''
                            status = " ❌" if t.get('is_reverted') else ""
                            response += f"• {date_str} {amount_str} {comment}{status}\n"
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Ошибка форматирования транзакции: {e}")
                        continue

            # Создаем клавиатуру с кнопками выписки
            keyboard_buttons = []

            # Кнопки выписки в Excel
            keyboard_buttons.append([
                InlineKeyboardButton("📊 Выписка (все операции)",
                                     callback_data=f"export_all_{target_account['account_id']}"),
                InlineKeyboardButton("📈 Текущий период",
                                     callback_data=f"export_current_{target_account['account_id']}")
            ])

            # Кнопки отката (если есть активные операции)
            if transactions:
                for t in transactions[-3:]:  # Кнопки отката для последних 3 операций
                    try:
                        if (t.get('amount') is not None and
                            not t.get('is_reverted', 0) and
                            not t.get('is_archived', 0)):
                            amount = float(t['amount'])
                            amount_str = f"+{amount:.{precision}f}" if amount >= 0 else f"{amount:.{precision}f}"
                            keyboard_buttons.append([
                                InlineKeyboardButton(f"❌ Откатить {amount_str}",
                                                     callback_data=f"cancel_{t['transaction_id']}")
                            ])
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Ошибка создания кнопки отката: {e}")
                        continue

            reply_markup = InlineKeyboardMarkup(keyboard_buttons) if keyboard_buttons else None

            await update.message.reply_text(response, reply_markup=reply_markup)

        else:
            # Показываем балансы по всем счетам
            response = "💼 Ваши средства:\n\n"
            total_balance = 0.0

            for account in accounts:
                # Используем единую функцию расчета баланса
                balance = get_account_balance(account['account_id'])
                total_balance += balance

                # Форматируем баланс с учетом разрядности
                precision = account.get('precision', 2)
                balance_str = f"{balance:.{precision}f}"
                response += f"💰 {account['account_name']}: {balance_str}\n"

            # Форматируем общий баланс с максимальной разрядностью
            max_precision = max(acc.get('precision', 2) for acc in accounts)
            response += f"\n💵 Итого: {total_balance:.{max_precision}f}"

            # ДВЕ КНОПКИ выписки по всем счетам
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("📊 Все операции", callback_data="export_all_accounts"),
                    InlineKeyboardButton("📈 Текущий период", callback_data="export_current_accounts")
                ]
            ])

            await update.message.reply_text(response, reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Критическая ошибка при получении баланса для пользователя {user_id}: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ Произошла ошибка при получении баланса. Попробуйте позже.",
            reply_markup=get_main_keyboard()
        )