# Changes Report — Milestone 1 Fixes

This report outlines the modifications made to the CNN backbone and training script in order to resolve Bugs #2, #8, #13, and #15.

## 1. Data Augmentation Setup (Bug #2)
- **File**: `backend/ml/cnn/train_cnn.py`
- **Details**:
  - Defined the `data_augmentation` sequential block containing `RandomFlip`, `RandomRotation`, `RandomBrightness`, and `RandomContrast` layers.
  - Applied the augmentation to `train_dataset` using `.map()` with `training=True`.
  - Scaled the mapping order such that it is mapped **after** `.cache()` but **before** `.prefetch()` to prevent caching augmented variants or slowing down data retrieval.
  - Left `valid_dataset` unaugmented (only `.cache().prefetch(...)` applied).

## 2. Model Head Layer Reordering & L2 Regularization (Bug #8 & Bug #15)
- **File**: `backend/ml/cnn/efficientnet_backbone.py`
- **Details**:
  - Reordered the classification head to:
    1. `Dense(256, activation=None, use_bias=False, kernel_regularizer=keras.regularizers.L2(1e-4), name="head_dense")`
    2. `BatchNormalization(name="head_bn")`
    3. `Activation("relu", name="head_activation")`
    4. `Dropout(0.4, name="head_dropout")`
    5. Final `Dense` output layer with softmax activation.
  - This ensures that normalization happens before the non-linear activation function, and regularizes the dense layer properly.

## 3. Dynamic Class Weight Calculation (Bug #13)
- **File**: `backend/ml/cnn/train_cnn.py`
- **Details**:
  - Added code to count training samples per category folder dynamically using `os.listdir`.
  - Calculated weights using the standard formula: `total_samples / (num_classes * count)`.
  - Passed `class_weight=class_weights` into the `model.fit()` call to handle class imbalance.

## 4. Learning Rate Adjustment (Bug #15)
- **File**: `backend/ml/cnn/train_cnn.py`
- **Details**:
  - Adjusted the Adam optimizer's learning rate from `0.001` to `1e-4` to stabilize gradient steps when fine-tuning.

## Verification Executed
- Implemented `verify_model.py` which dynamically imports `efficientnet_backbone.py` and constructs the classifier to assert and verify:
  - Exact layer sequence in the classification head.
  - Disabling of activation and bias in `head_dense`.
  - Presence and correctness of the L2 regularization coefficient (`1e-4`).
- Executed verification in the local environment `backend/venv_fix/Scripts/python.exe`.
- Result: **Verification PASSED**.
