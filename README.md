# VASTRAM E-Commerce Website

VASTRAM is a Django-based ecommerce website for browsing and purchasing traditional and occasion wear. The project includes customer accounts, product variants, offers, carts, wishlists, order tracking, return/exchange requests, inventory management, and a custom admin dashboard.

## Features

### Storefront

- Homepage with hero carousel, bridal collections, category collections, and special offers.
- Product listing with category, search, size, and availability support.
- Product detail pages with variant information, stock status, pricing, offers, image thumbnails, and image viewer.
- Responsive navigation with search, wishlist, cart, orders, and account access.
- Wishlist support for authenticated and guest users.

### Customer Accounts and Orders

- User registration, login, profile, and saved addresses.
- Cart and buy-now checkout flows.
- Variant and size-aware cart items.
- Order history and order detail pages.
- Order progress tracking for Pending, Confirmed, Shipped, and Delivered states.
- Return and exchange requests for delivered orders.
- Customer-visible return status, resolution, and admin notes.

### Offers and Pricing

- Time-bound product variant offers with start and end dates.
- Automatic active-offer checks based on the current time.
- Original, updated, offer, and restored-after-offer price history.
- Expired homepage offers display the current base price instead of an expired discount.
- Offer history is shown with offers; regular product price history excludes offer-linked variants.

### Inventory

- Stock is reserved atomically when an order is placed.
- Checkout rejects orders that exceed available stock.
- Dashboard inventory totals show available, pending, sold, and low-stock quantities.
- Admins can restore stock manually.
- Cancelled orders restore reserved stock once.
- Completed returns can restore stock after returned items are received and inspected.

### Admin Dashboard

- Responsive admin shell with sidebar navigation and mobile drawer.
- Dashboard charts for monthly orders, order value, and order status.
- Server-side searchable, sortable, paginated data tables for:
  - Products
  - Categories
  - Orders
  - Users
  - Offers
  - Regular product price history
  - Product inventory on the dashboard
- Category hierarchy showing main categories, child collections, and product counts.
- Offer table showing price before offer, offer price, dates, and restored price.
- Return-request notifications and admin resolution controls.

## Technology

- Python
- Django 6.0.7
- SQLite for local development
- Bootstrap 5 for admin layout support
- Chart.js for dashboard charts
- Font Awesome for interface icons
- HTML, CSS, and JavaScript templates

## Project Structure

```text
accounts/              Custom user model, authentication, addresses, admin views
cart/                  Cart and checkout preparation logic
ecommerce_project/     Django project settings, URLs, ASGI, and WSGI configuration
home/                  Homepage and contact-page views/models
orders/                Orders, order items, return requests, and order workflows
products/              Products, categories, variants, offers, and price history
wishlist/              Wishlist models and views
static/                Versioned static assets such as homepage images
media/                 User-uploaded product and image files
templates/             Storefront and admin dashboard templates
manage.py              Django management entry point
requirements.txt       Python dependencies
```

## Requirements

- Python 3.12 or newer is recommended for the current project setup.
- A virtual environment.
- Dependencies listed in `requirements.txt`.

## Local Setup

### 1. Clone the repository

```bash
git clone <repository-url>
cd E-commerce-website
```

### 2. Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Windows Command Prompt:

```bat
python -m venv .venv
.venv\Scripts\activate
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Apply migrations

```bash
python manage.py migrate
```

### 5. Create an admin user

```bash
python manage.py createsuperuser
```

The custom admin dashboard is available after login at:

```text
/accounts/admin-dashboard/
```

### 6. Start the development server

```bash
python manage.py runserver
```

Open the storefront at [http://127.0.0.1:8000/](http://127.0.0.1:8000/).

## Static Files and Media

Static files are stored in `static/` and discovered through `STATICFILES_DIRS` in `ecommerce_project/settings.py`. Homepage images and other versioned assets belong in `static/images/` and should be committed to version control.

Uploaded product and user media belong in `media/`. The repository `.gitignore` excludes `media/` and the local SQLite database by default because they are runtime data. In production, configure persistent media storage and a production database separately.

During local development, Django serves media files when `DEBUG` is enabled through the URL configuration.

## Database and Migrations

The local development database is SQLite. Create and apply migrations with:

```bash
python manage.py makemigrations
python manage.py migrate
```

Before committing model changes, verify that no migration is missing:

```bash
python manage.py makemigrations --check --dry-run
```

Important migrations include:

- `orders.0006_returnrequest`: return and exchange requests.
- `orders.0007_orderitem_stock_reserved_orderitem_stock_restored`: stock reservation/restoration flags.
- `products.0010_alter_pricehistory_price_type`: restored-after-offer history type and existing offer backfill.
- `products.0011_backfill_variant_price_baselines`: baseline price history for variants without prior history.

## Testing

Run the complete test suite:

```bash
python manage.py test
```

Run focused tests while developing:

```bash
python manage.py test products.tests
python manage.py test orders.tests
python manage.py test accounts.tests
python manage.py test home.tests
```

Run Django checks:

```bash
python manage.py check
```

## Price History Rules

The project separates normal product pricing from offer pricing:

- `original`: initial base price for a variant.
- `updated`: later base-price changes.
- `offer`: discounted offer price and its validity period.
- `after_offer`: base price restored when an offer ends.

The regular Price History page shows original and updated base-price events for products without offers. Offer-related pricing is shown on the Offers page with price before offer, offer price, offer start/end dates, and restored price.

## Inventory Rules

- A variant's stock is reduced atomically when checkout creates an order.
- Pending inventory is reserved in Pending, Confirmed, and Shipped orders.
- Sold inventory is counted from Delivered orders.
- Cancelled orders restore reserved stock once.
- Returned stock is restored only when an admin marks the return completed and confirms the items were received and inspected.
- Manual restocking is available from the dashboard inventory table.

## Security and Production Notes

The current settings are intended for local development. Before deployment:

- Set `DEBUG = False`.
- Replace the development `SECRET_KEY` with an environment variable.
- Configure `ALLOWED_HOSTS`.
- Configure secure database credentials and persistent storage.
- Configure a real email backend if email notifications are required.
- Configure static file collection and media storage.
- Use HTTPS and secure cookie settings.
- Do not commit `.env`, `db.sqlite3`, media uploads, or virtual environments.

## Common Commands

```bash
# Start the server
python manage.py runserver

# Inspect project configuration
python manage.py check

# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Run all tests
python manage.py test

# Find a static asset
python manage.py findstatic images/example.jpg

# Open the Django shell
python manage.py shell
```

## Current Category Structure

The database currently contains six top-level categories:

- Anarkali: 4 collections
- Bridal Collection: 3 collections
- Kurtis: 4 collections
- Party Wear: 4 collections
- Saree: 4 collections
- Set Mundu: 4 collections

That is 23 child collections in total. The admin Categories table displays the actual database hierarchy and counts rather than assuming every main category has the same number of collections.
