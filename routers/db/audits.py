from fastapi import APIRouter, status, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Annotated
from models import audit_id
from database import get_db, engine
from validations import AuditOrder, AuditPlan
from sqlalchemy import select
import models
from datetime import datetime
import pickle
import pandas as pd
from sklearn.compose import make_column_selector, make_column_transformer, ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.linear_model import LinearRegression
import random

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
    
    for item in items:
        orders += f"\"{item.order_id}\"" if orders == "" else f",\"{item.order_id}\""

    receptions = pd.read_sql_query(f"SELECT * FROM receptions as r JOIN products as p on p.product_id = r.product_id WHERE r.order_id IN ({orders})", con=engine)
    audit_criterias, sampling, audit_quantity = audit_plan.model_dump().values()
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
    products_issues_statuses = pd.read_sql_query(f"SELECT * FROM products_defects WHERE uuid IN ({uuids})",con=engine)
    item_audits = item_audits.set_index('package_uuid').join(products_issues_statuses.set_index('uuid'),rsuffix='_defects')
    
    for item in item_audits:
        x = pd.DataFrame([[issue,garment_type,material,size,collection,weight]],columns=['issue_description','garment_type','material','size','collection','weight'])
        cost_log = model.predict(x)[0]
        cost = round(10**cost_log,3)
        next_id_val = db.execute(select(audit_id.next_value())).scalar_one()
        generated_audit_id = f"AUD{next_id_val:08d}"
 
        audit_db.append(
            models.Audits(
                audit_id=generated_audit_id,
                reception_id=item.reception_id,
                product_id=item.product_id,
                package_uuid=item.package_uuid,
                created_date=datetime.now(),
                packaging_quality=item.package_quality,
                issue_description=issue,
                audit_date=datetime.now(),
                cost_impact=cost
            )
        )

        for criteria in audit_criterias:
            if issue in criteria.accept_categories:
                units_without_issues += 1
            elif issue in criteria.reject_categories:
                units_with_issues += 1
            else:
                unknown_issue += 1

            if criteria.accepted_quantity > 0:
                if units_without_issues == criteria.accepted_quantity:
                    audit_ended = True
            if criteria.rejected_quantity > 0:
                if units_with_issues == criteria.rejected_quantity:
                    audit_ended = True
        
        if audit_ended:
            break
    
    db.add_all(audit_db)
    db.commit()

    return {"message":"Audit completed","results":"yes","audits":audit_db}