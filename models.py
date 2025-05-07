from database import Base
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from typing import List

class Products(Base):
    __tablename__ = 'products'
    product_id: Mapped[str] = mapped_column(String(8), unique=True, nullable=False, index=True, primary_key=True)
    garment_type:Mapped[str] = mapped_column(String(50), nullable=False)
    material: Mapped[str] = mapped_column(String(50), nullable=False)
    size: Mapped[str] = mapped_column(String(5), nullable=False)
    collection: Mapped[str] = mapped_column(String(25), nullable=False)
    weight: Mapped[float] = mapped_column(Float(3), nullable=False)
    weight_units: Mapped[str] = mapped_column(String(5), nullable=False, default="kg")
    created_date:Mapped[DateTime] = mapped_column(DateTime, nullable=False,default=func.now())
    active:Mapped[bool] = mapped_column(String(1), nullable=False, default=True)
    
    product_id_supplierprod: Mapped[List["SuppliersProducts"]] = relationship(back_populates="parent_products")
    product_id_packaging: Mapped[List["Packaging"]] = relationship(back_populates="parent_products")
    product_id_orderitems: Mapped[List["Orders"]] = relationship(back_populates="parent_products")

class Suppliers(Base):
    __tablename__ = 'suppliers'
    supplier_id: Mapped[str] = mapped_column(String(8), unique=True, nullable=False, index=True, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    created_date:Mapped[DateTime] = mapped_column(DateTime, nullable=False,default=func.now())
    active:Mapped[bool] = mapped_column(String(1), nullable=False, default=True)
    
    supplier_id_supplierprod: Mapped[List["SuppliersProducts"]] = relationship(back_populates="parent_suppliers")

class SuppliersProducts(Base):
    __tablename__ = 'suppliers_products'
    id:Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    supplier_id:Mapped[str] = mapped_column(String(8), ForeignKey('suppliers.supplier_id', ondelete="CASCADE"), index=True)
    product_id:Mapped[str] = mapped_column(String(8), ForeignKey('products.product_id', ondelete="CASCADE") , index=True, unique=True)
    created_date:Mapped[DateTime] = mapped_column(DateTime, nullable=False,default=func.now())
    
    parent_products: Mapped["Products"] = relationship(back_populates="product_id_supplierprod")
    parent_suppliers: Mapped["Suppliers"] = relationship(back_populates="supplier_id_supplierprod")

class Packaging(Base):
    __tablename__ = 'packaging'
    product_id:Mapped[str] = mapped_column(String(8), ForeignKey('products.product_id', ondelete="CASCADE"),primary_key=True)
    suggested_folding_method:Mapped[str] = mapped_column(String(25), nullable=False)
    suggested_quantity:Mapped[int] = mapped_column(Float, nullable=False)
    suggested_layout:Mapped[str] = mapped_column(String(25), nullable=False)
    created_date:Mapped[DateTime] = mapped_column(DateTime, nullable=False, default=func.now())

    parent_products: Mapped["Products"] = relationship(back_populates="product_id_packaging")

class Orders(Base):
    __tablename__ = 'orders'
    id:Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    order_id:Mapped[str] = mapped_column(String(8), nullable=False, index=True, primary_key=True)
    product_id:Mapped[str] = mapped_column(String(8), ForeignKey('products.product_id', ondelete="CASCADE"), nullable=False, index=True)
    boxes_ordered:Mapped[int] = mapped_column(Integer, nullable=False)
    created_date:Mapped[DateTime] = mapped_column(DateTime, nullable=False,default=func.now())

    parent_products: Mapped["Products"] = relationship(back_populates="product_id_orderitems")
    order_id_receptions: Mapped[List["Receptions"]] = relationship(back_populates="parent_orders")

class Receptions(Base):
    __tablename__ = 'receptions'
    id:Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    reception_id:Mapped[str] = mapped_column(String(12), unique=True, nullable=False, index=True, primary_key=True)
    order_id:Mapped[str] = mapped_column(String(12), ForeignKey('orders.order_id', ondelete="CASCADE"), nullable=False, index=True)
    product_id:Mapped[str] = mapped_column(String(8), ForeignKey('products.product_id', ondelete="CASCADE"), nullable=False, index=True)
    reception_date:Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    quantity_received:Mapped[int] = mapped_column(Integer, nullable=False)
    packaging_quality:Mapped[str] = mapped_column(String(5), nullable=False)

    parent_orders: Mapped["Orders"] = relationship(back_populates="order_id_receptions")


# class Audits(Base):
#     __tablename__ = 'audits'
#     id:Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
#     inspection_id:Mapped[str] = mapped_column(String(12), unique=True, nullable=False, index=True, primary_key=True)
#     reception_id:Mapped[str] = mapped_column(String(12), ForeignKey('receptions.reception_id', ondelete="CASCADE"), nullable=False, index=True)
#     inspection_date:Mapped[DateTime] = mapped_column(DateTime, nullable=False)
#     real_quantity:Mapped[int] = mapped_column(Integer, nullable=False)
#     real_folding_method:Mapped[str] = mapped_column(String(25), nullable=False)
#     real_layout:Mapped[str] = mapped_column(String(25), nullable=False)
#     audit_date:Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    

