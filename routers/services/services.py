from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List
import pandas as pd
import numpy as np
import scipy.stats as ss
import random
import models

density = pd.read_csv(r'C:\Users\esteb\Projects\MBD\Capgemin\app\data\csv\density.csv',encoding='utf-8')
density_suppliers = density.groupby(['DateOfReport','SupplierName']).count()
density_products = density.groupby(['DateOfReport','SupplierName','ProductReference']).count()



def create_fake_order(db:Session):
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
            quantity = random.choices(quantities,probabilities,k=1)[0]
            items.append({
                "product_id":product,
                "boxes_ordered":float(quantity)
                })
            curr_items += float(quantity)
        
        data.append({"items":items})

    return data
    