# Data model

Core SQLAlchemy tables are users, departments, complaints, complaint status history, private attachment metadata, notifications, and blockchain audit records. Complaint rows carry the citizen and department references, coordinates, priority rationale, and SLA deadline. The current bootstrap uses SQLite by default and supports a PostgreSQL URL. PostGIS geometry columns and Alembic history remain deployment work.
