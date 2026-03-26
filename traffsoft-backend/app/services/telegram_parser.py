import asyncio
import re
from datetime import datetime
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.orm import Session, joinedload

from app.models.audience import (
    AudienceMember,
    AudienceSource,
    LastSeenBucket,
    ParseJob,
    ParseJobStatus,
    ParseMode,
    SourceMember,
)
from app.core.config import settings


def _phone_to_country(phone: str | None) -> Optional[str]:
    if not phone:
        return None
    phone = phone.lstrip("+").lstrip("00")
    country_codes = {
        "7": "RU", "77": "KZ", "76": "KZ",
        "380": "UA", "哑": "UA",
        "1": "US", "44": "GB", "49": "DE",
        "33": "FR", "39": "IT", "34": "ES",
        "90": "TR", "972": "IL",
    }
    for code, country in sorted(country_codes.items(), key=lambda x: -len(x[0])):
        if phone.startswith(code):
            return country
    return None


def _status_to_bucket(status) -> str:
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
    if status_type == "UserStatusOffline":
        return LastSeenBucket.long_ago.value
    return LastSeenBucket.unknown.value


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

    if not api_id or not api_hash:
        job.status = ParseJobStatus.failed.value
        job.error_message = "TELEGRAM_API_ID и TELEGRAM_API_HASH не настроены"
        job.finished_at = datetime.utcnow()
        db.commit()
        return

    session_name = settings.TELEGRAM_SESSION_NAME or "tg_session"

    async def do_work():
        from telethon import TelegramClient
        client = TelegramClient(session_name, api_id, api_hash)

        try:
            await client.start()

            entity = source.username or source.external_id
            if not entity:
                raise ValueError("Source has no username or external_id")

            mode = job.mode

            if mode == ParseMode.members_full.value:
                count = await _parse_members_full(client, db, job, source, entity)
            elif mode == ParseMode.members_lite.value:
                count = await _parse_members_lite(client, db, job, source, entity)
            elif mode == ParseMode.members_active.value:
                count = await _parse_members_active(client, db, job, source, entity)
            elif mode == ParseMode.admins.value:
                count = await _parse_admins(client, db, job, source, entity)
            else:
                count = await _parse_members_full(client, db, job, source, entity)

            job.status = ParseJobStatus.completed.value
            job.processed_items = count
            job.total_items = count
            job.finished_at = datetime.utcnow()
            job.error_message = None
            db.commit()

            source.is_verified = True
            source.last_parsed_at = datetime.utcnow()
            db.commit()

        except Exception as exc:
            job.status = ParseJobStatus.failed.value
            job.error_message = str(exc)
            job.finished_at = datetime.utcnow()
            db.commit()

            source.parse_errors = (source.parse_errors or 0) + 1
            db.commit()

        finally:
            await client.disconnect()

    asyncio.run(do_work())


async def _parse_members_full(client, db: Session, job: ParseJob, source: AudienceSource, entity):
    count = 0
    new_count = 0
    skip_count = 0
    delay = job.delay_ms / 1000.0

    limit = job.limit_members
    processed = 0

    async for user in client.iter_participants(entity, aggressive=True):
        if limit and processed >= limit:
            break

        if job.skip_bots and getattr(user, "bot", False):
            skip_count += 1
            processed += 1
            continue

        if job.skip_deleted and getattr(user, "deleted", False):
            skip_count += 1
            processed += 1
            continue

        member = _upsert_member(db, user)
        is_new = member.created_at >= (job.started_at - datetime.utcnow().replace(hour=0, minute=0, second=0))

        existing_sm = db.query(SourceMember).filter(
            SourceMember.source_id == source.id,
            SourceMember.member_id == member.id,
        ).first()

        if existing_sm:
            existing_sm.parsed_at = datetime.utcnow()
            existing_sm.is_active = True
        else:
            sm = SourceMember(
                source_id=source.id,
                member_id=member.id,
                role=getattr(user, "participant", None),
                parsed_at=datetime.utcnow(),
                is_active=True,
                is_new=True,
            )
            db.add(sm)

        member.sources_count = db.query(func.count(SourceMember.id)).filter(
            SourceMember.member_id == member.id
        ).scalar() or 0

        count += 1
        if is_new or not existing_sm:
            new_count += 1

        processed += 1

        if processed % 50 == 0:
            job.processed_items = processed
            job.new_members = new_count
            job.skipped_members = skip_count
            db.commit()

        if delay > 0:
            await asyncio.sleep(delay)

    job.new_members = new_count
    job.skipped_members = skip_count
    return count


async def _parse_members_lite(client, db: Session, job: ParseJob, source: AudienceSource, entity):
    count = 0
    new_count = 0
    limit = job.limit_members
    processed = 0

    async for user in client.iter_participants(entity, aggressive=True):
        if limit and processed >= limit:
            break

        if job.skip_bots and getattr(user, "bot", False):
            processed += 1
            continue

        member = db.query(AudienceMember).filter(
            AudienceMember.telegram_id == user.id
        ).first()

        is_new = member is None

        if not member:
            member = AudienceMember(telegram_id=user.id)
            db.add(member)
            db.flush()

        member.username = getattr(user, "username", None)
        member.first_name = getattr(user, "first_name", None)
        member.last_name = getattr(user, "last_name", None)
        member.lang_code = getattr(user, "lang_code", None)
        member.is_bot = bool(getattr(user, "bot", False))

        status = getattr(user, "status", None)
        member.last_seen_bucket = _status_to_bucket(status)
        if hasattr(status, "was_online") and status.was_online:
            member.last_seen_at = status.was_online

        existing_sm = db.query(SourceMember).filter(
            SourceMember.source_id == source.id,
            SourceMember.member_id == member.id,
        ).first()

        if not existing_sm:
            sm = SourceMember(
                source_id=source.id,
                member_id=member.id,
                parsed_at=datetime.utcnow(),
                is_active=True,
                is_new=True,
            )
            db.add(sm)

        count += 1
        if is_new:
            new_count += 1

        processed += 1

        if processed % 100 == 0:
            job.processed_items = processed
            job.new_members = new_count
            db.commit()

        await asyncio.sleep(job.delay_ms / 1000.0)

    job.new_members = new_count
    return count


async def _parse_members_active(client, db: Session, job: ParseJob, source: AudienceSource, entity):
    count = 0
    new_count = 0
    limit = job.limit_members
    processed = 0

    async for user in client.iter_participants(entity, aggressive=True):
        if limit and processed >= limit:
            break

        if job.skip_bots and getattr(user, "bot", False):
            processed += 1
            continue

        status = getattr(user, "status", None)
        bucket = _status_to_bucket(status)

        if bucket in (LastSeenBucket.long_ago.value, LastSeenBucket.unknown.value, LastSeenBucket.hidden.value):
            processed += 1
            continue

        member = _upsert_member(db, user)

        existing_sm = db.query(SourceMember).filter(
            SourceMember.source_id == source.id,
            SourceMember.member_id == member.id,
        ).first()

        if not existing_sm:
            sm = SourceMember(
                source_id=source.id,
                member_id=member.id,
                parsed_at=datetime.utcnow(),
                is_active=True,
                is_new=True,
            )
            db.add(sm)
            new_count += 1

        count += 1
        processed += 1

        if processed % 100 == 0:
            job.processed_items = processed
            job.new_members = new_count
            db.commit()

        await asyncio.sleep(job.delay_ms / 1000.0)

    job.new_members = new_count
    return count


async def _parse_admins(client, db: Session, job: ParseJob, source: AudienceSource, entity):
    count = 0
    new_count = 0

    try:
        chat = await client.get_entity(entity)
        async for user in client.iter_participants(chat, filter=lambda x: x):
            participant = await client.get_permissions(chat, user)
            if not participant or not getattr(participant, "is_admin", False):
                continue

            member = _upsert_member(db, user)

            existing_sm = db.query(SourceMember).filter(
                SourceMember.source_id == source.id,
                SourceMember.member_id == member.id,
            ).first()

            role = None
            if participant.is_creator:
                role = "creator"
            elif participant.is_admin:
                role = "admin"

            if not existing_sm:
                sm = SourceMember(
                    source_id=source.id,
                    member_id=member.id,
                    role=role,
                    parsed_at=datetime.utcnow(),
                    is_active=True,
                    is_new=True,
                )
                db.add(sm)
                new_count += 1
            elif role:
                existing_sm.role = role

            count += 1

            if count % 20 == 0:
                db.commit()

            await asyncio.sleep(job.delay_ms / 1000.0)

    except Exception:
        pass

    job.new_members = new_count
    return count


def _upsert_member(db: Session, user) -> AudienceMember:
    member: AudienceMember = db.query(AudienceMember).filter(
        AudienceMember.telegram_id == user.id
    ).first()

    is_new = member is None
    if not member:
        member = AudienceMember(telegram_id=user.id)
        db.add(member)
        db.flush()

    member.username = getattr(user, "username", None)
    member.first_name = getattr(user, "first_name", None)
    member.last_name = getattr(user, "last_name", None)
    member.lang_code = getattr(user, "lang_code", None)
    member.is_bot = bool(getattr(user, "bot", False))
    member.is_verified = bool(getattr(user, "verified", False))
    member.is_scam = bool(getattr(user, "scam", False))
    member.is_fake = bool(getattr(user, "fake", False))
    member.is_restricted = bool(getattr(user, "restricted", False))
    member.is_deleted = bool(getattr(user, "deleted", False))
    member.bio = getattr(user, "about", None)

    phone = getattr(user, "phone", None)
    if phone:
        member.phone = phone
        member.has_phone = True
        member.country_code = _phone_to_country(phone)

    member.has_photo = bool(getattr(user, "photo", None))

    status = getattr(user, "status", None)
    member.last_seen_bucket = _status_to_bucket(status)
    if hasattr(status, "was_online") and status.was_online:
        member.last_seen_at = status.was_online

    return member
