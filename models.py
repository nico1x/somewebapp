from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(254))
    lastname = db.Column(db.String(254))
    username = db.Column(db.String(254), unique=True)
    password = db.Column(db.String(254))

    transactions = db.relationship("Transaction", backref='user', lazy='dynamic')
    categories = db.relationship("Category", backref='user', lazy='dynamic')

    def __init__(self, firstname, lastname, username, password):
        self.firstname = firstname
        self.lastname = lastname
        self.username = username
        self.password = password
    #end __init__

    def __repr__(self):
        return '<User { id: %r, first name: %r, lastname: %r, username: %r, password: %r }>' % (self.id, self.firstname, self.lastname, self.username, self.password)
    #end __repr__

    def isExists(self):
        return User.query.filter_by(username=self.username).count() > 0
    #end isExists

    def is_active(self):
        return True
    #end is_active

    def get_id(self):
        return unicode(self.id)
    #end get_id

    def is_authenticated(self):
        return True

    def is_anonymous(self):
        return False
#end User
    
class Category(db.Model):
    __tablename__ = "category"
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(64))
    category_type = db.Column(db.String(64))

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    transactions = db.relationship("Transaction", backref='category', lazy='dynamic')

    def __init__(self, user_id, description, category_type):
        self.description = description
        self.category_type = category_type
        self.user_id = user_id
    #end __init__

    def __repr__(self):
        return '<Category { description: %r, type: %r }>' % (self.description, self.category_type)
    #end __repr__

    def isExists(self):
        return Category.query.filter_by(description=self.description, category_type=self.category_type).count() > 0
    #end isExists
#end Category

class Transaction(db.Model):
    __tablename__ = "transaction"
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, default=datetime.now())
    amount = db.Column(db.Float)
    transaction_type = db.Column(db.String(64))

    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __init__(self, user_id, amount, transaction_type, category_id):
        self.amount = amount
        self.transaction_type = transaction_type
        self.category_id = category_id
        self.user_id = user_id
    #end __init__

    def __repr__(self):
        return '<Transaction { id: %r, amount: %r, type: %r, user.id: %r, category.id: %r, date: %r }>' % (self.id, self.amount, self.transaction_type, self.user_id, self.category_id, self.date)
    #end __repr__
#end Transaction

# db.create_all()