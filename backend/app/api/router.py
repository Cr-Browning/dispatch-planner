"""Aggregate API router."""

from fastapi import APIRouter

from app.api import auth, backups, dispatch, employees, health, jobs, settings, skills

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(employees.router)
api_router.include_router(skills.router)
api_router.include_router(jobs.router)
api_router.include_router(dispatch.router)
api_router.include_router(settings.router)
api_router.include_router(backups.router)
