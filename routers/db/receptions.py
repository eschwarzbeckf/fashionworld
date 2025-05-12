from fastapi import APIRouter, status, HTTPException, Depends
from validations import RecievedPackage
from sqlalchemy.orm import Session
from sqlalchemy import select, Sequence
from database import metadata, get_db
from typing import List, Annotated

reception_id = Sequence('reception_id_seq', start=1, increment=1, metadata=metadata)

router = APIRouter(
    prefix="/api/db/receptions"
)

db_dependency = Annotated[Session, Depends(get_db)]

@router.post("/deliveries", status_code=status.HTTP_200_OK)
async def package_recieved(deliveries: List[RecievedPackage], db:db_dependency):
    if deliveries is None:
        raise HTTPException(status_code=400, detail="No order information provided.")
    
    next_id_val = db.execute(select(reception_id.next_value())).scalar_one()
    generated_order_id = f"REC{next_id_val:08d}"
    reception_id.order_id = generated_order_id