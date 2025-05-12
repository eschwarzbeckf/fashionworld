from fastapi import APIRouter, status, HTTPException, Depends
from typing import List
from validations import Supplier, SupplierProducts
from sqlalchemy.orm import Session
from sqlalchemy import select,Sequence
from database import metadata, get_db
import models
from routers.db.products import add_products
from typing import Annotated

supplier_id = Sequence('supplier_id_seq', start=1, increment=1, metadata=metadata)

db_dependency = Annotated[Session, Depends(get_db)]

router = APIRouter(
    prefix="/api/db/suppliers"
    )

@router.post("/add_suppliers", status_code=status.HTTP_201_CREATED)
async def add_suppliers(suppliers: List[Supplier], db: db_dependency):
    if not suppliers:
        raise HTTPException(status_code=400, detail="No suppliers provided.")
    suppliers_ids = []
    db_suppliers = []
    suppliers_already_exists = []
    for supplier in suppliers:

        try:
            check_supplier_exists = db.query(models.Suppliers).filter(models.Suppliers.name == supplier.name).first()
            if check_supplier_exists:
                continue
            
            next_id_val = db.execute(select(supplier_id.next_value())).scalar_one()
            generated_supplier_id = f"SUP{next_id_val:05d}"
            supplier.supplier_id = generated_supplier_id
            suppliers_ids.append(supplier.supplier_id)
            db_suppliers.append(models.Suppliers(**supplier.model_dump()))
        except HTTPException:
            select_supplier = db.query(models.Suppliers).filter(models.Suppliers.name == supplier.name).first()
            suppliers_already_exists.append({"name":select_supplier.name,"supplier_id":select_supplier.supplier_id})
            continue

    db.add_all(db_suppliers)
    db.commit()
    return {"message": "Suppliers added successfully", "suppliers_ids": suppliers_ids, "suppliers_added": suppliers, "suppliers_already_exists": suppliers_already_exists}

@router.post("/assign_supplier_product", status_code=status.HTTP_201_CREATED)
async def add_supplier_product(info:List[SupplierProducts], db: db_dependency):
    if not info:
        raise HTTPException(status_code=400, detail="No supplier product information provided.")

    supplier_product_relation = []
    for supplier_product in info:
        try:
            if not supplier_product.supplier:
                raise HTTPException(status_code=400, detail="Supplier and product information are required.")
            elif not supplier_product.data:
                raise HTTPException(status_code=400, detail="Product information is required.")
            
            #Check if the supplier exists
            db_supplier = db.query(models.Suppliers).filter(models.Suppliers.name == supplier_product.supplier.name).first()
            if db_supplier is None:
                #If the supplier does not exist, add it to the database
                res = await add_suppliers([supplier_product.supplier], db)
                supplier_id = res["suppliers_ids"][0] #Get the first supplier_id from the response
            else:
                #If the supplier exists, get the supplier_id
                supplier_id = db_supplier.supplier_id #Get the supplier_id from the database
            
            #Add the products to the database
            res = await add_products(supplier_product.data, db)
            products_ids = res["products_ids"]
            
            for product_id in products_ids:
                #Create the relation between supplier and product
                supplier_product_relation.append(models.SuppliersProducts(product_id=product_id, supplier_id=supplier_id))
            
            #Commit the relation to the database
            db.add_all(supplier_product_relation)
            db.commit()
            
        except HTTPException as e:
            print(e.detail)
            continue
    return {"message": "Supplier product added successfully", "supplier_id":supplier_id, "products_ids": products_ids}
