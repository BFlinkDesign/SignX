# File Management Guide

Complete guide to file uploads, storage, and management with MinIO.

## Overview

File management uses:
- **MinIO** (S3-compatible) for object storage
- **SHA256** verification for integrity
- **Presigned URLs** for secure uploads
- **Project attachments** for file association

## Upload Flow

### Step 1: Presign Upload URL

Get presigned URL for direct client upload:

```bash
curl -X POST http://localhost:8000/files/presign \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "drawing.pdf",
    "content_type": "application/pdf"
  }'
```

**Response:**
```json
{
  "result": {
    "upload_url": "http://object:9000/apex-uploads/uploads/abc123.pdf?X-Amz-Algorithm=...",
    "blob_key": "uploads/abc123.pdf",
    "expires_in": 3600
  }
}
```

### Step 2: Upload File

Upload directly to MinIO using presigned URL:

```bash
curl -X PUT "$UPLOAD_URL" \
  -H "Content-Type: application/pdf" \
  --data-binary "@drawing.pdf"
```

### Step 3: Calculate SHA256

Calculate file hash:

```bash
SHA256=$(sha256sum drawing.pdf | cut -d' ' -f1)
```

### Step 4: Attach to Project

Attach file to project:

```bash
curl -X POST http://localhost:8000/files/attach \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "proj_abc123",
    "blob_key": "uploads/abc123.pdf",
    "sha256": "'$SHA256'",
    "filename": "drawing.pdf",
    "content_type": "application/pdf",
    "size_bytes": 1048576
  }'
```

**Response:**
```json
{
  "result": {
    "file_id": 1,
    "project_id": "proj_abc123",
    "blob_key": "uploads/abc123.pdf",
    "sha256": "abc123...",
    "attached": true
  }
}
```

## File Verification

### SHA256 Verification

System verifies file integrity:
- **On upload**: SHA256 calculated
- **On attach**: SHA256 verified
- **Mismatch**: Returns `422 Unprocessable Entity`

### Verification Process

```bash
# Upload file
curl -X PUT "$UPLOAD_URL" --data-binary "@file.pdf"

# Attach with SHA256
curl -X POST http://localhost:8000/files/attach \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "proj_abc123",
    "blob_key": "uploads/file.pdf",
    "sha256": "correct_sha256_here"
  }'

# If SHA256 mismatches:
# Response: 422 with error detail
```

## File Types

### Supported Types

Common file types:
- **PDF**: `application/pdf` - Drawings, reports
- **DXF**: `application/dxf` - CAD files
- **Images**: `image/png`, `image/jpeg` - Photos, renderings
- **Documents**: `application/msword`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document`

### Content Type Validation

System validates content type:
- Must match file extension
- Invalid types return `422`

## File Storage

### MinIO Configuration

MinIO settings:

```bash
APEX_MINIO_URL=http://object:9000
APEX_MINIO_ACCESS_KEY=minioadmin
APEX_MINIO_SECRET_KEY=minioadmin
APEX_MINIO_BUCKET=apex-uploads
```

### Storage Structure

```
apex-uploads/
├── uploads/
│   ├── abc123.pdf          # User uploads
│   └── def456.dxf
└── blobs/
    ├── ab/
    │   └── abc123def456.pdf  # Generated reports (SHA256-based)
    └── cd/
        └── cde789...pdf
```

### Blob Keys

Blob keys follow pattern:
- **Uploads**: `uploads/{random_id}.{ext}`
- **Reports**: `blobs/{sha256[:2]}/{sha256}.pdf`

## File Management

### List Project Files

Files are associated with projects via payloads:

```bash
# Get project with payload (includes files)
curl http://localhost:8000/projects/proj_abc123 | jq '.result.payload.files'
```

### File Download

Download file via blob key:

```bash
# Get download URL (presigned)
curl -X POST http://localhost:8000/files/download \
  -H "Content-Type: application/json" \
  -d '{
    "blob_key": "uploads/abc123.pdf"
  }'
```

**Response:**
```json
{
  "result": {
    "download_url": "http://object:9000/apex-uploads/uploads/abc123.pdf?X-Amz-Algorithm=...",
    "expires_in": 3600
  }
}
```

### File Deletion

Files are typically not deleted (immutable audit trail). For cleanup:

```bash
# Manual deletion via MinIO client
mc rm object/apex-uploads/uploads/abc123.pdf
```

## Integration Examples

### Complete Upload Flow

```bash
#!/bin/bash

PROJECT_ID="proj_abc123"
FILENAME="drawing.pdf"
CONTENT_TYPE="application/pdf"

# 1. Presign upload URL
PRESIGN=$(curl -s -X POST http://localhost:8000/files/presign \
  -H "Content-Type: application/json" \
  -d "{
    \"filename\": \"$FILENAME\",
    \"content_type\": \"$CONTENT_TYPE\"
  }")

UPLOAD_URL=$(echo $PRESIGN | jq -r '.result.upload_url')
BLOB_KEY=$(echo $PRESIGN | jq -r '.result.blob_key')

# 2. Upload file
curl -X PUT "$UPLOAD_URL" \
  -H "Content-Type: $CONTENT_TYPE" \
  --data-binary "@$FILENAME"

# 3. Calculate SHA256
SHA256=$(sha256sum "$FILENAME" | cut -d' ' -f1)
SIZE=$(stat -f%z "$FILENAME")  # macOS
# SIZE=$(stat -c%s "$FILENAME")  # Linux

# 4. Attach to project
ATTACH=$(curl -s -X POST http://localhost:8000/files/attach \
  -H "Content-Type: application/json" \
  -d "{
    \"project_id\": \"$PROJECT_ID\",
    \"blob_key\": \"$BLOB_KEY\",
    \"sha256\": \"$SHA256\",
    \"filename\": \"$FILENAME\",
    \"content_type\": \"$CONTENT_TYPE\",
    \"size_bytes\": $SIZE
  }")

echo "File attached: $(echo $ATTACH | jq -r '.result.blob_key')"
```

### Include Files in Payload

```bash
# Save payload with file references
curl -X POST http://localhost:8000/projects/$PROJECT_ID/payload \
  -H "Content-Type: application/json" \
  -d '{
    "module": "signage.single_pole",
    "config": {...},
    "files": [
      "uploads/drawing.pdf",
      "uploads/render.png"
    ],
    "cost_snapshot": {...}
  }'
```

## Best Practices

### 1. Always Verify SHA256

```bash
# Calculate before upload
SHA256=$(sha256sum file.pdf | cut -d' ' -f1)

# Verify on attach
# System validates automatically
```

### 2. Use Appropriate Content Types

```bash
# PDF files
"content_type": "application/pdf"

# DXF files
"content_type": "application/dxf"

# Images
"content_type": "image/png"
```

### 3. Include Files in Payload

Always reference files in project payload:
- Enables report generation
- Maintains file associations
- Supports audit trail

### 4. Handle Upload Errors

```bash
# Check upload status
if [ $? -ne 0 ]; then
  echo "Upload failed"
  exit 1
fi

# Verify attachment
if [ "$(echo $ATTACH | jq -r '.result.attached')" != "true" ]; then
  echo "Attachment failed"
  exit 1
fi
```

## Error Handling

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| 422 Presign failed | Invalid filename | Check filename format |
| 422 SHA256 mismatch | File corrupted | Re-upload file |
| 404 Blob not found | File deleted | Check blob_key |
| 403 Access denied | MinIO credentials | Verify credentials |

### Example Error Response

```json
{
  "result": null,
  "assumptions": ["SHA256 verification failed"],
  "confidence": 0.1,
  "trace": {
    "data": {
      "error_id": "error-abc123",
      "error_type": "ValidationError"
    }
  }
}
```

## MinIO Management

### Access MinIO Console

```bash
# MinIO console (if enabled)
open http://localhost:9001

# Login: minioadmin / minioadmin
```

### List Buckets

```bash
mc ls object/
```

### List Files

```bash
mc ls object/apex-uploads/uploads/
```

### Download File

```bash
mc cp object/apex-uploads/uploads/file.pdf ./file.pdf
```

## Next Steps

- [**Project Management**](project-management.md) - Manage project files
- [**Sign Design Workflow**](sign-design-workflow.md) - Include files in design
- [**API Reference**](../reference/api-endpoints.md) - Endpoint details

