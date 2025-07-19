from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    enabled = db.Column(db.Boolean, default=True)
    content = db.Column(db.Text, nullable=True)  # 解析后内容
    raw_content = db.Column(db.Text, nullable=True)  # 原始订阅内容
    last_update = db.Column(db.DateTime, nullable=True)  # 最后更新时间
    type = db.Column(db.String(32), default='unknown')  # 新增字段，clash/shadowrocket/unknown
    def __repr__(self):
        return f'<Subscription {self.name}>'

class Config(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=True)