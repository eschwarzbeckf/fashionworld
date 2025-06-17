from fastapi import APIRouter, status, HTTPException, Depends
from validations import RecievedDelivery
from sqlalchemy.orm import Session
from sqlalchemy import select, func, update
from database import get_db, engine
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
async def package_recieved(deliveries: List[RecievedDelivery], db:db_dependency):
    if deliveries is None:
        raise HTTPException(status_code=400, detail="No order information provided.")
    
    # Set our variables to save and do the update
    delivery_db = []
    packages_to_return = []
    product_issues = []
    # Gerate the delivery id
    next_id_val = db.execute(select(reception_id.next_value())).scalar_one()
    generated_recieved_id = f"REC{next_id_val:08d}"
    orders_db = pd.read_sql("SELECT order_id,product_id,item_no,boxes_ordered FROM orders WHERE order_status = \"confirmed\" ORDER BY boxes_ordered",con=engine).values
    recieved_db = pd.read_sql("SELECT order_id, product_id, count(product_id) FROM receptions GROUP BY order_id, product_id", con=engine).values
    orders_to_update = []
    for delivery in deliveries:
        # query which orders are not filled and are confirmed
        orders = [order for order in filter(lambda x: x[0] == delivery.order_id and x[1] == delivery.product_id,orders_db)]
        # check the packages we have recieved
        recieved = [event for event in filter(lambda x: x[0] == delivery.order_id and x[1] == delivery.product_id,recieved_db)]

        # Else need to check the quantities of the orders, so:
        # Need to get the order quantity from the orders
        order_quantity = int(sum([order[2] for order in orders if order[0] == delivery.order_id]))
        # Know how much we have recieved
        recieved_quantity = int(sum([event[2] for event in recieved]))
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
                orders_to_update += update_orders(total_to_be_recieved,orders)
            
            
        elif order_quantity > total_to_be_recieved:
            # If the order quantity is greater than the total to be recieved, then we will accept the whole delivery
            for package in range(delivery.quantity_recieved):
                response = recieve_process(delivery,generated_recieved_id,db)
                [delivery_db.append(i) for i in response["deliveries_accepted"]]
                delivery = response["delivery"]
                product_issues += response["issues"]
                # After recieveing the delivery, we will update the orders and see if we can 'fill' the orders

            orders_to_update += update_orders(total_to_be_recieved,orders)

        elif order_quantity <= total_to_be_recieved:
            # If the order quantity is less or equals to the total to be recieved, then we will only take what is pending to recieve
            total_to_be_recieved = recieved_quantity + pending_to_recieve
            for package in range(int(pending_to_recieve)):
                response = recieve_process(delivery,generated_recieved_id,db)
                [delivery_db.append(i) for i in response["deliveries_accepted"]]
                delivery = response["delivery"]
                product_issues += response["issues"]
                # After recieveing the delivery, we will update the orders and see if we can 'fill' the orders
            orders_to_update += update_orders(total_to_be_recieved,orders)
            
            #Return the packages that are left over
            delivery.quantity_recieved -= pending_to_recieve
            packages_to_return.append(delivery)
    # Add the deliveries to the database
    
    db.execute(
        update(models.Orders),
        orders_to_update
    )
    db.add_all(delivery_db)
    db.add_all(product_issues)

    db.commit()
    return {"message":"Accepted deliveries","accepted_packages":delivery_db, "packages_to_return":packages_to_return}

@router.get("/deliveries_fake", status_code=status.HTTP_201_CREATED)
async def fake_package_recieved(db:db_dependency):    
    deliveries = await create_fake_delivery(db)
    message = await package_recieved(deliveries,db)
    return message