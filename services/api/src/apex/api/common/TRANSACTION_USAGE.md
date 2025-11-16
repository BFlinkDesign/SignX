# Transaction Management Usage Guide

This module provides two patterns for managing database transactions: **decorator** and **context manager**.

## Decorator Pattern (`@with_transaction`)

Use when you want automatic transaction management for an entire route function.

### Usage Example

```python
from ..common.transactions import with_transaction

@router.post("/projects")
@with_transaction
async def create_project(
    req: ProjectCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope:
    """Create project - auto-commits on success, auto-rollbacks on error."""
    project = Project(...)
    db.add(project)
    await log_event(db, project_id, "project.created", ...)
    # No manual commit needed - decorator handles it
    return make_envelope(...)
```

### Benefits
- ✅ Automatic commit on success
- ✅ Automatic rollback on exception
- ✅ Clean, minimal code
- ✅ Works with FastAPI dependency injection

### When to Use
- Route handlers that perform database writes
- Simple operations that fit in a single transaction
- When you want declarative transaction management

---

## Context Manager Pattern (`async with transaction(db)`)

Use when you need explicit transaction boundaries or partial transaction control.

### Usage Example

```python
from ..common.transactions import transaction

@router.post("/projects/{project_id}/submit")
async def submit_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope:
    """Submit project with explicit transaction control."""
    # Some operations outside transaction
    pm_task_id = enqueue_pm_dispatch(...)
    
    # Explicit transaction for related DB operations
    try:
        async with transaction(db):
            project.status = "submitted"
            await log_event(db, project_id, "project.submitted", ...)
            # Auto-commits when exiting context successfully
    except Exception as e:
        # Transaction already rolled back
        logger.error("submission_failed", error=str(e))
        raise HTTPException(status_code=500, ...)
    
    # Operations after transaction (e.g., async tasks)
    enqueue_email(...)
    
    return make_envelope(...)
```

### Benefits
- ✅ Explicit transaction boundaries
- ✅ Mix transaction and non-transaction operations
- ✅ Fine-grained control
- ✅ Works well with try/except for custom error handling

### When to Use
- Complex flows with operations outside the transaction
- When you need custom error handling around transactions
- When transaction boundaries are not obvious
- When mixing DB operations with external service calls

---

## Comparison

| Pattern | Decorator | Context Manager |
|---------|-----------|----------------|
| **Syntax** | `@with_transaction` | `async with transaction(db):` |
| **Explicit Control** | No | Yes |
| **Flexibility** | Low | High |
| **Code Clarity** | High | Medium |
| **Best For** | Simple routes | Complex flows |

---

## Error Handling

Both patterns automatically roll back on exceptions:

```python
@with_transaction
async def my_route(db: AsyncSession = Depends(get_db)):
    db.add(item)
    raise ValueError("Something went wrong")
    # Transaction automatically rolled back
    # Exception propagates normally
```

---

## Nested Transactions

SQLAlchemy handles nested transactions using savepoints. Both patterns work correctly:

```python
async with transaction(db):
    db.add(item1)
    
    async with transaction(db):  # Creates savepoint
        db.add(item2)
        # If this fails, only item2 is rolled back
        # item1 remains committed
    
    # Outer transaction commits both if successful
```

**Note:** In practice, prefer flat transactions when possible for simplicity.

---

## Best Practices

1. **Use decorator for simple routes** - Less boilerplate
2. **Use context manager for complex flows** - More control
3. **Don't mix both patterns** - Pick one per function
4. **Keep transactions short** - Don't include long-running external calls
5. **Log transaction failures** - Always log rollbacks for debugging

---

## Migration Guide

### Before (Manual Management)

```python
async def create_project(...):
    try:
        db.add(project)
        await log_event(...)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
```

### After (Decorator)

```python
@with_transaction
async def create_project(...):
    db.add(project)
    await log_event(...)
    # Auto-commit/rollback handled
```

### After (Context Manager)

```python
async def create_project(...):
    async with transaction(db):
        db.add(project)
        await log_event(...)
    # Auto-commit/rollback handled
```

---

## Examples

### Example 1: Simple Create (Decorator)

```python
@router.post("/projects")
@with_transaction
async def create_project(
    req: ProjectCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope:
    project = Project(...)
    db.add(project)
    await log_event(db, project.project_id, "project.created", ...)
    return make_envelope(result={...})
```

### Example 2: Complex Submission (Context Manager)

```python
@router.post("/projects/{project_id}/submit")
async def submit_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope:
    # Operations outside transaction
    pm_task_id = enqueue_pm_dispatch(...)
    
    # Transaction for DB operations
    try:
        async with transaction(db):
            project.status = "submitted"
            await log_event(db, project_id, "project.submitted", ...)
    except Exception as e:
        logger.error("submission_failed", error=str(e))
        raise HTTPException(status_code=500, ...)
    
    # Async operations after transaction
    enqueue_email(...)
    
    return make_envelope(result={...})
```

---

## Debugging

Both patterns log transaction events:

```python
# Successful commit
logger.debug("transaction.committed", func="create_project")

# Rollback on error
logger.error(
    "transaction.rolled_back",
    func="create_project",
    error="...",
    error_type="ValueError"
)
```

Check logs for transaction lifecycle events.

