from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


class Update(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.String(10000))
    data = db.Column(db.DateTime(timezone=True))
