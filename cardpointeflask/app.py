from flask import Flask
from celery import Celery
from itsdangerous import URLSafeTimedSerializer
import logging

from cardpointeflask.blueprints.page import page
from cardpointeflask.blueprints.contact import contact
from cardpointeflask.blueprints.dropfiles import dropfiles
from cardpointeflask.blueprints.user import user
from cardpointeflask.blueprints.user.models import User

from cardpointeflask.extensions import (
    debug_toolbar,
    mail,
    csrf,
    excel,
    db,
    login_manager
)

CELERY_TASK_LIST = [
    'cardpointeflask.blueprints.contact.tasks',
    'cardpointeflask.blueprints.user.tasks',
    'cardpointeflask.blueprints.dropfiles.tasks',
]


def create_celery_app(app=None):
    """
    Create a new Celery object and tie together the Celery config to the app's
    config. Wrap all tasks in the context of the application.

    :param app: Flask app
    :return: Celery app
    """
    app = app or create_app()

    celery = Celery(app.import_name, broker=app.config['CELERY_BROKER_URL'],
                    include=CELERY_TASK_LIST)
    celery.conf.update(app.config)
    TaskBase = celery.Task

    class ContextTask(TaskBase):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)

    celery.Task = ContextTask
    return celery


def create_app(settings_override=None):
    """
    Create a Flask application using the app factory pattern.

    :param settings_override: Override settings
    :return: Flask app
    """
    app = Flask(__name__, instance_relative_config=True)

    app.config.from_object('config.settings')
    app.config.from_pyfile('settings.py', silent=True)

    if settings_override:
        app.config.update(settings_override)

    configure_logging()

    app.register_blueprint(page)
    app.register_blueprint(contact)
    app.register_blueprint(dropfiles)
    app.register_blueprint(user)
    extensions(app)
    authentication(app, User)

    return app


def extensions(app):
    """
    Register 0 or more extensions (mutates the app passed in).

    :param app: Flask application instance
    :return: None
    """
    debug_toolbar.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)
    db.init_app(app)
    login_manager.init_app(app)
    excel.init_excel(app)

    return None


def authentication(app, user_model):
    """
    Initialize the Flask-Login extension (mutates the app passed in).

    :param app: Flask application instance
    :param user_model: Model that contains the authentication information
    :type user_model: SQLAlchemy model
    :return: None
    """
    login_manager.login_view = 'user.login'

    @login_manager.user_loader
    def load_user(uid):
        return user_model.query.get(uid)

    @login_manager.request_loader
    def load_request(request):
        duration = app.config['REMEMBER_COOKIE_DURATION'].total_seconds()
        serializer = URLSafeTimedSerializer(app.secret_key)

        token = request.headers.get('Authorization')
        if token is None:
            token = request.args.get('token')
        if token is not None:
            data = serializer.loads(token, max_age=duration)
            user_uid = data[0]
            return user_model.query.get(user_uid)
        return None

def configure_logging():
    # register root logging
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger('werkzeug').setLevel(logging.INFO)
