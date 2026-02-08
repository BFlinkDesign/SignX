"""RBAC (Role-Based Access Control) decorators and utilities."""

from __future__ import annotations

import structlog
from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .audit import log_audit
from .auth import TokenData, get_current_user
from .db import get_db
from .models_audit import Permission, Role, UserRole, role_permissions

logger = structlog.get_logger(__name__)


async def get_user_permissions(
    db: AsyncSession,
    user_id: str,
    account_id: str,
) -> set[str]:
    """Get all permissions for a user in a given account.
    
    Returns:
        Set of permission strings in format "{resource}.{action}"
        e.g., {"calculation.approve", "project.delete", "file.read"}
    """
    # Get user's roles in this account
    user_roles_query = select(UserRole).where(
        UserRole.user_id == user_id,
        UserRole.account_id == account_id,
    )
    result = await db.execute(user_roles_query)
    user_roles = result.scalars().all()
    
    if not user_roles:
        return set()
    
    role_ids = [ur.role_id for ur in user_roles]
    
    # Get permissions for these roles
    permissions_query = (
        select(Permission)
        .join(role_permissions, Permission.permission_id == role_permissions.c.permission_id)
        .where(role_permissions.c.role_id.in_(role_ids))
    )
    result = await db.execute(permissions_query)
    permissions = result.scalars().all()
    
    # Format as "{resource}.{action}"
    return {f"{p.resource}.{p.action}" for p in permissions}


async def check_permission(
    db: AsyncSession,
    user: TokenData,
    permission: str,
) -> bool:
    """Check if user has a specific permission.
    
    Args:
        db: Database session
        user: Current user token data
        permission: Permission string in format "{resource}.{action}"
    
    Returns:
        True if user has permission, False otherwise
    """
    # Admins have all permissions
    if "admin" in user.roles:
        return True
    
    # Get user permissions
    user_perms = await get_user_permissions(db, user.user_id, user.account_id)
    
    return permission in user_perms


def require_permission(permission: str):
    """Decorator factory for requiring specific permissions.
    
    Usage:
        @router.post("/calculations/{id}/approve")
        @require_permission("calculation.approve")
        async def approve_calculation(
            id: str,
            current_user: TokenData = Depends(get_current_user),
            db: AsyncSession = Depends(get_db),
        ):
            ...
    
    Args:
        permission: Permission string in format "{resource}.{action}"
    
    Returns:
        FastAPI dependency that checks permission and raises 403 if missing
    """
    async def _permission_check(
        current_user: TokenData = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> TokenData:
        has_permission = await check_permission(db, current_user, permission)
        
        if not has_permission:
            logger.warning(
                "rbac.permission_denied",
                user_id=current_user.user_id,
                account_id=current_user.account_id,
                permission=permission,
            )
            
            # Log failed permission check
            await log_audit(
                db=db,
                action="permission.denied",
                resource_type="access_control",
                user_id=current_user.user_id,
                account_id=current_user.account_id,
                error_details={"permission": permission, "user_roles": current_user.roles},
            )
            
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission required: {permission}",
            )
        
        return current_user
    
    return _permission_check


def require_any_permission(permissions: list[str]):
    """Decorator factory for requiring any of multiple permissions.
    
    Usage:
        @router.get("/projects/{id}")
        @require_any_permission(["project.read", "project.read_all"])
        async def get_project(...):
            ...
    """
    async def _permission_check(
        current_user: TokenData = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> TokenData:
        # Admins have all permissions
        if "admin" in current_user.roles:
            return current_user
        
        user_perms = await get_user_permissions(db, current_user.user_id, current_user.account_id)
        
        if not any(perm in user_perms for perm in permissions):
            logger.warning(
                "rbac.permission_denied",
                user_id=current_user.user_id,
                permissions=permissions,
            )
            
            await log_audit(
                db=db,
                action="permission.denied",
                resource_type="access_control",
                user_id=current_user.user_id,
                account_id=current_user.account_id,
                error_details={"permissions": permissions, "user_roles": current_user.roles},
            )
            
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required permission: one of {permissions}",
            )
        
        return current_user
    
    return _permission_check


def require_all_permissions(permissions: list[str]):
    """Decorator factory for requiring all of multiple permissions.
    
    Usage:
        @router.delete("/projects/{id}")
        @require_all_permissions(["project.delete", "project.confirm"])
        async def delete_project(...):
            ...
    """
    async def _permission_check(
        current_user: TokenData = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> TokenData:
        # Admins have all permissions
        if "admin" in current_user.roles:
            return current_user
        
        user_perms = await get_user_permissions(db, current_user.user_id, current_user.account_id)
        
        if not all(perm in user_perms for perm in permissions):
            missing = [p for p in permissions if p not in user_perms]
            
            logger.warning(
                "rbac.permission_denied",
                user_id=current_user.user_id,
                missing_permissions=missing,
            )
            
            await log_audit(
                db=db,
                action="permission.denied",
                resource_type="access_control",
                user_id=current_user.user_id,
                account_id=current_user.account_id,
                error_details={"missing_permissions": missing, "user_roles": current_user.roles},
            )
            
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required permissions: {permissions}",
            )
        
        return current_user
    
    return _permission_check


# Helper to seed default roles and permissions
async def seed_default_rbac(db: AsyncSession) -> None:
    """Seed default roles and permissions for RBAC system."""
    from sqlalchemy import select
    
    # Default roles
    default_roles = [
        {"name": "admin", "description": "Full system access"},
        {"name": "engineer", "description": "Engineering calculations and approvals"},
        {"name": "approver", "description": "Can approve calculations and projects"},
        {"name": "viewer", "description": "Read-only access"},
        {"name": "pe", "description": "Professional Engineer - can stamp calculations"},
    ]
    
    # Default permissions
    default_permissions = [
        # Project permissions
        {"resource": "project", "action": "create", "description": "Create new projects"},
        {"resource": "project", "action": "read", "description": "View own projects"},
        {"resource": "project", "action": "read_all", "description": "View all projects"},
        {"resource": "project", "action": "update", "description": "Update projects"},
        {"resource": "project", "action": "delete", "description": "Delete projects"},
        {"resource": "project", "action": "submit", "description": "Submit projects for approval"},
        
        # Calculation permissions
        {"resource": "calculation", "action": "create", "description": "Create calculations"},
        {"resource": "calculation", "action": "read", "description": "View calculations"},
        {"resource": "calculation", "action": "approve", "description": "Approve calculations"},
        {"resource": "calculation", "action": "stamp", "description": "PE stamp calculations"},
        
        # File permissions
        {"resource": "file", "action": "upload", "description": "Upload files"},
        {"resource": "file", "action": "read", "description": "View files"},
        {"resource": "file", "action": "delete", "description": "Delete files"},
        
        # Audit permissions
        {"resource": "audit", "action": "read", "description": "View audit logs"},
        
        # Admin permissions
        {"resource": "admin", "action": "manage_users", "description": "Manage users and roles"},
        {"resource": "admin", "action": "manage_permissions", "description": "Manage permissions"},
    ]
    
    # Create roles
    for role_data in default_roles:
        existing = await db.execute(select(Role).where(Role.name == role_data["name"]))
        if not existing.scalar_one_or_none():
            role = Role(**role_data)
            db.add(role)
    
    await db.commit()
    
    # Create permissions
    permission_map = {}
    for perm_data in default_permissions:
        existing = await db.execute(
            select(Permission).where(
                Permission.resource == perm_data["resource"],
                Permission.action == perm_data["action"],
            )
        )
        if not existing.scalar_one_or_none():
            perm = Permission(**perm_data)
            db.add(perm)
            permission_map[f"{perm_data['resource']}.{perm_data['action']}"] = perm
    
    await db.commit()
    
    # Refresh to get IDs
    for role_data in default_roles:
        role_result = await db.execute(select(Role).where(Role.name == role_data["name"]))
        role = role_result.scalar_one()
        
        # Assign permissions to roles
        if role.name == "admin":
            # Admin gets all permissions
            for perm in permission_map.values():
                role.permissions.append(perm)
        elif role.name == "engineer":
            # Engineer can create/read calculations, approve
            for key, perm in permission_map.items():
                if key.startswith("calculation.") or key.startswith("project.create"):
                    role.permissions.append(perm)
        elif role.name == "approver":
            # Approver can approve calculations and projects
            for key, perm in permission_map.items():
                if "approve" in key or key in ["project.submit", "project.read_all"]:
                    role.permissions.append(perm)
        elif role.name == "pe":
            # PE can stamp calculations
            for key, perm in permission_map.items():
                if "stamp" in key or key in ["calculation.read", "calculation.approve"]:
                    role.permissions.append(perm)
        elif role.name == "viewer":
            # Viewer gets read permissions
            for key, perm in permission_map.items():
                if "read" in key:
                    role.permissions.append(perm)
    
    await db.commit()
    
    logger.info("rbac.seeded", roles=len(default_roles), permissions=len(default_permissions))
