#!/usr/bin/env python3
"""
CircuitX: Mechanistic Interpretability Pipeline Orchestrator
Extracts model activations and serializes circuit subgraphs for web parsing.
"""

import os
import sys
import json
import argparse
import numpy as np
import torch
from transformer_lens import HookedTransformer

def parse_args():
    parser = argparse.ArgumentParser(description="CircuitX Mechanistic Extraction Pipeline")
    parser.add_argument("--model", type=str, default="gpt2-small", help="Target architecture name")
    parser.add_argument("--prompt", type=str, required=True, help="Input query to trace through network layers")
    parser.add_argument("--threshold", type=float, default=0.35, help="Edge filtering weight boundary")
    parser.add_argument("--out", type=str, default="web/circuit_data.json", help="Output filepath destination")
    return parser.parse_args()

def execute_extraction(model_name: str, prompt: str, threshold: float, output_path: str):
    print(f"⚡ Loading model framework: {model_name}...")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = HookedTransformer.from_pretrained(model_name, device=device)
    
    print(f"🔭 Registering internal hooks and tracking structural activations...")
    logits, cache = model.run_with_cache(prompt)
    
    tokens = model.to_str_tokens(prompt)
    nodes = []
    links = []
    
    # Map input embedding layer arrays
    for i, tok in enumerate(tokens):
        nodes.append({
            "id": f"Token_{i}", 
            "type": "Input Token", 
            "layer": 0, 
            "val": 1.0, 
            "label": f"[{i}] {tok}"
        })

    # Trace active attention paths across deep layers
    for layer in range(min(model.cfg.n_layers, 4)):  # Truncate layers to keep graph highly legible
        attn_pattern = cache["pattern", layer, "attn"][0].cpu().numpy()
        for head in range(model.cfg.n_heads):
            head_id = f"L{layer}_H{head}"
            mean_act = float(np.mean(attn_pattern[head]))
            
            nodes.append({
                "id": head_id,
                "type": "Attention Head",
                "layer": layer + 1,
                "val": mean_act,
                "label": f"Layer {layer} Head {head}"
            })
            
            # Draw vectors based on computational activation strengths
            for q_idx in range(attn_pattern.shape[1]):
                for k_idx in range(attn_pattern.shape[2]):
                    weight = float(attn_pattern[head, q_idx, k_idx])
                    if weight >= threshold:
                        links.append({
                            "source": f"Token_{k_idx}",
                            "target": head_id,
                            "weight": weight
                        })
                        
    # Anchor target node output projections
    nodes.append({
        "id": "Output_Logit",
        "type": "Output Logit",
        "layer": 5,
        "val": 0.90,
        "label": "Next Token Matrix"
    })
    
    # Tie final operational matrix to outputs
    for head in range(model.cfg.n_heads):
        links.append({
            "source": f"L{min(model.cfg.n_layers, 4)-1}_H{head}",
            "target": "Output_Logit",
            "weight": 0.40
        })

    # Output serialized payloads cleanly
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump({"nodes": nodes, "links": links}, f, indent=4)
        
    print(f"💾 Graph artifacts safely saved down to -> {output_path}")

if __name__ == "__main__":
    args = parse_args()
    execute_extraction(args.model, args.prompt, args.threshold, args.out)
