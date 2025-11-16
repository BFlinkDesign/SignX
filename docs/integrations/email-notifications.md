# Email Notifications Integration

Complete guide for email notification setup and customization.

## Overview

Email notifications are sent for:
- Project submission
- Report ready
- Project approval/rejection
- Engineering review required

## SMTP Configuration

### Gmail SMTP

```python
# .env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=noreply@example.com
SMTP_USE_TLS=true
```

### SendGrid

```python
# .env
SENDGRID_API_KEY=SG.xxx
SENDGRID_FROM_EMAIL=noreply@example.com
SENDGRID_FROM_NAME="SIGN X Studio"
```

### AWS SES

```python
# .env
AWS_SES_REGION=us-east-1
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx
SMTP_FROM=noreply@example.com
```

## Email Templates

### Jinja2 Template System

```python
# services/api/src/apex/api/utils/email.py
from jinja2 import Environment, FileSystemLoader

env = Environment(loader=FileSystemLoader("templates/email"))

def render_email(template_name: str, context: dict) -> tuple[str, str]:
    template = env.get_template(template_name)
    html = template.render(**context)
    
    # Plain text version
    text = html2text(html)
    
    return text, html
```

### Template: Project Submitted

```html
<!-- templates/email/project_submitted.html -->
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; }
        .header { background-color: #0066cc; color: white; padding: 20px; }
        .content { padding: 20px; }
        .button { background-color: #0066cc; color: white; padding: 10px 20px; text-decoration: none; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Project Submitted: {{ project_name }}</h1>
    </div>
    <div class="content">
        <p>Your sign design project has been submitted for review.</p>
        <p><strong>Project ID:</strong> {{ project_id }}</p>
        <p><strong>Confidence Score:</strong> {{ confidence }}%</p>
        {% if assumptions %}
        <p><strong>Notes:</strong></p>
        <ul>
            {% for assumption in assumptions %}
            <li>{{ assumption }}</li>
            {% endfor %}
        </ul>
        {% endif %}
        <p>
            <a href="{{ project_url }}" class="button">View Project</a>
        </p>
    </div>
</body>
</html>
```

### Template: Report Ready

```html
<!-- templates/email/report_ready.html -->
<!DOCTYPE html>
<html>
<body>
    <h1>Engineering Report Ready</h1>
    <p>Your report for project <strong>{{ project_name }}</strong> is ready for download.</p>
    <p>
        <a href="{{ report_url }}">Download PDF Report</a>
    </p>
    <p>Report SHA256: <code>{{ report_sha256 }}</code></p>
</body>
</html>
```

## Event Triggers

### Submission Event

```python
# services/api/src/apex/api/routes/submission.py
@router.post("/projects/{project_id}/submit")
async def submit_project(...):
    # Submit project
    ...
    
    # Send email notification
    if project.manager_email:
        await send_email(
            to=project.manager_email,
            subject=f"Project Submitted: {project.name}",
            template="project_submitted",
            context={
                "project_id": project.project_id,
                "project_name": project.name,
                "confidence": f"{project.confidence:.0%}",
                "assumptions": project.assumptions or [],
                "project_url": f"https://app.example.com/projects/{project.project_id}",
            }
        )
```

### Report Ready Event

```python
# services/worker/src/apex/worker/tasks.py
@celery_app.task(name="projects.report.generate")
async def generate_report_task(project_id: str, payload: dict):
    # Generate report
    report = await generate_report(payload)
    
    # Send email
    project = await get_project(project_id)
    if project.manager_email:
        await send_email(
            to=project.manager_email,
            subject=f"Report Ready: {project.name}",
            template="report_ready",
            context={
                "project_name": project.name,
                "report_url": f"https://api.example.com/artifacts/{report.pdf_ref}",
                "report_sha256": report.sha256,
            }
        )
```

### Engineering Review Required

```python
# Check confidence on submission
if confidence < 0.5:
    await send_email(
        to=project.engineering_email,
        subject=f"Engineering Review Required: {project.name}",
        template="engineering_review",
        context={
            "project_id": project.project_id,
            "project_name": project.name,
            "confidence": f"{confidence:.0%}",
            "assumptions": assumptions,
        }
    )
```

## Email Sending Service

### Implementation

```python
# services/api/src/apex/api/utils/email.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

async def send_email(
    to: str,
    subject: str,
    template: str,
    context: dict,
):
    text, html = render_email(template, context)
    
    if settings.SENDGRID_API_KEY:
        # Use SendGrid
        await send_via_sendgrid(to, subject, text, html)
    elif settings.SMTP_HOST:
        # Use SMTP
        await send_via_smtp(to, subject, text, html)
    else:
        logger.warning("No email provider configured")
```

### SendGrid Implementation

```python
import sendgrid
from sendgrid.helpers.mail import Mail

async def send_via_sendgrid(to: str, subject: str, text: str, html: str):
    sg = sendgrid.SendGridAPIClient(settings.SENDGRID_API_KEY)
    
    message = Mail(
        from_email=settings.SENDGRID_FROM_EMAIL,
        to_emails=to,
        subject=subject,
        plain_text_content=text,
        html_content=html
    )
    
    response = sg.send(message)
    return response.status_code == 202
```

### SMTP Implementation

```python
async def send_via_smtp(to: str, subject: str, text: str, html: str):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to
    
    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))
    
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        if settings.SMTP_USE_TLS:
            server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(msg)
```

## Customization

### Template Variables

Available in all templates:
- `project_id` - Project identifier
- `project_name` - Project name
- `customer` - Customer name
- `confidence` - Confidence score
- `assumptions` - List of assumptions
- `project_url` - Link to project
- `report_url` - Link to report (if applicable)

### Custom Templates

1. **Create Template**
   ```html
   <!-- templates/email/custom_template.html -->
   <h1>{{ subject }}</h1>
   <p>{{ message }}</p>
   ```

2. **Use Template**
   ```python
   await send_email(
       to="user@example.com",
       subject="Custom Notification",
       template="custom_template",
       context={"message": "Custom content"}
   )
   ```

## Testing

### Local Testing

```python
# Use MailHog for local development
SMTP_HOST=localhost
SMTP_PORT=1025
# Access MailHog UI: http://localhost:8025
```

### Send Test Email

```bash
curl -X POST http://localhost:8000/admin/test-email \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "to": "test@example.com",
    "template": "project_submitted",
    "context": {...}
  }'
```

---

**Next Steps:**
- [**API Reference**](../api/api-reference.md)
- [**Troubleshooting**](../operations/troubleshooting.md)

