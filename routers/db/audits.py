from fastapi import APIRouter
from sqlalchemy import Sequence
from database import metadata

audit_id = Sequence('audit_id_seq', start=1, increment=1, metadata=metadata)

router = APIRouter(
    prefix="/api/db/audits"
)