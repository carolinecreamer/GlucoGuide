from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def new_id() -> str:
    return str(uuid4())


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    display_name: Mapped[str] = mapped_column(String(100), default="Demo User")
    height_cm: Mapped[float | None] = mapped_column(Float)
    weight_kg: Mapped[float | None] = mapped_column(Float)
    pump_type: Mapped[str | None] = mapped_column(String(100))
    insulin_action_hours: Mapped[float] = mapped_column(Float, default=4.0)
    glucose_low_threshold: Mapped[int] = mapped_column(Integer, default=70)
    glucose_high_threshold: Mapped[int] = mapped_column(Integer, default=180)
    clinician_review_required: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class RegimenSetting(Base):
    __tablename__ = "regimen_settings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("user_profiles.id"), index=True)
    start_minute: Mapped[int] = mapped_column(Integer)
    basal_units_per_hour: Mapped[float] = mapped_column(Float)
    insulin_carb_ratio: Mapped[float] = mapped_column(Float)
    correction_factor: Mapped[float | None] = mapped_column(Float)
    target_glucose: Mapped[int | None] = mapped_column(Integer)


class MealLog(Base):
    __tablename__ = "meal_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("user_profiles.id"), index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    name: Mapped[str] = mapped_column(String(200))
    carbs_g: Mapped[float] = mapped_column(Float)
    protein_g: Mapped[float] = mapped_column(Float, default=0)
    fat_g: Mapped[float] = mapped_column(Float, default=0)
    fiber_g: Mapped[float] = mapped_column(Float, default=0)
    notes: Mapped[str | None] = mapped_column(Text)


class ExerciseLog(Base):
    __tablename__ = "exercise_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("user_profiles.id"), index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    exercise_type: Mapped[str] = mapped_column(String(100))
    intensity: Mapped[str] = mapped_column(String(30))
    duration_minutes: Mapped[int] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)


class InsulinDose(Base):
    __tablename__ = "insulin_doses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("user_profiles.id"), index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    units: Mapped[float] = mapped_column(Float)
    dose_type: Mapped[str] = mapped_column(String(30), default="bolus")
    notes: Mapped[str | None] = mapped_column(Text)


class GlucoseReading(Base):
    __tablename__ = "glucose_readings"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("user_profiles.id"), index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    value_mg_dl: Mapped[int] = mapped_column(Integer)
    trend: Mapped[str | None] = mapped_column(String(50))
    source: Mapped[str] = mapped_column(String(30), default="dexcom")


class DexcomConnection(Base):
    __tablename__ = "dexcom_connections"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("user_profiles.id"), primary_key=True
    )
    encrypted_access_token: Mapped[str] = mapped_column(Text)
    encrypted_refresh_token: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class OAuthState(Base):
    __tablename__ = "oauth_states"

    state: Mapped[str] = mapped_column(String(100), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("user_profiles.id"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Insight(Base):
    __tablename__ = "insights"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("user_profiles.id"), index=True)
    insight_type: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(200))
    summary: Mapped[str] = mapped_column(Text)
    evidence: Mapped[dict] = mapped_column(JSON)
    confidence: Mapped[float] = mapped_column(Float)
    safety_classification: Mapped[str] = mapped_column(
        String(50), default="clinician_review"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

