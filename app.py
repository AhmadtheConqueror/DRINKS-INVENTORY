from flask import Flask, render_template, request, redirect, url_for
from flask import send_file
import io
from openpyxl import Workbook

from datetime import datetime
from models import db, Product, Expense, Debt
from models import db, Product, Expense, Debt, Sale  # 👈 import Sale

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()

@app.route('/')
def home():
    return redirect(url_for('inventory'))

# ============================ INVENTORY ============================
@app.route('/inventory', methods=['GET', 'POST'])
def inventory():
    if request.method == 'POST':
        name = request.form['name']
        quantity = int(request.form['quantity'])
        selling_price = float(request.form['selling_price'])
        cost_price = float(request.form['cost_price'])

        new_product = Product(
            name=name,
            quantity=quantity,
            selling_price=selling_price,
            cost_price=cost_price
        )
        db.session.add(new_product)
        db.session.commit()
        return redirect(url_for('inventory'))

    products = Product.query.all()
    return render_template('inventory.html', products=products)
@app.route('/adjust_quantity/<int:product_id>', methods=['POST'])
def adjust_quantity(product_id):
    product = Product.query.get_or_404(product_id)
    try:
        delta = int(request.form['delta'])
        product.quantity += delta
        db.session.commit()
    except ValueError:
        pass  # Optionally flash a message if input is invalid
    return redirect(url_for('inventory'))

    product = Product.query.get(product_id)
    if product:
        if delta < 0 and product.quantity >= abs(delta):
            # Record the sale
            sale = Sale(
                product_id=product.id,
                product_name=product.name,
                quantity_sold=abs(delta),
                unit_price=product.selling_price,
                total_price=abs(delta) * product.selling_price,
                date=datetime.now()
            )
            db.session.add(sale)

        product.quantity += delta
        db.session.commit()
    return redirect(url_for('inventory'))



@app.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    if request.method == 'POST':
        product.name = request.form['name']
        product.quantity = int(request.form['quantity'])
        product.selling_price = float(request.form['selling_price'])
        product.cost_price = float(request.form['cost_price'])
        db.session.commit()
        return redirect(url_for('inventory'))
    return render_template('edit_product.html', product=product)

@app.route('/delete_product/<int:product_id>')
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    return redirect(url_for('inventory'))

# ============================ EXPENSES ============================
@app.route('/expenses', methods=['GET', 'POST'])
def expenses():
    if request.method == 'POST':
        description = request.form['description']
        amount = float(request.form['amount'])
        category = request.form['category']
        new_expense = Expense(
            description=description,
            amount=amount,
            category=category,
            date=datetime.now()
        )
        db.session.add(new_expense)
        db.session.commit()
        return redirect(url_for('expenses'))

    expenses = Expense.query.order_by(Expense.date.desc()).all()
    return render_template('expenses.html', expenses=expenses)

@app.route('/edit_expense/<int:expense_id>', methods=['GET', 'POST'])
def edit_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    if request.method == 'POST':
        expense.description = request.form['description']
        expense.amount = float(request.form['amount'])
        expense.category = request.form['category']
        db.session.commit()
        return redirect(url_for('expenses'))
    return render_template('edit_expense.html', expense=expense)

@app.route('/delete_expense/<int:expense_id>')
def delete_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    db.session.delete(expense)
    db.session.commit()
    return redirect(url_for('expenses'))

# ============================ DEBTS ============================
@app.route('/debts', methods=['GET', 'POST'])
def debts():
    if request.method == 'POST':
        customer_name = request.form['customer_name']
        amount = float(request.form['amount'])
        new_debt = Debt(
            customer_name=customer_name,
            amount=amount,
            status='pending',
            date=datetime.now()
        )
        db.session.add(new_debt)
        db.session.commit()
        return redirect(url_for('debts'))

    debts = Debt.query.order_by(Debt.date.desc()).all()
    return render_template('debts.html', debts=debts)

@app.route('/mark_paid/<int:debt_id>')
def mark_paid(debt_id):
    debt = Debt.query.get_or_404(debt_id)
    if debt:
        debt.status = 'paid'
        db.session.commit()
    return redirect(url_for('debts'))

@app.route('/edit_debt/<int:debt_id>', methods=['GET', 'POST'])
def edit_debt(debt_id):
    debt = Debt.query.get_or_404(debt_id)
    if request.method == 'POST':
        debt.customer_name = request.form['customer_name']
        debt.amount = float(request.form['amount'])
        debt.status = request.form['status'].lower()
        db.session.commit()
        return redirect(url_for('debts'))
    return render_template('edit_debt.html', debt=debt)

@app.route('/delete_debt/<int:debt_id>')
def delete_debt(debt_id):
    debt = Debt.query.get_or_404(debt_id)
    db.session.delete(debt)
    db.session.commit()
    return redirect(url_for('debts'))




# ============================ REPORTS ============================
@app.route('/reports')
def reports():
    products = Product.query.all()
    total_revenue = sum(p.quantity * p.selling_price for p in products)
    total_cost = sum(p.quantity * p.cost_price for p in products)
    profit = total_revenue - total_cost

    expenses = Expense.query.all()
    total_expenses = sum(e.amount for e in expenses)

    pending_debts = Debt.query.filter_by(status='pending').all()
    pending_debt = sum(d.amount for d in pending_debts)

    net_profit = total_revenue - total_expenses

    return render_template('reports.html',
                           total_revenue=total_revenue,
                           total_expenses=total_expenses,
                           profit=profit,
                           net_profit=net_profit,
                           pending_debt=pending_debt)


@app.route('/export_sales')
def export_sales():
    sales = Sale.query.order_by(Sale.date.desc()).all()

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Sales Report"

    # Headers
    sheet.append(["Product Name", "Quantity Sold", "Unit Price", "Total Price", "Date"])

    for sale in sales:
        sheet.append([
            sale.product_name,
            sale.quantity_sold,
            f"{sale.unit_price:.2f}",
            f"{sale.total_price:.2f}",
            sale.date.strftime("%Y-%m-%d %H:%M:%S")
        ])

    output = io.BytesIO()
    workbook.save(output)
    output.seek(0)

    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='sales_report.xlsx'
    )




# ============================ MAIN ============================
if __name__ == '__main__':
    app.run(debug=True)
