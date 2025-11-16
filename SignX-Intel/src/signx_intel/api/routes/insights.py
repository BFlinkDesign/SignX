"""Insights and analytics endpoints."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from signx_intel.storage.database import get_db_session
from signx_intel.storage.models.cost_record import CostRecord

router = APIRouter()


@router.get("/insights/summary")
async def get_cost_summary(
    db: AsyncSession = Depends(get_db_session)
):
    """Get overall cost statistics."""
    # Count total records
    count_query = select(func.count(CostRecord.id))
    count_result = await db.execute(count_query)
    total_records = count_result.scalar() or 0
    
    if total_records == 0:
        return {
            "total_records": 0,
            "average_cost": 0,
            "min_cost": 0,
            "max_cost": 0,
            "total_cost_sum": 0
        }
    
    # Get statistics
    stats_query = select(
        func.avg(CostRecord.total_cost).label("avg_cost"),
        func.min(CostRecord.total_cost).label("min_cost"),
        func.max(CostRecord.total_cost).label("max_cost"),
        func.sum(CostRecord.total_cost).label("sum_cost")
    )
    stats_result = await db.execute(stats_query)
    stats = stats_result.one()
    
    return {
        "total_records": total_records,
        "average_cost": float(stats.avg_cost) if stats.avg_cost else 0,
        "min_cost": float(stats.min_cost) if stats.min_cost else 0,
        "max_cost": float(stats.max_cost) if stats.max_cost else 0,
        "total_cost_sum": float(stats.sum_cost) if stats.sum_cost else 0
    }


@router.get("/insights/drivers")
async def get_driver_analysis(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Analyze which cost drivers appear most frequently.
    
    This gives you insights into what features are commonly used in projects.
    """
    # Get all cost records
    query = select(CostRecord.drivers).limit(1000)  # Sample for performance
    result = await db.execute(query)
    records = result.scalars().all()
    
    # Count driver occurrences
    driver_counts = {}
    for drivers in records:
        for driver in drivers.keys():
            driver_counts[driver] = driver_counts.get(driver, 0) + 1
    
    # Sort by frequency
    sorted_drivers = sorted(
        driver_counts.items(),
        key=lambda x: x[1],
        reverse=True
    )[:limit]
    
    return {
        "most_common_drivers": [
            {"driver": driver, "count": count, "percentage": count / len(records) * 100}
            for driver, count in sorted_drivers
        ],
        "total_records_analyzed": len(records)
    }


@router.get("/insights/trends")
async def get_cost_trends(
    db: AsyncSession = Depends(get_db_session)
):
    """Get cost trends over time."""
    # TODO: Implement time-series analysis
    # This would query cost_records grouped by month/year
    return {
        "message": "Cost trend analysis coming soon",
        "status": "not_implemented"
    }

