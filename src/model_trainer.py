import os
import pandas as pd
import mlflow
import mlflow.sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
import joblib
import io
import logging
from logging.handlers import RotatingFileHandler

class ModelTrainer:
    def __init__(self, mlflow_uri: str = "http://192.168.1.86:5050", log_level=logging.INFO):
        """
        Initialize the ModelTrainer.

        Parameters
        ----------
        mlflow_uri : str
            The URI of the MLflow tracking server.
        log_level : int
            The log level. Default is logging.INFO.

        Notes
        -----
        This initializer sets up logging and MLflow.
        If an existing model is found, it is loaded.
        If an error occurs during initialization, an exception is raised.
        """
        # Initialize logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(log_level)
        
        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)
        
        # Create handlers
        file_handler = RotatingFileHandler(
            'logs/model_trainer.log',
            maxBytes=10485760,  # 10MB
            backupCount=5
        )
        console_handler = logging.StreamHandler()
        
        # Create formatters and add it to handlers
        log_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(log_format)
        console_handler.setFormatter(log_format)
        
        # Add handlers to the logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # ML-Flow settings to be logged
        self.model_path = "model.pkl"
        self.experiment_name = "CICD_IDS_Model_v1"
        self.mlflow_uri = mlflow_uri
        
        self.logger.info(f"Initializing ModelTrainer with MLflow URI: {mlflow_uri}")
        
        try:
            # Set up MLflow
            mlflow.set_tracking_uri(self.mlflow_uri)
            mlflow.set_experiment(self.experiment_name)
            self.logger.info(f"MLflow experiment '{self.experiment_name}' set up successfully")
                            
        except Exception as e:
            self.logger.error(f"Error during initialization: {str(e)}", exc_info=True)
            raise

    

    def train(self, X: pd.DataFrame, y: pd.Series) -> dict:
        """
        Train the model with the provided data and labels
        
        Args:
            X (pd.DataFrame): Training features
            y (pd.Series): Target labels
            
        Returns:
            dict: Training results including accuracy
        """
        self.logger.info(f"Starting model training with data shape: {X.shape}")
        
        try:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )
            self.logger.debug(f"Train set shape: {X_train.shape}, Test set shape: {X_test.shape}")
            
            class_weights = {0:1, 1:1, 2:1, 3:1, 4:4, 5:5, 6:1, 7:1, 8:1, 9:1}
            
            rf_classifier = RandomForestClassifier(
                n_estimators=100,
                max_depth=20,
                class_weight=class_weights,
                random_state=42,
                n_jobs=-1
            )
            
            self.pipeline = Pipeline([
                ('scaler', StandardScaler()),
                ('classifier', rf_classifier)
            ])
            
            with mlflow.start_run(run_name="RandomForest_Weighted") as run:
                self.logger.info(f"MLflow run started with run_id: {run.info.run_id}")
                
                #Log the training dataset
                dataset = pd.concat([X_train, y_train], axis=1)
                dataset.columns = [*X.columns, y.name]
                dataset.to_csv("dataset.csv", index=False)
                mlflow.log_artifact("dataset.csv")
                                
                # Log parameters
                params = {
                    "n_estimators": 100,
                    "max_depth": 20,
                    "class_weight": class_weights,
                    "random_state": 42,
                    "n_jobs": -1
                }
                mlflow.log_params(params)
                
                # Train the model
                self.logger.info("Training model...")
                self.pipeline.fit(X_train, y_train)
                self.logger.info("Model training completed")
                
                # Evaluate
                y_pred = self.pipeline.predict(X_test)
                accuracy = accuracy_score(y_test, y_pred)
                self.logger.info(f"Model accuracy: {accuracy}")
                
                # Log metrics
                mlflow.log_metric("accuracy", accuracy)
                
                # Generate and log classification report
                report_text = classification_report(y_test, y_pred)
                mlflow.log_text(report_text, "classification_report.txt")
                
                # Save and log feature importance
                feature_importance = pd.DataFrame({
                    'feature': X.columns,
                    'importance': rf_classifier.feature_importances_
                }).sort_values('importance', ascending=False)
                feature_importance.to_json("feature_importance.json", orient="records", indent=2)
                mlflow.log_artifact("feature_importance.json")
                
                # Log model
                self.logger.info("Logging model to MLflow...")
                mlflow.sklearn.log_model(
                    sk_model=self.pipeline,
                    artifact_path="model",
                    registered_model_name="CICD_IDS_Model"
                )             
                
                
            return {
                "message": "Model trained and registered in MLflow",
                "accuracy": accuracy,
                "mlflow_uri": self.mlflow_uri,
                "run_id": run.info.run_id
            }
            
        except Exception as e:
            self.logger.error(f"Error during model training: {str(e)}", exc_info=True)
            raise