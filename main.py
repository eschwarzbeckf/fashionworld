from fastapi import FastAPI, HTTPException, Depends, status
from routers.llm import llm
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

@app.post("/api/db/add_products", status_code=status.HTTP_201_CREATED)
async def add_products(products: List[Product], db: db_dependency):
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

@app.post("/api/db/add_suppliers", status_code=status.HTTP_201_CREATED)
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

@app.post("/api/db/assign_supplier_product", status_code=status.HTTP_201_CREATED)
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

@app.post("/api/db/orders/place", status_code=status.HTTP_201_CREATED)
async def place_order(orders: List[PlaceOrder], db: db_dependency):
    if not orders:
        raise HTTPException(status_code=400, detail="No order information provided.")
    
    order_ids = []
    db_orders = []
    for order in orders:
        next_id_val = db.execute(select(order_id.next_value())).scalar_one()
        generated_order_id = f"ORD{next_id_val:05d}"
        order.order_id = generated_order_id
        for i,item in enumerate(order.items):
            db_orders.append(models.Orders(
                order_id=order.order_id,
                item_no=i+1,
                product_id=item.product_id,
                boxes_ordered=item.boxes_ordered,
                order_placed_date=order.order_placed_date
                )
            )

    db.add_all(db_orders)
    db.commit()
    return {"message": "Order placed successfully", "order_id": order_ids, "order": orders}

@app.put("/api/db/orders/confirm", status_code=status.HTTP_202_ACCEPTED)
async def confirm_order(orders: List[ConfirmOrder], db:db_dependency):
    if orders is None:
        raise HTTPException(status_code=400, detail="No order information provided.")
    
    db_orders = []
    not_found = []
    for order in orders:
        print(f"\n\n\n{order.order_id}\n\n\n")
        db_order = db.query(models.Orders).filter(models.Orders.order_id==order.order_id).all()
        if db_order:
            for order_update in db_order:
                db_orders.append(order_update.order_id)
                order_update.order_confirmed_date = order.order_confirmed_date
                order_update.order_status = order.order_status
                order_update.supplier_order_id = order.supplier_order_id
                order_update.last_updated = order.last_updated
        else:
            not_found.append(order.order_id)

    db.commit()
    return {"message":"Orders Confirmed", "orders_id":db_orders, "orders_not_found":not_found}

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