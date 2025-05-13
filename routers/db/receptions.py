from fastapi import APIRouter, status, HTTPException, Depends
from validations import RecievedDelivery
from sqlalchemy.orm import Session
from sqlalchemy import select, func, label
from database import metadata, get_db
from typing import List, Annotated
import models
from models import reception_id, audit_id
from datetime import datetime
from random import choices
from uuid import uuid4
from datetime import datetime


router = APIRouter(
    prefix="/api/db/receptions"
)

db_dependency = Annotated[Session, Depends(get_db)]

@router.post("/deliveries", status_code=status.HTTP_201_CREATED)
async def package_recieved(deliveries: List[RecievedDelivery], db:db_dependency):
    if deliveries is None:
        raise HTTPException(status_code=400, detail="No order information provided.")
    
    delivery_db = []
    audits_db = []
    packages_to_return = []
    order_updates = []
    for delivery in deliveries:
        audit = delivery.audit_threshold
        order_db = db.execute(
            select(
                models.Orders.order_id,
                models.Orders.product_id,
                models.Orders.item_no,
                func.sum(models.Orders.boxes_ordered).label('total_boxes_order')
                ).where(
                    models.Orders.order_id == delivery.order_id,
                    models.Orders.product_id == delivery.product_id,
                    models.Orders.order_status == 'confirmed'
                ).group_by(
                    models.Orders.order_id,
                    models.Orders.product_id
                ).order_by(models.Orders.boxes_ordered.desc())
                ).all()
        recieved_db = db.execute(
            select(
                models.Receptions.order_id,
                models.Receptions.product_id,
                func.count(models.Receptions.product_id).label('total_boxes_recieved')
            ).where(
                models.Receptions.order_id == delivery.order_id,
                models.Receptions.product_id == delivery.product_id,
            ).group_by(
                models.Receptions.order_id,
                models.Receptions.product_id
            )
        ).all()

        if len(recieved_db) == 0:
            next_id_val = db.execute(select(reception_id.next_value())).scalar_one()
            generated_recieved_id = f"REC{next_id_val:08d}"
            for package in range(delivery.quantity_recieved):
                delivery_db.append(models.Receptions(
                    reception_id = generated_recieved_id,
                    package_uuid=str(uuid4()),
                    product_id=delivery.product_id,
                    order_id=delivery.order_id,
                    reception_date=datetime.now(),
                    to_audit=choices([False, True], weights=[1-audit,audit], k=1)[0],
                    on_time=delivery.on_time,
                    package_quality=choices(['good', 'bad'], weights=[0.97,0.03], k=1)[0]
                    )
                )
            continue
        elif len(order_db) == 0:
            packages_to_return.append(delivery)
            continue
        else:
            order_quantity = int(sum([order[3] for order in order_db if order.order_id == delivery.order_id]))
            recieved_quantity = int(sum([recieved[2] for recieved in recieved_db]))
            total_to_be_recieved = recieved_quantity + delivery.quantity_recieved # What would be recieved if accept ALL the delivery + what we have already accepted
            pending_to_recieve = order_quantity - recieved_quantity # What is pending to recieve in the current order

        if pending_to_recieve <= 0:
            print(f"\n\n\n\npending to recieve is: {pending_to_recieve}\n\n\n\n")
            continue
        elif order_quantity > total_to_be_recieved:
            print(f"\n\n\n\nLess than what is pending to recieve\n\n\n\n")
            next_id_val = db.execute(select(reception_id.next_value())).scalar_one()
            generated_recieved_id = f"REC{next_id_val:08d}"
            for package in range(delivery.quantity_recieved):
                delivery_db.append(models.Receptions(
                    reception_id = generated_recieved_id,
                    package_uuid=str(uuid4()),
                    product_id=delivery.product_id,
                    order_id=delivery.order_id,
                    reception_date=datetime.now(),
                    to_audit=choices([False, True], weights=[1-audit,audit], k=1)[0],
                    on_time=delivery.on_time,
                    package_quality=choices(['good', 'bad'], weights=[0.97,0.03], k=1)[0]
                    )
                )

            for order in order_db:
                if order[3] <= total_to_be_recieved:
                    order.order_filled_date = datetime.now()
                    order.order_status = 'filled'
                    total_to_be_recieved =- order.boxes_ordered
                    db.commit()
                elif total_to_be_recieved <= 0:
                    break
            continue

        elif order_quantity <= total_to_be_recieved:
            print(f"\n\n\n\nRecieved more than what is pending to recieve\n\n\n\n")
            next_id_val = db.execute(select(reception_id.next_value())).scalar_one()
            generated_recieved_id = f"REC{next_id_val:08d}"
            for package in range(int(pending_to_recieve)):
                delivery_db.append(models.Receptions(
                    reception_id = generated_recieved_id,
                    package_uuid=str(uuid4()),
                    product_id=delivery.product_id,
                    order_id=delivery.order_id,
                    reception_date=datetime.now(),
                    to_audit=choices([False, True], weights=[1-audit,audit], k=1)[0],
                    on_time=delivery.on_time,
                    package_quality=choices(['good', 'bad'], weights=[0.97,0.03], k=1)[0]
                    )
                )
            packages_to_return.append(delivery.quantity_recieved - pending_to_recieve)
            
            
            continue

    db.add_all(delivery_db)
    if len(audits_db) > 0:
        db.add_all(audits_db)

    if len(order_updates) > 0:
        db.add_all(order_updates)
    db.commit()
    return {"message":"Added deliveries","accepted_packages":delivery_db, "packages_to_return":packages_to_return}





