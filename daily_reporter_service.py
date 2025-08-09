"""
Daily Reporter Service - Runs continuously and sends reports at scheduled time
"""

import asyncio
from daily_summary_reporter import DailySummaryReporter
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Run the daily reporter service"""
    reporter = DailySummaryReporter()
    
    logger.info("Daily Summary Reporter Service Started")
    logger.info(f"Reports scheduled for {reporter.report_time} daily")
    logger.info("Sending initial summary...")
    
    # Send immediate summary on startup
    reporter.send_immediate_summary()
    
    # Run scheduler
    await reporter.run_scheduler()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Daily reporter service stopped")