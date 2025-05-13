from fastapi import APIRouter, status, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Annotated
from models import audit_id
from database import get_db
from validations import ItemToAudit
from sqlalchemy import select
import models
from datetime import datetime


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
        packaging_db = db.execute(
            select(
                models.Packaging.revision,
                models.Packaging.suggested_folding_method,
                models.Packaging.suggested_layout,
                models.Packaging.suggested_quantity
            ).where(
                models.Packaging.product_id == item.product_id
            ).order_by(
                models.Packaging.revision.desc()
            )
        ).first()
        products_db = db.execute(
            select(
                models.Products.garment_type,
                models.Products.material,
                models.Products.collection,
                models.Products.weight,
                models.Products.size
            ).where(
                models.Products.product_id == item.product_id
            )
        ).first()
        revision,suggested_folding_method,suggested_layout,suggested_quantity = packaging_db
        garment_type,material,collection,weight,size = products_db

        next_id_val = db.execute(select(audit_id.next_value())).scalar_one()
        generated_audit_id = f"AUD{next_id_val:08d}"
        audit_db.append(
            models.Audits(
                audit_id=generated_audit_id,
                reception_id=item.reception_id,
                package_uuid=item.package_uuid,
                product_id=item.product_id,
                package_revision=revision,
                created_date=datetime.now(),
                suggested_folding_method=suggested_folding_method,
                suggested_quantity=suggested_quantity,
                suggested_layout=suggested_layout,
                garment_type=garment_type,
                material=material,
                collection=collection,
                weight=weight,
                packaging_quality=item.package_quality,
                size=size
            )
        )
    
    db.add_all(audit_db)
    db.commit()

    return {"message":"Audit created","audits":audit_db}
        
        

