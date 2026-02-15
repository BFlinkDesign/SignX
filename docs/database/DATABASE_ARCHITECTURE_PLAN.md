# SignX/APEX Database Architecture Plan

## Executive Summary

This document provides a comprehensive database architecture plan for SignX/APEX - a structural engineering calculation system. It builds upon the existing foundation schema (migration 001_foundation) and extends it with additional reference data, enhanced project tracking, BOM/pricing capabilities, and user management.

---

## 1. Current State Analysis

### 1.1 Existing Tables (Foundation Schema)

The foundation schema (`001_foundation.py`) already provides:

| Category | Tables | Status |
|----------|--------|--------|
| **Projects** | `projects`, `project_payloads`, `project_events` | Complete |
| **AISC Database** | `aisc_shapes_v16` (schema only, ~2500 shapes pending) | Schema Complete |
| **Material Costs** | `material_cost_indices`, `regional_cost_factors`, `material_suppliers` | Complete |
| **Calibration** | `calibration_constants`, `pricing_configs` | Complete |
| **Reference** | `material_catalog`, `code_references` | Partial |
| **Audit/RBAC** | `audit_logs`, `roles`, `permissions`, `user_roles`, `role_permissions` | Complete |
| **Compliance** | `compliance_records`, `pe_stamps` | Complete |
| **Files/CRM** | `file_uploads`, `crm_webhooks` | Complete |
| **Pole Configs** | `single_pole_configs/results`, `double_pole_configs/results` | Complete |
| **Cantilever** | `cantilever_configs`, `cantilever_analysis_results`, `cantilever_sections` | Complete |

### 1.2 Gap Analysis

| Missing Component | Priority | Description |
|-------------------|----------|-------------|
| **AISC Shapes Data** | Critical | Need to seed ~2500 shapes from AISC v16.0 |
| **Wind Speed Maps** | Critical | ASCE 7-22 Figure 26.5-1 digitized by location |
| **Seismic Parameters** | High | Ss, S1, TL values by location (USGS data) |
| **Soil Classifications** | High | Bearing capacities by ASCE 7 site class |
| **Anchor Catalog** | High | Manufacturer anchors (Hilti, Simpson, Powers) |
| **BOM Items** | High | Bill of materials tracking per project |
| **Labor Rates** | Medium | Trade-specific labor rates by region |
| **Supplier Quotes** | Medium | RFQ tracking and quote management |
| **Users/Organizations** | Medium | Supabase integration supplement |
| **Calculation Archive** | High | Long-term storage of all calculation I/O |

---

## 2. Complete Schema Design

### 2.1 Reference Data Tables

#### 2.1.1 Wind Speed Maps (ASCE 7-22)

```sql
-- ASCE 7-22 Basic Wind Speed Data by Location
-- Source: ASCE 7-22 Figure 26.5-1A through 26.5-1D (digitized)
CREATE TABLE wind_speed_maps (
    id SERIAL PRIMARY KEY,

    -- Location (multiple lookup methods)
    latitude DECIMAL(9,6) NOT NULL,
    longitude DECIMAL(10,6) NOT NULL,
    state_code VARCHAR(2),
    county_fips VARCHAR(5),
    zip_code VARCHAR(10),
    city VARCHAR(100),

    -- Risk Category wind speeds (3-second gust, mph)
    -- ASCE 7-22 Figure 26.5-1A/B/C/D
    v_risk_i FLOAT NOT NULL,      -- Risk Category I
    v_risk_ii FLOAT NOT NULL,     -- Risk Category II (standard)
    v_risk_iii FLOAT NOT NULL,    -- Risk Category III
    v_risk_iv FLOAT NOT NULL,     -- Risk Category IV (essential)

    -- Special wind zones
    is_hurricane_prone BOOLEAN DEFAULT false,
    is_special_wind_region BOOLEAN DEFAULT false,
    special_wind_region_name VARCHAR(100),

    -- Exposure defaults based on terrain
    default_exposure_category VARCHAR(1) DEFAULT 'C',
    terrain_roughness_category VARCHAR(10),

    -- Metadata
    asce_version VARCHAR(20) DEFAULT 'ASCE 7-22',
    source VARCHAR(100) DEFAULT 'ASCE Hazard Tool',
    effective_date DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT chk_wind_latitude CHECK (latitude BETWEEN -90 AND 90),
    CONSTRAINT chk_wind_longitude CHECK (longitude BETWEEN -180 AND 180),
    CONSTRAINT chk_wind_speeds CHECK (
        v_risk_i >= 85 AND v_risk_i <= 200 AND
        v_risk_ii >= 85 AND v_risk_ii <= 200 AND
        v_risk_iii >= 85 AND v_risk_iii <= 200 AND
        v_risk_iv >= 85 AND v_risk_iv <= 200
    )
);

-- Spatial index for lat/long lookups
CREATE INDEX ix_wind_speed_location ON wind_speed_maps USING GIST (
    point(longitude, latitude)
);
CREATE INDEX ix_wind_speed_state ON wind_speed_maps(state_code);
CREATE INDEX ix_wind_speed_zip ON wind_speed_maps(zip_code);
CREATE INDEX ix_wind_speed_county ON wind_speed_maps(county_fips);
```

#### 2.1.2 Seismic Parameters (USGS)

```sql
-- Seismic Design Parameters per ASCE 7-22 / IBC 2024
-- Source: USGS Seismic Design Maps (https://earthquake.usgs.gov/ws/designmaps/)
CREATE TABLE seismic_parameters (
    id SERIAL PRIMARY KEY,

    -- Location
    latitude DECIMAL(9,6) NOT NULL,
    longitude DECIMAL(10,6) NOT NULL,
    state_code VARCHAR(2),
    zip_code VARCHAR(10),

    -- MCE_R Ground Motion (Maximum Considered Earthquake)
    ss FLOAT NOT NULL,      -- Spectral acceleration at 0.2 sec (g)
    s1 FLOAT NOT NULL,      -- Spectral acceleration at 1.0 sec (g)

    -- Site Class D defaults (can be modified by geotechnical report)
    sms FLOAT,              -- Site-modified Ss
    sm1 FLOAT,              -- Site-modified S1
    sds FLOAT,              -- Design spectral acceleration at 0.2 sec
    sd1 FLOAT,              -- Design spectral acceleration at 1.0 sec

    -- Long-period transition period
    tl FLOAT,               -- Long-period transition period (sec)

    -- Seismic Design Category
    sdc_risk_ii VARCHAR(1),     -- SDC for Risk Category II
    sdc_risk_iii VARCHAR(1),    -- SDC for Risk Category III
    sdc_risk_iv VARCHAR(1),     -- SDC for Risk Category IV

    -- Reference document info
    reference_document VARCHAR(50) DEFAULT 'ASCE 7-22',
    usgs_edition VARCHAR(20) DEFAULT '2024',
    site_class VARCHAR(1) DEFAULT 'D',

    -- Metadata
    data_source VARCHAR(100) DEFAULT 'USGS',
    effective_date DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT chk_seismic_ss CHECK (ss >= 0 AND ss <= 4.0),
    CONSTRAINT chk_seismic_s1 CHECK (s1 >= 0 AND s1 <= 2.0),
    CONSTRAINT chk_seismic_sdc CHECK (sdc_risk_ii IN ('A', 'B', 'C', 'D', 'E', 'F'))
);

CREATE INDEX ix_seismic_location ON seismic_parameters USING GIST (
    point(longitude, latitude)
);
CREATE INDEX ix_seismic_state ON seismic_parameters(state_code);
CREATE INDEX ix_seismic_zip ON seismic_parameters(zip_code);
```

#### 2.1.3 Soil Classifications

```sql
-- Soil Classifications per ASCE 7-22 Table 20.3-1 and IBC 2024
CREATE TABLE soil_classifications (
    id SERIAL PRIMARY KEY,

    -- Site class per ASCE 7-22
    site_class VARCHAR(2) NOT NULL,  -- A, B, C, D, E, F
    site_class_name VARCHAR(100) NOT NULL,
    description TEXT,

    -- Soil properties
    shear_wave_velocity_avg_fps_min FLOAT,  -- vs,avg minimum
    shear_wave_velocity_avg_fps_max FLOAT,  -- vs,avg maximum
    spt_n_value_min INTEGER,                -- Standard penetration test N-value min
    spt_n_value_max INTEGER,                -- N-value max
    undrained_shear_strength_psf_min FLOAT, -- su minimum
    undrained_shear_strength_psf_max FLOAT, -- su maximum

    -- Presumptive bearing capacities (IBC Table 1806.2)
    bearing_capacity_psf FLOAT,              -- Allowable bearing pressure
    lateral_bearing_capacity_psf_per_ft FLOAT, -- Lateral bearing per foot of depth
    lateral_sliding_coefficient FLOAT,       -- Coefficient of friction

    -- Site coefficients for seismic (ASCE 7-22 Tables 11.4-1 and 11.4-2)
    fa_default FLOAT,  -- Short-period site coefficient
    fv_default FLOAT,  -- Long-period site coefficient

    -- Common soil descriptions
    typical_soils TEXT[],

    -- Design considerations
    requires_site_specific_analysis BOOLEAN DEFAULT false,
    susceptible_to_liquefaction BOOLEAN DEFAULT false,

    -- Metadata
    code_reference VARCHAR(50) DEFAULT 'ASCE 7-22 / IBC 2024',
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT uq_soil_site_class UNIQUE (site_class)
);

-- Extended soil profiles for project-specific geotechnical data
CREATE TABLE soil_profiles (
    id SERIAL PRIMARY KEY,
    project_id VARCHAR(255) REFERENCES projects(project_id) ON DELETE CASCADE,

    -- Profile identification
    boring_id VARCHAR(50),
    location_description TEXT,
    latitude DECIMAL(9,6),
    longitude DECIMAL(10,6),
    ground_elevation_ft FLOAT,
    groundwater_depth_ft FLOAT,

    -- Determined site class
    site_class VARCHAR(2) REFERENCES soil_classifications(site_class),

    -- Bearing capacity from geotech report
    allowable_bearing_capacity_psf FLOAT,
    ultimate_bearing_capacity_psf FLOAT,
    lateral_earth_pressure_coefficient FLOAT,

    -- Soil layers (JSONB for flexibility)
    layers JSONB NOT NULL DEFAULT '[]',
    /*
    Example layers format:
    [
        {
            "depth_top_ft": 0,
            "depth_bottom_ft": 5,
            "soil_type": "Sandy clay",
            "uscs_classification": "SC",
            "unit_weight_pcf": 115,
            "cohesion_psf": 200,
            "friction_angle_deg": 28,
            "spt_n_value": 12
        }
    ]
    */

    -- Report reference
    geotech_report_ref VARCHAR(255),
    report_date DATE,
    pe_stamp_id INTEGER,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(255)
);

CREATE INDEX ix_soil_profiles_project ON soil_profiles(project_id);
```

#### 2.1.4 Anchor Catalog

```sql
-- Anchor Bolt Catalog (Hilti, Simpson, Powers, ITW Red Head, etc.)
CREATE TYPE anchor_type AS ENUM (
    'expansion_wedge',      -- Wedge anchors
    'expansion_sleeve',     -- Sleeve anchors
    'undercut',             -- Undercut anchors (Hilti HDA)
    'adhesive_threaded',    -- Adhesive with threaded rod
    'adhesive_rebar',       -- Adhesive with rebar
    'cast_in_place',        -- J-bolt, L-bolt, headed studs
    'screw_in',             -- Concrete screws (Tapcon, Titen)
    'drop_in',              -- Drop-in anchors
    'hammer_drive'          -- Hammer-drive pins
);

CREATE TYPE anchor_load_type AS ENUM (
    'tension', 'shear', 'combined'
);

CREATE TABLE anchor_catalog (
    id SERIAL PRIMARY KEY,

    -- Identification
    manufacturer VARCHAR(100) NOT NULL,
    product_name VARCHAR(200) NOT NULL,
    product_code VARCHAR(100) NOT NULL,
    anchor_type anchor_type NOT NULL,

    -- Dimensions
    diameter_in FLOAT NOT NULL,           -- Nominal diameter
    length_in FLOAT NOT NULL,             -- Overall length
    thread_length_in FLOAT,               -- Thread engagement
    embedment_depth_in FLOAT NOT NULL,    -- Effective embedment

    -- Material
    material VARCHAR(100),                -- Carbon steel, stainless 304, 316, etc.
    coating VARCHAR(100),                 -- Zinc plated, HDG, mechanically galvanized
    grade VARCHAR(50),                    -- Grade 5, Grade 8, etc.
    tensile_strength_psi INTEGER,
    yield_strength_psi INTEGER,

    -- Concrete requirements
    min_concrete_strength_psi INTEGER DEFAULT 2500,
    max_concrete_strength_psi INTEGER DEFAULT 8000,
    min_edge_distance_in FLOAT,
    min_spacing_in FLOAT,
    min_member_thickness_in FLOAT,

    -- Design capacities (ACI 318 / ICC-ES)
    -- All values in lbs, for f'c = 4000 psi, uncracked concrete
    allowable_tension_lbs FLOAT,          -- ASD tension capacity
    allowable_shear_lbs FLOAT,            -- ASD shear capacity
    ultimate_tension_lbs FLOAT,           -- LRFD tension capacity
    ultimate_shear_lbs FLOAT,             -- LRFD shear capacity

    -- Reduction factors
    cracked_concrete_factor FLOAT DEFAULT 0.75,
    seismic_factor FLOAT DEFAULT 0.75,
    overhead_factor FLOAT DEFAULT 0.85,

    -- Code compliance
    icc_es_report VARCHAR(50),            -- ESR number
    ul_listed BOOLEAN DEFAULT false,
    aci_318_compliant BOOLEAN DEFAULT true,
    ada_compliant BOOLEAN DEFAULT false,

    -- Installation
    drill_bit_diameter_in FLOAT,
    hole_depth_in FLOAT,
    installation_torque_ftlbs FLOAT,

    -- Pricing (optional)
    unit_price_usd DECIMAL(10,4),
    pack_quantity INTEGER,

    -- Metadata
    data_sheet_url TEXT,
    technical_manual_url TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT uq_anchor_product UNIQUE (manufacturer, product_code)
);

CREATE INDEX ix_anchor_type ON anchor_catalog(anchor_type);
CREATE INDEX ix_anchor_manufacturer ON anchor_catalog(manufacturer);
CREATE INDEX ix_anchor_diameter ON anchor_catalog(diameter_in);
CREATE INDEX ix_anchor_capacity ON anchor_catalog(allowable_tension_lbs, allowable_shear_lbs);

-- Anchor capacity adjustment factors by condition
CREATE TABLE anchor_adjustment_factors (
    id SERIAL PRIMARY KEY,
    condition_name VARCHAR(100) NOT NULL,
    condition_code VARCHAR(50) NOT NULL,
    description TEXT,

    tension_factor FLOAT NOT NULL DEFAULT 1.0,
    shear_factor FLOAT NOT NULL DEFAULT 1.0,

    applies_to_types anchor_type[],

    code_reference VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT uq_anchor_condition UNIQUE (condition_code)
);
```

### 2.2 Project & Calculation Tables

#### 2.2.1 Calculation Archive (Immutable Storage)

```sql
-- Immutable calculation archive for PE compliance
-- Every calculation is stored with full I/O for reproducibility
CREATE TABLE calculation_archive (
    id SERIAL PRIMARY KEY,
    calculation_id VARCHAR(255) NOT NULL UNIQUE,
    project_id VARCHAR(255) REFERENCES projects(project_id) ON DELETE SET NULL,

    -- Calculation identification
    calculation_type VARCHAR(100) NOT NULL,  -- 'wind_load', 'foundation', 'pole_stress', etc.
    module VARCHAR(100) NOT NULL,            -- 'single_pole', 'double_pole', 'cantilever'
    version VARCHAR(50) NOT NULL,            -- Calculation engine version

    -- Full input/output capture (JSONB for flexibility)
    inputs JSONB NOT NULL,
    outputs JSONB NOT NULL,
    intermediates JSONB,

    -- Deterministic verification
    content_sha256 VARCHAR(64) NOT NULL,     -- SHA256 of canonical JSON(inputs + outputs)
    inputs_sha256 VARCHAR(64) NOT NULL,      -- SHA256 of inputs only (for cache lookup)

    -- Code references used
    code_references JSONB NOT NULL DEFAULT '[]',
    /*
    Example:
    [
        {"code": "ASCE 7-22", "section": "26.10.1", "description": "Velocity pressure"},
        {"code": "AISC 360-22", "section": "F2.1", "description": "Flexural strength"}
    ]
    */

    -- Assumptions and warnings
    assumptions TEXT[] NOT NULL DEFAULT '{}',
    warnings TEXT[] NOT NULL DEFAULT '{}',

    -- Confidence and status
    confidence FLOAT NOT NULL,
    passes_all_checks BOOLEAN NOT NULL,
    critical_check VARCHAR(100),             -- Name of controlling check

    -- User and audit
    created_by VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,

    -- Immutability enforcement
    CONSTRAINT chk_calc_confidence CHECK (confidence >= 0 AND confidence <= 1)
);

-- Prevent updates/deletes (append-only)
CREATE OR REPLACE FUNCTION prevent_calculation_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Calculation archive is immutable. Cannot modify or delete records.';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_calculation_archive_immutable
BEFORE UPDATE OR DELETE ON calculation_archive
FOR EACH ROW EXECUTE FUNCTION prevent_calculation_modification();

-- Indexes for common queries
CREATE INDEX ix_calc_archive_project ON calculation_archive(project_id);
CREATE INDEX ix_calc_archive_type ON calculation_archive(calculation_type);
CREATE INDEX ix_calc_archive_module ON calculation_archive(module);
CREATE INDEX ix_calc_archive_sha256 ON calculation_archive(content_sha256);
CREATE INDEX ix_calc_archive_inputs_sha ON calculation_archive(inputs_sha256);
CREATE INDEX ix_calc_archive_created ON calculation_archive(created_at DESC);
CREATE INDEX ix_calc_archive_confidence ON calculation_archive(confidence) WHERE confidence < 0.9;

-- GIN index for JSONB queries
CREATE INDEX ix_calc_archive_inputs ON calculation_archive USING GIN (inputs);
CREATE INDEX ix_calc_archive_outputs ON calculation_archive USING GIN (outputs);
```

#### 2.2.2 Calculation Inputs Table (Structured)

```sql
-- Structured calculation inputs for common engineering parameters
CREATE TABLE calculation_inputs (
    id SERIAL PRIMARY KEY,
    project_id VARCHAR(255) NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    config_type VARCHAR(50) NOT NULL,  -- 'single_pole', 'double_pole', 'cantilever'
    config_id VARCHAR(255),            -- FK to respective config table

    -- Site/Environmental Parameters
    site_location JSONB NOT NULL,
    /*
    {
        "latitude": 29.7604,
        "longitude": -95.3698,
        "elevation_ft": 50,
        "city": "Houston",
        "state": "TX",
        "zip": "77001"
    }
    */

    -- Wind parameters
    basic_wind_speed_mph FLOAT NOT NULL,
    risk_category VARCHAR(3) NOT NULL DEFAULT 'II',
    exposure_category VARCHAR(1) NOT NULL DEFAULT 'C',
    topographic_factor_kzt FLOAT DEFAULT 1.0,
    wind_directionality_kd FLOAT DEFAULT 0.85,
    elevation_factor_ke FLOAT DEFAULT 1.0,

    -- Seismic parameters
    ss FLOAT,
    s1 FLOAT,
    site_class VARCHAR(2) DEFAULT 'D',
    seismic_design_category VARCHAR(1),

    -- Soil parameters
    soil_bearing_capacity_psf FLOAT DEFAULT 2000,
    soil_friction_angle_deg FLOAT,
    soil_cohesion_psf FLOAT,
    groundwater_depth_ft FLOAT,

    -- Snow/Ice loads
    ground_snow_load_psf FLOAT DEFAULT 0,
    ice_thickness_in FLOAT DEFAULT 0,

    -- Source tracking
    wind_speed_source VARCHAR(100),  -- 'ASCE Hazard Tool', 'Manual Entry'
    seismic_source VARCHAR(100),     -- 'USGS', 'Manual Entry'
    soil_source VARCHAR(100),        -- 'Geotech Report', 'Presumptive'

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(255),

    CONSTRAINT uq_calc_inputs_config UNIQUE (project_id, config_type, config_id)
);

CREATE INDEX ix_calc_inputs_project ON calculation_inputs(project_id);
CREATE INDEX ix_calc_inputs_type ON calculation_inputs(config_type);
```

### 2.3 BOM & Pricing Tables

#### 2.3.1 Bill of Materials

```sql
-- Bill of Materials items per project
CREATE TABLE bom_items (
    id SERIAL PRIMARY KEY,
    project_id VARCHAR(255) NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,

    -- BOM categorization
    category VARCHAR(100) NOT NULL,  -- 'structural', 'foundation', 'hardware', 'finish', 'electrical'
    subcategory VARCHAR(100),

    -- Item identification
    item_code VARCHAR(100),          -- Internal item code
    manufacturer VARCHAR(200),
    part_number VARCHAR(100),
    description TEXT NOT NULL,

    -- Quantities
    quantity DECIMAL(12,4) NOT NULL,
    unit VARCHAR(50) NOT NULL,       -- 'ea', 'lf', 'sf', 'cy', 'lbs', 'gal'

    -- Dimensions (for structural items)
    length_ft FLOAT,
    width_ft FLOAT,
    weight_lbs FLOAT,

    -- Pricing
    unit_cost DECIMAL(12,4),
    extended_cost DECIMAL(14,2) GENERATED ALWAYS AS (quantity * unit_cost) STORED,
    markup_pct DECIMAL(5,2) DEFAULT 0,
    sell_price DECIMAL(14,2),

    -- Source/reference
    material_cost_index_id INTEGER REFERENCES material_cost_indices(id),
    aisc_shape_id INTEGER,           -- FK to aisc_shapes_v16 if applicable
    anchor_id INTEGER REFERENCES anchor_catalog(id),

    -- Status
    status VARCHAR(50) DEFAULT 'estimated',  -- 'estimated', 'quoted', 'ordered', 'received'
    supplier_id INTEGER REFERENCES material_suppliers(id),
    quote_id INTEGER,                -- FK to supplier_quotes

    -- Calculation reference
    calculation_id VARCHAR(255),     -- Link to calculation that generated this item

    -- Metadata
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(255)
);

CREATE INDEX ix_bom_project ON bom_items(project_id);
CREATE INDEX ix_bom_category ON bom_items(category);
CREATE INDEX ix_bom_status ON bom_items(status);
```

#### 2.3.2 Labor Rates

```sql
-- Labor rates by trade and region
CREATE TABLE labor_rates (
    id SERIAL PRIMARY KEY,

    -- Trade identification
    trade_code VARCHAR(50) NOT NULL,
    trade_name VARCHAR(200) NOT NULL,
    /*
    Common trades:
    - 'IRONWORKER_STRUCT' - Structural ironworker
    - 'WELDER_CERT' - Certified welder
    - 'ELECTRICIAN_JW' - Electrician journeyman
    - 'CRANE_OP' - Crane operator
    - 'LABORER_GEN' - General laborer
    - 'CONCRETE_FIN' - Concrete finisher
    - 'EQUIPMENT_OP' - Equipment operator
    */

    -- Rate components (hourly)
    base_wage_hr DECIMAL(10,2) NOT NULL,
    fringe_benefits_hr DECIMAL(10,2) DEFAULT 0,
    payroll_burden_pct DECIMAL(5,2) DEFAULT 35.0,  -- FICA, WC, insurance, etc.
    total_hourly_cost DECIMAL(10,2) GENERATED ALWAYS AS (
        base_wage_hr + fringe_benefits_hr + (base_wage_hr * payroll_burden_pct / 100)
    ) STORED,

    -- Billing rate (with overhead and profit)
    overhead_pct DECIMAL(5,2) DEFAULT 15.0,
    profit_pct DECIMAL(5,2) DEFAULT 10.0,
    billing_rate_hr DECIMAL(10,2),

    -- Overtime and premium rates
    ot_multiplier DECIMAL(4,2) DEFAULT 1.5,
    dt_multiplier DECIMAL(4,2) DEFAULT 2.0,   -- Double time
    shift_differential_pct DECIMAL(5,2) DEFAULT 0,

    -- Regional application
    state VARCHAR(2),
    city VARCHAR(100),
    region VARCHAR(100),
    is_prevailing_wage BOOLEAN DEFAULT false,
    davis_bacon_class VARCHAR(50),

    -- Effective dates
    effective_from DATE NOT NULL,
    effective_to DATE,

    -- Source
    source VARCHAR(100),  -- 'RS Means', 'BLS', 'Union Scale', 'Company'
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT uq_labor_trade_region_date UNIQUE (trade_code, state, city, effective_from)
);

CREATE INDEX ix_labor_trade ON labor_rates(trade_code);
CREATE INDEX ix_labor_region ON labor_rates(state, city);
CREATE INDEX ix_labor_effective ON labor_rates(effective_from, effective_to);
```

#### 2.3.3 Supplier Quotes

```sql
-- Supplier quote tracking
CREATE TABLE supplier_quotes (
    id SERIAL PRIMARY KEY,
    project_id VARCHAR(255) REFERENCES projects(project_id) ON DELETE SET NULL,

    -- Quote identification
    quote_number VARCHAR(100) NOT NULL,
    supplier_id INTEGER REFERENCES material_suppliers(id),
    supplier_name VARCHAR(200),

    -- Quote details
    quote_date DATE NOT NULL,
    valid_until DATE,
    status VARCHAR(50) DEFAULT 'pending',  -- 'pending', 'accepted', 'rejected', 'expired'

    -- Totals
    subtotal DECIMAL(14,2),
    tax_pct DECIMAL(5,2) DEFAULT 0,
    tax_amount DECIMAL(14,2),
    shipping DECIMAL(10,2) DEFAULT 0,
    total DECIMAL(14,2),

    -- Terms
    payment_terms VARCHAR(100),      -- 'Net 30', '2/10 Net 30', etc.
    lead_time_days INTEGER,
    fob_point VARCHAR(100),          -- 'Origin', 'Destination', etc.
    freight_terms VARCHAR(100),

    -- Quote document
    document_key VARCHAR(500),       -- MinIO/S3 key

    -- Line items stored as JSONB for flexibility
    line_items JSONB NOT NULL DEFAULT '[]',
    /*
    [
        {
            "item": "HSS8x8x1/2",
            "description": "Square HSS A500 Grade B",
            "quantity": 120,
            "unit": "LF",
            "unit_price": 45.50,
            "extended": 5460.00
        }
    ]
    */

    -- Metadata
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(255)
);

CREATE INDEX ix_quotes_project ON supplier_quotes(project_id);
CREATE INDEX ix_quotes_supplier ON supplier_quotes(supplier_id);
CREATE INDEX ix_quotes_status ON supplier_quotes(status);
CREATE INDEX ix_quotes_date ON supplier_quotes(quote_date DESC);
```

### 2.4 User & Organization Tables

Note: Primary user authentication is handled by Supabase. These tables supplement with app-specific data.

```sql
-- User profiles (supplements Supabase auth.users)
CREATE TABLE user_profiles (
    user_id VARCHAR(255) PRIMARY KEY,  -- Matches Supabase user ID

    -- Display info
    display_name VARCHAR(200),
    email VARCHAR(255),
    phone VARCHAR(50),
    avatar_url TEXT,

    -- Professional credentials
    title VARCHAR(100),                -- 'PE', 'SE', 'EIT', etc.
    pe_license_number VARCHAR(100),
    pe_license_state VARCHAR(2),
    pe_license_expiry DATE,
    pe_seal_image_key VARCHAR(500),    -- MinIO key for PE seal image

    -- Preferences
    preferences JSONB DEFAULT '{}',
    /*
    {
        "default_units": "imperial",
        "default_code": "ASCE7-22",
        "notification_email": true,
        "notification_sms": false,
        "theme": "light"
    }
    */

    -- Status
    is_active BOOLEAN DEFAULT true,
    last_login_at TIMESTAMPTZ,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Organizations (multi-tenant support)
CREATE TABLE organizations (
    org_id VARCHAR(255) PRIMARY KEY,

    -- Organization info
    name VARCHAR(255) NOT NULL,
    legal_name VARCHAR(255),
    dba_name VARCHAR(255),

    -- Contact
    address_line1 VARCHAR(255),
    address_line2 VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(2),
    zip_code VARCHAR(20),
    country VARCHAR(2) DEFAULT 'US',
    phone VARCHAR(50),
    email VARCHAR(255),
    website VARCHAR(255),

    -- Business info
    tax_id VARCHAR(50),               -- EIN
    license_number VARCHAR(100),

    -- Branding
    logo_url TEXT,
    primary_color VARCHAR(7),         -- Hex color

    -- Subscription/billing
    subscription_tier VARCHAR(50) DEFAULT 'starter',  -- 'starter', 'professional', 'enterprise'
    billing_email VARCHAR(255),
    stripe_customer_id VARCHAR(100),

    -- Limits (based on tier)
    max_projects INTEGER DEFAULT 10,
    max_users INTEGER DEFAULT 3,
    max_storage_gb INTEGER DEFAULT 5,

    -- Status
    is_active BOOLEAN DEFAULT true,
    trial_ends_at TIMESTAMPTZ,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(255)
);

-- Organization membership
CREATE TABLE organization_members (
    id SERIAL PRIMARY KEY,
    org_id VARCHAR(255) NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
    user_id VARCHAR(255) NOT NULL REFERENCES user_profiles(user_id) ON DELETE CASCADE,

    -- Role within organization
    role VARCHAR(50) NOT NULL DEFAULT 'member',  -- 'owner', 'admin', 'member', 'viewer'

    -- Permissions override (JSONB for flexibility)
    custom_permissions JSONB,

    -- Status
    is_active BOOLEAN DEFAULT true,
    invited_at TIMESTAMPTZ,
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    invited_by VARCHAR(255),

    CONSTRAINT uq_org_member UNIQUE (org_id, user_id)
);

CREATE INDEX ix_org_members_org ON organization_members(org_id);
CREATE INDEX ix_org_members_user ON organization_members(user_id);
```

---

## 3. Alembic Migration Sequence

### 3.1 Migration Order

```
013_add_wind_seismic_soil_tables.py     -- Environmental reference data
014_add_anchor_catalog.py               -- Anchor bolt database
015_add_calculation_archive.py          -- Immutable calculation storage
016_add_bom_pricing_tables.py           -- BOM, labor rates, quotes
017_add_user_organization_tables.py     -- User profiles and orgs
018_seed_reference_data.py              -- Seed data scripts
```

### 3.2 Complete Migration Code

See separate migration files in `/services/api/alembic/versions/`

---

## 4. Data Sources

### 4.1 AISC Shapes Database v16.0

| Source | Method | Notes |
|--------|--------|-------|
| AISC Steel Construction Manual v16 | CSV/Excel import | ~2,500 shapes |
| AISC Shapes Database v16.0 | Direct download | aisc.org/shapes |

**Seeding Script Location:** `/services/api/scripts/seed_aisc_shapes.py`

### 4.2 Wind Speed Data (ASCE 7-22)

| Source | Method | Coverage |
|--------|--------|----------|
| ASCE Hazard Tool | API/Web scraping | All US locations |
| ATC Hazards by Location | Backup source | US cities |

**API:** `https://asce7hazardtool.online/`

### 4.3 Seismic Parameters

| Source | Method | Notes |
|--------|--------|-------|
| USGS Seismic Design Maps | REST API | Official source |
| ASCE 7 Hazard Tool | Backup | Same data |

**API:** `https://earthquake.usgs.gov/ws/designmaps/asce7-22.json?latitude=LAT&longitude=LNG`

### 4.4 Anchor Catalogs

| Manufacturer | Source | Update Frequency |
|--------------|--------|------------------|
| Hilti | Technical data sheets | Annual |
| Simpson Strong-Tie | Technical catalog | Annual |
| Powers Fasteners | Product guide | Annual |
| ITW Red Head | ICC-ES reports | As updated |

### 4.5 Labor Rates

| Source | Method | Notes |
|--------|--------|-------|
| RS Means | Licensed data | Quarterly updates |
| BLS (Bureau of Labor Statistics) | Public API | Annual |
| Davis-Bacon Wage Determinations | SAM.gov | Project-specific |

---

## 5. Query Patterns

### 5.1 Wind Speed Lookup by Location

```sql
-- Get wind speed for a location using nearest neighbor
CREATE OR REPLACE FUNCTION get_wind_speed(
    p_latitude FLOAT,
    p_longitude FLOAT,
    p_risk_category VARCHAR DEFAULT 'II'
)
RETURNS TABLE (
    wind_speed_mph FLOAT,
    exposure_default VARCHAR,
    distance_miles FLOAT,
    source_city VARCHAR
)
LANGUAGE SQL
STABLE
AS $$
    SELECT
        CASE p_risk_category
            WHEN 'I' THEN v_risk_i
            WHEN 'II' THEN v_risk_ii
            WHEN 'III' THEN v_risk_iii
            WHEN 'IV' THEN v_risk_iv
            ELSE v_risk_ii
        END as wind_speed_mph,
        default_exposure_category,
        (point(p_longitude, p_latitude) <-> point(longitude, latitude)) * 69.0 as distance_miles,
        city
    FROM wind_speed_maps
    ORDER BY point(p_longitude, p_latitude) <-> point(longitude, latitude)
    LIMIT 1;
$$;

-- Usage:
SELECT * FROM get_wind_speed(29.7604, -95.3698, 'II');
```

### 5.2 Section Lookup by Required Capacity

```sql
-- Find optimal pole section for given moment demand
CREATE OR REPLACE FUNCTION find_optimal_section(
    p_required_moment_kipft FLOAT,
    p_max_height_ft FLOAT,
    p_shape_types VARCHAR[] DEFAULT ARRAY['HSS', 'PIPE']
)
RETURNS TABLE (
    designation VARCHAR,
    shape_type VARCHAR,
    weight_plf FLOAT,
    sx_in3 FLOAT,
    moment_capacity_kipft FLOAT,
    stress_ratio FLOAT,
    max_slenderness_height_ft FLOAT,
    status VARCHAR
)
LANGUAGE SQL
STABLE
AS $$
    WITH candidates AS (
        SELECT
            aisc_manual_label as designation,
            type as shape_type,
            w as weight_plf,
            sx as sx_in3,
            (sx * 50 * 0.9) / 12.0 as moment_capacity_kipft,  -- phi*Mn
            p_required_moment_kipft / ((sx * 50 * 0.9) / 12.0) as stress_ratio,
            (rx * 200) / 12.0 as max_slenderness_height_ft
        FROM aisc_shapes_v16
        WHERE type = ANY(p_shape_types)
            AND is_available = true
            AND sx >= (p_required_moment_kipft * 12) / (50 * 0.9) * 0.8  -- 80% of required
    )
    SELECT
        designation,
        shape_type,
        weight_plf,
        sx_in3,
        moment_capacity_kipft,
        stress_ratio,
        max_slenderness_height_ft,
        CASE
            WHEN stress_ratio > 1.0 THEN 'OVERSTRESSED'
            WHEN max_slenderness_height_ft < p_max_height_ft THEN 'TOO_SLENDER'
            WHEN stress_ratio > 0.9 THEN 'HIGH_STRESS'
            ELSE 'OK'
        END as status
    FROM candidates
    WHERE stress_ratio <= 1.0
        AND max_slenderness_height_ft >= p_max_height_ft
    ORDER BY weight_plf ASC
    LIMIT 10;
$$;

-- Usage:
SELECT * FROM find_optimal_section(15.5, 25.0, ARRAY['HSS', 'PIPE']);
```

### 5.3 Project Search with Filters

```sql
-- Efficient project search with multiple filters
CREATE OR REPLACE FUNCTION search_projects(
    p_account_id VARCHAR,
    p_status VARCHAR[] DEFAULT NULL,
    p_date_from DATE DEFAULT NULL,
    p_date_to DATE DEFAULT NULL,
    p_search_term VARCHAR DEFAULT NULL,
    p_limit INTEGER DEFAULT 50,
    p_offset INTEGER DEFAULT 0
)
RETURNS TABLE (
    project_id VARCHAR,
    name VARCHAR,
    customer VARCHAR,
    status VARCHAR,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    config_summary JSONB
)
LANGUAGE SQL
STABLE
AS $$
    SELECT
        p.project_id,
        p.name,
        p.customer,
        p.status,
        p.created_at,
        p.updated_at,
        jsonb_build_object(
            'has_single_pole', p.has_single_pole,
            'has_double_pole', p.has_double_pole,
            'has_cantilever', p.has_cantilever
        ) as config_summary
    FROM projects p
    WHERE p.account_id = p_account_id
        AND (p_status IS NULL OR p.status = ANY(p_status))
        AND (p_date_from IS NULL OR p.created_at >= p_date_from)
        AND (p_date_to IS NULL OR p.created_at <= p_date_to)
        AND (p_search_term IS NULL OR
             p.name ILIKE '%' || p_search_term || '%' OR
             p.customer ILIKE '%' || p_search_term || '%' OR
             p.site_name ILIKE '%' || p_search_term || '%')
    ORDER BY p.updated_at DESC
    LIMIT p_limit
    OFFSET p_offset;
$$;
```

### 5.4 Audit Log Query

```sql
-- Get audit trail for a project
SELECT
    al.timestamp,
    al.action,
    al.user_id,
    al.resource_type,
    al.before_state,
    al.after_state,
    al.ip_address
FROM audit_logs al
WHERE al.resource_type = 'project'
    AND al.resource_id = 'proj_123'
ORDER BY al.timestamp DESC
LIMIT 100;

-- Get all actions by a user in last 30 days
SELECT
    DATE_TRUNC('day', timestamp) as day,
    action,
    COUNT(*) as action_count
FROM audit_logs
WHERE user_id = 'user_456'
    AND timestamp >= NOW() - INTERVAL '30 days'
GROUP BY DATE_TRUNC('day', timestamp), action
ORDER BY day DESC, action_count DESC;
```

---

## 6. Performance Optimization

### 6.1 Indexing Strategy

```sql
-- Composite indexes for common query patterns
CREATE INDEX CONCURRENTLY ix_projects_account_status_date
ON projects(account_id, status, created_at DESC);

CREATE INDEX CONCURRENTLY ix_calc_archive_project_type_date
ON calculation_archive(project_id, calculation_type, created_at DESC);

CREATE INDEX CONCURRENTLY ix_bom_project_category
ON bom_items(project_id, category);

-- Partial indexes for active records
CREATE INDEX CONCURRENTLY ix_projects_active
ON projects(account_id, updated_at DESC)
WHERE status IN ('draft', 'estimating');

CREATE INDEX CONCURRENTLY ix_quotes_pending
ON supplier_quotes(project_id, quote_date DESC)
WHERE status = 'pending';

-- GIN indexes for JSONB search
CREATE INDEX CONCURRENTLY ix_calc_inputs_gin
ON calculation_inputs USING GIN (site_location);

CREATE INDEX CONCURRENTLY ix_bom_items_calc_ref
ON bom_items(calculation_id) WHERE calculation_id IS NOT NULL;
```

### 6.2 Materialized Views

```sql
-- Project summary statistics (refresh hourly)
CREATE MATERIALIZED VIEW project_summary_stats AS
SELECT
    account_id,
    DATE_TRUNC('month', created_at) as month,
    status,
    COUNT(*) as project_count,
    AVG(confidence) as avg_confidence
FROM projects
GROUP BY account_id, DATE_TRUNC('month', created_at), status
WITH DATA;

CREATE UNIQUE INDEX ix_project_summary_unique
ON project_summary_stats(account_id, month, status);

-- Refresh command (run via cron/scheduler)
-- REFRESH MATERIALIZED VIEW CONCURRENTLY project_summary_stats;

-- Popular sections by usage
CREATE MATERIALIZED VIEW popular_sections AS
SELECT
    s.aisc_manual_label as designation,
    s.type,
    s.w as weight_plf,
    COUNT(DISTINCT sp.project_id) as usage_count,
    AVG(spr.combined_stress_ratio) as avg_stress_ratio
FROM aisc_shapes_v16 s
LEFT JOIN single_pole_configs sp ON s.aisc_manual_label = sp.pole_section
LEFT JOIN single_pole_results spr ON sp.id = spr.config_id
WHERE s.type IN ('HSS', 'PIPE')
GROUP BY s.aisc_manual_label, s.type, s.w
ORDER BY usage_count DESC
WITH DATA;

CREATE UNIQUE INDEX ix_popular_sections_unique ON popular_sections(designation);
```

### 6.3 Connection Pooling Configuration

```yaml
# docker-compose.yaml PgBouncer configuration
pgbouncer:
  image: bitnami/pgbouncer:latest
  environment:
    POSTGRESQL_HOST: postgres
    POSTGRESQL_USERNAME: apex
    POSTGRESQL_PASSWORD: ${POSTGRES_PASSWORD}
    POSTGRESQL_DATABASE: apex
    PGBOUNCER_POOL_MODE: transaction
    PGBOUNCER_MAX_CLIENT_CONN: 200
    PGBOUNCER_DEFAULT_POOL_SIZE: 20
    PGBOUNCER_MIN_POOL_SIZE: 5
    PGBOUNCER_RESERVE_POOL_SIZE: 5
```

### 6.4 Table Partitioning (Future)

```sql
-- Partition calculation_archive by month (for high-volume systems)
-- Convert to partitioned table when > 10M rows

CREATE TABLE calculation_archive_partitioned (
    LIKE calculation_archive INCLUDING ALL
) PARTITION BY RANGE (created_at);

-- Create monthly partitions
CREATE TABLE calculation_archive_2025_01 PARTITION OF calculation_archive_partitioned
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

CREATE TABLE calculation_archive_2025_02 PARTITION OF calculation_archive_partitioned
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');

-- Auto-create partitions with pg_partman extension
-- SELECT partman.create_parent('public.calculation_archive_partitioned', 'created_at', 'native', 'monthly');
```

### 6.5 Read Replica Configuration

```python
# services/api/src/apex/api/db.py - Read replica support

from sqlalchemy.ext.asyncio import create_async_engine

# Primary (write) connection
_primary_engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    pool_size=10,
    max_overflow=20,
)

# Read replica connection (if available)
_replica_engine = create_async_engine(
    settings.DATABASE_URL_REPLICA.replace("postgresql://", "postgresql+asyncpg://"),
    pool_size=20,
    max_overflow=40,
) if settings.DATABASE_URL_REPLICA else None

async def get_read_db() -> AsyncSession:
    """Get read-only session (uses replica if available)."""
    engine = _replica_engine or _primary_engine
    async with async_sessionmaker(engine, class_=AsyncSession)() as session:
        yield session
```

---

## 7. Data Retention & Archiving

### 7.1 Retention Policies

| Table | Retention | Archive Strategy |
|-------|-----------|------------------|
| `calculation_archive` | 7 years | Partition, then S3 archive |
| `audit_logs` | 7 years | Partition, then S3 archive |
| `project_events` | Project lifetime + 7 years | Cascade with project |
| `supplier_quotes` | 3 years | Soft delete, then archive |
| `pe_stamps` | Permanent | Never delete |

### 7.2 Archive Script

```python
# scripts/archive_old_calculations.py
async def archive_calculations_to_s3(older_than_months: int = 24):
    """Archive calculations older than N months to S3/MinIO."""
    cutoff = datetime.utcnow() - timedelta(days=older_than_months * 30)

    # Export to JSONL
    async with SessionLocal() as db:
        results = await db.execute(
            select(CalculationArchive)
            .where(CalculationArchive.created_at < cutoff)
            .limit(10000)
        )

        # Write to MinIO
        for calc in results.scalars():
            key = f"archive/calculations/{calc.created_at.year}/{calc.created_at.month}/{calc.calculation_id}.json"
            await minio_client.put_object(bucket, key, calc.to_json())

        # Delete archived records (or move to archive partition)
        await db.execute(
            delete(CalculationArchive)
            .where(CalculationArchive.id.in_([c.id for c in results]))
        )
```

---

## 8. Testing Commands

```bash
# Apply migrations
cd services/api
alembic upgrade head

# Rollback last migration
alembic downgrade -1

# Check current revision
alembic current

# Show migration history
alembic history --verbose

# Generate new migration (auto-detect)
alembic revision --autogenerate -m "description"

# Seed reference data
python scripts/seed_aisc_shapes.py
python scripts/seed_wind_speed_data.py
python scripts/seed_seismic_data.py
python scripts/seed_soil_classifications.py
python scripts/seed_anchor_catalog.py
```

---

## Appendix A: Complete ER Diagram

```
                                    SIGNX/APEX DATABASE SCHEMA

    ┌─────────────────────────────────────────────────────────────────────────────────────┐
    │                              REFERENCE DATA                                          │
    ├─────────────────────────────────────────────────────────────────────────────────────┤
    │                                                                                      │
    │  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐              │
    │  │ aisc_shapes_v16  │    │ wind_speed_maps  │    │ seismic_params   │              │
    │  ├──────────────────┤    ├──────────────────┤    ├──────────────────┤              │
    │  │ id               │    │ id               │    │ id               │              │
    │  │ type             │    │ latitude         │    │ latitude         │              │
    │  │ aisc_manual_label│◄───┤ longitude        │    │ longitude        │              │
    │  │ w, area, ix, sx  │    │ v_risk_i/ii/iii  │    │ ss, s1, sds, sd1 │              │
    │  │ fy_ksi, fu_ksi   │    │ exposure_default │    │ sdc_risk_ii      │              │
    │  └──────────────────┘    └──────────────────┘    └──────────────────┘              │
    │                                                                                      │
    │  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐              │
    │  │ soil_classifs    │    │ anchor_catalog   │    │ code_references  │              │
    │  ├──────────────────┤    ├──────────────────┤    ├──────────────────┤              │
    │  │ site_class       │    │ manufacturer     │    │ ref_id           │              │
    │  │ bearing_psf      │    │ product_code     │    │ code, section    │              │
    │  │ fa_default       │    │ diameter, length │    │ title, formula   │              │
    │  └──────────────────┘    │ allowable_tension│    └──────────────────┘              │
    │                          └──────────────────┘                                       │
    └─────────────────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────────────────────────────────────┐
    │                              PROJECT DATA                                            │
    ├─────────────────────────────────────────────────────────────────────────────────────┤
    │                                                                                      │
    │  ┌──────────────────┐                                                               │
    │  │    projects      │──────────────────────────────────────┐                        │
    │  ├──────────────────┤                                      │                        │
    │  │ project_id (PK)  │◄──────────────────────────────┐      │                        │
    │  │ account_id       │                               │      │                        │
    │  │ name, status     │                               │      │                        │
    │  └──────────────────┘                               │      │                        │
    │         │                                           │      │                        │
    │         ▼                                           │      │                        │
    │  ┌──────────────────┐    ┌──────────────────┐      │      │                        │
    │  │ single_pole_conf │    │ double_pole_conf │      │      │                        │
    │  ├──────────────────┤    ├──────────────────┤      │      │                        │
    │  │ id               │    │ id               │      │      │                        │
    │  │ project_id (FK)  │    │ project_id (FK)  │──────┤      │                        │
    │  │ pole_section     │────│ pole_section     │──────┤──────│──►aisc_shapes_v16     │
    │  │ pole_height_ft   │    │ pole_spacing_ft  │      │      │                        │
    │  │ wind_speed_mph   │    │ wind_speed_mph   │      │      │                        │
    │  └────────┬─────────┘    └────────┬─────────┘      │      │                        │
    │           │                       │                │      │                        │
    │           ▼                       ▼                │      │                        │
    │  ┌──────────────────┐    ┌──────────────────┐      │      │                        │
    │  │ single_pole_res  │    │ double_pole_res  │      │      │                        │
    │  ├──────────────────┤    ├──────────────────┤      │      │                        │
    │  │ config_id (FK)   │    │ config_id (FK)   │      │      │                        │
    │  │ qz_psf, forces   │    │ qz_psf, forces   │      │      │                        │
    │  │ stress_ratios    │    │ stress_ratios    │      │      │                        │
    │  │ passes_all       │    │ passes_all       │      │      │                        │
    │  └──────────────────┘    └──────────────────┘      │      │                        │
    │                                                     │      │                        │
    │  ┌──────────────────┐    ┌──────────────────┐      │      │                        │
    │  │ calc_archive     │    │ bom_items        │      │      │                        │
    │  ├──────────────────┤    ├──────────────────┤      │      │                        │
    │  │ calculation_id   │    │ project_id (FK)  │──────┘      │                        │
    │  │ project_id (FK)  │────│ category         │             │                        │
    │  │ inputs (JSONB)   │    │ quantity, unit   │             │                        │
    │  │ outputs (JSONB)  │    │ unit_cost        │             │                        │
    │  │ content_sha256   │    │ anchor_id (FK)   │─────────────│──►anchor_catalog       │
    │  └──────────────────┘    └──────────────────┘             │                        │
    │                                                            │                        │
    └────────────────────────────────────────────────────────────┼────────────────────────┘
                                                                 │
    ┌────────────────────────────────────────────────────────────┼────────────────────────┐
    │                              AUDIT & COMPLIANCE            │                        │
    ├────────────────────────────────────────────────────────────┼────────────────────────┤
    │                                                            │                        │
    │  ┌──────────────────┐    ┌──────────────────┐             │                        │
    │  │ audit_logs       │    │ pe_stamps        │             │                        │
    │  ├──────────────────┤    ├──────────────────┤             │                        │
    │  │ user_id          │    │ project_id (FK)  │─────────────┘                        │
    │  │ action           │    │ pe_license_num   │                                      │
    │  │ resource_type    │    │ pe_state         │                                      │
    │  │ before/after     │    │ stamped_at       │                                      │
    │  │ timestamp        │    │ code_references  │                                      │
    │  └──────────────────┘    └──────────────────┘                                      │
    │                                                                                      │
    └─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Appendix B: Migration File Template

```python
"""Migration template

Revision ID: XXX_description
Revises: YYY_previous
Create Date: YYYY-MM-DD
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import logging

logger = logging.getLogger(__name__)

revision: str = 'XXX_description'
down_revision: Union[str, None] = 'YYY_previous'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply migration."""
    logger.info("[INFO] Starting migration XXX...")

    # Create tables
    op.create_table(
        'table_name',
        sa.Column('id', sa.Integer(), nullable=False),
        # ... columns
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index('ix_table_column', 'table_name', ['column'])

    logger.info("[OK] Migration XXX complete")


def downgrade() -> None:
    """Rollback migration."""
    op.drop_index('ix_table_column', 'table_name')
    op.drop_table('table_name')
```

---

*Document Version: 1.0*
*Last Updated: 2025-01-22*
*Author: Database Architecture Team*
