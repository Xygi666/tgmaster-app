import asyncio
import random
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audience import AudienceMember, SourceMember, LastSeenBucket
from app.models.masslooking import MasslookingJob, MasslookingLog, MasslookingStatus, MasslookingSource
from app.core.config import settings


ML_ERROR_TRANSLATIONS = {
    "Chat admin privileges are required": "Аккаунт не является админом. Нужны права администратора.",
    "Chat not found": "Чат не найден. Проверьте username.",
    "You haven't joined this chat": "Аккаунт не состоит в этом чате.",
    "Privacy Prevention": "Telegram запрещает это действие из-за настроек приватности.",
    " FLOOD_WAIT": "Flood wait. Telegram ограничил запросы. Подождите.",
    "Too many requests": "Слишком много запросов. Увеличьте задержку.",
    "SESSION_REVOKED": "Сессия отозвана. Переавторизуйте аккаунт.",
    "AuthKeyDuplicated": "Сессия используется в другом месте.",
    "User not participant": "Аккаунт не является участником чата.",
}


def _translate_error(error: str) -> str:
    for key, translation in ML_ERROR_TRANSLATIONS.items():
        if key.lower() in error.lower():
            return translation
    return error


def _mode_to_delays(mode: str) -> tuple[int, int]:
    if mode == "safe":
        return 8000, 20000
    elif mode == "aggressive":
        return 500, 2000
    else:
        return 3000, 8000


def run_masslooking_job_sync(db: Session, job_id: int):
    job: MasslookingJob = db.query(MasslookingJob).filter(MasslookingJob.id == job_id).first()
    if not job:
        return

    job.status = MasslookingStatus.running.value
    job.started_at = datetime.utcnow()
    db.commit()
    db.refresh(job)

    api_id = settings.TELEGRAM_API_ID
    api_hash = settings.TELEGRAM_API_HASH

    if not api_id or not api_hash:
        job.status = MasslookingStatus.failed.value
        job.error_message = "TELEGRAM_API_ID и TELEGRAM_API_HASH не настроены"
        job.finished_at = datetime.utcnow()
        db.commit()
        return

    session_name = settings.TELEGRAM_SESSION_NAME or "tg_session"

    async def do_work():
        from telethon import TelegramClient
        from telethon.tl.functions import stories

        client = TelegramClient(session_name, api_id, api_hash)

        try:
            await client.start()

            min_delay = job.delay_min_ms / 1000.0
            max_delay = job.delay_max_ms / 1000.0

            users_to_watch = await _collect_users(client, db, job)
            job.total_users = len(users_to_watch)
            db.commit()

            for idx, user_info in enumerate(users_to_watch):
                current_job: MasslookingJob = db.query(MasslookingJob).filter(MasslookingJob.id == job_id).first()
                if current_job.status in (MasslookingStatus.cancelled.value, MasslookingStatus.paused.value):
                    break

                user_id, username, first_name, lang_code, activity = user_info
                processed = idx + 1
                job.processed_users = processed

                if job.skip_bots and getattr(user_info, "is_bot", False):
                    job.users_skipped += 1
                    db.commit()
                    continue

                try:
                    if not hasattr(user_id, "__int__"):
                        user_id = int(user_id)

                    result = await client(
                        stories.ReadStoriesRequest(
                            peer=user_id,
                            max_id=0,
                        )
                    )
                    stories_count = len(result) if result else 1
                    job.stories_watched += stories_count
                    job.users_with_stories += 1

                    _add_log(db, job_id, user_id, username, first_name, "watch", "success", watched_stories=stories_count)

                except Exception as exc:
                    err_str = str(exc)
                    if "stories_unavailable" in err_str.lower() or "no stories" in err_str.lower():
                        job.users_skipped += 1
                        _add_log(db, job_id, user_id, username, first_name, "watch", "no_stories")
                    elif "user not found" in err_str.lower() or "peer_id_invalid" in err_str.lower():
                        job.errors_count += 1
                        _add_log(db, job_id, user_id, username, first_name, "watch", "user_not_found", err_str)
                    else:
                        job.errors_count += 1
                        _add_log(db, job_id, user_id, username, first_name, "watch", "error", err_str)

                db.commit()

                delay = random.uniform(min_delay, max_delay)
                await asyncio.sleep(delay)

                if processed % 50 == 0:
                    db.commit()

            final_job: MasslookingJob = db.query(MasslookingJob).filter(MasslookingJob.id == job_id).first()
            if final_job.status == MasslookingStatus.running.value:
                final_job.status = MasslookingStatus.completed.value
            final_job.finished_at = datetime.utcnow()
            db.commit()

        except Exception as exc:
            job.status = MasslookingStatus.failed.value
            job.error_message = _translate_error(str(exc))
            job.finished_at = datetime.utcnow()
            db.commit()

        finally:
            await client.disconnect()

    asyncio.run(do_work())


async def _collect_users(client, db: Session, job: MasslookingJob) -> list:
    users = []
    seen_ids = set()

    if job.source_type == MasslookingSource.dialogs.value:
        async for dialog in client.iter_dialogs(limit=500):
            if dialog.is_group or dialog.is_channel:
                try:
                    async for user in client.iter_participants(dialog.entity, limit=500, aggressive=True):
                        if user.id in seen_ids:
                            continue
                        seen_ids.add(user.id)

                        if _filter_user(user, job):
                            users.append((
                                user.id,
                                getattr(user, "username", None),
                                getattr(user, "first_name", None),
                                getattr(user, "lang_code", None),
                                _get_activity(user),
                            ))

                        if job.limit_users and len(users) >= job.limit_users:
                            return users

                except Exception:
                    continue

    elif job.source_type == MasslookingSource.sources.value:
        source_ids = job.source_ids or []
        if not source_ids:
            return users

        for source_id in source_ids:
            source_members = db.query(SourceMember).options().filter(
                SourceMember.source_id == source_id
            ).all()

            for sm in source_members:
                member: AudienceMember = db.query(AudienceMember).filter(
                    AudienceMember.id == sm.member_id
                ).first()

                if not member or member.telegram_id in seen_ids:
                    continue
                seen_ids.add(member.telegram_id)

                if _filter_member(member, job):
                    users.append((
                        member.telegram_id,
                        member.username,
                        member.first_name,
                        member.lang_code,
                        member.last_seen_bucket,
                    ))

                if job.limit_users and len(users) >= job.limit_users:
                    return users

    elif job.source_type == MasslookingSource.custom.value:
        usernames = job.custom_usernames or []
        for username in usernames:
            clean = username.lstrip("@").strip()
            try:
                entity = await client.get_entity(clean)
                if hasattr(entity, "id"):
                    if entity.id in seen_ids:
                        continue
                    seen_ids.add(entity.id)

                    if _filter_user(entity, job):
                        users.append((
                            entity.id,
                            getattr(entity, "username", None),
                            getattr(entity, "first_name", None),
                            getattr(entity, "lang_code", None),
                            _get_activity(entity),
                        ))
            except Exception:
                continue

            if job.limit_users and len(users) >= job.limit_users:
                return users

    if job.limit_users:
        return users[:job.limit_users]
    return users


def _filter_user(user, job: MasslookingJob) -> bool:
    if job.skip_bots and getattr(user, "bot", False):
        return False

    lang_codes = job.lang_codes
    if lang_codes:
        user_lang = getattr(user, "lang_code", None)
        if not user_lang or user_lang.lower() not in [l.lower() for l in lang_codes]:
            return False

    return True


def _filter_member(member: AudienceMember, job: MasslookingJob) -> bool:
    if job.skip_bots and member.is_bot:
        return False

    lang_codes = job.lang_codes
    if lang_codes:
        if not member.lang_code or member.lang_code.lower() not in [l.lower() for l in lang_codes]:
            return False

    activity_filter = job.activity_filter
    if activity_filter:
        if not member.last_seen_bucket or member.last_seen_bucket not in activity_filter:
            return False

    return True


def _get_activity(user) -> str:
    status = getattr(user, "status", None)
    if status is None:
        return LastSeenBucket.unknown.value
    status_type = type(status).__name__
    if status_type in ("UserStatusOnline",):
        return LastSeenBucket.online.value
    if status_type in ("UserStatusRecently",):
        return LastSeenBucket.day.value
    if hasattr(status, "was_online") and status.was_online:
        delta = datetime.utcnow() - status.was_online
        if delta.days <= 1:
            return LastSeenBucket.day.value
        if delta.days <= 7:
            return LastSeenBucket.week.value
        if delta.days <= 30:
            return LastSeenBucket.month.value
        return LastSeenBucket.long_ago.value
    if status_type == "UserStatusEmpty":
        return LastSeenBucket.hidden.value
    return LastSeenBucket.unknown.value


def _add_log(
    db: Session,
    job_id: int,
    telegram_id: int | None,
    username: str | None,
    first_name: str | None,
    action: str,
    result: str,
    error_message: str | None = None,
    watched_stories: int = 0,
):
    log = MasslookingLog(
        job_id=job_id,
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        action=action,
        result=result,
        error_message=error_message,
        watched_stories=watched_stories,
    )
    db.add(log)
