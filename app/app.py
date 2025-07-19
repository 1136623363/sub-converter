from flask import Flask, render_template, request, redirect, url_for, jsonify
from .models import db, Subscription, Config
from .converter import generate_clash_config, generate_shadowrocket_config
from .scheduler import init_scheduler
import os

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///D:/Desktop/sub-converter/app/data/subscriptions.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
        init_scheduler(app)
        # 启动时自动更新一次所有订阅
        from .converter import fetch_subscription
        from .models import Subscription
        subs = Subscription.query.all()
        for sub in subs:
            try:
                fetch_subscription(sub.url)
            except Exception as e:
                print(f"订阅{sub.name}启动时更新失败: {str(e)}")
    
    @app.route('/')
    def index():
        subscriptions = Subscription.query.all()
        return render_template('index.html', subscriptions=subscriptions)

    @app.route('/raw/<int:id>')
    def view_raw_content(id):
        sub = Subscription.query.get_or_404(id)
        raw = sub.raw_content or '(无原始内容)'
        # 直接返回原文内容，防止被 Jinja2/HTML 转义
        return f"""
<h3>原始内容 - {sub.name}</h3>
<pre style='white-space:pre-wrap;word-break:break-all;background:#f8f9fa;padding:1em;border-radius:6px;'>{raw if isinstance(raw, str) else raw.decode('utf-8', 'ignore')}</pre>
<a href='/' style='margin-top:1em;display:inline-block;'>返回</a>
"""
    
    @app.route('/add', methods=['POST'])
    def add_subscription():
        url = request.form['url']
        name = request.form.get('name', 'Unnamed')
        # 校验 URL
        if not url.startswith(('http://', 'https://')):
            return "无效的URL，必须以http://或https://开头", 400
        # 校验重复
        if Subscription.query.filter_by(url=url).first():
            return "该订阅已存在", 400
        # 校验名称唯一性
        if Subscription.query.filter_by(name=name).first():
            return "名称已存在，请更换名称", 400
        try:
            sub = Subscription(name=name, url=url, content='', raw_content='')
            db.session.add(sub)
            db.session.commit()
            # 添加后立即更新订阅内容
            from .converter import fetch_subscription
            try:
                fetch_subscription(sub.url)
            except Exception as e:
                db.session.delete(sub)
                db.session.commit()
                return f"订阅添加后自动更新失败: {str(e)}", 500
        except Exception as e:
            db.session.rollback()
            return f"添加失败: {str(e)}", 500
        return redirect(url_for('index'))

    @app.route('/edit/<int:id>', methods=['GET', 'POST'])
    def edit_subscription(id):
        sub = Subscription.query.get_or_404(id)
        if request.method == 'POST':
            url = request.form['url']
            name = request.form.get('name', 'Unnamed')
            # 校验 URL
            if not url.startswith(('http://', 'https://')):
                return "无效的URL，必须以http://或https://开头", 400
            # 校验重复（排除自身）
            if Subscription.query.filter(Subscription.url == url, Subscription.id != id).first():
                return "该订阅已存在", 400
            # 校验名称唯一性（排除自身）
            if Subscription.query.filter(Subscription.name == name, Subscription.id != id).first():
                return "名称已存在，请更换名称", 400
            try:
                sub.url = url
                sub.name = name
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                return f"修改失败: {str(e)}", 500
            return redirect(url_for('index'))
        return render_template('edit.html', sub=sub)
    

    @app.route('/update/<int:id>')
    def update_subscription(id):
        sub = Subscription.query.get_or_404(id)
        from .converter import fetch_subscription
        try:
            fetch_subscription(sub.url)
        except Exception as e:
            # AJAX请求返回纯文本，普通请求重定向
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.accept_mimetypes.best == 'application/json':
                return f"更新失败: {str(e)}", 500
            return f"更新失败: {str(e)}", 500
        # AJAX请求返回200纯文本，普通请求重定向
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.accept_mimetypes.best == 'application/json':
            return 'ok'
        return redirect(url_for('index'))

    @app.route('/delete/<int:id>')
    def delete_subscription(id):
        sub = Subscription.query.get_or_404(id)
        db.session.delete(sub)
        db.session.commit()
        return redirect(url_for('index'))
    

    @app.route('/sub')
    def sub_config():
        ua = request.headers.get('User-Agent', '').lower()
        try:
            resp = generate_clash_config()
            if resp.data.strip() == b'proxies: []\nproxy-groups:\n- name: PROXY\n  type: select\n  proxies: []\nrules:\n- GEOIP,CN,DIRECT\n- MATCH,PROXY\n':
                return "无可用节点，无法生成配置", 400
            return resp
        except Exception as e:
            return f"生成订阅失败: {str(e)}", 500
    
    @app.route('/subscribe')
    def subscribe():
        return render_template('subscribe.html', 
                              sub_url=request.url_root + 'sub')
    
    return app

# 兼容直接 python app.py 启动
if __name__ == "__main__":
    app = create_app()
    app.run()