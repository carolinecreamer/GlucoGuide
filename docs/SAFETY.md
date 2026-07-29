# Safety and intended use

## Intended use

GlucoGuide helps an adult user organize diabetes data, recognize repeated patterns, prepare
questions for a clinician, and follow the user's existing clinician-approved meal and exercise
plans.

## Explicit exclusions

- No autonomous or closed-loop insulin delivery.
- No direct pump control.
- No exact insulin dose recommendation.
- No instruction to change basal rates or insulin-to-carbohydrate ratios without clinician review.
- No replacement for CGM alerts, blood glucose confirmation, ketone testing, glucagon,
  emergency services, or the user's prescribed plan.

## Required safety controls

- Hard stop for low glucose in exercise guidance.
- High-glucose/ketone caution for vigorous exercise.
- IOB labeled as an estimate based only on manually logged doses.
- Evidence, method, sample count, confidence, and uncertainty on every learned insight.
- Minimum evidence thresholds and abstention when data are sparse or conflicting.
- Versioned advisory rules and model artifacts with reproducible audit records.
- User-visible correction/deletion of logs and a way to flag inaccurate advice.
- Clinical review and human-factors testing before public use.
- Incident response, rollback, model monitoring, and post-market surveillance if regulated.

This prototype's intended use and claims require review by qualified medical, legal, privacy,
security, and regulatory professionals before real-world use.

