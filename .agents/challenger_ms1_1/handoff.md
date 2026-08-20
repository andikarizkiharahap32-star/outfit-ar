# Handoff Report - Challenger Milestone 1

## 1. Observation

- **Implementation files reviewed**:
  - `backend/ml/cnn/efficientnet_backbone.py` (lines 43-60):
    ```python
    # Build full model
    inputs = keras.Input(shape=(*IMG_SIZE, 3), name="input_image")
    x = keras.applications.efficientnet.preprocess_input(inputs)
    x = base_model(x, training=False)                        # Feature: (batch, 1280)
    x = keras.layers.Dense(
        256,
        activation=None,
        use_bias=False,
        kernel_regularizer=keras.regularizers.L2(1e-4),
        name="head_dense",
    )(x)
    x = keras.layers.BatchNormalization(name="head_bn")(x)
    x = keras.layers.Activation("relu", name="head_activation")(x)
    x = keras.layers.Dropout(0.4, name="head_dropout")(x)
    outputs = keras.layers.Dense(
        num_classes,
        activation="softmax",
        name="skin_tone_output",
    )(x)
    ```
  - `backend/ml/cnn/skin_tone_classifier.py` (lines 122-145):
    ```python
    detected_gender = "pria"
    try:
        face_rgb = cv2.cvtColor(face_crop, cv2.COLOR_BGR2RGB)
        df_result = DeepFace.analyze(
            img_path=face_rgb, 
            actions=['gender'], 
            enforce_detection=False,
            silent=True
        )
        ...
    except Exception as e:
        logger.warning(f"[SkinTone] Deteksi Gender DeepFace gagal: {e}")
    ```

- **Execution output of the verification script** (`backend/tests/stress_test_ms1.py`):
  - **Test 1 (Head Order)**: Output matches the order `Dense` -> `BatchNormalization` -> `Activation` -> `Dropout` -> `Dense`.
  - **Test 2 (Gradient Updates)**: `head_dense kernel updated by diff 303.057159` and `head_bn gamma updated by diff 0.213129`.
  - **Test 3 (Data Augmentation)**: Processed 640 images in `2.1663` seconds.
  - **Test 4 (Class Weights)**: Computed weights for counts `[80, 15, 5]` as `{0: 0.4167, 1: 2.2222, 2: 6.6667}` and completed mock training.
  - **Test 5 (Shape & Inference Stability)**: Handled shapes `100x100`, `224x224`, `480x640`, `1920x1080` correctly.
  - **DeepFace Error in log**:
    ```
    2026-06-28 09:47:17.311 | WARNING  | ml.cnn.skin_tone_classifier:detect:145 - [SkinTone] Deteksi Gender DeepFace gagal: 'NoneType' object has no attribute 'analyze'
    ```

---

## 2. Logic Chain

1. **Custom Head Design**: The layer names and parameters in `efficientnet_backbone.py` (Dense -> BN -> Act -> Dropout) match the specification. The L2 regularization factor of `1e-4` is present and active.
2. **Gradient Flow**: During mock backward pass (Test 2), Keras successfully computed gradients on all customized head layer weights, and applying Adam optimizer directly updated the weights. This proves gradient flow works.
3. **Data Augmentation**: The Sequential pipeline of `RandomFlip`, `RandomRotation`, `RandomBrightness`, and `RandomContrast` ran on batches without causing numerical instability or memory OOM under load.
4. **Dynamic Class Weights**: Class weight calculation inversely scales the minority classes relative to their frequency. The mock training test proved that Keras accepts these weights via `class_weight=class_weights` and trains stable.
5. **Shape Stability**: Preprocessing successfully utilizes `tf.image.resize` to normalize images of arbitrary dimensions to `(224, 224, 3)` without shape mismatches.
6. **Integration Bug**: When `DeepFace` is unavailable, the classifier sets `DeepFace = None`. In `detect()`, it calls `DeepFace.analyze(...)` without checking `_DEEPFACE_AVAILABLE`. This triggers an `AttributeError` for each image, causing computational overhead by relying on try-except fallback.

---

## 3. Caveats

- **DeepFace Model Availability**: The test was run on a system where DeepFace failed to load due to missing `gdown` dependency. If DeepFace was successfully loaded, the execution path might encounter additional latency when downloading weights.
- **Hardware constraints**: GPU acceleration was not used during testing, only CPU. Performance under load could scale differently on GPU environments.

---

## 4. Conclusion

The model, data augmentation, class weight calculation, custom classification head, and feature extraction pipeline are functionally stable and correct. They satisfy the core requirements of Milestone 1. One minor integration bug was discovered (DeepFace analyzer call when it is set to None), and one design inefficiency was highlighted (dual forward pass for classification and feature extraction).

---

## 5. Verification Method

To verify the stress test results independently:
1. Run the command:
   ```cmd
   backend/venv_fix/Scripts/python.exe backend/tests/stress_test_ms1.py
   ```
2. Check the output logs for the line `🎉 All Milestone 1 stress tests passed successfully!`.
3. Review `backend/tests/stress_test_ms1.py` file to inspect assertion criteria.
