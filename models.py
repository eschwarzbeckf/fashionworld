from database import Base,metadata
from sqlalchemy import Integer, String, DateTime, Float, ForeignKey, Boolean, PrimaryKeyConstraint, Sequence, ForeignKeyConstraint
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from typing import List

supplier_id = Sequence('supplier_id_seq', start=1, increment=1, metadata=metadata)
reception_id = Sequence('reception_id_seq', start=1, increment=1, metadata=metadata)
order_id = Sequence('order_id_seq', start=1, increment=1, metadata=metadata)
audit_id = Sequence('audit_id_seq', start=1, increment=1, metadata=metadata)
product_id = Sequence('product_id_seq', start=1, increment=1, metadata=metadata)
density_id = Sequence('density_id_seq', start=1, increment=1, metadata=metadata)


class Products(Base):
    __tablename__ = 'products'
    product_id: Mapped[str] = mapped_column(String(9), unique=True, nullable=False, index=True, primary_key=True)
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
    product_id_receptions: Mapped[List["Receptions"]] = relationship(back_populates="parent_products")
    product_id_audits: Mapped[List["Audits"]] = relationship(back_populates="parent_products")
    products_id_productsdefects: Mapped[List["ProductsDefects"]] = relationship(back_populates="parent_products")
    products_id_reportedincidents: Mapped[List["ReportedIncidents"]] = relationship(back_populates="parent_products")
    products_id_productsdefectsrate: Mapped[List["ProductsDefectsRate"]] = relationship(back_populates="parent_products")
    products_id_inventory: Mapped[List["Inventory"]] = relationship(back_populates="parent_products")
    products_id_shipments: Mapped[List["Shipments"]] = relationship(back_populates="parent_products")
    

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
    product_id:Mapped[str] = mapped_column(String(9), ForeignKey('products.product_id', ondelete="CASCADE") , index=True, nullable=True)
    created_date:Mapped[DateTime] = mapped_column(DateTime, nullable=False,default=func.now())
    
    parent_products: Mapped["Products"] = relationship(back_populates="product_id_supplierprod")
    parent_suppliers: Mapped["Suppliers"] = relationship(back_populates="supplier_id_supplierprod")

    __table_args__ = (
        PrimaryKeyConstraint('supplier_id', 'product_id', name='pk_supplier_product'),
    )

class Packaging(Base):
    __tablename__ = 'packaging'
    product_id:Mapped[str] = mapped_column(String(9), ForeignKey('products.product_id', ondelete="CASCADE"), nullable=False, index=True)
    revision:Mapped[int] = mapped_column(Integer, nullable=False)
    suggested_folding_method:Mapped[str] = mapped_column(String(25), nullable=False)
    suggested_quantity:Mapped[float] = mapped_column(Float, nullable=False)
    suggested_layout:Mapped[str] = mapped_column(String(25), nullable=False)
    created_date:Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    last_updated_date:Mapped[DateTime] = mapped_column(DateTime, nullable=True)

    parent_products:Mapped["Products"] = relationship(back_populates="product_id_packaging")

    __table_args__ = (
        PrimaryKeyConstraint('product_id','revision',name='pk_product_id_revision'),
    )

class Density(Base):
    __tablename__="density"
    report_id:Mapped[str] = mapped_column(String(10), unique=True, nullable=False, index=True, primary_key=True)
    date_created: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    date_of_report:Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    product_id:Mapped[str] = mapped_column(String(9), ForeignKey('products.product_id', ondelete="CASCADE"))
    garment_type:Mapped[str] = mapped_column(String(50), nullable=False)
    material: Mapped[str] = mapped_column(String(50), nullable=False)
    size: Mapped[str] = mapped_column(String(5), nullable=True)
    collection: Mapped[str] = mapped_column(String(25), nullable=True)
    weight: Mapped[float] = mapped_column(Float(3), nullable=False)
    weight_units: Mapped[str] = mapped_column(String(5), nullable=False, default="kg")
    suggested_folding_method:Mapped[str] = mapped_column(String(25), nullable=False)
    suggested_quantity:Mapped[float] = mapped_column(Float, nullable=False)
    suggested_layout:Mapped[str] = mapped_column(String(25), nullable=False)
    packaging_quality: Mapped[str] = mapped_column(String(25), nullable=False)

    parent_products: Mapped["Products"] = relationship(back_populates="product_id_density")

class Orders(Base):
    __tablename__ = 'orders'
    order_id:Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    item_no:Mapped[int] = mapped_column(Integer, nullable=False)
    product_id:Mapped[str] = mapped_column(String(9), ForeignKey('products.product_id', ondelete="CASCADE"), nullable=False, index=True)
    boxes_ordered:Mapped[int] = mapped_column(Integer, nullable=False)
    order_placed_date:Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    supplier_order_id:Mapped[str] = mapped_column(String(50), nullable=True, index=True)
    order_confirmed_date:Mapped[DateTime] = mapped_column(DateTime, nullable=True) # When supplier confirmed order
    order_due_date:Mapped[DateTime] = mapped_column(DateTime, nullable=True) # TAT of order
    order_filled_date:Mapped[DateTime] = mapped_column(DateTime, nullable=True) # when order was completed (last material recieved)
    order_status:Mapped[str] = mapped_column(String(25), nullable=False, default="pending") # Status of order
    last_updated:Mapped[DateTime] = mapped_column(DateTime, nullable=True)

    parent_products: Mapped["Products"] = relationship(back_populates="product_id_orderitems")
    order_id_receptions: Mapped[List["Receptions"]] = relationship(back_populates="parent_orders")
    order_id_reportedissues: Mapped[List["ReportedIncidents"]] = relationship(back_populates="parent_orders")
    order_id_inventory: Mapped[List["Inventory"]] = relationship(back_populates="parent_orders")
    order_id_shipments: Mapped[List["Shipments"]] = relationship(back_populates="parent_orders")

    __table_args__ = (
        PrimaryKeyConstraint('order_id','item_no', name='pk_order_item'),
    )

class Audits(Base):
    __tablename__ = 'audits'
    audit_id:Mapped[str] = mapped_column(String(12), unique=True, nullable=False, index=True, primary_key=True)
    audit_plan_name:Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    reception_id:Mapped[str] = mapped_column(String(12), ForeignKey('receptions.reception_id', ondelete="CASCADE"), nullable=False, index=True)
    product_id:Mapped[str] = mapped_column(String(9), ForeignKey('products.product_id', ondelete="CASCADE"), nullable=False, index=True)
    package_uuid:Mapped[str] = mapped_column(String(36), ForeignKey('receptions.package_uuid',ondelete="CASCADE"), nullable=False, index=True)
    created_date:Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    packaging_quality:Mapped[str] = mapped_column(String(5), nullable=False)
    issue_description:Mapped[str] = mapped_column(String(50), nullable=False)
    cost_impact:Mapped[float] = mapped_column(Float(3), nullable=True)
    audit_date:Mapped[DateTime] = mapped_column(DateTime, nullable=True)

    parent_products: Mapped["Products"] = relationship("Products",
                                                      back_populates="product_id_audits")
    parent_reception: Mapped["Receptions"] = relationship("Receptions",
                                                          foreign_keys=[reception_id,package_uuid],
                                                          primaryjoin="and_(Receptions.reception_id == Audits.reception_id, Receptions.package_uuid == Audits.package_uuid)",
                                                          back_populates="reception_id_audits")
class Receptions(Base):
    __tablename__ = 'receptions'
    reception_id:Mapped[str] = mapped_column(String(12), nullable=False, index=True)
    package_uuid:Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    product_id:Mapped[str] = mapped_column(String(9), ForeignKey('products.product_id', ondelete="CASCADE"), nullable=False, index=True)
    order_id:Mapped[str] = mapped_column(String(8), ForeignKey('orders.order_id', ondelete="CASCADE"), nullable=False, index=True)
    reception_date:Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    on_time: Mapped[bool] = mapped_column(Boolean, nullable=False)
    package_quality: Mapped[str] = mapped_column(String(5), nullable=False)

    parent_orders: Mapped["Orders"] = relationship(back_populates="order_id_receptions")
    parent_products:  Mapped["Products"] = relationship("Products",back_populates="product_id_receptions")
    reception_id_audits: Mapped[List["Audits"]] = relationship("Audits",
                                                               foreign_keys="[Audits.reception_id,Audits.package_uuid]",
                                                               primaryjoin="and_(Audits.reception_id == Receptions.reception_id, Audits.package_uuid == Receptions.package_uuid)",
                                                               back_populates="parent_reception")


    __table_args__= (
        PrimaryKeyConstraint('reception_id','package_uuid', name='pk_receptions'),
    )

class Scorecard(Base):
    __tablename__ = 'scorecard'
    supplier_id: Mapped[str] = mapped_column(String(9),ForeignKey('suppliers.supplier_id',ondelete="CASCADE"), index=True, nullable=False)
    num_month: Mapped[int] =mapped_column(Integer, nullable=False, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    packages_handled: Mapped[int] = mapped_column(Integer, nullable=False)
    bad_packaging: Mapped[int] = mapped_column(Integer, nullable=False)
    total_incidents: Mapped[int] = mapped_column(Integer, nullable=False)
    cost_per_incident: Mapped[float] = mapped_column(Float(2),nullable=False)
    currency: Mapped[str] = mapped_column(String(5),nullable=False, default="EUR")
    on_time_delivery:Mapped[int] = mapped_column(Integer,nullable=False)
    anomalies_detected:Mapped[int] = mapped_column(Integer,nullable=False)

    parent_suppliers: Mapped["Suppliers"] = relationship(back_populates="supplier_id_scorecard")

    __table_args__= (
        PrimaryKeyConstraint('supplier_id','num_month','year', name='pk_scorecard'),
    )

class ProductsDefects(Base):
    __tablename__ ="products_defects"
    uuid: Mapped[str] = mapped_column(String(36), primary_key=True,unique=True,nullable=False, index=True)
    product_id: Mapped[str] = mapped_column(String(9), ForeignKey('products.product_id', ondelete="CASCADE"), nullable=False, index=True)
    issue: Mapped[str] = mapped_column(String(50), nullable=False)
    cost_impact: Mapped[float] = mapped_column(Float(2), nullable=True)

    parent_products:Mapped["Products"] = relationship(back_populates="products_id_productsdefects")
    productdefects_uuid_reportedissues:Mapped["ReportedIncidents"] = relationship(back_populates="parent_productsdefects")
    uuid_inventory: Mapped[List["Inventory"]] = relationship(back_populates="parent_productsdefects")
    uuid_shipments: Mapped[List["Shipments"]] = relationship(back_populates="parent_productsdefects")

class ReportedIncidents(Base):
    __tablename__ = "reported_incidents"
    incident_id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True, index=True)
    uuid: Mapped[str] = mapped_column(String(36),ForeignKey("products_defects.uuid",ondelete="CASCADE"), nullable=False, index=True)
    date_reported: Mapped[DateTime] = mapped_column(DateTime,nullable=False)
    product_id: Mapped[str] = mapped_column(String(9), ForeignKey('products.product_id', ondelete="CASCADE"), nullable=False, index=True)
    order_id:Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    item_no:Mapped[str] = mapped_column(Integer, nullable=False, index=True)
    cost_impact: Mapped[float] = mapped_column(Float(2), nullable=True)

    parent_products:Mapped["Products"] = relationship(back_populates="products_id_reportedincidents")
    parent_orders:Mapped["Orders"] = relationship(back_populates="order_id_reportedissues",foreign_keys=[order_id,item_no], primaryjoin="and_(Orders.order_id == ReportedIncidents.order_id, Orders.item_no == ReportedIncidents.item_no)")
    parent_productsdefects:Mapped["ProductsDefects"] = relationship(back_populates="productdefects_uuid_reportedissues")

    __table_args__=(
        ForeignKeyConstraint(
            ['order_id', 'item_no'],
            ['orders.order_id', 'orders.item_no'],
            ondelete="CASCADE"
        ),
    )

class ProductsDefectsRate(Base):
    __tablename__ = "products_defects_rate"
    record: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[str] = mapped_column(String(9),ForeignKey("products.product_id",ondelete="CASCADE") ,nullable=False, index=True)
    suggested_folding_method:Mapped[str] = mapped_column(String(25), nullable=False)
    suggested_quantity:Mapped[float] = mapped_column(Float, nullable=False)
    suggested_layout:Mapped[str] = mapped_column(String(25), nullable=False)
    package_quality: Mapped[str] = mapped_column(String(10),nullable=False, index=True)
    package_quality_rate: Mapped[float] = mapped_column(Float(4), nullable=False)
    issue_description: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    defect_rate: Mapped[float] = mapped_column(Float(4), nullable=False)

    parent_products:Mapped["Products"] = relationship(back_populates="products_id_productsdefectsrate")

class Incidents(Base):
    __tablename__="incidents"
    incident_id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True,index=True)
    product_id: Mapped[str] = mapped_column(String(9), ForeignKey('products.product_id', ondelete="CASCADE"), nullable=False, index=True)
    supplier_id: Mapped[str] = mapped_column(String(8), ForeignKey('suppliers.supplier_id', ondelete="CASCADE"), index=True, nullable=True)
    date_of_incident: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    issue_description: Mapped[str] = mapped_column(String(40), nullable=False)
    cost_impact: Mapped[float] = mapped_column(Float(2), nullable=False)
    currency: Mapped[str] = mapped_column(String(5),nullable=False, default="EUR")

class Inventory(Base):
    __tablename__ = "inventory"
    inventory_no: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True, index=True)
    audit_plan_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    order_id: Mapped[str] = mapped_column(String(8), ForeignKey('orders.order_id', ondelete="CASCADE"), nullable=False, index=True)
    uuid: Mapped[str] = mapped_column(String(36), ForeignKey('products_defects.uuid', ondelete="CASCADE"), nullable=False, index=True)
    product_id: Mapped[str] = mapped_column(String(9), ForeignKey('products.product_id', ondelete="CASCADE"), nullable=False, index=True)
    order_status: Mapped[str] = mapped_column(String(25), nullable=False, index=True)
    rework_cost: Mapped[float] = mapped_column(Float(2), nullable=True)

    parent_products:Mapped["Products"] = relationship(back_populates="products_id_inventory")
    parent_orders:Mapped["Orders"] = relationship(back_populates="order_id_inventory")
    parent_productsdefects:Mapped["ProductsDefects"] = relationship(back_populates="uuid_inventory")

class Shipments(Base):
    __tablename__ = "shipments"
    shipment_id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True, index=True)
    product_id: Mapped[str] = mapped_column(String(9), ForeignKey('products.product_id', ondelete="CASCADE"), nullable=False, index=True)
    uuid: Mapped[str] = mapped_column(String(36), ForeignKey('products_defects.uuid', ondelete="CASCADE"), nullable=False, index=True)
    audit_plan_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    order_id: Mapped[str] = mapped_column(String(8), ForeignKey('orders.order_id', ondelete="CASCADE"), nullable=False, index=True)
    issue_description: Mapped[str] = mapped_column(String(50), nullable=False)
    cost_impact: Mapped[float] = mapped_column(Float(2), nullable=False)

    parent_products:Mapped["Products"] = relationship(back_populates="products_id_shipments")
    parent_orders:Mapped["Orders"] = relationship(back_populates="order_id_shipments")
    parent_productsdefects:Mapped["ProductsDefects"] = relationship(back_populates="uuid_shipments")
    