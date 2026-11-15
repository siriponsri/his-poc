"""Clinical/source identity excludes operational ownership-only task updates."""
from fastapi import HTTPException
from .models import TaskCoordination


def task_source_version(db, task):
    coordination = db.get(TaskCoordination, task.id)
    value = task.version - (coordination.operational_updates if coordination else 0)
    if value < 1:
        raise HTTPException(409, detail={'code':'TASK_SOURCE_VERSION_INVALID'})
    return value
