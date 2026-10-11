import os
from decimal import Decimal, InvalidOperation
from functools import wraps

import click
from dotenv import load_dotenv
from flask import (
    Flask, abort, flash, redirect, render_template, request, session, url_for
)
from flask_migrate import Migrate
from sqlalchemy import or_
from werkzeug.security import check_password_hash, generate_password_hash

from models import db, User, Customer, Service, Order, Payment

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-only-change-this-secret")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

if not app.config["SQLALCHEMY_DATABASE_URI"]:
    raise RuntimeError("DATABASE_URL is missing. Copy .env.example to .env and configure it.")

db.init_app(app)
migrate = Migrate(app, db)

ORDER_STATUSES = ["Pending", "Processing", "Ready", "Delivered"]


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not session.get("user_id"):
                flash("Please log in to continue.", "warning")
                return redirect(url_for("login"))
            user = db.session.get(User, session["user_id"])
            if not user or user.role not in roles:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


@app.context_processor
def inject_globals():
    current_user = db.session.get(User, session["user_id"]) if session.get("user_id") else None
    return {"current_user": current_user, "order_statuses": ORDER_STATUSES, "now": __import__("datetime").datetime.now}


@app.cli.command("init-db")
def init_db():
    """Create database tables and insert starter services."""
    db.create_all()
    defaults = [
        ("Washing", Decimal("25.00")),
        ("Dry Cleaning", Decimal("80.00")),
        ("Ironing", Decimal("15.00")),
        ("Wash & Iron", Decimal("40.00")),
    ]
    for name, price in defaults:
        if not Service.query.filter_by(service_name=name).first():
            db.session.add(Service(service_name=name, price=price))
    db.session.commit()
    click.echo("Database tables are ready. Starter services have been added.")


@app.cli.command("create-admin")
@click.option("--username", prompt=True, help="Admin username")
@click.password_option()
def create_admin(username, password):
    """Create an administrator account."""
    username = username.strip()
    if not username:
        raise click.ClickException("Username cannot be empty.")
    if User.query.filter_by(username=username).first():
        raise click.ClickException("That username already exists.")
    user = User(
        username=username,
        password_hash=generate_password_hash(password),
        role="admin",
    )
    db.session.add(user)
    db.session.commit()
    click.echo(f"Admin account '{username}' created.")


@app.route("/")
def index():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session.clear()
            session["user_id"] = user.user_id
            flash(f"Welcome back, {user.username}!", "success")
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.", "danger")
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    total_customers = Customer.query.count()
    total_orders = Order.query.count()
    pending_orders = Order.query.filter(Order.order_status.in_(["Pending", "Processing"])).count()
    ready_orders = Order.query.filter_by(order_status="Ready").count()
    recent_orders = Order.query.order_by(Order.order_date.desc()).limit(8).all()
    revenue = sum(
        (p.amount for p in Payment.query.filter_by(payment_status="Completed").all()),
        Decimal("0.00"),
    )
    return render_template(
        "dashboard.html",
        total_customers=total_customers,
        total_orders=total_orders,
        pending_orders=pending_orders,
        ready_orders=ready_orders,
        recent_orders=recent_orders,
        revenue=revenue,
    )


@app.route("/customers", methods=["GET", "POST"])
@login_required
def customers():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()
        if not name or not phone:
            flash("Customer name and phone are required.", "danger")
        else:
            db.session.add(Customer(name=name, phone=phone, address=address or None))
            db.session.commit()
            flash("Customer added successfully.", "success")
            return redirect(url_for("customers"))
    search = request.args.get("q", "").strip()
    query = Customer.query
    if search:
        query = query.filter(
            or_(Customer.name.ilike(f"%{search}%"), Customer.phone.ilike(f"%{search}%"))
        )
    customer_list = query.order_by(Customer.name.asc()).all()
    return render_template("customers.html", customers=customer_list)


@app.route("/customers/<int:customer_id>/delete", methods=["POST"])
@role_required("admin")
def delete_customer(customer_id):
    customer = db.session.get(Customer, customer_id) or abort(404)
    if customer.orders:
        flash("This customer has orders and cannot be deleted. You can keep the record for history.", "warning")
    else:
        db.session.delete(customer)
        db.session.commit()
        flash("Customer deleted.", "success")
    return redirect(url_for("customers"))


@app.route("/services", methods=["GET", "POST"])
@login_required
def services():
    if request.method == "POST":
        name = request.form.get("service_name", "").strip()
        price_raw = request.form.get("price", "").strip()
        try:
            price = Decimal(price_raw)
            if not name or price < 0:
                raise InvalidOperation
            if Service.query.filter_by(service_name=name).first():
                flash("A service with that name already exists.", "warning")
            else:
                db.session.add(Service(service_name=name, price=price))
                db.session.commit()
                flash("Service added successfully.", "success")
                return redirect(url_for("services"))
        except (InvalidOperation, ValueError):
            flash("Enter a valid service name and non-negative price.", "danger")
    service_list = Service.query.order_by(Service.service_name.asc()).all()
    return render_template("services.html", services=service_list)


@app.route("/services/<int:service_id>/toggle", methods=["POST"])
@role_required("admin")
def toggle_service(service_id):
    service = db.session.get(Service, service_id) or abort(404)
    service.is_active = not service.is_active
    db.session.commit()
    flash("Service availability updated.", "success")
    return redirect(url_for("services"))


@app.route("/orders", methods=["GET", "POST"])
@login_required
def orders():
    if request.method == "POST":
        try:
            customer_id = int(request.form.get("customer_id", ""))
            service_id = int(request.form.get("service_id", ""))
            quantity = int(request.form.get("quantity", ""))
            customer = db.session.get(Customer, customer_id)
            service = db.session.get(Service, service_id)
            if not customer or not service or not service.is_active:
                raise ValueError
            if quantity <= 0:
                raise ValueError
            total = (Decimal(service.price) * quantity).quantize(Decimal("0.01"))
            order = Order(
                customer_id=customer.customer_id,
                service_id=service.service_id,
                user_id=session["user_id"],
                quantity=quantity,
                total_amount=total,
                order_status="Pending",
            )
            db.session.add(order)
            db.session.commit()
            flash(f"Order #{order.order_id} created. Total: ₹{total:.2f}", "success")
            return redirect(url_for("order_detail", order_id=order.order_id))
        except (ValueError, TypeError, InvalidOperation):
            flash("Choose a valid customer, service, and quantity.", "danger")
    customer_list = Customer.query.order_by(Customer.name.asc()).all()
    service_list = Service.query.filter_by(is_active=True).order_by(Service.service_name.asc()).all()
    search = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    query = Order.query
    if search.isdigit():
        query = query.filter(Order.order_id == int(search))
    elif search:
        query = query.join(Customer).filter(Customer.name.ilike(f"%{search}%"))
    if status in ORDER_STATUSES:
        query = query.filter_by(order_status=status)
    order_list = query.order_by(Order.order_date.desc()).all()
    return render_template(
        "orders.html",
        orders=order_list,
        customers=customer_list,
        services=service_list,
        search=search,
        selected_status=status,
    )


@app.route("/orders/<int:order_id>", methods=["GET", "POST"])
@login_required
def order_detail(order_id):
    order = db.session.get(Order, order_id) or abort(404)
    if request.method == "POST":
        status = request.form.get("order_status", "")
        if status not in ORDER_STATUSES:
            flash("Select a valid order status.", "danger")
        else:
            order.order_status = status
            db.session.commit()
            flash("Order status updated.", "success")
            return redirect(url_for("order_detail", order_id=order_id))
    return render_template("order_detail.html", order=order)


@app.route("/orders/<int:order_id>/payments", methods=["POST"])
@login_required
def add_payment(order_id):
    order = db.session.get(Order, order_id) or abort(404)
    try:
        amount = Decimal(request.form.get("amount", "").strip()).quantize(Decimal("0.01"))
        if amount <= 0 or amount > order.balance_due:
            raise InvalidOperation
        payment = Payment(order_id=order.order_id, amount=amount, payment_status="Completed")
        db.session.add(payment)
        db.session.commit()
        flash("Payment recorded successfully.", "success")
    except (InvalidOperation, ValueError):
        flash("Enter a valid payment amount no greater than the outstanding balance.", "danger")
    return redirect(url_for("order_detail", order_id=order_id))


@app.route("/payments")
@login_required
def payments():
    payment_list = Payment.query.order_by(Payment.payment_date.desc()).all()
    total_received = sum(
        (p.amount for p in payment_list if p.payment_status == "Completed"),
        Decimal("0.00"),
    )
    return render_template("payments.html", payments=payment_list, total_received=total_received)


@app.route("/users", methods=["GET", "POST"])
@role_required("admin")
def users():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "staff")
        if not username or len(password) < 8:
            flash("Username is required and password must be at least 8 characters.", "danger")
        elif role not in ("admin", "staff"):
            flash("Choose a valid role.", "danger")
        elif User.query.filter_by(username=username).first():
            flash("That username already exists.", "warning")
        else:
            db.session.add(User(
                username=username,
                password_hash=generate_password_hash(password),
                role=role,
            ))
            db.session.commit()
            flash("User account created.", "success")
            return redirect(url_for("users"))
    user_list = User.query.order_by(User.username.asc()).all()
    return render_template("users.html", users=user_list)


@app.errorhandler(403)
def forbidden(_error):
    return render_template("error.html", code=403, message="You do not have permission to access this page."), 403


@app.errorhandler(404)
def not_found(_error):
    return render_template("error.html", code=404, message="The page or record could not be found."), 404


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        
    app.run(debug=True, port = 8901)
