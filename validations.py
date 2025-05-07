from pydantic import BaseModel, Field
from typing import List, Literal, Optional

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
    product_id: Optional[str] = Field(default=None, min_length=1, max_length=8, description="The unique identifier for the product.")

class Supplier(BaseModel):
    name: Optional[str] = Field(default=None,min_length=3, max_length=50, description="The name of the supplier.")
    supplier_id: Optional[str] = Field(default=None, min_length=1, max_length=8, description="The unique identifier for the supplier.")

class SupplierProducts(BaseModel):
    supplier: Supplier = Field(default=None, description="The supplier name.")
    data: List[Product] = Field(default=[], description="List of products.")

class Item(BaseModel):
    product_id: str = Field(default=None, min_length=1, max_length=8, description="The unique identifier for the product.")
    boxes_ordered: int = Field(default=1, description="The number of boxes ordered.")
    order_id: Optional[str] = Field(default=None, min_length=1, max_length=8, description="The unique identifier for the order.")
