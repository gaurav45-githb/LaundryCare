from datetime import datetime
from decimal import Decimal

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CheckConstraint

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="staff")

    __table_args__ = (
        CheckConstraint("role IN ('admin', 'staff')", name="check_user_role"),
    )

    orders = db.relationship("Order", back_populates="created_by")

    def __repr__(self):
        return f"<User {self.username}>"


class Customer(db.Model):
    __tablename__ = "customers"

    customer_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    address = db.Column(db.String(200))

    orders = db.relationship("Order", back_populates="customer")

    def __repr__(self):
        return f"<Customer {self.name}>"


class Service(db.Model):
    __tablename__ = "services"

    service_id = db.Column(db.Integer, primary_key=True)
    service_name = db.Column(db.String(50), unique=True, nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    __table_args__ = (
        CheckConstraint("price >= 0", name="check_service_price"),
    )

    orders = db.relationship("Order", back_populates="service")

    def __repr__(self):
        return f"<Service {self.service_name}>"


class Order(db.Model):
    __tablename__ = "orders"

    order_id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.customer_id"), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey("services.service_id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    order_status = db.Column(db.String(30), nullable=False, default="Pending")
    order_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint("quantity > 0", name="check_order_quantity"),
        CheckConstraint("total_amount >= 0", name="check_order_amount"),
        CheckConstraint(
            "order_status IN ('Pending', 'Processing', 'Ready', 'Delivered')",
            name="check_order_status",
        ),
    )

    customer = db.relationship("Customer", back_populates="orders")
    service = db.relationship("Service", back_populates="orders")
    created_by = db.relationship("User", back_populates="orders")
    payments = db.relationship("Payment", back_populates="order", cascade="all, delete-orphan")

    @property
    def paid_amount(self):
        return sum(
            (p.amount for p in self.payments if p.payment_status == "Completed"),
            Decimal("0.00"),
        )

    @property
    def balance_due(self):
        return self.total_amount - self.paid_amount

    def __repr__(self):
        return f"<Order {self.order_id}>"


class Payment(db.Model):
    __tablename__ = "payments"

    payment_id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.order_id"), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_status = db.Column(db.String(20), nullable=False, default="Completed")
    payment_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint("amount > 0", name="check_payment_amount"),
        CheckConstraint(
            "payment_status IN ('Completed', 'Failed')",
            name="check_payment_status",
        ),
    )

    order = db.relationship("Order", back_populates="payments")

    def __repr__(self):
        return f"<Payment {self.payment_id}>"
