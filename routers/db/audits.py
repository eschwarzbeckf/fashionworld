from fastapi import APIRouter, status, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Annotated
from models import audit_id
from database import get_db, engine
from validations import AuditPlan
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
def create_audit(items: List[str],audit_plan: AuditPlan, db:db_dependency,sampling:str="random"):
    if items is None:
        raise HTTPException(status_code=400, detail="No order information provided.")
    elif audit_plan is None:
        raise HTTPException(status_code=400, detail="No audit criteria provided")
    items = list(set(items))
    orders = ""
    update_orders = []
    for order in items:
        orders += f"\"{order}\"" if orders == "" else f",\"{order}\""

    receptions = pd.read_sql_query(f"""
                                   SELECT r.*,p.garment_type,p.material,p.size,p.collection,p.weight 
                                   FROM receptions as r 
                                   JOIN products as p on p.product_id = r.product_id 
                                   WHERE r.order_id IN ({orders})
                                   """, con=engine)
    orders_db =   pd.read_sql_query(f"""
                                    SELECT o.order_id, o.item_no, o.order_status
                                    FROM orders as o
                                    WHERE o.order_id in ({orders})
                                    """,con=engine)
    uuids = ""
    for item in receptions["package_uuid"].values:
        uuids += f"\"{item}\"" if uuids == "" else f",\"{item}\""

    products_issues_statuses = pd.read_sql_query(f"SELECT * FROM products_defects WHERE uuid IN ({uuids})",con=engine)

    receptions = receptions.set_index('package_uuid').join(products_issues_statuses.set_index('uuid'),rsuffix='_defects').rename(columns={"issue":"issue_description"})
    x = receptions[['issue_description','garment_type','material','size','collection','weight']]
    cost_log = model.predict(x)
    cost = np.round(10**cost_log,2)
    receptions["estimated_cost"] = cost
    receptions.reset_index(inplace=True)

    audit_name, audit_criterias, sampling, audit_quantity = audit_plan.model_dump().values()

    all_reject_criterias = []
    issues = {}
    results = {}
    for order in items:
        issues[order] = {}
        results[order] = {"status":"pass","unknown":[]}
        for criteria in audit_criterias:
            all_reject_criterias += criteria["reject_categories"]
            issues[order][criteria["criteria_name"]] = {"pass":0,"rejected":0} 
            results[order][criteria["criteria_name"]] = {"pass":[],"rejected":[],"unknown":[]}

    audit_db = []

    for order in items:
        # Loop through each order
        audit_ended = False
        if sampling.lower() == "random":
            if audit_quantity > 0:
                item_audits = receptions[receptions["order_id"] == order].sample(audit_quantity,replace=False)
                item_audits = random.shuffle(receptions) if len(item_audits) < audit_quantity else item_audits
            else:
                item_audits = random.shuffle(receptions[receptions["order_id"] == order])
        elif sampling.lower() == "model":
            pass
        
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

            for audit_criteria in audit_criterias:
                criteria_name, accept_categories, reject_categories, accepted_quantity = audit_criteria.values()
                if item_audits.loc[idx,"issue_description"] in accept_categories:
                   # print(f"\n\n{order}\n{item_audits.loc[idx,"issue_description"]}\n'is in categories accepted: '{item_audits.loc[idx,"issue_description"] in criteria["accept_categories"]}\n{criteria["criteria_name"]}\n\n")
                    issues[order][criteria_name]["pass"] += 1
                    results[order][criteria_name]["pass"].append(
                        {
                            "product_id":item_audits.loc[idx,"product_id"],
                            "uuid":item_audits.loc[idx,"package_uuid"],
                            "package_quality":item_audits.loc[idx,"package_quality"],
                            "issue":item_audits.loc[idx, "issue_description"],
                            "cost_impact":item_audits.loc[idx,"estimated_cost"]
                        }
                    )
                elif item_audits.loc[idx,"issue_description"] in reject_categories:
                    issues[order][criteria_name]["rejected"] += 1
                   # print(f"\n\n{order}\n{item_audits.loc[idx,"issue_description"]}\n'is in categories rejected: '{item_audits.loc[idx,"issue_description"] in criteria["reject_categories"]}\n{criteria["criteria_name"]}\n\n")
                    results[order][criteria_name]["rejected"].append(
                        {
                            "product_id":item_audits.loc[idx,"product_id"],
                            "uuid":item_audits.loc[idx,"package_uuid"],
                            "package_quality":item_audits.loc[idx,"package_quality"],
                            "issue":item_audits.loc[idx, "issue_description"],
                            "cost_impact":item_audits.loc[idx,"estimated_cost"]
                        }
                    )
                elif item_audits.loc[idx,"issue_description"] not in all_reject_criterias:
                   # print(f"\n\n{order}\n{item_audits.loc[idx,"issue_description"]}\n'is in categories unknown: '{item_audits.loc[idx,"issue_description"] in all_reject_criterias}\n{criteria["criteria_name"]}\n\n")
                    results[order][criteria_name]["unknown"].append(
                        {
                            "product_id":item_audits.loc[idx,"product_id"],
                            "uuid":item_audits.loc[idx,"package_uuid"],
                            "package_quality":item_audits.loc[idx,"package_quality"],
                            "issue":item_audits.loc[idx, "issue_description"],
                            "cost_impact":None
                        }
                    )

                if accepted_quantity > -1:
                    if issues[order][criteria_name]["rejected"] > accepted_quantity:
                        audit_ended = True
                        results[order]["status"]=f"rejected reached threshold for {criteria_name}"
                        for idx2 in orders_db[orders_db["order_id"] == order].index:
                            update_orders.append(
                                {
                                    "order_id":orders_db.loc[idx2,"order_id"],
                                    "item_no":orders_db.loc[idx2,"item_no"],
                                    "order_status":"rejected",
                                    "last_updated":datetime.now()
                                }
                            )
                
                if audit_ended:
                    break

            if audit_ended:
                break

        if audit_ended:
            print(order)
            continue
            
        for idx3 in orders_db[orders_db["order_id"] == order].index:
            update_orders.append(
                    {
                        "order_id":orders_db.loc[idx3,"order_id"],
                        "item_no":orders_db.loc[idx3,"item_no"],
                        "order_status":"pass",
                        "last_updated":datetime.now()
                    }
                )
    
    if len(update_orders) > 0:
        db.execute(
            update(models.Orders),
            update_orders
        )
    db.add_all(audit_db)
    db.commit()

    return {"message":"Audit completed","results":results}