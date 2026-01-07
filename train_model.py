import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
import joblib
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import os

class VotingFraudMLTrainer:
    def __init__(self):
        self.isolation_forest = None
        self.random_forest = None
        self.scaler = StandardScaler()
        self.feature_names = [
            'session_duration', 
            'mouse_movements', 
            'keystroke_patterns',
            'hour_of_day', 
            'votes_from_ip', 
            'time_since_page_load'
        ]
        
    def generate_synthetic_data(self, n_samples=1000):
        """Generate synthetic voting data for training"""
        np.random.seed(42)
        
        # Normal voting behavior (90%)
        n_normal = int(n_samples * 0.9)
        normal_data = {
            'session_duration': np.random.normal(30, 10, n_normal),  # 30 sec average
            'mouse_movements': np.random.normal(50, 15, n_normal),    # 50 movements
            'keystroke_patterns': np.random.normal(20, 8, n_normal),  # 20 keystrokes
            'hour_of_day': np.random.choice(range(8, 22), n_normal), # 8 AM - 10 PM
            'votes_from_ip': np.ones(n_normal),                       # Single vote
            'time_since_page_load': np.random.normal(25, 8, n_normal),
            'is_fraud': np.zeros(n_normal)
        }
        
        # Fraudulent behavior (10%)
        n_fraud = n_samples - n_normal
        
        # Type 1: Bot attacks (fast voting, low interaction)
        n_bot = n_fraud // 3
        bot_data = {
            'session_duration': np.random.uniform(1, 5, n_bot),
            'mouse_movements': np.random.uniform(0, 5, n_bot),
            'keystroke_patterns': np.random.uniform(0, 3, n_bot),
            'hour_of_day': np.random.choice(range(24), n_bot),
            'votes_from_ip': np.ones(n_bot),
            'time_since_page_load': np.random.uniform(1, 5, n_bot),
            'is_fraud': np.ones(n_bot)
        }
        
        # Type 2: Multiple voting attempts
        n_multiple = n_fraud // 3
        multiple_data = {
            'session_duration': np.random.normal(20, 8, n_multiple),
            'mouse_movements': np.random.normal(40, 12, n_multiple),
            'keystroke_patterns': np.random.normal(15, 5, n_multiple),
            'hour_of_day': np.random.choice(range(8, 22), n_multiple),
            'votes_from_ip': np.random.uniform(2, 5, n_multiple),
            'time_since_page_load': np.random.normal(20, 6, n_multiple),
            'is_fraud': np.ones(n_multiple)
        }
        
        # Type 3: Unusual timing attacks
        n_timing = n_fraud - n_bot - n_multiple
        timing_data = {
            'session_duration': np.random.normal(25, 10, n_timing),
            'mouse_movements': np.random.normal(45, 15, n_timing),
            'keystroke_patterns': np.random.normal(18, 7, n_timing),
            'hour_of_day': np.random.choice(range(2, 6), n_timing),  # 2-6 AM
            'votes_from_ip': np.ones(n_timing),
            'time_since_page_load': np.random.normal(23, 8, n_timing),
            'is_fraud': np.ones(n_timing)
        }
        
        # Combine all data
        all_data = {}
        for key in normal_data.keys():
            all_data[key] = np.concatenate([
                normal_data[key], 
                bot_data[key], 
                multiple_data[key], 
                timing_data[key]
            ])
        
        df = pd.DataFrame(all_data)
        
        # Add some noise to make it realistic
        for col in self.feature_names:
            noise = np.random.normal(0, 0.1, len(df))
            df[col] = df[col] + noise
            df[col] = df[col].clip(lower=0)  # Ensure non-negative values
        
        return df
    
    def load_data_from_database(self):
        """Load real voting data from database"""
        # This would connect to your PostgreSQL database
        # For now, we'll use synthetic data
        print("Loading data from database...")
        # Implement database connection here
        pass
    
    def train_isolation_forest(self, X_train):
        """Train Isolation Forest for anomaly detection"""
        print("\nTraining Isolation Forest...")
        
        self.isolation_forest = IsolationForest(
            contamination=0.1,
            random_state=42,
            n_estimators=100,
            max_samples='auto',
            max_features=1.0,
            bootstrap=False,
            n_jobs=-1,
            verbose=1
        )
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        
        # Train model
        self.isolation_forest.fit(X_train_scaled)
        
        print("✓ Isolation Forest trained successfully")
        
    def train_random_forest(self, X_train, y_train):
        """Train Random Forest classifier"""
        print("\nTraining Random Forest Classifier...")
        
        self.random_forest = RandomForestClassifier(
            n_estimators=200,
            max_depth=10,
            min_samples_split=10,
            min_samples_leaf=5,
            random_state=42,
            n_jobs=-1,
            verbose=1,
            class_weight='balanced'
        )
        
        # Scale features
        X_train_scaled = self.scaler.transform(X_train)
        
        # Train model
        self.random_forest.fit(X_train_scaled, y_train)
        
        # Cross-validation
        cv_scores = cross_val_score(self.random_forest, X_train_scaled, y_train, cv=5)
        print(f"Cross-validation scores: {cv_scores}")
        print(f"Mean CV score: {cv_scores.mean():.4f} (+/- {cv_scores.std() * 2:.4f})")
        
        print("✓ Random Forest trained successfully")
    
    def evaluate_models(self, X_test, y_test):
        """Evaluate both models"""
        print("\n" + "="*60)
        print("MODEL EVALUATION")
        print("="*60)
        
        X_test_scaled = self.scaler.transform(X_test)
        
        # Isolation Forest Evaluation
        print("\n--- Isolation Forest ---")
        if_predictions = self.isolation_forest.predict(X_test_scaled)
        if_predictions = np.where(if_predictions == -1, 1, 0)  # Convert to binary
        
        print("\nClassification Report:")
        print(classification_report(y_test, if_predictions, 
                                   target_names=['Normal', 'Fraud']))
        
        print("\nConfusion Matrix:")
        cm_if = confusion_matrix(y_test, if_predictions)
        print(cm_if)
        
        # Random Forest Evaluation
        print("\n--- Random Forest Classifier ---")
        rf_predictions = self.random_forest.predict(X_test_scaled)
        rf_proba = self.random_forest.predict_proba(X_test_scaled)[:, 1]
        
        print("\nClassification Report:")
        print(classification_report(y_test, rf_predictions,
                                   target_names=['Normal', 'Fraud']))
        
        print("\nConfusion Matrix:")
        cm_rf = confusion_matrix(y_test, rf_predictions)
        print(cm_rf)
        
        print(f"\nROC-AUC Score: {roc_auc_score(y_test, rf_proba):.4f}")
        
        # Feature Importance
        print("\n--- Feature Importance ---")
        feature_importance = pd.DataFrame({
            'feature': self.feature_names,
            'importance': self.random_forest.feature_importances_
        }).sort_values('importance', ascending=False)
        
        print(feature_importance)
        
        return {
            'isolation_forest': {
                'predictions': if_predictions,
                'confusion_matrix': cm_if
            },
            'random_forest': {
                'predictions': rf_predictions,
                'probabilities': rf_proba,
                'confusion_matrix': cm_rf,
                'feature_importance': feature_importance
            }
        }
    
    def plot_results(self, results, y_test):
        """Visualize model performance"""
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        
        # Confusion Matrix - Isolation Forest
        sns.heatmap(results['isolation_forest']['confusion_matrix'], 
                   annot=True, fmt='d', cmap='Blues', ax=axes[0, 0])
        axes[0, 0].set_title('Isolation Forest - Confusion Matrix')
        axes[0, 0].set_ylabel('True Label')
        axes[0, 0].set_xlabel('Predicted Label')
        
        # Confusion Matrix - Random Forest
        sns.heatmap(results['random_forest']['confusion_matrix'],
                   annot=True, fmt='d', cmap='Greens', ax=axes[0, 1])
        axes[0, 1].set_title('Random Forest - Confusion Matrix')
        axes[0, 1].set_ylabel('True Label')
        axes[0, 1].set_xlabel('Predicted Label')
        
        # Feature Importance
        feature_imp = results['random_forest']['feature_importance']
        axes[1, 0].barh(feature_imp['feature'], feature_imp['importance'])
        axes[1, 0].set_xlabel('Importance')
        axes[1, 0].set_title('Random Forest Feature Importance')
        
        # Prediction Distribution
        rf_proba = results['random_forest']['probabilities']
        axes[1, 1].hist([rf_proba[y_test == 0], rf_proba[y_test == 1]], 
                       bins=30, label=['Normal', 'Fraud'], alpha=0.7)
        axes[1, 1].set_xlabel('Fraud Probability')
        axes[1, 1].set_ylabel('Frequency')
        axes[1, 1].set_title('Prediction Probability Distribution')
        axes[1, 1].legend()
        
        plt.tight_layout()
        plt.savefig('model_evaluation.png', dpi=300, bbox_inches='tight')
        print("\n✓ Evaluation plots saved as 'model_evaluation.png'")
    
    def save_models(self, output_dir='models'):
        """Save trained models"""
        os.makedirs(output_dir, exist_ok=True)
        
        joblib.dump(self.isolation_forest, f'{output_dir}/isolation_forest.pkl')
        joblib.dump(self.random_forest, f'{output_dir}/random_forest.pkl')
        joblib.dump(self.scaler, f'{output_dir}/scaler.pkl')
        
        # Save metadata
        metadata = {
            'trained_date': datetime.now().isoformat(),
            'feature_names': self.feature_names,
            'contamination_rate': 0.1,
            'n_estimators_if': 100,
            'n_estimators_rf': 200
        }
        
        joblib.dump(metadata, f'{output_dir}/model_metadata.pkl')
        
        print(f"\n✓ Models saved to '{output_dir}/' directory")
    
    def run_training_pipeline(self, use_synthetic=True, n_samples=5000):
        """Run complete training pipeline"""
        print("="*60)
        print("VOTING FRAUD DETECTION - ML MODEL TRAINING")
        print("="*60)
        
        # Load or generate data
        if use_synthetic:
            print(f"\nGenerating {n_samples} synthetic samples...")
            df = self.generate_synthetic_data(n_samples)
        else:
            df = self.load_data_from_database()
        
        print(f"Dataset shape: {df.shape}")
        print(f"Fraud cases: {df['is_fraud'].sum()} ({df['is_fraud'].mean()*100:.2f}%)")
        
        # Prepare data
        X = df[self.feature_names]
        y = df['is_fraud']
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        print(f"\nTraining set: {X_train.shape}")
        print(f"Test set: {X_test.shape}")
        
        # Train models
        self.train_isolation_forest(X_train)
        self.train_random_forest(X_train, y_train)
        
        # Evaluate models
        results = self.evaluate_models(X_test, y_test)
        
        # Plot results
        self.plot_results(results, y_test)
        
        # Save models
        self.save_models()
        
        print("\n" + "="*60)
        print("TRAINING COMPLETE!")
        print("="*60)

if __name__ == '__main__':
    trainer = VotingFraudMLTrainer()
    trainer.run_training_pipeline(use_synthetic=True, n_samples=5000)