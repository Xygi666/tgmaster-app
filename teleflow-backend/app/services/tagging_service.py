import asyncio
import random
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.audience import AudienceMember, SourceMember
from app.models.tagging import TaggingJob, TaggingLog, TaggingStatus, TaggingSource
from app.core.config import settings


TAG_ERROR_TRANSLATIONS = {
    "Chat admin privileges are required": "Аккаунт не является админом. Нужны права администратора.",
    "Chat not found": "Чат не найден. Проверьте ссылку.",
    "You haven't joined this chat": "Аккаунт не состоит в чате.",
    "Privacy Prevention": "Telegram запрещает это действие из-за настроек приватности.",
    " FLOOD_WAIT": "Flood wait. Telegram ограничил запросы. Подождите.",
    "Too many requests": "Слишком много запросов. Увеличьте задержку.",
    "SESSION_REVOKED": "Сессия отозвана. Переавторизуйте аккаунт.",
    "AuthKeyDuplicated": "Сессия используется в другом месте.",
    "Message not found": "Сообщение не найдено. Проверьте ID сообщения.",
}


def _translate_error(error: str) -> str:
    for key, translation in TAG_ERROR_TRANSLATIONS.items():
        if key.lower() in error.lower():
            return translation
    return error


def run_tagging_job_sync(db: Session, job_id: int):
    job: TaggingJob = db.query(TaggingJob).filter(TaggingJob.id == job_id).first()
    if not job:
        return

    job.status = TaggingStatus.running.value
    job.started_at = datetime.utcnow()
    db.commit()
    db.refresh(job)

    api_id = settings.TELEGRAM_API_ID
    api_hash = settings.TELEGRAM_API_HASH

    if not api_id or not api_hash:
        job.status = TaggingStatus.failed.value
        job.error_message = "TELEGRAM_API_ID и TELEGRAM_API_HASH не настроены"
        job.finished_at = datetime.utcnow()
        db.commit()
        return

    session_name = settings.TELEGRAM_SESSION_NAME or "tg_session"

    async def do_work():
        from telethon import TelegramClient
        from telethon.tl.functions.messages import GetMessagesRequest

        client = TelegramClient(session_name, api_id, api_hash)

        try:
            await client.start()

            min_delay = job.delay_min_ms / 1000.0
            max_delay = job.delay_max_ms / 1000.0
            batch_size = job.batch_size

            users_to_tag = _collect_users(db, job)
            job.total_users = len(users_to_tag)
            db.commit()

            target_title = None
            target_entity = None
            if job.target_link:
                try:
                    target_entity = await client.get_entity(job.target_link)
                    target_title = getattr(target_entity, "title", None) or getattr(target_entity, "first_name", None)
                    job.target_title = target_title
                    db.commit()
                except Exception:
                    pass

            for idx in range(0, len(users_to_tag), batch_size):
                current_job: TaggingJob = db.query(TaggingJob).filter(TaggingJob.id == job_id).first()
                if current_job.status in (TaggingStatus.cancelled.value, TaggingStatus.paused.value):
                    break

                batch = users_to_tag[idx:idx + batch_size]
                mentions = []

                for user_info in batch:
                    user_id, username, first_name, lang_code = user_info
                    if not username and job.skip_no_username:
                        job.skipped += 1
                        job.processed_users += 1
                        continue

                    if username:
                        try:
                            entity = await client.get_entity(username)
                            mentions.append(entity)
                        except Exception:
                            job.skipped += 1
                            job.processed_users += 1
                            continue
                    else:
                        job.skipped += 1
                        job.processed_users += 1
                        continue

                    job.processed_users += 1

                if not mentions:
                    continue

                try:
                    text = job.template or "Привет!"
                    mention_text = " ".join(f"@{getattr(u, 'username', '')}" for u in mentions)

                    if target_entity and job.message_id:
                        reply = await client.get_messages(target_entity, ids=job.message_id)
                        if reply:
                            await client.send_message(
                                target_entity,
                                f"@{reply.from_id.user_id} {mention_text}",
                                reply_to=job.message_id,
                            )
                        else:
                            await client.send_message(target_entity, f"{text}\n{mention_text}")
                    elif target_entity:
                        await client.send_message(target_entity, f"{text}\n{mention_text}")
                    else:
                        for user_entity in mentions:
                            await client.send_message(
                                user_entity,
                                text.replace("{username}", f"@{getattr(user_entity, 'username', '')}").replace("@", ""),
                            )

                    job.tagged_users += len(mentions)
                    for u in mentions:
                        _add_log(db, job_id, u.id, getattr(u, "username", None),
                                 getattr(u, "first_name", None), "tag", "success")

                except Exception as exc:
                    job.errors_count += 1
                    err_str = str(exc)
                    _add_log(db, job_id, None, None, None, "tag", "error", err_str)

                db.commit()
                await asyncio.sleep(random.uniform(min_delay, max_delay))

                if (idx + batch_size) % 50 == 0:
                    db.commit()

            final_job: TaggingJob = db.query(TaggingJob).filter(TaggingJob.id == job_id).first()
            if final_job.status == TaggingStatus.running.value:
                final_job.status = TaggingStatus.completed.value
            final_job.finished_at = datetime.utcnow()
            db.commit()

        except Exception as exc:
            job.status = TaggingStatus.failed.value
            job.error_message = _translate_error(str(exc))
            job.finished_at = datetime.utcnow()
            db.commit()

        finally:
            await client.disconnect()

    asyncio.run(do_work())


def _collect_users(db: Session, job: TaggingJob) -> list:
    users = []
    seen_ids = set()

    if job.source_type == TaggingSource.sources.value:
        for source_id in (job.source_ids or []):
            sms = db.query(SourceMember).filter(SourceMember.source_id == source_id).all()
            for sm in sms:
                member: AudienceMember = db.query(AudienceMember).filter(
                    AudienceMember.id == sm.member_id
                ).first()
                if not member or member.telegram_id in seen_ids:
                    continue
                if job.skip_no_username and not member.username:
                    continue
                if job.lang_codes:
                    lc = job.lang_codes
                    if not member.lang_code or member.lang_code.lower() not in [l.lower() for l in lc]:
                        continue
                seen_ids.add(member.telegram_id)
                users.append((
                    member.telegram_id,
                    member.username,
                    member.first_name,
                    member.lang_code,
                ))
                if job.limit_users and len(users) >= job.limit_users:
                    return users

    elif job.source_type == TaggingSource.custom.value:
        for username in (job.custom_usernames or []):
            clean = username.lstrip("@").strip()
            users.append((None, clean, None, None))
            if job.limit_users and len(users) >= job.limit_users:
                return users

    if job.limit_users:
        return users[:job.limit_users]
    return users


def _add_log(
    db: Session,
    job_id: int,
    telegram_id: int | None,
    username: str | None,
    first_name: str | None,
    action: str,
    result: str,
    error_message: str | None = None,
):
    log = TaggingLog(
        job_id=job_id,
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        action=action,
        result=result,
        error_message=error_message,
    )
    db.add(log)
