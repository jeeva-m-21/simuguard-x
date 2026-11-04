#!/usr/bin/env python3
"""
generate_extended_paper_figures.py
Generates high-quality IEEE journal tier comparison figures:
- fig5_rq1_specification_fidelity.pdf / .png
- fig6_rq4_coverage_comparison.pdf / .png
- fig7_rq7_mutation_kill_scores.pdf / .png
Guarantees zero overlap, publication typography, and high contrast.
"""

import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

# Set publication style
plt.rcParams.update({
    'font.family': 'serif',
    'font.serif': ['Times New Roman', 'DejaVu Serif', 'Times'],
    'font.size': 10,
    'axes.labelsize': 10,
    'axes.titlesize': 11,
    'xtick.labelsize': 9,
    'ytick.labelsize': 9,
    'legend.fontsize': 9,
    'figure.titlesize': 12,
    'figure.dpi': 300,
    'text.usetex': False,
    'mathtext.fontset': 'stix',
})

FIGURES_DIR = os.path.join(os.path.dirname(__file__), '..', 'paper', 'figures')
os.makedirs(FIGURES_DIR, exist_ok=True)

# -------------------------------------------------------------
# Figure 5: RQ1 Specification Mutation Detection Rate & Fidelity
# -------------------------------------------------------------
def generate_fig5():
    fig, ax = plt.subplots(figsize=(6.8, 3.2), constrained_layout=True)

    categories = ['Inversion\nDetection', 'Boundary Shift\nDetection', 'Polarity Error\nDetection', 'Overall F1\nScore (x100)']
    x = np.arange(len(categories))
    width = 0.24

    zero_shot = [41.6, 33.3, 58.3, 51.0]
    back_trans = [62.5, 54.1, 70.8, 67.0]
    simuguard = [95.8, 91.6, 97.9, 95.0]

    rects1 = ax.bar(x - width, zero_shot, width, label='Zero-Shot Prompting (GPT-4o)', color='#94a3b8', edgecolor='#334155', hatch='//', alpha=0.9)
    rects2 = ax.bar(x, back_trans, width, label='LLM Self-Back-Translation', color='#38bdf8', edgecolor='#0369a1', hatch='\\\\', alpha=0.9)
    rects3 = ax.bar(x + width, simuguard, width, label='SimuGuard-X (Witnesses $w^+, w^-$)', color='#059669', edgecolor='#064e3b', alpha=0.95)

    ax.set_ylabel('Verification Rate (%)')
    ax.set_title('RQ1: Formal Specification Mutation Detection and Semantic Fidelity', pad=8)
    ax.set_xticks(x)
    ax.set_xticklabels(categories)
    ax.set_ylim(0, 115)
    ax.grid(axis='y', linestyle='--', alpha=0.4)

    # Value labels on top of bars
    for rects in [rects1, rects2, rects3]:
        for rect in rects:
            height = rect.get_height()
            ax.annotate(f'{height:.1f}%',
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 2),  # 2 points vertical offset
                        textcoords="offset points",
                        ha='center', va='bottom', fontsize=7.5, rotation=0)

    ax.legend(loc='upper left', frameon=True, framealpha=0.92, facecolor='white', edgecolor='#cbd5e1')

    out_pdf = os.path.join(FIGURES_DIR, 'fig5_rq1_specification_fidelity.pdf')
    out_png = os.path.join(FIGURES_DIR, 'fig5_rq1_specification_fidelity.png')
    plt.savefig(out_pdf, bbox_inches='tight')
    plt.savefig(out_png, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Generated {out_pdf} and {out_png}")

# -------------------------------------------------------------
# Figure 6: RQ4 Cumulative Branch and Condition Coverage
# -------------------------------------------------------------
def generate_fig6():
    fig, ax = plt.subplots(figsize=(6.8, 3.2), constrained_layout=True)

    models = ['Automatic Trans.\n(AT)', 'Air-Fuel Control\n(AFC)', 'HEV Powertrain\n(HEV)', 'Overall\nAverage']
    x = np.arange(len(models))
    width = 0.20

    random_fuzz = [54.2, 61.8, 48.6, 54.9]
    sldv = [78.4, 81.2, 68.2, 75.9]
    simcotest = [72.1, 76.4, 64.8, 71.1]
    simuguard = [89.6, 92.3, 84.1, 88.7]

    r1 = ax.bar(x - 1.5*width, random_fuzz, width, label='Random Fuzzing', color='#cbd5e1', edgecolor='#475569', hatch='..', alpha=0.9)
    r2 = ax.bar(x - 0.5*width, sldv, width, label='Simulink Design Verifier (SLDV)', color='#fbbf24', edgecolor='#b45309', hatch='--', alpha=0.9)
    r3 = ax.bar(x + 0.5*width, simcotest, width, label='SimCoTest (Metaheuristic)', color='#60a5fa', edgecolor='#1d4ed8', hatch='//', alpha=0.9)
    r4 = ax.bar(x + 1.5*width, simuguard, width, label='SimuGuard-X (Auxiliary STL)', color='#10b981', edgecolor='#065f46', alpha=0.95)

    ax.set_ylabel('Cumulative Coverage (%)')
    ax.set_title('RQ7: Structural Condition and Stateflow Branch Coverage on Invariant Models', pad=8)
    ax.set_xticks(x)
    ax.set_xticklabels(models)
    ax.set_ylim(0, 115)
    ax.grid(axis='y', linestyle='--', alpha=0.4)

    for rects in [r1, r2, r3, r4]:
        for rect in rects:
            height = rect.get_height()
            ax.annotate(f'{height:.1f}%',
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 2),
                        textcoords="offset points",
                        ha='center', va='bottom', fontsize=7.0, rotation=0)

    ax.legend(loc='upper left', ncol=2, frameon=True, framealpha=0.92, facecolor='white', edgecolor='#cbd5e1')

    out_pdf = os.path.join(FIGURES_DIR, 'fig6_rq4_coverage_comparison.pdf')
    out_png = os.path.join(FIGURES_DIR, 'fig6_rq4_coverage_comparison.png')
    plt.savefig(out_pdf, bbox_inches='tight')
    plt.savefig(out_png, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Generated {out_pdf} and {out_png}")

# -------------------------------------------------------------
# Figure 7: RQ7 Simulink Model Mutation Kill Scores
# -------------------------------------------------------------
def generate_fig7():
    fig, ax = plt.subplots(figsize=(6.8, 3.4), constrained_layout=True)

    operators = ['ROR\n(Relational)', 'AOR\n(Arithmetic)', 'DSS\n(Delay State)', 'DMM\n(Deadlock Mode)', 'SLM\n(Saturation)', 'Overall\nMutation Score']
    x = np.arange(len(operators))
    width = 0.20

    random_fuzz = [32.5, 27.5, 20.0, 16.7, 22.5, 24.4]
    breach = [67.5, 62.5, 53.3, 46.7, 55.0, 57.8]
    simcotest = [75.0, 70.0, 63.3, 56.7, 65.0, 66.7]
    simuguard = [95.0, 92.5, 90.0, 86.7, 92.5, 91.7]

    r1 = ax.bar(x - 1.5*width, random_fuzz, width, label='Random Fuzzing', color='#e2e8f0', edgecolor='#64748b', hatch='..', alpha=0.85)
    r2 = ax.bar(x - 0.5*width, breach, width, label='Breach-CMA-ES', color='#fdba74', edgecolor='#c2410c', hatch='xx', alpha=0.9)
    r3 = ax.bar(x + 0.5*width, simcotest, width, label='SimCoTest', color='#93c5fd', edgecolor='#1d4ed8', hatch='//', alpha=0.9)
    r4 = ax.bar(x + 1.5*width, simuguard, width, label='SimuGuard-X Admitted Suite', color='#047857', edgecolor='#064e3b', alpha=0.95)

    ax.set_ylabel('Mutation Kill Score (%)')
    ax.set_title(r'RQ10: Test Suite Fault Sensitivity Across 180 Simulink Model Mutants ($\mathcal{M}_{\mathrm{Sim}}$)', pad=8)
    ax.set_xticks(x)
    ax.set_xticklabels(operators)
    ax.set_ylim(0, 118)
    ax.grid(axis='y', linestyle='--', alpha=0.4)

    for rects in [r1, r2, r3, r4]:
        for rect in rects:
            height = rect.get_height()
            ax.annotate(f'{height:.0f}%' if height.is_integer() else f'{height:.1f}%',
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 2),
                        textcoords="offset points",
                        ha='center', va='bottom', fontsize=6.8, rotation=0)

    ax.legend(loc='upper left', ncol=2, frameon=True, framealpha=0.92, facecolor='white', edgecolor='#cbd5e1')

    out_pdf = os.path.join(FIGURES_DIR, 'fig7_rq7_mutation_kill_scores.pdf')
    out_png = os.path.join(FIGURES_DIR, 'fig7_rq7_mutation_kill_scores.png')
    plt.savefig(out_pdf, bbox_inches='tight')
    plt.savefig(out_png, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Generated {out_pdf} and {out_png}")

if __name__ == '__main__':
    generate_fig5()
    generate_fig6()
    generate_fig7()
    print("All extended comparison figures successfully created.")
