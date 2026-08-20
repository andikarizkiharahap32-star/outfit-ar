# Plan: E2E Testing Track

This plan decomposes the scope into sequential milestones and individual verification steps.

## Milestone 1: Test Infrastructure Setup
- [ ] Step 1.1: Verify virtual environment and pytest installation.
  - Verification: Run `pytest --version` using `venv_fix` python.
- [ ] Step 1.2: Establish `tests` directory under `backend`.
  - Verification: Verify directory exists and is accessible.
- [ ] Step 1.3: Create pytest config and fixture file (`conftest.py`) with a database session/mock database or test client setup.
  - Verification: conftest imports properly and test client can connect to FastAPI app.

## Milestone 2: Tier 1 - Feature Coverage Tests
- [ ] Step 2.1: Write tests for Health and static endpoints.
  - Verification: Test returns 200 OK.
- [ ] Step 2.2: Write tests for the skin tone detection endpoint `/detect-skin-tone`.
  - Verification: Test uploads mock image, verifies level, confidence, label, recommended_colors, avoid_colors are returned, and verifies DB record is created and committed.
- [ ] Step 2.3: Write tests for recommendations endpoint `/recommendations`.
  - Verification: Test sends body with valid parameters and receives a successful list of outfits.
- [ ] Step 2.4: Write tests for feedback endpoint `/feedback`.
  - Verification: Test sends accepted/rejected feedback, verifies it gets logged in DB.

## Milestone 3: Tier 2-4 - Boundary, Cross-Feature, and Real-World Tests
- [ ] Step 3.1: Write boundary tests (invalid inputs, edge cases).
  - Verification: Verifies status code 400 or 422, appropriate error messages.
- [ ] Step 3.2: Write tests specifically auditing the 15 bugs.
  - Verification:
    - KNN Recommender: Verify KNN is not dead code (either called, or stubbed if feature vectors missing).
    - Diversity score: Verify diversity score is not hardcoded 1.0 (calculate and check variation).
    - Category slot: Verify category slots match product name keywords instead of hardcoded "top".
    - Shuffle/Sorting logic: Verify deterministic diversity sorting from top-30 instead of plain shuffle + sort.
    - Feature Vector: Verify intermediate model is used for feature extraction (check if it predicts correctly).
    - Rounding: Verify ensemble banker's rounding is replaced by standard round half up.
    - Layer order: Verify sequence is Dense -> BN -> Activation(relu) -> Dropout.
    - Range: Verify skin tone range is 1-3 (no range(1, 6) in KNN or anywhere).
    - Db commit: Verify `await db.commit()` is called and transaction is committed.
    - Class weight & LR: Verify CNN training configuration is correct (learning rate <= 1e-4, regularizer, class weights).
- [ ] Step 3.3: Write Tier 3 (cross-feature) and Tier 4 (real-world workflows) tests.
  - Verification: Full scenario runs successfully.

## Milestone 4: Test Ready Verification
- [ ] Step 4.1: Run the full test suite and confirm all pass.
  - Verification: Pytest returns 100% success.
- [ ] Step 4.2: Generate `TEST_READY.md` summarizing feature checklist and test suite execution command.
  - Verification: `TEST_READY.md` exists and matches the spec template.
