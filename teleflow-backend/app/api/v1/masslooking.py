from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.masslooking import MasslookingJob, MasslookingLog, MasslookingStatus, MasslookingSource
from app.models.account import Account
from app.schemas.masslooking import (
    MasslookingJobCreate,
    MasslookingJobUpdate,
    MasslookingJobRead,
    MasslookingJobList,
    MasslookingProgress,
    MasslookingLogRead,
    MasslookingStats,
)

router = APIRouter(prefix="/api/v1/masslooking", tags=["masslooking"])


@router.post("/jobs", response_model=MasslookingJobRead)
async def create_masslooking_job(
    payload: MasslookingJobCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    if payload.account_id:
        result = await db.execute(select(Account).where(Account.id == payload.account_id))
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Аккаунт не найден")

    job = MasslookingJob(
        name=payload.name,
        account_id=payload.account_id,
        source_type=payload.source_type.value,
        source_ids=payload.source_ids,
        custom_usernames=payload.custom_usernames,
        mode=payload.mode.value,
        status=MasslookingStatus.pending.value,
        delay_min_ms=payload.delay_min_ms,
        delay_max_ms=payload.delay_max_ms,
        limit_users=payload.limit_users,
        skip_bots=payload.skip_bots,
        skip_no_stories=payload.skip_no_stories,
        lang_codes=payload.lang_codes,
        activity_filter=payload.activity_filter,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    job_id = job.id

    def run_job():
        from app.core.database import sync_session_maker
        with sync_session_maker() as s:
            from app.services.masslooking_service import run_masslooking_job_sync
            run_masslooking_job_sync(s, job_id)

    background_tasks.add_task(run_job)

    return job


@router.get("/jobs", response_model=list[MasslookingJobList])
async def list_masslooking_jobs(
    db: AsyncSession = Depends(get_db),
    status: Optional[str] = Query(None),
    limit: int = Query(20, le=100),
):
    query = (
        select(MasslookingJob, Account.phone)
        .outerjoin(Account, MasslookingJob.account_id == Account.id)
        .options(selectinload(MasslookingJob.account))
        .order_by(MasslookingJob.created_at.desc())
        .limit(limit)
    )
    if status:
        query = query.where(MasslookingJob.status == status)

    result = await db.execute(query)
    rows = result.all()
    return [
        MasslookingJobList(
            id=job.id,
            name=job.name,
            account_id=job.account_id,
            account_phone=phone,
            source_type=job.source_type,
            mode=job.mode,
            status=job.status,
            total_users=job.total_users,
            processed_users=job.processed_users,
            stories_watched=job.stories_watched,
            users_with_stories=job.users_with_stories,
            errors_count=job.errors_count,
            created_at=job.created_at,
            started_at=job.started_at,
            finished_at=job.finished_at,
            error_message=job.error_message,
        )
        for job, phone in rows
    ]


@router.get("/jobs/stats", response_model=MasslookingStats)
async def get_masslooking_stats(db: AsyncSession = Depends(get_db)):
    total = await db.scalar(select(func.count(MasslookingJob.id))) or 0

    running = await db.scalar(
        select(func.count(MasslookingJob.id))
        .where(MasslookingJob.status == MasslookingStatus.running.value)
    ) or 0

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    completed_today = await db.scalar(
        select(func.count(MasslookingJob.id))
        .where(
            and_(
                MasslookingJob.status == MasslookingStatus.completed.value,
                MasslookingJob.finished_at >= today_start,
            )
        )
    ) or 0

    total_stories = await db.scalar(
        select(func.sum(MasslookingJob.stories_watched))
    ) or 0

    total_processed = await db.scalar(
        select(func.sum(MasslookingJob.processed_users))
    ) or 0

    total_errors = await db.scalar(
        select(func.sum(MasslookingJob.errors_count))
    ) or 0

    return MasslookingStats(
        total_jobs=total,
        running_jobs=running,
        completed_today=completed_today,
        total_stories_watched=total_stories or 0,
        total_users_processed=total_processed or 0,
        total_errors=total_errors or 0,
    )


@router.get("/jobs/{job_id}", response_model=MasslookingJobRead)
async def get_masslooking_job(job_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(MasslookingJob).where(MasslookingJob.id == job_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return job


@router.get("/jobs/{job_id}/progress", response_model=MasslookingProgress)
async def get_masslooking_progress(job_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(
            MasslookingJob.status,
            MasslookingJob.processed_users,
            MasslookingJob.total_users,
            MasslookingJob.stories_watched,
            MasslookingJob.users_with_stories,
            MasslookingJob.users_skipped,
            MasslookingJob.errors_count,
            MasslookingJob.error_message,
        ).where(MasslookingJob.id == job_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return MasslookingProgress(
        id=job_id,
        status=row[0],
        processed_users=row[1],
        total_users=row[2],
        stories_watched=row[3],
        users_with_stories=row[4],
        users_skipped=row[5],
        errors_count=row[6],
        error_message=row[7],
    )


@router.patch("/jobs/{job_id}", response_model=MasslookingJobRead)
async def update_masslooking_job(
    job_id: int,
    payload: MasslookingJobUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(MasslookingJob).where(MasslookingJob.id == job_id))
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
async def pause_masslooking_job(job_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MasslookingJob).where(MasslookingJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    if job.status != MasslookingStatus.running.value:
        raise HTTPException(status_code=400, detail="Можно приостановить только выполняющуюся задачу")
    job.status = MasslookingStatus.paused.value
    await db.commit()
    return {"status": "paused", "id": job_id}


@router.post("/jobs/{job_id}/resume")
async def resume_masslooking_job(job_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MasslookingJob).where(MasslookingJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    if job.status != MasslookingStatus.paused.value:
        raise HTTPException(status_code=400, detail="Можно продолжить только приостановленную задачу")
    job.status = MasslookingStatus.running.value
    await db.commit()
    return {"status": "running", "id": job_id}


@router.post("/jobs/{job_id}/cancel")
async def cancel_masslooking_job(job_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MasslookingJob).where(MasslookingJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    if job.status not in (MasslookingStatus.running.value, MasslookingStatus.paused.value, MasslookingStatus.pending.value):
        raise HTTPException(status_code=400, detail="Нельзя отменить завершённую задачу")
    job.status = MasslookingStatus.cancelled.value
    await db.commit()
    return {"status": "cancelled", "id": job_id}


@router.delete("/jobs/{job_id}")
async def delete_masslooking_job(job_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MasslookingJob).where(MasslookingJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    await db.delete(job)
    await db.commit()
    return {"status": "deleted", "id": job_id}


@router.post("/jobs/bulk-delete")
async def bulk_delete_masslooking_jobs(
    job_ids: list[int],
    db: AsyncSession = Depends(get_db),
):
    if not job_ids:
        raise HTTPException(status_code=400, detail="Укажите job_ids")

    result = await db.execute(
        select(MasslookingJob).where(MasslookingJob.id.in_(job_ids))
    )
    jobs = result.scalars().all()
    count = len(jobs)
    for job in jobs:
        await db.delete(job)
    await db.commit()
    return {"deleted": count}


@router.get("/jobs/{job_id}/logs", response_model=list[MasslookingLogRead])
async def get_job_logs(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(100, le=500),
):
    result_job = await db.execute(
        select(MasslookingJob).where(MasslookingJob.id == job_id)
    )
    if not result_job.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Задача не найдена")

    result = await db.execute(
        select(MasslookingLog)
        .where(MasslookingLog.job_id == job_id)
        .order_by(MasslookingLog.timestamp.desc())
        .limit(limit)
    )
    return result.scalars().all()
