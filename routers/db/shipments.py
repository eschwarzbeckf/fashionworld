from fastapi import APIRouter, HTTPException, status,Depends
from database import get_db, engine
from sqlalchemy.orm import Session
from sqlalchemy import update
from typing import Annotated
import models
import pandas as pd
import numpy as np
import pickle
from typing import List

with open(r'C:\Users\esteb\Projects\MBD\Capgemin\app\routers\machinelearning\lr.pkl','rb') as f:
    model = pickle.load(f)


db_dependency = Annotated[Session, Depends(get_db)]

router = APIRouter(
    prefix="/api/db/shipments"
    )

@router.put("/costs", status_code=status.HTTP_202_ACCEPTED)
def calculate_rework_costs(db: db_dependency):
    df = pd.read_sql("""
        SELECT pd.*,pa.*,p.*, a.cost_impact 
        FROM products_defects as pd 
        LEFT JOIN audits as a on pd.uuid = a.package_uuid 
        JOIN products as p on p.product_id = pd.product_id 
        JOIN packaging as pa on pa.product_id = pd.product_id
        WHERE a.cost_impact IS NULL
        """,con=engine
        )
    
    x = df[['issue','garment_type','material','size','collection','weight']].rename(columns={"issue":"issue_description"})
    cost_log = model.predict(x)
    cost = np.round(10**cost_log,2)
    df["cost_impact"] = cost
    updated_costs = df[["uuid","cost_impact"]].to_dict(orient='records')

    db.execute(
        update(models.ProductsDefects),
        updated_costs
    )
    db.commit()

    return {"Records Updated Succesffully"}


@router.put("/ship", status_code=status.HTTP_202_ACCEPTED)
def ship_orders(orders:List[str],db: db_dependency):
    if orders is None:
        raise HTTPException(status_code=400, detail="No order was provided")
    
    order_db = ""
    for order in orders:
        order_db += f"\"{order}\"" if order_db == "" else f",\"{order}\""

    df = pd.read_sql(f"""
    SELECT pd.*,pa.*,p.*, a.cost_impact 
    FROM products_defects as pd 
    LEFT JOIN audits as a on pd.uuid = a.package_uuid 
    JOIN products as p on p.product_id = pd.product_id 
    JOIN packaging as pa on pa.product_id = pd.product_id
    JOIN receptions as r on r.package_uui = pd.uuid
    WHERE a.cost_impact IS NULL AND r.order_id IN ({order_db})
    """,con=engine)
    
    x = df[['issue','garment_type','material','size','collection','weight']].rename(columns={"issue":"issue_description"})
    cost_log = model.predict(x)
    cost = np.round(10**cost_log,2)
    df["cost_impact"] = cost
    updated_costs = df[["uuid","cost_impact"]].to_dict(orient='records')

    db.execute(
        update(models.ProductsDefects),
        updated_costs
    )
    db.commit()

    return {"Records Updated Succesffully"}

