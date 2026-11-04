#!/usr/bin/env python3
"""Generate publication-grade Five-Layer Architecture Diagram for SimuGuard-X.
Target: IEEE Transactions on Computer-Aided Design (TCAD) double-column figure.
Output: paper/figures/fig_architecture.pdf
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path

# Configure matplotlib for IEEE publication quality
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["DejaVu Sans", "Helvetica", "Arial"],
    "font.size": 8,
    "axes.titlesize": 9,
    "axes.labelsize": 8,
    "figure.titlesize": 10,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})

fig = plt.figure(figsize=(7.16, 1.95), dpi=300) # Compact IEEE full textwidth
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 100)
ax.set_ylim(0, 31)
ax.axis("off")

# Color palette (professional muted academic scheme)
c_layer_bg = ["#F0F4F8", "#FDF6EC", "#F4F9F4", "#F5F3F9", "#FEF2F2"]
c_layer_border = ["#2B6CB0", "#D97706", "#2F855A", "#6B46C1", "#C53030"]
c_box_bg = "#FFFFFF"
c_arrow = "#4A5568"
c_text_title = "#1A202C"
c_text_body = "#2D3748"

# Layer configurations: [x, y, w, h]
layers = [
    {
        "num": "Layer 1",
        "title": "Interface Grounding (ASIE)",
        "x": 1.2, "y": 1.5, "w": 18.2, "h": 27.5,
        "bg": c_layer_bg[0], "border": c_layer_border[0],
        "items": [
            ("Model Introspection", "Simulink.findVars, SLDD"),
            ("AUTOSAR Bus Parsing", "Bus.cellToObject hierarchy"),
            ("Tarjan SCC Pruning", "Feedback cut at 1/s, 1/z"),
            ("Causal Metadata", "Signal bounds, Ts, units")
        ]
    },
    {
        "num": "Layer 2",
        "title": "Dual-Track Synthesis",
        "x": 21.0, "y": 1.5, "w": 18.2, "h": 27.5,
        "bg": c_layer_bg[1], "border": c_layer_border[1],
        "items": [
            ("Frontier LLM Reasoning", "Grounded by ASIE context"),
            ("Track A: Formal STL", "NASA FRET Semantics"),
            ("Track B: Scenario DSL", "EBNF grammar, d <= 12"),
            ("Low-Rank Parameterization", "Piecewise-linear controls")
        ]
    },
    {
        "num": "Layer 3",
        "title": "Witness Validation",
        "x": 40.8, "y": 1.5, "w": 18.2, "h": 27.5,
        "bg": c_layer_bg[2], "border": c_layer_border[2],
        "items": [
            ("Dual-Witness Synthesis", "Positive w+ & Negative w-"),
            ("RTAMT STL Monitor", "Independent formal monitor"),
            ("Semantic Non-Vacuity", "rho(w+) > 0, rho(w-) < 0"),
            ("Iterative Repair Loop", "Prompt feedback (K <= 3)")
        ]
    },
    {
        "num": "Layer 4",
        "title": "Lexicographic CMA-ES",
        "x": 60.6, "y": 1.5, "w": 18.2, "h": 27.5,
        "bg": c_layer_bg[3], "border": c_layer_border[3],
        "items": [
            ("Three-Regime Order", "Regime 2 > Regime 1 > 0"),
            ("Antecedent Guidance", "Log-Sum-Exp smooth pull"),
            ("Covariance Damping", "p_sigma <- alpha_damp * p_sigma"),
            ("Simulink Execution", "Active closed-loop engine")
        ]
    },
    {
        "num": "Layer 5",
        "title": "Dual-Fidelity Gate 2",
        "x": 80.4, "y": 1.5, "w": 18.2, "h": 27.5,
        "bg": c_layer_bg[4], "border": c_layer_border[4],
        "items": [
            ("Candidate Verification", "Nominal falsifier (rho < 0)"),
            ("Dual-Solver Cross-Check", "ode5 baseline vs ode15s"),
            ("SCR Stiffness Metric", "SCR >= 10^3 transient flag"),
            ("Digital Certificate", "Auditable witness bundle")
        ]
    }
]

for L in layers:
    # Outer layer card
    card = patches.FancyBboxPatch(
        (L["x"], L["y"]), L["w"], L["h"],
        boxstyle="round,pad=0.4,rounding_size=1.0",
        linewidth=1.0, edgecolor=L["border"], facecolor=L["bg"]
    )
    ax.add_patch(card)
    
    # Layer header pill
    hdr_box = patches.FancyBboxPatch(
        (L["x"] + 0.8, L["y"] + L["h"] - 4.2), L["w"] - 1.6, 3.4,
        boxstyle="round,pad=0.2,rounding_size=0.6",
        linewidth=0.6, edgecolor=L["border"], facecolor=L["border"]
    )
    ax.add_patch(hdr_box)
    
    # Header text
    ax.text(
        L["x"] + L["w"] / 2.0, L["y"] + L["h"] - 1.8,
        L["num"].upper(),
        color="#FFFFFF", fontsize=6.2, fontweight="bold",
        ha="center", va="center"
    )
    ax.text(
        L["x"] + L["w"] / 2.0, L["y"] + L["h"] - 3.2,
        L["title"],
        color="#FFFFFF", fontsize=6.6, fontweight="bold",
        ha="center", va="center"
    )
    
    # Inner feature items
    item_y_start = L["y"] + L["h"] - 5.8
    item_h = 4.6
    for i, (title, desc) in enumerate(L["items"]):
        iy = item_y_start - i * (item_h + 0.8)
        ibox = patches.FancyBboxPatch(
            (L["x"] + 0.8, iy - item_h), L["w"] - 1.6, item_h,
            boxstyle="round,pad=0.2,rounding_size=0.5",
            linewidth=0.5, edgecolor="#CBD5E0", facecolor=c_box_bg
        )
        ax.add_patch(ibox)
        
        ax.text(
            L["x"] + 1.5, iy - 1.6,
            title,
            color=c_text_title, fontsize=6.0, fontweight="bold",
            ha="left", va="center"
        )
        ax.text(
            L["x"] + 1.5, iy - 3.4,
            desc,
            color="#4A5568", fontsize=5.2,
            ha="left", va="center"
        )

# Inter-layer connecting arrows
arrow_y = 15.0
for i in range(len(layers) - 1):
    x_start = layers[i]["x"] + layers[i]["w"] + 0.1
    x_end = layers[i + 1]["x"] - 0.1
    ax.annotate(
        "", xy=(x_end, arrow_y), xytext=(x_start, arrow_y),
        arrowprops=dict(
            arrowstyle="-|>", color=c_arrow,
            lw=1.2, mutation_scale=8
        )
    )

# Feedback loop: RTAMT to LLM repair loop (Layer 3 back to Layer 2)
ax.annotate(
    "Repair (K <= 3)",
    xy=(layers[1]["x"] + layers[1]["w"] / 2.0, layers[1]["y"]),
    xytext=(layers[2]["x"] + layers[2]["w"] / 2.0, layers[2]["y"] - 1.0),
    arrowprops=dict(
        arrowstyle="-|>", color="#D97706", lw=0.9, linestyle="--",
        connectionstyle="arc3,rad=-0.25", mutation_scale=7
    ),
    ha="center", va="top", fontsize=5.2, color="#D97706", fontweight="bold"
)

# Output artifact callout at right of Layer 5
ax.text(
    90.0, 0.4,
    "Certified Witness (*.mat)",
    fontsize=5.2, color="#C53030", fontweight="bold", ha="center"
)

output_path = Path(__file__).resolve().parent.parent / "paper" / "figures" / "fig_architecture.pdf"
output_path.parent.mkdir(parents=True, exist_ok=True)
plt.savefig(output_path, format="pdf", bbox_inches="tight", pad_inches=0.03)
png_path = output_path.with_suffix(".png")
plt.savefig(png_path, format="png", dpi=300, bbox_inches="tight", pad_inches=0.03)
plt.close()

print(f"Successfully generated architecture figure:")
print(f"  PDF: {output_path}")
print(f"  PNG: {png_path}")
