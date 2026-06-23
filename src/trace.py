"""
CircuitX: Induction Head & Computation Pathway Tracer
Uses TransformerLens to map causal weight activations across model sequences.
"""
import torch
import numpy as np
from transformer_lens import HookedTransformer

class CircuitTracer:
    def __init__(self, model_name: str = "gpt2-small"):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = HookedTransformer.from_pretrained(model_name, device=self.device)

    def discover_induction_circuit(self, prompt: str, threshold: float = 0.3):
        logits, cache = self.model.run_with_cache(prompt)
        tokens = self.model.to_str_tokens(prompt)
        
        nodes = []
        links = []
        
        # 1. Map input token nodes
        for i, tok in enumerate(tokens):
            nodes.append({
                "id": f"Token_{i}",
                "type": "Input Token",
                "layer": 0,
                "val": 1.0,
                "label": f"[{i}] {tok}"
            })

        # 2. Extract attention patterns layer-by-layer
        for layer in range(self.model.cfg.n_layers):
            attn_pattern = cache["pattern", layer, "attn"][0].cpu().numpy()
            
            for head in range(self.model.cfg.n_heads):
                head_id = f"L{layer}_H{head}"
                head_matrix = attn_pattern[head]
                mean_activation = float(np.mean(head_matrix))
                
                nodes.append({
                    "id": head_id,
                    "type": "Attention Head",
                    "layer": layer + 1,
                    "val": mean_activation,
                    "label": f"L{layer} H{head}"
                })
                
                # Causal mapping based on attention magnitude weights
                for q in range(head_matrix.shape[0]):
                    for k in range(head_matrix.shape[1]):
                        w = float(head_matrix[q, k])
                        if w >= threshold:
                            links.append({
                                "source": f"Token_{k}",
                                "target": head_id,
                                "weight": w
                            })
                            
        return {"nodes": nodes, "links": links}
