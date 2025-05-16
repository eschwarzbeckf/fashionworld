from fastapi import APIRouter, status, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Annotated
from models import audit_id
from database import get_db
from validations import ItemToAudit
from sqlalchemy import select
import models
from datetime import datetime
import pickle
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.linear_model import LinearRegression
from sklearn.compose import make_column_selector, make_column_transformer, ColumnTransformer
from sklearn.preprocessing import OneHotEncoder

with open(r'C:\Users\esteb\Projects\MBD\Capgemin\app\routers\machinelearning\lr.pkl','rb') as f:
    model = pickle.load(f)

router = APIRouter(
    prefix="/api/db/audits"
)

db_dependency = Annotated[Session, Depends(get_db)]

@router.post("/create", status_code=status.HTTP_201_CREATED)
async def create_audit(items: List[ItemToAudit], db:db_dependency):
    if items is None:
        raise HTTPException(status_code=400, detail="No order information provided.")

    audit_db = []
    for item in items:
        issue, = db.execute(
            select(
                models.ProductsDefects.issue
            ).where(
                models.ProductsDefects.uuid == item.package_uuid
            )
        ).first()
        
        next_id_val = db.execute(select(audit_id.next_value())).scalar_one()
        generated_audit_id = f"AUD{next_id_val:08d}"
        audit_db.append(
            models.Audits(
                audit_id=generated_audit_id,
                reception_id=item.reception_id,
                product_id=item.product_id,
                package_uuid=item.package_uuid,
                created_date=datetime.now(),
                packaging_quality=item.package_quality,
                issue_description=issue,
                audit_date=datetime.now()
            )
        )
    
    db.add_all(audit_db)
    db.commit()

    return {"message":"Audit created","audits":audit_db}
        
        

