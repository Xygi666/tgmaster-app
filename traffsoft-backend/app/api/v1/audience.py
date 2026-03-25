import csv
import io
import re
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, and_, or_, text
from sqlalchemy.orm import aliased, selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.audience import (
    AudienceMember,
    AudienceSegment,
    AudienceSource,
    LastSeenBucket,
    MemberExclusion,
    ParseJob,
    ParseJobStatus,
    ParseMode,
    SourceMember,
)
from app.schemas.audience import (
    ActivityStats,
    AnalyticsOverview,
    AudienceMemberRead,
    AudienceSourceCreate,
    AudienceSourceRead,
    AudienceSourceUpdate,
    ExclusionByUsername,
    ExclusionCreate,
    MemberExportRequest,
    MemberFilters,
    ParseJobCreate,
    ParseJobList,
    ParseJobProgress,
    ParseJobRead,
    SegmentCreate,
    SegmentRead,
    SourceOverlap,
    SourceStats,
)
from app.services.telegram_parser import run_parse_job_sync

router = APIRouter(prefix="/api/v1/audience", tags=["audience"])


def _extract_handle(link: str) -> tuple[str | None, str | None]:
    """Из ссылки @username, https://t.me/username или username -> username и external_id."""
    link = link.strip().lstrip("+")
    if link.startswith("http"):
        match = re.search(r"(?:t\\.me/|telegram\\.me/)([a-zA-Z0-9_]+)", link)
        if match:
            return f"@{match.group(1)}", match.group(1)
        return None, None
    if link.startswith("@"):
        return link, link[1:]
    if re.match(r"^[a-zA-Z0-9_]+$", link):
        return f"@{link}", link
    return None, None


# ---------- SOURCES ----------

@router.post("/sources", response_model=AudienceSourceRead)
async def create_source(
    payload: AudienceSourceCreate,
    db: AsyncSession = Depends(get_db),
):
    username, external_id = _extract_handle(payload.link)

    existing = await db.execute(
        select(AudienceSource).where(
            or_(
                AudienceSource.username == username,
                AudienceSource.external_id == external_id,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Источник уже существует")

    source = AudienceSource(
        type=payload.type.value,
        username=username,
        external_id=external_id,
        title=payload.title or username,
        description=payload.description,
    )
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return source


@router.get("/sources", response_model=list[AudienceSourceRead])
async def list_sources(
    db: AsyncSession = Depends(get_db),
    type_filter: Optional[str] = Query(None, alias="type"),
    verified_only: bool = Query(False, alias="verified"),
):
    query = select(AudienceSource)
    if type_filter:
        query = query.where(AudienceSource.type == type_filter)
    if verified_only:
        query = query.where(AudienceSource.is_verified == True)
    query = query.order_by(AudienceSource.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/sources/{source_id}", response_model=AudienceSourceRead)
async def get_source(source_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AudienceSource).where(AudienceSource.id == source_id))
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Источник не найден")
    return source


@router.patch("/sources/{source_id}", response_model=AudienceSourceRead)
async def update_source(
    source_id: int,
    payload: AudienceSourceUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AudienceSource).where(AudienceSource.id == source_id))
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Источник не найден")
    if payload.title is not None:
        source.title = payload.title
    if payload.description is not None:
        source.description = payload.description
    await db.commit()
    await db.refresh(source)
    return source


@router.delete("/sources/{source_id}")
async def delete_source(source_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AudienceSource).where(AudienceSource.id == source_id))
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Источник не найден")
    await db.delete(source)
    await db.commit()
    return {"status": "deleted"}


# ---------- SOURCE STATS ----------

@router.get("/sources/{source_id}/stats", response_model=SourceStats)
async def get_source_stats(source_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AudienceSource).where(AudienceSource.id == source_id))
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Источник не найден")

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    sm_alias = aliased(SourceMember)

    total_result = await db.execute(
        select(func.count(SourceMember.id)).where(SourceMember.source_id == source_id)
    )
    total = total_result.scalar() or 0

    new_result = await db.execute(
        select(func.count(SourceMember.id)).where(
            and_(
                SourceMember.source_id == source_id,
                SourceMember.parsed_at >= today_start,
            )
        )
    )
    new_today = new_result.scalar() or 0

    active_day = await db.scalar(
        select(func.count(SourceMember.id))
        .join(AudienceMember, SourceMember.member_id == AudienceMember.id)
        .where(
            and_(
                SourceMember.source_id == source_id,
                AudienceMember.last_seen_bucket.in_([LastSeenBucket.online.value, LastSeenBucket.day.value]),
            )
        )
    ) or 0

    active_week = await db.scalar(
        select(func.count(SourceMember.id))
        .join(AudienceMember, SourceMember.member_id == AudienceMember.id)
        .where(
            and_(
                SourceMember.source_id == source_id,
                AudienceMember.last_seen_bucket.in_([LastSeenBucket.online.value, LastSeenBucket.day.value, LastSeenBucket.week.value]),
            )
        )
    ) or 0

    active_month = await db.scalar(
        select(func.count(SourceMember.id))
        .join(AudienceMember, SourceMember.member_id == AudienceMember.id)
        .where(
            and_(
                SourceMember.source_id == source_id,
                AudienceMember.last_seen_bucket.in_([
                    LastSeenBucket.online.value, LastSeenBucket.day.value,
                    LastSeenBucket.week.value, LastSeenBucket.month.value,
                ]),
            )
        )
    ) or 0

    long_ago = await db.scalar(
        select(func.count(SourceMember.id))
        .join(AudienceMember, SourceMember.member_id == AudienceMember.id)
        .where(
            and_(SourceMember.source_id == source_id, AudienceMember.last_seen_bucket == LastSeenBucket.long_ago.value)
        )
    ) or 0

    hidden = await db.scalar(
        select(func.count(SourceMember.id))
        .join(AudienceMember, SourceMember.member_id == AudienceMember.id)
        .where(
            and_(SourceMember.source_id == source_id, AudienceMember.last_seen_bucket == LastSeenBucket.hidden.value)
        )
    ) or 0

    bots = await db.scalar(
        select(func.count(SourceMember.id))
        .join(AudienceMember, SourceMember.member_id == AudienceMember.id)
        .where(and_(SourceMember.source_id == source_id, AudienceMember.is_bot == True))
    ) or 0

    with_usernames = await db.scalar(
        select(func.count(SourceMember.id))
        .join(AudienceMember, SourceMember.member_id == AudienceMember.id)
        .where(and_(SourceMember.source_id == source_id, AudienceMember.username.isnot(None)))
    ) or 0

    with_phones = await db.scalar(
        select(func.count(SourceMember.id))
        .join(AudienceMember, SourceMember.member_id == AudienceMember.id)
        .where(and_(SourceMember.source_id == source_id, AudienceMember.has_phone == True))
    ) or 0

    with_bio = await db.scalar(
        select(func.count(SourceMember.id))
        .join(AudienceMember, SourceMember.member_id == AudienceMember.id)
        .where(and_(SourceMember.source_id == source_id, AudienceMember.bio.isnot(None)))
    ) or 0

    with_photos = await db.scalar(
        select(func.count(SourceMember.id))
        .join(AudienceMember, SourceMember.member_id == AudienceMember.id)
        .where(and_(SourceMember.source_id == source_id, AudienceMember.has_photo == True))
    ) or 0

    lang_result = await db.execute(
        select(AudienceMember.lang_code, func.count(AudienceMember.id))
        .join(SourceMember, SourceMember.member_id == AudienceMember.id)
        .where(
            and_(
                SourceMember.source_id == source_id,
                AudienceMember.lang_code.isnot(None),
            )
        )
        .group_by(AudienceMember.lang_code)
    )
    languages = {row[0]: row[1] for row in lang_result.all()}

    country_result = await db.execute(
        select(AudienceMember.country_code, func.count(AudienceMember.id))
        .join(SourceMember, SourceMember.member_id == AudienceMember.id)
        .where(
            and_(
                SourceMember.source_id == source_id,
                AudienceMember.country_code.isnot(None),
            )
        )
        .group_by(AudienceMember.country_code)
    )
    countries = {row[0]: row[1] for row in country_result.all()}

    return SourceStats(
        source_id=source_id,
        total_members=total,
        new_members_today=new_today,
        active_last_day=active_day,
        active_last_week=active_week,
        active_last_month=active_month,
        long_ago=long_ago,
        hidden=hidden,
        bots=bots,
        with_usernames=with_usernames,
        with_phones=with_phones,
        with_bio=with_bio,
        with_photos=with_photos,
        languages=languages,
        countries=countries,
    )


# ---------- PARSE JOBS ----------

@router.post("/parse-jobs", response_model=ParseJobRead)
async def create_parse_job(
    payload: ParseJobCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AudienceSource).where(AudienceSource.id == payload.source_id))
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Источник не найден")

    job = ParseJob(
        source_id=payload.source_id,
        mode=payload.mode.value,
        status=ParseJobStatus.pending.value,
        limit_members=payload.limit_members,
        delay_ms=payload.delay_ms,
        skip_bots=payload.skip_bots,
        skip_deleted=payload.skip_deleted,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    from app.core.database import sync_session_maker
    job_id = job.id

    def run_job():
        with sync_session_maker() as s:
            from app.services.telegram_parser import run_parse_job_sync
            run_parse_job_sync(s, job_id)

    background_tasks.add_task(run_job)

    return job


@router.get("/parse-jobs", response_model=list[ParseJobList])
async def list_parse_jobs(
    db: AsyncSession = Depends(get_db),
    source_id: Optional[int] = Query(None, alias="source_id"),
    status: Optional[str] = None,
    limit: int = Query(20, le=100),
):
    query = (
        select(ParseJob, AudienceSource.title)
        .join(AudienceSource, ParseJob.source_id == AudienceSource.id)
        .order_by(ParseJob.created_at.desc())
        .limit(limit)
    )
    if source_id:
        query = query.where(ParseJob.source_id == source_id)
    if status:
        query = query.where(ParseJob.status == status)

    result = await db.execute(query)
    rows = result.all()
    return [
        ParseJobList(
            id=job.id,
            source_id=job.source_id,
            source_title=title,
            mode=job.mode,
            status=job.status,
            processed_items=job.processed_items,
            new_members=job.new_members,
            created_at=job.created_at,
            finished_at=job.finished_at,
        )
        for job, title in rows
    ]


@router.get("/parse-jobs/{job_id}", response_model=ParseJobRead)
async def get_parse_job(job_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ParseJob).where(ParseJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job не найден")
    return job


@router.get("/parse-jobs/{job_id}/progress", response_model=ParseJobProgress)
async def get_parse_progress(job_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ParseJob.processed_items, ParseJob.new_members, ParseJob.skipped_members,
               ParseJob.status, ParseJob.total_items, ParseJob.error_message)
        .where(ParseJob.id == job_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Job не найден")
    return ParseJobProgress(
        id=job_id,
        status=row[3],
        processed_items=row[0],
        new_members=row[1],
        skipped_members=row[2],
        total_items=row[4],
        error_message=row[5],
    )


# ---------- MEMBERS ----------

def _build_members_query(filters: MemberFilters, db: AsyncSession):
    q = (
        select(AudienceMember)
        .options(selectinload(AudienceMember.sources).selectinload(SourceMember.source))
    )

    if filters.source_ids:
        q = q.join(SourceMember).where(SourceMember.source_id.in_(filters.source_ids))

    if filters.has_username is not None:
        q = q.where(
            AudienceMember.username.isnot(None) if filters.has_username
            else AudienceMember.username.is_(None)
        )

    if filters.has_phone is not None:
        q = q.where(AudienceMember.has_phone == filters.has_phone)

    if filters.has_bio is not None:
        q = q.where(
            AudienceMember.bio.isnot(None) if filters.has_bio
            else AudienceMember.bio.is_(None)
        )

    if filters.is_bot is not None:
        q = q.where(AudienceMember.is_bot == filters.is_bot)

    if filters.is_verified is not None:
        q = q.where(AudienceMember.is_verified == filters.is_verified)

    if filters.is_deleted is not None:
        q = q.where(AudienceMember.is_deleted == filters.is_deleted)

    if filters.activity:
        q = q.where(AudienceMember.last_seen_bucket.in_(filters.activity))

    if filters.lang_codes:
        q = q.where(AudienceMember.lang_code.in_(filters.lang_codes))

    if filters.countries:
        q = q.where(AudienceMember.country_code.in_(filters.countries))

    if filters.sources_count_min is not None:
        q = q.where(AudienceMember.sources_count >= filters.sources_count_min)

    if filters.sources_count_max is not None:
        q = q.where(AudienceMember.sources_count <= filters.sources_count_max)

    if filters.search:
        search_term = f"%{filters.search}%"
        q = q.where(
            or_(
                AudienceMember.username.ilike(search_term),
                AudienceMember.first_name.ilike(search_term),
                AudienceMember.bio.ilike(search_term),
            )
        )

    return q


@router.post("/members", response_model=list[AudienceMemberRead])
async def list_members(
    filters: MemberFilters,
    db: AsyncSession = Depends(get_db),
):
    q = _build_members_query(filters, db)
    q = q.order_by(AudienceMember.id.desc()).offset(filters.offset).limit(filters.limit)
    result = await db.execute(q)
    members = result.scalars().all()

    return [
        AudienceMemberRead(
            id=m.id,
            telegram_id=m.telegram_id,
            username=m.username,
            first_name=m.first_name,
            last_name=m.last_name,
            phone=m.phone,
            bio=m.bio,
            lang_code=m.lang_code,
            country_code=m.country_code,
            is_bot=m.is_bot,
            is_verified=m.is_verified,
            is_scam=m.is_scam,
            is_fake=m.is_fake,
            is_deleted=m.is_deleted,
            has_photo=m.has_photo,
            has_phone=m.has_phone,
            last_seen_bucket=m.last_seen_bucket,
            last_seen_at=m.last_seen_at,
            account_created_at=m.account_created_at,
            sources_count=m.sources_count,
            sources=[sm.source.title for sm in m.sources if sm.source],
            created_at=m.created_at,
        )
        for m in members
    ]


@router.get("/members/count")
async def count_members(
    db: AsyncSession = Depends(get_db),
    source_ids: Optional[str] = Query(None, alias="source_ids"),
    activity: Optional[str] = Query(None, alias="activity"),
    lang_codes: Optional[str] = Query(None, alias="lang_codes"),
):
    q = select(func.count(AudienceMember.id))
    if source_ids:
        ids = [int(x) for x in source_ids.split(",")]
        q = q.join(SourceMember).where(SourceMember.source_id.in_(ids))
    if activity:
        buckets = activity.split(",")
        q = q.where(AudienceMember.last_seen_bucket.in_(buckets))
    if lang_codes:
        langs = lang_codes.split(",")
        q = q.where(AudienceMember.lang_code.in_(langs))
    result = await db.execute(q)
    return {"count": result.scalar()}


@router.post("/members/export")
async def export_members(
    payload: MemberExportRequest,
    db: AsyncSession = Depends(get_db),
):
    q = _build_members_query(payload.filters, db)
    result = await db.execute(q)
    members = result.scalars().all()

    default_cols = ["username", "first_name", "last_name", "phone", "lang_code", "last_seen_bucket"]
    cols = payload.include_columns or default_cols

    output = io.StringIO()

    if payload.format == "csv":
        writer = csv.writer(output)
        writer.writerow(cols)
        for m in members:
            row = []
            for col in cols:
                if col == "username":
                    row.append(m.username or "")
                elif col == "first_name":
                    row.append(m.first_name or "")
                elif col == "last_name":
                    row.append(m.last_name or "")
                elif col == "phone":
                    row.append(m.phone or "")
                elif col == "lang_code":
                    row.append(m.lang_code or "")
                elif col == "bio":
                    row.append(m.bio or "")
                elif col == "last_seen_bucket":
                    row.append(m.last_seen_bucket)
                elif col == "last_seen":
                    row.append(m.last_seen_at.isoformat() if m.last_seen_at else "")
                elif col == "sources_count":
                    row.append(m.sources_count)
                elif col == "is_bot":
                    row.append(m.is_bot)
                else:
                    row.append("")
            writer.writerow(row)
        output.seek(0)
        media_type = "text/csv"
        filename = "audience_export.csv"

    elif payload.format == "txt":
        for m in members:
            if m.username:
                output.write(f"@{m.username}\n")
            elif m.phone:
                output.write(f"{m.phone}\n")
        output.seek(0)
        media_type = "text/plain"
        filename = "usernames.txt"

    elif payload.format == "phones":
        for m in members:
            if m.phone:
                output.write(f"{m.phone}\n")
        output.seek(0)
        media_type = "text/plain"
        filename = "phones.txt"

    elif payload.format == "json":
        import json
        data = []
        for m in members:
            item = {}
            for col in cols:
                if hasattr(m, col):
                    v = getattr(m, col)
                    if isinstance(v, datetime):
                        v = v.isoformat()
                    item[col] = v
            data.append(item)
        output.write(json.dumps(data, ensure_ascii=False, indent=2))
        output.seek(0)
        media_type = "application/json"
        filename = "audience_export.json"

    else:
        raise HTTPException(status_code=400, detail="Неподдерживаемый формат")

    return StreamingResponse(
        output,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------- SEGMENTS ----------

@router.post("/segments", response_model=SegmentRead)
async def create_segment(payload: SegmentCreate, db: AsyncSession = Depends(get_db)):
    filters_dict = payload.filters or {}
    if payload.source_ids:
        filters_dict["source_ids"] = payload.source_ids

    count_q = select(func.count(AudienceMember.id))
    if payload.source_ids:
        count_q = count_q.join(SourceMember).where(SourceMember.source_id.in_(payload.source_ids))

    count_result = await db.execute(count_q)
    member_count = count_result.scalar() or 0

    segment = AudienceSegment(
        name=payload.name,
        description=payload.description,
        filters=filters_dict,
        source_ids=payload.source_ids,
        member_count=member_count,
    )
    db.add(segment)
    await db.commit()
    await db.refresh(segment)
    return segment


@router.get("/segments", response_model=list[SegmentRead])
async def list_segments(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AudienceSegment).order_by(AudienceSegment.created_at.desc()))
    return result.scalars().all()


@router.get("/segments/{segment_id}", response_model=SegmentRead)
async def get_segment(segment_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AudienceSegment).where(AudienceSegment.id == segment_id))
    segment = result.scalar_one_or_none()
    if not segment:
        raise HTTPException(status_code=404, detail="Сегмент не найден")
    return segment


@router.delete("/segments/{segment_id}")
async def delete_segment(segment_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AudienceSegment).where(AudienceSegment.id == segment_id))
    segment = result.scalar_one_or_none()
    if not segment:
        raise HTTPException(status_code=404, detail="Сегмент не найден")
    await db.delete(segment)
    await db.commit()
    return {"status": "deleted"}


# ---------- EXCLUSIONS ----------

@router.post("/exclusions", response_model=dict)
async def add_exclusion(payload: ExclusionCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(
        select(MemberExclusion).where(MemberExclusion.member_id == payload.member_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Участник уже в исключениях")

    exc = MemberExclusion(member_id=payload.member_id, reason=payload.reason)
    db.add(exc)
    await db.commit()
    return {"status": "added"}


@router.post("/exclusions/by-username", response_model=dict)
async def add_exclusions_by_username(payload: ExclusionByUsername, db: AsyncSession = Depends(get_db)):
    added = 0
    for username in payload.usernames:
        clean = username.lstrip("@").strip()
        result = await db.execute(
            select(AudienceMember).where(AudienceMember.username == clean)
        )
        member = result.scalar_one_or_none()
        if member:
            existing = await db.execute(
                select(MemberExclusion).where(MemberExclusion.member_id == member.id)
            )
            if not existing.scalar_one_or_none():
                exc = MemberExclusion(
                    member_id=member.id,
                    reason=payload.reason,
                    telegram_id=member.telegram_id,
                    username=member.username,
                    first_name=member.first_name,
                )
                db.add(exc)
                added += 1

    await db.commit()
    return {"added": added}


@router.get("/exclusions", response_model=list[dict])
async def list_exclusions(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(100, le=500),
):
    result = await db.execute(
        select(MemberExclusion)
        .order_by(MemberExclusion.excluded_at.desc())
        .limit(limit)
    )
    exclusions = result.scalars().all()
    return [
        {
            "id": e.id,
            "member_id": e.member_id,
            "username": e.username,
            "first_name": e.first_name,
            "reason": e.reason,
            "excluded_at": e.excluded_at,
        }
        for e in exclusions
    ]


@router.delete("/exclusions/{exclusion_id}")
async def remove_exclusion(exclusion_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MemberExclusion).where(MemberExclusion.id == exclusion_id))
    exc = result.scalar_one_or_none()
    if not exc:
        raise HTTPException(status_code=404, detail="Исключение не найдено")
    await db.delete(exc)
    await db.commit()
    return {"status": "removed"}


# ---------- ANALYTICS ----------

@router.get("/analytics/overview", response_model=AnalyticsOverview)
async def analytics_overview(db: AsyncSession = Depends(get_db)):
    total_members = await db.scalar(select(func.count(AudienceMember.id))) or 0
    total_sources = await db.scalar(select(func.count(AudienceSource.id))) or 0

    with_usernames = await db.scalar(
        select(func.count(AudienceMember.id)).where(AudienceMember.username.isnot(None))
    ) or 0

    with_phones = await db.scalar(
        select(func.count(AudienceMember.id)).where(AudienceMember.has_phone == True)
    ) or 0

    with_bio = await db.scalar(
        select(func.count(AudienceMember.id)).where(AudienceMember.bio.isnot(None))
    ) or 0

    active_week = await db.scalar(
        select(func.count(AudienceMember.id)).where(
            AudienceMember.last_seen_bucket.in_([
                LastSeenBucket.online.value,
                LastSeenBucket.day.value,
                LastSeenBucket.week.value,
            ])
        )
    ) or 0

    active_month = await db.scalar(
        select(func.count(AudienceMember.id)).where(
            AudienceMember.last_seen_bucket.in_([
                LastSeenBucket.online.value,
                LastSeenBucket.day.value,
                LastSeenBucket.week.value,
                LastSeenBucket.month.value,
            ])
        )
    ) or 0

    bots_count = await db.scalar(
        select(func.count(AudienceMember.id)).where(AudienceMember.is_bot == True)
    ) or 0

    lang_count = await db.scalar(
        select(func.count(func.distinct(AudienceMember.lang_code)))
        .where(AudienceMember.lang_code.isnot(None))
    ) or 0

    sources_result = await db.execute(
        select(AudienceSource.title, func.count(SourceMember.id))
        .join(SourceMember, SourceMember.source_id == AudienceSource.id)
        .group_by(AudienceSource.id, AudienceSource.title)
        .order_by(func.count(SourceMember.id).desc())
        .limit(5)
    )
    top_sources = [{"title": r[0], "members": r[1]} for r in sources_result.all()]

    lang_result = await db.execute(
        select(AudienceMember.lang_code, func.count(AudienceMember.id))
        .where(AudienceMember.lang_code.isnot(None))
        .group_by(AudienceMember.lang_code)
        .order_by(func.count(AudienceMember.id).desc())
        .limit(10)
    )
    top_languages = [{row[0]: row[1]} for row in lang_result.all()]

    return AnalyticsOverview(
        total_sources=total_sources,
        total_members=total_members,
        members_with_usernames=with_usernames,
        members_with_phones=with_phones,
        members_with_bio=with_bio,
        active_last_week=active_week,
        active_last_month=active_month,
        bots_count=bots_count,
        unique_languages=lang_count,
        top_sources=top_sources,
        top_languages=top_languages,
    )


@router.get("/analytics/overlap/{source_a_id}/{source_b_id}", response_model=SourceOverlap)
async def source_overlap(
    source_a_id: int,
    source_b_id: int,
    db: AsyncSession = Depends(get_db),
):
    sa_result = await db.execute(select(AudienceSource).where(AudienceSource.id == source_a_id))
    sa = sa_result.scalar_one_or_none()
    if not sa:
        raise HTTPException(status_code=404, detail="Источник A не найден")

    sb_result = await db.execute(select(AudienceSource).where(AudienceSource.id == source_b_id))
    sb = sb_result.scalar_one_or_none()
    if not sb:
        raise HTTPException(status_code=404, detail="Источник B не найден")

    total_a = await db.scalar(
        select(func.count(SourceMember.id)).where(SourceMember.source_id == source_a_id)
    ) or 0
    total_b = await db.scalar(
        select(func.count(SourceMember.id)).where(SourceMember.source_id == source_b_id)
    ) or 0

    intersection = await db.scalar(
        select(func.count(SourceMember.member_id))
        .where(
            and_(
                SourceMember.source_id == source_a_id,
                SourceMember.member_id.in_(
                    select(SourceMember.member_id).where(SourceMember.source_id == source_b_id)
                ),
            )
        )
    ) or 0

    return SourceOverlap(
        source_a_id=source_a_id,
        source_b_id=source_b_id,
        source_a_title=sa.title,
        source_b_title=sb.title,
        intersection_count=intersection,
        intersection_percent_a=round(intersection / total_a * 100, 1) if total_a else 0,
        intersection_percent_b=round(intersection / total_b * 100, 1) if total_b else 0,
    )


@router.get("/analytics/activity", response_model=list[ActivityStats])
async def activity_stats(
    db: AsyncSession = Depends(get_db),
    source_id: Optional[int] = Query(None, alias="source_id"),
    days: int = Query(30, ge=7, le=90),
):
    q = (
        select(
            func.date(SourceMember.parsed_at).label("date"),
            func.count(func.distinct(SourceMember.member_id)).label("members"),
        )
        .where(SourceMember.parsed_at.isnot(None))
    )
    if source_id:
        q = q.where(SourceMember.source_id == source_id)

    q = q.group_by(text("date")).order_by(text("date")).limit(days)

    result = await db.execute(q)
    rows = result.all()

    if not rows:
        return []

    return [
        ActivityStats(
            date=str(row[0]),
            new_members=row[1],
            active_members=row[1],
        )
        for row in rows
    ]
