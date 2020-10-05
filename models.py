from flask_sqlalchemy import SQLAlchemy as SA


class SQLAlchemy(SA):
    def apply_pool_defaults(self, app, options):
        SA.apply_pool_defaults(self, app, options)
        options["pool_pre_ping"] = True


db = SQLAlchemy()


class Users(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.String(63), nullable=False, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    room = db.Column(db.String(63), nullable=True)


class Answers(db.Model):
    __tablename__ = 'answers'
    id = db.Column(db.Integer, nullable=False, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String(63), nullable=False)
    number = db.Column(db.Float, nullable=False)
    status = db.Column(db.Integer, nullable=False, default=1)


class Quiz(db.Model):
    __tablename__ = 'quiz'
    id = db.Column(db.Integer, nullable=False, primary_key=True, autoincrement=True)
    text = db.Column(db.Text, nullable=False)
