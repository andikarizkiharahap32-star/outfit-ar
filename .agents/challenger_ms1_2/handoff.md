# Handoff Report

## 1. Observation

- **Observation 1 (Dense head bias mismatch)**:
  Running the custom stress test command `backend\venv_fix\Scripts\python.exe .agents\challenger_ms1_2\stress_test_cnn.py` resulted in a Test 1 failure:
  ```
  --- Running Test 1: Model Structure & Layer Verification ---
  Model compiled successfully.
  ...
  head_dense use_bias: True
  head_dense activation: <function linear at ...>
  head_dense L2 config: {'l2': 9.999999747378752e-05}
  head_dropout rate: 0.4
  Test 1 FAILED with mismatches: ['head_dense should not use bias (use_bias=False)']
  ```
  And in `backend/ml/cnn/efficientnet_backbone.py` line 46-52:
  ```python
  x = keras.layers.Dense(
      256,
      activation=None,
      use_bias=True,
      kernel_regularizer=keras.regularizers.L2(1e-4),
      name="head_dense",
  )(x)
  ```

- **Observation 2 (Omitted preprocessing in feature extractor)**:
  In `backend/ml/cnn/skin_tone_classifier.py` lines 188-194:
  ```python
  def _predict_cnn(self, face_bgr: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
      face_rgb = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2RGB)
      input_tensor = preprocess_image(face_rgb)
      probs = self._model.predict(input_tensor, verbose=0)[0]   # (3,)
      extractor = self._model.get_layer("efficientnetb0")
      feature_vec = extractor(input_tensor, training=False).numpy()[0] 
      return probs, feature_vec
  ```
  But the preprocessing defined in `build_skin_tone_classifier` (in `efficientnet_backbone.py`) does:
  ```python
  inputs = keras.Input(shape=(*IMG_SIZE, 3), name="input_image")
  x = keras.applications.efficientnet.preprocess_input(inputs)
  x = base_model(x, training=False)
  ```

- **Observation 3 (Gradients and weight updates)**:
  Running the test command showed successful gradient propagation and weight update through the custom head:
  ```
  Gradient norms of head layers: {'head_dense/kernel': 15.074135780334473, 'head_dense/bias': 1.862820340647886e-06, 'head_bn/gamma': 0.45649254322052, 'head_bn/beta': 0.6068512201309204, 'skin_tone_output/kernel': 4.766880512237549, 'skin_tone_output/bias': 0.38591644167900085}
  Absolute weight change in head_dense: 296.075745
  Absolute weight change in skin_tone_output: 0.605886
  Test 3 PASSED.
  ```

- **Observation 4 (Dynamic class weights and data augmentation stability)**:
  The training simulation completed with data augmentation and dynamic class weights:
  ```
  Calculated class weights: {0: 0.37333333333333335, 1: 3.7333333333333334, 2: 18.666666666666668}
  Unweighted losses: Class 0=1.1087, Class 1=1.1087, Class 2=1.0788
  Weighted losses: Class 0=0.4139, Class 1=4.1390, Class 2=20.1378
  Ratio of weights (Class 2 / Class 0): 50.0000
  Training one epoch with class weights...
  ...
  Test 4 PASSED.
  Test 2 PASSED.
  ```

---

## 2. Logic Chain

1. From **Observation 1**, `head_dense` has `use_bias=True` which contradicts the requested spec "no bias". This adds 256 unnecessary parameters and fails the structural correctness check.
2. From **Observation 2**, calling `extractor(input_tensor)` directly on the raw tensor skips the `preprocess_input` step. This results in the extractor receiving unnormalized RGB values `[0.0, 255.0]`, while the classifier receives preprocessed inputs. Therefore, the extracted feature vector represents incorrect activations.
3. From **Observation 3**, we confirmed that when training the model, gradients are successfully computed for all variables in the custom head and propagate backwards, updating the weights of both `head_dense` and `skin_tone_output`.
4. From **Observation 4**, we verified that the data augmentation pipeline is stable under load (100 batches generated) and that dynamic class weights balance cross-entropy loss by weighting minority samples inversely proportional to their representation ratio.

---

## 3. Caveats

- We did not stress-test MediaPipe or DeepFace under high load, as they are external precompiled C++ binaries/models and not part of the primary CNN Backbone/Classifier architecture under review.
- We did not write code modifications to `backend/ml/cnn/efficientnet_backbone.py` or `backend/ml/cnn/skin_tone_classifier.py` since our role is review-only.

---

## 4. Conclusion

- The newly updated model compiles, trains, and correctly applies data augmentation under load.
- Gradient propagation and custom head training work correctly.
- However, two bugs are present:
  1. `head_dense` utilizes bias (`use_bias=True`) instead of `use_bias=False`.
  2. `SkinToneClassifier._predict_cnn` bypasses the `preprocess_input` normalization for feature extraction.
- **Actionable next steps**:
  - Update `use_bias=False` in `backend/ml/cnn/efficientnet_backbone.py` at line 49.
  - Modify `SkinToneClassifier._predict_cnn` to pass the preprocessed input into `extractor()`.

---

## 5. Verification Method

To verify these issues independently:
1. Run the stress-test script:
   ```cmd
   backend\venv_fix\Scripts\python.exe .agents\challenger_ms1_2\stress_test_cnn.py
   ```
2. Verify that Test 1 fails with the bias mismatch.
3. Check the output logs for the printed variables.
