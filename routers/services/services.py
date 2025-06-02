from sqlalchemy.orm import Session
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

density = pd.read_sql_query("SELECT d.*,s.name  FROM density as d JOIN suppliers_products as sp ON sp.product_id = d.product_id JOIN suppliers as s ON s.supplier_id = sp.supplier_id", con=engine)
density_suppliers = density.groupby(['date_of_report','name']).count()
density_products = density.groupby(['date_of_report','name','product_id']).count()

def create_fake_order(db:Session) -> dict:
    # Data to return
    data = []
    
    db_supplier_ids = db.execute(
        select(
            models.Suppliers.supplier_id,
            models.Suppliers.name
        )
    ).all()

    products_suppliers_db = db.execute(
        select(
            models.SuppliersProducts.supplier_id,
            models.SuppliersProducts.product_id
        ).distinct()
    ).all()

    # Each order
    for supplier in ['A','B','C','D','F','G','H']:
        # Set Supplier name
        supplier = f'Supplier{supplier}'
        supplier_id = [id[0] if supplier == id[1] else id[0] for id in db_supplier_ids][0]
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

        products = [product[1] for product in filter(lambda x: x[0] == supplier_id, products_suppliers_db)]
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
    orders_db = db.execute(
        select(
            models.Orders.order_id,
            models.Orders.product_id,
            func.sum(models.Orders.boxes_ordered).label('total_boxes')
        ).where(
            models.Orders.order_status == 'confirmed'
        ).group_by(
            models.Orders.order_id,
            models.Orders.product_id
        )
    ).all()

    order_products = [RecievedDelivery(order_id=order_id,product_id=product_id,quantity_recieved=total_boxes) for order_id,product_id,total_boxes in orders_db]
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

def audit_result(audit, db:Session):
    result = ''
    
    return result

def update_orders(delivery, total_to_be_recieved:int|float, db:Session):
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
    orders_to_update =[]
    for order in order_db:
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
    db.execute(
        update(models.Orders),
        orders_to_update
    )
    db.commit()

def assign_issue(delivery: RecievedDelivery,db:Session, package_quality) -> str:
    uuid = str(uuid4())
    incidents = pd.read_csv(r'C:\Users\esteb\Projects\MBD\Capgemin\app\data\csv\incidents.csv')
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
        package_quality_rate,supplier_id = db.execute(
            select(
                models.SupplierError.packaging_quality_rate,
                models.SuppliersProducts.supplier_id
            ).join(
                models.SuppliersProducts,models.SuppliersProducts.product_id == delivery.product_id
            ).where(
                models.SuppliersProducts.product_id == delivery.product_id
            )
        ).first()

        audit_level, = db.execute(
            select(
                models.Suppliers.audit_level
            ).where(
                models.Suppliers.supplier_id == supplier_id
            )
        ).first()
        package_quality = choices(['good','bad'],[1-package_quality_rate,package_quality_rate],k=1)[0]
        delivery.package_quality = package_quality
        uuid = assign_issue(delivery,db,package_quality)
        to_audit = choices([False, True], weights=[1-audit_level,audit_level], k=1)[0]
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

