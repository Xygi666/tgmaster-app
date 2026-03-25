import asyncio
from datetime import datetime
from typing import Optional

from telethon import TelegramClient
from telethon.tl.types import UserStatusOnline, UserStatusRecently, UserStatusOffline

from sqlalchemy.orm import Session

from app.models.audience import (
    AudienceMember,
    AudienceSource,
    LastSeenBucket,
    ParseJob,
    ParseJobStatus,
    SourceMember,
)
from app.core.config import settings


def _status_to_bucket(status) -> str:
    if isinstance(status, (UserStatusOnline, UserStatusRecently)):
        return LastSeenBucket.online.value
    if isinstance(status, UserStatusOffline) and status.was_online:
        delta = datetime.utcnow() - status.was_online
        if delta.days <= 1:
            return LastSeenBucket.day.value
        if delta.days <= 7:
            return LastSeenBucket.week.value
        if delta.days <= 30:
            return LastSeenBucket.month.value
        return LastSeenBucket.long_ago.value
    return LastSeenBucket.unknown.value


async def _iter_members(client: TelegramClient, source: AudienceSource, limit: Optional[int] = None):
    entity = source.username or source.external_id
    if not entity:
        raise ValueError("Source must have username or external_id")

    count = 0
    async for user in client.iter_participants(entity, aggressive=True):
        yield user
        count += 1
        if limit and count >= limit:
            break


def run_parse_job_sync(db: Session, job_id: int):
    job: ParseJob = db.query(ParseJob).filter(ParseJob.id == job_id).first()
    if not job:
        return

    source: AudienceSource = job.source

    job.status = ParseJobStatus.running.value
    job.started_at = datetime.utcnow()
    db.commit()
    db.refresh(job)

    api_id = settings.TELEGRAM_API_ID
    api_hash = settings.TELEGRAM_API_HASH
    session_name = settings.TELEGRAM_SESSION_NAME or "tg_parser"

    client = TelegramClient(session_name, api_id, api_hash)

    async def do_work():
        processed = 0
        async for user in _iter_members(client, source, limit=None):
            member: AudienceMember = (
                db.query(AudienceMember)
                .filter(AudienceMember.telegram_id == user.id)
                .first()
            )
            if not member:
                member = AudienceMember(telegram_id=user.id)

            member.username = user.username
            member.first_name = user.first_name
            member.last_name = user.last_name
            member.lang_code = getattr(user, "lang_code", None)
            member.is_bot = bool(getattr(user, "bot", False))
            member.bio = getattr(user, "about", None)

            status = getattr(user, "status", None)
            member.last_seen_bucket = _status_to_bucket(status)
            if isinstance(status, UserStatusOffline):
                member.last_seen_at = status.was_online

            db.add(member)
            db.flush()

            sm = (
                db.query(SourceMember)
                .filter(
                    SourceMember.source_id == source.id,
                    SourceMember.member_id == member.id,
                )
                .first()
            )
            if not sm:
                sm = SourceMember(source_id=source.id, member_id=member.id)
            sm.parsed_at = datetime.utcnow()
            sm.is_active = True
            db.add(sm)

            processed += 1
            if processed % 100 == 0:
                job.processed_items = processed
                db.commit()
                db.refresh(job)

        job.status = ParseJobStatus.completed.value
        job.processed_items = processed
        job.finished_at = datetime.utcnow()
        job.error_message = None
        db.commit()
        db.refresh(job)

        source.is_verified = True
        db.commit()

    async def run():
        try:
            await client.start()
            await do_work()
        except Exception as exc:
            job.status = ParseJobStatus.failed.value
            job.error_message = str(exc)
            job.finished_at = datetime.utcnow()
            db.commit()
        finally:
            await client.disconnect()

    asyncio.run(run())
