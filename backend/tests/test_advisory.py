from datetime import datetime, timedelta, timezone

from app.models import InsulinDose
from app.services.advisory import estimated_iob


def test_estimated_iob_uses_linear_decay_and_ignores_old_doses():
    now = datetime.now(timezone.utc)
    doses = [
        InsulinDose(occurred_at=now - timedelta(hours=1), units=4, dose_type="bolus"),
        InsulinDose(occurred_at=now - timedelta(hours=5), units=10, dose_type="bolus"),
        InsulinDose(occurred_at=now - timedelta(minutes=10), units=2, dose_type="basal"),
    ]

    assert estimated_iob(doses, now, action_hours=4) == 3.0

