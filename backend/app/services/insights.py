from collections import defaultdict
from datetime import timedelta, timezone
from statistics import median

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import GlucoseReading, Insight, MealLog


async def generate_insights(session: AsyncSession, user_id: str) -> list[Insight]:
    readings = list(
        (
            await session.scalars(
                select(GlucoseReading)
                .where(GlucoseReading.user_id == user_id)
                .order_by(GlucoseReading.observed_at)
            )
        ).all()
    )
    meals = list(
        (
            await session.scalars(
                select(MealLog)
                .where(MealLog.user_id == user_id)
                .order_by(MealLog.occurred_at)
            )
        ).all()
    )
    generated: list[Insight] = []

    overnight_by_day: dict[str, list[int]] = defaultdict(list)
    for reading in readings:
        observed = reading.observed_at.replace(tzinfo=timezone.utc)
        if 0 <= observed.hour < 6:
            overnight_by_day[observed.date().isoformat()].append(reading.value_mg_dl)
    day_medians = [median(values) for values in overnight_by_day.values() if len(values) >= 6]
    if len(day_medians) >= 3:
        spread = max(day_medians) - min(day_medians)
        if median(day_medians) > 160 or spread > 50:
            generated.append(
                Insight(
                    user_id=user_id,
                    insight_type="basal_pattern",
                    title="Overnight glucose pattern merits review",
                    summary=(
                        "At least three nights show elevated or variable overnight glucose. "
                        "Discuss basal timing and other causes with your clinician; do not change "
                        "basal settings from this insight alone."
                    ),
                    evidence={
                        "nights": len(day_medians),
                        "median_mg_dl": round(median(day_medians)),
                        "range_mg_dl": round(spread),
                        "method": "Nightly medians from 00:00-06:00 with >=6 readings",
                    },
                    confidence=min(0.9, 0.45 + len(day_medians) * 0.06),
                )
            )

    meal_excursions: dict[str, list[int]] = defaultdict(list)
    for meal in meals:
        meal_time = meal.occurred_at.replace(tzinfo=timezone.utc)
        before = [
            r.value_mg_dl
            for r in readings
            if meal_time - timedelta(minutes=20)
            <= r.observed_at.replace(tzinfo=timezone.utc)
            <= meal_time + timedelta(minutes=10)
        ]
        after = [
            r.value_mg_dl
            for r in readings
            if meal_time + timedelta(minutes=90)
            <= r.observed_at.replace(tzinfo=timezone.utc)
            <= meal_time + timedelta(minutes=180)
        ]
        if before and after:
            period = (
                "breakfast"
                if meal_time.hour < 11
                else "lunch"
                if meal_time.hour < 16
                else "dinner"
            )
            meal_excursions[period].append(max(after) - median(before))

    for period, excursions in meal_excursions.items():
        if len(excursions) >= 3 and median(excursions) > 60:
            generated.append(
                Insight(
                    user_id=user_id,
                    insight_type="ic_ratio_pattern",
                    title=f"Repeated post-{period} rise merits review",
                    summary=(
                        f"Logged {period} meals repeatedly preceded a larger glucose rise. "
                        "Review carbohydrate estimates, bolus timing, and the prescribed "
                        "insulin-to-carbohydrate ratio with your clinician."
                    ),
                    evidence={
                        "meals": len(excursions),
                        "median_excursion_mg_dl": round(median(excursions)),
                        "method": "Peak 90-180 minute glucose minus pre-meal median",
                    },
                    confidence=min(0.9, 0.45 + len(excursions) * 0.07),
                )
            )

    await session.execute(delete(Insight).where(Insight.user_id == user_id))
    session.add_all(generated)
    await session.commit()
    return generated

