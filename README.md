# LaundryCare — Laundry & Dry-Cleaning Management System

A beginner-friendly Flask and PostgreSQL project for managing laundry customers, services, orders, and payments. It uses five database tables and has separate administrator and staff roles.

## Features

- Secure login with hashed passwords
- Admin and staff roles
- Dashboard summary cards and recent orders
- Customer management and search
- Service pricing management
- Order creation with quantity × service price
- Order status updates: Pending, Processing, Ready, Delivered
- Full or partial payment recording and balance calculation
- Payment history
- Admin-only user management and service activation/deactivation
- Responsive Bootstrap dashboard

## Requirements

- Python 3.10+
- PostgreSQL
- VS Code (recommended)

## Setup on Windows / PowerShell

1. Create and activate a virtual environment:

   ```powershell
   py -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

2. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

3. Create the PostgreSQL database:

   ```sql
   CREATE DATABASE laundrycare_db;
   ```

4. Copy `.env.example` to `.env`, then edit `DATABASE_URL` with your PostgreSQL username and password. Change `SECRET_KEY` to a long random secret.

   Example:

   ```dotenv
   SECRET_KEY=use-a-long-random-secret-here
   DATABASE_URL=postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/laundrycare_db
   ```

   If the password contains URL-reserved characters, URL-encode the password in the URL.

5. Create the tables and starter services:

   ```powershell
   flask --app app init-db
   ```

6. Create the first admin account:

   ```powershell
   flask --app app create-admin
   ```

   Follow the prompts to enter an admin username and password. Use a strong password.

7. Start the application:

   ```powershell
   flask --app app run --debug
   ```

8. Open `http://127.0.0.1:5000` in your browser and sign in with the admin account you created.

## Roles

- **Admin:** can use all management features, create accounts, activate/deactivate services, and delete customers who have no orders.
- **Staff:** can manage customers, create orders, update statuses, and record payments. Staff cannot manage users or deactivate services.

## Database tables

1. `users`
2. `customers`
3. `services`
4. `orders`
5. `payments`

Tables are created by the `flask --app app init-db` command. For a student project, `db.create_all()` is used for the initial schema. For future schema changes, use Flask-Migrate migrations.

## Billing notes

An order has one service and one quantity. The total is saved at order creation as `service price × quantity`, so a later service price change does not alter existing orders. Payments can be partial; the order balance is the total minus completed payments.

## Important security notes

- Do not commit `.env` to source control.
- Passwords are stored as Werkzeug password hashes.
- Change the development secret key before using the app beyond local development.
- This is a learning project; before public deployment, add CSRF protection (for example Flask-WTF), secure cookie settings, production server configuration, backups, and additional validation.

## Troubleshooting

- **`DATABASE_URL is missing`:** make sure `.env` exists in the project root and contains `DATABASE_URL`.
- **Could not connect to server:** check that PostgreSQL is running, the database exists, and credentials are correct.
- **Password authentication failed:** verify your PostgreSQL username/password in `.env`.
- **PowerShell activation blocked:** run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` and activate again.
