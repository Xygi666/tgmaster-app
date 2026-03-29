import asyncio
import random
import re
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.audience import AudienceMember, SourceMember
from app.models.inviting import InvitingJob, InvitingLog, InvitingStatus, InvitingSource
from app.core.config import settings


INV_ERROR_TRANSLATIONS = {
    "Chat admin privileges are required": "Аккаунт не является админом канала/группы. Нужны права администратора.",
    "Chat not found": "Чат не найден. Проверьте ссылку на целевую группу.",
    "You haven't joined this chat": "Аккаунт не состоит в группе. Вступите в группу.",
    "Privacy Prevention": "Telegram запрещает приглашение из-за настроек приватности.",
    " FLOOD_WAIT": "Flood wait. Telegram ограничил запросы. Подождите.",
    "Too many requests": "Слишком много запросов. Увеличьте задержку.",
    "SESSION_REVOKED": "Сессия отозвана. Переавторизуйте аккаунт.",
    "AuthKeyDuplicated": "Сессия используется в другом месте.",
    "User not participant": "Пользователь не найден в Telegram.",
    "USERS_TOO_MUCH": "Слишком много участников. Достигнут лимит группы.",
    "Peer_id_invalid": "Неверный ID получателя. Попробуйте другой username.",
    "Chat write forbidden": "Нет прав на запись в чат. Аккаунт не состоит в группе.",
}


def _translate_error(error: str) -> str:
    for key, translation in INV_ERROR_TRANSLATIONS.items():
        if key.lower() in error.lower():
            return translation
    return error


def _extract_handle(link: str) -> tuple[str | None, str | None]:
    link = link.strip().lstrip("+")
    if link.startswith("http"):
        match = re.search(r"(?:t\.me/|telegram\.me/)([a-zA-Z0-9_]+)", link)
        if match:
            return f"@{match.group(1)}", match.group(1)
        match2 = re.search(r"joinchat/([a-zA-Z0-9_=-]+)", link)
        if match2:
            return None, match2.group(1)
        return None, None
    if link.startswith("@"):
        return link, link[1:]
    if re.match(r"^[a-zA-Z0-9_]+$", link):
        return f"@{link}", link
    return None, None


def run_inviting_job_sync(db: Session, job_id: int):
    job: InvitingJob = db.query(InvitingJob).filter(InvitingJob.id == job_id).first()
    if not job:
        return

    job.status = InvitingStatus.running.value
    job.started_at = datetime.utcnow()
    db.commit()
    db.refresh(job)

    api_id = settings.TELEGRAM_API_ID
    api_hash = settings.TELEGRAM_API_HASH

    if not api_id or not api_hash:
        job.status = InvitingStatus.failed.value
        job.error_message = "TELEGRAM_API_ID и TELEGRAM_API_HASH не настроены"
        job.finished_at = datetime.utcnow()
        db.commit()
        return

    session_name = settings.TELEGRAM_SESSION_NAME or "tg_session"

    async def do_work():
        from telethon import TelegramClient
        from telethon.tl.functions.channels import InviteToChannelRequest
        from telethon.tl.functions.messages import AddChatUserRequest

        client = TelegramClient(session_name, api_id, api_hash)

        try:
            await client.start()

            min_delay = job.delay_min_ms / 1000.0
            max_delay = job.delay_max_ms / 1000.0

            users_to_invite = _collect_users(db, job)
            job.total_users = len(users_to_invite)
            db.commit()

            target_entity = await client.get_entity(job.target_link)
            target_title = getattr(target_entity, "title", None) or getattr(target_entity, "first_name", None)
            job.target_title = target_title
            db.commit()

            for idx, user_info in enumerate(users_to_invite):
                current_job: InvitingJob = db.query(InvitingJob).filter(InvitingJob.id == job_id).first()
                if current_job.status in (InvitingStatus.cancelled.value, InvitingStatus.paused.value):
                    break

                user_id, username, first_name, lang_code = user_info
                processed = idx + 1
                job.processed_users = processed

                try:
                    user_entity = None
                    if username:
                        try:
                            user_entity = await client.get_entity(username)
                        except Exception:
                            pass

                    if user_id:
                        try:
                            user_entity = await client.get_entity(user_id)
                        except Exception:
                            pass

                    if not user_entity:
                        job.skipped += 1
                        _add_log(db, job_id, user_id, username, first_name, "invite", "not_found")
                        db.commit()
                        await asyncio.sleep(random.uniform(min_delay, max_delay))
                        continue

                    is_channel = hasattr(target_entity, "broadcast") or hasattr(target_entity, "megagroup")
                    if is_channel:
                        await client(InviteToChannelRequest(target_entity, [user_entity]))
                    else:
                        await client(AddChatUserRequest(target_entity, user_entity))

                    job.invited_users += 1
                    _add_log(db, job_id, user_id, username, first_name, "invite", "success")

                except Exception as exc:
                    err_str = str(exc)
                    if "already" in err_str.lower() or "already a member" in err_str.lower() or "user_already_participant" in err_str.lower():
                        job.already_in += 1
                        _add_log(db, job_id, user_id, username, first_name, "invite", "already_in")
                    elif "flood" in err_str.lower() or "flood_wait" in err_str.lower():
                        job.errors_count += 1
                        _add_log(db, job_id, user_id, username, first_name, "invite", "flood", err_str)
                        await asyncio.sleep(random.uniform(max_delay * 2, max_delay * 4))
                    else:
                        job.errors_count += 1
                        _add_log(db, job_id, user_id, username, first_name, "invite", "error", err_str)

                db.commit()

                await asyncio.sleep(random.uniform(min_delay, max_delay))

                if processed % 20 == 0:
                    db.commit()

            final_job: InvitingJob = db.query(InvitingJob).filter(InvitingJob.id == job_id).first()
            if final_job.status == InvitingStatus.running.value:
                final_job.status = InvitingStatus.completed.value
            final_job.finished_at = datetime.utcnow()
            db.commit()

        except Exception as exc:
            job.status = InvitingStatus.failed.value
            job.error_message = _translate_error(str(exc))
            job.finished_at = datetime.utcnow()
            db.commit()

        finally:
            await client.disconnect()

    asyncio.run(do_work())


def _collect_users(db: Session, job: InvitingJob) -> list:
    users = []
    seen_ids = set()

    if job.source_type == InvitingSource.sources.value:
        source_ids = job.source_ids or []
        for source_id in source_ids:
            sms = db.query(SourceMember).filter(SourceMember.source_id == source_id).all()
            for sm in sms:
                member: AudienceMember = db.query(AudienceMember).filter(
                    AudienceMember.id == sm.member_id
                ).first()
                if not member or member.telegram_id in seen_ids:
                    continue
                if job.skip_bots and member.is_bot:
                    continue
                if not _filter_member(member, job):
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

    elif job.source_type == InvitingSource.custom.value:
        for username in (job.custom_usernames or []):
            clean = username.lstrip("@").strip()
            users.append((None, clean, None, None))
            if job.limit_users and len(users) >= job.limit_users:
                return users

    if job.limit_users:
        return users[:job.limit_users]
    return users


def _filter_member(member: AudienceMember, job: InvitingJob) -> bool:
    lang_codes = job.lang_codes
    if lang_codes:
        if not member.lang_code or member.lang_code.lower() not in [l.lower() for l in lang_codes]:
            return False

    activity_filter = job.activity_filter
    if activity_filter:
        if not member.last_seen_bucket or member.last_seen_bucket not in activity_filter:
            return False

    if not member.username and job.skip_already_in:
        return False

    return True


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
    log = InvitingLog(
        job_id=job_id,
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        action=action,
        result=result,
        error_message=error_message,
    )
    db.add(log)
