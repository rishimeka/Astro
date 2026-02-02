# Security Best Practices for Astro Platform

This document outlines security best practices for deploying and operating the Astro platform.

## Table of Contents
1. [Environment Configuration](#environment-configuration)
2. [CORS Configuration](#cors-configuration)
3. [API Security](#api-security)
4. [Database Security](#database-security)
5. [Secrets Management](#secrets-management)
6. [Monitoring and Logging](#monitoring-and-logging)
7. [Production Deployment Checklist](#production-deployment-checklist)

---

## Environment Configuration

### Required Environment Variables

**Critical:** Always set `OPENAI_API_KEY` before starting the application. The application will fail to start if this is not set.

```bash
export OPENAI_API_KEY=your_key_here
```

### Environment File Security

1. **Never commit `.env` files** to version control
2. Use `.env.example` as a template
3. Set appropriate file permissions:
   ```bash
   chmod 600 .env
   ```
4. Use different `.env` files for each environment (dev, staging, prod)

---

## CORS Configuration

### Default Configuration

The default CORS configuration allows `http://localhost:3000` for development.

### Production Configuration

**CRITICAL:** In production, set `ALLOWED_ORIGINS` to your specific domain(s):

```bash
# Single domain
ALLOWED_ORIGINS=https://yourdomain.com

# Multiple domains
ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com,https://admin.yourdomain.com
```

### What NOT to Do

❌ **NEVER** use wildcard origins with credentials:
```python
# BAD - Do not do this!
allow_origins=["*"]
allow_credentials=True
```

This configuration is a severe security vulnerability that allows any website to make authenticated requests to your API.

### Testing CORS Configuration

Test your CORS configuration using curl:

```bash
# Should succeed from allowed origin
curl -H "Origin: https://yourdomain.com" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: Content-Type" \
     -X OPTIONS \
     http://your-api.com/chat

# Should fail from disallowed origin  
curl -H "Origin: https://evil.com" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: Content-Type" \
     -X OPTIONS \
     http://your-api.com/chat
```

---

## API Security

### Rate Limiting

Implement rate limiting to prevent abuse:

```python
# Install slowapi
pip install slowapi

# Add to main.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

# Apply to sensitive endpoints
@app.post("/chat")
@limiter.limit("10/minute")
async def chat(...):
    ...
```

### Input Validation

Always validate user inputs:

1. Use Pydantic models for request validation
2. Validate IDs and user-provided strings
3. Sanitize inputs before logging
4. Set reasonable limits on input sizes

Example:
```python
from pydantic import Field, validator

class QueryRequest(BaseModel):
    query: str = Field(..., max_length=5000, min_length=1)
    
    @validator('query')
    def validate_query(cls, v):
        if not v or v.isspace():
            raise ValueError('Query cannot be empty')
        return v.strip()
```

### Authentication (Future)

When implementing authentication:

1. Use industry-standard protocols (OAuth 2.0, JWT)
2. Hash passwords with bcrypt or Argon2
3. Implement session management
4. Use HTTPS only
5. Implement CSRF protection

---

## Database Security

### MongoDB Security Checklist

✅ **Enable authentication:**
```javascript
// Create admin user
use admin
db.createUser({
  user: "admin",
  pwd: "strong_password",
  roles: ["userAdminAnyDatabase", "dbAdminAnyDatabase", "readWriteAnyDatabase"]
})

// Create application user
use astro
db.createUser({
  user: "astro_app",
  pwd: "strong_password",
  roles: ["readWrite"]
})
```

✅ **Connection string with authentication:**
```bash
MONGO_URI=mongodb://astro_app:password@localhost:27017/astro?authSource=astro
```

✅ **Network security:**
- Enable firewall rules
- Use TLS/SSL for connections
- Restrict access to specific IPs
- Use MongoDB Atlas for managed security

✅ **Encryption:**
- Enable encryption at rest
- Use TLS for data in transit
- Consider field-level encryption for sensitive data

### Connection Pool Configuration

The application is configured with optimal connection pool settings:

```python
AsyncIOMotorClient(
    mongo_uri,
    maxPoolSize=100,          # Maximum connections
    minPoolSize=10,           # Minimum connections to maintain
    serverSelectionTimeoutMS=5000,  # Server selection timeout
    connectTimeoutMS=10000,   # Initial connection timeout
    socketTimeoutMS=20000,    # Socket operation timeout
)
```

---

## Secrets Management

### Development

Use `.env` files for local development:

```bash
# .env
OPENAI_API_KEY=sk-...
MONGO_URI=mongodb://localhost:27017
```

### Production

**DO NOT** use `.env` files in production. Instead, use a secrets manager:

#### AWS Secrets Manager

```python
import boto3
import json

def get_secret(secret_name):
    client = boto3.client('secretsmanager', region_name='us-east-1')
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])

secrets = get_secret('astro/production')
os.environ['OPENAI_API_KEY'] = secrets['OPENAI_API_KEY']
```

#### Azure Key Vault

```python
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

credential = DefaultAzureCredential()
client = SecretClient(vault_url="https://your-vault.vault.azure.net/", credential=credential)

os.environ['OPENAI_API_KEY'] = client.get_secret("OPENAI-API-KEY").value
```

#### Kubernetes Secrets

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: astro-secrets
type: Opaque
stringData:
  OPENAI_API_KEY: sk-...
  MONGO_URI: mongodb://...
```

---

## Monitoring and Logging

### Logging Best Practices

1. **Use structured logging:**
   ```python
   import logging
   import json
   
   logger = logging.getLogger(__name__)
   logger.info(json.dumps({
       "event": "constellation_executed",
       "constellation_id": constellation_id,
       "duration_ms": duration,
       "status": "success"
   }))
   ```

2. **Never log sensitive data:**
   - ❌ API keys
   - ❌ Passwords
   - ❌ Personal information
   - ❌ Full API responses
   - ✅ Request IDs
   - ✅ Error codes
   - ✅ Timing information

3. **Set appropriate log levels:**
   ```python
   # Production
   logging.basicConfig(level=logging.INFO)
   
   # Development
   logging.basicConfig(level=logging.DEBUG)
   ```

### Security Monitoring

Monitor for:

1. **Authentication failures**
2. **Rate limit violations**
3. **Unusual access patterns**
4. **High error rates**
5. **Slow queries**
6. **Failed database connections**

### Recommended Tools

- **Application Performance Monitoring:** Datadog, New Relic, Application Insights
- **Log Aggregation:** ELK Stack, Splunk, CloudWatch Logs
- **Security Monitoring:** Snyk, Dependabot, OWASP Dependency Check
- **Infrastructure Monitoring:** Prometheus + Grafana

---

## Production Deployment Checklist

### Before Deployment

- [ ] All environment variables set correctly
- [ ] `ALLOWED_ORIGINS` configured for production domain(s)
- [ ] `OPENAI_API_KEY` set and validated
- [ ] MongoDB authentication enabled
- [ ] MongoDB connection uses TLS/SSL
- [ ] Database backups configured
- [ ] Secrets stored in secrets manager (not `.env` files)
- [ ] Rate limiting implemented
- [ ] Logging configured appropriately
- [ ] Error monitoring set up
- [ ] HTTPS enforced on all endpoints
- [ ] Security headers configured
- [ ] Dependencies updated and scanned for vulnerabilities

### Security Headers

Add security headers to your reverse proxy (nginx, Apache, etc.):

```nginx
# nginx example
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Content-Security-Policy "default-src 'self'" always;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
```

### Docker Deployment

If using Docker:

```dockerfile
# Use non-root user
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
USER appuser

# Don't copy .env files
# Use secrets or environment variables instead

# Set secure defaults
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
```

### Regular Maintenance

- [ ] Weekly dependency updates
- [ ] Monthly security scans
- [ ] Quarterly penetration testing
- [ ] Regular backup testing
- [ ] API key rotation schedule
- [ ] Review access logs
- [ ] Update SSL/TLS certificates

---

## Incident Response

### If API Keys are Compromised

1. **Immediately revoke** the compromised key
2. **Generate new key** and update in secrets manager
3. **Review logs** for unauthorized access
4. **Assess damage** and data exposure
5. **Update all systems** with new key
6. **Notify users** if data was accessed

### If Database is Compromised

1. **Isolate** the database
2. **Change all credentials**
3. **Review audit logs**
4. **Assess data exposure**
5. **Restore from clean backup** if necessary
6. **Implement additional security measures**
7. **Document incident** and lessons learned

---

## Security Contacts

For security issues:
- **Report vulnerabilities:** [Create private security advisory on GitHub]
- **Critical issues:** [Contact maintainer directly]

---

## Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [FastAPI Security Best Practices](https://fastapi.tiangolo.com/tutorial/security/)
- [MongoDB Security Checklist](https://docs.mongodb.com/manual/administration/security-checklist/)
- [OpenAI API Best Practices](https://platform.openai.com/docs/guides/safety-best-practices)

---

**Last Updated:** 2026-02-02  
**Version:** 1.0
