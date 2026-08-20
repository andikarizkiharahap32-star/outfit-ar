# Challenge Report - Milestone 1

## Challenge Summary

**Overall risk assessment**: LOW

All five key tests passed. The backbone and custom classification head compile, update weights, apply data augmentation under load, calculate class weights, and extract features across different shapes stably. However, two minor architecture/performance improvements and a bug in the new gender detection integration were identified.

---

## Challenges

### [Medium] Challenge 1: DeepFace Gender Analysis Call Without Availability Check

- **Assumption challenged**: Assumed `DeepFace` is always loaded successfully if the `import` fails and falls back to `None`.
- **Attack scenario**: If DeepFace fails to import (e.g. `gdown` dependency or other package metadata issue), `DeepFace` is set to `None`. However, `detect()` still attempts to call `DeepFace.analyze(...)`. This throws an `AttributeError: 'NoneType' object has no attribute 'analyze'`. Although caught by a generic try-except, it wastes computational overhead with exception handling on every single image detection.
- **Blast radius**: Increased latency on skin tone detection and unnecessary log warnings (`[SkinTone] Deteksi Gender DeepFace gagal: 'NoneType' object has no attribute 'analyze'`).
- **Mitigation**: Add a guard condition `if _DEEPFACE_AVAILABLE and DeepFace is not None:` before invoking `DeepFace.analyze()`.

### [Low] Challenge 2: Dual Backbone Forward Passes (Efficiency Overhead)

- **Assumption challenged**: Assumed calling model prediction and backbone extraction separately is optimal.
- **Attack scenario**: In `_predict_cnn()`, the code first runs `probs = self._model.predict(input_tensor)` (which passes through the entire model, including EfficientNet-B0). Then it separately calls `extractor(input_tensor, training=False)` (which runs EfficientNet-B0 a second time). Under heavy concurrent load, this doubles the inference computation for the CNN.
- **Blast radius**: Computational overhead, high response times under load, higher GPU/CPU utilization.
- **Mitigation**: Redefine the Keras Functional model to output both the classification logits and the bottleneck/feature layer output simultaneously, i.e., `model = keras.Model(inputs, [outputs, features])`. This achieves single-pass execution.

---

## Stress Test Results

The verification script `backend/tests/stress_test_ms1.py` was executed successfully.

### Test 1: Custom Head Layer Order and Properties
- **Scenario**: Validate order of custom head layers and check dense layer hyperparameters.
- **Expected behavior**: Order: `head_dense` (Dense, no bias, L2=1e-4) -> `head_bn` (BatchNormalization) -> `head_activation` (relu) -> `head_dropout` (rate=0.4) -> `skin_tone_output` (Dense).
- **Actual behavior**: Verified exactly as specified. L2 config successfully parsed.
- **Status**: PASS

### Test 2: Gradient Propagation and Weight Updates
- **Scenario**: Perform forward pass on a mock batch, calculate loss, compute gradients via `GradientTape`, apply gradients via Adam, and check if weights change.
- **Expected behavior**: Gradients calculated for `head_dense` and `head_bn`, weights updated.
- **Actual behavior**: 
  - `head_dense` kernel grad sum: `2687.59` (non-zero)
  - `head_bn` gamma grad sum: `4.62` (non-zero)
  - Dense kernel weight change: `303.06`
  - BN gamma weight change: `0.21`
  - BN beta weight change: `0.21`
- **Status**: PASS

### Test 3: Data Augmentation Pipeline under Load
- **Scenario**: Apply RandomFlip, RandomRotation, RandomBrightness, RandomContrast sequence on 20 batches of size 32 (640 total images).
- **Expected behavior**: Process successfully without shape mismatches or resource exhaustion.
- **Actual behavior**: Processed 640 images in `2.17` seconds (avg `295.43` images/sec).
- **Status**: PASS

### Test 4: Dynamic Class Weights & Mock Training
- **Scenario**: Compute weights for imbalanced class counts `[80, 15, 5]` and train model for 2 epochs.
- **Expected behavior**: Minor classes scaled inversely to frequencies. Train without crashing.
- **Actual behavior**: 
  - Class weights: `0: 0.42`, `1: 2.22`, `2: 6.67`.
  - Epoch 1 loss: `1.6541` -> Epoch 2 loss: `1.6999`. Completed training successfully.
- **Status**: PASS

### Test 5: Inference Shape Stability
- **Scenario**: Run inference on random noise images of sizes `100x100`, `224x224`, `480x640`, and `1920x1080` using `SkinToneClassifier` and `OutfitFeatureExtractor`.
- **Expected behavior**: Dynamic resizing scales inputs to `(224, 224, 3)` and runs without tensor shape mismatch crashes.
- **Actual behavior**: 
  - `SkinToneClassifier` returned `SkinToneResult` (level 1-3, 1280-dim feature vector).
  - `OutfitFeatureExtractor` single returns `(1377,)` vector.
  - `OutfitFeatureExtractor` batch returns `(5, 1377)` matrix.
- **Status**: PASS

---

## Unchallenged Areas

- **Real face accuracy under augmentations** — Not challenged because our task is to stress-test the pipeline stability, compile config, and layer mechanics using mock data, rather than measuring final validation accuracy metrics.
