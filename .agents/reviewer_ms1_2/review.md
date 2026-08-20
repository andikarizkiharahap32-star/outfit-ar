# Review Report — Milestone 1 (CNN & Backbone Fixes)

## Review Summary

**Verdict**: APPROVE

## Findings

### Minor Finding 1: `get_compile_config()` Unused in `train_cnn.py`
- What: The helper function `get_compile_config()` is defined in `efficientnet_backbone.py` but is not imported or used in `train_cnn.py`.
- Where: `backend/ml/cnn/efficientnet_backbone.py` (lines 166-183) and `backend/ml/cnn/train_cnn.py` (lines 99-103)
- Why: While this does not break model training, it creates dead code/inconsistency. `train_cnn.py` compiles the model directly using `categorical_crossentropy` and `accuracy` metrics instead of utilizing `get_compile_config()`.
- Suggestion: Either refactor `train_cnn.py` to use `get_compile_config()` (with adaptation for categorical label mode) or remove the unused helper function to keep the codebase clean.

## Verified Claims

- **Data augmentation layers implemented and mapped correctly** → verified via `view_file` on `train_cnn.py` → **PASS**
  - **Details**: `RandomFlip`, `RandomRotation`, `RandomBrightness`, and `RandomContrast` are defined in `data_augmentation` sequential block and mapped to the train dataset *after* `.cache()` but *before* `.prefetch()` (lines 78-88).
- **Dynamic class weight calculation** → verified via `view_file` on `train_cnn.py` → **PASS**
  - **Details**: Category directory file count is computed dynamically via `os.listdir` and weights computed using standard inverse frequency formula: `total_samples / (num_classes * count)`. Passed to `model.fit(..., class_weight=class_weights)`.
- **Dense head layer ordering & configuration** → verified via running `verify_model.py` and `view_file` on `efficientnet_backbone.py` → **PASS**
  - **Details**: Order is strictly Dense (activation=None, use_bias=False, L2 regularizer of 1e-4) -> BatchNormalization -> Activation (relu) -> Dropout (0.4) -> Dense (softmax).
- **Compilation and backend tests execution** → verified via executing `verify_model.py` and backend `pytest` → **PASS**
  - **Details**: Model building verification script succeeded with return code 0. Pytest suite ran and 3 tests passed with 0 failures.

## Coverage Gaps

- None — the review covered all modified backbone files, configuration scripts, and dataset loading pipeline methods.

## Unverified Items

- Model accuracy/convergence on full training run — reason not verified: full training (20 epochs) is time/resource-intensive and not required to verify code correctness and structural constraints.

---

## Challenge Summary (Adversarial Review)

**Overall risk assessment**: LOW

## Challenges

### Low Challenge 1: Empty Class Folder Crash
- **Assumption challenged**: Each subdirectory in the training dataset (`dark`, `fair`, `light`) contains at least one image file.
- **Attack scenario**: If a dataset split is corrupted or missing images in a specific class folder, `count` will be 0.
- **Blast radius**: Division by zero exception when calculating class weights.
- **Mitigation**: The implementation is robust as it handles this edge case via: `class_weights[i] = total_samples / (num_classes * count) if count > 0 else 1.0`.

### Low Challenge 2: Label Mode Incompatibility between training and inference
- **Assumption challenged**: The number of classes in training matches the expectation in inference.
- **Attack scenario**: The training dataset uses 3 folders (`dark`, `fair`, `light`), but default classifier construction builds 5 classes.
- **Blast radius**: IndexOutOfRange / shape mismatch when loading weights or running inference.
- **Mitigation**: During classifier initialization in `skin_tone_classifier.py`, `build_skin_tone_classifier(num_classes=3)` is explicitly instantiated with 3 classes, matching the training dataset classes exactly.
