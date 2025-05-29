from sqlalchemy.orm import Session
from sqlalchemy import Sequence, select, exists, text
import models
import csv
from datetime import datetime

def add_initial_data(db: Session, supplier_id: Sequence):
    print("Application startup: Initializing...")
    products = []
    with open('./data/csv/supplierproducts_short.csv', 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            supplier_name = row['SupplierName'].strip()
            supplier_exists = db.query(exists().where(models.Suppliers.name == supplier_name)).scalar()
            if not supplier_exists:
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
                supplier_id_value = db.execute(select(models.Suppliers.supplier_id).where(models.Suppliers.name == supplier_name)).scalar()
                supplier_id_value = supplier_id_value
            # exists_query = session.query(exists().where(User.email == email_to_check)).scalar()
            product_id_curr = f"{row["ProductReference"].strip()+supplier_name[-1]}"
            product_exist_in_db = db.query(exists().where(models.Products.product_id == product_id_curr)).scalar()
            product_exist_in_products = product_id_curr in [product.product_id for product in products]
            if product_exist_in_db == False and product_exist_in_products == False:
                db.add(models.Products(
                    garment_type=row['GarmentType'].strip().lower(),
                    material=row["Material"].strip().lower(),
                    size=row["Size"].strip().lower(),
                    collection=row["Collection"].strip().lower(),
                    weight_units="kg",
                    weight=float(row["Weight"].strip().lower()),
                    product_id=product_id_curr
                ))

                db.add(
                    models.SuppliersProducts(
                        supplier_id=supplier_id_value,
                        product_id=product_id_curr
                    )
                )
                db.commit()
                
                db.add(models.Packaging(
                    product_id=product_id_curr,
                    revision=1,
                    suggested_folding_method=row['ProposedFoldingMethod'].strip().lower(),
                    suggested_quantity=float(row['ProposedUnitsPerCarton']),
                    suggested_layout=row['ProposedLayout'].strip().lower(),
                    created_date=datetime.now()
                ))
                db.commit()
            
            else:
                packaging_info = db.execute(select(models.Packaging.product_id,models.Packaging.revision,models.Packaging.created_date,models.Packaging.suggested_folding_method,models.Packaging.suggested_layout, models.Packaging.suggested_quantity).where(models.Products.product_id == product_id_curr).order_by(models.Packaging.product_id.desc(),models.Packaging.revision.desc())).first()
                package_product_id, revision, created_date, suggested_folding, suggested_layout, suggested_quantity = packaging_info
                revision = int(revision)
                for left, right in zip([package_product_id, suggested_folding, suggested_layout, float(suggested_quantity)],[product_id_curr,row['ProposedFoldingMethod'].strip().lower(),row['ProposedLayout'].strip().lower(),float(row['ProposedUnitsPerCarton'].strip())]):
                    if left != right:
                        db.add(models.Packaging(
                            product_id=package_product_id,
                            revision=int(revision) + 1,
                            suggested_folding_method=row['ProposedFoldingMethod'].strip().lower(),
                            suggested_quantity=float(row['ProposedUnitsPerCarton'].strip()),
                            suggested_layout=row['ProposedLayout'].strip().lower(),
                            created_date=created_date,
                            last_updated_date=datetime.now()
                        ))
                        db.commit()
                        break          
                    

        print("CSV data processing finished. Application ready.")
            
def add_density_data(db: Session):
    print("Starting to add density data...")
    CSV_PROCESSING_BATCH_SIZE = 1000
    curr_row = 0
    density_data = []
    with open('./data/csv/density_short.csv', 'r') as f:
        reader = csv.DictReader(f)

        for row in reader:
            supplier_name = row["SupplierName"].strip()
            product_id = f'{row['ProductReference'].strip()+supplier_name[-1]}'
            density_data.append(models.Density(
                report_id=row["ReportID"].strip(),
                date_created=datetime.now(),
                date_of_report=datetime.strptime(row['DateOfReport'].strip(), '%Y-%m-%d'),
                product_id =product_id,
                garment_type=row['GarmentType'].strip().lower(),
                material=row['Material'].strip().lower(),
                size=row['Size'].strip().lower(),
                collection=row['Collection'].strip().lower(),
                weight=float(row['Weight'].strip()),
                weight_units='kg',
                suggested_folding_method=row['ProposedFoldingMethod'].strip().lower(),
                suggested_quantity=float(row['ProposedUnitsPerCarton'].strip()),
                suggested_layout=row['ProposedLayout'].strip().lower(),
                packaging_quality=row['PackagingQuality'].strip().lower()
            ))
            curr_row += 1
            if curr_row >= CSV_PROCESSING_BATCH_SIZE:
                db.add_all(density_data)
                db.commit()
                density_data = []
                curr_row = 0
            
    db.add_all(density_data)
    db.commit()