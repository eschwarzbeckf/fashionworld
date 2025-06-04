from fastapi import FastAPI
from routers.llm import llm
from routers.db import orders, products, packaging, suppliers, receptions, audits, shipments
from database import engine, metadata
from script import add_initial_data, add_density_data, add_scorecard_data
from sqlalchemy.orm import Session
from database import SessionLocal
from contextlib import asynccontextmanager
from models import supplier_id, density_id
import uvicorn

# metadata.drop_all(bind=engine) #Drops all tables in the database, if they exists (comment this if want to keep data)
metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Code to run on startup
    # db: Session = SessionLocal()
    # add_initial_data(db,supplier_id) # Add data from CSV
    # add_density_data(db)
    # add_scorecard_data(db)
    # db.close()
    yield
    # Code to run on shutdown (optional)
    print("Application shutdown.")


app = FastAPI(lifespan=lifespan)

app.include_router(llm.router)
app.include_router(orders.router)
app.include_router(products.router)
app.include_router(suppliers.router)
app.include_router(packaging.router)
app.include_router(receptions.router)
app.include_router(audits.router)
app.include_router(shipments.router)

@app.get("/")
def read_root():
    return {"message": "Your app is running!"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)