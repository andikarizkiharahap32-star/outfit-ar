import sys
import os
from loguru import logger

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from efficientnet_backbone import build_skin_tone_classifier

def main():
    logger.info("Initializing skin tone classifier to verify layer order...")
    try:
        model = build_skin_tone_classifier(num_classes=5)
        logger.info("Model built successfully.")
        
        # We expect the layers after the backbone/input to follow a specific order
        # Let's inspect the layers in the model
        print("\n--- Model Layers ---")
        for i, layer in enumerate(model.layers):
            print(f"{i}: {layer.name} ({layer.__class__.__name__})")
            
        print("\nChecking expected head layers...")
        head_layers = [layer for layer in model.layers if layer.name.startswith("head_") or layer.name == "skin_tone_output"]
        
        expected_order = [
            ("head_dense", "Dense"),
            ("head_bn", "BatchNormalization"),
            ("head_activation", "Activation"),
            ("head_dropout", "Dropout"),
            ("skin_tone_output", "Dense")
        ]
        
        match = True
        for (exp_name, exp_type), layer in zip(expected_order, head_layers):
            if layer.name != exp_name or layer.__class__.__name__ != exp_type:
                logger.error(f"Mismatch: Expected {exp_name} ({exp_type}), got {layer.name} ({layer.__class__.__name__})")
                match = False
            else:
                logger.info(f"Verified: {layer.name} ({layer.__class__.__name__}) is correct.")
                
            # Extra checks
            if exp_name == "head_dense":
                if layer.activation is not None and layer.activation.__name__ != "linear":
                    logger.error(f"head_dense activation should be None (linear), got {layer.activation}")
                    match = False
                if layer.use_bias:
                    logger.error("head_dense use_bias should be False")
                    match = False
                if layer.kernel_regularizer is None:
                    logger.error("head_dense kernel_regularizer should not be None")
                    match = False
                else:
                    logger.info(f"head_dense L2 regularizer: {layer.kernel_regularizer.get_config()}")
                    
        if match and len(head_layers) == len(expected_order):
            logger.info("Verification PASSED: All head layers are correct and in the correct order.")
            sys.exit(0)
        else:
            logger.error("Verification FAILED: Layer mismatch found.")
            sys.exit(1)
            
    except Exception as e:
        logger.exception("Error during verification:")
        sys.exit(2)

if __name__ == "__main__":
    main()
