import os
from flask_migrate import Migrate
from app import create_app,db
from app.models import User,Follow,Role,Permission,Post,Comment
from app.fake import users,posts

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
migrate = Migrate(app,db)


@app.shell_context_processor
def make_shell_context():
    return dict(db=db,User=User,Follow=Follow,Role=Role,
                Permission=Permission,Post=Post,Comment=Comment,users=users,posts=posts)
            
        
@app.cli.command()
def deploy():
    '''
    Run deployment tasks.
    '''

    Role.insert_roles()

    User.add_self_follows()