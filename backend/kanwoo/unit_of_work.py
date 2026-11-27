from sqlalchemy.orm.session import Session
from collections.abc import Callable
from contextvars import ContextVar
from enum import Enum

class TransactionStatusEnum(Enum):
    OPENED = "opened"
    CLOSED = "closed"
    ROLLED_BACK = "rolled_back"
    UNKNOWN = "unknown"

nesting_level_var: ContextVar[int] = ContextVar('nesting_level', default=0)
after_commit_callbacks: ContextVar[list[Callable[[], None]]] = ContextVar("after_commit_callbacks")

transaction_status: ContextVar[TransactionStatusEnum] = ContextVar(
    'transaction_status', 
    default=TransactionStatusEnum.UNKNOWN
)


class UnitOfWork:
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self._tokens = []

    def flush(self):
        self.db_session.flush()

    def after_commit(self, callback: Callable[[], None]):
        after_commit_callbacks.get().append(callback)

    def __enter__(self):
        nesting_level = nesting_level_var.get()
        if nesting_level == 0:
            after_commit_callbacks.set([])
        token = nesting_level_var.set(nesting_level + 1)
        self._tokens.append(token)
        transaction_status.set(TransactionStatusEnum.OPENED)
        return self

    def __exit__(self, exc_type, exc, tb):
        if not self._tokens:
            raise RuntimeError("Failed to get context token")
        
        token = self._tokens.pop()
        nesting_level_var.reset(token)

        if nesting_level_var.get() == 0:
            callbacks = after_commit_callbacks.get()
            after_commit_callbacks.set([])
            if exc_type is not None:
                self.db_session.rollback()
                transaction_status.set(TransactionStatusEnum.ROLLED_BACK)
                return False

            try:
                self.db_session.commit()
                transaction_status.set(TransactionStatusEnum.CLOSED)
            except Exception:
                self.db_session.rollback()
                transaction_status.set(TransactionStatusEnum.ROLLED_BACK)
                raise
            for callback in callbacks:
                callback()

        return False
