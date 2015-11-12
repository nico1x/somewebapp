from flask import Flask, render_template, request, Response, g, flash, redirect, url_for
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
from flask.ext.script import Manager
from flask.ext.migrate import Migrate, MigrateCommand
from sqlalchemy import event
from functools import wraps
from models import User, Category, Transaction, db
from flask.ext.login import LoginManager, login_user, logout_user,  current_user, login_required

app = Flask(__name__, static_url_path="/static")
app.debug = True
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://root:password@localhost/webappdb"
app.secret_key = "42!!"

db.init_app(app)
migrate = Migrate(app, db)
manager = Manager(app)
manager.add_command('db', MigrateCommand)

login_manager = LoginManager()
login_manager.init_app(app)

login_manager.login_view = 'login'
login_manager.login_message = ""

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

@app.route('/register' , methods=['GET','POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')
    user = User(request.form['firstname'], request.form['lastname'], request.form['username'], request.form['password'])
    url = url_for('login')
    if not user.isExists():
        db.session.add(user)
        db.session.commit()
        #flash('User successfully registered')
    else:
        flash('User already registered')
        url = url_for('register')

    return redirect(url)
 
@app.route('/login',methods=['GET','POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
 
    username = request.form['username']
    password = request.form['password']
    remember_me = False
    if 'remember_me' in request.form:
        remember_me = True
    registered_user = User.query.filter_by(username=username,password=password).first()
    if registered_user is None:
        flash('Username or Password is invalid' , 'error')
        return redirect(url_for('login'))
    login_user(registered_user, remember = remember_me)
    #flash('Logged in successfully')
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.before_request
def before_request():
    g.user = current_user

def net_income():
    return float("{0:.2f}".format(Calculation(Transaction,Category).net_income))
def total_income():
    return float("{0:.2f}".format(Calculation(Transaction,Category).total_income))
def total_expense():
    return float("{0:.2f}".format(Calculation(Transaction,Category).total_expense))
def total_allocation():
    return float("{0:.2f}".format(Calculation(Transaction,Category).total_allocation))

class Calculation(object):

    allocation_rs = None
    allocated_expense_rs = None
    unallocated_expense = None
    expense_rs = None
    net_income = None
    net_allocation = None
    total_income = None
    total_expense = None
    total_allocation = None

    def __init__(self, Transaction, Category):

        self.expense_rs = Transaction.query.filter_by(transaction_type="Expense", user_id=g.user.id).join(Category).with_entities(Category.id, Category.description, func.sum(Transaction.amount).label('total_amount')).group_by(Category.id)

        self.allocation_rs = Transaction.query.filter_by(transaction_type="Allocation", user_id=g.user.id).join(Category).with_entities(Category.id, Category.description, func.sum(Transaction.amount).label('total_amount')).group_by(Category.id)

        explist = []
        for a in self.allocation_rs.all():
            explist.append(a.id)

        gross_unallocated = []
        gross_expense = []
        for e in self.expense_rs:
            gross_expense.append(e.total_amount)
            if not e.id in explist:
                gross_unallocated.append(e.total_amount)

        self.unallocated_expense = sum(gross_unallocated)
        self.total_expense = sum(gross_expense)

        # print explist
        self.allocated_expense_rs = Transaction.query.filter_by(transaction_type="Expense", user_id=g.user.id).join(Category).with_entities(Category.id, Category.description, func.sum(Transaction.amount).label('total_amount')).filter(Category.id.in_(explist)).group_by(Category.id)

        gross_allocation = []
        self.net_allocation = []
        for e in self.allocated_expense_rs.all():
            d = {}
            for a in self.allocation_rs.all():
                if a.id == e.id:
                    d["id"] = e.id
                    d["description"] = e.description
                    d["total_amount"] = a.total_amount - e.total_amount
                    gross_allocation.append(a.total_amount)
            self.net_allocation.append(d)

        income_rs = Transaction.query.filter_by(transaction_type="Income", user_id=g.user.id).join(Category).with_entities(Category.id, Category.description, func.sum(Transaction.amount).label('total_amount')).group_by(Transaction.transaction_type).first()

        self.total_income = income_rs.total_amount
        sum_gross_allocation = sum(gross_allocation)
        self.total_allocation = sum_gross_allocation

        self.net_income = income_rs.total_amount - (sum_gross_allocation + self.unallocated_expense)

@app.route("/test")
@login_required
def test():
    calc = Calculation(Transaction, Category)
    return render_template("test.html", allocation_rs=calc.allocation_rs.all(), expense_rs=calc.expense_rs.all(), net_allocation=calc.net_allocation, net_income=calc.net_income)

@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    loc = "nav-home"
    user = g.user.firstname
    return render_template("index.html", user = user, total_income=total_income(), total_expense=total_expense(), total_allocation=total_allocation(), net_income=net_income(), locid = loc)
#end index

@app.route("/category", methods=["GET", "POST"])
@login_required
def category():
    loc = "nav-category"
    if request.method == "POST" and request.form["action"] == "insert":
        #insert new category
        description = request.form["description"]
        category_type = request.form["categorytype"]
        success = False

        category = Category(g.user.id, description, category_type)
        if not category.isExists():
            db.session.add(category)
            db.session.commit()
            success = (True if category.id != -1 else False)
        return render_template("category.html", success = success, locid = loc)
    elif request.method == "POST" and request.form["action"] == "add":
        #show add category
        return render_template("category.html", action = "add", locid = loc)
    elif request.method == "POST" and request.form["action"] == "edit":
        #show edit category
        category_id = request.form["categoryid"]
        return render_template("category.html", action = "edit", category = Category.query.filter_by(id=category_id).one(), locid = loc)
    elif request.method == "POST" and request.form["action"] == "fin-edit":
        #show finalise edit category
        category_id = request.form["categoryid"]
        description = request.form["description"]
        category_type = request.form["categorytype"]
        success = False

        category = Category(g.user.id, description, category_type)
        if not category.isExists():
            category = Category.query.get(category_id)
            category.description = description
            category.category_type = category_type
            db.session.commit()
            success = True

        return render_template("category.html", action = "edit-fin", success = success, locid = loc)
    elif request.method == "POST" and request.form["action"] == "delete":
        #delete category
        category_id = request.form["categoryid"]
        category = Category.query.get(category_id)
        db.session.delete(category)
        db.session.commit()
        return render_template("category.html", action = "delete-fin", locid = loc)
    else:
        #show category list
        rs = db.session.query(Category).filter_by(user_id=g.user.id)
        return render_template("category.html", action = "show", category = rs, locid = loc)
#category

@app.route("/income", methods=["GET", "POST"])
@login_required
def income():
    loc = "nav-income"
    if request.method == "POST" and request.form["action"] == "insert":
        #insert new income
        amount = request.form["amount"]
        category_id = request.form["categoryid"]
        income = Transaction(g.user.id, amount, "Income", category_id)
        db.session.add(income)
        db.session.commit()
        success = (True if income.id != -1 else False)
        return render_template("income.html", success = success, locid = loc)
    elif request.method == "POST" and request.form["action"] == "add":
        #show add income
        return render_template("income.html", action = "add", category = Category.query.filter_by(category_type="Income"),  locid = loc)
    else:
        #show income list
        income_total = 0
        qry = db.session.query(Transaction, func.sum(Transaction.amount).label("total_amount")).filter_by(transaction_type="Income").filter_by(user_id=g.user.id)
        for _res in qry.all():
            income_total = _res.total_amount

        percentage_list = []

        qry = db.session.query(Transaction, Category, func.sum(Transaction.amount).label("total_amount")).filter_by(transaction_type="Income").filter_by(user_id=g.user.id).join(Category).group_by(Category.description)
        for _res in qry.all():
            a = { "percent" : int(round(((_res.total_amount / income_total) * 100))), "description" : _res.Category.description, "amount" : _res.total_amount }
            percentage_list.append(a)
            
        rs = db.session.query(Transaction, Category).filter_by(transaction_type="Income").filter_by(user_id=g.user.id).join(Category)
        return render_template("income.html", action = "show", income = rs, percentage_list=percentage_list, locid = loc)
#end income

@app.route("/expense", methods=["GET", "POST"])
@login_required
def expense():
    loc = "nav-expense"
    if request.method == "POST" and request.form["action"] == "insert":
        #insert new expense
        amount = request.form["amount"]
        category_id = request.form["categoryid"]
        expense = Transaction(g.user.id, amount, "Expense", category_id)
        db.session.add(expense)
        db.session.commit()
        success = (True if expense.id != -1 else False)
        return render_template("expense.html", success = success, locid = loc)
    elif request.method == "POST" and request.form["action"] == "add":
        #show add expense
        return render_template("expense.html", action = "add", net_income = net_income(), category = Category.query.filter_by(category_type="Expense"),  locid = loc)
    else:
        #show expense list
        expense_total = 0
        qry = db.session.query(Transaction, func.sum(Transaction.amount).label("total_amount")).filter_by(transaction_type="Expense").filter_by(user_id=g.user.id)
        for _res in qry.all():
            expense_total = _res.total_amount

        percentage_list = []

        qry = db.session.query(Transaction, Category, func.sum(Transaction.amount).label("total_amount")).filter_by(transaction_type="Expense").filter_by(user_id=g.user.id).join(Category).group_by(Category.description)
        for _res in qry.all():
            a = { "percent" : int(round(((_res.total_amount / expense_total) * 100))), "description" : _res.Category.description, "amount" : _res.total_amount }
            percentage_list.append(a)
            
        rs = db.session.query(Transaction, Category).filter_by(transaction_type="Expense").filter_by(user_id=g.user.id).join(Category)
        return render_template("expense.html", action = "show", expense = rs, percentage_list=percentage_list, locid = loc)
#end expense

@app.route("/allocation", methods=["GET", "POST"])
@login_required
def allocation():
    loc = "nav-allocation"
    if request.method == "POST" and request.form["action"] == "insert":
        #insert new allocation
        amount = request.form["amount"]
        category_id = request.form["categoryid"]
        allocation = Transaction(g.user.id, amount, "Allocation", category_id)
        db.session.add(allocation)
        db.session.commit()
        success = (True if allocation.id != -1 else False)
        return render_template("allocation.html", success = success, locid = loc)
    elif request.method == "POST" and request.form["action"] == "add":
        #show add allocation
        return render_template("allocation.html", action = "add", net_income = net_income(), category = Category.query.filter_by(category_type="Expense"),  locid = loc)
    else:
        #show allocation list
        allocation_total = 0
        qry = db.session.query(Transaction, func.sum(Transaction.amount).label("total_amount")).filter_by(transaction_type="Allocation").filter_by(user_id=g.user.id)
        for _res in qry.all():
            allocation_total = _res.total_amount

        percentage_list = []

        qry = db.session.query(Transaction, Category, func.sum(Transaction.amount).label("total_amount")).filter_by(transaction_type="Allocation").filter_by(user_id=g.user.id).join(Category).group_by(Category.description)
        for _res in qry.all():
            a = { "percent" : int(round(((_res.total_amount / allocation_total) * 100))), "description" : _res.Category.description, "amount" : _res.total_amount }
            percentage_list.append(a)
            
        rs = db.session.query(Transaction, Category).filter_by(transaction_type="Allocation").filter_by(user_id=g.user.id).join(Category)
        return render_template("allocation.html", action = "show", allocation = rs, percentage_list=percentage_list, locid = loc)
#end allocation

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

if app.debug:
    @app.route("/populatecategory")
    def populatecategory():
        i = 0
        u = "Income"
        while i != 50:
            if i > 25:
                u = "Expense"
            db.session.add(Category(g.user.id, "%s%d" % (u, i), u))
            db.session.commit()
            i += 1
        return render_template("populate.html", name="Category")
    #end populatecategory
    @app.route("/populateincome")
    def populateincome():
        i = 0
        c = 1
        while i != 50:
            if i % 2 == 0:
                c = 1
            elif i % 3 == 0:
                c = 2
            else:
                c = 3

            db.session.add(Transaction(g.user.id, i*2, "Income", c))
            db.session.commit()
            i += 1
        return render_template("populate.html", name="Income")
    #end populateincome
    @app.route("/populateexpense")
    def populateexpense():
        i = 0
        c = 27
        while i != 50:
            if i % 2 == 0:
                c = 27
            elif i % 3 == 0:
                c = 28
            else:
                c = 29

            db.session.add(Transaction(g.user.id, i*2, "Expense", c))
            db.session.commit()
            i += 1
        return render_template("populate.html", name="Expense")
    #end populateexpense
    @app.route("/populateallocation")
    def populateallocation():
        i = 0
        c = 27
        while i != 50:
            if i % 2 == 0:
                c = 27
            elif i % 3 == 0:
                c = 28
            else:
                c = 29

            db.session.add(Transaction(g.user.id, i*2, "Allocation", c))
            db.session.commit()
            i += 1
        return render_template("populate.html", name="Allocation")
    #end populateallocation

if __name__ == "__main__":
    manager.run()
    app.run()
#end run
