from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.audience import (
    AudienceMember,
    AudienceSource,
    ParseJob,
    ParseJobStatus,
    SourceMember,
)
from app.schemas.audience import (
    AudienceMembersFilter,
    AudienceMemberRead,
    AudienceSourceCreate,
    AudienceSourceRead,
    ParseJobCreate,
    ParseJobProgress,
    ParseJobRead,
)
from app.services.telegram_parser import run_parse_job_blocking

import csv
import io
from typing import List


router = APIRouter(prefix="/audience", tags=["audience"])


# ---------- SOURCES ----------

@router.post("/sources", response_model=AudienceSourceRead)
def create_source(
    payload: AudienceSourceCreate,
    db: Session = Depends(get_db),
):
    # минимальная валидация
    if not payload.username:
        raise HTTPException(status_code=400, detail="username is required for now")

    source = AudienceSource(
        type=payload.type,
        username=payload.username,
        title=payload.title,
        description=payload.description,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


@router.get("/sources", response_model=List[AudienceSourceRead])
def list_sources(db: Session = Depends(get_db)):
    sources = db.query(AudienceSource).order_by(AudienceSource.created_at.desc()).all()
    return sources


# ---------- PARSE JOBS ----------

@router.post("/parse-jobs", response_model=ParseJobRead)
def create_parse_job(
    payload: ParseJobCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    source = db.query(AudienceSource).filter(AudienceSource.id == payload.source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    job = ParseJob(
        source_id=payload.source_id,
        mode=payload.mode,
        status=ParseJobStatus.pending,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # запускаем фоновой процесс
    background_tasks.add_task(run_parse_job_blocking, db, job.id)

    return job


@router.get("/parse-jobs/{job_id}", response_model=ParseJobProgress)
def get_parse_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(ParseJob).filter(ParseJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


# ---------- MEMBERS ----------

@router.post("/members", response_model=List[AudienceMemberRead])
def list_members(
    filters: AudienceMembersFilter,
    db: Session = Depends(get_db),
):
    q = db.query(AudienceMember)

    if filters.source_ids:
        q = (
            q.join(SourceMember)
            .filter(SourceMember.source_id.in_(filters.source_ids))
        )

    if filters.has_username is True:
        q = q.filter(AudienceMember.username.isnot(None))
    elif filters.has_username is False:
        q = q.filter(AudienceMember.username.is_(None))

    if filters.is_bot is not None:
        q = q.filter(AudienceMember.is_bot == filters.is_bot)

    if filters.activity:
        q = q.filter(AudienceMember.last_seen_bucket.in_(filters.activity))

    q = q.order_by(AudienceMember.id.desc())
    q = q.offset(filters.offset).limit(filters.limit)

    members = q.all()
    return members


@router.post("/members/export")
def export_members(
    filters: AudienceMembersFilter,
    db: Session = Depends(get_db),
):
    q = db.query(AudienceMember)

    if filters.source_ids:
        q = (
            q.join(SourceMember)
            .filter(SourceMember.source_id.in_(filters.source_ids))
        )

    if filters.has_username is True:
        q = q.filter(AudienceMember.username.isnot(None))
    elif filters.has_username is False:
        q = q.filter(AudienceMember.username.is_(None))

    if filters.is_bot is not None:
        q = q.filter(AudienceMember.is_bot == filters.is_bot)

    if filters.activity:
        q = q.filter(AudienceMember.last_seen_bucket.in_(filters.activity))

    members = q.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "id",
            "telegram_id",
            "username",
            "first_name",
            "last_name",
            "lang_code",
            "is_bot",
            "last_seen_bucket",
            "last_seen_at",
        ]
    )
    for m in members:
        writer.writerow(
            [
                m.id,
                m.telegram_id,
                m.username or "",
                m.first_name or "",
                m.last_name or "",
                m.lang_code or "",
                m.is_bot,
                m.last_seen_bucket.value,
                m.last_seen_at.isoformat() if m.last_seen_at else "",
            ]
        )

    output.seek(0)
    headers = {
        "Content-Disposition": 'attachment; filename="audience_export.csv"'
    }
    return StreamingResponse(
        output, media_type="text/csv", headers=headers
    )
