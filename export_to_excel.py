# export_to_excel.py - ОБНОВЛЕННАЯ ВЕРСИЯ С USERNAME
import os
import pandas as pd
from datetime import datetime, timedelta
from crud import get_user_accounts, get_account_transactions, get_account_balance, get_account, \
    get_account_reconciliations
from utils.logger import logger
import sqlite3
from core import get_db_connection


def ensure_exports_dir():
    """Создает папку для экспортируемых файлов если её нет"""
    exports_dir = "exports"
    if not os.path.exists(exports_dir):
        os.makedirs(exports_dir)
    return exports_dir


def get_account_transactions_with_details(account_id):
    """Получает все транзакции счета с дополнительной информацией, ВКЛЮЧАЯ username"""
    conn = get_db_connection()
    try:
        query = """
        SELECT 
            t.transaction_id,
            t.amount,
            t.date,
            t.comment,
            t.is_archived,
            t.is_reverted,
            t.created_at,
            t.username,  -- ДОБАВЛЕНО: username пользователя
            a.account_name,
            a.precision
        FROM transactions t
        LEFT JOIN accounts a ON t.account_id = a.account_id
        WHERE t.account_id = ?
        ORDER BY t.date
        """

        cursor = conn.execute(query, (account_id,))
        transactions = []

        for row in cursor.fetchall():
            transactions.append(dict(row))

        return transactions
    except Exception as e:
        logger.error(f"Ошибка при получении транзакций для экспорта: {e}")
        return []
    finally:
        conn.close()


def calculate_correct_running_balance(transactions, reconciliations, precision):
    """ПРАВИЛЬНО рассчитывает бегущий баланс с учетом статусов И username"""
    # Объединяем все события
    all_events = []

    # Добавляем транзакции
    for t in transactions:
        # Формируем комментарий с username если есть
        comment = t.get('comment', '') or ''
        username = t.get('username', '')
        if username:
            comment = f"{comment} (@{username})" if comment else f"@{username}"

        all_events.append({
            'type': 'transaction',
            'date': t['date'],
            'amount': float(t['amount']),
            'comment': comment,
            'is_archived': t.get('is_archived', 0),
            'is_reverted': t.get('is_reverted', 0),
            'transaction_id': t['transaction_id']
        })

    # Добавляем сверки
    for recon in reconciliations:
        # Формируем комментарий с username если есть
        comment = 'Сверка баланса'
        username = recon.get('username', '')
        if username:
            comment = f"{comment} (@{username})"

        all_events.append({
            'type': 'reconciliation',
            'date': recon['reconciliation_date'],
            'balance': float(recon['balance']),
            'comment': comment,
            'reconciliation_id': recon['reconciliation_id']
        })

    # Если нет событий, возвращаем пустой список
    if not all_events:
        return []

    # Сортируем по дате
    all_events.sort(key=lambda x: x['date'])

    # Находим даты сверок для определения статусов
    recon_dates = [recon['reconciliation_date'] for recon in reconciliations]
    recon_dates.sort()

    # Рассчитываем бегущий баланс
    current_balance = 0.0
    result = []

    for event in all_events:
        if event['type'] == 'transaction':
            # Определяем статус операции
            if event.get('is_reverted', 0):
                status = "Отменено"
            else:
                # Проверяем, есть ли сверки после этой операции
                has_later_recon = any(
                    recon_date > event['date'] for recon_date in recon_dates
                )
                if event.get('is_archived', 0) or has_later_recon:
                    status = "Архивировано"
                else:
                    status = "Активно"

                # Только НЕ отмененные операции влияют на баланс
                if not event.get('is_reverted', 0):
                    current_balance += event['amount']

            # Форматируем сумму с учетом точности счета
            amount_format = f"{{:+.{precision}f}}"
            amount_display = amount_format.format(event['amount'])

            result.append({
                'Дата': event['date'][:19],
                'Сумма': amount_display,
                'Баланс': f"{current_balance:.{precision}f}",
                'Комментарий': event['comment'],
                'Статус': status
            })

        else:  # reconciliation
            # При сверке баланс устанавливается в зафиксированное значение
            current_balance = event['balance']
            result.append({
                'Дата': event['date'][:19],
                'Сумма': f"{0:.{precision}f}",
                'Баланс': f"{current_balance:.{precision}f}",
                'Комментарий': event['comment'],
                'Статус': "Сверка"
            })

    return result


def create_account_sheet(writer, account, transactions, reconciliations):
    """Создает лист для одного счета с учетом точности И username"""
    try:
        # Получаем точность счета
        precision = account.get('precision', 2)

        # Рассчитываем данные с правильным бегущим балансом
        sheet_data = calculate_correct_running_balance(transactions, reconciliations, precision)

        if not sheet_data:
            # Если нет данных, создаем информационный лист
            empty_df = pd.DataFrame([{
                'Дата': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'Сумма': '0.00',
                'Баланс': '0.00',
                'Комментарий': 'Нет операций для отображения',
                'Статус': 'Нет данных'
            }])
            sheet_name = account['account_name'][:31]
            empty_df.to_excel(writer, sheet_name=sheet_name, index=False)

            # Форматируем лист
            worksheet = writer.sheets[sheet_name]
            column_widths = {
                'A': 20, 'B': 15, 'C': 15, 'D': 40, 'E': 15  # Увеличили ширину для комментария с username
            }
            for col, width in column_widths.items():
                worksheet.column_dimensions[col].width = width
            return

        df = pd.DataFrame(sheet_data)

        # Записываем данные в лист
        df.to_excel(writer, sheet_name=account['account_name'][:31], index=False)

        # Форматируем лист
        worksheet = writer.sheets[account['account_name'][:31]]

        # Автоподбор ширины колонок
        column_widths = {
            'A': 20,  # Дата
            'B': 15,  # Сумма
            'C': 15,  # Баланс
            'D': 40,  # Комментарий (увеличили для username)
            'E': 15  # Статус
        }

        for col, width in column_widths.items():
            worksheet.column_dimensions[col].width = width

    except Exception as e:
        logger.error(f"Ошибка при создании листа для счета {account['account_name']}: {e}")
        # Создаем минимальный лист с ошибкой
        error_df = pd.DataFrame([{
            'Дата': 'Ошибка',
            'Сумма': 'Ошибка',
            'Баланс': 'Ошибка',
            'Комментарий': f'Не удалось создать выписку: {str(e)}',
            'Статус': 'Ошибка'
        }])
        error_df.to_excel(writer, sheet_name='Ошибка', index=False)


def create_excel_export(accounts_data, export_type, chat_id):
    """Создает Excel файл с отдельными листами для каждого счета"""
    try:
        if not accounts_data:
            return False, None, "Нет данных для экспорта"

        # Создаем файл
        exports_dir = ensure_exports_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"выписка_{export_type}_{chat_id}_{timestamp}.xlsx"
        filepath = os.path.join(exports_dir, filename)

        # Создаем Excel writer
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            for account_data in accounts_data:
                account = account_data['account']
                transactions = account_data['transactions']
                reconciliations = account_data['reconciliations']

                create_account_sheet(writer, account, transactions, reconciliations)

        logger.info(f"Создан файл экспорта: {filepath}")
        return True, filepath, f"📊 Выписка ({export_type}) успешно сгенерирована"

    except Exception as e:
        logger.error(f"Ошибка при создании Excel файла: {e}")
        return False, None, f"❌ Ошибка при создании файла: {str(e)}"


def get_accounts_export_data(chat_id, user_id, include_archived=True):
    """Собирает данные для экспорта по всем счетам"""
    try:
        accounts = get_user_accounts(user_id, chat_id)
        accounts_data = []

        for account in accounts:
            # Получаем транзакции счета
            transactions = get_account_transactions_with_details(account['account_id'])

            # Если не включаем архивные, фильтруем их
            if not include_archived:
                transactions = [t for t in transactions if not t.get('is_archived', 0)]

            # Получаем сверки счета
            reconciliations = get_account_reconciliations(account['account_id'])

            accounts_data.append({
                'account': account,
                'transactions': transactions,
                'reconciliations': reconciliations
            })

        return accounts_data

    except Exception as e:
        logger.error(f"Ошибка при сборе данных для экспорта: {e}")
        return []


def handle_export_command(chat_id, user_id, export_type="full"):
    """Основная функция обработки экспорта"""
    try:
        logger.info(f"Экспорт для chat_id: {chat_id}, user_id: {user_id}, тип: {export_type}")

        # Определяем, включать ли архивные операции
        include_archived = (export_type == "full")

        # Собираем данные по всем счетам
        accounts_data = get_accounts_export_data(chat_id, user_id, include_archived)

        if not accounts_data:
            return False, None, "❌ Нет данных для экспорта"

        # Создаем Excel файл
        return create_excel_export(accounts_data, export_type, chat_id)

    except Exception as e:
        logger.error(f"Ошибка в handle_export_command: {e}")
        return False, None, f"❌ Ошибка экспорта: {str(e)}"


def cleanup_old_exports(hours=24):
    """Очищает старые файлы экспорта"""
    try:
        exports_dir = ensure_exports_dir()
        now = datetime.now()
        deleted_count = 0

        for filename in os.listdir(exports_dir):
            if filename.endswith('.xlsx'):
                filepath = os.path.join(exports_dir, filename)
                file_time = datetime.fromtimestamp(os.path.getctime(filepath))

                if now - file_time > timedelta(hours=hours):
                    os.remove(filepath)
                    deleted_count += 1
                    logger.info(f"Удален старый файл экспорта: {filename}")

        if deleted_count > 0:
            logger.info(f"Очищено файлов экспорта: {deleted_count}")

    except Exception as e:
        logger.error(f"Ошибка при очистке старых файлов экспорта: {e}")


# Тестирование
if __name__ == "__main__":
    # Тест создания папки
    ensure_exports_dir()
    print("✅ Модуль экспорта готов к работе")