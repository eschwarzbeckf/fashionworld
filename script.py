from sqlalchemy.orm import Session
from sqlalchemy import Sequence, select, exists, text
import models
import csv
from datetime import datetime

def add_initial_data(db: Session, supplier_id: Sequence):
    print("Application startup: Initializing...")
    CSV_PROCESSING_BATCH_SIZE = 1000  # Number of rows to process at a time
    current_batch = 0
    supplier_product_relation = []
    products = []
    packaging = []
    with open('./data/csv/supplierproducts.csv', 'r') as file:
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

                db.add(
                    models.SupplierError(
                        supplier_id=supplier_id_value,
                        name=supplier_name,
                        error_rate=0.05,
                        packaging_quality_rate=0.01
                    )
                )
                db.commit()
            else:
                supplier_id_value = supplier_id_value
            # exists_query = session.query(exists().where(User.email == email_to_check)).scalar()
            product_exist_in_db = db.query(exists().where(models.Products.product_id == row["ProductReference"])).scalar()
            product_exist_in_products = row["ProductReference"].strip() in [product.product_id for product in products]
            if product_exist_in_db == False and product_exist_in_products == False:
                products.append(models.Products(
                    garment_type=row['GarmentType'].strip().lower(),
                    material=row["Material"].strip().lower(),
                    size=row["Size"].strip().lower(),
                    collection=row["Collection"].strip().lower(),
                    weight_units="kg",
                    weight=float(row["Weight"].strip().lower()),
                    product_id=row["ProductReference"].strip()
                ))

                supplier_product_relation.append(
                    models.SuppliersProducts(
                        supplier_id=supplier_id_value,
                        product_id=row['ProductReference']
                    )
                )
                db_packaging = db.query(models.Packaging).filter(models.Packaging.product_id == row["ProductReference"]).order_by(models.Packaging.revision.desc()).first()
                try:
                    print(db_packaging.revision)
                except:
                    pass
                if db_packaging is None:
                    packaging.append(models.Packaging(
                        product_id=row['ProductReference'],
                        revision=1,
                        suggested_folding_method=row['ProposedFoldingMethod'].strip().lower(),
                        suggested_quantity=row['ProposedUnitsPerCarton'].strip(),
                        suggested_layout=row['ProposedLayout'].strip().lower(),
                        created_date=datetime.now()
                    ))
                else:
                    packaging.append(models.Packaging(
                        product_id=row['ProductReference'],
                        revision=db_packaging.revision + 1,
                        suggested_folding_method=row['ProposedFoldingMethod'].strip().lower(),
                        suggested_quantity=row['ProposedUnitsPerCarton'].strip(),
                        suggested_layout=row['ProposedLayout'].strip().lower(),
                        created_date=db_packaging.created_date,
                        last_updated_date=datetime.now()
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
            
