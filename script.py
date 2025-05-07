from sqlalchemy.orm import Session
from sqlalchemy import Sequence, select
import models
import csv

def add_initial_data(db: Session, supplier_id: Sequence):
    print("Application startup: Initializing...")
    CSV_PROCESSING_BATCH_SIZE = 1000  # Number of rows to process at a time
    current_batch = 0
    supplier_product_relation = []
    products = []
    packaging = []
    with open('./csv/supplierproducts.csv', 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            supplier_name = row['SupplierName'].strip()
            db_supplier = db.query(models.Suppliers).filter(models.Suppliers.name == supplier_name).first()            
            if db_supplier is None:
                next_id_val = db.execute(select(supplier_id.next_value())).scalar_one()
                supplier_id_value = f"SUP{next_id_val:05d}"
                db.add(models.Suppliers(
                    name=supplier_name,
                    supplier_id=supplier_id_value
                ))
                db.commit()
            else:
                supplier_id_value = supplier_id_value
            
            print({"name":supplier_name,"id":supplier_id_value})
            products.append(models.Products(
                garment_type=row['GarmentType'].strip().lower(),
                material=row["Material"].strip().lower(),
                size=row["Size"].strip().lower(),
                collection=row["Collection"].strip().lower(),
                weight_units="kg",
                weight=float(row["Weight"].strip().lower()),
                product_id=row["ProductReference"]
            ))

            supplier_product_relation.append(
                models.SuppliersProducts(
                    supplier_id=supplier_id_value,
                    product_id=row['ProductReference']
                )
            )
            
            packaging.append(models.Packaging(
                product_id=row['ProductReference'],
                suggested_folding_method=row['ProposedFoldingMethod'].strip().lower(),
                suggested_quantity=row['ProposedUnitsPerCarton'].strip(),
                suggested_layout=row['ProposedLayout'].strip().lower()
            ))
            current_batch += 1
            
            if current_batch >= CSV_PROCESSING_BATCH_SIZE:
                db.add_all(products)                
                db.add_all(supplier_product_relation)
                db.add_all(packaging)
                db.commit()
                current_batch = 0
                supplier_product_relation = []
                products = []

                print(f"1000 records processed from {file.name}")
        
        db.add_all(products)
        db.add_all(supplier_product_relation)
        db.add_all(packaging)
        db.commit()
        print("CSV data processing finished. Application ready.")
            
            
