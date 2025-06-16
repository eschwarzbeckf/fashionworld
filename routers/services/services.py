from sqlalchemy.orm import Session
from fastapi import HTTPException
from sqlalchemy import select, func, update
from typing import List
import pandas as pd
import numpy as np
import scipy.stats as ss
import random
import models
from datetime import datetime
from random import choices
from uuid import uuid4
from validations import RecievedDelivery, ItemToAudit
from database import engine
import time


db_suppliers_products = pd.read_sql("SELECT s.name,sp.product_id FROM suppliers as s JOIN suppliers_products as sp ON sp.supplier_id = s.supplier_id", con=engine)
density = pd.read_sql_query("SELECT d.*,s.name  FROM density as d JOIN suppliers_products as sp ON sp.product_id = d.product_id JOIN suppliers as s ON s.supplier_id = sp.supplier_id", con=engine)
density_suppliers = density.groupby(['date_of_report','name']).count()
density_products = density.groupby(['date_of_report','name','product_id']).count()
products_defects_rate = pd.read_sql("SELECT * FROM products_defects_rate", con=engine)
grouped_defects = {
    name: group[["issue_description","defect_rate"]].to_dict('list')
    for name, group in products_defects_rate.groupby(["product_id","package_quality"])
}
grouped_packaging_quality = {
    name: group[["package_quality_rate"]].to_dict('list')
    for name, group in products_defects_rate[["product_id","package_quality","package_quality_rate"]].drop_duplicates().groupby(["product_id","package_quality"])
}

def create_fake_order() -> dict:
    # Data to return
    global db_suppliers_products
    data = []

    # Each order
    for supplier in ['A','B','C','D','F','G','H']:
        # Set Supplier name
        supplier = f'Supplier{supplier}'

        # Creates The historical data for the supplier
        orders_historical = density_suppliers[density_suppliers.index.get_loc_level(supplier,level=1)[0]]['product_id']

        # Normal distribution of the orders
        model = ss.norm.fit(orders_historical)
        
        # Total products of that supplier
        total_products = round(random.normalvariate(model[0],model[1]),0)
        
        # Proportions table
        proportions = density_products[density_products.index.get_loc_level(supplier,level=1)[0]]['garment_type'].value_counts(normalize=True)

        # Quantity to place per product
        quantities = np.array(proportions.index)

        # Distribution chance
        probabilities = np.array(proportions.values)
        curr_items = 0

        products = db_suppliers_products[db_suppliers_products["name"] == supplier]["product_id"].tolist()
        items = []
        while curr_items < total_products:
            product = random.choice(products)
            quantity = float(random.choices(quantities,probabilities,k=1)[0])
            items.append({
                "product_id":product,
                "boxes_ordered":quantity
                })
            curr_items += quantity
        
        data.append({"items":items})

    return data

async def create_fake_delivery(db:Session) -> List[RecievedDelivery]:
    orders_db = pd.read_sql("SELECT o.order_id, o.product_id, sum(o.boxes_ordered) as total_boxes FROM orders as o WHERE o.order_status = \"confirmed\" group by o.order_id, o.product_id;",con=engine)
    
    if len(orders_db) == 0:
        raise HTTPException(status_code=400, detail="No order on confirmed status")

    order_products = [RecievedDelivery(order_id=order,product_id=product,quantity_recieved=quantity) for order, product, quantity in orders_db.values]
    capacity = random.choices([1000,500,200,10],weights=[0.35,0.35,0.2,0.1],k=1)[0]
    curr_load = 0
    deliveries = []
    
    while curr_load < capacity:
        order = random.choice(order_products)
        remaining = capacity - curr_load
        if order.quantity_recieved >= remaining:
            order.quantity_recieved = remaining
            deliveries.append(order)
            curr_load += remaining
            order_products.remove(order)
        else:
            deliveries.append(order)
            curr_load += order.quantity_recieved
            order_products.remove(order)
        if len(order_products) <= 0:
            break
    
    return deliveries

def update_orders(total_to_be_recieved:int|float, orders:list):
    """Updates the Orders table to the filled status and adds when it was recieved.
    
    Keyword arguments:
    argument -- description
    Return: total_to_be_recieved
    """
    # Select the orders that are relevant to the order and product, order them based on the boxes ordered
    orders_to_update =[]
    for order in orders:
        # For each order, check if the total recieved amount is less than the order,
        # If it is, then the order is considered filled. so we need to update the status, and the filled date
        if order[3] <= total_to_be_recieved:
            orders_to_update.append(
                {
                    "order_id":order[0],
                    "item_no":order[2],
                    "product_id":order[1],
                    "order_filled_date":datetime.now(),
                    "order_status":"filled",
                    "last_updated":datetime.now()
                }
            )
            # We need to remove the units we assigned to the order
            total_to_be_recieved =- order[3]
        elif total_to_be_recieved <= 0:
            break
    return orders_to_update

def assign_issue(delivery: RecievedDelivery) -> tuple:
    uuid = str(uuid4())
    key = (delivery.product_id, delivery.package_quality)
    rates_data = grouped_defects.get(key)
    if not rates_data:
        raise HTTPException(401,f"No defect rates found for {delivery.product_id}")
    
    issue = random.choices(rates_data["issue_description"],rates_data["defect_rate"],k=1)[0]
    product_issue = [models.ProductsDefects(
        uuid = uuid,
        product_id=delivery.product_id,
        issue=issue
    )]
    return (uuid, product_issue)

def recieve_process(delivery:RecievedDelivery,id:str,db:Session) -> dict:

    good_quality = grouped_packaging_quality.get((delivery.product_id,'good'))["package_quality_rate"][0]
    package_quality = choices(['good','bad'],[good_quality, 1-good_quality],k=1)[0]
    delivery.package_quality = package_quality
    (uuid,product_issue) = assign_issue(delivery)
    deliveries_accepted = []
    deliveries_accepted.append(models.Receptions(
        reception_id = id,
        package_uuid=uuid,
        product_id=delivery.product_id,
        order_id=delivery.order_id,
        reception_date=datetime.now(),
        on_time=delivery.on_time,
        package_quality=delivery.package_quality
        )
    )

    return {"deliveries_accepted":deliveries_accepted,"delivery":delivery, "issues":product_issue}

