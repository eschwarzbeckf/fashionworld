from sqlalchemy.orm import Session
from sqlalchemy import Sequence, select, exists, text, Table
import models
import csv
from database import metadata
from datetime import datetime
import pandas as pd
from database import engine
import random

def add_initial_data(db: Session, supplier_id: Sequence):
    print("Application startup: Initializing...")
    products = []
    packaging = []
    supplier_products = []
    BATCH_SIZE = 1000
    counter = 0
    with open('./data/csv/supplierproducts.csv', 'r') as file:
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
    with open('./data/csv/density.csv', 'r') as f:
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

def add_incidents(db:Session):
    incidents_table = Table('incidents',metadata)
    incidents_table.drop(engine,checkfirst=True)
    incidents_table.create(engine,checkfirst=True)
    incidents_db = []
    BATCH_SIZE = 1000
    curr_row = 0
    suppliers = db.execute(select(models.Suppliers.name,models.Suppliers.supplier_id)).all()
    supplier_ids = {supplier[0]:supplier[1] for supplier in suppliers}
    with open('./data/csv/incidents.csv','r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            product_id = row["ProductReference"] + row["SupplierName"][-1]
            incidents_db.append(models.Incidents(
                    product_id=product_id.strip(),
                    supplier_id=supplier_ids[row["SupplierName"]].strip(),
                    date_of_incident=datetime.strptime(row['DateOfIncident'].strip(), '%Y-%m-%d'),
                    issue_description=row["IssueDescription"].lower().strip(),
                    cost_impact=float(row["CostImpact"])
                )
            )
            curr_row += 1
            if curr_row >= BATCH_SIZE:
                db.add_all(incidents_db)
                db.commit()
                incidents_db=[]
                curr_row =0

        db.add_all(incidents_db)
        db.commit()

def rand_distr_prob(main:str,categories:list,main_prob:float) -> dict:
    copy_cat = categories.copy()
    remaining = 1 - main_prob
    res = {main:main_prob}
    copy_cat.remove(main)
    for cat in copy_cat:
        res[cat] = 0
    loop = True
    while loop:
        for cat in copy_cat:
            res[cat] += random.uniform(0.00000001,remaining)
            remaining -= res[cat]
            if remaining <= 0:
                loop = False
                break
        
        
    return res

def add_defects_rate(db:Session):
    product_defects_rate_table = Table('products_defects_rate',metadata)
    product_defects_rate_table.drop(engine,checkfirst=True)
    product_defects_rate_table.create(engine,checkfirst=True)
    productsdefectsrate_db = []
    BATCH_SIZE = 1000
    curr_row = 0

    issues = list(pd.read_sql("SELECT DISTINCT(issue_description) FROM incidents",con=engine).values.ravel())
    if 'none' not in issues:
        issues += ['none']

    products = pd.read_sql("""
                           SELECT DISTINCT(p.product_id), pa.suggested_layout, pa.suggested_folding_method, pa.suggested_quantity
                           FROM products as p 
                           JOIN (select p1.product_id,p1.suggested_folding_method,p1.suggested_quantity,p1.suggested_layout,p1.revision from packaging as p1 where p1.revision = (select max(p2.revision) from packaging as p2 where p2.product_id = p1.product_id)) as pa ON p.product_id = pa.product_id;
                           """,con=engine).values
    
    
    for product in products:
        good_package_quality_rate = random.uniform(.800000,.999999)
        package_qualities_rates = [good_package_quality_rate,1-good_package_quality_rate]
        for package_quality_rate in package_qualities_rates:
            prob_distr = rand_distr_prob(
                'none',
                issues,
                random.uniform(0.8943,0.99943) if package_quality_rate < good_package_quality_rate else random.uniform(0.7843,0.96382)
                )
            for issue in issues:
                productsdefectsrate_db.append(
                    models.ProductsDefectsRate(
                        product_id=product[0],
                        suggested_layout=product[1],
                        suggested_folding_method=product[2],
                        suggested_quantity=product[3],
                        package_quality='bad'if package_quality_rate < good_package_quality_rate else 'good',
                        package_quality_rate=package_quality_rate,
                        issue_description=issue,
                        defect_rate=prob_distr[issue]
                    )
                )
                curr_row += 1

                if curr_row >= BATCH_SIZE:
                    db.add_all(productsdefectsrate_db)
                    db.commit()
                    curr_row = 0
                    productsdefectsrate_db = []
    
    db.add_all(productsdefectsrate_db)
    db.commit()

    
    
    