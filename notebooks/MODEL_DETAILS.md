# Model Details

## Random Forest Classifier
- `n_estimators=100`, `max_depth=20`, `class_weight='balanced'` or custom weights
- Used for initial classification and feature importance analysis

## Stacking Classifier
- Base estimators: Random Forest, Logistic Regression
- Meta-estimator: Logistic Regression
- Wrapped in a pipeline with `StandardScaler`
- Cross-validation: 5-fold

## Performance Metrics
- Accuracy, precision, recall, F1-score (per class)
- Confusion matrix and ROC curves for each class
- Feature importance (built-in and permutation-based)
