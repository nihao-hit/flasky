import os
from flask_migrate import Migrate
from app import create_app,db
from app.models import User,Follow,Role,Permission,Post,Comment
from app.fake import users,posts

app = create_app()
migrate = Migrate(app,db)


'''
@app.shell_context_processor
def make_shell_context():
    return dict(db=db,User=User,Follow=Follow,Role=Role,
                Permission=Permission,Post=Post,Comment=Comment,users=users,posts=posts)
'''


@app.cli.command()
def deploy():
    '''
    部署命令
    '''
    db.create_all()

    Role.insert_roles()

    User.add_self_follows()


@app.cli.command()
def fake():
    '''
    生成测试数据命令
    :return:
    '''
    users()

    posts()