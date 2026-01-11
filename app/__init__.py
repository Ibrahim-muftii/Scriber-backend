from flask import Flask
from app.routes.YoutubeVideoSummarizer import yvs_bp
from app.routes.CodeLanguageChanger import clc_bp
from app.routes.GestureModule import gm_bp
from app.routes.SummarizerChatbot import chatbot_bp
from app.routes.HealthCheck import health_bp
from app.routes.VideoTranscription import vt_bp
from flask_cors import CORS


def create_app():

    app = Flask(__name__)
    app.config['DEBUG'] = True
    
    CORS(app, resources={r"/*": {"origins": "*"}})

    # Set app config if you have any, e.g.:
    # app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mydatabase.db'
    # db.init_app(app)

    app.register_blueprint(yvs_bp, url_prefix='/yvs')
    app.register_blueprint(clc_bp, url_prefix='/clc')
    app.register_blueprint(gm_bp, url_prefix='/gm')
    app.register_blueprint(chatbot_bp, url_prefix='/sc')
    app.register_blueprint(health_bp)
    app.register_blueprint(vt_bp, url_prefix='/vt')
    # Import and register Blueprints AFTER the app is created
    
    # You can register more blueprints here if you want:
    # from app.admin_routes import admin as admin_blueprint
    # app.register_blueprint(admin_blueprint, url_prefix='/admin')
    
    return app
