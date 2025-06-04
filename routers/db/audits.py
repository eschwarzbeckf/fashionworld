from fastapi import APIRouter, status, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Annotated
from models import audit_id
from database import get_db, engine
from validations import AuditOrder, AuditPlan
from sqlalchemy import select, update
import models
from datetime import datetime
import pickle
import pandas as pd
from sklearn.compose import make_column_selector, make_column_transformer, ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.linear_model import LinearRegression
import random
from datetime import datetime
import numpy as np

with open(r'C:\Users\esteb\Projects\MBD\Capgemin\app\routers\machinelearning\lr.pkl','rb') as f:
    model = pickle.load(f)

router = APIRouter(
    prefix="/api/db/audits"
)

db_dependency = Annotated[Session, Depends(get_db)]

@router.post("/create", status_code=status.HTTP_201_CREATED)
async def create_audit(items: List[AuditOrder],audit_plan: AuditPlan, db:db_dependency,sampling:str="random"):
    if items is None:
        raise HTTPException(status_code=400, detail="No order information provided.")
    elif audit_plan is None:
        raise HTTPException(status_code=400, detail="No audit criteria provided")
    orders = ""
    results = {}
    failed_orders = []
    for item in items:
        orders += f"\"{item.order_id}\"" if orders == "" else f",\"{item.order_id}\""
        results[item.order_id]={"status":"pass","pass":[],"rejected":[],"unknown":[]}

    receptions = pd.read_sql_query(f"""
                                   SELECT r.*,o.item_no,p.garment_type,p.material,p.size,p.collection,p.weight 
                                   FROM receptions as r 
                                   JOIN orders as o ON o.order_id = r.order_id 
                                   JOIN products as p on p.product_id = r.product_id 
                                   WHERE r.order_id IN ({orders})
                                   """, con=engine)
    audit_name, audit_criterias, sampling, audit_quantity = audit_plan.model_dump().values()
    units_without_issues = 0
    units_with_issues = 0
    unknown_issue = 0
    audit_ended = False

    audit_db = []
    

    if sampling.lower() == "random":
        item_audits = receptions.sample(audit_quantity)
        item_audits = len(receptions) if len(item_audits) < audit_quantity else item_audits
    elif sampling.lower() == "model":
        pass

    uuids = ""
    
    for item in item_audits["package_uuid"].values:
        uuids += f"\"{item}\"" if uuids == "" else f",\"{item}\""

    all_reject_criterias = []
    for criteria in audit_criterias:
        all_reject_criterias += criteria["reject_categories"]

    products_issues_statuses = pd.read_sql_query(f"SELECT * FROM products_defects WHERE uuid IN ({uuids})",con=engine)
    item_audits = item_audits.set_index('package_uuid').join(products_issues_statuses.set_index('uuid'),rsuffix='_defects').rename(columns={"issue":"issue_description"})
    x = item_audits[['issue_description','garment_type','material','size','collection','weight']]
    cost_log = model.predict(x)
    cost = np.round(10**cost_log,2)
    item_audits["estimated_cost"] = cost
    item_audits.reset_index(inplace=True)
    
    for idx in item_audits.index:
        next_id_val = db.execute(select(audit_id.next_value())).scalar_one()
        generated_audit_id = f"AUD{next_id_val:08d}"
        audit_db.append(
            models.Audits(
                audit_id=generated_audit_id,
                audit_plan_name=audit_name,
                reception_id=item_audits.loc[idx,"reception_id"],
                product_id=item_audits.loc[idx,"product_id"],
                package_uuid=item_audits.loc[idx,"package_uuid"],
                created_date=datetime.now(),
                packaging_quality=item_audits.loc[idx,"package_quality"],
                issue_description=item_audits.loc[idx, "issue_description"],
                audit_date=datetime.now(),
                cost_impact=item_audits.loc[idx,"estimated_cost"]
            )
        )

        for criteria in audit_criterias:
            if item_audits.loc[idx,"issue_description"] in criteria["accept_categories"]:
                units_without_issues += 1
                results[item_audits.loc[idx,"order_id"]]["pass"].append(
                    {
                        "product_id":item_audits.loc[idx,"product_id"],
                        "uuid":item_audits.loc[idx,"package_uuid"],
                        "package_quality":item_audits.loc[idx,"package_quality"],
                        "issue":item_audits.loc[idx, "issue_description"],
                        "cost_impact":item_audits.loc[idx,"estimated_cost"]
                    }
                )
            
            elif item_audits.loc[idx,"issue_description"] in criteria["reject_categories"]:
                units_with_issues += 1
                results[item_audits.loc[idx,"order_id"]]["rejected"].append(
                    {
                        "product_id":item_audits.loc[idx,"product_id"],
                        "uuid":item_audits.loc[idx,"package_uuid"],
                        "package_quality":item_audits.loc[idx,"package_quality"],
                        "issue":item_audits.loc[idx, "issue_description"],
                        "cost_impact":item_audits.loc[idx,"estimated_cost"]
                    }
                )
            elif item_audits.loc[idx,"issue_description"] not in all_reject_criterias:
                unknown_issue += 1
                results[item_audits.loc[idx,"order_id"]]["unknown"].append(
                    {
                        "product_id":item_audits.loc[idx,"product_id"],
                        "uuid":item_audits.loc[idx,"package_uuid"],
                        "package_quality":item_audits.loc[idx,"package_quality"],
                        "issue":item_audits.loc[idx, "issue_description"],
                        "cost_impact":0.00
                    }
                )

            if criteria["accepted_quantity"] > 0:
                if units_with_issues > criteria["accepted_quantity"]:
                    audit_ended = True
                    results[item_audits.loc[idx,"order_id"]]["status"]=f"rejected reached threshold for {criteria["criteria_name"]}"
                    for idx in receptions[receptions["order_id"] == item_audits.loc[idx,"order_id"]].index:
                        failed_orders.append(
                            {
                                "order_id":receptions.loc[idx,"order_id"],
                                "item_no":receptions.loc[idx,"item_no"],
                                "order_status":"rejected",
                                "last_updated":datetime.now()
                            }
                        )
            else:
                failed_orders.append(
                    {
                        "order_id":receptions.loc[idx,"order_id"],
                        "item_no":receptions.loc[idx,"item_no"],
                        "order_status":"pass",
                        "last_updated":datetime.now()
                    }
                )

        
        if audit_ended:
            break
    
    if len(failed_orders) > 0:
        db.execute(
            update(models.Orders),
            failed_orders
        )
    db.add_all(audit_db)
    db.commit()

    return {"message":"Audit completed","results":results}