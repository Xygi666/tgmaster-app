from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.inviting import InvitingJob, InvitingLog, InvitingStatus, InvitingSource
from app.models.account import Account
from app.schemas.inviting import (
    InvitingJobCreate,
    InvitingJobUpdate,
    InvitingJobRead,
    InvitingJobList,
    InvitingProgress,
    InvitingLogRead,
    InvitingStats,
)

router = APIRouter(prefix="/api/v1/inviting", tags=["inviting"])


@router.post("/jobs", response_model=InvitingJobRead)
async def create_inviting_job(
    payload: InvitingJobCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    if payload.account_id:
        result = await db.execute(select(Account).where(Account.id == payload.account_id))
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Аккаунт не найден")

    job = InvitingJob(
        name=payload.name,
        account_id=payload.account_id,
        target_link=payload.target_link,
        source_type=payload.source_type.value,
        source_ids=payload.source_ids,
        custom_usernames=payload.custom_usernames,
        mode=payload.mode.value,
        status=InvitingStatus.pending.value,
        delay_min_ms=payload.delay_min_ms,
        delay_max_ms=payload.delay_max_ms,
        limit_users=payload.limit_users,
        skip_already_in=payload.skip_already_in,
        skip_bots=payload.skip_bots,
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
            from app.services.inviting_service import run_inviting_job_sync
            run_inviting_job_sync(s, job_id)

    background_tasks.add_task(run_job)

    return job


@router.get("/jobs", response_model=list[InvitingJobList])
async def list_inviting_jobs(
    db: AsyncSession = Depends(get_db),
    status: Optional[str] = Query(None),
    limit: int = Query(20, le=100),
):
    query = (
        select(InvitingJob, Account.phone)
        .outerjoin(Account, InvitingJob.account_id == Account.id)
        .order_by(InvitingJob.created_at.desc())
        .limit(limit)
    )
    if status:
        query = query.where(InvitingJob.status == status)

    result = await db.execute(query)
    rows = result.all()
    return [
        InvitingJobList(
            id=job.id,
            name=job.name,
            account_id=job.account_id,
            account_phone=phone,
            target_title=job.target_title or job.target_link,
            source_type=job.source_type,
            mode=job.mode,
            status=job.status,
            total_users=job.total_users,
            processed_users=job.processed_users,
            invited_users=job.invited_users,
            errors_count=job.errors_count,
            created_at=job.created_at,
            started_at=job.started_at,
            finished_at=job.finished_at,
            error_message=job.error_message,
        )
        for job, phone in rows
    ]


@router.get("/jobs/stats", response_model=InvitingStats)
async def get_inviting_stats(db: AsyncSession = Depends(get_db)):
    total = await db.scalar(select(func.count(InvitingJob.id))) or 0

    running = await db.scalar(
        select(func.count(InvitingJob.id))
        .where(InvitingJob.status == InvitingStatus.running.value)
    ) or 0

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    completed_today = await db.scalar(
        select(func.count(InvitingJob.id))
        .where(
            and_(
                InvitingJob.status == InvitingStatus.completed.value,
                InvitingJob.finished_at >= today_start,
            )
        )
    ) or 0

    total_invited = await db.scalar(select(func.sum(InvitingJob.invited_users))) or 0
    total_errors = await db.scalar(select(func.sum(InvitingJob.errors_count))) or 0

    return InvitingStats(
        total_jobs=total,
        running_jobs=running,
        completed_today=completed_today,
        total_invited=total_invited or 0,
        total_errors=total_errors or 0,
    )


@router.get("/jobs/{job_id}", response_model=InvitingJobRead)
async def get_inviting_job(job_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(InvitingJob).where(InvitingJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return job


@router.get("/jobs/{job_id}/progress", response_model=InvitingProgress)
async def get_inviting_progress(job_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(
            InvitingJob.status,
            InvitingJob.processed_users,
            InvitingJob.total_users,
            InvitingJob.invited_users,
            InvitingJob.already_in,
            InvitingJob.skipped,
            InvitingJob.errors_count,
            InvitingJob.error_message,
        ).where(InvitingJob.id == job_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return InvitingProgress(
        id=job_id,
        status=row[0],
        processed_users=row[1],
        total_users=row[2],
        invited_users=row[3],
        already_in=row[4],
        skipped=row[5],
        errors_count=row[6],
        error_message=row[7],
    )


@router.patch("/jobs/{job_id}", response_model=InvitingJobRead)
async def update_inviting_job(
    job_id: int,
    payload: InvitingJobUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(InvitingJob).where(InvitingJob.id == job_id))
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
async def pause_inviting_job(job_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(InvitingJob).where(InvitingJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    if job.status != InvitingStatus.running.value:
        raise HTTPException(status_code=400, detail="Можно приостановить только выполняющуюся задачу")
    job.status = InvitingStatus.paused.value
    await db.commit()
    return {"status": "paused", "id": job_id}


@router.post("/jobs/{job_id}/resume")
async def resume_inviting_job(job_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(InvitingJob).where(InvitingJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    if job.status != InvitingStatus.paused.value:
        raise HTTPException(status_code=400, detail="Можно продолжить только приостановленную задачу")
    job.status = InvitingStatus.running.value
    await db.commit()
    return {"status": "running", "id": job_id}


@router.post("/jobs/{job_id}/cancel")
async def cancel_inviting_job(job_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(InvitingJob).where(InvitingJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    if job.status not in (
        InvitingStatus.running.value, InvitingStatus.paused.value, InvitingStatus.pending.value
    ):
        raise HTTPException(status_code=400, detail="Нельзя отменить завершённую задачу")
    job.status = InvitingStatus.cancelled.value
    await db.commit()
    return {"status": "cancelled", "id": job_id}


@router.delete("/jobs/{job_id}")
async def delete_inviting_job(job_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(InvitingJob).where(InvitingJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    await db.delete(job)
    await db.commit()
    return {"status": "deleted", "id": job_id}


@router.get("/jobs/{job_id}/logs", response_model=list[InvitingLogRead])
async def get_inviting_job_logs(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(100, le=500),
):
    result_job = await db.execute(select(InvitingJob).where(InvitingJob.id == job_id))
    if not result_job.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Задача не найдена")

    result = await db.execute(
        select(InvitingLog)
        .where(InvitingLog.job_id == job_id)
        .order_by(InvitingLog.timestamp.desc())
        .limit(limit)
    )
    return result.scalars().all()
