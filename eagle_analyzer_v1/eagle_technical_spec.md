# Eagle Sign Analyzer Technical Specification

**Version:** 1.0  
**Date:** December 2024  
**Classification:** Proprietary & Confidential

## 1. System Architecture

### 1.1 Core Components

- **PDF Processing Engine**: PyPDF2-based extraction with OCR fallback
- **ML Pipeline**: PyTorch neural networks for labor prediction
- **Memory Agent**: SQLite-based learning system
- **Cost Database**: Centralized pricing management
- **GUI Interface**: Tkinter with drag-and-drop support

### 1.2 Technology Stack

- **Language**: Python 3.7+
- **ML Framework**: PyTorch 1.9+
- **Database**: SQLite 3
- **GUI**: Tkinter + tkinterdnd2
- **Dependencies**: pandas, numpy, scipy, openpyxl

### 1.3 System Requirements

- **OS**: Windows 10+, macOS 10.14+, Ubuntu 18.04+
- **RAM**: Minimum 4GB, Recommended 8GB
- **Storage**: 500MB installation + 2GB for data
- **CPU**: 2+ cores recommended
- **GPU**: Optional, CUDA 11.0+ for acceleration

## 2. Data Flow Architecture

```
PDF Input → Extraction → Parsing → Validation → Feature Engineering
    ↓           ↓           ↓          ↓              ↓
  OCR      Context     Business    Memory       ML Models
 Fallback   Analysis    Rules      Recall      Prediction
                                                    ↓
                                             Cost Calculation
                                                    ↓
                                              Final Estimate
```

## 3. Database Schema

### 3.1 Analysis Memory
```sql
CREATE TABLE analysis_memory (
    id INTEGER PRIMARY KEY,
    session_id TEXT,
    part_number TEXT,
    sign_type TEXT,
    analysis_data TEXT,
    predictions TEXT,
    actual_hours TEXT,
    accuracy_score REAL,
    created_at TIMESTAMP
);
```

### 3.2 Cost Database
```sql
CREATE TABLE labor_costs (
    id INTEGER PRIMARY KEY,
    code TEXT,
    description TEXT,
    department TEXT,
    regular_rate REAL,
    overtime_rate REAL,
    burden_rate REAL,
    effective_date DATE
);
```

## 4. API Specifications

### 4.1 Core Analysis API

```python
def analyze_workorder(pdf_path: str) -> Dict:
    """
    Analyze work order and return estimates
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        {
            'success': bool,
            'part_number': str,
            'labor_estimates': {
                'code': {
                    'recommended_hours': float,
                    'confidence_interval': [lower, upper],
                    'confidence_level': str
                }
            },
            'total_cost': float,
            'warnings': List[str]
        }
    """
```

### 4.2 Memory API

```python
def recall_similar(part_number: str, limit: int = 10) -> List[Dict]:
    """Retrieve similar historical analyses"""
    
def update_accuracy(session_id: str, actual_hours: Dict):
    """Update predictions with actual results"""
```

## 5. Machine Learning Models

### 5.1 Labor Prediction Network
- **Architecture**: 3-layer feedforward neural network
- **Input Features**: 18 dimensions (sign type, size, complexity, etc.)
- **Output**: Hours prediction with uncertainty
- **Training**: AdamW optimizer, SmoothL1Loss

### 5.2 Workflow Attention Model
- **Architecture**: Transformer encoder (3 layers, 4 heads)
- **Purpose**: Understand work code sequences
- **Training**: 50 epochs on historical sequences

## 6. Security Considerations

- **Data Encryption**: SQLite databases encrypted at rest
- **Access Control**: File-based permissions
- **Audit Logging**: All analyses logged with timestamps
- **Data Retention**: Configurable retention policies

## 7. Performance Specifications

- **PDF Processing**: 100 pages/minute
- **Analysis Time**: <5 seconds per work order
- **Memory Recall**: <100ms for similar job lookup
- **Concurrent Users**: Single-user desktop application

## 8. Integration Points

- **Input**: PDF files via GUI or command line
- **Output**: Excel, JSON, PDF reports
- **Database**: SQLite files portable between installations
- **APIs**: Future REST API planned for v2.0

## 9. Error Handling

- **PDF Corruption**: Automatic OCR fallback
- **Missing Data**: Statistical imputation
- **Model Failure**: Fallback to historical averages
- **Database Lock**: Retry with exponential backoff

## 10. Scalability Roadmap

- **v1.0**: Desktop single-user
- **v2.0**: Multi-user with central database
- **v3.0**: Cloud-based SaaS platform
- **v4.0**: Mobile applications