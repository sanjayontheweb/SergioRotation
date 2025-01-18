# SergioRotation
# Addiction and Alcohol Dependence Prediction Pipeline

This repository contains a pipeline for predicting alcohol and opioid dependence using electronic health records (EHRs) and graph embeddings from the Scalable Precision Medicine Open Knowledge Engine (SPOKE). The project includes querying relevant EHR data, embedding patient concepts as personalized SPOKE embedding vectors (PSEVs), and training machine learning models to classify dependence status.

---

## Repository Structure

### Main Components

1. **Querying EHR Data:**
   - Extracts patient records relevant to addiction and SPOKE concepts using UCSF's OMOP de-identified EHR database.

2. **Embedding Patient Data:**
   - Converts patient-specific SPOKE concepts into PSEVs, representing weighted graph features unique to each patient.

3. **Random Forest Training:**
   - Trains random forest (RF) classifiers on PSEVs to predict alcohol and opioid dependence.

4. **Feature Comparison:**
   - Analyzes the most important features from the RF models.

### File Overview

#### Notebooks and Scripts
- **AddictionEHRQuery.ipynb / AlcoholEHRQuery.ipynb**: Notebooks for querying addiction and alcohol-related EHR data.
- **AddictionEmbedding.ipynb / AlcoholEmbedding.ipynb**: Embedding patient SPOKE concepts into PSEVs.
- **Addiction_RF.ipynb / Alcohol_RF.ipynb**: Training random forest classifiers for addiction and alcohol dependence.
- **CompareFeatures.ipynb**: Comparing important features across models.

#### Data Files
- **data/**: Contains various intermediate and processed data files:
  - `.feather` files: Cohort details and concept maps.
  - `.npy` files: Patient embeddings segmented by node type.
  - `.tsv` files: Mapping between OMOP and SPOKE concepts.
  
- **features/**: Stores top feature tables from RF models.
- **models/**: Saved trained models (e.g., random forest, AdaBoost).

#### Configuration Files
- **cdw_db_config.ini / omop_db_config.ini**: Database connection details for querying UCSF's OMOP EHR database.

#### Other Files
- **README.md**: This file.
- **effect_size.png**: Visualization of feature effect sizes.

---

## Pipeline Overview

### 1. EHR Query
- Extract patient records related to alcohol and opioid dependence.
- Identify SPOKE concepts associated with each patient.
- Save the results in `.csv` and `.feather` formats.

### 2. Embedding
- Map SPOKE concepts to embedding vectors using the SPOKE graph.
- Generate PSEVs for each patient to capture unique relationships in the knowledge graph.
- Save embeddings as `.npy` files, segmented by node type.

### 3. Random Forest Training
- Train random forest classifiers using PSEVs to predict alcohol and opioid dependence.
- Save models in the `models/` directory for reuse.

### 4. Feature Comparison
- Analyze the most important features identified by the RF models.
- Compare the results between alcohol and addiction datasets.

---

## Data Requirements

### Input Data
- **EHR Data**: Extracted from UCSF's OMOP de-identified EHR database.
- **SPOKE Graph**: Used to derive patient-specific embedding vectors.

### Intermediate and Processed Data
- **Cohort Data**: `.feather` files storing patient cohort details.
- **Embeddings**: `.npy` files containing patient embeddings.

### Output Data
- **Predictions**: Random forest classification results.
- **Feature Importance**: CSVs summarizing top features.

---

## Usage Instructions

### Prerequisites
- Python environment with the following libraries:
  - pandas, numpy, scikit-learn, feather-format, matplotlib
- Access to UCSF's OMOP EHR database.
- SPOKE graph and associated tools for generating embeddings.

### Steps
1. Configure database access in `cdw_db_config.ini` or `omop_db_config.ini`.
2. Run the query notebooks to extract relevant EHR data.
3. Generate PSEVs using the embedding notebooks.
4. Train the RF classifiers using the `*_RF.ipynb` notebooks.
5. Compare feature importance using `CompareFeatures.ipynb`.

---

## Acknowledgments

This work leverages:
- UCSF's OMOP de-identified EHR database.
- SPOKE: Scalable Precision Medicine Open Knowledge Engine.

For questions, contact the repository maintainer.

