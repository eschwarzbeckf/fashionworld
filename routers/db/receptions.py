from fastapi import APIRouter, status, HTTPException
from main import reception_id
from validations import RecievedPackage
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List

router = APIRouter(
    prefix="api/db/receptions"
)

@router.post("/deliveries", status_code=status.HTTP_200_OK)
async def package_recieved(deliveries: List[RecievedPackage], db:Session):
    if deliveries is None:
        raise HTTPException(status_code=400, detail="No order information provided.")
    
    next_id_val = db.execute(select(reception_id.next_value())).scalar_one()
    generated_order_id = f"REC{next_id_val:08d}"
    reception_id.order_id = generated_order_id