#!/usr/bin/env python3
"""
Eagle Sign Analyzer - Implementation Layer
Connects deep architecture to real-world usage
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd
import numpy as np
from datetime import datetime
import json
import logging

# Import core architecture
from eagle_core_architecture import (
    ProductionOrchestrator,
    SignType,
    WorkOrderContext,
    LaborEntry
)

class EagleProductionSystem:
    """Complete production system with context understanding"""
    
    def __init__(self):
        # Configuration
        self.config = self._load_production_config()
        
        # Initialize orchestrator
        self.orchestrator = ProductionOrchestrator(self.config)
        
        # Historical knowledge base
        self.knowledge_base = SignKnowledgeBase()
        
        # Model registry
        self.models = ModelRegistry()
        
        # Data store
        self.data_store = DataStore()
        
        logging.info("Eagle Production System initialized")
    
    def analyze_workorder(self, pdf_path: str) -> Dict:
        """Analyze with full context and ML"""
        
        # Process through pipeline
        result = self.orchestrator.process_document(pdf_path)
        
        if not result['success']:
            return result
            
        # Enhance with knowledge base
        enhanced_results = []
        for wo_result in result['results']:
            enhanced = self.knowledge_base.enhance_with_context(wo_result)
            enhanced_results.append(enhanced)
            
        # Generate recommendations
        recommendations = self._generate_recommendations(enhanced_results)
        
        # Store for continuous learning
        self.data_store.store_results(enhanced_results)
        
        return {
            'success': True,
            'analysis': enhanced_results,
            'recommendations': recommendations,
            'confidence_metrics': self._aggregate_confidence(enhanced_results)
        }
    
    def _generate_recommendations(self, results: List[Dict]) -> Dict:
        """Generate actionable recommendations"""
        recommendations = {
            'labor_hours': {},
            'risk_factors': [],
            'optimization_opportunities': []
        }
        
        for result in results:
            part = result['part_number']
            sign_type = result['sign_type']
            
            # Labor recommendations by phase
            labor_by_phase = self._aggregate_by_phase(result['labor_recommendation'])
            
            recommendations['labor_hours'][part] = {
                'base_hours': labor_by_phase,
                'complexity_adjusted': self._apply_complexity(labor_by_phase, result['complexity_score']),
                'confidence': result['confidence_metrics']['confidence'],
                'suggested_crew': self._suggest_crew_composition(result)
            }
            
            # Risk identification
            if result['complexity_score'] > 2.0:
                recommendations['risk_factors'].append({
                    'part': part,
                    'risk': 'High complexity',
                    'mitigation': 'Assign experienced crew, allow extra time'
                })
                
            # Optimization opportunities
            workflow_issues = result.get('workflow_analysis', {}).get('issues', [])
            for issue in workflow_issues:
                recommendations['optimization_opportunities'].append({
                    'part': part,
                    'issue': issue,
                    'potential_savings': self._estimate_savings(issue)
                })
                
        return recommendations
    
    def _aggregate_by_phase(self, labor_data: Dict) -> Dict:
        """Aggregate hours by work phase"""
        phase_hours = {
            'design': 0,
            'fabrication': 0,
            'electrical': 0,
            'paint': 0,
            'vinyl': 0,
            'installation': 0
        }
        
        phase_mapping = {
            '0098': 'design', '0099': 'design', '0110': 'design',
            '0200': 'fabrication', '0210': 'fabrication', '0215': 'fabrication',
            '0220': 'fabrication', '0230': 'fabrication', '0260': 'fabrication',
            '0310': 'electrical', '0340': 'electrical',
            '0410': 'paint', '0420': 'paint',
            '0510': 'vinyl', '0520': 'vinyl', '0550': 'vinyl',
            '0605': 'installation', '0640': 'installation', '0650': 'installation'
        }
        
        for code, hours in labor_data.items():
            phase = phase_mapping.get(code, 'other')
            if phase in phase_hours:
                phase_hours[phase] += hours
                
        return phase_hours
    
    def _suggest_crew_composition(self, result: Dict) -> Dict:
        """Suggest optimal crew composition"""
        sign_type = SignType(result['sign_type'])
        complexity = result['complexity_score']
        
        crew_templates = {
            SignType.CHANNEL_LETTER: {
                'fabrication': {'welders': 1, 'fabricators': 2},
                'electrical': {'electricians': 1},
                'installation': {'installers': 2, 'crane_operator': 1 if complexity > 1.5 else 0}
            },
            SignType.MONUMENT: {
                'fabrication': {'welders': 2, 'fabricators': 1},
                'electrical': {'electricians': 1},
                'installation': {'installers': 3, 'equipment_operator': 1}
            }
        }
        
        return crew_templates.get(sign_type, {})
    
    def _load_production_config(self) -> str:
        """Load or create production configuration"""
        config_path = Path('config/production.json')
        
        if not config_path.exists():
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            default_config = {
                'version': '1.0.0',
                'pipeline': {
                    'extraction': {
                        'ocr_enabled': True,
                        'table_detection': True
                    },
                    'parsing': {
                        'context_window': 500,
                        'confidence_threshold': 0.7
                    },
                    'ml': {
                        'ensemble_models': ['xgboost', 'lightgbm', 'catboost'],
                        'prediction_intervals': True,
                        'min_samples_for_training': 30
                    }
                },
                'business_rules': {
                    'min_bid_hours': 4.0,
                    'max_overtime_percentage': 0.20,
                    'complexity_multipliers': {
                        'high_rise': 1.3,
                        'difficult_access': 1.2,
                        'weather_sensitive': 1.1
                    }
                },
                'eagle_codes': {
                    # Complete Eagle code mapping
                }
            }
            
            with open(config_path, 'w') as f:
                json.dump(default_config, f, indent=2)
                
        return str(config_path)

class SignKnowledgeBase:
    """Domain knowledge for sign fabrication"""
    
    def __init__(self):
        self.sign_components = self._load_sign_components()
        self.material_relationships = self._load_material_relationships()
        self.workflow_patterns = self._load_workflow_patterns()
        
    def enhance_with_context(self, wo_result: Dict) -> Dict:
        """Add domain knowledge to results"""
        sign_type = SignType(wo_result['sign_type'])
        
        # Add expected components
        wo_result['expected_components'] = self.sign_components.get(sign_type, [])
        
        # Add material correlations
        wo_result['material_correlations'] = self._get_material_correlations(wo_result)
        
        # Add workflow validation
        wo_result['workflow_validation'] = self._validate_workflow(wo_result)
        
        return wo_result
    
    def _load_sign_components(self) -> Dict:
        """Load sign component knowledge"""
        return {
            SignType.CHANNEL_LETTER: [
                {'name': 'face', 'required': True, 'material_options': ['acrylic', 'polycarbonate']},
                {'name': 'return', 'required': True, 'material_options': ['aluminum', 'stainless']},
                {'name': 'back', 'required': True, 'material_options': ['aluminum']},
                {'name': 'LED_modules', 'required': True, 'spacing_inches': 3},
                {'name': 'transformer', 'required': True, 'sizing': 'based_on_LED_count'}
            ],
            SignType.MONUMENT: [
                {'name': 'structure', 'required': True, 'material_options': ['steel', 'aluminum', 'masonry']},
                {'name': 'cladding', 'required': True, 'material_options': ['aluminum', 'ACM', 'stone']},
                {'name': 'foundation', 'required': True, 'depth_feet': 'frost_line_plus_2'},
                {'name': 'electrical_service', 'required': True, 'voltage': 120}
            ]
        }
    
    def _load_material_relationships(self) -> Dict:
        """Load material-to-labor relationships"""
        return {
            'channel_letter_face': {
                'material_codes': ['202-0220'],  # Acrylic
                'triggers_labor': ['0260'],       # Face fabrication
                'sqft_per_hour': 2.5
            },
            'aluminum_return': {
                'material_codes': ['209-0380'],  # Aluminum coil
                'triggers_labor': ['0230'],       # Channel letter fab
                'linear_ft_per_hour': 15
            }
        }
    
    def _validate_workflow(self, wo_result: Dict) -> Dict:
        """Validate workflow sequence"""
        expected_pattern = self.workflow_patterns.get(SignType(wo_result['sign_type']), [])
        actual_codes = [entry['code'] for entry in wo_result.get('labor_entries', [])]
        
        missing_steps = set(expected_pattern) - set(actual_codes)
        out_of_sequence = self._check_sequence(expected_pattern, actual_codes)
        
        return {
            'is_valid': len(missing_steps) == 0 and len(out_of_sequence) == 0,
            'missing_steps': list(missing_steps),
            'out_of_sequence': out_of_sequence,
            'completeness_score': 1 - (len(missing_steps) / max(1, len(expected_pattern)))
        }

class ModelRegistry:
    """Manage ML models with versioning"""
    
    def __init__(self):
        self.models = {}
        self.active_version = None
        self.performance_history = []
        
    def register_model(self, model_id: str, model: any, metadata: Dict):
        """Register new model version"""
        self.models[model_id] = {
            'model': model,
            'metadata': metadata,
            'registered': datetime.now(),
            'performance': {}
        }
        
    def get_active_model(self) -> Optional[any]:
        """Get current production model"""
        if self.active_version:
            return self.models.get(self.active_version, {}).get('model')
        return None
        
    def update_performance(self, model_id: str, metrics: Dict):
        """Track model performance"""
        if model_id in self.models:
            self.models[model_id]['performance'].update(metrics)
            self.performance_history.append({
                'model_id': model_id,
                'timestamp': datetime.now(),
                'metrics': metrics
            })
            
    def select_best_model(self):
        """Select best performing model"""
        # A/B testing logic
        pass

class DataStore:
    """Persistent storage with data lineage"""
    
    def __init__(self, db_path: str = "eagle_production.db"):
        self.db_path = db_path
        self._initialize_db()
        
    def store_results(self, results: List[Dict]):
        """Store analysis results with lineage"""
        import sqlite3
        
        with sqlite3.connect(self.db_path) as conn:
            for result in results:
                # Store work order analysis
                conn.execute("""
                    INSERT INTO analyses (
                        session_id, work_order, part_number, sign_type,
                        complexity_score, analysis_data, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    result.get('session_id'),
                    result['work_order'],
                    result['part_number'],
                    result['sign_type'],
                    result['complexity_score'],
                    json.dumps(result),
                    datetime.now()
                ))
                
    def get_historical_performance(self, part_pattern: str) -> pd.DataFrame:
        """Retrieve historical data for similar parts"""
        import sqlite3
        
        query = """
            SELECT * FROM analyses 
            WHERE part_number LIKE ?
            ORDER BY created_at DESC
            LIMIT 100
        """
        
        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql_query(query, conn, params=[f"%{part_pattern}%"])
            
    def _initialize_db(self):
        """Create database schema"""
        import sqlite3
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    work_order TEXT,
                    part_number TEXT,
                    sign_type TEXT,
                    complexity_score REAL,
                    analysis_data TEXT,
                    created_at TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_part_number 
                ON analyses(part_number)
            """)

# Production CLI
def main():
    """Production command line interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Eagle Sign Production Analyzer')
    parser.add_argument('pdf_path', help='Path to PDF work order')
    parser.add_argument('--output', '-o', default='analysis_output.json', 
                       help='Output file path')
    parser.add_argument('--format', '-f', choices=['json', 'excel', 'report'],
                       default='report', help='Output format')
    parser.add_argument('--confidence', '-c', type=float, default=0.90,
                       help='Confidence interval (0.80-0.99)')
    
    args = parser.parse_args()
    
    # Initialize system
    system = EagleProductionSystem()
    
    # Analyze
    print(f"Analyzing {args.pdf_path}...")
    results = system.analyze_workorder(args.pdf_path)
    
    if not results['success']:
        print(f"Analysis failed: {results.get('error', 'Unknown error')}")
        return 1
        
    # Format output
    if args.format == 'json':
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
    elif args.format == 'excel':
        # Export to Excel
        pass
    else:
        # Generate text report
        report = generate_production_report(results)
        with open(args.output, 'w') as f:
            f.write(report)
            
    print(f"Analysis complete. Output saved to {args.output}")
    return 0

def generate_production_report(results: Dict) -> str:
    """Generate human-readable report"""
    lines = []
    
    lines.append("EAGLE SIGN PRODUCTION ANALYSIS")
    lines.append("="*60)
    lines.append(f"Generated: {datetime.now()}")
    lines.append(f"Confidence Level: {results['confidence_metrics']['overall']:.0%}")
    lines.append("")
    
    for analysis in results['analysis']:
        lines.append(f"\nPART: {analysis['part_number']}")
        lines.append(f"Sign Type: {analysis['sign_type']}")
        lines.append(f"Complexity: {analysis['complexity_score']:.1f}")
        lines.append("")
        
        # Labor recommendations
        lines.append("RECOMMENDED HOURS BY PHASE:")
        for phase, hours in analysis['labor_recommendation'].items():
            lines.append(f"  {phase:15} {hours:8.2f} hrs")
            
        # Warnings
        if analysis.get('warnings'):
            lines.append("\nWARNINGS:")
            for warning in analysis['warnings']:
                lines.append(f"  • {warning}")
                
    return "\n".join(lines)

if __name__ == "__main__":
    sys.exit(main())
