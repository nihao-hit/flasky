'''
程序代码应该合理组织，尽量把业务逻辑写入数据库模型或独立于程序上下文的辅助类中，
这样测试起来才更简单。视图函数中的代码应该保持简洁，仅发挥粘合剂的作用，收到请求后
调用其他类中的对应操作或者封装程序逻辑的函数。
'''
from datetime import datetime
import hashlib
#使用werkzeug实现密码散列
from werkzeug.security import generate_password_hash,check_password_hash
#使用itsdangerous生成确认令牌
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from markdown import markdown
import bleach
from flask import current_app,url_for
#使用flask_login认证用户，不依赖特定的认证机制
from flask_login import UserMixin,AnonymousUserMixin
from .exceptions import ValidationError
from . import db,login_manager


class Permission:
    FOLLOW = 1    #0x01 0b00000001
    COMMENT = 2   #0x02 0b00000010
    WRITE = 4     #0x04 0b00000100
    MODERATE = 8  #0x08 0b00001000
    ADMIN = 16    #0x10 0b00010000


#赋予用户分立的角色，角色使用权限组织
class Role(db.Model):
    '''
    提供add_permission，reset_permission，reset_permission，has_permission函数
    '''
    __tablename__ = 'roles'
    id = db.Column(db.Integer,primary_key=True)
    name = db.Column(db.String(64),unique=True)
    #只有一个角色的default字段要设为True，其角色会被设为默认角色。
    default = db.Column(db.Boolean,default=False,index=True)
    permissions = db.Column(db.Integer)
    users = db.relationship('User',backref='role',lazy='dynamic')

    #初始化角色权限为0
    def __init__(self,**kwargs):
        super(Role,self).__init__(**kwargs)
        if self.permissions is None:
            self.permissions = 0

    @staticmethod
    def insert_roles():
        roles = {
            'User':[Permission.FOLLOW,Permission.COMMENT,Permission.WRITE],
            'Moderator':[Permission.FOLLOW,Permission.COMMENT,
                         Permission.WRITE,Permission.MODERATE],
            'Administrator':[Permission.FOLLOW,Permission.COMMENT,
                             Permission.WRITE,Permission.MODERATE,
                             Permission.ADMIN]
        }
        default_role = 'User'
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.reset_permission()
            for perm in roles[r]:
                role.add_permission(perm)
            role.default = (role.name == default_role)
            db.session.add(role)
        #静态函数在脚本中运行，config未初始化。注意，这里需要手动提交
        db.session.commit()

    def add_permission(self,perm):
        if not self.has_permission(perm):
            self.permissions += perm

    def remove_permission(self,perm):
        if self.has_permission(perm):
            self.permissions -= perm

    def reset_permission(self):
        self.permissions = 0

    def has_permission(self,perm):
        return self.permissions & perm == perm

    def __repr__(self):
        return '<Role {}>'.format(self.name)


class Follow(db.Model):
    __tablename__ = 'follows'
    follower_id = db.Column(db.Integer,db.ForeignKey('users.id'),
                            primary_key=True)
    followed_id = db.Column(db.Integer,db.ForeignKey('users.id'),
                            primary_key=True)
    timestamp = db.Column(db.DateTime,default=datetime.utcnow)


class User(UserMixin,db.Model):
    '''
    跟登陆有关的函数实现ping,
    跟关注有关的函数实现follow,unfollow,is_following,is_followed_by,
    跟密码有关的函数实现password,verify_password,reset_password
    跟认证有关的函数实现generate_confirmation_token,confirm,generate_reset_token
    跟修改邮箱有关的函数实现generate_email_change_token,change_email
    跟角色权限有关的函数实现can,is_administrator,
    跟用户头像有关的函数实现gravatar_hash,gravatar,
    rest风格的获取资源函数实现followed_posts,to_json
    rest风格的用户认证函数实现generate_auth_token,verify_auth_token
    '''
    __tablename__ = 'users'
    id = db.Column(db.Integer,primary_key=True)
    email = db.Column(db.String(64),unique=True,index=True)
    username = db.Column(db.String(64),unique=True,index=True)
    role_id = db.Column(db.Integer,db.ForeignKey('roles.id'))
    password_hash = db.Column(db.String(128))
    confirmed = db.Column(db.Boolean,default=False)
    
    name = db.Column(db.String(64))
    location = db.Column(db.String(64))
    about_me = db.Column(db.Text())
    member_since = db.Column(db.DateTime(),default=datetime.utcnow)
    last_seen = db.Column(db.DateTime(),default=datetime.utcnow)
    avatar_hash = db.Column(db.String(32))
    posts = db.relationship('Post',backref='author',lazy='dynamic')
    '''
    lazy参数指定为joined，这个lazy模式可以实现立即从连接查询中加载相关对象。
    例如，如果某用户关注了100个用户，调用user.followed.all()后会返回一个列表，
    其中包含100个Follow实例，每一个实例的follower和followed回引属性都指向相应的用户
    '''
    followed = db.relationship('Follow',foreign_keys=[Follow.follower_id],
                               backref=db.backref('follower',lazy='joined'),
                               lazy='dynamic',
                               cascade='all,delete-orphan')
    followers = db.relationship('Follow',foreign_keys=[Follow.followed_id],
                                backref=db.backref('followed',lazy='joined'),
                                lazy='dynamic',
                                cascade='all,delete-orphan')
    comments = db.relationship('Comment',backref='author',lazy='dynamic')

    #完成一些添加用户时的初始化,如用户角色设置，计算头像hash值保存，关注自己
    def __init__(self,**kwargs):
        super(User,self).__init__(**kwargs)
        if self.role is None:
            if self.email == current_app.config['FLASKY_ADMIN_EMAIL']:
                self.role = Role.query.filter_by(name='administrator').first()
            if self.role is None:
                self.role = Role.query.filter_by(default=True).first()
        if self.email is not None and self.avatar_hash is None:
            self.avatar_hash = self.gravatar_hash()
        self.follow(self)    
    
    def ping(self):
        self.last_seen = datetime.utcnow()
        db.session.add(self)

    #跟关注有关的函数实现
    @staticmethod
    def add_self_follows():
        for user in User.query.all():
            if not user.is_following(user):
                user.follow(user)
                db.session.add(user)
                # 静态函数在脚本中运行，config未初始化。注意，这里需要手动提交
                db.session.commit()

    def follow(self,user):
        if not self.is_following(user):
            f = Follow(follower=self,followed=user)
            db.session.add(f)

    def unfollow(self,user):
        f = self.followed.filter_by(followed_id=user.id).first()
        if f:
            db.session.delete(f)
    
    def is_following(self,user):
        if user.id is None:
            return False
        return self.followed.filter_by(followed_id=user.id).first() is not None
    
    def is_followed_by(self,user):
        if user.id is None:
            return False
        return self.followers.filter_by(follower_id=user.id) is not None

    #跟密码有关的函数实现
    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self,password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self,password):
        return check_password_hash(self.password_hash,password)


    def generate_reset_token(self,expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'],expiration)
        return s.dumps({'reset':self.id}).decode('utf-8')


    @staticmethod
    def reset_password(token,new_password):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token.encode('utf-8'))
        except:
            return False
        user = User.query.get(data.get('reset'))
        if user is None:
            return False
        user.password = new_password
        db.session.add(user)
        return True

    #跟认证有关的函数实现
    def generate_confirmation_token(self,expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'],expiration)
        return s.dumps({'confirm':self.id}).decode('utf-8')

    def confirm(self,token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            global data
            data = s.loads(token.encode('utf-8'))
        except:
            return False
        if data.get('confirm') != self.id:
            return False
        self.confirmed = True
        db.session.add(self)
        return True


    #跟修改邮箱有关的函数实现
    def generate_email_change_token(self,new_email,expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'],expiration)
        return s.dumps({'change_email':self.id,'new_email':new_email})\
            .decode('utf-8')

    def change_email(self,token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token.encode('utf-8'))
        except:
            return False
        if data.get('change_email') != self.id:
            return False
        new_email = data.get('new_email')
        if new_email is None:
            return False
        if self.query.filter_by(email=new_email).first() is not None:
            return False
        self.email = new_email
        self.avatar_hash = self.gravatar_hash()
        db.session.add(self)
        return True

    #跟角色权限有关的函数实现
    def can(self,perm):
        return self.role is not None and self.role.has_permission(perm)

    def is_administrator(self):
        return self.can(Permission.ADMIN)

    #跟用户头像有关的函数实现
    def gravatar_hash(self):
        return hashlib.md5(self.email.encode('utf-8')).hexdigest()

    def gravatar(self,size=100,default='identicon',rating='g'):
        url = 'https://secure.gravatar.com/avatar'
        hash = self.avatar_hash or self.gravatar_hash()
        return '{url}/{hash}?s={size}&d={default}&r={rating}'.format(
            url=url,hash=hash,size=size,default=default,rating=rating
        )

    #rest风格的获取资源函数实现
    @property
    def followed_posts(self):
        return Post.query.join(Follow,Follow.followed_id == Post.author_id)\
            .filter(Follow.follower_id == self.id)

    def to_json(self):
        json_user = {
            'user':url_for('api.get_user',id=self.id),
            'username':self.username,
            'member_since':self.member_since,
            'last_seen':self.last_seen,
            'posts_url':url_for('api.get_user_posts',id=self.id),
            'followed_posts_url':url_for('api.get_user_followed_posts',
                                         id=self.id),
            'post_count':self.posts.count()
        }
        return json_user
    
    #rest风格的用户认证函数实现
    def generate_auth_token(self,expiration):
        s = Serializer(current_app.config['SECRET_KEY'],
                       expires_in=expiration)
        return s.dumps({'id':self.id}).decode('utf-8')

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return None
        return User.query.get(data['id'])

    def __repr__(self):
        return '<User {}>'.format(self.username)


class AnonymousUser(AnonymousUserMixin):
    def can(self,permissions):
        return False

    def is_administrator(self):
        return False

login_manager.anonymous_user = AnonymousUser

#flask_login要求实现的回调函数，使用指定的标识符加载用户
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class Post(db.Model):
    '''
    提供函数to_json,from_json
    '''
    __tablename__ = 'posts'
    id = db.Column(db.Integer,primary_key=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime,default=datetime.utcnow,index=True)
    author_id = db.Column(db.Integer,db.ForeignKey('users.id'))
    comments = db.relationship('Comment',backref='post',lazy='dynamic')

    @staticmethod
    def on_changed_body(target,value,oldvalue,initiator):
        allowed_tags = ['a','abbr','acronym','b','blockquote','code',
                        'em','i','li','ol','pre','strong','ul','h1',
                        'h2','h3','p']
        target.body_html = bleach.linkify(bleach.clean(
            markdown(value,output_format='html'),
            tags=allowed_tags,strip=True))

    def to_json(self):
        json_post = {
            'url':url_for('api.get_post',id=self.id),
            'body':self.body,
            'body_html':self.body_html,
            'timestamp':self.timestamp,
            'author_url':url_for('api.get_user',id=self.author_id),
            'comments_url':url_for('api.get_post_comments',id=self.id),
            'comments_count':self.comments.count()
        }
        return json_post

    @staticmethod
    def from_json(json_post):
        body = json_post.get('body')
        if body is None or body == '':
            raise ValidationError('post does not have a body')
        return Post(body=body)
    
db.event.listen(Post.body,'set',Post.on_changed_body)


class Comment(db.Model):
    '''
    提供函数to_json
    '''
    __tablename__ = 'comments'
    id = db.Column(db.Integer,primary_key=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime,index=True,default=datetime.utcnow)
    disabled = db.Column(db.Boolean)
    author_id = db.Column(db.Integer,db.ForeignKey('users.id'))
    post_id = db.Column(db.Integer,db.ForeignKey('posts.id'))

    @staticmethod
    def on_changed_body(target,value,oldvalue,initiator):
        allowed_tags = ['a','abbr','acronym','b','code','em','i',
                        'strong']
        target.body_html = bleach.linkify(bleach.clean(
            markdown(value,output_format='html'),
            tags=allowed_tags,strip=True
        ))

    def to_json(self):
        json_comment = {
            'url':url_for('api.get_comment',id=self.id),
            'post_url':url_for('api.get_post',id=self.post_id),
            'body':self.body,
            'body_html':self.body_html,
            'timestamp':self.timestamp,
            'author_url':url_for('api.get_user',id=self.author_id)
        }
        return json_comment
    
db.event.listen(Comment.body,'set',Comment.on_changed_body)