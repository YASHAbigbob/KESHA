from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any


# ===== DATACLASS MODELS =====

@dataclass
class User:
    """Модель пользователя Telegram"""
    user_id: int
    username: Optional[str] = None
    created_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'user_id': self.user_id,
            'username': self.username,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        return cls(
            user_id=data['user_id'],
            username=data['username'],
            created_at=datetime.fromisoformat(data['created_at']) if data['created_at'] else None
        )


@dataclass
class Chat:
    """Модель чата (группа или личные сообщения)"""
    chat_id: int
    chat_type: str  # 'private' или 'group'
    title: Optional[str] = None
    created_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'chat_id': self.chat_id,
            'chat_type': self.chat_type,
            'title': self.title,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Chat':
        return cls(
            chat_id=data['chat_id'],
            chat_type=data['chat_type'],
            title=data['title'],
            created_at=datetime.fromisoformat(data['created_at']) if data['created_at'] else None
        )

    @property
    def is_private(self) -> bool:
        return self.chat_type == 'private'

    @property
    def is_group(self) -> bool:
        return self.chat_type == 'group'


@dataclass
class Account:
    """Модель счета пользователя"""
    account_id: int
    chat_id: int
    account_name: str
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'account_id': self.account_id,
            'chat_id': self.chat_id,
            'account_name': self.account_name,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Account':
        return cls(
            account_id=data['account_id'],
            chat_id=data['chat_id'],
            account_name=data['account_name'],
            created_by=data['created_by'],
            created_at=datetime.fromisoformat(data['created_at']) if data['created_at'] else None
        )


@dataclass
class Transaction:
    transaction_id: int
    account_id: int
    amount: float
    date: datetime
    comment: Optional[str] = None
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    is_archived: bool = False
    is_reverted: bool = False                    # ДОБАВИТЬ
    revert_comment: Optional[str] = None         # ДОБАВИТЬ
    reverted_by: Optional[int] = None            # ДОБАВИТЬ
    reverted_at: Optional[datetime] = None       # ДОБАВИТЬ

    def to_dict(self) -> Dict[str, Any]:
        return {
            'transaction_id': self.transaction_id,
            'account_id': self.account_id,
            'amount': self.amount,
            'date': self.date.isoformat(),
            'comment': self.comment,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_archived': 1 if self.is_archived else 0,
            'is_reverted': 1 if self.is_reverted else 0,           # ДОБАВИТЬ
            'revert_comment': self.revert_comment,                 # ДОБАВИТЬ
            'reverted_by': self.reverted_by,                       # ДОБАВИТЬ
            'reverted_at': self.reverted_at.isoformat() if self.reverted_at else None  # ДОБАВИТЬ
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Transaction':
        return cls(
            transaction_id=data['transaction_id'],
            account_id=data['account_id'],
            amount=data['amount'],
            date=datetime.fromisoformat(data['date']),
            comment=data['comment'],
            created_by=data['created_by'],
            created_at=datetime.fromisoformat(data['created_at']) if data['created_at'] else None,
            is_archived=bool(data['is_archived']),
            is_reverted=bool(data.get('is_reverted', 0)),                          # ДОБАВИТЬ
            revert_comment=data.get('revert_comment'),                             # ДОБАВИТЬ
            reverted_by=data.get('reverted_by'),                                   # ДОБАВИТЬ
            reverted_at=datetime.fromisoformat(data['reverted_at']) if data.get('reverted_at') else None  # ДОБАВИТЬ
        )

    @property
    def type(self) -> str:
        return "доход" if self.amount >= 0 else "расход"

    def get_formatted_amount(self) -> str:
        return f"{self.amount:+.2f}"


@dataclass
class Reconciliation:
    """Модель сверки баланса счета"""
    reconciliation_id: int
    account_id: int
    balance: float
    reconciliation_date: datetime
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'reconciliation_id': self.reconciliation_id,
            'account_id': self.account_id,
            'balance': self.balance,
            'reconciliation_date': self.reconciliation_date.isoformat(),
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Reconciliation':
        return cls(
            reconciliation_id=data['reconciliation_id'],
            account_id=data['account_id'],
            balance=data['balance'],
            reconciliation_date=datetime.fromisoformat(data['reconciliation_date']),
            created_by=data['created_by'],
            created_at=datetime.fromisoformat(data['created_at']) if data['created_at'] else None
        )


@dataclass
class ChatMember:
    """Модель участника чата"""
    chat_id: int
    user_id: int
    joined_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'chat_id': self.chat_id,
            'user_id': self.user_id,
            'joined_at': self.joined_at.isoformat() if self.joined_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChatMember':
        return cls(
            chat_id=data['chat_id'],
            user_id=data['user_id'],
            joined_at=datetime.fromisoformat(data['joined_at']) if data['joined_at'] else None
        )


# ===== VALIDATION FUNCTIONS =====

def validate_transaction_data(amount: float, date: datetime, comment: str = None) -> List[str]:
    errors = []

    if amount == 0:
        errors.append("Сумма не может быть равна нулю")

    if abs(amount) > 10 ** 9:
        errors.append("Сумма слишком большая")

    if date > datetime.now():
        errors.append("Дата не может быть в будущем")

    if comment and len(comment) > 500:
        errors.append("Комментарий слишком длинный (макс. 500 символов)")

    return errors


def validate_account_data(account_name: str) -> List[str]:
    errors = []

    if not account_name or not account_name.strip():
        errors.append("Название счета не может быть пустым")

    if len(account_name) > 100:
        errors.append("Название счета слишком длинное (макс. 100 символов)")

    return errors


def validate_reconciliation_data(balance: float, reconciliation_date: datetime) -> List[str]:
    errors = []

    if abs(balance) > 10 ** 12:
        errors.append("Баланс слишком большой")

    if reconciliation_date > datetime.now():
        errors.append("Дата сверки не может быть в будущем")

    return errors


# ===== CONVERSION FUNCTIONS =====

def dict_to_user(data: Dict[str, Any]) -> User:
    return User.from_dict(data)


def dict_to_chat(data: Dict[str, Any]) -> Chat:
    return Chat.from_dict(data)


def dict_to_account(data: Dict[str, Any]) -> Account:
    return Account.from_dict(data)


def dict_to_transaction(data: Dict[str, Any]) -> Transaction:
    return Transaction.from_dict(data)


def dict_to_reconciliation(data: Dict[str, Any]) -> Reconciliation:
    return Reconciliation.from_dict(data)


def dict_to_chat_member(data: Dict[str, Any]) -> ChatMember:
    return ChatMember.from_dict(data)


# ===== STATISTICS MODELS =====

@dataclass
class ChatSummary:
    """Сводная информация по чату"""
    chat: Chat
    total_income: float
    total_expenses: float
    current_balance: float
    account_count: int
    transaction_count: int
    last_transaction_date: Optional[datetime] = None


@dataclass
class AccountSummary:
    """Сводная информация по счету"""
    account: Account
    total_income: float
    total_expenses: float
    current_balance: float
    transaction_count: int
    last_transaction_date: Optional[datetime] = None


@dataclass
class UserChatSummary:
    """Сводная информация пользователя по чату"""
    user: User
    chat: Chat
    transactions_created: int
    accounts_created: int
    total_contribution: float  # общая сумма операций, созданных пользователем


def validate_precision(precision: int) -> List[str]:
    """Валидация точности счета"""
    errors = []

    if not isinstance(precision, int):
        errors.append("Точность должна быть целым числом")
    elif precision < 0 or precision > 8:
        errors.append("Точность должна быть в диапазоне от 0 до 8")

    return errors
