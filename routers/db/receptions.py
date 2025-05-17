from fastapi import APIRouter, status, HTTPException, Depends
from validations import RecievedDelivery, ItemToAudit
from sqlalchemy.orm import Session
from sqlalchemy import select, func, label, update
from database import get_db
from typing import List, Annotated
import models
from models import reception_id
from datetime import datetime
from random import choices
from uuid import uuid4
from datetime import datetime
from ..services.services import create_fake_delivery
from .audits import create_audit
import random
import pandas as pd
import numpy as np

incidents = pd.read_csv(r'C:\Users\esteb\Projects\MBD\Capgemin\app\data\csv\incidents.csv')

router = APIRouter(
    prefix="/api/db/receptions"
)

db_dependency = Annotated[Session, Depends(get_db)]

def update_orders(delivery, total_to_be_recieved:int|float, db:db_dependency):
    """Updates the Orders table to the filled status and adds when it was recieved.
    
    Keyword arguments:
    argument -- description
    Return: total_to_be_recieved
    """
    # Select the orders that are relevant to the order and product, order them based on the boxes ordered
    stmt = select(
            models.Orders.order_id,
            models.Orders.product_id,
            models.Orders.item_no,
            models.Orders.boxes_ordered
            ).where(
                models.Orders.order_id == delivery.order_id,
                models.Orders.product_id == delivery.product_id,
                models.Orders.order_status == 'confirmed'
            ).order_by(
                models.Orders.boxes_ordered
            )
    order_db = db.execute(stmt).all()
    for order in order_db:
        # For each order, check if the total recieved amount is less than the order,
        # If it is, then the order is considered filled. so we need to update the status, and the filled date
        if order[3] <= total_to_be_recieved:
            update_statement = update(
                    models.Orders
                ).where(
                    models.Orders.order_id == order[0],
                    models.Orders.product_id == order[1],
                    models.Orders.item_no == order[2]
                ).values(
                    order_filled_date=datetime.now(),
                    order_status='filled',
                    last_updated=datetime.now()
                )
            db.execute(update_statement)
            # We need to remove the units we assigned to the order
            total_to_be_recieved =- order[3]
        elif total_to_be_recieved <= 0:
            break

def assign_issue(delivery: RecievedDelivery,db:Session) -> str:
    uuid = str(uuid4())
    supplier_id, supplier_name = db.execute(
        select(
            models.SuppliersProducts.supplier_id,
            models.Suppliers.name
        ).join(
            models.Suppliers, models.Suppliers.supplier_id == models.SuppliersProducts.supplier_id
        ).where(
            models.SuppliersProducts.product_id == delivery.product_id
        )
    ).first()
    error, = db.execute(
        select(
            models.SupplierError.error_rate
        ).where(
            models.SupplierError.supplier_id == supplier_id
        )
    ).first()
    proportions = incidents[(incidents['SupplierName']==supplier_name) & (incidents['IssueDescription'] != 'Packaging Damage')]['IssueDescription'].value_counts(normalize=True)
    issue_categories = np.array([word.lower() for word in proportions.index])
    probabilities = np.array(proportions.values)
    issue = random.choices([True,False],[error,1-error],k=1)[0]
    if delivery.package_quality == 'bad':
        add_issue = 'packaging damage'
    elif issue:
        add_issue = random.choices(issue_categories,probabilities,k=1)[0]
    else:
        add_issue = 'none'
    
    product_issue = models.ProductsDefects(
        uuid = uuid,
        product_id=delivery.product_id,
        issue=add_issue
    )
    db.add(product_issue)
    db.commit()
    return uuid

def recieve_process(delivery:RecievedDelivery,id:str,audit:float,db:Session) -> dict:
        package_quality_rate,_ = db.execute(
            select(
                models.SupplierError.packaging_quality_rate,
                models.SuppliersProducts.supplier_id
            ).join(
                models.SuppliersProducts,models.SuppliersProducts.product_id == delivery.product_id
            ).where(
                models.SuppliersProducts.product_id == delivery.product_id
            )
        ).first()
        package_quality = choices(['good','bad'],[1-package_quality_rate,package_quality_rate],k=1)[0]
        delivery.package_quality = package_quality
        uuid = assign_issue(delivery,db)
        to_audit = choices([False, True], weights=[1-audit,audit], k=1)[0]
        deliveries_accepted = []
        units_to_audit = []
        deliveries_accepted.append(models.Receptions(
            reception_id = id,
            package_uuid=uuid,
            product_id=delivery.product_id,
            order_id=delivery.order_id,
            reception_date=datetime.now(),
            to_audit=to_audit,
            on_time=delivery.on_time,
            package_quality=delivery.package_quality
            )
        )
        if delivery.package_quality == 'bad':
            units_to_audit.append(ItemToAudit(
                reception_id=id,
                package_uuid=uuid,
                product_id=delivery.product_id,
               package_quality=delivery.package_quality
            ))
        elif to_audit:
            units_to_audit.append(ItemToAudit(
                reception_id=id,
                package_uuid=uuid,
                product_id=delivery.product_id,
               package_quality=delivery.package_quality
            ))
        
        return {"deliveries_accepted":deliveries_accepted,"units_to_audit":units_to_audit,"delivery":delivery}

@router.post("/deliveries", status_code=status.HTTP_201_CREATED)
async def package_recieved(deliveries: List[RecievedDelivery], db:db_dependency,audit:float = 0.10):
    if deliveries is None:
        raise HTTPException(status_code=400, detail="No order information provided.")
    
    # Set our variables to save and do the update
    delivery_db = []
    audits_db = []
    packages_to_return = []
    order_updates = []
    # Gerate the delivery id
    next_id_val = db.execute(select(reception_id.next_value())).scalar_one()
    generated_recieved_id = f"REC{next_id_val:08d}"
    for delivery in deliveries:
        # query which orders are not filled and are confirmed
        order_db = db.execute(
            select(
                models.Orders.order_id,
                models.Orders.product_id,
                func.sum(models.Orders.boxes_ordered).label('total_boxes_order')
                ).where(
                    models.Orders.order_id == delivery.order_id,
                    models.Orders.product_id == delivery.product_id,
                    models.Orders.order_status == 'confirmed'
                ).group_by(
                    models.Orders.order_id,
                    models.Orders.product_id
                ).order_by(
                    models.Orders.boxes_ordered.desc()
                    )
                ).all()
        # check the packages we have recieved
        recieved_db = db.execute(
            select(
                models.Receptions.order_id,
                models.Receptions.product_id,
                func.count(models.Receptions.product_id).label('total_boxes_recieved')
            ).where(
                models.Receptions.order_id == delivery.order_id,
                models.Receptions.product_id == delivery.product_id,
            ).group_by(
                models.Receptions.order_id,
                models.Receptions.product_id
            )
        ).all()

        # Else need to check the quantities of the orders, so:
        # Need to get the order quantity from the orders
        order_quantity = int(sum([order[2] for order in order_db if order.order_id == delivery.order_id]))
        # Know how much we have recieved
        recieved_quantity = int(sum([recieved[2] for recieved in recieved_db]))
        # What we have would be if we accept all the delivery the amount of packages
        total_to_be_recieved = recieved_quantity + delivery.quantity_recieved # What would be recieved if accept ALL the delivery + what we have already accepted
        pending_to_recieve = order_quantity - recieved_quantity # What is pending to recieve in the current order
        # Assign issue if there is any to product
        if pending_to_recieve <= 0:
            # If thereare nothing pending to recieve, then
            # Update the recieved quantity
            total_to_be_recieved = order_quantity
            for package in range(int(order_quantity)):
                # Fill orders
                update_orders(delivery,total_to_be_recieved,db)
            
            
        elif order_quantity > total_to_be_recieved:
            # If the order quantity is greater than the total to be recieved, then we will accept the whole delivery
            for package in range(delivery.quantity_recieved):
                response = recieve_process(delivery,generated_recieved_id,audit,db)
                [delivery_db.append(i) for i in response["deliveries_accepted"]]
                [audits_db.append(i) for i in response["units_to_audit"]]
                delivery = response["delivery"]
                # After recieveing the delivery, we will update the orders and see if we can 'fill' the orders
            update_orders(delivery,total_to_be_recieved,db)

        elif order_quantity <= total_to_be_recieved:
            # If the order quantity is less or equals to the total to be recieved, then we will only take what is pending to recieve
            total_to_be_recieved = recieved_quantity + pending_to_recieve
            for package in range(int(pending_to_recieve)):
                response = recieve_process(delivery,generated_recieved_id,audit,db)
                [delivery_db.append(i) for i in response["deliveries_accepted"]]
                [audits_db.append(i) for i in response["units_to_audit"]]
                delivery = response["delivery"]
                # After recieveing the delivery, we will update the orders and see if we can 'fill' the orders
            update_orders(delivery,total_to_be_recieved,db)
            
            #Return the packages that are left over
            delivery.quantity_recieved -= pending_to_recieve
            packages_to_return.append(delivery)
            
    # Add the deliveries to the database
    db.add_all(delivery_db)
    if len(audits_db) > 0:
        audit_message = await create_audit(audits_db,db)
    else:
        audit_message={"audits":"No Audits Created"}

    if len(order_updates) > 0:
        db.add_all(order_updates)
    db.commit()
    return {"message":"Accepted deliveries","accepted_packages":delivery_db, "packages_to_return":packages_to_return,"packages_for_audit":audit_message["audits"]}

@router.get("/deliveries_fake", status_code=status.HTTP_201_CREATED)
async def fake_package_recieved(db:db_dependency):    
    deliveries = await create_fake_delivery(db)
    message = await package_recieved(deliveries,db)
    return message