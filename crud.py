# crud.py - ОБНОВЛЕННАЯ ВЕРСИЯ С USERNAME
import sqlite3
from datetime import datetime
from core import get_db_connection

# ===== USERS & CHATS =====
def create_user(user_id: int, username: str = None) -> None:
    conn = get_db_connection()
    try:
        conn.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
        conn.commit()
    finally:
        conn.close()

def get_user(user_id: int) -> dict | None:
    conn = get_db_connection()
    try:
        cursor = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def create_chat(chat_id: int, chat_type: str, title: str = None) -> None:
    conn = get_db_connection()
    try:
        conn.execute("INSERT OR REPLACE INTO chats (chat_id, chat_type, title) VALUES (?, ?, ?)", (chat_id, chat_type, title))
        conn.commit()
    finally:
        conn.close()

def get_chat(chat_id: int) -> dict | None:
    conn = get_db_connection()
    try:
        cursor = conn.execute("SELECT * FROM chats WHERE chat_id = ?", (chat_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def add_chat_member(chat_id: int, user_id: int) -> None:
    conn = get_db_connection()
    try:
        conn.execute("INSERT OR IGNORE INTO chat_members (chat_id, user_id) VALUES (?, ?)", (chat_id, user_id))
        conn.commit()
    finally:
        conn.close()

# ===== ACCOUNTS ===== С USERNAME
def create_account(chat_id: int, account_name: str, created_by: int = None, username: str = None, precision: int = 2) -> int:
    """Создание счета с указанной точностью и username"""
    if precision < 0 or precision > 8:
        raise ValueError("Точность должна быть от 0 до 8")

    conn = get_db_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO accounts (chat_id, account_name, created_by, username, precision) VALUES (?, ?, ?, ?, ?)",
            (chat_id, account_name, created_by, username, precision)
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()

def get_account(account_id: int) -> dict | None:
    conn = get_db_connection()
    try:
        cursor = conn.execute("SELECT * FROM accounts WHERE account_id = ?", (account_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def get_chat_accounts(chat_id: int) -> list[dict]:
    conn = get_db_connection()
    try:
        cursor = conn.execute("SELECT * FROM accounts WHERE chat_id = ? ORDER BY account_name", (chat_id,))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

def get_account_precision(account_id: int) -> int:
    conn = get_db_connection()
    try:
        cursor = conn.execute("SELECT precision FROM accounts WHERE account_id = ?", (account_id,))
        row = cursor.fetchone()
        return row['precision'] if row else 2
    finally:
        conn.close()

def delete_account(account_id: int) -> None:
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM accounts WHERE account_id = ?", (account_id,))
        conn.commit()
    finally:
        conn.close()

# ===== TRANSACTIONS ===== С USERNAME
def create_transaction(account_id: int, chat_id: int, amount: float, date: datetime,
                       comment: str = None, created_by: int = None, username: str = None) -> int:
    """Создание транзакции с округлением до точности счета и сохранением username"""
    # Получаем точность счета
    precision = get_account_precision(account_id)

    # Округляем сумму до нужной точности
    rounded_amount = round(amount, precision)

    conn = get_db_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO transactions (account_id, chat_id, amount, date, comment, created_by, username) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (account_id, chat_id, rounded_amount, date, comment, created_by, username)
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()

def get_transaction(transaction_id: int) -> dict | None:
    conn = get_db_connection()
    try:
        cursor = conn.execute("SELECT * FROM transactions WHERE transaction_id = ?", (transaction_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def get_account_transactions(account_id: int, include_archived: bool = False,
                             include_reverted: bool = False) -> list[dict]:
    conn = get_db_connection()
    try:
        query = "SELECT * FROM transactions WHERE account_id = ?"
        params = [account_id]

        if not include_archived:
            query += " AND is_archived = 0"
        if not include_reverted:
            query += " AND is_reverted = 0"

        query += " ORDER BY date"

        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

def archive_transaction(transaction_id: int) -> None:
    conn = get_db_connection()
    try:
        conn.execute("UPDATE transactions SET is_archived = 1 WHERE transaction_id = ?", (transaction_id,))
        conn.commit()
    finally:
        conn.close()

def archive_all_transactions(account_id: int) -> int:
    """Архивация всех транзакций по счету и возврат количества архивированных"""
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            """UPDATE transactions 
            SET is_archived = 1 
            WHERE account_id = ? AND is_archived = 0""",
            (account_id,)
        )
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()

# ===== RECONCILIATIONS ===== С USERNAME
def create_reconciliation(account_id: int, chat_id: int, balance: float,
                          reconciliation_date: datetime, created_by: int = None, username: str = None) -> int:
    """Создание сверки с округлением до точности счета и сохранением username"""
    # Получаем точность счета
    precision = get_account_precision(account_id)

    # Округляем баланс до нужной точности
    rounded_balance = round(balance, precision)

    conn = get_db_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO reconciliations (account_id, chat_id, balance, reconciliation_date, created_by, username) VALUES (?, ?, ?, ?, ?, ?)",
            (account_id, chat_id, rounded_balance, reconciliation_date, created_by, username)
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()

def get_account_reconciliations(account_id: int) -> list[dict]:
    conn = get_db_connection()
    try:
        cursor = conn.execute("SELECT * FROM reconciliations WHERE account_id = ? ORDER BY reconciliation_date", (account_id,))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

def get_last_reconciliation(account_id: int) -> dict | None:
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            """SELECT * FROM reconciliations 
            WHERE account_id = ? 
            ORDER BY reconciliation_id DESC 
            LIMIT 1""",
            (account_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

# ===== BALANCE =====
def get_account_balance(account_id: int) -> float:
    """ИСПРАВЛЕННАЯ функция расчета баланса с учетом сверок и отмененных операций"""
    conn = get_db_connection()
    try:
        # Находим последнюю сверку
        cursor = conn.execute(
            "SELECT balance FROM reconciliations WHERE account_id = ? ORDER BY reconciliation_date DESC LIMIT 1",
            (account_id,)
        )
        last_recon = cursor.fetchone()

        # Суммируем операции после последней сверки (исключая отмененные)
        if last_recon:
            last_recon_date = conn.execute(
                "SELECT reconciliation_date FROM reconciliations WHERE account_id = ? ORDER BY reconciliation_date DESC LIMIT 1",
                (account_id,)
            ).fetchone()

            if last_recon_date:
                cursor = conn.execute(
                    """SELECT COALESCE(SUM(amount), 0) 
                    FROM transactions 
                    WHERE account_id = ? AND is_archived = 0 AND is_reverted = 0 AND date > ?""",
                    (account_id, last_recon_date['reconciliation_date'])
                )
            else:
                cursor = conn.execute(
                    "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE account_id = ? AND is_archived = 0 AND is_reverted = 0",
                    (account_id,)
                )
        else:
            cursor = conn.execute(
                "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE account_id = ? AND is_archived = 0 AND is_reverted = 0",
                (account_id,)
            )

        post_recon_sum = cursor.fetchone()[0]

        if last_recon:
            return float(last_recon['balance']) + float(post_recon_sum)
        else:
            return float(post_recon_sum)

    except Exception as e:
        print(f"Ошибка при расчете баланса для счета {account_id}: {e}")
        return 0.0
    finally:
        conn.close()

# ===== УТИЛИТЫ =====
def ensure_chat_exists(chat_id: int, chat_type: str, title: str = None) -> None:
    chat = get_chat(chat_id)
    if not chat:
        create_chat(chat_id, chat_type, title)

def get_user_accounts(user_id: int, chat_id: int) -> list[dict]:
    """
    Получить счета пользователя в указанном чате.
    В личных чатах — только счета пользователя.
    В группах — все счета чата (для совместимости с текущей логикой бота).
    """
    chat = get_chat(chat_id)
    if not chat:
        return []

    accounts = get_chat_accounts(chat_id)

    # В личных чатах показываем только счета пользователя
    if chat['chat_type'] == 'private':
        return [acc for acc in accounts if acc.get('created_by') == user_id]
    else:
        # В группах — все счета (как в оригинальной логике)
        return accounts

def get_account_current_balance(account_id: int) -> float:
    """Получить текущий баланс счета"""
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) as balance FROM transactions WHERE account_id = ? AND is_archived = 0",
            (account_id,)
        )
        result = cursor.fetchone()
        return result['balance'] if result else 0.0
    finally:
        conn.close()

def get_chat_financial_summary(chat_id: int) -> dict:
    """Получить финансовую сводку по чату"""
    conn = get_db_connection()
    try:
        # Общий баланс
        cursor = conn.execute(
            """SELECT COALESCE(SUM(t.amount), 0) as total_balance
            FROM transactions t
            JOIN accounts a ON t.account_id = a.account_id
            WHERE a.chat_id = ? AND t.is_archived = 0""",
            (chat_id,)
        )
        total_balance = cursor.fetchone()['total_balance']

        # Количество счетов
        cursor.execute(
            "SELECT COUNT(*) as account_count FROM accounts WHERE chat_id = ?",
            (chat_id,)
        )
        account_count = cursor.fetchone()['account_count']

        # Количество транзакций
        cursor.execute(
            """SELECT COUNT(*) as transaction_count
            FROM transactions t
            JOIN accounts a ON t.account_id = a.account_id
            WHERE a.chat_id = ? AND t.is_archived = 0""",
            (chat_id,)
        )
        transaction_count = cursor.fetchone()['transaction_count']

        # Доходы и расходы
        cursor.execute(
            """SELECT 
                COALESCE(SUM(CASE WHEN t.amount > 0 THEN t.amount ELSE 0 END), 0) as total_income,
                COALESCE(SUM(CASE WHEN t.amount < 0 THEN t.amount ELSE 0 END), 0) as total_expenses
            FROM transactions t
            JOIN accounts a ON t.account_id = a.account_id
            WHERE a.chat_id = ? AND t.is_archived = 0""",
            (chat_id,)
        )
        income_expenses = cursor.fetchone()

        return {
            'total_balance': total_balance,
            'account_count': account_count,
            'transaction_count': transaction_count,
            'total_income': income_expenses['total_income'],
            'total_expenses': income_expenses['total_expenses'],
            'net_flow': income_expenses['total_income'] + income_expenses['total_expenses']
        }
    finally:
        conn.close()

def revert_transaction(transaction_id: int, reverted_by: int = None,
                      revert_comment: str = None) -> None:
    """Отменить операцию (откат)"""
    conn = get_db_connection()
    try:
        conn.execute(
            """UPDATE transactions 
            SET is_reverted = 1, 
                revert_comment = ?,
                reverted_by = ?,
                reverted_at = CURRENT_TIMESTAMP
            WHERE transaction_id = ?""",
            (revert_comment, reverted_by, transaction_id)
        )
        conn.commit()
    finally:
        conn.close()