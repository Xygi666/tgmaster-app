from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.tagging import TaggingJob, TaggingLog, TaggingStatus, TaggingSource
from app.models.account import Account
from app.schemas.tagging import (
    TaggingJobCreate,
    TaggingJobUpdate,
    TaggingJobRead,
    TaggingJobList,
    TaggingProgress,
    TaggingLogRead,
    TaggingStats,
)

router = APIRouter(prefix="/api/v1/tagging", tags=["tagging"])


@router.post("/jobs", response_model=TaggingJobRead)
async def create_tagging_job(
    payload: TaggingJobCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    if payload.account_id:
        result = await db.execute(select(Account).where(Account.id == payload.account_id))
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Аккаунт не найден")

    job = TaggingJob(
        name=payload.name,
        account_id=payload.account_id,
        target_link=payload.target_link,
        template=payload.template,
        source_type=payload.source_type.value,
        source_ids=payload.source_ids,
        custom_usernames=payload.custom_usernames,
        mode=payload.mode.value,
        status=TaggingStatus.pending.value,
        delay_min_ms=payload.delay_min_ms,
        delay_max_ms=payload.delay_max_ms,
        limit_users=payload.limit_users,
        batch_size=payload.batch_size,
        skip_no_username=payload.skip_no_username,
        lang_codes=payload.lang_codes,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    job_id = job.id

    def run_job():
        from app.core.database import sync_session_maker
        with sync_session_maker() as s:
            from app.services.tagging_service import run_tagging_job_sync
            run_tagging_job_sync(s, job_id)

    background_tasks.add_task(run_job)

    return job


@router.get("/jobs", response_model=list[TaggingJobList])
async def list_tagging_jobs(
    db: AsyncSession = Depends(get_db),
    status: Optional[str] = Query(None),
    limit: int = Query(20, le=100),
):
    query = (
        select(TaggingJob, Account.phone)
        .outerjoin(Account, TaggingJob.account_id == Account.id)
        .order_by(TaggingJob.created_at.desc())
        .limit(limit)
    )
    if status:
        query = query.where(TaggingJob.status == status)

    result = await db.execute(query)
    rows = result.all()
    return [
        TaggingJobList(
            id=job.id,
            name=job.name,
            account_id=job.account_id,
            account_phone=phone,
            target_title=job.target_title or job.target_link,
            template=job.template,
            source_type=job.source_type,
            mode=job.mode,
            status=job.status,
            total_users=job.total_users,
            processed_users=job.processed_users,
            tagged_users=job.tagged_users,
            errors_count=job.errors_count,
            created_at=job.created_at,
            started_at=job.started_at,
            finished_at=job.finished_at,
            error_message=job.error_message,
        )
        for job, phone in rows
    ]


@router.get("/jobs/stats", response_model=TaggingStats)
async def get_tagging_stats(db: AsyncSession = Depends(get_db)):
    total = await db.scalar(select(func.count(TaggingJob.id))) or 0

    running = await db.scalar(
        select(func.count(TaggingJob.id))
        .where(TaggingJob.status == TaggingStatus.running.value)
    ) or 0

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    completed_today = await db.scalar(
        select(func.count(TaggingJob.id))
        .where(
            and_(
                TaggingJob.status == TaggingStatus.completed.value,
                TaggingJob.finished_at >= today_start,
            )
        )
    ) or 0

    total_tagged = await db.scalar(select(func.sum(TaggingJob.tagged_users))) or 0
    total_errors = await db.scalar(select(func.sum(TaggingJob.errors_count))) or 0

    return TaggingStats(
        total_jobs=total,
        running_jobs=running,
        completed_today=completed_today,
        total_tagged=total_tagged or 0,
        total_errors=total_errors or 0,
    )


@router.get("/jobs/{job_id}", response_model=TaggingJobRead)
async def get_tagging_job(job_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TaggingJob).where(TaggingJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return job


@router.get("/jobs/{job_id}/progress", response_model=TaggingProgress)
async def get_tagging_progress(job_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(
            TaggingJob.status,
            TaggingJob.processed_users,
            TaggingJob.total_users,
            TaggingJob.tagged_users,
            TaggingJob.skipped,
            TaggingJob.errors_count,
            TaggingJob.error_message,
        ).where(TaggingJob.id == job_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return TaggingProgress(
        id=job_id,
        status=row[0],
        processed_users=row[1],
        total_users=row[2],
        tagged_users=row[3],
        skipped=row[4],
        errors_count=row[5],
        error_message=row[6],
    )


@router.patch("/jobs/{job_id}", response_model=TaggingJobRead)
async def update_tagging_job(
    job_id: int,
    payload: TaggingJobUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(TaggingJob).where(TaggingJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    if payload.name is not None:
        job.name = payload.name
    if payload.delay_min_ms is not None:
        job.delay_min_ms = payload.delay_min_ms
    if payload.delay_max_ms is not None:
        job.delay_max_ms = payload.delay_max_ms
    if payload.limit_users is not None:
        job.limit_users = payload.limit_users

    await db.commit()
    await db.refresh(job)
    return job


@router.post("/jobs/{job_id}/pause")
async def pause_tagging_job(job_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TaggingJob).where(TaggingJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    if job.status != TaggingStatus.running.value:
        raise HTTPException(status_code=400, detail="Можно приостановить только выполняющуюся задачу")
    job.status = TaggingStatus.paused.value
    await db.commit()
    return {"status": "paused", "id": job_id}


@router.post("/jobs/{job_id}/resume")
async def resume_tagging_job(job_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TaggingJob).where(TaggingJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    if job.status != TaggingStatus.paused.value:
        raise HTTPException(status_code=400, detail="Можно продолжить только приостановленную задачу")
    job.status = TaggingStatus.running.value
    await db.commit()
    return {"status": "running", "id": job_id}


@router.post("/jobs/{job_id}/cancel")
async def cancel_tagging_job(job_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TaggingJob).where(TaggingJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    if job.status not in (
        TaggingStatus.running.value, TaggingStatus.paused.value, TaggingStatus.pending.value
    ):
        raise HTTPException(status_code=400, detail="Нельзя отменить завершённую задачу")
    job.status = TaggingStatus.cancelled.value
    await db.commit()
    return {"status": "cancelled", "id": job_id}


@router.delete("/jobs/{job_id}")
async def delete_tagging_job(job_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TaggingJob).where(TaggingJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    await db.delete(job)
    await db.commit()
    return {"status": "deleted", "id": job_id}


@router.get("/jobs/{job_id}/logs", response_model=list[TaggingLogRead])
async def get_tagging_job_logs(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(100, le=500),
):
    result_job = await db.execute(select(TaggingJob).where(TaggingJob.id == job_id))
    if not result_job.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Задача не найдена")

    result = await db.execute(
        select(TaggingLog)
        .where(TaggingLog.job_id == job_id)
        .order_by(TaggingLog.timestamp.desc())
        .limit(limit)
    )
    return result.scalars().all()
