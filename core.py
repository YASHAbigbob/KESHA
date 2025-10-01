# core.py - ПОЛНОСТЬЮ ОБНОВЛЕННАЯ ВЕРСИЯ С USERNAME
import sqlite3
from datetime import datetime

def get_db_connection():
    """Установить соединение с базой данных"""
    conn = sqlite3.connect('accountant_bot.db')
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():
    """Создать все необходимые таблицы в базе данных с поддержкой username"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")

    try:
        # Таблица пользователей
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # Таблица чатов
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS chats (
            chat_id INTEGER PRIMARY KEY,
            chat_type TEXT NOT NULL,
            title TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # Таблица счетов - С USERNAME
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            account_id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            account_name TEXT NOT NULL,
            created_by INTEGER,
            username TEXT,  -- Telegram username
            precision INTEGER DEFAULT 2,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (chat_id) REFERENCES chats(chat_id) ON DELETE CASCADE,
            FOREIGN KEY (created_by) REFERENCES users(user_id) ON DELETE SET NULL
        )
        ''')

        # Таблица транзакций - С USERNAME
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL,
            chat_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            date DATETIME NOT NULL,
            comment TEXT,
            created_by INTEGER,
            username TEXT,  -- Telegram username
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_archived BOOLEAN DEFAULT 0,
            is_reverted BOOLEAN DEFAULT 0,
            revert_comment TEXT,
            reverted_by INTEGER,
            reverted_at DATETIME,
            FOREIGN KEY (account_id) REFERENCES accounts(account_id) ON DELETE CASCADE,
            FOREIGN KEY (created_by) REFERENCES users(user_id) ON DELETE SET NULL,
            FOREIGN KEY (reverted_by) REFERENCES users(user_id) ON DELETE SET NULL
        )
        ''')

        # Таблица сверок - С USERNAME
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS reconciliations (
            reconciliation_id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL,
            chat_id INTEGER NOT NULL,
            balance REAL NOT NULL,
            reconciliation_date DATETIME NOT NULL,
            created_by INTEGER,
            username TEXT,  -- Telegram username
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (account_id) REFERENCES accounts(account_id) ON DELETE CASCADE,
            FOREIGN KEY (created_by) REFERENCES users(user_id) ON DELETE SET NULL
        )
        ''')

        # Таблица участников чатов
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_members (
            chat_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (chat_id, user_id),
            FOREIGN KEY (chat_id) REFERENCES chats(chat_id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
        ''')

        # ДОБАВЛЯЕМ КОЛОНКИ ДЛЯ ОБРАТНОЙ СОВМЕСТИМОСТИ
        tables_to_update = ['accounts', 'transactions', 'reconciliations']
        for table in tables_to_update:
            try:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN username TEXT")
                print(f"✅ Добавлена колонка username в таблицу {table}")
            except sqlite3.OperationalError:
                print(f"ℹ️ Колонка username уже существует в таблице {table}")

        # Создание индексов
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_chats_type ON chats(chat_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_accounts_chat ON accounts(chat_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_accounts_created_by ON accounts(created_by)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_account ON transactions(account_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_archived ON transactions(is_archived)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_reverted ON transactions(is_reverted)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_created_by ON transactions(created_by)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_reconciliations_account ON reconciliations(account_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_reconciliations_date ON reconciliations(reconciliation_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_chat_members_chat ON chat_members(chat_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_chat_members_user ON chat_members(user_id)')

        conn.commit()
        print("✅ Таблицы базы данных успешно созданы/обновлены с поддержкой username!")

    except Exception as e:
        print(f"❌ Ошибка при создании таблиц: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()