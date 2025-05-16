from sqlalchemy.orm import Session
from sqlalchemy import select, func
from typing import List
import pandas as pd
import numpy as np
import scipy.stats as ss
import random
import models
from validations import RecievedDelivery

density = pd.read_csv(r'C:\Users\esteb\Projects\MBD\Capgemin\app\data\csv\density.csv',encoding='utf-8')
density_suppliers = density.groupby(['DateOfReport','SupplierName']).count()
density_products = density.groupby(['DateOfReport','SupplierName','ProductReference']).count()



def create_fake_order(db:Session) -> dict:
    # Data to return
    data = []
    
    # Each order
    for supplier in ['A','B','C','D','F','G','H']:
        # Set Supplier name
        supplier = f'Supplier{supplier}'

        # Creates The historical data for the supplier
        orders_historical = density_suppliers[density_suppliers.index.get_loc_level(supplier,level=1)[0]]['ProductReference']

        # Normal distribution of the orders
        model = ss.norm.fit(orders_historical)
        
        # Total products of that supplier
        total_products = round(random.normalvariate(model[0],model[1]),0)
        
        # Proportions table
        proportions = density_products[density_products.index.get_loc_level(supplier,level=1)[0]]['GarmentType'].value_counts(normalize=True)

        # Quantity to place per product
        quantities = np.array(proportions.index)

        # Distribution chance
        probabilities = np.array(proportions.values)
        curr_items = 0

        db_supplier_id = db.execute(
                select(
                    models.Suppliers.supplier_id
                ).where(
                    models.Suppliers.name == supplier.lower()
                )
            ).first()
        
        product_supplier_db = db.execute(
                select(
                    models.SuppliersProducts.supplier_id,
                    models.SuppliersProducts.product_id
                ).where(
                    models.SuppliersProducts.supplier_id == db_supplier_id[0]
                ).distinct()
            ).all()
        products = [product[1] for product in product_supplier_db]
        products = list(set(products))
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
        else:
            deliveries.append(order)
            curr_load += order.quantity_recieved
            order_products.remove(order)
        
    
    return deliveries


