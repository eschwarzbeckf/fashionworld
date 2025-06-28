from fastapi import APIRouter, status, HTTPException, Depends
from sqlalchemy.orm import Session
from database import get_db
from validations import InventoryItem
from database import engine
import models
from typing import List, Annotated
import pandas as pd
import pickle
import numpy as np


with open(r'C:\Users\esteb\Projects\MBD\Capgemin\app\routers\machinelearning\lr.pkl','rb') as f:
    model = pickle.load(f)

router = APIRouter(
    prefix="/api/db/inventory"
)

db_dependency = Annotated[Session, Depends(get_db)]

@router.post("/add", status_code=status.HTTP_201_CREATED)
def add_to_inventory(items: List[InventoryItem], db: db_dependency):
    if not items:
        raise HTTPException(status_code=400, detail="No inventory items provided.")

    items = list(set(items))  # Remove duplicates
    inventory = []
    
    audits_db = db.query(models.Audits).filter(models.Audits.audit_plan_name.in_([item.audit_plan_name for item in items]))

    orders = ""
    for item in items:
        orders += f"\"{item.order_id}\"" if orders == "" else f",\"{item.order_id}\""
    
    receptions_df = pd.read_sql(f"""
                            SELECT r.*,p.garment_type,p.material,p.size,p.collection,s.name, pa.suggested_folding_method, pa.suggested_layout, pa.revision
                            FROM receptions as r 
                            LEFT JOIN products as p on p.product_id = r.product_id
                            LEFT JOIN suppliers_products as sp on sp.product_id = r.product_id
                            LEFT JOIN suppliers as s on s.supplier_id = sp.supplier_id
                            LEFT JOIN (select p1.product_id,p1.suggested_folding_method,p1.suggested_quantity,p1.suggested_layout,p1.revision from packaging as p1 where p1.revision = (select max(p2.revision) from packaging as p2 where p2.product_id = p1.product_id)) as pa on p.product_id = pa.product_id
                            WHERE r.order_id IN ({orders})
                            """, con=engine)
    audits_df = pd.read_sql(audits_db.statement, con=engine)
    
    x = receptions_df.rename(columns={"issue":"issue_description"})
    x = x[['name', 'issue_description', 'garment_type', 'material','suggested_folding_method', 'suggested_layout', 'size', 'collection']]
    cost_log = model.predict(x)
    cost = np.round(10 ** cost_log, 2)
    receptions_df['cost'] = cost
    idx = receptions_df[receptions_df['package_uuid'].isin(audits_df['package_uuid'])].index
    receptions_df.loc[idx, 'cost'] = 0.0
    order_audit_plan = {item.order_id:item.audit_plan_name for item in items}
    order_status_dict = {item.order_id:item.order_status for item in items}
        
    for reception in receptions_df.itertuples(index=False):
        inventory.append(models.Inventory(
            audit_plan_name = order_audit_plan[reception.order_id],
            order_id = reception.order_id,
            order_status = order_status_dict[reception.order_id],
            uuid = reception.package_uuid,
            product_id = reception.product_id,
            rework_cost = reception.cost
        ))
    
    if len(inventory) > 0:
        db.add_all(inventory)
    
    db.commit()

    return {"message": "Inventory items added successfully", "count": len(inventory)}