"""应用入口 — 注册蓝图并启动"""

from flask import Flask, redirect, url_for
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# 注册蓝图
from blueprints.principal import principal_bp
from blueprints.securities import securities_bp
from blueprints.otc_app import otc_app_bp
from blueprints.statistics import statistics_bp
from blueprints.settlement import settlement_bp

app.register_blueprint(principal_bp, url_prefix='/principal')
app.register_blueprint(securities_bp, url_prefix='/securities')
app.register_blueprint(otc_app_bp, url_prefix='/otc_app')
app.register_blueprint(statistics_bp, url_prefix='/statistics')
app.register_blueprint(settlement_bp, url_prefix='/settlement')


@app.route('/')
def index():
    return redirect(url_for('principal.query'))


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
