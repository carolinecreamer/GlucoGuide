# Privacy and security

- Collect only data needed for the advisory feature the user enables.
- Obtain granular, revocable consent for Dexcom, health, meal, exercise, and clinician sharing.
- Never use health data for advertising or unrelated profiling.
- Encrypt in transit and at rest; keep OAuth client secrets and encryption keys in Key Vault.
- Use per-user authorization for every object and prevent identifier-based cross-user access.
- Redact health data, OAuth codes, and tokens from logs, traces, crash reports, and analytics.
- Keep an access/audit history and notify users of relevant exports and clinician access.
- Support export, correction, revocation, and deletion with documented retention windows.
- Complete HIPAA applicability analysis and BAAs where needed; assess state and international
  health privacy laws independently.
- Complete an App Store privacy disclosure and accessible in-app privacy policy.

The current demo-user mechanism is local-development-only and is not a production authentication
or authorization system.

