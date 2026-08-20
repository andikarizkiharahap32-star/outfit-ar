# Challenge Report

## Challenge Summary

**Overall risk assessment**: MEDIUM

- We identified two distinct issues in the CNN & backbone implementation.
- First, the classifier head's `head_dense` layer uses bias (`use_bias=True`) on disk, which directly violates the specification requirement ("no bias"). This adds 256 redundant parameters and diverges from the target architecture.
- Second, during feature extraction in the ensemble detection pipeline (`SkinToneClassifier._predict_cnn`), the backbone is called directly on raw inputs `extractor(input_tensor)` rather than preprocessed inputs, bypassing the `preprocess_input` layer. This leads to incorrect feature representation vectors.

---

## Challenges

### [Medium] Challenge 1: Classifier Head `use_bias` Mismatch
- **Assumption challenged**: The model classifier head conforms exactly to the specification of "Dense (linear, no bias, L2 regularizer of 1e-4)".
- **Attack scenario**: The model compiled and executed during training. However, the parameter count was 4,379,302 instead of the expected 4,379,046. The extra 256 weights are bias parameters in `head_dense` because `use_bias` is set to `True` in `backend/ml/cnn/efficientnet_backbone.py` at line 49.
- **Blast radius**: Redundant parameters in the head, potential minor overfitting risk, and architectural inconsistency.
- **Mitigation**: Update `backend/ml/cnn/efficientnet_backbone.py` at line 49 to set `use_bias=False`.

### [High] Challenge 2: Bypassed Preprocessing in Feature Extraction
- **Assumption challenged**: Features extracted by the classifier's backbone match the classification features and are properly normalized.
- **Attack scenario**: In `SkinToneClassifier._predict_cnn` (file: `backend/ml/cnn/skin_tone_classifier.py` lines 188-194):
  ```python
  probs = self._model.predict(input_tensor, verbose=0)[0]   # (3,)
  extractor = self._model.get_layer("efficientnetb0")
  feature_vec = extractor(input_tensor, training=False).numpy()[0]
  ```
  While `self._model.predict` runs the entire model (including the preprocessing layer `preprocess_input`), `extractor` is a direct reference to the `efficientnetb0` backbone layer. Calling `extractor(input_tensor)` directly feeds raw image values `[0, 255]` into the backbone, completely bypassing the `preprocess_input` normalization.
- **Blast radius**: Feature vectors are extracted using unnormalized pixel data, leading to severe numerical shift and degradation in the downstream KNN recommendation system (`outfit_recommender.py`).
- **Mitigation**: Preprocess the input before passing it to the backbone extractor:
  ```python
  preprocessed_input = tf.keras.applications.efficientnet.preprocess_input(input_tensor)
  feature_vec = extractor(preprocessed_input, training=False).numpy()[0]
  ```

---

## Stress Test Results

- **Model structure & layer sequence verification** → Verify expected layer type, ordering, activations, and L2 parameters → **FAILED** due to `head_dense` having `use_bias: True` (expected `False`).
- **Data augmentation under load** → Run 100 iterations of RandomFlip, RandomRotation, RandomBrightness, RandomContrast with size (32, 224, 224, 3) → **PASSED** (completed in 7.02s with no errors, shape mismatches, or invalid numbers).
- **Gradient propagation & weight updates** → Verify that custom head layers receive non-zero gradients and update weights after an optimizer step → **PASSED** (gradient norms: `head_dense/kernel`: 15.07, `head_bn/gamma`: 0.46, `head_bn/beta`: 0.61, `skin_tone_output/kernel`: 4.77, `skin_tone_output/bias`: 0.39; weights updated successfully).
- **Dynamic class weights balancing** → Prove dynamic class weights calculation and run 1 epoch on imbalanced mock dataset → **PASSED** (Class weights successfully scaled losses: Class 0 weight=0.37, Class 2 weight=18.67; loss scaling factor matches sample imbalance ratio of 50.0).
- **Inference & feature extraction stability** → Test inference on batch sizes 1, 4, and 16 → **PASSED** (No shape mismatches or crashes observed).

---

## Unchallenged Areas

- **MediaPipe Selfie Segmentation and DeepFace Gender Detection** — Not challenged under load in this specific test script because they rely on external binary models and libraries (`mediapipe`, `deepface`) which were out of scope for the backbone/CNN architectural stress test.
