from fastapi import APIRouter, status, HTTPException, Depends
from validations import RecievedDelivery
from sqlalchemy.orm import Session
from sqlalchemy import select, func, update
from database import get_db
from typing import List, Annotated
import models
from models import reception_id
from ..services.services import create_fake_delivery,update_orders, recieve_process
from .audits import create_audit
import pandas as pd
import numpy as np

router = APIRouter(
    prefix="/api/db/receptions"
)

db_dependency = Annotated[Session, Depends(get_db)]


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