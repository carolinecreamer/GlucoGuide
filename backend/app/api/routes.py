from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.models import (
    ExerciseLog,
    GlucoseReading,
    InsulinDose,
    MealDoseLink,
    MealLog,
    RegimenSetting,
    UserProfile,
)
from app.schemas import (
    DoseInput,
    ExerciseGuidanceRequest,
    ExerciseInput,
    GuidanceView,
    HistoryItem,
    InsightView,
    MealDoseEstimateRequest,
    MealDoseEstimateView,
    MealGuidanceRequest,
    MealInput,
    MealWithDoseInput,
    PersonalizationReadiness,
    ProfileUpsert,
    ProfileView,
    RegimenInput,
)
from app.services.advisory import exercise_guidance, meal_guidance
from app.services.dexcom import DexcomOAuthError, DexcomService
from app.services.insights import generate_insights

router = APIRouter(prefix="/api/v1")


def user_id(settings: Settings = Depends(get_settings)) -> str:
    # Development vertical slice. Replace with the authenticated subject from
    # Microsoft Entra External ID before any multi-user deployment.
    return settings.demo_user_id


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "glucoguide-api"}


@router.put("/profile", response_model=ProfileView)
async def upsert_profile(
    payload: ProfileUpsert,
    session: AsyncSession = Depends(get_session),
    current_user: str = Depends(user_id),
) -> UserProfile:
    profile = await session.get(UserProfile, current_user)
    if profile is None:
        profile = UserProfile(id=current_user)
        session.add(profile)
    for key, value in payload.model_dump().items():
        setattr(profile, key, value)
    await session.commit()
    await session.refresh(profile)
    return profile


@router.get("/profile", response_model=ProfileView)
async def get_profile(
    session: AsyncSession = Depends(get_session),
    current_user: str = Depends(user_id),
) -> UserProfile:
    profile = await session.get(UserProfile, current_user)
    if profile is None:
        raise HTTPException(404, "Profile not found")
    return profile


@router.put("/regimen")
async def replace_regimen(
    payload: list[RegimenInput],
    session: AsyncSession = Depends(get_session),
    current_user: str = Depends(user_id),
) -> dict:
    existing = list(
        (
            await session.scalars(
                select(RegimenSetting).where(RegimenSetting.user_id == current_user)
            )
        ).all()
    )
    for item in existing:
        await session.delete(item)
    session.add_all(
        [RegimenSetting(user_id=current_user, **item.model_dump()) for item in payload]
    )
    await session.commit()
    return {"saved": len(payload)}


@router.post("/logs/meals", status_code=201)
async def log_meal(
    payload: MealInput,
    session: AsyncSession = Depends(get_session),
    current_user: str = Depends(user_id),
) -> dict:
    item = MealLog(user_id=current_user, **payload.model_dump())
    session.add(item)
    await session.commit()
    return {"id": item.id}


@router.post("/logs/meals-with-dose", status_code=201)
async def log_meal_with_dose(
    payload: MealWithDoseInput,
    session: AsyncSession = Depends(get_session),
    current_user: str = Depends(user_id),
) -> dict:
    meal = MealLog(user_id=current_user, **payload.meal.model_dump())
    session.add(meal)
    await session.flush()

    dose_id = None
    if payload.confirmed_units is not None:
        dose = InsulinDose(
            user_id=current_user,
            occurred_at=payload.meal.occurred_at,
            units=payload.confirmed_units,
            dose_type="bolus",
            notes=f"Confirmed meal bolus for {payload.meal.name}",
        )
        session.add(dose)
        await session.flush()
        session.add(MealDoseLink(meal_id=meal.id, dose_id=dose.id))
        dose_id = dose.id

    await session.commit()
    return {"meal_id": meal.id, "dose_id": dose_id}


@router.post("/guidance/meal-dose-estimate", response_model=MealDoseEstimateView)
async def meal_dose_estimate(
    payload: MealDoseEstimateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: str = Depends(user_id),
) -> MealDoseEstimateView:
    minute = payload.occurred_at.hour * 60 + payload.occurred_at.minute
    settings = list(
        (
            await session.scalars(
                select(RegimenSetting)
                .where(RegimenSetting.user_id == current_user)
                .order_by(RegimenSetting.start_minute)
            )
        ).all()
    )
    if not settings:
        raise HTTPException(409, "No prescribed insulin-to-carbohydrate ratio is configured")

    active = settings[-1]
    for setting in settings:
        if setting.start_minute <= minute:
            active = setting
        else:
            break

    estimate = round(payload.carbs_g / active.insulin_carb_ratio, 1)
    return MealDoseEstimateView(
        prescribed_ratio=active.insulin_carb_ratio,
        estimated_units=estimate,
        period_start_minute=active.start_minute,
        explanation=(
            f"{payload.carbs_g:g} g carbohydrate divided by the configured "
            f"1:{active.insulin_carb_ratio:g} prescribed ratio."
        ),
        disclaimer=(
            "This is arithmetic from your saved prescribed ratio, not an AI dose "
            "recommendation. It does not account for current glucose, IOB, trend, exercise, "
            "illness, or clinician-directed adjustments. Confirm the actual dose yourself."
        ),
    )


@router.post("/logs/exercise", status_code=201)
async def log_exercise(
    payload: ExerciseInput,
    session: AsyncSession = Depends(get_session),
    current_user: str = Depends(user_id),
) -> dict:
    item = ExerciseLog(user_id=current_user, **payload.model_dump())
    session.add(item)
    await session.commit()
    return {"id": item.id}


@router.post("/logs/doses", status_code=201)
async def log_dose(
    payload: DoseInput,
    session: AsyncSession = Depends(get_session),
    current_user: str = Depends(user_id),
) -> dict:
    item = InsulinDose(user_id=current_user, **payload.model_dump())
    session.add(item)
    await session.commit()
    return {"id": item.id}


@router.get("/logs/history", response_model=list[HistoryItem])
async def log_history(
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
    current_user: str = Depends(user_id),
) -> list[HistoryItem]:
    meals = list(
        (
            await session.scalars(
                select(MealLog)
                .where(MealLog.user_id == current_user)
                .order_by(MealLog.occurred_at.desc())
                .limit(limit)
            )
        ).all()
    )
    exercises = list(
        (
            await session.scalars(
                select(ExerciseLog)
                .where(ExerciseLog.user_id == current_user)
                .order_by(ExerciseLog.occurred_at.desc())
                .limit(limit)
            )
        ).all()
    )
    doses = list(
        (
            await session.scalars(
                select(InsulinDose)
                .where(InsulinDose.user_id == current_user)
                .order_by(InsulinDose.occurred_at.desc())
                .limit(limit)
            )
        ).all()
    )
    links = {
        link.dose_id: link.meal_id
        for link in (
            await session.scalars(
                select(MealDoseLink).join(
                    MealLog, MealLog.id == MealDoseLink.meal_id
                ).where(MealLog.user_id == current_user)
            )
        ).all()
    }
    items = [
        HistoryItem(
            id=meal.id,
            occurred_at=meal.occurred_at,
            item_type="meal",
            title=meal.name,
            detail=(
                f"{meal.carbs_g:g}g carbs · {meal.protein_g:g}g protein · "
                f"{meal.fat_g:g}g fat"
            ),
        )
        for meal in meals
    ]
    items.extend(
        HistoryItem(
            id=dose.id,
            occurred_at=dose.occurred_at,
            item_type="insulin",
            title=f"{dose.units:g} U {dose.dose_type}",
            detail=dose.notes or "Manually logged insulin",
            related_id=links.get(dose.id),
        )
        for dose in doses
    )
    items.extend(
        HistoryItem(
            id=exercise.id,
            occurred_at=exercise.occurred_at,
            item_type="exercise",
            title=exercise.exercise_type,
            detail=f"{exercise.duration_minutes} min · {exercise.intensity}",
        )
        for exercise in exercises
    )
    return sorted(items, key=lambda item: item.occurred_at, reverse=True)[:limit]


@router.get("/glucose/recent")
async def recent_glucose(
    limit: int = Query(default=48, ge=1, le=288),
    session: AsyncSession = Depends(get_session),
    current_user: str = Depends(user_id),
) -> list[dict]:
    readings = (
        await session.scalars(
            select(GlucoseReading)
            .where(GlucoseReading.user_id == current_user)
            .order_by(GlucoseReading.observed_at.desc())
            .limit(limit)
        )
    ).all()
    return [
        {
            "id": row.id,
            "observed_at": row.observed_at,
            "value_mg_dl": row.value_mg_dl,
            "trend": row.trend,
        }
        for row in readings
    ]


@router.post("/sample-data")
async def create_sample_data(
    session: AsyncSession = Depends(get_session),
    current_user: str = Depends(user_id),
) -> dict:
    if await session.scalar(
        select(GlucoseReading.id).where(GlucoseReading.user_id == current_user).limit(1)
    ):
        return {"created": 0}
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    rows = []
    for index in range(288):
        observed = now - timedelta(minutes=(287 - index) * 5)
        baseline = 125 + (20 if 7 <= observed.hour <= 10 else 0)
        value = baseline + ((index % 24) - 12)
        rows.append(
            GlucoseReading(
                id=f"sample-{current_user}-{index}",
                user_id=current_user,
                observed_at=observed,
                value_mg_dl=value,
                trend="Flat",
                source="sample",
            )
        )
    session.add_all(rows)
    await session.commit()
    return {"created": len(rows)}


@router.post("/sample-history")
async def create_sample_history(
    session: AsyncSession = Depends(get_session),
    current_user: str = Depends(user_id),
) -> dict:
    if await session.scalar(
        select(GlucoseReading.id).where(
            GlucoseReading.id.like(f"demo-history-{current_user}-%")
        ).limit(1)
    ):
        return {"created": 0}

    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    start_day = (now - timedelta(days=4)).replace(hour=0, minute=0)
    created = 0
    for day_index in range(4):
        day_start = start_day + timedelta(days=day_index)
        for reading_index in range(288):
            observed = day_start + timedelta(minutes=reading_index * 5)
            minute = observed.hour * 60 + observed.minute
            if minute < 360:
                value = 170 + (reading_index % 9)
            elif 460 <= minute <= 500:
                value = 118 + (reading_index % 5)
            elif 570 <= minute <= 660:
                value = 205 + (reading_index % 11)
            else:
                value = 130 + ((reading_index % 13) - 6)
            session.add(
                GlucoseReading(
                    id=f"demo-history-{current_user}-{day_index}-{reading_index}",
                    user_id=current_user,
                    observed_at=observed,
                    value_mg_dl=value,
                    trend="Flat",
                    source="sample",
                )
            )
            created += 1

        meal_time = day_start.replace(hour=8)
        meal = MealLog(
            user_id=current_user,
            occurred_at=meal_time,
            name="Demo oatmeal breakfast",
            carbs_g=45,
            protein_g=12,
            fat_g=8,
            fiber_g=6,
            notes="Synthetic example data",
        )
        session.add(meal)
        await session.flush()
        dose = InsulinDose(
            user_id=current_user,
            occurred_at=meal_time,
            units=4.5,
            dose_type="bolus",
            notes="Synthetic confirmed meal bolus",
        )
        session.add(dose)
        await session.flush()
        session.add(MealDoseLink(meal_id=meal.id, dose_id=dose.id))
        created += 2

    await session.commit()
    return {"created": created}


@router.delete("/sample-history")
async def delete_sample_history(
    session: AsyncSession = Depends(get_session),
    current_user: str = Depends(user_id),
) -> dict:
    demo_meal_ids = select(MealLog.id).where(
        MealLog.user_id == current_user,
        MealLog.notes == "Synthetic example data",
    )
    await session.execute(
        delete(MealDoseLink).where(MealDoseLink.meal_id.in_(demo_meal_ids))
    )
    dose_result = await session.execute(
        delete(InsulinDose).where(
            InsulinDose.user_id == current_user,
            InsulinDose.notes == "Synthetic confirmed meal bolus",
        )
    )
    meal_result = await session.execute(
        delete(MealLog).where(
            MealLog.user_id == current_user,
            MealLog.notes == "Synthetic example data",
        )
    )
    glucose_result = await session.execute(
        delete(GlucoseReading).where(
            GlucoseReading.user_id == current_user,
            GlucoseReading.id.like(f"demo-history-{current_user}-%"),
        )
    )
    await session.commit()
    return {
        "deleted": (
            (dose_result.rowcount or 0)
            + (meal_result.rowcount or 0)
            + (glucose_result.rowcount or 0)
        )
    }


@router.get("/insights/readiness", response_model=PersonalizationReadiness)
async def insight_readiness(
    session: AsyncSession = Depends(get_session),
    current_user: str = Depends(user_id),
) -> PersonalizationReadiness:
    readings = list(
        (
            await session.scalars(
                select(GlucoseReading).where(GlucoseReading.user_id == current_user)
            )
        ).all()
    )
    meals = list(
        (
            await session.scalars(
                select(MealLog).where(MealLog.user_id == current_user)
            )
        ).all()
    )

    overnight: dict[str, int] = {}
    for reading in readings:
        observed = reading.observed_at.replace(tzinfo=timezone.utc)
        if observed.hour < 6:
            key = observed.date().isoformat()
            overnight[key] = overnight.get(key, 0) + 1

    period_counts = {"breakfast": 0, "lunch": 0, "dinner": 0}
    for meal in meals:
        meal_time = meal.occurred_at.replace(tzinfo=timezone.utc)
        has_before = any(
            meal_time - timedelta(minutes=20)
            <= reading.observed_at.replace(tzinfo=timezone.utc)
            <= meal_time + timedelta(minutes=10)
            for reading in readings
        )
        has_after = any(
            meal_time + timedelta(minutes=90)
            <= reading.observed_at.replace(tzinfo=timezone.utc)
            <= meal_time + timedelta(minutes=180)
            for reading in readings
        )
        if has_before and has_after:
            period = (
                "breakfast"
                if meal_time.hour < 11
                else "lunch"
                if meal_time.hour < 16
                else "dinner"
            )
            period_counts[period] += 1

    return PersonalizationReadiness(
        overnight_nights_ready=sum(1 for count in overnight.values() if count >= 6),
        overnight_nights_required=3,
        meal_period_counts=period_counts,
        meals_per_period_required=3,
        explanation=[
            "Basal review needs at least 3 nights with 6 or more readings between midnight and 6 AM.",
            "Meal-ratio review needs at least 3 logged meals in the same time period, each with pre-meal and 90-180 minute glucose data.",
            "More data improves confidence; the engine evaluates new logs whenever insights refresh and does not require a separate training command.",
        ],
    )


@router.get("/integrations/dexcom/start")
async def dexcom_start(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    current_user: str = Depends(user_id),
) -> dict:
    try:
        url = await DexcomService(settings).authorization_url(session, current_user)
        return {"authorization_url": url}
    except RuntimeError as error:
        raise HTTPException(503, str(error)) from error


@router.get("/integrations/dexcom/callback", response_class=HTMLResponse)
async def dexcom_callback(
    code: str,
    state: str,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> str:
    try:
        await DexcomService(settings).complete_authorization(session, code, state)
    except DexcomOAuthError as error:
        raise HTTPException(502, str(error)) from error
    except (ValueError, RuntimeError) as error:
        raise HTTPException(400, str(error)) from error
    except httpx.HTTPError as error:
        raise HTTPException(502, "Dexcom rejected the authorization exchange") from error
    return """
    <html><body style="font-family: -apple-system; padding: 32px">
      <h1>Dexcom connected</h1>
      <p>You can return to GlucoGuide and synchronize your glucose history.</p>
    </body></html>
    """


@router.post("/integrations/dexcom/sync")
async def dexcom_sync(
    hours: int = Query(default=72, ge=1, le=720),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    current_user: str = Depends(user_id),
) -> dict:
    try:
        inserted = await DexcomService(settings).sync_egvs(session, current_user, hours)
        return {"inserted": inserted}
    except DexcomOAuthError as error:
        raise HTTPException(502, str(error)) from error
    except ValueError as error:
        raise HTTPException(409, str(error)) from error
    except RuntimeError as error:
        raise HTTPException(503, str(error)) from error
    except httpx.HTTPError as error:
        raise HTTPException(502, "Dexcom synchronization failed") from error


@router.post("/insights/generate", response_model=list[InsightView])
async def refresh_insights(
    session: AsyncSession = Depends(get_session),
    current_user: str = Depends(user_id),
):
    return await generate_insights(session, current_user)


@router.post("/guidance/exercise", response_model=GuidanceView)
async def get_exercise_guidance(
    payload: ExerciseGuidanceRequest,
    session: AsyncSession = Depends(get_session),
    current_user: str = Depends(user_id),
):
    try:
        return await exercise_guidance(session, current_user, payload)
    except ValueError as error:
        raise HTTPException(409, str(error)) from error


@router.post("/guidance/meals", response_model=GuidanceView)
async def get_meal_guidance(
    payload: MealGuidanceRequest,
    session: AsyncSession = Depends(get_session),
    current_user: str = Depends(user_id),
):
    return await meal_guidance(session, current_user, payload)
