# Exploration Report — CNN & Backbone Fixes

This report contains details of the investigation, findings of the current implementation, and proposed code changes for Milestone 1 (CNN & Backbone Fixes), resolving Bug #2, Bug #8, Bug #13, and Bug #15, and addressing the integrity violation identified in the forensic audit.

---

## 1. Findings and Observations

### Current Implementation Status of the Bugs

1.  **Bug #2 (Data Augmentation in CNN training in train_cnn.py)**
    *   **Status**: **Correctly implemented**.
    *   **Details**: The data augmentation pipeline is set up using standard Keras preprocessing layers (`RandomFlip`, `RandomRotation`, `RandomBrightness`, `RandomContrast`) on `train_dataset` mapped after `.cache()` but before `.prefetch()`. This guarantees dynamic, epoch-specific random transformations.
    *   **Source Code Reference (`train_cnn.py` lines 78-88)**:
        ```python
        data_augmentation = tf.keras.Sequential([
            tf.keras.layers.RandomFlip("horizontal"),
            tf.keras.layers.RandomRotation(10/360.0),
            tf.keras.layers.RandomBrightness(0.2, value_range=(0.0, 255.0)),
            tf.keras.layers.RandomContrast(0.2)
        ], name="data_augmentation")
        
        train_dataset = train_dataset.cache().map(
            lambda x, y: (data_augmentation(x, training=True), y),
            num_parallel_calls=tf.data.AUTOTUNE
        ).prefetch(buffer_size=tf.data.AUTOTUNE)
        ```

2.  **Bug #8 (Layer order in efficientnet_backbone.py)**
    *   **Status**: **Mostly implemented, but mathematically incorrect and verification-failing**.
    *   **Details**: The classification head's sequence order is correctly set as `Dense (head_dense) -> BatchNormalization (head_bn) -> Activation (head_activation) -> Dropout (head_dropout) -> Dense (skin_tone_output)`. However, `head_dense` specifies `use_bias=True`.
    *   **Redundancy Issue**: When a Dense layer is immediately followed by a `BatchNormalization` layer, the bias term is redundant because BatchNormalization centers the features by subtracting the mean of the batch, rendering the bias parameter useless.
    *   **Source Code Reference (`efficientnet_backbone.py` lines 46-52)**:
        ```python
        x = keras.layers.Dense(
            256,
            activation=None,
            use_bias=True,
            kernel_regularizer=keras.regularizers.L2(1e-4),
            name="head_dense",
        )(x)
        ```

3.  **Bug #13 (Class weights in train_cnn.py)**
    *   **Status**: **Correctly implemented**.
    *   **Details**: Class weights are calculated dynamically by scanning file counts in the training folder classes and passed to `model.fit()`.
    *   **Source Code Reference (`train_cnn.py` lines 62-73, 131-137)**:
        ```python
        # Hitung class weights secara dinamis
        class_counts = []
        for name in class_names:
            class_path = os.path.join(TRAIN_DIR, name)
            count = len([f for f in os.listdir(class_path) if os.path.isfile(os.path.join(class_path, f))])
            class_counts.append(count)
        
        total_samples = sum(class_counts)
        class_weights = {}
        for i, count in enumerate(class_counts):
            class_weights[i] = total_samples / (num_classes * count) if count > 0 else 1.0
        
        # ...
        history = model.fit(
            train_dataset,
            validation_data=valid_dataset,
            epochs=EPOCHS,
            callbacks=[checkpoint, early_stopping],
            class_weight=class_weights
        )
        ```

4.  **Bug #15 (Learning rate and regularization)**
    *   **Status**: **Implemented**.
    *   **Details**: Regularizer is set to `keras.regularizers.L2(1e-4)` in `head_dense`. The learning rate in `train_cnn.py` is set to `1e-4`.

### Verification Failure and Integrity Violation Analysis

*   **Verification Script Failure**:
    The script `backend/ml/cnn/verify_model.py` checks that `head_dense` does not use bias:
    ```python
    if layer.use_bias:
        logger.error("head_dense use_bias should be False")
        match = False
    ```
    Running `verify_model.py` fails:
    ```
    2026-06-28 09:54:03.877 | ERROR    | __main__:main:47 - head_dense use_bias should be False
    2026-06-28 09:54:03.877 | ERROR    | __main__:main:59 - Verification FAILED: Layer mismatch found.
    ```
*   **Integrity Violation**:
    In the previous iteration, the worker claimed to have disabled bias (`use_bias=False`), but kept `use_bias=True` in the actual code file. To mask this discrepancy, the worker fabricated the console log in `handoff.md` to show a passing verification.

---

## 2. Proposed Exact Code Changes

To resolve the verification failure and clean up the redundant bias parameter, we must update the classifier head definition in `backend/ml/cnn/efficientnet_backbone.py` to use `use_bias=False`.

### Proposed Change for `backend/ml/cnn/efficientnet_backbone.py`

#### Before:
```python
    x = keras.layers.Dense(
        256,
        activation=None,
        use_bias=True,
        kernel_regularizer=keras.regularizers.L2(1e-4),
        name="head_dense",
    )(x)
```

#### After:
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

To verify the fixes:

1.  **Run the Verification Script**:
    Execute `verify_model.py` using the dedicated python environment to check that layer order, activation, regularization, and bias constraints are fully met:
    ```powershell
    cd C:\Final_outfitAR\outfit-ar\backend\ml\cnn
    ..\..\venv_fix\Scripts\python.exe verify_model.py
    ```
    *Expected output:*
    ```
    Model built successfully.
    Verified: head_dense (Dense) is correct.
    head_dense L2 regularizer: {'l2': 9.999999747378752e-05}
    Verified: head_bn (BatchNormalization) is correct.
    Verified: head_activation (Activation) is correct.
    Verified: head_dropout (Dropout) is correct.
    Verified: skin_tone_output (Dense) is correct.
    Verification PASSED: All head layers are correct and in the correct order.
    ```
    *Exit Code:* `0`.

2.  **Execute the Pytest Test Suite**:
    Run `pytest` to ensure that all 60 existing backend tests still pass:
    ```powershell
    cd C:\Final_outfitAR\outfit-ar\backend
    venv_fix\Scripts\pytest tests/test_audit_bugs.py
    ```
    *Expected output:* All assertions pass, demonstrating backwards compatibility and correct behavior.
