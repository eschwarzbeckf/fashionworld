from fastapi import APIRouter, status, HTTPException
import models
from validations import UpdatePackage
from typing import List
from sqlalchemy.orm import Session

router = APIRouter(
    prefix="/api/db/packaging"
)

@router.put("/update", status_code=status.HTTP_202_ACCEPTED)
async def update_packaging(packaging:List[UpdatePackage], db:Session):
    if not packaging:
        raise HTTPException(status_code=400, detail="No package information provided")
    
    not_found = []
    changed_products = []
    changed = False
    for package in packaging:
        db_package = db.query(models.Packaging).filter(models.Packaging.product_id == package.product_id).scalar()
        if db_package is None:
            not_found.append(package.product_id)
            continue
        
        revision = db_package.revision        

        if package.new_method:
            db_package.suggested_folding_method = package.new_method
            db_package.last_updated_date = package.last_updated
            changed = True
        
        if package.new_layout:
            db_package.suggested_layout = package.new_layout
            db_package.last_updated_date = package.last_updated
            changed = True

        if package.new_suggested_quantity:
            db_package.suggested_quantity = package.new_suggested_quantity
            db_package.last_updated_date = package.last_updated
            changed = True

        if changed:
            revision += 1
            db_package.revision = revision
            db.commit()
            return {"message": "Changes applied", "changed products":changed_products, "products not found":not_found}
        
        db.close()
        return {"message": "No changes", "products not found":not_found}