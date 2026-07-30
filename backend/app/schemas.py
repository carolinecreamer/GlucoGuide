from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProfileUpsert(BaseModel):
    display_name: str = "Demo User"
    height_cm: float | None = Field(default=None, ge=50, le=275)
    weight_kg: float | None = Field(default=None, ge=20, le=400)
    pump_type: str | None = None
    insulin_action_hours: float = Field(default=4, ge=2, le=8)
    glucose_low_threshold: int = Field(default=70, ge=55, le=100)
    glucose_high_threshold: int = Field(default=180, ge=120, le=300)


class ProfileView(ProfileUpsert):
    model_config = ConfigDict(from_attributes=True)
    id: str
    clinician_review_required: bool


class RegimenInput(BaseModel):
    start_minute: int = Field(ge=0, lt=1440)
    basal_units_per_hour: float = Field(gt=0, le=20)
    insulin_carb_ratio: float = Field(gt=0, le=100)
    correction_factor: float | None = Field(default=None, gt=0, le=500)
    target_glucose: int | None = Field(default=None, ge=70, le=250)


class MealInput(BaseModel):
    occurred_at: datetime
    name: str = Field(min_length=1, max_length=200)
    carbs_g: float = Field(ge=0, le=500)
    protein_g: float = Field(default=0, ge=0, le=300)
    fat_g: float = Field(default=0, ge=0, le=300)
    fiber_g: float = Field(default=0, ge=0, le=100)
    notes: str | None = None


class ExerciseInput(BaseModel):
    occurred_at: datetime
    exercise_type: str = Field(min_length=1, max_length=100)
    intensity: str = Field(pattern="^(low|moderate|high)$")
    duration_minutes: int = Field(gt=0, le=600)
    notes: str | None = None


class DoseInput(BaseModel):
    occurred_at: datetime
    units: float = Field(gt=0, le=100)
    dose_type: str = Field(default="bolus", pattern="^(bolus|basal|correction)$")
    notes: str | None = None


class MealWithDoseInput(BaseModel):
    meal: MealInput
    confirmed_units: float | None = Field(default=None, gt=0, le=100)


class MealDoseEstimateRequest(BaseModel):
    occurred_at: datetime
    carbs_g: float = Field(gt=0, le=500)


class MealDoseEstimateView(BaseModel):
    prescribed_ratio: float
    estimated_units: float
    period_start_minute: int
    explanation: str
    disclaimer: str


class HistoryItem(BaseModel):
    id: str
    occurred_at: datetime
    item_type: str
    title: str
    detail: str
    related_id: str | None = None


class PersonalizationReadiness(BaseModel):
    overnight_nights_ready: int
    overnight_nights_required: int
    meal_period_counts: dict[str, int]
    meals_per_period_required: int
    explanation: list[str]


class InsightView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    insight_type: str
    title: str
    summary: str
    evidence: dict
    confidence: float
    safety_classification: str
    created_at: datetime


class ExerciseGuidanceRequest(BaseModel):
    planned_at: datetime
    exercise_type: str
    intensity: str = Field(pattern="^(low|moderate|high)$")
    duration_minutes: int = Field(gt=0, le=600)


class MealGuidanceRequest(BaseModel):
    name: str
    carbs_g: float = Field(ge=0, le=500)
    protein_g: float = Field(default=0, ge=0, le=300)
    fat_g: float = Field(default=0, ge=0, le=300)
    fiber_g: float = Field(default=0, ge=0, le=100)


class GuidanceView(BaseModel):
    status: str
    headline: str
    guidance: list[str]
    evidence: list[str]
    uncertainty: str
    emergency_note: str
