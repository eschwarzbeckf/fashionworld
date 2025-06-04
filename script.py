from sqlalchemy.orm import Session
from sqlalchemy import Sequence, select, exists, text
import models
import csv
from datetime import datetime
import pandas as pd
from database import engine

def add_initial_data(db: Session, supplier_id: Sequence):
    print("Application startup: Initializing...")
    products = []
    packaging = []
    supplier_products = []
    BATCH_SIZE = 1000
    counter = 0
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
                
            # exists_query = session.query(exists().where(User.email == email_to_check)).scalar()
            product_id_curr = f"{row["ProductReference"].strip()+supplier_name[-1]}"
            product_exist_in_db = db.query(exists().where(models.Products.product_id == product_id_curr)).scalar()
            product_exist_in_products = product_id_curr in [product.product_id for product in products]
            if product_exist_in_db == False and product_exist_in_products == False:
                products.append(models.Products(
                        garment_type=row['GarmentType'].strip().lower(),
                        material=row["Material"].strip().lower(),
                        size=row["Size"].strip().lower(),
                        collection=row["Collection"].strip().lower(),
                        weight_units="kg",
                        weight=float(row["Weight"].strip().lower()),
                        product_id=product_id_curr
                ))

                supplier_products.append(
                    models.SuppliersProducts(
                        supplier_id=supplier_id_value,
                        product_id=product_id_curr
                    )
                )
                
                packaging.append(models.Packaging(
                    product_id=product_id_curr,
                    revision=1,
                    suggested_folding_method=row['ProposedFoldingMethod'].strip().lower(),
                    suggested_quantity=float(row['ProposedUnitsPerCarton']),
                    suggested_layout=row['ProposedLayout'].strip().lower(),
                    created_date=datetime.now()
                ))
            
            else:
                curr_packaging = [packaging_item for packaging_item in packaging if packaging_item.product_id == product_id_curr]
                curr_packaging_sorted = sorted(curr_packaging, key=lambda x: x.revision, reverse=True)
                if len(curr_packaging_sorted) > 0:
                    curr_packaging_latest = curr_packaging_sorted[0]
                else:
                    curr_packaging_latest = None

                packaging_info = db.execute(select(models.Packaging.product_id,models.Packaging.revision,models.Packaging.created_date,models.Packaging.suggested_folding_method,models.Packaging.suggested_layout, models.Packaging.suggested_quantity).where(models.Products.product_id == product_id_curr).order_by(models.Packaging.product_id.desc(),models.Packaging.revision.desc())).first()
                
                if packaging_info is None:
                    revision = curr_packaging_latest.revision + 1
                    created_date = curr_packaging_latest.created_date
                    suggested_folding = curr_packaging_latest.suggested_folding_method
                    suggested_layout = curr_packaging_latest.suggested_layout
                    suggested_quantity = curr_packaging_latest.suggested_quantity
                elif curr_packaging_latest is None:
                    revision = int(packaging_info[1]) + 1
                    created_date = packaging_info[2]
                    suggested_folding = packaging_info[3].strip().lower()
                    suggested_layout = packaging_info[4].strip().lower()
                    suggested_quantity = float(packaging_info[5])
                
                elif curr_packaging_latest.revision > packaging_info[1]:
                    revision = curr_packaging_latest.revision + 1
                    created_date = curr_packaging_latest.created_date
                    suggested_folding = curr_packaging_latest.suggested_folding_method
                    suggested_layout = curr_packaging_latest.suggested_layout
                    suggested_quantity = curr_packaging_latest.suggested_quantity

                elif curr_packaging_latest.revision < packaging_info[1]:
                    revision = int(packaging_info[1]) + 1
                    created_date = packaging_info[2]
                    suggested_folding = packaging_info[3].strip().lower()
                    suggested_layout = packaging_info[4].strip().lower()
                    suggested_quantity = float(packaging_info[5])
                
                for left, right in zip([suggested_folding, suggested_layout, suggested_quantity],[row['ProposedFoldingMethod'].strip().lower(),row['ProposedLayout'].strip().lower(),float(row['ProposedUnitsPerCarton'].strip())]):
                    if left != right:
                        packaging.append(models.Packaging(
                            product_id=product_id_curr,
                            revision=revision,
                            suggested_folding_method=row['ProposedFoldingMethod'].strip().lower(),
                            suggested_quantity=float(row['ProposedUnitsPerCarton'].strip()),
                            suggested_layout=row['ProposedLayout'].strip().lower(),
                            created_date=created_date,
                            last_updated_date=datetime.now()
                        ))
                        break
                counter += 1
                if counter == BATCH_SIZE:
                    if len(products) > 0:
                        db.add_all(products)
                        db.commit()
                    if len(supplier_products) > 0:
                        db.add_all(supplier_products)
                        db.commit()
                    if len(packaging) > 0:
                        db.add_all(packaging)
                        db.commit()

                    products = []
                    packaging = []
                    supplier_products = []
                    counter = 0
        
        if len(products) > 0:
            db.add_all(products)
            db.commit()
        if len(supplier_products) > 0:
            db.add_all(supplier_products)
            db.commit()
        if len(packaging) > 0:
            db.add_all(packaging)
            db.commit()
                    

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

def add_scorecard_data(db:Session):
    scorecard_db = []
    BATCH_SIZE = 1000
    curr_row = 0
    with open('./data/csv/scorecard.csv', 'r') as f:
        reader = csv.DictReader(f)
        suppliers = db.execute(select(models.Suppliers.name,models.Suppliers.supplier_id)).all()
        supplier_ids = {supplier[0]:supplier[1] for supplier in suppliers}
        for row in reader:
            scorecard_db.append(models.Scorecard(
                supplier_id=supplier_ids[row["SupplierName"].strip()],
                num_month=int(row['Month']),
                year=int(row['Year']),
                total_incidents=int(row["TotalIncidents"]),
                packages_handled=int(row['PackagesHandled']),
                bad_packaging=float(row["BadPackagingRate"]),
                cost_per_incident=float(row["CostPerIncident"]),
                on_time_delivery=float(row["OnTimeDeliveryRate"]),
                anomalies_detected=float(row["AnomaliesDetected"]),
            ))
            curr_row += 1
            if curr_row >= BATCH_SIZE:
                db.add_all(scorecard_db)
                db.commit()
                scorecard_db = []
                curr_row = 0
        
        db.add_all(scorecard_db)
        db.commit()

def add_supplier_error():
    db_suppliers_products = pd.read_sql("SELECT s.name,sp.product_id FROM suppliers as s JOIN suppliers_products as sp ON sp.supplier_id = s.supplier_id", con=engine)
    density = pd.read_sql_query("SELECT d.*,s.name  FROM density as d JOIN suppliers_products as sp ON sp.product_id = d.product_id JOIN suppliers as s ON s.supplier_id = sp.supplier_id", con=engine)
    density_suppliers = density.groupby(['date_of_report','name']).count()
    density_products = density.groupby(['date_of_report','name','product_id']).count()