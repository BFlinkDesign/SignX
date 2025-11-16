"""Feature engineering pipeline for cost prediction."""
import pandas as pd
import numpy as np
from typing import List, Dict, Any
from sklearn.preprocessing import StandardScaler, LabelEncoder


class CostFeatureEngineering:
    """Feature engineering for cost prediction models."""
    
    def __init__(self):
        """Initialize feature engineering pipeline."""
        self.scalers = {}
        self.encoders = {}
        self.feature_names = []
    
    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Fit feature engineering pipeline and transform data.
        
        Args:
            df: DataFrame with cost records and drivers
        
        Returns:
            Transformed DataFrame with engineered features
        """
        df = df.copy()
        
        # Extract driver columns from JSONB
        driver_df = self._extract_drivers(df)
        
        # Combine with base features
        features = pd.concat([df, driver_df], axis=1)
        
        # Create interaction features
        features = self._create_interactions(features)
        
        # Encode categorical variables
        features = self._encode_categoricals(features, fit=True)
        
        # Scale numeric features
        features = self._scale_features(features, fit=True)
        
        self.feature_names = features.columns.tolist()
        
        return features
    
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform new data using fitted pipeline.
        
        Args:
            df: DataFrame with cost records and drivers
        
        Returns:
            Transformed DataFrame
        """
        df = df.copy()
        
        driver_df = self._extract_drivers(df)
        features = pd.concat([df, driver_df], axis=1)
        features = self._create_interactions(features)
        features = self._encode_categoricals(features, fit=False)
        features = self._scale_features(features, fit=False)
        
        return features
    
    def _extract_drivers(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract driver JSON into separate columns."""
        if 'drivers' not in df.columns:
            return pd.DataFrame(index=df.index)
        
        # Extract all unique driver keys
        all_drivers = set()
        for drivers in df['drivers']:
            if isinstance(drivers, dict):
                all_drivers.update(drivers.keys())
        
        # Create columns for each driver
        driver_df = pd.DataFrame(index=df.index)
        for driver in all_drivers:
            driver_df[driver] = df['drivers'].apply(
                lambda x: x.get(driver) if isinstance(x, dict) else None
            )
        
        return driver_df
    
    def _create_interactions(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create interaction features."""
        df = df.copy()
        
        # Example: area * height interaction
        if 'sign_area_sqft' in df.columns and 'sign_height_ft' in df.columns:
            df['area_height_interaction'] = (
                df['sign_area_sqft'].fillna(0) * df['sign_height_ft'].fillna(0)
            )
        
        # Example: wind load factor (wind speed * area)
        if 'wind_speed_mph' in df.columns and 'sign_area_sqft' in df.columns:
            df['wind_load_factor'] = (
                df['wind_speed_mph'].fillna(0) * df['sign_area_sqft'].fillna(0)
            )
        
        return df
    
    def _encode_categoricals(self, df: pd.DataFrame, fit: bool = False) -> pd.DataFrame:
        """Encode categorical variables."""
        df = df.copy()
        
        categorical_columns = df.select_dtypes(include=['object', 'category']).columns
        
        for col in categorical_columns:
            if fit:
                self.encoders[col] = LabelEncoder()
                df[f'{col}_encoded'] = self.encoders[col].fit_transform(
                    df[col].fillna('missing')
                )
            else:
                if col in self.encoders:
                    # Handle unseen categories
                    df[f'{col}_encoded'] = df[col].fillna('missing').apply(
                        lambda x: self.encoders[col].transform([x])[0]
                        if x in self.encoders[col].classes_
                        else -1
                    )
            
            # Drop original categorical column
            df = df.drop(columns=[col])
        
        return df
    
    def _scale_features(self, df: pd.DataFrame, fit: bool = False) -> pd.DataFrame:
        """Scale numeric features."""
        df = df.copy()
        
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        numeric_columns = [col for col in numeric_columns if col != 'total_cost']
        
        if fit:
            self.scalers['standard'] = StandardScaler()
            df[numeric_columns] = self.scalers['standard'].fit_transform(
                df[numeric_columns].fillna(0)
            )
        else:
            if 'standard' in self.scalers:
                df[numeric_columns] = self.scalers['standard'].transform(
                    df[numeric_columns].fillna(0)
                )
        
        return df

