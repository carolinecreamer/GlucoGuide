# Contributing

Contributions are welcome when they preserve the project's educational, advisory-only scope.

## Development

1. Create a branch from the default branch.
2. Keep secrets and personal health information out of commits, fixtures, issues, and logs.
3. Install backend dependencies with `python -m pip install -e ".[test]"` from `backend/`.
4. Run `python -m pytest` before opening a pull request.
5. Generate the iOS project with `xcodegen generate` from `ios/` and build the `GlucoGuide`
   scheme without code signing.

## Safety requirements

- Do not add exact insulin-dose recommendations, autonomous dosing, or pump control.
- Do not weaken low-glucose or high-glucose exercise safeguards.
- Recommendations must expose their evidence, assumptions, uncertainty, and abstention rules.
- Any proposed medical or regulatory claim must have authoritative evidence and qualified review.
- Add tests when changing advisory rules, data boundaries, OAuth, or authorization behavior.

Pull requests should explain the user-visible behavior, safety implications, and validation
performed.

