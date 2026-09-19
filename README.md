# Veritas Grid ⚖️
### Sovereign Multi-Tenant Anonymous Whistleblowing & Risk Isolation Core

Veritas Grid is a lean, self-hostable anonymous intake gateway designed for organizations that need controlled whistleblowing, civic reporting, and tenant-isolated risk processing without building their entire intake layer around a large cloud platform.

It provides a unified ingestion layer for:

- Web-based anonymous reporting
- Twilio WhatsApp intake
- Africa's Talking SMS intake
- Tenant-isolated case routing
- Identity-data sanitization
- Cryptographic tracking tokens
- Sanitized audit ledgers
- Operational risk classification

The system is designed to run on organization-controlled infrastructure, allowing deployments that minimize dependence on external cloud storage and third-party data-processing APIs.

---

## Core Architecture

Veritas Grid is built around three principles:

1. **Protect the identity of the reporting party**
2. **Isolate organizational data between tenants**
3. **Keep core processing under operator control**

The architecture deliberately keeps the primary intake-processing path local to the deployment environment rather than sending report contents to external AI-processing services.

---

## 🛡️ 1. Anonymous Intake & Identity Sanitization

Anonymous reporting is only useful when the system minimizes unnecessary exposure of identifying information.

### Local identity sanitization

Incoming report text passes through the gateway's identity-scrubbing layer before the report is committed to the local ledger.

The scrubber is designed to identify and remove supported forms of identifying information, including patterns such as:

- Names
- Telephone numbers
- Email addresses
- Corporate email addresses
- Other configured identity-bearing patterns

This processing occurs inside the gateway rather than requiring report contents to be sent to an external AI service.

> Identity sanitization reduces the amount of identifying information retained by the application. It should not be interpreted as a guarantee that a reporting party is technically untraceable across every network, carrier, browser, device, or infrastructure layer.

### One-way tracking tokens

Each accepted report receives a cryptographic tracking identifier based on HMAC-SHA256.

The token allows the system to reference a submission without exposing the sender's identity through the token itself.

Because the token is derived using a server-side secret rather than reversible encryption, the identifier is not intended to contain recoverable sender information.

---

## 🏢 2. Multi-Tenant Risk Isolation

Veritas Grid supports isolated organizational workspaces through tenant-aware ingestion and authorization.

Each organization is represented by a tenant context and associated deployment tier.

Example tenants include:

- Government agencies
- NGOs
- Law firms
- Commercial organizations
- Enterprise workspaces

### Tenant authorization

Tenant access is controlled through cryptographically verified tenant credentials.

The backend determines the authorized tenant before returning dashboard data.

This is important because UI-level filtering is not considered a security boundary.

The dashboard receives only the records that the backend has already authorized for the current tenant.

### Tenant-isolated audit records

Each report is associated with its target tenant and processed into the corresponding operational ledger.

The architecture is designed to prevent one tenant's authorized dashboard context from exposing another tenant's records.

---

## 🏛️ 3. Government & Civic Reporting

Veritas Grid can also operate as a lightweight civic reporting infrastructure for public institutions.

Government deployments can receive reports through multiple channels while maintaining a consistent internal processing model.

Supported intake paths include:

- Web forms
- SMS
- WhatsApp

This allows reporting infrastructure to remain accessible in environments where users may have limited bandwidth or older mobile devices.

The deployment model can be operated on organization-controlled infrastructure rather than requiring the report database itself to reside in a public cloud environment.

---

## ⚙️ Technical Architecture

### Embedded SQLite WAL Ledger

The system uses SQLite with Write-Ahead Logging (WAL) for its local ledger.

WAL allows readers to continue accessing the database while writes are being committed, improving concurrency for the application's read-heavy dashboard workloads.

The database remains embedded within the application deployment rather than requiring a separate database server.

### Local processing pipeline

The core processing pipeline is intentionally lightweight:

```text
Web / SMS / WhatsApp
        │
        ▼
   Intake Gateway
        │
        ▼
Identity Sanitization
        │
        ▼
Tenant Resolution
        │
        ▼
Risk / Category Processing
        │
        ▼
Cryptographic Tracking Token
        │
        ▼
Local SQLite Ledger
        │
        ▼
Authorized Tenant Dashboard