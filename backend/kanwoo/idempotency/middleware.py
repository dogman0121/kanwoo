import hashlib
import json
from datetime import datetime, timezone
from functools import wraps
from uuid import UUID

from dependency_injector.wiring import Provide, inject
from flask import Response, request
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import OperationalError

from kanwoo import AppContainer
from kanwoo.unit_of_work import UnitOfWork

from .exceptions import IdempotencyError
from .models import Idempotency


def idempotent(func):
    @wraps(func)
    @inject
    def wrapper(
        current_profile,
        *args,
        uow: UnitOfWork = Provide[AppContainer.unit_of_work],
        **kwargs,
    ):
        header = request.headers.get("Idempotency-Key")
        if header is None:
            raise IdempotencyError(error="idempotency_key_required")
        try:
            token = UUID(header)
        except ValueError:
            raise IdempotencyError(error="invalid_idempotency_key") from None
        if token.version != 4:
            raise IdempotencyError(error="invalid_idempotency_key")

        scope = f"{current_profile.id}:{request.method}:{request.endpoint}:{token}"
        key = hashlib.sha256(scope.encode()).hexdigest()
        payload = json.dumps(request.get_json(), sort_keys=True, separators=(",", ":"))
        fingerprint = hashlib.sha256(f"{request.path}:{payload}".encode()).hexdigest()

        with uow:
            session = uow.db_session
            try:
                with session.begin_nested():
                    session.execute(text("SET LOCAL lock_timeout = '100ms'"))
                    acquired = session.execute(
                        insert(Idempotency).values(uuid=key)
                        .on_conflict_do_nothing(index_elements=[Idempotency.uuid])
                        .returning(Idempotency.uuid)
                    ).scalar_one_or_none()
                    session.execute(text("SET LOCAL lock_timeout = DEFAULT"))
            except OperationalError as exc:
                if getattr(exc.orig, "sqlstate", getattr(exc.orig, "pgcode", None)) == "55P03":
                    raise IdempotencyError(error="operation_in_progress", status_code=409) from exc
                raise

            record = session.get(Idempotency, key)
            if acquired is None:
                if record.request_hash != fingerprint:
                    raise IdempotencyError(error="request_does_not_match", status_code=409)
                if datetime.fromisoformat(record.expires_at) <= datetime.now(timezone.utc):
                    raise IdempotencyError(error="idempotency_key_expired", status_code=409)
                return Response(record.body, status=record.status_code, mimetype="application/json")

            response = func(current_profile, *args, **kwargs)
            if not 200 <= response.status_code < 300:
                session.rollback()
                return response

            record.request_hash = fingerprint
            record.status_code = response.status_code
            record.body = response.get_data(as_text=True)
            return response

    return wrapper
