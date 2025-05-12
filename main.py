from fastapi import FastAPI, HTTPException, Depends, status
from routers.llm import llm
from routers.db import orders, products, packaging, suppliers, receptions
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
metadata.create_all(bind=engine)
product_id = Sequence('product_id_seq', start=1, increment=1, metadata=metadata)
supplier_id = Sequence('supplier_id_seq', start=1, increment=1, metadata=metadata)
order_id = Sequence('order_id_seq', start=1, increment=1, metadata=metadata)
audit_id = Sequence('audit_id_seq', start=1, increment=1, metadata=metadata)
reception_id = Sequence('reception_id_seq', start=1, increment=1, metadata=metadata)

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
app.include_router(suppliers.router)
app.include_router(packaging.router)
app.include_router(receptions.router)

    


@app.get("/")
def read_root():
    return {"message": "Your app is running!"}