# Security policy

## Supported status

GlucoGuide is an educational prototype, not a production or clinically validated application.
Security updates are provided on a best-effort basis for the latest revision only.

## Reporting a vulnerability

Do not include credentials, tokens, health information, or exploit details in a public issue.
Use GitHub's private vulnerability reporting feature under the repository's **Security** tab.
If that feature is unavailable, contact the repository owner privately through the contact
method listed on their GitHub profile.

Include the affected component, reproduction steps, impact, and any suggested remediation.
Do not access another person's data or run testing against systems you do not own.

## Secrets

Never commit a Dexcom client secret, OAuth token, encryption key, database credential, or
personal health record. Use `.env` for local development and Azure Key Vault for deployed
environments. If a secret is exposed, revoke and rotate it immediately.

