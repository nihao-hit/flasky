import os


class Config:
    #flask配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard to guess string'
    #flask_mail配置
    MAIL_SERVER = os.environ.get('MAIL_SERVER','smtp.163.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT','465'))
    MAIL_USE_SSL = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME','nihao_cx@163.com')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD','nihao123456789')
    #flask_sqlalchemy配置
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True

    FLASKY_ADMIN_EMAIL = os.environ.get('FLASKY_ADMIN_EMAIL','nihao_cx@163.com')
    FLASKY_MAIL_SUBJECT_PREFIX = '[Chenxin]'
    FLASKY_MAIL_SENDER = 'Flasky Admin Chenxin <{}>'.format(FLASKY_ADMIN_EMAIL)

    FLASKY_POSTS_PER_PAGE = 20
    FLASKY_FOLLOWERS_PER_PAGE = 50
    FLASKY_COMMENTS_PER_PAGE = 30

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URI') or \
        'mysql+pymysql://root:@localhost/data_dev'


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URI') or \
        'mysql+pymysql://root:@localhost/data_test'


class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URI') or \
        'mysql+pymysql://root:@localhost/data'


config = {
    'development':DevelopmentConfig,
    'testing':TestingConfig,
    'production':ProductionConfig,

    'default':DevelopmentConfig
}