#!/usr/bin/env python3
"""Master Figure Generation Suite for SimuGuard-X.

Generates all publication vector PDFs and high-resolution PNGs:
- Fig. Architecture (5-layer neuro-symbolic pipeline)
- Fig. 1 (Counterexample witness trace for AT1)
- Fig. 2 (Gate 2 Solver integrity Step-Collapse Ratio)
- Fig. 3 (Factorial ablation STF distribution)
- Fig. 4 (WTTF break-even survival analysis)
- Fig. 5 (RQ1 specification fidelity)
- Fig. 6 (RQ4 coverage comparison)
- Fig. 7 (RQ7 mutation kill scores)
"""

import subprocess
import sys
from pathlib import Path

def main() -> None:
    scripts_dir = Path(__file__).resolve().parent
    repo_root = scripts_dir.parent

    print("=" * 80)
    print("SIMUGUARD-X: MASTER PUBLICATION FIGURE GENERATOR")
    print("=" * 80)

    generators = [
        ("Architecture Diagram", scripts_dir / "generate_architecture_figure.py"),
        ("Core Figures (Figs 1-4)", scripts_dir / "generate_paper_figures.py"),
        ("Extended Figures (Figs 5-7)", scripts_dir / "generate_extended_paper_figures.py"),
    ]

    for label, script_path in generators:
        print(f"\n>>> Generating: {label} ({script_path.name})...")
        res = subprocess.run([sys.executable, str(script_path)], cwd=str(repo_root))
        if res.returncode != 0:
            print(f"[ERROR] Failed to generate {label} (exit code {res.returncode})")
            sys.exit(res.returncode)
        print(f"[SUCCESS] {label} generated successfully.")

    print("\n" + "=" * 80)
    print("All 8 publication figures generated in paper/figures/ (PDF & PNG)")
    print("=" * 80)

if __name__ == "__main__":
    main()
