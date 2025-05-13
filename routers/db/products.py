from fastapi import APIRouter, status, HTTPException, Depends
from sqlalchemy import select, Sequence
from sqlalchemy.orm import Session
from database import metadata, get_db
from validations import Product
from typing import List, Annotated
import models
from models import product_id


db_dependency = Annotated[Session, Depends(get_db)]

router = APIRouter(
    prefix="/api/db/products"
)


@router.post("/add_products", status_code=status.HTTP_201_CREATED)
async def add_products(products: List[Product], db: db_dependency):
    if not products:
        raise HTTPException(status_code=400, detail="No products provided.")
    
    products_ids = []
    db_products = []
    for product in products:
        next_id_val = db.execute(select(product_id.next_value())).scalar_one()
        generated_product_id = f"PRD{next_id_val:05d}"
        product.product_id = generated_product_id
        products_ids.append(product.product_id)
        db_products.append(models.Products(**product.model_dump()))


    db.add_all(db_products)
    db.commit()
    return {"message": "Products added successfully", "products_ids":products_ids ,"products_added": products}