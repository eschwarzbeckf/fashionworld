from fastapi import FastAPI, HTTPException, Depends, status
from routers.llm import llm
from routers.db import orders, products
from validations import SupplierProducts, Product, Supplier, PlaceOrder, ConfirmOrder, RecievedPackage, UpdatePackage
import models
from database import engine, get_db, SessionLocal
from sqlalchemy.orm import Session
from sqlalchemy import Sequence, select
from typing import Annotated, List
from script import add_initial_data
from contextlib import asynccontextmanager


metadata = models.Base.metadata
# metadata.drop_all(bind=engine) #Drops all tables in the database, if they exists (comment this if want to keep data)
product_id = Sequence('product_id_seq', start=1, increment=1, metadata=metadata)
supplier_id = Sequence('supplier_id_seq', start=1, increment=1, metadata=metadata)
order_id = Sequence('order_id_seq', start=1, increment=1, metadata=metadata)
audit_id = Sequence('audit_id_seq', start=1, increment=1, metadata=metadata)
reception_id = Sequence('reception_id_seq', start=1, increment=1, metadata=metadata)
metadata.create_all(bind=engine)

db_dependency = Annotated[Session, Depends(get_db)]

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Code to run on startup
    # db: Session = SessionLocal()
    # add_initial_data(db,supplier_id) # Add data from CSV
    #add scorecard and then incidents
    # db.close()
    yield
    # Code to run on shutdown (optional)
    print("Application shutdown.")


app= FastAPI(lifespan=lifespan)

app.include_router(llm.router)
app.include_router(orders.router)
app.include_router(products.router)

@app.post("/api/db/suppliers/assign_supplier_product", status_code=status.HTTP_201_CREATED)
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

@app.post("api/db/receptions/deliveries", status_code=status.HTTP_200_OK)
async def package_recieved(deliveries: List[RecievedPackage], db:db_dependency):
    if deliveries is None:
        raise HTTPException(status_code=400, detail="No order information provided.")
    
    next_id_val = db.execute(select(reception_id.next_value())).scalar_one()
    generated_order_id = f"REC{next_id_val:08d}"
    reception_id.order_id = generated_order_id

@app.put("/api/db/packaging/update", status_code=status.HTTP_202_ACCEPTED)
async def update_packaging(packaging:List[UpdatePackage], db:db_dependency):
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

    


@app.get("/")
def read_root():
    return {"message": "Your app is running!"}