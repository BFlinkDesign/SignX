#!/usr/bin/env python3
"""
Eagle Sign Memory Agent & Centralized Cost Database
Persistent memory and comprehensive cost tracking
"""

import sqlite3
import json
import pickle
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import numpy as np
from dataclasses import dataclass, asdict
import hashlib

@dataclass
class CostEntry:
    """Cost database entry"""
    category: str  # labor, material, overhead, equipment
    code: str
    description: str
    unit: str  # hour, SF, EA, etc
    cost: float
    effective_date: datetime
    expiry_date: Optional[datetime]
    source: str  # invoice, quote, contract
    notes: str

class MemoryAgent:
    """Intelligent memory management for Eagle system"""
    
    def __init__(self, db_path: str = "eagle_memory.db"):
        self.db_path = db_path
        self._init_database()
        
    def _init_database(self):
        """Initialize memory database"""
        with sqlite3.connect(self.db_path) as conn:
            # Analysis memory
            conn.execute("""
                CREATE TABLE IF NOT EXISTS analysis_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    part_number TEXT,
                    sign_type TEXT,
                    analysis_data TEXT,
                    predictions TEXT,
                    actual_hours TEXT,
                    accuracy_score REAL,
                    created_at TIMESTAMP,
                    UNIQUE(session_id, part_number)
                )
            """)
            
            # Pattern memory
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pattern_memory (
                    pattern_id TEXT PRIMARY KEY,
                    pattern_type TEXT,  -- workflow, crew, seasonal
                    pattern_data TEXT,
                    confidence REAL,
                    occurrences INTEGER,
                    last_seen TIMESTAMP,
                    created_at TIMESTAMP
                )
            """)
            
            # Learning memory
            conn.execute("""
                CREATE TABLE IF NOT EXISTS learning_memory (
                    learning_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    concept TEXT,  -- what was learned
                    context TEXT,  -- when/where it applies
                    impact REAL,   -- effect on accuracy
                    examples TEXT,
                    created_at TIMESTAMP
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_part_sign ON analysis_memory(part_number, sign_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_pattern_type ON pattern_memory(pattern_type)")
    
    def remember_analysis(self, analysis: Dict) -> str:
        """Store analysis in memory"""
        memory_id = hashlib.md5(f"{analysis['session_id']}{analysis['part_number']}".encode()).hexdigest()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO analysis_memory 
                (session_id, part_number, sign_type, analysis_data, predictions, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                analysis['session_id'],
                analysis['part_number'],
                analysis.get('sign_type'),
                json.dumps(analysis),
                json.dumps(analysis.get('predictions', {})),
                datetime.now()
            ))
            
        return memory_id
    
    def recall_similar(self, part_number: str, sign_type: str = None, limit: int = 10) -> List[Dict]:
        """Recall similar past analyses"""
        with sqlite3.connect(self.db_path) as conn:
            # Pattern matching for similar parts
            base_pattern = part_number[:6] if len(part_number) > 6 else part_number
            
            query = """
                SELECT analysis_data, accuracy_score
                FROM analysis_memory
                WHERE part_number LIKE ? 
            """
            params = [f"{base_pattern}%"]
            
            if sign_type:
                query += " AND sign_type = ?"
                params.append(sign_type)
                
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            cursor = conn.execute(query, params)
            
            results = []
            for row in cursor:
                data = json.loads(row[0])
                data['historical_accuracy'] = row[1]
                results.append(data)
                
        return results
    
    def learn_pattern(self, pattern_type: str, pattern_data: Dict):
        """Learn and store patterns"""
        pattern_id = hashlib.md5(f"{pattern_type}{json.dumps(pattern_data, sort_keys=True)}".encode()).hexdigest()
        
        with sqlite3.connect(self.db_path) as conn:
            # Check if pattern exists
            existing = conn.execute(
                "SELECT occurrences, confidence FROM pattern_memory WHERE pattern_id = ?",
                (pattern_id,)
            ).fetchone()
            
            if existing:
                # Update existing pattern
                occurrences = existing[0] + 1
                confidence = min(0.95, existing[1] + 0.05)  # Increase confidence
                
                conn.execute("""
                    UPDATE pattern_memory 
                    SET occurrences = ?, confidence = ?, last_seen = ?
                    WHERE pattern_id = ?
                """, (occurrences, confidence, datetime.now(), pattern_id))
            else:
                # New pattern
                conn.execute("""
                    INSERT INTO pattern_memory 
                    (pattern_id, pattern_type, pattern_data, confidence, occurrences, last_seen, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    pattern_id, pattern_type, json.dumps(pattern_data),
                    0.5, 1, datetime.now(), datetime.now()
                ))
    
    def get_patterns(self, pattern_type: str, min_confidence: float = 0.7) -> List[Dict]:
        """Retrieve learned patterns"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT pattern_data, confidence, occurrences
                FROM pattern_memory
                WHERE pattern_type = ? AND confidence >= ?
                ORDER BY confidence DESC, occurrences DESC
            """, (pattern_type, min_confidence))
            
            patterns = []
            for row in cursor:
                patterns.append({
                    'data': json.loads(row[0]),
                    'confidence': row[1],
                    'occurrences': row[2]
                })
                
        return patterns
    
    def update_accuracy(self, session_id: str, part_number: str, actual_hours: Dict, predicted_hours: Dict):
        """Update accuracy after job completion"""
        # Calculate accuracy
        accuracy_scores = []
        for code, actual in actual_hours.items():
            if code in predicted_hours:
                predicted = predicted_hours[code]
                error = abs(actual - predicted) / max(actual, 0.1)
                accuracy = max(0, 1 - error)
                accuracy_scores.append(accuracy)
                
        overall_accuracy = np.mean(accuracy_scores) if accuracy_scores else 0
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE analysis_memory
                SET actual_hours = ?, accuracy_score = ?
                WHERE session_id = ? AND part_number = ?
            """, (
                json.dumps(actual_hours),
                overall_accuracy,
                session_id,
                part_number
            ))
            
        # Learn from errors
        if overall_accuracy < 0.8:
            self._learn_from_error(actual_hours, predicted_hours, part_number)
    
    def _learn_from_error(self, actual: Dict, predicted: Dict, context: str):
        """Learn from prediction errors"""
        learnings = []
        
        for code, actual_hrs in actual.items():
            if code in predicted:
                pred_hrs = predicted[code]
                error_pct = (actual_hrs - pred_hrs) / pred_hrs if pred_hrs > 0 else 0
                
                if abs(error_pct) > 0.2:  # Significant error
                    learning = {
                        'concept': f"Code {code} variance",
                        'context': context,
                        'impact': error_pct,
                        'correction_factor': actual_hrs / pred_hrs if pred_hrs > 0 else 1
                    }
                    learnings.append(learning)
                    
        # Store learnings
        with sqlite3.connect(self.db_path) as conn:
            for learning in learnings:
                conn.execute("""
                    INSERT INTO learning_memory
                    (concept, context, impact, examples, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    learning['concept'],
                    learning['context'],
                    learning['impact'],
                    json.dumps(learning),
                    datetime.now()
                ))

class CostDatabase:
    """Centralized cost management"""
    
    def __init__(self, db_path: str = "eagle_costs.db"):
        self.db_path = db_path
        self._init_database()
        
    def _init_database(self):
        """Initialize cost database"""
        with sqlite3.connect(self.db_path) as conn:
            # Labor costs
            conn.execute("""
                CREATE TABLE IF NOT EXISTS labor_costs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT,
                    description TEXT,
                    department TEXT,
                    regular_rate REAL,
                    overtime_rate REAL,
                    burden_rate REAL,  -- Benefits, taxes, etc
                    effective_date DATE,
                    expiry_date DATE,
                    created_at TIMESTAMP
                )
            """)
            
            # Material costs
            conn.execute("""
                CREATE TABLE IF NOT EXISTS material_costs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_code TEXT,
                    description TEXT,
                    vendor TEXT,
                    unit TEXT,
                    cost_per_unit REAL,
                    min_order_qty REAL,
                    lead_time_days INTEGER,
                    effective_date DATE,
                    created_at TIMESTAMP
                )
            """)
            
            # Overhead costs
            conn.execute("""
                CREATE TABLE IF NOT EXISTS overhead_costs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT,  -- rent, utilities, insurance
                    description TEXT,
                    allocation_method TEXT,  -- per_hour, per_sqft, percentage
                    rate REAL,
                    effective_date DATE,
                    created_at TIMESTAMP
                )
            """)
            
            # Equipment costs
            conn.execute("""
                CREATE TABLE IF NOT EXISTS equipment_costs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    equipment_code TEXT,
                    description TEXT,
                    ownership_type TEXT,  -- owned, leased, rented
                    hourly_rate REAL,
                    daily_rate REAL,
                    fuel_per_hour REAL,
                    maintenance_per_hour REAL,
                    created_at TIMESTAMP
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_labor_code ON labor_costs(code)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_material_code ON material_costs(item_code)")
    
    def add_labor_cost(self, code: str, description: str, department: str,
                      regular_rate: float, overtime_multiplier: float = 1.5,
                      burden_rate: float = 0.35):
        """Add or update labor cost"""
        overtime_rate = regular_rate * overtime_multiplier
        
        with sqlite3.connect(self.db_path) as conn:
            # Expire previous rates
            conn.execute("""
                UPDATE labor_costs
                SET expiry_date = DATE('now')
                WHERE code = ? AND expiry_date IS NULL
            """, (code,))
            
            # Insert new rate
            conn.execute("""
                INSERT INTO labor_costs
                (code, description, department, regular_rate, overtime_rate, burden_rate,
                 effective_date, created_at)
                VALUES (?, ?, ?, ?, ?, ?, DATE('now'), ?)
            """, (
                code, description, department, regular_rate, overtime_rate,
                burden_rate, datetime.now()
            ))
    
    def add_material_cost(self, item_code: str, description: str, vendor: str,
                         unit: str, cost_per_unit: float, min_order_qty: float = 1,
                         lead_time_days: int = 1):
        """Add material cost"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO material_costs
                (item_code, description, vendor, unit, cost_per_unit, 
                 min_order_qty, lead_time_days, effective_date, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, DATE('now'), ?)
            """, (
                item_code, description, vendor, unit, cost_per_unit,
                min_order_qty, lead_time_days, datetime.now()
            ))
    
    def get_labor_cost(self, code: str, overtime: bool = False) -> Optional[float]:
        """Get current labor cost"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT regular_rate, overtime_rate, burden_rate
                FROM labor_costs
                WHERE code = ? AND expiry_date IS NULL
                ORDER BY effective_date DESC
                LIMIT 1
            """, (code,))
            
            row = cursor.fetchone()
            if row:
                base_rate = row[1] if overtime else row[0]
                burden = row[2]
                return base_rate * (1 + burden)
                
        return None
    
    def get_material_cost(self, item_code: str, quantity: float = 1) -> Optional[Dict]:
        """Get material cost with quantity pricing"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT cost_per_unit, unit, min_order_qty, lead_time_days
                FROM material_costs
                WHERE item_code = ?
                ORDER BY effective_date DESC
                LIMIT 1
            """, (item_code,))
            
            row = cursor.fetchone()
            if row:
                cost_per_unit, unit, min_qty, lead_time = row
                order_qty = max(quantity, min_qty)
                
                return {
                    'unit_cost': cost_per_unit,
                    'total_cost': cost_per_unit * order_qty,
                    'order_quantity': order_qty,
                    'unit': unit,
                    'lead_time_days': lead_time
                }
                
        return None
    
    def calculate_job_cost(self, labor_hours: Dict, materials: Dict, 
                          overhead_percentage: float = 0.15) -> Dict:
        """Calculate total job cost"""
        costs = {
            'labor': 0,
            'materials': 0,
            'overhead': 0,
            'total': 0,
            'details': {}
        }
        
        # Labor costs
        for code, hours in labor_hours.items():
            is_overtime = code.startswith('9')
            rate = self.get_labor_cost(code[:4], overtime=is_overtime)
            if rate:
                cost = hours * rate
                costs['labor'] += cost
                costs['details'][f'labor_{code}'] = {
                    'hours': hours,
                    'rate': rate,
                    'cost': cost
                }
                
        # Material costs
        for item_code, quantity in materials.items():
            material = self.get_material_cost(item_code, quantity)
            if material:
                costs['materials'] += material['total_cost']
                costs['details'][f'material_{item_code}'] = material
                
        # Overhead
        costs['overhead'] = (costs['labor'] + costs['materials']) * overhead_percentage
        costs['total'] = costs['labor'] + costs['materials'] + costs['overhead']
        
        return costs
    
    def load_standard_costs(self):
        """Load Eagle standard costs"""
        # Labor rates by department
        labor_rates = {
            # Design/Admin
            '0098': {'desc': 'PERMIT SUBMITTED', 'dept': 'ADMIN', 'rate': 45},
            '0110': {'desc': 'SKETCHING', 'dept': 'DESIGN', 'rate': 65},
            
            # Fabrication
            '0200': {'desc': 'FABRICATION LAYOUT', 'dept': 'FAB', 'rate': 55},
            '0230': {'desc': 'CHANNEL LETTERS', 'dept': 'FAB', 'rate': 60},
            
            # Electrical
            '0340': {'desc': 'ELECTRICAL WIRING', 'dept': 'ELEC', 'rate': 75},
            
            # Installation
            '0640': {'desc': '2 MEN & TRUCK INSTALL', 'dept': 'INSTALL', 'rate': 85},
        }
        
        for code, data in labor_rates.items():
            self.add_labor_cost(code, data['desc'], data['dept'], data['rate'])
            
        # Common materials
        materials = [
            ('202-0220', 'ACRYLIC SHEET WHITE', 'GEMINI', 'SF', 12.50),
            ('209-0380', 'ALUMINUM COIL .040', 'METAL SUPPLY', 'LB', 2.85),
            ('216-0100', 'LED MODULE 12V', 'PRINCIPAL', 'EA', 0.85),
        ]
        
        for item in materials:
            self.add_material_cost(*item)

# Integration with main system
class CostAwareAnalyzer:
    """Analyzer with memory and cost integration"""
    
    def __init__(self):
        self.memory = MemoryAgent()
        self.costs = CostDatabase()
        
    def analyze_with_memory_and_cost(self, work_order: Dict) -> Dict:
        """Analyze using memory and calculate costs"""
        
        # Recall similar past jobs
        similar = self.memory.recall_similar(
            work_order['part_number'],
            work_order.get('sign_type')
        )
        
        # Use memory to improve prediction
        if similar:
            # Weight recent similar jobs
            labor_predictions = self._weighted_average_prediction(similar)
        else:
            # Fallback to standard analysis
            labor_predictions = self._standard_prediction(work_order)
            
        # Calculate costs
        material_list = self._estimate_materials(work_order)
        job_cost = self.costs.calculate_job_cost(labor_predictions, material_list)
        
        # Store in memory
        analysis = {
            'session_id': work_order.get('session_id'),
            'part_number': work_order['part_number'],
            'sign_type': work_order.get('sign_type'),
            'predictions': labor_predictions,
            'estimated_cost': job_cost
        }
        
        self.memory.remember_analysis(analysis)
        
        return analysis
    
    def _weighted_average_prediction(self, similar_jobs: List[Dict]) -> Dict:
        """Predict based on similar past jobs"""
        predictions = defaultdict(list)
        weights = []
        
        for job in similar_jobs:
            weight = job.get('historical_accuracy', 0.5)
            weights.append(weight)
            
            for code, hours in job.get('predictions', {}).items():
                predictions[code].append(hours * weight)
                
        # Weighted average
        final_predictions = {}
        total_weight = sum(weights)
        
        for code, weighted_hours in predictions.items():
            final_predictions[code] = sum(weighted_hours) / total_weight
            
        return final_predictions
    
    def _estimate_materials(self, work_order: Dict) -> Dict:
        """Estimate materials based on sign type"""
        # Simple estimation - would be more complex in production
        sqft = work_order.get('total_sqft', 10)
        
        materials = {}
        if work_order.get('sign_type') == 'CLLIT':
            materials['202-0220'] = sqft * 1.1  # 10% waste
            materials['216-0100'] = sqft * 3    # 3 LEDs per sqft
            
        return materials

if __name__ == "__main__":
    # Initialize system
    analyzer = CostAwareAnalyzer()
    
    # Load standard costs
    analyzer.costs.load_standard_costs()
    
    # Example analysis
    work_order = {
        'session_id': 'abc123',
        'part_number': 'CHL-48-RED',
        'sign_type': 'CLLIT',
        'total_sqft': 48
    }
    
    result = analyzer.analyze_with_memory_and_cost(work_order)
    print(f"Estimated cost: ${result['estimated_cost']['total']:.2f}")
