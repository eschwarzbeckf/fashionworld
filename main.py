from fastapi import FastAPI, HTTPException, Depends, status
import ollama
from validations import ModelandText, SupplierProducts, Product, Supplier, Item
import models
from database import engine, get_db, SessionLocal
from sqlalchemy.orm import Session
from sqlalchemy import Sequence, select
from typing import Annotated, List
from script import add_initial_data
from contextlib import asynccontextmanager

ollama_client = ollama.Client(host="http://localhost:11434")


metadata = models.Base.metadata
metadata.drop_all(bind=engine) #Drops all tables in the database, if they exists (comment this if want to keep data)
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
    db: Session = SessionLocal()
    add_initial_data(db,supplier_id) # Add data from CSV
    yield
    # Code to run on shutdown (optional)
    print("Application shutdown.")
    db.close()


app= FastAPI(lifespan=lifespan)

@app.post("/api/ollama/read_email", status_code=status.HTTP_200_OK)
async def read_email(model_and_text: ModelandText):
    """
    """
    model_name = model_and_text.model_name
    text = model_and_text.text

    prompt = f"""
        You are an AI assistant tasked with extracting structured data from emails sent by textile providers. 
        Read the following email content carefully and extract the relevant information about the textile products mentioned. 
        Format the extracted information strictly as a JSON object according to the structure provided below.

        Look for the supplier name, garment type, material, size, collection, weight, and weight units.
        The supplier name is mentioned either at the signature of the email or at the beginning of the email, or in the subject line.
        The email may contain information about multiple garments, and you should extract details for each garment separately.
        The garments may include jackets, shorts, sweaters, skirts, shirts, t-shirts, coats, pants, dresses, suits, blouses, and hoodies.
        The materials may include cotton, polyester, silk, linen, wool, and denim.
        The sizes may include s, m, l, x, and xxl.
        The collections may include summer, winter, fall, and spring.
        The weight may be mentioned in grams or other units, and you should extract the weight value and its unit.

        If there is any null value set the null_values to true.
        If all the information can be extracted set the null_values to false.

        **Desired JSON Structure:**
        ```json
        {{
            "supplier": "Supplier Name from Email",
            "data":[{{
                "garment_type": "extracted garment type",
                "material": "extracted material",
                "size": "extracted size or null",
                "collection": "extracted collection or null",
                "weight_units": "extracted weight units or 'kg'",
                "weight": extracted weight (number)
            }},
            "null_values": false
            // ... repeat for each garment mentioned in the email
            ]
        }}

        --- START OF EMAIL CONTENT ---
        {text}
        --- END OF EMAIL CONTENT ---
    """
    if not model_name:
        raise HTTPException(status_code=400, detail="Model name is required.")
    
    if text:
        messages = [{"role":"system","content": "You are a helpful assistant."}, {"role": "user", "content": prompt}]
        response = ollama_client.chat(
            model=model_name, 
            messages=messages,
            stream=False,
            format=SupplierProducts.model_json_schema(),
            options={
                "temperature":0.0
                }
            )
        return response
    else:
        raise HTTPException(status_code=400, detail="Text is required.")

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

@app.post("/api/db/order/place", status_code=status.HTTP_201_CREATED)
async def place_order(order: List[Item], db: db_dependency):
    if not order:
        raise HTTPException(status_code=400, detail="No order information provided.")
    
    order_ids = []
    db_orders = []
    next_id_val = db.execute(select(order_id.next_value())).scalar_one()
    generated_order_id = f"ORD{next_id_val:05d}"
    order_ids.append(generated_order_id)
    for item in order:
        print(f"\n\n{item}\n\n")
        item.order_id = generated_order_id
        db_orders.append(models.Orders(**item.model_dump()))

    db.add_all(db_orders)
    db.commit()
    return {"message": "Order placed successfully", "order_id": order_ids, "order": order}

@app.get("/")
def read_root():
    return {"message": "Your app is running!"}