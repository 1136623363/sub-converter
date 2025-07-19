from apscheduler.schedulers.background import BackgroundScheduler
from models import Subscription, db
from .converter import fetch_subscription

def update_all_subscriptions(app):
    with app.app_context():
        subs = Subscription.query.all()
        for sub in subs:
            try:
                fetch_subscription(sub.url)
            except Exception as e:
                print(f"定时任务更新{sub.name}失败: {str(e)}")

def init_scheduler(app):
    scheduler = BackgroundScheduler()
    if not hasattr(app, 'apscheduler_started'):
        scheduler.add_job(func=lambda: update_all_subscriptions(app), trigger='interval', minutes=15)
        scheduler.start()
        app.apscheduler_started = True