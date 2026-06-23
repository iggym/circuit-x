"""
CircuitX: Sparse Autoencoder Feature Decomposer
Uses SAELens to map polysemantic neuron activations into interpretability paths.
"""
import torch
from transformer_lens import HookedTransformer
from sae_lens import SAE

class FeatureDecomposer:
    def __init__(self, sae_release: str = "gpt2-small-res-jb", sae_id: str = "blocks.6.hook_resid_post"):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = HookedTransformer.from_pretrained("gpt2-small", device=self.device)
        self.sae, _, _ = SAE.from_pretrained(release=sae_release, sae_id=sae_id, device=self.device)

    def extract_latent_features(self, prompt: str, sparsity_threshold: float = 1.2):
        tokens = self.model.to_tokens(prompt)
        _, cache = self.model.run_with_cache(tokens, names_filter=[self.sae.cfg.hook_name])
        
        hidden_states = cache[self.sae.cfg.hook_name]
        feature_activations = self.sae.encode(hidden_states)
        
        # Isolate target metrics at the final token position
        final_token_profile = feature_activations[0, -1, :]
        active_latents = torch.where(final_token_profile > sparsity_threshold)[0].tolist()
        
        nodes = [{"id": "Residual_Stream_L6", "type": "Input", "layer": 0, "val": 1.0, "label": "Residual L6 Stream"}]
        links = []
        
        for index in active_latents:
            act_val = float(final_token_profile[index])
            feature_id = f"SAE_{index}"
            
            nodes.append({
                "id": feature_id,
                "type": "SAE Feature",
                "layer": 1,
                "val": act_val,
                "label": f"Feature #{index}"
            })
            links.append({
                "source": "Residual_Stream_L6",
                "target": feature_id,
                "weight": min(act_val / 5.0, 1.0)
            })
            
        return {"nodes": nodes, "links": links}
