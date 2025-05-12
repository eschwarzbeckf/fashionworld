from fastapi import APIRouter, status, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from validations import PlaceOrder, ConfirmOrder
import models
from main import order_id
from typing import List

router = APIRouter(
    prefix="/api/db/orders"
)


@router.post("/place", status_code=status.HTTP_201_CREATED)
async def place_order(orders: List[PlaceOrder], db: Session):
    if not orders:
        raise HTTPException(status_code=400, detail="No order information provided.")
    
    order_ids = []
    db_orders = []
    for order in orders:
        next_id_val = db.execute(select(order_id.next_value())).scalar_one()
        generated_order_id = f"ORD{next_id_val:05d}"
        order.order_id = generated_order_id
        for i,item in enumerate(order.items):
            db_orders.append(models.Orders(
                order_id=order.order_id,
                item_no=i+1,
                product_id=item.product_id,
                boxes_ordered=item.boxes_ordered,
                order_placed_date=order.order_placed_date
                )
            )

    db.add_all(db_orders)
    db.commit()
    return {"message": "Order placed successfully", "order_id": order_ids, "order": orders}

@router.put("/api/db/orders/confirm", status_code=status.HTTP_202_ACCEPTED)
async def confirm_order(orders: List[ConfirmOrder], db:Session):
    if orders is None:
        raise HTTPException(status_code=400, detail="No order information provided.")
    
    db_orders = []
    not_found = []
    for order in orders:
        db_order = db.query(models.Orders).filter(models.Orders.order_id==order.order_id).all()
        if db_order:
            for order_update in db_order:
                db_orders.append(order_update.order_id)
                order_update.order_confirmed_date = order.order_confirmed_date
                order_update.order_status = order.order_status
                order_update.supplier_order_id = order.supplier_order_id
                order_update.last_updated = order.last_updated
        else:
            not_found.append(order.order_id)

    db.commit()
    return {"message":"Orders Confirmed", "orders_id":db_orders, "orders_not_found":not_found}