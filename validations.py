from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from datetime import datetime
from random import choices

class ModelandText(BaseModel):
    model_name: str = Field(default="gemma:2b", description="The name of the model to use for processing the email content.")
    text: str = Field(min_length=1, description="The text of the email.")

class Product(BaseModel):
    garment_type: Optional[Literal['jacket','shorts','sweater','skirt','shirt','t-shirt','coat','pants','dress','suit','blouse','hoodie']] = Field(default=None, description="The type of garment.")
    material: Optional[Literal['cotton', 'polyester', 'silk', 'linen', 'wool', 'denim']] = Field(default=None, description="The material of the garment.")
    size: Optional[Literal['xs','s','m','l','xl','xxl']] = Field(default=None, description="The size of the garment.")
    collection: Optional[Literal['summer','winter','fall','spring']] = Field(default=None, description="The collection of the garment.")
    weight_units: Optional[Literal['kg']] = Field(default="g", description="The unit of weight, default is grams.")
    weight: Optional[float] = Field(default=None,description="The weight of the garment.")
    product_id: Optional[str] = Field(default=None, min_length=1, max_length=9, description="The unique identifier for the product.")

class Supplier(BaseModel):
    name: Optional[str] = Field(default=None,min_length=3, max_length=50, description="The name of the supplier.")
    supplier_id: Optional[str] = Field(default=None, min_length=1, max_length=8, description="The unique identifier for the supplier.")

class SupplierProducts(BaseModel):
    supplier: Supplier = Field(default=None, description="The supplier name.")
    data: List[Product] = Field(default=[], description="List of products.")

class Item(BaseModel):
    product_id: str = Field(default=None, min_length=1, max_length=9, description="The unique identifier for the product.")
    boxes_ordered: int = Field(default=1, description="The number of boxes ordered.")

class PlaceOrder(BaseModel):
    order_id: Optional[str] = Field(description="Id of the order", default=None)
    order_placed_date: datetime = Field(description="Date when order was placed/created", default=datetime.now())
    items: List[Item] = Field(description="List of the items in the order")

class ConfirmOrder(BaseModel):
    order_id: str = Field(description="Id of the order")
    supplier_order_id: str = Field(description="Supplier order number on their end", default=None)
    order_confirmed_date:Optional[datetime] = Field(description="Date when order is confirmed", default=datetime.now())
    order_status:Optional[str] = Field(description="Status of the order", default="confirmed")
    last_updated:Optional[datetime] = Field(description="Last time record was updated", default=datetime.now())

class RecievedDelivery(BaseModel):
    order_id: str = Field(description="Id of the order")
    product_id: str = Field(description="Id of the product that its being scanned")
    reception_date: datetime = Field(description="date of the reception", default=datetime.now())
    quantity_recieved: int = Field(description="total boxes recieved", gt=0)
    on_time: Optional[bool] = Field(description="If delivery was recieved on the accorded lead time", default=choices([True, False], weights=[0.8,0.2], k=1)[0])
    package_quality: Optional[Literal['good','bad']] = Field(description="Quality of Package", default='good')

class UpdatePackage(BaseModel):
    product_id: str = Field(description="Id of the product to update")
    new_method: Optional[Literal['method1','method2','method3']] = Field(description="New Method", default=None)
    new_layout: Optional[Literal['layouta','layoutb','layoutc','layoutd','layoute','layoutf','layoutg','layouth']] = Field(description="new Layout", default=None)
    new_suggested_quantity: Optional[int] = Field(description="New packaging quantity per box", default=None)
    last_updated: datetime = Field(description="Updated time", default=datetime.now())

class ItemToAudit(BaseModel):
    reception_id: str = Field(description="Reception ID")
    package_uuid: str = Field(description="package UUID to audit",min_length=36,max_length=36)
    product_id: str = Field(description="Product ID")
    package_quality: Literal['good','bad'] = Field(description="Quality of Package")

class OrderFakeData(BaseModel):
    supplier: str = Field(description="Fake Supplier Name")
    product_id: str = Field(description="Product_id")

class AuditOrder(BaseModel):
    order_id: str = Field(description="Order to audit")
class AuditCriteria(BaseModel):
    criteria_name: str = Field(description="Description of the items to look for")
    accept_categories: List[str] = Field(description="Attributes that we consider to accept package")
    reject_categories: List[str] = Field(description="Attributes that we consider to reject package")
    accepted_quantity: int = Field(description="Minimum acceptance of defects quantity",ge=0, default=0)

class AuditPlan(BaseModel):
    audit_plan_name: str = Field(description="Name of the plan", min_length=5, max_length=50)
    audit_criterias: List[AuditCriteria] = Field(description="The Audit Criteria to be used")
    sampling: Literal["random","model"] = Field(description="Type of sampling either using a ML model or random sampling", default="random")
    audit_quantity: int = Field(description="Total amount to check", default=5, gt=0)
