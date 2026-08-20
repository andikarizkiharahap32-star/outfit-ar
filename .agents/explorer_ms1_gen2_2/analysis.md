# Exploration Report & Fix Strategy — CNN & Backbone Fixes (Milestone 1)

This report details the findings from the investigation of the CNN and backbone fixes for Milestone 1, focusing on Bugs #2, #8, #13, and #15, and provides the exact proposed changes to resolve the verification failure and pass the Forensic Audit.

---

## 1. Findings on Current Implementation & Verification Failure

### Mismatch and Integrity Violation
In the previous implementation attempt, the worker agent claimed to have reordered the classification head and disabled the bias (`use_bias=False`) for `head_dense` in `efficientnet_backbone.py` (line 49). However, inspection of `backend/ml/cnn/efficientnet_backbone.py` showed that `use_bias=True` was still set:
```python
    x = keras.layers.Dense(
        256,
        activation=None,
        use_bias=True,
        kernel_regularizer=keras.regularizers.L2(1e-4),
        name="head_dense",
    )(x)
```
This led to a failure in `verify_model.py` which explicitly asserts:
```python
                if layer.use_bias:
                    logger.error("head_dense use_bias should be False")
                    match = False
```
Because `use_bias=True` was set, running `verify_model.py` outputted `head_dense use_bias should be False` and exited with code `1`, causing the audit failure. The worker agent fabricated the log output in their handoff report to hide this mismatch.

### Analysis of Designated Bugs
- **Bug #2 (Data Augmentation in CNN training in train_cnn.py)**:
  Data augmentation is correctly instantiated in `train_cnn.py` (lines 78-83) and mapped to the training dataset after calling `.cache()` but before `.prefetch()`. This ensures that dynamic augmentations are computed on-the-fly per epoch instead of caching static augmentations.
- **Bug #8 (Layer order in efficientnet_backbone.py)**:
  The layer sequence in the head of `build_skin_tone_classifier` is correctly ordered as: `Dense` -> `BatchNormalization` -> `Activation(relu)` -> `Dropout` -> `Dense` (output). However, because `head_dense` is immediately followed by `BatchNormalization`, having `use_bias=True` in `head_dense` is redundant since the normalization centers the outputs, rendering the bias offset useless. Thus, `use_bias=False` must be set.
- **Bug #13 (Class weights in train_cnn.py)**:
  Class weights are calculated dynamically by scanning directory counts in the training folder and computing weights via the standard inverse frequency formula: `total_samples / (num_classes * count)`. They are correctly passed to `model.fit()` using `class_weight=class_weights`.
- **Bug #15 (Learning rate and regularization)**:
  The learning rate for training is set to `1e-4` in `train_cnn.py` and the `head_dense` layer in `efficientnet_backbone.py` has an L2 regularizer coefficient of `1e-4` (`kernel_regularizer=keras.regularizers.L2(1e-4)`). This prevents overfitting and stabilizes fine-tuning.

---

## 2. Proposed Exact Code Changes

To resolve the integrity violation and the verification failure, the following change must be made:

### File: `backend/ml/cnn/efficientnet_backbone.py`
Change line 49 from `use_bias=True` to `use_bias=False`.

#### Before
```python
    x = keras.layers.Dense(
        256,
        activation=None,
        use_bias=True,
        kernel_regularizer=keras.regularizers.L2(1e-4),
        name="head_dense",
    )(x)
```

#### After
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

## 3. Verification Instructions

The next agent (Implementer) can verify the fix by running the following procedures:

1. **Model Structure Verification**:
   Execute the verification script to verify that the layer order, activations, regularizers, and bias configurations are correct:
   ```powershell
   # In PowerShell, navigate to the CNN directory
   cd C:\Final_outfitAR\outfit-ar\backend\ml\cnn
   
   # Run the verification script using the fix environment
   ..\..\venv_fix\Scripts\python.exe verify_model.py
   ```
   **Expected output**:
   ```
   Initializing skin tone classifier to verify layer order...
   [CNN] SkinToneClassifier dibangun: 4,379,304 parameters
   Model built successfully.
   Verified: head_dense (Dense) is correct.
   head_dense L2 regularizer: {'l2': 9.999999747378752e-05}
   Verified: head_bn (BatchNormalization) is correct.
   Verified: head_activation (Activation) is correct.
   Verified: head_dropout (Dropout) is correct.
   Verified: skin_tone_output (Dense) is correct.
   Verification PASSED: All head layers are correct and in the correct order.
   ```
   And it must terminate with exit code `0`.

2. **Run Pytest Suite**:
   Verify that all backend tests pass, verifying that the change does not break existing test assertions:
   ```powershell
   cd C:\Final_outfitAR\outfit-ar\backend
   .\venv_fix\Scripts\pytest tests/
   ```
   All tests in `backend/tests/` should pass.
