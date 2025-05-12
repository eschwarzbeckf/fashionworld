from fastapi import APIRouter, status, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from validations import Product
from typing import List
import models
from main import product_id

router = APIRouter(
    prefix="/api/db/products"
)


@router.post("/add_products", status_code=status.HTTP_201_CREATED)
async def add_products(products: List[Product], db: Session):
    if not products:
        raise HTTPException(status_code=400, detail="No products provided.")
    
    products_ids = []
    db_products = []
    for product in products:
        print(product)
        next_id_val = db.execute(select(product_id.next_value())).scalar_one()
        generated_product_id = f"PRD{next_id_val:05d}"
        product.product_id = generated_product_id
        products_ids.append(product.product_id)
        db_products.append(models.Products(**product.model_dump()))


    db.add_all(db_products)
    db.commit()
    return {"message": "Products added successfully", "products_ids":products_ids ,"products_added": products}