# Architecture

## Request and data flow

1. The SwiftUI app records onboarding data and manual meal, exercise, and insulin logs.
2. Dexcom OAuth starts at the backend. Dexcom returns the authorization code to the backend,
   so the client secret never enters the iOS binary.
3. The backend encrypts access and refresh tokens and imports processed EGV records.
4. Deterministic/statistical services calculate bounded observations and supporting evidence.
5. The API returns a safety classification, confidence, method, evidence, uncertainty, and
   clinician-review wording.
6. A future language model may rewrite approved structured facts for readability, but it must
   not originate clinical claims, select a dose, override a safety gate, or access raw secrets.

## Azure target

- Azure Container Apps: FastAPI API.
- Azure Database for PostgreSQL Flexible Server: transactional health and application data.
- Azure Key Vault: Dexcom client secret, token encryption key, and database credentials.
- Microsoft Entra External ID: user authentication and account lifecycle.
- Application Insights / Log Analytics: operational telemetry with health-data redaction.
- Azure Storage: encrypted exports and audit archives only when required.

Production should use private endpoints, managed identities, zone-redundant database backups,
WAF/rate limiting, immutable audit events, and separate development and production tenants.

## Personalization strategy

The first layer is transparent feature engineering:

- time-of-day and weekday/day-type cohorts;
- pre-meal baseline and 90–180 minute excursion;
- overnight median, variability, and trend;
- manually estimated insulin-on-board with explicit action-duration assumptions;
- meal similarity from carbohydrate, protein, fat, fiber, and eventual user tags;
- exercise cohorts by activity, intensity, duration, starting glucose, trend, and estimated IOB.

Only generate an insight after minimum evidence thresholds. Show counterexamples and confidence,
and suppress inference around confounders such as recent exercise, illness, sensor gaps, or
unlogged insulin as those data become available.

Current prototype thresholds are intentionally simple and visible:

- basal-pattern review requires at least three nights with six readings between 00:00 and 06:00;
- meal-ratio review requires at least three meals in the same day period, each with a pre-meal
  reading and glucose coverage 90–180 minutes afterward;
- the engine reevaluates stored outcomes when insights refresh; it does not fine-tune an LLM or
  silently update dosing logic.

The synthetic demo-history endpoint exists only to exercise the example workflow. Synthetic
records must be removed before interpreting personal patterns.

## Later model path

Use a hierarchical model that starts from population priors and gradually personalizes, rather
than training a free-form agent on sparse individual data. Validate retrospectively, then run
silently, then expose advisory output under clinician-approved bounds. Monitor calibration,
subgroup performance, drift, false reassurance, and alert burden.
