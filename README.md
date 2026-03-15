# Materiamind

![Language](https://img.shields.io/badge/Language-Python-3776AB?style=flat-square) ![Stars](https://img.shields.io/github/stars/Devanik21/MateriaMind?style=flat-square&color=yellow) ![Forks](https://img.shields.io/github/forks/Devanik21/MateriaMind?style=flat-square&color=blue) ![Author](https://img.shields.io/badge/Author-Devanik21-black?style=flat-square&logo=github) ![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=flat-square)

> AI for materials discovery — predicting material properties, screening candidate structures, and accelerating computational materials science workflows.

---

**Topics:** `active-inference` · `autopoietic-systems` · `cognitive-architecture` · `free-energy-principle` · `healthcare-ai` · `homeopathic-medicine` · `medical-diagnosis` · `personalized-medicine` · `predictive-coding` · `self-modeling`

## Overview

MateriaMind is a machine learning toolkit for accelerated computational materials science, targeting
one of the most computationally expensive problems in chemistry and physics: predicting material
properties from crystal structure without running expensive Density Functional Theory (DFT) simulations
for every candidate. It trains and deploys property prediction models on existing DFT-computed datasets
(Materials Project, AFLOW, OQMD) to provide fast, ML-based property screening as a first-pass filter
before expensive quantum chemistry calculations.

The platform supports regression and classification tasks across multiple material property categories:
electronic (band gap, conductivity type, effective mass), mechanical (Young's modulus, bulk modulus,
Poisson ratio), thermodynamic (formation energy, decomposition enthalpy, thermal conductivity),
and magnetic (magnetic moment, ordering temperature). Each property model is trained on the
appropriate dataset partition and evaluated with domain-relevant metrics (formation energy MAE in
eV/atom, band gap MAE in eV).

Crystal structures are represented through multiple featurisation schemes — Coulomb matrices,
Many-Body Tensor Representation (MBTR), Smooth Overlap of Atomic Positions (SOAP), and graph-based
representations for use with Message Passing Neural Networks (MPNNs) — allowing systematic comparison
of structural descriptors for different property prediction tasks.

---

## Motivation

Materials discovery through pure DFT calculation is tractable for hundreds of candidates but prohibitive
for the millions of plausible structures in crystal structure prediction problems. ML surrogates that
achieve DFT-quality accuracy at CPU-millisecond inference time are therefore transformative for
the discovery of battery materials, catalysts, semiconductors, and structural alloys. MateriaMind
was built to make those ML surrogates accessible to materials science researchers without a deep
ML engineering background.

---

## Architecture

```
Crystal Structure Input (CIF / POSCAR / JSON)
        │
  Structure preprocessing (ase / pymatgen)
        │
  Featurisation:
  ├── Coulomb Matrix (CM)
  ├── MBTR (Many-Body Tensor Representation)
  ├── SOAP (Smooth Overlap of Atomic Positions)
  └── Crystal Graph (for MPNN / SchNet)
        │
  Property Predictor:
  ├── Random Forest / Gradient Boosting (CM, MBTR)
  ├── Kernel Ridge Regression (SOAP)
  └── SchNet / MEGNet / CGCNN (Crystal Graph)
        │
  Prediction + uncertainty estimation
        │
  Candidate screening and Pareto front visualisation
```

---

## Features

### Multi-Property Prediction Models
Trained models for electronic, mechanical, thermodynamic, and magnetic properties — each optimised for the appropriate structural descriptor and evaluated on held-out Materials Project data.

### Multiple Featurisation Schemes
Crystal structure featurisation via Coulomb Matrix, MBTR, SOAP, and graph representations — with a benchmark comparison of accuracy vs. computational cost per featuriser.

### Graph Neural Network Models
SchNet and Crystal Graph Convolutional Neural Network (CGCNN) implementations for end-to-end property prediction directly from crystal graphs without hand-crafted descriptors.

### Uncertainty Quantification
Monte Carlo Dropout and ensemble-based uncertainty estimates for all predictions — critical for identifying candidates at the ML model's confidence boundary that require DFT validation.

### High-Throughput Screening
Screen thousands of candidate structures from CIF file directories or Materials Project API queries against target property windows, outputting a Pareto-optimal candidate list.

### Materials Project API Integration
Query the Materials Project database programmatically for training data, property benchmarks, and structure validation via the pymatgen MPRester interface.

### Property Distribution Visualisation
Interactive Plotly charts of property distributions across the training dataset, t-SNE/UMAP projections of the structural feature space, and Pareto front plots for multi-objective screening.

### Model Interpretability
SHAP feature importance for tree-based models, showing which atomic descriptors most strongly influence each property prediction.

---

## Tech Stack

| Library / Tool | Role | Why This Choice |
|---|---|---|
| **pymatgen** | Materials analysis | Crystal structure parsing, symmetry analysis, MP API |
| **ase** | Atomic simulation | Structure I/O, Coulomb matrix, SOAP via dscribe |
| **dscribe** | Featurisation | MBTR, SOAP, Coulomb Matrix descriptors |
| **PyTorch Geometric** | Graph neural networks | SchNet and CGCNN implementations |
| **scikit-learn** | Classical ML models | RF, GBM, KRR for descriptor-based models |
| **SHAP** | Interpretability | Feature importance for tree-based property models |
| **Plotly** | Visualisation | Property distributions, Pareto fronts, t-SNE projections |

---

## Getting Started

### Prerequisites

- Python 3.9+ (or Node.js 18+ for TypeScript/JavaScript projects)
- A virtual environment manager (`venv`, `conda`, or equivalent)
- API keys as listed in the Configuration section

### Installation

```bash
git clone https://github.com/Devanik21/MateriaMind.git
cd MateriaMind
python -m venv venv && source venv/bin/activate
pip install pymatgen ase dscribe scikit-learn shap plotly torch torch-geometric pandas
# MP API key for training data: https://materialsproject.org/api
echo 'MP_API_KEY=your_key' > .env
streamlit run app.py
```

---

## Usage

```bash
# Predict band gap for a crystal structure
python predict.py --structure POSCAR --property band_gap --model schnet

# Screen a database of structures
python screen.py --input structures/ --property_window 'band_gap:1.0-2.5,e_above_hull:<0.1'

# Train a new property model
python train.py --property formation_energy --featuriser soap --model kridge

# Query Materials Project for training data
python fetch_mp_data.py --formula Li --property band_gap --output mp_band_gaps.json
```

---

## Configuration

| Variable | Default | Description |
|---|---|---|
| `MP_API_KEY` | `(required)` | Materials Project API key for data access |
| `DEFAULT_FEATURISER` | `mbtr` | Structural featuriser: cm, mbtr, soap, graph |
| `DEFAULT_MODEL` | `rf` | ML model: rf, gbm, kridge, schnet, cgcnn |
| `UNCERTAINTY_SAMPLES` | `100` | MC Dropout samples for uncertainty estimation |
| `SCREEN_PARETO_OBJECTIVES` | `band_gap,stability` | Property objectives for Pareto screening |

> Copy `.env.example` to `.env` and populate required values before running.

---

## Project Structure

```
MateriaMind/
├── README.md
├── requirements.txt
├── app.py
└── ...
```

---

## Roadmap

- [ ] Generative model for inverse materials design: GAN or diffusion model conditioned on target properties
- [ ] Active learning loop: iteratively query DFT for the most informative uncertain predictions
- [ ] Phonon spectrum prediction for thermal conductivity and dynamical stability assessment
- [ ] Integration with VASP and Quantum ESPRESSO for automated DFT validation of screened candidates
- [ ] Transfer learning from bulk to surface properties for catalysis applications

---

## Contributing

Contributions, issues, and suggestions are welcome.

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-idea`
3. Commit your changes: `git commit -m 'feat: add your idea'`
4. Push to your branch: `git push origin feature/your-idea`
5. Open a Pull Request with a clear description

Please follow conventional commit messages and add documentation for new features.

---

## Notes

MateriaMind ML models achieve DFT-comparable accuracy for their training distribution but may extrapolate poorly to chemistries outside the training set. Always validate ML-screened candidates with DFT or experiment before drawing scientific conclusions. Formation energy models from the Materials Project have their own systematic errors relative to experiment.

---

## Author

**Devanik Debnath**  
B.Tech, Electronics & Communication Engineering  
National Institute of Technology Agartala

[![GitHub](https://img.shields.io/badge/GitHub-Devanik21-black?style=flat-square&logo=github)](https://github.com/Devanik21)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-devanik-blue?style=flat-square&logo=linkedin)](https://www.linkedin.com/in/devanik/)

---

## License

This project is open source and available under the [MIT License](LICENSE).

---

*Built with curiosity, depth, and care — because good projects deserve good documentation.*
