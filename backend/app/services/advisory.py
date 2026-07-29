from datetime import datetime, timedelta, timezone
from math import sqrt

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ExerciseLog, GlucoseReading, InsulinDose, MealLog, UserProfile
from app.schemas import ExerciseGuidanceRequest, GuidanceView, MealGuidanceRequest


EMERGENCY_NOTE = (
    "Not medical advice or an emergency service. Follow your prescribed diabetes plan. "
    "For severe symptoms, loss of consciousness, or inability to treat a low, use glucagon "
    "if prescribed and contact emergency services."
)


def estimated_iob(doses: list[InsulinDose], at: datetime, action_hours: float) -> float:
    total = 0.0
    for dose in doses:
        age_hours = (at - dose.occurred_at.replace(tzinfo=timezone.utc)).total_seconds() / 3600
        if dose.dose_type not in {"bolus", "correction"} or not 0 <= age_hours < action_hours:
            continue
        total += dose.units * (1 - age_hours / action_hours)
    return round(total, 2)


async def exercise_guidance(
    session: AsyncSession, user_id: str, request: ExerciseGuidanceRequest
) -> GuidanceView:
    profile = await session.get(UserProfile, user_id)
    if profile is None:
        raise ValueError("Complete onboarding before requesting guidance")

    readings = list(
        (
            await session.scalars(
                select(GlucoseReading)
                .where(GlucoseReading.user_id == user_id)
                .order_by(GlucoseReading.observed_at.desc())
                .limit(3)
            )
        ).all()
    )
    doses = list(
        (
            await session.scalars(
                select(InsulinDose).where(
                    InsulinDose.user_id == user_id,
                    InsulinDose.occurred_at
                    >= request.planned_at - timedelta(hours=profile.insulin_action_hours),
                )
            )
        ).all()
    )
    iob = estimated_iob(doses, request.planned_at, profile.insulin_action_hours)

    if not readings:
        return GuidanceView(
            status="insufficient_data",
            headline="Check current glucose before exercise",
            guidance=[
                "CGM data is unavailable; use your prescribed pre-exercise checking protocol.",
                "Do not rely on this app to decide whether exercise is safe.",
            ],
            evidence=[f"Estimated manually logged IOB: {iob:.1f} U"],
            uncertainty="High: no recent glucose readings are available.",
            emergency_note=EMERGENCY_NOTE,
        )

    current = readings[0].value_mg_dl
    trend = readings[0].trend or "unknown"
    evidence = [
        f"Latest glucose: {current} mg/dL ({trend})",
        f"Estimated manually logged IOB: {iob:.1f} U",
        f"Planned activity: {request.duration_minutes} min, {request.intensity} intensity",
    ]

    if current < profile.glucose_low_threshold:
        return GuidanceView(
            status="stop",
            headline="Do not start exercise while glucose is low",
            guidance=[
                "Follow your prescribed hypoglycemia treatment plan now.",
                "Recheck and wait until you meet your clinician-approved exercise threshold.",
            ],
            evidence=evidence,
            uncertainty="Low for the stop signal; CGM values can lag blood glucose.",
            emergency_note=EMERGENCY_NOTE,
        )

    if current < 100 or trend.lower() in {"falling", "fallingquickly", "doubleDown"}:
        headline = "Use caution before exercise"
        guidance = [
            "Confirm glucose and follow your clinician-approved carbohydrate plan before starting.",
            "Carry rapid-acting carbohydrate and monitor more frequently during activity.",
        ]
    elif current > 250:
        headline = "Check your high-glucose exercise protocol"
        guidance = [
            "Check ketones if this is part of your prescribed plan before vigorous activity.",
            "Avoid using exercise as an urgent correction and follow your clinician's instructions.",
        ]
    else:
        headline = "Conditions appear compatible with your logged plan"
        guidance = [
            "Continue monitoring because aerobic activity can lower glucose during and afterward.",
            "Use your clinician-approved adjustments; this app does not calculate a dose.",
        ]

    if iob >= 2:
        guidance.append(
            "Meaningful insulin may still be active; use the more conservative option in your plan."
        )

    return GuidanceView(
        status="caution" if current < 100 or current > 250 or iob >= 2 else "informational",
        headline=headline,
        guidance=guidance,
        evidence=evidence,
        uncertainty="Moderate: IOB is an estimate based only on manually logged doses.",
        emergency_note=EMERGENCY_NOTE,
    )


async def meal_guidance(
    session: AsyncSession, user_id: str, request: MealGuidanceRequest
) -> GuidanceView:
    meals = list(
        (
            await session.scalars(
                select(MealLog)
                .where(MealLog.user_id == user_id)
                .order_by(MealLog.occurred_at.desc())
                .limit(100)
            )
        ).all()
    )
    if not meals:
        return GuidanceView(
            status="insufficient_data",
            headline="No comparable meals yet",
            guidance=[
                "Use your prescribed insulin-to-carbohydrate ratio and timing plan.",
                "Log this meal and outcome so future comparisons have evidence.",
            ],
            evidence=[],
            uncertainty="High: there is no personal meal history.",
            emergency_note=EMERGENCY_NOTE,
        )

    def distance(meal: MealLog) -> float:
        return sqrt(
            ((meal.carbs_g - request.carbs_g) / 15) ** 2
            + ((meal.protein_g - request.protein_g) / 20) ** 2
            + ((meal.fat_g - request.fat_g) / 15) ** 2
        )

    matches = sorted(meals, key=distance)[:3]
    close = [meal for meal in matches if distance(meal) <= 2]
    if not close:
        return GuidanceView(
            status="insufficient_data",
            headline="This meal is unlike your logged meals",
            guidance=[
                "Use your prescribed ratio and timing rather than extrapolating from weak matches.",
                "Consider extra monitoring according to your care plan.",
            ],
            evidence=["No logged meal was sufficiently similar in carbohydrate, protein, and fat."],
            uncertainty="High: macro similarity was low.",
            emergency_note=EMERGENCY_NOTE,
        )

    evidence = [
        f"{meal.name}: {meal.carbs_g:g}g carbs, {meal.protein_g:g}g protein, "
        f"{meal.fat_g:g}g fat"
        for meal in close
    ]
    return GuidanceView(
        status="informational",
        headline=f"Found {len(close)} comparable logged meal(s)",
        guidance=[
            "Review these prior meals and their glucose traces before applying your prescribed ratio.",
            "Higher fat or protein can delay glucose rise; use only adjustments already approved by "
            "your clinician.",
            "This app intentionally does not calculate insulin units.",
        ],
        evidence=evidence,
        uncertainty="Moderate: similarity uses macros and time history, not absorption certainty.",
        emergency_note=EMERGENCY_NOTE,
    )

