# 🚀 ConjoinAI Backend - Migration Workflow Guide

## 📋 **NEVER Face Migration Issues Again!**

This guide ensures **100% reliable database migrations** for all team members, production deployments, and local development.

---

## 🔧 **Prerequisites**

### **Environment Setup**
```bash
# Activate conda environment
conda activate conjoin

# Verify PostgreSQL connection
docker ps | grep postgres
```

### **Required Environment Variables**
```bash
# In your .env file
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_SERVER=localhost
POSTGRES_DB=conjoin_ai
```

---

## 📚 **Core Migration Commands**

### **1. Check Current Migration State**
```bash
# Always run this FIRST to see where you are
alembic current

# See migration history
alembic history --verbose
```

### **2. Create New Migration**
```bash
# For schema changes (recommended approach)
alembic revision --autogenerate -m "descriptive_change_name"

# For manual migrations (advanced)
alembic revision -m "manual_change_name"
```

### **3. Apply Migrations**
```bash
# Apply all pending migrations
alembic upgrade head

# Apply specific migration
alembic upgrade <revision_id>

# See what will be applied (dry-run)
alembic upgrade head --sql
```

### **4. Rollback Migrations**
```bash
# Rollback one migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade <revision_id>

# Rollback to base (DANGEROUS!)
alembic downgrade base
```

---

## 🏗️ **Development Workflow**

### **Step 1: Before Making Schema Changes**
```bash
# 1. Check current state
alembic current

# 2. Pull latest code
git pull origin main

# 3. Apply any pending migrations
alembic upgrade head
```

### **Step 2: Make Your Schema Changes**
```python
# Edit files in app/postgres/schema/
# Example: Add new column to existing model

class User(Base):
    __tablename__ = "User"
    
    # Existing columns...
    new_column = Column(String(255), nullable=True)  # New column
```

### **Step 3: Generate Migration**
```bash
# Auto-generate migration from schema changes
alembic revision --autogenerate -m "add_new_column_to_user"

# Review the generated migration file
# Edit if needed for complex changes
```

### **Step 4: Test Migration**
```bash
# Apply migration locally
alembic upgrade head

# Test your application
python app/main.py

# If issues, rollback and fix
alembic downgrade -1
```

### **Step 5: Commit and Push**
```bash
git add alembic/versions/
git commit -m "feat: add new column to user table"
git push origin feature-branch
```

---

## 🔄 **Production Deployment**

### **Safe Production Migration Steps**

1. **Pre-deployment Check**
   ```bash
   # Check current production state
   alembic current
   
   # See what will be applied
   alembic upgrade head --sql > migration_plan.sql
   ```

2. **Backup Database (CRITICAL!)**
   ```bash
   # Docker backup
   docker exec conjoin_postgres pg_dump -U postgres conjoin_ai > backup_$(date +%Y%m%d_%H%M%S).sql
   
   # Or direct backup
   pg_dump -h localhost -U postgres conjoin_ai > backup_$(date +%Y%m%d_%H%M%S).sql
   ```

3. **Apply Migrations**
   ```bash
   # Apply migrations
   alembic upgrade head
   
   # Verify success
   alembic current
   ```

4. **Rollback Plan (If Issues)**
   ```bash
   # Quick rollback
   alembic downgrade -1
   
   # Or restore from backup
   docker exec -i conjoin_postgres psql -U postgres conjoin_ai < backup_file.sql
   ```

---

## 🛠️ **Handling Manual Changes**

### **When You've Made Manual Database Changes**

If you've already created tables/columns manually (like we did with `daily_wellness_metrics`):

```bash
# 1. Create migration that matches your manual changes
alembic revision -m "add_wellness_metrics_table"

# 2. Edit the migration file to match what you created
# 3. Mark migration as applied (since table already exists)
alembic stamp <revision_id>

# 4. Continue with normal workflow
alembic upgrade head
```

### **Example: Marking Manual Changes as Applied**
```bash
# If you manually created wellness table
alembic stamp 4957533a9ab9

# If you manually added is_positive column  
alembic stamp 882a637ec342
```

---

## 🔍 **Troubleshooting Common Issues**

### **"Table Already Exists" Error**
```bash
# Solution: Mark the migration as already applied
alembic stamp <revision_id>
```

### **"Column Already Exists" Error**
```bash
# Solution: Mark the migration as already applied
alembic stamp <revision_id>
```

### **"KeyError: 'revision_id'" Error**
```bash
# Solution: Reset migration chain (ADVANCED)
# 1. Backup current database
# 2. Clear alembic_version table
# 3. Create new baseline migration
alembic revision --autogenerate -m "baseline_migration"
alembic stamp head
```

### **Migration Chain Broken**
```bash
# Nuclear option (use with caution):
# 1. Backup database
pg_dump -h localhost -U postgres conjoin_ai > backup.sql

# 2. Reset Alembic completely
rm alembic/versions/*.py
docker exec conjoin_postgres psql -U postgres conjoin_ai -c "DELETE FROM alembic_version;"

# 3. Create new baseline
alembic revision --autogenerate -m "baseline_current_schema"
alembic stamp head
```

---

## 📊 **Database Inspection Commands**

### **Docker Commands**
```bash
# Connect to PostgreSQL in Docker
docker exec -it conjoin_postgres psql -U postgres conjoin_ai

# Check table exists
docker exec conjoin_postgres psql -U postgres conjoin_ai -c "\\dt"

# Describe table structure
docker exec conjoin_postgres psql -U postgres conjoin_ai -c "\\d daily_wellness_metrics"

# Check data
docker exec conjoin_postgres psql -U postgres conjoin_ai -c "SELECT * FROM daily_wellness_metrics LIMIT 5;"
```

### **Direct PostgreSQL Commands**
```bash
# Connect directly (if not using Docker)
psql -h localhost -U postgres conjoin_ai

# List tables
\\dt

# Describe table
\\d table_name

# Check migration status
SELECT * FROM alembic_version;
```

---

## 🎯 **Team Guidelines**

### **DO's**
✅ Always check `alembic current` before starting work  
✅ Use `--autogenerate` for schema changes  
✅ Review generated migrations before applying  
✅ Test migrations locally before pushing  
✅ Backup production before applying migrations  
✅ Use descriptive migration names  
✅ Document complex migrations  

### **DON'Ts**
❌ Never edit applied migration files  
❌ Never apply migrations directly in production without testing  
❌ Never skip migration files  
❌ Never manually edit database in production without creating migration  
❌ Never force push migration changes  
❌ Never ignore migration conflicts  

---

## 🚨 **Emergency Procedures**

### **If Production Database is Broken**
1. **Immediate Response**
   ```bash
   # Stop application
   docker-compose down
   
   # Restore from backup
   docker exec -i conjoin_postgres psql -U postgres conjoin_ai < latest_backup.sql
   
   # Restart application
   docker-compose up -d
   ```

2. **Root Cause Analysis**
   ```bash
   # Check what migrations were applied
   docker exec conjoin_postgres psql -U postgres conjoin_ai -c "SELECT * FROM alembic_version;"
   
   # Review recent migration files
   ls -la alembic/versions/ | head -10
   ```

3. **Fix and Redeploy**
   ```bash
   # Fix migration issue locally
   # Test thoroughly
   # Apply to production with extra caution
   ```

---

## 📝 **Migration File Best Practices**

### **Good Migration Example**
```python
"""add_user_email_verification

Revision ID: abc123def456
Revises: previous_revision
Create Date: 2025-01-17 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'abc123def456'
down_revision = 'previous_revision'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add email_verified column
    op.add_column('User', sa.Column('email_verified', sa.Boolean(), 
                                   nullable=False, server_default='false'))
    
    # Create index for faster queries
    op.create_index('ix_user_email_verified', 'User', ['email_verified'])

def downgrade() -> None:
    # Remove index first
    op.drop_index('ix_user_email_verified', 'User')
    
    # Remove column
    op.drop_column('User', 'email_verified')
```

### **Migration Naming Convention**
```
Format: <timestamp>_<descriptive_name>.py

Examples:
- 20250117_100000_add_user_email_verification.py
- 20250117_110000_create_wellness_metrics_table.py  
- 20250117_120000_add_card_completion_is_positive.py
```

---

## 🔄 **Local Development Setup**

### **Fresh Local Setup**
```bash
# 1. Clone repository
git clone <repo-url>
cd conjoin-backend

# 2. Setup environment
conda create -n conjoin python=3.11
conda activate conjoin
pip install -r requirements.txt

# 3. Setup database
docker-compose up -d postgres

# 4. Apply all migrations
alembic upgrade head

# 5. Verify setup
alembic current
python app/main.py
```

### **Reset Local Database**
```bash
# Complete reset (DESTRUCTIVE!)
docker-compose down -v
docker-compose up -d postgres
alembic upgrade head
```

---

## 📞 **Support & Contacts**

### **When to Ask for Help**
- Migration chain is broken
- Production deployment failed
- Unsure about complex schema changes
- Need to coordinate large migrations

### **Emergency Contacts**
- **Database Issues**: [Contact Info]
- **DevOps Support**: [Contact Info]  
- **Lead Developer**: [Contact Info]

---

## 📈 **Success Metrics**

### **How to Know It's Working**
✅ `alembic current` shows expected revision  
✅ `alembic upgrade head` runs without errors  
✅ Application starts successfully  
✅ Database queries work as expected  
✅ Tests pass after migration  

---

## 🔐 **Security Notes**

- Never commit database credentials
- Use environment variables for sensitive data
- Backup before major changes
- Test migrations on staging first
- Have rollback plan ready

---

## 📚 **Additional Resources**

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

---

**Remember: When in doubt, backup first! 🛡️**
