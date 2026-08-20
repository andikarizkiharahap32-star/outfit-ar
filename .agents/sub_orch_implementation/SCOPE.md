# Scope: Implementation Track

## Architecture
The implementation track must resolve all 15 audited bugs in the FastAPI backend, CNN models, and KNN recommender.
All modifications should be minimal, precise, and preserve core functionalities.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | CNN & Backbone Fixes | Fix training pipeline (augmentation, lr, class weight), dense head layers order and regularization. (Bugs #2, #8, #13, #15) | none | PLANNED |
| 2 | CNN Inference Fixes | Fix feature vector preprocessing bypass, ensemble rounding, and L2 normalization. (Bugs #6, #7, #14) | none | PLANNED |
| 3 | KNN & Recommendation Router | Fix KNN dead code integration/commenting, diversity scoring, category slots keyword fallback, shuffle logic, skin tone ranges, save fitted check, and db commit. (Bugs #1, #3, #4, #5, #9, #10, #11, #12) | M1, M2 | PLANNED |
| 4 | Phase 1: E2E Integration | Run the full test suite when `TEST_READY.md` is published and ensure 100% pass rate. | M3 | PLANNED |
| 5 | Phase 2: Adversarial Hardening | Run adversarial testing (Tier 5) using Challenger to identify remaining coverage gaps. | M4 | PLANNED |
