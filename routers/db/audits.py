from fastapi import APIRouter, status, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Annotated
from models import audit_id
from database import get_db
from validations import ItemToAudit
from sqlalchemy import select
import models


router = APIRouter(
    prefix="/api/db/audits"
)

db_dependency = Annotated[Session, Depends(get_db)]

router.post("/create_audit", status_code=status.HTTP_201_CREATED)
async def create_audit(items: List[ItemToAudit], db:db_dependency):
    audit_db = []
    for item in items:
        next_id_val = db.execute(select(audit_id.next_value())).scalar_one()
        generated_audit_id = f"AUD{next_id_val:08d}"
        layout_of_product = db.query(models.Packaging).filter(models.Packaging.product_id == item.product_id).scalar()
        
