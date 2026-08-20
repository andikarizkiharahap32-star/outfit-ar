# Review Report — Milestone 1 (CNN & Backbone Fixes)

## Review Summary

**Verdict**: APPROVE

The CNN backbone fixes applied by the Worker successfully resolve all designated bugs (#2, #8, #13, and #15) while adhering to correct TF/Keras engineering guidelines. The head layer sequence is constructed properly, data augmentation is placed correctly in the TF dataset pipeline, and class weights are computed dynamically.

---

## Findings

### [Minor] Finding 1: File Counting for Class Weights

- **What**: The script counts all items in directory to compute class counts.
- **Where**: `train_cnn.py`, line 65-66:
  ```python
  count = len([f for f in os.listdir(class_path) if os.path.isfile(os.path.join(class_path, f))])
  ```
- **Why**: Non-image files (e.g., `.DS_Store`, `.gitkeep`, `readme.txt`) will be counted, but `image_dataset_from_directory` will ignore them. This can cause a minor discrepancy in the computed class weights.
- **Suggestion**: Check file extensions (e.g., `.jpg`, `.jpeg`, `.png`, `.bmp`) when counting:
  ```python
  IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.bmp'}
  count = len([f for f in os.listdir(class_path) if os.path.isfile(os.path.join(class_path, f)) and os.path.splitext(f.lower())[1] in IMAGE_EXTS])
  ```

---

## Verified Claims

- **Claim 1**: Data augmentation layers (`RandomFlip`, `RandomRotation`, `RandomBrightness`, `RandomContrast`) are implemented and mapped after caching but before prefetching.
  - *Method*: Inspected `train_cnn.py` lines 78-90 and ran a validation python snippet ensuring Keras Sequential block instantiates correctly.
  - *Result*: **PASS**
- **Claim 2**: Class weights are computed dynamically and passed to `model.fit()`.
  - *Method*: Inspected `train_cnn.py` lines 63-72 (dynamic directory check) and line 136 (passed to `model.fit`).
  - *Result*: **PASS**
- **Claim 3**: The Dense head layer ordering in `efficientnet_backbone.py` is strictly: Dense (linear, use_bias=False, L2 regularizer of 1e-4) -> BatchNormalization -> Activation (relu) -> Dropout (0.4) -> Dense (softmax).
  - *Method*: Ran `verify_model.py` which builds the model and programmatically asserts layer class types, activation, bias, and kernel regularizer configurations.
  - *Result*: **PASS**
- **Claim 4**: Run unit/verification tests using `backend/venv_fix/Scripts/python.exe`.
  - *Method*: Executed `backend/venv_fix/Scripts/python.exe backend/ml/cnn/verify_model.py` and obtained a successful exit code (0) and log confirming verification passed.
  - *Result*: **PASS**

---

## Coverage Gaps

- **Verify training convergence with large epoch run** — Risk level: **LOW** — Recommendation: Accept risk. Executing training for 20 full epochs is computationally heavy and unnecessary for confirming structural and integration correctness of the pipeline.

---

## Unverified Items

- **MediaPipe Segmentation and DeepFace integrations in skin_tone_classifier.py** — Reason not verified: Out of scope for Milestone 1 backbone structural fixes, but code imports `build_skin_tone_classifier` correctly.

---

## Challenge Summary

**Overall risk assessment**: LOW

The structural implementation is solid. The primary risks lie in the dataset uniformity and static hyperparameter limits.

---

## Challenges

### [Medium] Challenge 1: Label Order Mismatch Risk

- **Assumption challenged**: The class folder directory names in the training dataset are identical and will map to the same order in both train and validation datasets.
- **Attack scenario**: A class folder name has mismatching case in validation (e.g. `valid/Dark` vs `train/dark`), or a folder is empty.
- **Blast radius**: `image_dataset_from_directory` sorts folders alphabetically. Case discrepancies (e.g. `Dark` vs `dark`) will cause the training and validation labels to map to different index representations, yielding invalid training results and corrupt validation metrics.
- **Mitigation**: Add a sanity check asserting `train_dataset.class_names == valid_dataset.class_names`.

### [Low] Challenge 2: Static Learning Rate

- **Assumption challenged**: A static learning rate of `1e-4` is optimal throughout the entire training process.
- **Attack scenario**: The learning rate becomes too high once fine-tuning approaches a local minimum, leading to loss oscillation.
- **Blast radius**: Suboptimal model convergence or validation accuracy.
- **Mitigation**: Introduce a learning rate scheduler callback (e.g., `ReduceLROnPlateau`) in `model.fit()`.

---

## Stress Test Results

- **Non-image files present in class folders** $\rightarrow$ Counted in class count but skipped by loader $\rightarrow$ Small class weight discrepancy $\rightarrow$ **PASS** (handled safely by python checking logic).
- **Empty class folder** $\rightarrow$ `count == 0` check defaults to `1.0` $\rightarrow$ No division by zero error $\rightarrow$ **PASS**.
- **Execution of model layer checker** $\rightarrow$ Layer configurations dynamically read and verified $\rightarrow$ Output matches expectation $\rightarrow$ **PASS**.

---

## Unchallenged Areas

- **GPU memory capacity under large batch training** — Reason: Tests run on CPU context; batch training limits are hardware-dependent.
