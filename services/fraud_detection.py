import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import joblib
from datetime import datetime, timedelta

class DynamicFraudDetectionEngine:
    def __init__(self):
        self.isolation_forest = None
        self.random_forest = None
        self.scaler = StandardScaler()
        self.is_trained = False
        self.config = self.load_configuration()
        self.feature_names = self.config.get('features', [
            'session_duration', 'mouse_movements', 'keystroke_patterns',
            'hour_of_day', 'votes_from_ip', 'time_since_page_load'
        ])
        
    def load_configuration(self):
        """Load dynamic ML configuration from database"""
        try:
            from models.audit import MLModelConfiguration
            model_config = MLModelConfiguration.query.filter_by(is_active=True).first()
            if model_config:
                return {
                    'features': list(model_config.parameters.get('features', [])),
                    'thresholds': model_config.threshold_config or {},
                    'weights': model_config.feature_weights or {}
                }
        except:
            pass
        
        # Default configuration
        return {
            'features': [
                'session_duration', 'mouse_movements', 'keystroke_patterns',
                'hour_of_day', 'votes_from_ip', 'time_since_page_load'
            ],
            'thresholds': {
                'fast_voting': 5000,  # milliseconds
                'low_interaction': 5,
                'unusual_hours_start': 2,
                'unusual_hours_end': 5,
                'high_risk_score': 0.75,
                'medium_risk_score': 0.45
            },
            'weights': {
                'session_duration': 0.25,
                'mouse_movements': 0.20,
                'keystroke_patterns': 0.15,
                'hour_of_day': 0.15,
                'votes_from_ip': 0.25
            }
        }
    
    def extract_features(self, vote_data):
        """Extract features dynamically based on configuration"""
        from models.vote import Vote
        
        timestamp = datetime.fromisoformat(vote_data['timestamp']) if isinstance(vote_data['timestamp'], str) else vote_data['timestamp']
        
        # Dynamic IP vote counting
        recent_votes = Vote.query.filter(
            Vote.ip_address == vote_data['ip_address'],
            Vote.timestamp >= datetime.utcnow() - timedelta(minutes=30)
        ).count()
        
        features = {
            'session_duration': vote_data.get('session_duration', 0) / 1000,
            'mouse_movements': vote_data.get('mouse_movements', 0),
            'keystroke_patterns': vote_data.get('keystroke_patterns', 0),
            'hour_of_day': timestamp.hour,
            'votes_from_ip': recent_votes,
            'time_since_page_load': vote_data.get('time_since_page_load', 0) / 1000
        }
        
        return features
    
    def calculate_anomaly_score(self, features):
        """Calculate anomaly score using dynamic thresholds"""
        score = 0.0
        reasons = []
        thresholds = self.config['thresholds']
        weights = self.config['weights']
        
        # Dynamic fast voting detection
        if features['session_duration'] < (thresholds.get('fast_voting', 5000) / 1000):
            weight = weights.get('session_duration', 0.35)
            score += weight
            reasons.append(f'Unusually fast voting (< {thresholds.get("fast_voting")/1000}s)')
        
        # Dynamic multiple voting detection
        if features['votes_from_ip'] > 1:
            weight = weights.get('votes_from_ip', 0.40)
            score += weight
            reasons.append(f'Multiple votes from IP ({features["votes_from_ip"]} attempts)')
        
        # Dynamic unusual hours detection
        unusual_start = thresholds.get('unusual_hours_start', 2)
        unusual_end = thresholds.get('unusual_hours_end', 5)
        if features['hour_of_day'] >= unusual_start and features['hour_of_day'] <= unusual_end:
            weight = weights.get('hour_of_day', 0.20)
            score += weight
            reasons.append(f'Voting during unusual hours ({unusual_start}AM - {unusual_end}AM)')
        
        # Dynamic low interaction detection
        low_interaction_threshold = thresholds.get('low_interaction', 5)
        if features['mouse_movements'] < low_interaction_threshold:
            weight = weights.get('mouse_movements', 0.25)
            score += weight
            reasons.append(f'Low user interaction (< {low_interaction_threshold} movements)')
        
        if features['keystroke_patterns'] < 3:
            weight = weights.get('keystroke_patterns', 0.15)
            score += weight
            reasons.append('Minimal keyboard activity')
        
        # ML model prediction if trained
        if self.is_trained:
            try:
                feature_vector = np.array([[
                    features['session_duration'],
                    features['mouse_movements'],
                    features['keystroke_patterns'],
                    features['hour_of_day'],
                    features['votes_from_ip'],
                    features['time_since_page_load']
                ]])
                
                scaled_features = self.scaler.transform(feature_vector)
                ml_prediction = self.isolation_forest.predict(scaled_features)[0]
                
                if ml_prediction == -1:
                    score = max(score, 0.8)
                    reasons.append('ML model detected anomalous pattern')
            except Exception as e:
                print(f"ML prediction error: {e}")
        
        return min(score, 1.0), reasons
    
    def assess_risk_level(self, anomaly_score):
        """Assess risk level using dynamic thresholds"""
        thresholds = self.config['thresholds']
        high_threshold = thresholds.get('high_risk_score', 0.75)
        medium_threshold = thresholds.get('medium_risk_score', 0.45)
        
        if anomaly_score >= high_threshold:
            return 'HIGH'
        elif anomaly_score >= medium_threshold:
            return 'MEDIUM'
        return 'LOW'
    
    def analyze_vote(self, vote_data):
        """Main analysis function"""
        features = self.extract_features(vote_data)
        anomaly_score, reasons = self.calculate_anomaly_score(features)
        risk_level = self.assess_risk_level(anomaly_score)
        
        return {
            'anomaly_score': round(anomaly_score, 3),
            'risk_level': risk_level,
            'is_flagged': anomaly_score > self.config['thresholds'].get('medium_risk_score', 0.45),
            'reasons': reasons,
            'features': features
        }


# Initialize fraud detector
fraud_detector = DynamicFraudDetectionEngine()