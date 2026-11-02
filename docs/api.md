# API guide

FastAPI publishes the full OpenAPI schema at `/openapi.json` and interactive docs at `/docs`.

| Group | Routes | Access |
|---|---|---|
| Health | `GET /health` | Public |
| Auth | `POST /api/auth/register`, `/login`, `/logout`; `GET /me` | Public / bearer |
| Complaints | `POST /api/complaints`; `GET /api/complaints`; `GET /api/complaints/{id}` | Citizen submission; ownership or department scope on reads |
| Workflow | `POST /api/complaints/{id}/update-status`; `/reopen`; `/feedback`; `/attachments` | Role and owner checks |
| AI | `/api/ai/classify-complaint`, `/detect-duplicates`, `/assistant`, `/translate`, `/analyze-image` | Local baseline; image analysis authenticated |
| Admin | `GET /api/admin/dashboard`; `POST /api/admin/complaints/{id}/assign` | Authorized official roles |
| Schemes | `GET /api/schemes`; `POST /api/schemes/check-eligibility` | Public demonstration data |
| GIS | `/api/gis/complaints`, `/heatmap` | Authenticated, complaint-scope filtering |
| Notifications | `GET /api/notifications`; `PATCH /api/notifications/{id}/read` | Own account |
| Blockchain | `/api/blockchain/records/{complaint_id}`, `/verify/{record_id}` | Complaint-scope access |
| Reports | `/api/reports/complaints`, `/export` | Manager / administrator |

The API currently uses schema creation at startup; Alembic migration scripts have not yet been generated. File downloads are intentionally not public. Upload metadata is private and the prototype does not expose a download endpoint.
