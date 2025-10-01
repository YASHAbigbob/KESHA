# callbacks.py - ОБНОВЛЕННАЯ ВЕРСИЯ
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram.error import TimedOut, NetworkError
from utils.logger import logger
from crud import revert_transaction, get_transaction, get_account, get_account_transactions, get_account_balance
from export_to_excel import handle_export_command, cleanup_old_exports
import asyncio
import os


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на inline-кнопки"""
    query = update.callback_query
    try:
        await query.answer()
    except (TimedOut, NetworkError) as e:
        logger.warning(f"Таймаут при answer callback: {e}")
    except Exception as e:
        logger.error(f"Ошибка при answer callback: {e}")

    user_id = query.from_user.id
    data = query.data
    chat_id = query.message.chat_id

    logger.info(f"Пользователь {user_id} нажал кнопку: {data}")

    if data.startswith("cancel_"):
        transaction_id = int(data.split("_")[1])
        await handle_transaction_cancel(query, transaction_id, user_id)
    elif data.startswith("export_"):
        await handle_export_callback(query, data, user_id, chat_id, context)
    elif data.startswith("reconcile_"):
        await handle_reconciliation_callback(update, context)
    else:
        try:
            await query.edit_message_text("[ОШИБКА] Неизвестная команда")
        except Exception as e:
            logger.error(f"Ошибка при редактировании сообщения: {e}")


async def handle_export_callback(query, data: str, user_id: int, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Обработка кнопок экспорта в Excel"""
    try:
        await query.edit_message_text("📊 Генерирую выписку в Excel...")

        # Определяем тип экспорта
        if data == "export_all_accounts":
            export_type = "full"
        elif data == "export_current_accounts":
            export_type = "current"
        elif data.startswith("export_all_"):
            export_type = "full"
        elif data.startswith("export_current_"):
            export_type = "current"
        else:
            await query.edit_message_text("❌ Неизвестный тип экспорта")
            return

        # Вызываем функцию экспорта
        success, file_path, message = handle_export_command(chat_id, user_id, export_type)

        if success and file_path and os.path.exists(file_path):
            # Отправляем файл пользователю
            with open(file_path, 'rb') as file:
                await context.bot.send_document(
                    chat_id=chat_id,
                    document=file,
                    caption=message,
                    filename=os.path.basename(file_path)
                )
            # Удаляем временный файл
            try:
                os.remove(file_path)
            except Exception as e:
                logger.warning(f"Не удалось удалить временный файл {file_path}: {e}")

            await query.delete_message()
        else:
            await query.edit_message_text(f"❌ {message}")

    except Exception as e:
        logger.error(f"Ошибка при экспорте в Excel: {e}")
        try:
            await query.edit_message_text("❌ Произошла ошибка при генерации выписки.")
        except:
            pass


async def handle_transaction_cancel(query, transaction_id: int, user_id: int):
    """Обработка отката транзакции с ПРАВИЛЬНОЙ проверкой прав"""
    try:
        # Получаем транзакцию
        transaction = get_transaction(transaction_id)
        if not transaction:
            await safe_edit_message(query, "❌ Транзакция не найдена")
            return

        # Проверяем права
        if transaction.get('created_by') is not None and transaction['created_by'] != user_id:
            await safe_edit_message(query, "❌ Недостаточно прав для отката этой операции")
            return

        # Проверяем, не отменена ли уже транзакция
        if transaction.get('is_reverted'):
            await safe_edit_message(query, "❌ Эта операция уже откачена")
            return

        # Отменяем транзакцию (откат)
        revert_transaction(transaction_id, user_id, "Откат пользователем")

        # Получаем счёт для отображения баланса
        account = get_account(transaction['account_id'])
        if not account:
            await safe_edit_message(query, "❌ Счет не найден")
            return

        # Используем единую функцию расчёта баланса
        balance = get_account_balance(account['account_id'])
        precision = account.get('precision', 2)
        balance_str = f"{balance:.{precision}f}"

        # Формируем сообщение
        original_text = query.message.text
        lines = original_text.split('\n')
        if lines and lines[0].startswith("❌ ОТКАТАНО"):
            lines = lines[1:]
            original_text = '\n'.join(lines).strip()

        new_text = f"❌ ОТКАТАНО\n{original_text}\n💳 Новый баланс: {balance_str} {account['account_name']}"

        await safe_edit_message(query, new_text, reply_markup=None)
        logger.info(f"Пользователь {user_id} откатил транзакцию {transaction_id}")

    except Exception as e:
        logger.error(f"Ошибка при откате транзакции {transaction_id} пользователем {user_id}: {e}")
        await safe_edit_message(query, "❌ Произошла ошибка при откате операции.")


async def handle_reconciliation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик callback'ов для сверки"""
    from handlers.reconciliation import handle_reconciliation_callback as reconcile_handler
    try:
        await reconcile_handler(update, context)
    except Exception as e:
        logger.error(f"Ошибка при обработке callback сверки: {e}")
        try:
            await update.callback_query.edit_message_text("❌ Ошибка при выполнении сверки")
        except:
            pass


async def safe_edit_message(query, text, reply_markup=None):
    """Безопасное редактирование сообщения с обработкой ошибок"""
    try:
        await query.edit_message_text(text, reply_markup=reply_markup)
    except (TimedOut, NetworkError) as e:
        logger.warning(f"Таймаут при редактировании сообщения: {e}")
        try:
            await query.message.reply_text(text)
        except Exception as e2:
            logger.error(f"Не удалось отправить новое сообщение: {e2}")
    except Exception as e:
        logger.error(f"Ошибка при редактировании сообщения: {e}")
        try:
            await query.message.reply_text(text)
        except Exception as e2:
            logger.error(f"Не удалось отправить новое сообщение: {e2}")


def get_callback_handler():
    """Возвращает обработчик callback'ов"""
    return CallbackQueryHandler(handle_callback)