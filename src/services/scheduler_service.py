"""Scheduler service for background tasks."""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from typing import Optional
import asyncio

from ..core.config import settings
from ..core.logging import setup_logging
from ..db.postgres import AsyncSessionLocal
from .drift_detection_service import DriftDetectionService
from ..db.repositories.log_repo import LogRepository
from ..db.models.drift_log import DriftLog

logger = setup_logging()


class SchedulerService:
    """Service for scheduling background tasks."""
    
    def __init__(self):
        self.scheduler: Optional[AsyncIOScheduler] = None
        self._running = False
    
    async def start(self):
        """Start the scheduler."""
        if self._running:
            logger.warning("Scheduler is already running")
            return
        
        self.scheduler = AsyncIOScheduler()
        
        # Schedule monthly drift detection
        # Parse cron schedule from config (format: "0 2 1 * *" = monthly on 1st day at 2 AM)
        try:
            cron_parts = settings.drift_check_schedule.split()
            if len(cron_parts) == 5:
                trigger = CronTrigger(
                    minute=cron_parts[0],
                    hour=cron_parts[1],
                    day=cron_parts[2],
                    month=cron_parts[3],
                    day_of_week=cron_parts[4]
                )
            else:
                # Default to monthly on 1st day at 2 AM
                trigger = CronTrigger(day=1, hour=2, minute=0)
            
            self.scheduler.add_job(
                self._run_drift_detection,
                trigger=trigger,
                id="drift_detection",
                name="Monthly Drift Detection",
                replace_existing=True
            )
            
            logger.info(f"Scheduled drift detection (monthly): {settings.drift_check_schedule}")
        except Exception as e:
            logger.error(f"Failed to parse cron schedule: {e}, using default (monthly on 1st at 2 AM)")
            self.scheduler.add_job(
                self._run_drift_detection,
                trigger=CronTrigger(day=1, hour=2, minute=0),
                id="drift_detection",
                name="Monthly Drift Detection",
                replace_existing=True
            )
        
        self.scheduler.start()
        self._running = True
        logger.info("Scheduler started")
    
    async def shutdown(self):
        """Shutdown the scheduler."""
        if self.scheduler and self._running:
            self.scheduler.shutdown(wait=True)
            self._running = False
            logger.info("Scheduler shut down")
    
    async def _run_drift_detection(self):
        """Background task to run drift detection."""
        try:
            logger.info("Running scheduled drift detection...")
            
            async with AsyncSessionLocal() as session:
                log_repo = LogRepository(session)
                drift_service = DriftDetectionService(log_repo)
                
                # Run drift detection
                result = await drift_service.check_drift()
                
                # Log result
                drift_log = DriftLog(
                    data_drift_score=result["data_drift"].get("data_drift_score", 0.0),
                    performance_drift_score=result["performance_drift"].get("performance_drift_score"),
                    drift_detected=result["drift_detected"],
                    recommendation=result["recommendation"],
                    drift_metadata={
                        "data_drift": result["data_drift"],
                        "performance_drift": result["performance_drift"]
                    }
                )
                await log_repo.log_drift(drift_log)
                await session.commit()
                
                if result["drift_detected"]:
                    logger.warning(f"Drift detected! Recommendation: {result['recommendation']}")
                    logger.warning(f"Data drift score: {result['data_drift'].get('data_drift_score', 0.0)}")
                    if result["performance_drift"].get("performance_drift_score"):
                        logger.warning(f"Performance drift score: {result['performance_drift'].get('performance_drift_score')}")
                else:
                    logger.info("No drift detected")
        
        except Exception as e:
            logger.error(f"Error in scheduled drift detection: {e}", exc_info=True)
    
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._running

