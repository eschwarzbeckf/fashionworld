from database import Base
from sqlalchemy import Integer, String, DateTime, Float, ForeignKey, Boolean, PrimaryKeyConstraint, UniqueConstraint, ForeignKeyConstraint
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from typing import List

class Products(Base):
    __tablename__ = 'products'
    product_id: Mapped[str] = mapped_column(String(8), unique=True, nullable=False, index=True, primary_key=True)
    garment_type:Mapped[str] = mapped_column(String(50), nullable=False)
    material: Mapped[str] = mapped_column(String(50), nullable=False)
    size: Mapped[str] = mapped_column(String(5), nullable=True)
    collection: Mapped[str] = mapped_column(String(25), nullable=True)
    weight: Mapped[float] = mapped_column(Float(3), nullable=False)
    weight_units: Mapped[str] = mapped_column(String(5), nullable=False, default="kg")
    created_date:Mapped[DateTime] = mapped_column(DateTime, nullable=False,default=func.now())
    active:Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    
    product_id_supplierprod: Mapped[List["SuppliersProducts"]] = relationship(back_populates="parent_products")
    product_id_packaging: Mapped[List["Packaging"]] = relationship(back_populates="parent_products")
    product_id_density: Mapped[List["Density"]] = relationship(back_populates="parent_products")
    product_id_orderitems: Mapped[List["Orders"]] = relationship(back_populates="parent_products")
    product_id_incidents: Mapped[List["Incidents"]] = relationship(back_populates="parent_products")
    

class Suppliers(Base):
    __tablename__ = 'suppliers'
    supplier_id: Mapped[str] = mapped_column(String(8), unique=True, nullable=False, index=True, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    created_date:Mapped[DateTime] = mapped_column(DateTime, nullable=False,default=func.now())
    active:Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    
    supplier_id_supplierprod: Mapped[List["SuppliersProducts"]] = relationship(back_populates="parent_suppliers")
    supplier_id_scorecard: Mapped[List["Scorecard"]] = relationship(back_populates="parent_suppliers")

class SuppliersProducts(Base):
    __tablename__ = 'suppliers_products'
    supplier_id:Mapped[str] = mapped_column(String(8), ForeignKey('suppliers.supplier_id', ondelete="CASCADE"), index=True, nullable=True)
    product_id:Mapped[str] = mapped_column(String(8), ForeignKey('products.product_id', ondelete="CASCADE") , index=True, nullable=True)
    created_date:Mapped[DateTime] = mapped_column(DateTime, nullable=False,default=func.now())
    
    parent_products: Mapped["Products"] = relationship(back_populates="product_id_supplierprod")
    parent_suppliers: Mapped["Suppliers"] = relationship(back_populates="supplier_id_supplierprod")

    __table_args__ = (
        PrimaryKeyConstraint('supplier_id', 'product_id', name='pk_supplier_product'),
    )

class Packaging(Base):
    __tablename__ = 'packaging'
    product_id:Mapped[str] = mapped_column(String(8), ForeignKey('products.product_id', ondelete="CASCADE"), nullable=False, index=True)
    revision:Mapped[int] = mapped_column(Integer, nullable=False)
    suggested_folding_method:Mapped[str] = mapped_column(String(25), nullable=False)
    suggested_quantity:Mapped[float] = mapped_column(Float, nullable=False)
    suggested_layout:Mapped[str] = mapped_column(String(25), nullable=False)
    created_date:Mapped[DateTime] = mapped_column(DateTime, nullable=False, default=func.now())
    last_updated_date:Mapped[DateTime] = mapped_column(DateTime, nullable=True)

    parent_products:Mapped["Products"] = relationship(back_populates="product_id_packaging")

    __table_args__ = (
        PrimaryKeyConstraint('product_id','revision',name='pk_product_id_revision'),
    )

class Density(Base):
    __tablename__="density"
    product_id:Mapped[str] = mapped_column(String(8), ForeignKey('products.product_id', ondelete="CASCADE"),primary_key=True)
    date_of_report:Mapped[DateTime] = mapped_column(DateTime, nullable=False)

    parent_products: Mapped["Products"] = relationship(back_populates="product_id_density")

class Orders(Base):
    __tablename__ = 'orders'
    order_id:Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    item_no:Mapped[str] = mapped_column(Integer, nullable=False)
    product_id:Mapped[str] = mapped_column(String(8), ForeignKey('products.product_id', ondelete="CASCADE"), nullable=False, index=True)
    boxes_ordered:Mapped[int] = mapped_column(Integer, nullable=False)
    order_placed_date:Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    supplier_order_id:Mapped[str] = mapped_column(String(20), nullable=True, index=True)
    order_confirmed_date:Mapped[DateTime] = mapped_column(DateTime, nullable=True) # When supplier confirmed order
    order_due_date:Mapped[DateTime] = mapped_column(DateTime, nullable=True) # TAT of order
    order_filled_date:Mapped[DateTime] = mapped_column(DateTime, nullable=True) # when order was completed (last material recieved)
    order_status:Mapped[str] = mapped_column(String(25), nullable=False, default="pending") # Status of order
    last_updated:Mapped[DateTime] = mapped_column(DateTime, nullable=True)

    parent_products: Mapped["Products"] = relationship(back_populates="product_id_orderitems")
    order_id_receptions: Mapped[List["Receptions"]] = relationship(back_populates="parent_orders")

    __table_args__ = (
        PrimaryKeyConstraint('order_id','item_no', name='pk_order_item'),
    )

class Receptions(Base):
    __tablename__ = 'receptions'
    reception_id:Mapped[str] = mapped_column(String(12), unique=True, nullable=False, index=True, primary_key=True)
    order_id:Mapped[str] = mapped_column(String(8), ForeignKey('orders.order_id', ondelete="CASCADE"), nullable=False, index=True)
    product_id:Mapped[str] = mapped_column(String(8), ForeignKey('products.product_id', ondelete="CASCADE"), nullable=False, index=True)
    reception_date:Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    quantity_received:Mapped[int] = mapped_column(Integer, nullable=False)
    to_audit:Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    on_time: Mapped[bool] = mapped_column(Boolean, nullable=False)

    parent_orders: Mapped["Orders"] = relationship(back_populates="order_id_receptions")


class Audits(Base):
    __tablename__ = 'audits'
    inspection_id:Mapped[str] = mapped_column(String(12), unique=True, nullable=False, index=True, primary_key=True)
    reception_id:Mapped[str] = mapped_column(String(12), ForeignKey('receptions.reception_id', ondelete="CASCADE"), nullable=False, index=True)
    product_id:Mapped[str] = mapped_column(String(8), ForeignKey('products.product_id', ondelete="CASCADE"), nullable=False, index=True)
    inspection_date:Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    real_quantity:Mapped[int] = mapped_column(Integer, nullable=False)
    real_folding_method:Mapped[str] = mapped_column(String(25), nullable=False)
    real_layout:Mapped[str] = mapped_column(String(25), nullable=False)
    real_material:Mapped[str] = mapped_column(String(50), nullable=False)
    real_weight:Mapped[float] = mapped_column(Float(3), nullable=False)
    weight_units:Mapped[str] = mapped_column(String(5), nullable=False, default="kg")
    real_size:Mapped[str] = mapped_column(String(5), nullable=True)
    real_collection:Mapped[str] = mapped_column(String(25), nullable=True)
    audit_date:Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    packaging_quality:Mapped[str] = mapped_column(String(5), nullable=False)
    needs_rework: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    score: Mapped[float] = mapped_column(Float(3), nullable=True)

class Scorecard(Base):
    __tablename__ = 'scorecard'
    supplier_id: Mapped[str] = mapped_column(String(8),ForeignKey('suppliers.supplier_id',ondelete="CASCADE"), index=True, nullable=False)
    num_month: Mapped[int] =mapped_column(Integer, nullable=False, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    month: Mapped[str] = mapped_column(String(15))
    bad_packaging_rate: Mapped[float] = mapped_column(Float, nullable=False)
    total_incidents: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_cost_per_incident: Mapped[float] = mapped_column(Float,nullable=False)
    cost_units: Mapped[str] = mapped_column(String(5),nullable=False, default="EUR")
    on_time_delivery_rate:Mapped[float] = mapped_column(Float,nullable=False)
    anomalies_detected:Mapped[int] = mapped_column(Integer,nullable=False)

    parent_suppliers: Mapped["Suppliers"] = relationship(back_populates="supplier_id_scorecard")

    __table_args__= (
        PrimaryKeyConstraint('supplier_id','num_month','year', name='pk_scorecard'),
    )

class Incidents(Base):
    __tablename__ = 'incidents'
    product_id:Mapped[str] = mapped_column(String(8), ForeignKey('products.product_id', ondelete="CASCADE"), nullable=False, index=True, primary_key=True)
    date_of_incident:Mapped[DateTime] = mapped_column(DateTime,nullable=False)
    issue_description:Mapped[str] = mapped_column(String(50),nullable=False)
    cost_impact:Mapped[float] = mapped_column(Float, nullable=False)

    parent_products: Mapped["Products"] = relationship(back_populates='product_id_incidents')
    

