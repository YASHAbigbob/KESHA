# accounts.py - ОБНОВЛЕННАЯ ВЕРСИЯ С USERNAME
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from utils.logger import logger
from crud import create_account, get_user_accounts, delete_account, create_user, ensure_chat_exists

def get_main_keyboard():
    """Создает основную клавиатуру с кнопками"""
    keyboard = [
        [KeyboardButton("/help"), KeyboardButton("/счета")],
        [KeyboardButton("/сверь"), KeyboardButton("/дай")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


async def add_account_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /добавь с поддержкой username"""
    user = update.effective_user
    user_id = user.id
    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type
    username = user.username or user.full_name  # Получаем username

    # Убедимся, что чат существует
    ensure_chat_exists(chat_id, chat_type, update.effective_chat.title)

    # Получаем весь текст после команды
    if update.message.text:
        command_parts = update.message.text.split()
        if len(command_parts) > 1:
            account_name = command_parts[1].strip()
            precision = 2  # значение по умолчанию

            if len(command_parts) > 2:
                try:
                    prec_value = int(command_parts[2])
                    if 2 <= prec_value <= 8:
                        precision = prec_value
                    else:
                        await update.message.reply_text(
                            "❌ Разрядность должна быть от 2 до 8. Использую значение по умолчанию: 2",
                            reply_markup=get_main_keyboard()
                        )
                except ValueError:
                    pass
        else:
            account_name = None
    else:
        account_name = None

    logger.info(f"Пользователь {user_id} ({username}) в чате {chat_id} создает счет: '{account_name}'")

    if not account_name:
        await update.message.reply_text(
            "❌ Укажите название счета. Например:\n"
            "• `/добавь руб` - счет с разрядностью 2\n"
            "• `/добавь карта 4` - счет с разрядностью 4",
            reply_markup=get_main_keyboard()
        )
        return

    if len(account_name) > 100:
        await update.message.reply_text(
            "❌ Название счета слишком длинное (максимум 100 символов).",
            reply_markup=get_main_keyboard()
        )
        return

    try:
        # Получаем существующие счета в чате
        existing_accounts = get_user_accounts(user_id, chat_id)

        for account in existing_accounts:
            if account['account_name'].lower() == account_name.lower():
                await update.message.reply_text(
                    f"❌ Счет с названием '{account_name}' уже существует в этом чате.",
                    reply_markup=get_main_keyboard()
                )
                return

        # Создаем пользователя если его нет
        create_user(user_id, username)

        # Создаем счет с указанной разрядностью И USERNAME
        account_id = create_account(chat_id, account_name, user_id, username, precision)

        logger.info(f"Создан счет '{account_name}' (ID: {account_id}) пользователем {username} в чате {chat_id}")

        precision_info = f" с разрядностью {precision}" if precision != 2 else ""
        chat_info = " в группе" if chat_type != "private" else ""

        await update.message.reply_text(
            f"✅ Счёт '{account_name}' добавлен{precision_info}{chat_info}.",
            reply_markup=get_main_keyboard()
        )

    except Exception as e:
        logger.error(f"Ошибка при создании счета: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при создании счета. Попробуйте еще раз.",
            reply_markup=get_main_keyboard()
        )


async def delete_account_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /удали"""
    user = update.effective_user
    user_id = user.id
    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type
    username = user.username or user.full_name

    # Убедимся, что чат существует
    ensure_chat_exists(chat_id, chat_type, update.effective_chat.title)

    if update.message.text:
        command_parts = update.message.text.split()
        if len(command_parts) > 1:
            account_name = ' '.join(command_parts[1:]).strip()
        else:
            account_name = None
    else:
        account_name = None

    logger.info(f"Пользователь {user_id} ({username}) удаляет счет '{account_name}' в чате {chat_id}")

    if not account_name:
        await update.message.reply_text(
            "❌ Укажите название счета для удаления.",
            reply_markup=get_main_keyboard()
        )
        return

    try:
        # Получаем счета пользователя в чате
        existing_accounts = get_user_accounts(user_id, chat_id)

        account_to_delete = None
        for account in existing_accounts:
            if account['account_name'].lower() == account_name.lower():
                # В группах проверяем, что удалять может только создатель
                if chat_type != "private" and account.get('created_by') != user_id:
                    await update.message.reply_text(
                        f"❌ Вы можете удалять только созданные вами счета.",
                        reply_markup=get_main_keyboard()
                    )
                    return
                account_to_delete = account
                break

        if not account_to_delete:
            await update.message.reply_text(
                f"❌ Счет с названием '{account_name}' не найден.",
                reply_markup=get_main_keyboard()
            )
            return

        delete_account(account_to_delete['account_id'])
        logger.info(f"Удален счет '{account_name}' (ID: {account_to_delete['account_id']}) пользователем {username}")

        await update.message.reply_text(
            f"✅ Счёт '{account_name}' удален.",
            reply_markup=get_main_keyboard()
        )

    except Exception as e:
        logger.error(f"Ошибка при удалении счета: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при удалении счета.",
            reply_markup=get_main_keyboard()
        )


async def list_accounts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /счета с отображением username создателей"""
    user = update.effective_user
    user_id = user.id
    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type

    # Убедимся, что чат существует
    ensure_chat_exists(chat_id, chat_type, update.effective_chat.title)

    logger.info(f"Пользователь {user_id} запросил счета в чате {chat_id}")

    try:
        # Умное получение счетов
        accounts = get_user_accounts(user_id, chat_id)

        if not accounts:
            await update.message.reply_text(
                "💼 В этом чате пока нет счетов.\n\n"
                "Создайте первый счет командой:\n"
                "• `/добавь руб` - для рублей\n"
                "• `/добавь карта` - для банковской карты",
                reply_markup=get_main_keyboard()
            )
            return

        accounts_list = []
        for i, account in enumerate(accounts, 1):
            precision_info = f" (разрядность: {account['precision']})" if account.get('precision', 2) != 2 else ""
            creator_info = ""

            # В группах показываем создателя счета (username)
            if chat_type != "private" and account.get('username'):
                creator_info = f" 👤 @{account['username']}"
            elif chat_type != "private" and account.get('created_by'):
                creator_info = f" 👤 user_{account['created_by']}"

            accounts_list.append(f"{i}. {account['account_name']}{precision_info}{creator_info}")

        header = "💼 Счета в этом чате:\n\n" if chat_type != "private" else "💼 Ваши счета:\n\n"

        await update.message.reply_text(
            header + "\n".join(accounts_list) +
            "\n\n💡 Для добавления операции используйте:\n`/<имя_счета> <сумма> <комментарий>`",
            reply_markup=get_main_keyboard()
        )

    except Exception as e:
        logger.error(f"Ошибка при получении счетов: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при получении списка счетов.",
            reply_markup=get_main_keyboard()
        )