#!/usr/bin/env python
"""Setup database and run migrations for APEX"""

import asyncio
import asyncpg
import os
import sys
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Database connection settings
DATABASE_HOST = os.getenv("DATABASE_HOST", "localhost")
DATABASE_PORT = os.getenv("DATABASE_PORT", "5432")
DATABASE_USER = os.getenv("DATABASE_USER", "apex")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD", "apex")
DATABASE_NAME = os.getenv("DATABASE_NAME", "apex")

# Connection URLs
POSTGRES_URL = f"postgresql://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_HOST}:{DATABASE_PORT}/postgres"
DATABASE_URL = f"postgresql://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}"


async def create_database():
    """Create database if it doesn't exist"""
    try:
        # Connect to postgres database to create apex database
        conn = await asyncpg.connect(POSTGRES_URL)
        
        # Check if database exists
        exists = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM pg_database WHERE datname=$1)",
            DATABASE_NAME
        )
        
        if not exists:
            logger.info(f"Creating database '{DATABASE_NAME}'...")
            await conn.execute(f'CREATE DATABASE "{DATABASE_NAME}"')
            logger.info(f"[OK] Database '{DATABASE_NAME}' created")
        else:
            logger.info(f"[OK] Database '{DATABASE_NAME}' already exists")
        
        await conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Error creating database: {e}")
        return False


async def create_tables():
    """Create tables directly without Alembic"""
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        
        # Create projects table if not exists
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            project_id VARCHAR(255) PRIMARY KEY,
            account_id VARCHAR(255),
            name VARCHAR(255),
            customer VARCHAR(255),
            description TEXT,
            site_name VARCHAR(255),
            street VARCHAR(255),
            status VARCHAR(50),
            created_by VARCHAR(255),
            updated_by VARCHAR(255),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            etag VARCHAR(64),
            constants_version VARCHAR(500),
            content_sha256 VARCHAR(64),
            has_cantilever BOOLEAN DEFAULT FALSE,
            cantilever_config_id VARCHAR(255)
        )
        """)
        logger.info("[OK] Projects table ready")
        
        # Create ENUMs for cantilever tables
        await conn.execute("""
        DO $$ BEGIN
            CREATE TYPE cantilever_type AS ENUM ('single', 'double', 'truss', 'cable');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
        """)
        
        await conn.execute("""
        DO $$ BEGIN
            CREATE TYPE connection_type AS ENUM ('bolted_flange', 'welded', 'pinned', 'clamped');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
        """)
        logger.info("[OK] Created ENUMs")
        
        # Create cantilever_configs table
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS cantilever_configs (
            id VARCHAR PRIMARY KEY,
            project_id VARCHAR NOT NULL,
            cantilever_type cantilever_type NOT NULL,
            arm_length_ft FLOAT NOT NULL,
            arm_angle_deg FLOAT NOT NULL DEFAULT 0,
            arm_section VARCHAR NOT NULL,
            connection_type connection_type NOT NULL,
            num_arms INTEGER NOT NULL DEFAULT 1,
            arm_spacing_ft FLOAT DEFAULT 0,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE,
            CHECK (arm_length_ft > 0 AND arm_length_ft <= 30),
            CHECK (arm_angle_deg >= -15 AND arm_angle_deg <= 15),
            CHECK (num_arms >= 1 AND num_arms <= 4)
        )
        """)
        logger.info("[OK] Created cantilever_configs table")
        
        # Create cantilever_sections catalog table
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS cantilever_sections (
            id SERIAL PRIMARY KEY,
            designation VARCHAR UNIQUE NOT NULL,
            shape_type VARCHAR NOT NULL,
            weight_plf FLOAT NOT NULL,
            area_in2 FLOAT NOT NULL,
            ix_in4 FLOAT NOT NULL,
            sx_in3 FLOAT NOT NULL,
            rx_in FLOAT NOT NULL,
            iy_in4 FLOAT,
            sy_in3 FLOAT,
            ry_in FLOAT,
            j_in4 FLOAT,
            fy_ksi FLOAT DEFAULT 50,
            max_span_ft FLOAT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
        """)
        logger.info("[OK] Created cantilever_sections table")
        
        # Insert standard cantilever sections
        await conn.execute("""
        INSERT INTO cantilever_sections 
        (designation, shape_type, weight_plf, area_in2, ix_in4, sx_in3, rx_in, j_in4, max_span_ft)
        VALUES 
        ('HSS6x6x3/8', 'HSS', 19.08, 5.59, 39.0, 13.0, 2.64, 60.8, 12.0),
        ('HSS8x8x3/8', 'HSS', 25.78, 7.58, 94.5, 23.6, 3.53, 147.0, 18.0),
        ('HSS8x8x1/2', 'HSS', 33.68, 9.86, 120.0, 30.1, 3.49, 187.0, 20.0),
        ('HSS10x10x3/8', 'HSS', 32.58, 9.58, 192.0, 38.5, 4.48, 300.0, 22.0),
        ('HSS10x10x1/2', 'HSS', 42.68, 12.5, 246.0, 49.3, 4.44, 385.0, 25.0),
        ('HSS12x12x1/2', 'HSS', 52.08, 15.3, 430.0, 71.7, 5.30, 673.0, 30.0),
        ('PIPE8STD', 'PIPE', 28.55, 8.40, 72.5, 16.8, 2.94, 145.0, 15.0),
        ('PIPE10STD', 'PIPE', 40.48, 11.9, 161.0, 29.9, 3.67, 321.0, 20.0),
        ('PIPE12STD', 'PIPE', 49.56, 14.6, 279.0, 43.8, 4.38, 558.0, 25.0)
        ON CONFLICT (designation) DO NOTHING
        """)
        logger.info("[OK] Inserted standard cantilever sections")
        
        # Create AISC shapes table (main steel database)
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS aisc_shapes_v16 (
            id SERIAL PRIMARY KEY,
            type VARCHAR(20) NOT NULL,
            edi_std_nomenclature VARCHAR(100),
            aisc_manual_label VARCHAR(100) UNIQUE NOT NULL,
            t_f VARCHAR(10),
            w FLOAT,
            area FLOAT,
            d FLOAT,
            d_det FLOAT,
            ht FLOAT,
            h FLOAT,
            od FLOAT,
            bf FLOAT,
            bf_det FLOAT,
            b FLOAT,
            id_dim FLOAT,
            tw FLOAT,
            tw_det FLOAT,
            tf FLOAT,
            tf_det FLOAT,
            ix FLOAT,
            sx FLOAT,
            rx FLOAT,
            zx FLOAT,
            iy FLOAT,
            sy FLOAT,
            ry FLOAT,
            zy FLOAT,
            j FLOAT,
            cw FLOAT,
            rts FLOAT,
            ho FLOAT,
            torsion_constant FLOAT,
            tdes FLOAT,
            wt_class VARCHAR(20),
            aw FLOAT,
            bf_2tf FLOAT,
            h_tw FLOAT,
            x_bar FLOAT,
            y_bar FLOAT,
            ro FLOAT,
            h_bar FLOAT,
            is_available BOOLEAN DEFAULT true,
            is_astm_a1085 BOOLEAN DEFAULT false,
            nominal_depth INTEGER,
            nominal_weight INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        logger.info("[OK] Created aisc_shapes_v16 table")
        
        # Create indexes for performance
        await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_aisc_type ON aisc_shapes_v16(type);
        CREATE INDEX IF NOT EXISTS idx_aisc_weight ON aisc_shapes_v16(w);
        CREATE INDEX IF NOT EXISTS idx_aisc_sx ON aisc_shapes_v16(sx);
        CREATE INDEX IF NOT EXISTS idx_aisc_ix ON aisc_shapes_v16(ix);
        CREATE INDEX IF NOT EXISTS idx_aisc_label ON aisc_shapes_v16(aisc_manual_label);
        """)
        logger.info("[OK] Created indexes")
        
        # Create views for sign-specific shapes
        await conn.execute("""
        CREATE OR REPLACE VIEW sign_pole_sections AS
        SELECT 
            aisc_manual_label as designation,
            type,
            w as weight_plf,
            area as area_in2,
            ix as ix_in4,
            sx as sx_in3,
            rx as rx_in,
            zx as zx_in3,
            j as j_in4,
            CASE 
                WHEN type = 'HSS' THEN d * 2.5
                WHEN type = 'PIPE' THEN d * 2.0
                WHEN type = 'W' THEN d * 1.5
                ELSE d
            END as max_cantilever_ft
        FROM aisc_shapes_v16
        WHERE type IN ('HSS', 'PIPE', 'W', 'WT')
            AND w > 10
            AND sx > 5
        ORDER BY type, w;
        """)
        logger.info("[OK] Created sign_pole_sections view")
        
        await conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Error creating tables: {e}")
        return False


async def main():
    """Main setup function"""
    logger.info("=" * 60)
    logger.info("APEX DATABASE SETUP")
    logger.info("=" * 60)
    
    # Try to create database
    if not await create_database():
        logger.error("\nERROR: Could not create database")
        logger.info("\nMake sure PostgreSQL is running:")
        logger.info("  - For Docker: docker run -d --name postgres -e POSTGRES_PASSWORD=apex -e POSTGRES_USER=apex -p 5432:5432 postgres:16")
        logger.info("  - For local: pg_ctl start")
        return
    
    # Create tables
    if not await create_tables():
        logger.error("\nERROR: Could not create tables")
        return
    
    logger.info("\n" + "=" * 60)
    logger.info("DATABASE SETUP COMPLETE!")
    logger.info("=" * 60)
    logger.info("\nNext steps:")
    logger.info("1. Run: python scripts/import_aisc_database.py")
    logger.info("2. The database is ready for AISC data import")


if __name__ == "__main__":
    asyncio.run(main())