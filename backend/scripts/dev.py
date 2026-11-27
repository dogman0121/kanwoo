import os
import signal
import subprocess
import sys
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory

from .utils.compose_down import compose_down
from .utils.compose_up import compose_up
from .utils.upgrade_database import upgrade_database
from .utils.seed_database import seed_database

COMPOSE_FILE = "docker/docker-compose.dev.yml"


def _stop_process(process):
    if process.poll() is None:
        try:
            if os.name == "nt":
                process.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                os.killpg(process.pid, signal.SIGTERM)
        except OSError:
            _kill_process_group(process)
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        _kill_process_group(process)
        process.wait()


def _kill_process_group(process):
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if process.poll() is None:
            process.kill()
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def _run_dev_processes():
    celery = [sys.executable, "-m", "celery", "-A", "manage:celery_app"]
    process_group = (
        {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
        if os.name == "nt"
        else {"start_new_session": True}
    )
    with TemporaryDirectory(prefix="kanwoo-celery-") as schedule_dir, ExitStack() as stack:
        commands = {
            "Celery worker": [*celery, "worker", "--pool=solo", "--concurrency=1", "--loglevel=INFO"],
            "Celery Beat": [
                *celery, "beat", "--loglevel=INFO", "--schedule", str(Path(schedule_dir) / "schedule")
            ],
        }
        celery_processes = {}
        for name, command in commands.items():
            process = subprocess.Popen(command, **process_group)
            stack.callback(_stop_process, process)
            celery_processes[name] = process

        flask = subprocess.Popen(
            [sys.executable, "-m", "flask", "run", "-h", "0.0.0.0", "-p", "5000"],
            **process_group,
        )
        stack.callback(_stop_process, flask)
        while True:
            for name, process in celery_processes.items():
                if (code := process.poll()) is not None:
                    raise RuntimeError(f"{name} завершился с кодом {code}")
            try:
                return flask.wait(timeout=1)
            except subprocess.TimeoutExpired:
                continue


def _shutdown_signals():
    """Сигналы, которые означают «останови dev‑стек» на данной ОС."""
    # SIGTERM и SIGINT есть и на Linux, и на Windows
    sigs = [signal.SIGTERM, signal.SIGINT]

    # SIGHUP — только POSIX (Linux/macOS)
    if hasattr(signal, "SIGHUP"):
        sigs.append(signal.SIGHUP)

    # SIGBREAK — только Windows (Ctrl+Break), полезен как аналог SIGHUP
    if hasattr(signal, "SIGBREAK"):
        sigs.append(signal.SIGBREAK)

    return sigs


def main():
    def handle_graceful_down(*_args, **_kwargs):
        # Не вызываем compose_down здесь — просто разворачиваем стек,
        # а cleanup сделает `finally` ниже (иначе compose_down вызовется дважды).
        sys.exit(0)

    for sig in _shutdown_signals():
        try:
            signal.signal(sig, handle_graceful_down)
        except (ValueError, OSError, RuntimeError):
            # Например, код выполняется не в главном потоке — такой сигнал
            # зарегистрировать нельзя, просто пропускаем.
            pass

    up_process = compose_up(COMPOSE_FILE)

    if up_process.returncode != 0:
        compose_down(COMPOSE_FILE)
        raise BrokenPipeError("Не получилось запустить Docker контейнер.")

    try:
        upgrade_process = upgrade_database()

        if upgrade_process.returncode != 0:
            raise BrokenPipeError("Невозможно применить миграции")

        seed_database()

        return _run_dev_processes()
    finally:
        compose_down(COMPOSE_FILE)
