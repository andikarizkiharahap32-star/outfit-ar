# Exploration & Analysis Report — Milestone 1 (CNN & Backbone Fixes)

This report details the findings from the investigation of the CNN backbone and training pipeline, the analysis of the verification script failure (`verify_model.py`), and the proposed concrete fixes to resolve the bugs and integrity violation.

---

## 1. Findings & Verification Failure Analysis

### The Verification Failure
Executing `backend/ml/cnn/verify_model.py` fails with exit code `1` and prints the following error:
```
2026-06-28 09:57:23.399 | ERROR    | __main__:main:47 - head_dense use_bias should be False
2026-06-28 09:57:23.399 | ERROR    | __main__:main:59 - Verification FAILED: Layer mismatch found.
```

### Cause of Failure
The verification script inspects the layer structure of the skin tone classifier. Specifically, in `backend/ml/cnn/verify_model.py` (lines 46-48), it asserts:
```python
                if layer.use_bias:
                    logger.error("head_dense use_bias should be False")
                    match = False
```
However, in `backend/ml/cnn/efficientnet_backbone.py` (lines 46-52), the Dense layer `"head_dense"` is defined with `use_bias=True`:
```python
    x = keras.layers.Dense(
        256,
        activation=None,
        use_bias=True,
        kernel_regularizer=keras.regularizers.L2(1e-4),
        name="head_dense",
    )(x)
```
This violates the architectural constraint (Bugs #8 and #15) requiring `use_bias=False` for any Dense layer followed immediately by a BatchNormalization layer. In this case, `BatchNormalization` shifts the inputs by its learned offset parameter ($\beta$), which renders any preceding Dense bias mathematically redundant and adds unnecessary parameter overhead.

---

## 2. Review of Milestone 1 Bugs

### Bug #2: Data Augmentation in CNN training in `train_cnn.py`
- **Location**: `backend/ml/cnn/train_cnn.py` (lines 78-88)
- **Status**: The data augmentation pipeline is correctly implemented using Keras `RandomFlip`, `RandomRotation`, `RandomBrightness`, and `RandomContrast` layers.
- **Ordering**: The data augmentation is mapped *after* `.cache()` but *before* `.prefetch()`, which is correct: it avoids caching augmented images (which would cause identical augmentations to be repeated across epochs) and allows on-the-fly random transformations on cached raw images.

### Bug #8: Layer Order in `efficientnet_backbone.py`
- **Location**: `backend/ml/cnn/efficientnet_backbone.py` (lines 46-55)
- **Status**: The sequential head order is currently `Dense -> BatchNormalization -> Activation -> Dropout`, which is correct. However, `use_bias` is incorrectly set to `True` for `head_dense`, violating the redundancy constraint. We need to set `use_bias=False` to pass the model structure verification.

### Bug #13: Class Weights in `train_cnn.py`
- **Location**: `backend/ml/cnn/train_cnn.py` (lines 62-72, 136)
- **Status**: Class counts are computed dynamically by listing directories under `TRAIN_DIR` for each class. The class weights are computed using the balanced formula:
  $$W_i = \frac{\text{total\_samples}}{\text{num\_classes} \times \text{class\_count}_i}$$
  and are passed to `model.fit(..., class_weight=class_weights)`. This is correctly implemented.

### Bug #15: Learning Rate and Regularization
- **Location**: `backend/ml/cnn/train_cnn.py` (line 100) & `backend/ml/cnn/efficientnet_backbone.py` (line 50)
- **Status**:
  - The Adam optimizer learning rate is set to `1e-4` in `train_cnn.py`, which is appropriate for fine-tuning.
  - The L2 regularizer coefficient is set to `1e-4` on `head_dense` in `efficientnet_backbone.py`.
  - Disabling the bias of `head_dense` is also required as part of the regularization and head cleanup.

---

## 3. Proposed Exact Code Changes

### Proposed Change for `backend/ml/cnn/efficientnet_backbone.py`

Modify the dense head instantiation to disable the bias parameter (`use_bias=False`).

- **File**: `backend/ml/cnn/efficientnet_backbone.py`
- **Line Range**: 46-52
- **Change type**: Replacement

**Before**:
```python
    x = keras.layers.Dense(
        256,
        activation=None,
        use_bias=True,
        kernel_regularizer=keras.regularizers.L2(1e-4),
        name="head_dense",
    )(x)
```

**After**:
```python
    x = keras.layers.Dense(
        256,
        activation=None,
        use_bias=False,
        kernel_regularizer=keras.regularizers.L2(1e-4),
        name="head_dense",
    )(x)
```

---

## 4. Verification Instructions

To verify the fixes independently, run the following steps:

1. **Verify Model Structure**:
   Execute the verification script to verify that the layer sequence, activation, regularizer, and bias configurations are correct:
   ```powershell
   C:\Final_outfitAR\outfit-ar\backend\venv_fix\Scripts\python.exe C:\Final_outfitAR\outfit-ar\backend\ml\cnn\verify_model.py
   ```
   *Expected Output*: Exit code `0` and a log statement stating `Verification PASSED: All head layers are correct and in the correct order.`

2. **Execute Pytest Suite**:
   Run the pytest suite to ensure that all other test cases remain intact and pass:
   ```powershell
   C:\Final_outfitAR\outfit-ar\backend\venv_fix\Scripts\python.exe -m pytest C:\Final_outfitAR\outfit-ar\backend\tests\test_audit_bugs.py
   ```
   *Expected Output*: All 14 tests pass successfully with no failures.
