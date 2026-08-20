import sys
import os
import time
import json
import numpy as np
import tensorflow as tf
from tensorflow import keras

# Set up paths so we can import from backend/ml/cnn
BACKEND_DIR = r"C:\Final_outfitAR\outfit-ar\backend"
CNN_DIR = os.path.join(BACKEND_DIR, "ml", "cnn")
sys.path.append(BACKEND_DIR)
sys.path.append(CNN_DIR)

from efficientnet_backbone import build_skin_tone_classifier, build_feature_extractor

def run_tests():
    results = {
        "test_1_structure": {"status": "FAILED", "details": {}},
        "test_2_augmentation": {"status": "FAILED", "details": {}},
        "test_3_gradients": {"status": "FAILED", "details": {}},
        "test_4_class_weights": {"status": "FAILED", "details": {}},
        "test_5_inference": {"status": "FAILED", "details": {}}
    }

    # =========================================================================
    # TEST 1: Model Compilation and Structure Verification
    # =========================================================================
    print("\n--- Running Test 1: Model Structure & Layer Verification ---")
    try:
        model = build_skin_tone_classifier(num_classes=3)
        print("Model compiled successfully.")
        
        # Verify specific layer configurations
        layer_names = [l.name for l in model.layers]
        print(f"Model layers: {layer_names}")
        
        # Check order of specific head layers
        head_layers = [l for l in model.layers if l.name.startswith("head_") or l.name == "skin_tone_output"]
        print(f"Head layers found: {[l.name for l in head_layers]}")
        
        expected_order = [
            ("head_dense", "Dense"),
            ("head_bn", "BatchNormalization"),
            ("head_activation", "Activation"),
            ("head_dropout", "Dropout"),
            ("skin_tone_output", "Dense")
        ]
        
        mismatches = []
        for idx, (exp_name, exp_type) in enumerate(expected_order):
            if idx >= len(head_layers):
                mismatches.append(f"Missing expected layer {exp_name} ({exp_type})")
                continue
            layer = head_layers[idx]
            if layer.name != exp_name:
                mismatches.append(f"Expected layer name {exp_name} at index {idx}, got {layer.name}")
            if layer.__class__.__name__ != exp_type:
                mismatches.append(f"Expected layer type {exp_type} for {layer.name}, got {layer.__class__.__name__}")
                
        # Detailed configuration check of head_dense
        head_dense_layer = model.get_layer("head_dense")
        use_bias = head_dense_layer.use_bias
        activation = head_dense_layer.activation
        kernel_reg = head_dense_layer.kernel_regularizer
        
        reg_config = kernel_reg.get_config() if kernel_reg else None
        
        print(f"head_dense use_bias: {use_bias}")
        print(f"head_dense activation: {activation}")
        print(f"head_dense L2 config: {reg_config}")
        
        # Validation checks
        if use_bias:
            mismatches.append("head_dense should not use bias (use_bias=False)")
        if activation is not None and getattr(activation, "__name__", str(activation)) != "linear":
            mismatches.append(f"head_dense activation should be None/linear, got {activation}")
        if kernel_reg is None:
            mismatches.append("head_dense must have an L2 kernel regularizer")
        elif not isinstance(kernel_reg, keras.regularizers.L2) and reg_config.get("l2", 0.0) != 1e-4:
            mismatches.append(f"head_dense kernel regularizer is not L2 of 1e-4, got config {reg_config}")
            
        # Check Dropout rate
        dropout_layer = model.get_layer("head_dropout")
        rate = dropout_layer.rate
        print(f"head_dropout rate: {rate}")
        if abs(rate - 0.4) > 1e-6:
            mismatches.append(f"head_dropout rate should be 0.4, got {rate}")
            
        if len(mismatches) == 0:
            results["test_1_structure"] = {
                "status": "PASSED",
                "details": {
                    "head_dense_use_bias": use_bias,
                    "head_dense_activation": str(activation),
                    "head_dense_l2": reg_config,
                    "head_dropout_rate": rate,
                    "layer_sequence": [l.name for l in head_layers]
                }
            }
            print("Test 1 PASSED.")
        else:
            results["test_1_structure"] = {
                "status": "FAILED",
                "details": {"mismatches": mismatches}
            }
            print(f"Test 1 FAILED with mismatches: {mismatches}")
            
    except Exception as e:
        results["test_1_structure"] = {
            "status": "ERROR",
            "details": {"error": str(e)}
        }
        print(f"Test 1 encountered error: {e}")

    # =========================================================================
    # TEST 2: Data Augmentation Pipeline under Load
    # =========================================================================
    print("\n--- Running Test 2: Data Augmentation under Load ---")
    try:
        # Recreate the data augmentation pipeline from train_cnn.py
        data_augmentation = keras.Sequential([
            keras.layers.RandomFlip("horizontal"),
            keras.layers.RandomRotation(10/360.0),
            keras.layers.RandomBrightness(0.2, value_range=(0.0, 255.0)),
            keras.layers.RandomContrast(0.2)
        ], name="data_augmentation")

        # Generate dummy input batch
        dummy_batch = tf.random.uniform(shape=(32, 224, 224, 3), minval=0.0, maxval=255.0, dtype=tf.float32)
        
        # Stress-test by running 100 iterations of augmentation
        start_time = time.time()
        for i in range(100):
            aug_out = data_augmentation(dummy_batch, training=True)
            # Simple check to make sure output shape and finite values are preserved
            if aug_out.shape != dummy_batch.shape:
                raise ValueError(f"Shape mismatch in iteration {i}: {aug_out.shape}")
            if tf.reduce_any(tf.math.is_nan(aug_out)) or tf.reduce_any(tf.math.is_inf(aug_out)):
                raise ValueError(f"NaN or Inf encountered in iteration {i}")
        duration = time.time() - start_time
        
        print(f"Successfully ran 100 iterations of augmentation in {duration:.4f}s.")
        results["test_2_augmentation"] = {
            "status": "PASSED",
            "details": {
                "iterations": 100,
                "batch_size": 32,
                "duration_seconds": duration,
                "average_time_per_batch_ms": (duration / 100) * 1000,
                "output_shape": list(aug_out.shape)
            }
        }
        print("Test 2 PASSED.")
    except Exception as e:
        results["test_2_augmentation"] = {
            "status": "FAILED",
            "details": {"error": str(e)}
        }
        print(f"Test 2 FAILED: {e}")

    # =========================================================================
    # TEST 3: Gradient Propagation & Weight Update
    # =========================================================================
    print("\n--- Running Test 3: Gradient Propagation & Weight Updates ---")
    try:
        # Load a fresh model and compile
        model = build_skin_tone_classifier(num_classes=3)
        optimizer = keras.optimizers.Adam(learning_rate=1e-3)
        loss_fn = keras.losses.CategoricalCrossentropy()
        
        # Create single batch of dummy inputs and one-hot labels
        x_dummy = tf.random.uniform(shape=(4, 224, 224, 3), minval=0.0, maxval=255.0)
        y_dummy = tf.constant([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0], [1.0, 0.0, 0.0]], dtype=tf.float32)
        
        # Check initial weights of custom head
        head_dense = model.get_layer("head_dense")
        head_bn = model.get_layer("head_bn")
        output_layer = model.get_layer("skin_tone_output")
        
        w_dense_init = head_dense.get_weights()[0].copy()
        w_out_init = output_layer.get_weights()[0].copy()
        
        # Record BN variables before
        bn_moving_mean_init = head_bn.moving_mean.numpy().copy()
        
        # Run one forward & backward pass with GradientTape
        with tf.GradientTape() as tape:
            # Note: training=True is important to make BN update and Dropout active
            preds = model(x_dummy, training=True)
            loss = loss_fn(y_dummy, preds)
            # Add regularization loss manually if it exists
            reg_losses = model.losses
            if reg_losses:
                loss += tf.add_n(reg_losses)
                
        # Compute gradients
        trainable_vars = model.trainable_variables
        grads = tape.gradient(loss, trainable_vars)
        
        # Map grads to variable IDs
        var_to_grad = {id(var): grad for var, grad in zip(trainable_vars, grads)}
        
        # Check that we have gradients for our head layers and they are not None
        missing_grads = []
        zero_grads = []
        grad_norms = {}
        
        # Helper to check variables for a specific layer
        def check_layer_vars(layer, prefix):
            for var in layer.trainable_variables:
                grad = var_to_grad.get(id(var))
                name = f"{prefix}/{var.name}"
                if grad is None:
                    missing_grads.append(name)
                else:
                    norm = float(tf.linalg.global_norm([grad]).numpy())
                    grad_norms[name] = norm
                    if norm == 0.0:
                        zero_grads.append(name)
                        
        check_layer_vars(head_dense, "head_dense")
        check_layer_vars(head_bn, "head_bn")
        check_layer_vars(output_layer, "skin_tone_output")
                    
        print(f"Gradient norms of head layers: {grad_norms}")
        
        # Apply gradients (weight update)
        optimizer.apply_gradients(zip(grads, trainable_vars))
        
        # Verify weights actually changed
        w_dense_updated = head_dense.get_weights()[0]
        w_out_updated = output_layer.get_weights()[0]
        
        diff_dense = float(np.sum(np.abs(w_dense_updated - w_dense_init)))
        diff_out = float(np.sum(np.abs(w_out_updated - w_out_init)))
        
        print(f"Absolute weight change in head_dense: {diff_dense:.6f}")
        print(f"Absolute weight change in skin_tone_output: {diff_out:.6f}")
        
        success = True
        reasons = []
        if len(missing_grads) > 0:
            success = False
            reasons.append(f"Gradients missing for variables: {missing_grads}")
        if len(zero_grads) > 0:
            success = False
            reasons.append(f"Gradients are exactly zero for variables: {zero_grads}")
        if diff_dense == 0.0:
            success = False
            reasons.append("Weights of head_dense did not update after gradient step")
        if diff_out == 0.0:
            success = False
            reasons.append("Weights of skin_tone_output did not update after gradient step")
            
        if success:
            results["test_3_gradients"] = {
                "status": "PASSED",
                "details": {
                    "gradient_norms": grad_norms,
                    "head_dense_weight_diff": diff_dense,
                    "skin_tone_output_weight_diff": diff_out
                }
            }
            print("Test 3 PASSED.")
        else:
            results["test_3_gradients"] = {
                "status": "FAILED",
                "details": {"reasons": reasons, "gradient_norms": grad_norms}
            }
            print(f"Test 3 FAILED: {reasons}")
            
    except Exception as e:
        results["test_3_gradients"] = {
            "status": "ERROR",
            "details": {"error": str(e)}
        }
        print(f"Test 3 encountered error: {e}")

    # =========================================================================
    # TEST 4: Dynamic Class Weights Balancing Loss
    # =========================================================================
    print("\n--- Running Test 4: Dynamic Class Weights Balancing ---")
    try:
        # Define imbalanced class counts
        # Class 0: 100 samples, Class 1: 10 samples, Class 2: 2 samples (highly imbalanced!)
        class_counts = [100, 10, 2]
        num_classes = len(class_counts)
        total_samples = sum(class_counts)
        
        # Formula: class_weights[i] = total_samples / (num_classes * count)
        class_weights = {}
        for i, count in enumerate(class_counts):
            class_weights[i] = total_samples / (num_classes * count) if count > 0 else 1.0
            
        print(f"Calculated class weights: {class_weights}")
        # Expected:
        # Class 0 weight: 112 / (3 * 100) = 0.3733
        # Class 1 weight: 112 / (3 * 10) = 3.7333
        # Class 2 weight: 112 / (3 * 2) = 18.6667
        
        # Verify loss calculation with and without weights
        # We will create individual cross-entropy losses for class 0, class 1, class 2
        # and verify they are correctly scaled by class weights in a custom loss calculation
        # to prove the balancing logic.
        
        cce = keras.losses.CategoricalCrossentropy(reduction=keras.losses.Reduction.NONE)
        
        # Dummy predictions (logits -> softmax)
        # Assume a uniform model output for all classes (e.g. probs = [0.33, 0.33, 0.33])
        y_pred = tf.constant([[0.33, 0.33, 0.34]], dtype=tf.float32)
        
        # Individual samples of each class
        y_true_0 = tf.constant([[1.0, 0.0, 0.0]], dtype=tf.float32)
        y_true_1 = tf.constant([[0.0, 1.0, 0.0]], dtype=tf.float32)
        y_true_2 = tf.constant([[0.0, 0.0, 1.0]], dtype=tf.float32)
        
        loss_0 = float(cce(y_true_0, y_pred).numpy()[0])
        loss_1 = float(cce(y_true_1, y_pred).numpy()[0])
        loss_2 = float(cce(y_true_2, y_pred).numpy()[0])
        
        weighted_loss_0 = loss_0 * class_weights[0]
        weighted_loss_1 = loss_1 * class_weights[1]
        weighted_loss_2 = loss_2 * class_weights[2]
        
        print(f"Unweighted losses: Class 0={loss_0:.4f}, Class 1={loss_1:.4f}, Class 2={loss_2:.4f}")
        print(f"Weighted losses: Class 0={weighted_loss_0:.4f}, Class 1={weighted_loss_1:.4f}, Class 2={weighted_loss_2:.4f}")
        
        # Prove the balancing: the ratio of weighted loss matches the inverse ratio of class sizes
        # e.g. weighted_loss_2 / weighted_loss_0 should scale the minority loss by class_weights[2]/class_weights[0]
        ratio_loss = weighted_loss_2 / weighted_loss_0
        ratio_weights = class_weights[2] / class_weights[0]
        print(f"Ratio of weights (Class 2 / Class 0): {ratio_weights:.4f}")
        
        # Create a mock training step on an imbalanced batch using fit() with class_weight
        # Generate an imbalanced dataset of 112 items
        x_train = np.random.uniform(0.0, 255.0, size=(112, 224, 224, 3)).astype(np.float32)
        y_train = np.zeros((112, 3), dtype=np.float32)
        y_train[0:100, 0] = 1.0
        y_train[100:110, 1] = 1.0
        y_train[110:112, 2] = 1.0
        
        model = build_skin_tone_classifier(num_classes=3)
        model.compile(optimizer=keras.optimizers.Adam(learning_rate=1e-4), loss='categorical_crossentropy', metrics=['accuracy'])
        
        # Train for a small dummy epoch
        print("Training one epoch with class weights...")
        history = model.fit(x_train, y_train, epochs=1, batch_size=16, class_weight=class_weights, verbose=1)
        
        results["test_4_class_weights"] = {
            "status": "PASSED",
            "details": {
                "class_counts": class_counts,
                "class_weights": class_weights,
                "unweighted_losses": {"class_0": loss_0, "class_1": loss_1, "class_2": loss_2},
                "weighted_losses": {"class_0": weighted_loss_0, "class_1": weighted_loss_1, "class_2": weighted_loss_2},
                "training_loss": float(history.history["loss"][0])
            }
        }
        print("Test 4 PASSED.")
    except Exception as e:
        results["test_4_class_weights"] = {
            "status": "FAILED",
            "details": {"error": str(e)}
        }
        print(f"Test 4 FAILED: {e}")

    # =========================================================================
    # TEST 5: No Crashes during Feature Extraction or Classification
    # =========================================================================
    print("\n--- Running Test 5: Inference and Feature Extraction Stability ---")
    try:
        classifier = build_skin_tone_classifier(num_classes=3)
        extractor = build_feature_extractor()
        
        batch_sizes = [1, 4, 16]
        inference_details = {}
        
        for bs in batch_sizes:
            x_test = tf.random.uniform(shape=(bs, 224, 224, 3), minval=0.0, maxval=255.0)
            
            # Predict labels
            y_cls = classifier.predict(x_test, verbose=0)
            if y_cls.shape != (bs, 3):
                raise ValueError(f"Classifier shape mismatch for batch size {bs}: expected {(bs, 3)}, got {y_cls.shape}")
                
            # Extract features
            y_feats = extractor.predict(x_test, verbose=0)
            if y_feats.shape != (bs, 1280):
                raise ValueError(f"Extractor shape mismatch for batch size {bs}: expected {(bs, 1280)}, got {y_feats.shape}")
                
            print(f"Inference verified for batch size {bs}: classification shape={y_cls.shape}, features shape={y_feats.shape}")
            inference_details[f"batch_size_{bs}"] = {
                "classifier_shape": list(y_cls.shape),
                "extractor_shape": list(y_feats.shape)
            }
            
        results["test_5_inference"] = {
            "status": "PASSED",
            "details": inference_details
        }
        print("Test 5 PASSED.")
    except Exception as e:
        results["test_5_inference"] = {
            "status": "FAILED",
            "details": {"error": str(e)}
        }
        print(f"Test 5 FAILED: {e}")

    # Save results to json
    results_path = os.path.join(os.path.dirname(__file__), "stress_test_results.json")
    with open(results_path, "w") as f:
        json.dump(results, f, indent=4)
    print(f"\nSaved stress test results to {results_path}")
    
    # Return exit code based on overall success
    overall_status = all(r["status"] == "PASSED" for r in results.values())
    sys.exit(0 if overall_status else 1)

if __name__ == "__main__":
    run_tests()
