"""
CircuitX: Tuned Lens Predictive Prober & Causal Intervener
Intercepts and maps logit generation distributions layer by layer.
"""
import torch
from transformer_lens import HookedTransformer

class CausalSteeringEngine:
    def __init__(self, model_name: str = "gpt2-small"):
        self.model = HookedTransformer.from_pretrained(model_name)

    def zero_ablation_hook(self, activation_tensor, hook):
        # Target Layer 5, Attention Head 4 (simulated deception path driver)
        activation_tensor[:, :, 4, :] = 0.0
        return activation_tensor

    def run_steered_probing(self, prompt: str):
        # Baseline run
        clean_logits = self.model(prompt)
        clean_prediction = self.model.to_string(clean_logits[0, -1].argmax())
        
        # Causal intervention run
        steered_logits = self.model.run_with_hooks(
            prompt,
            fwd_hooks=[("blocks.5.attn.hook_z", self.zero_ablation_hook)]
        )
        steered_prediction = self.model.to_string(steered_logits[0, -1].argmax())
        
        return {
            "baseline_prediction": clean_prediction,
            "steered_prediction": steered_prediction
        }
