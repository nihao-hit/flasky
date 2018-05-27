from flask import Blueprint

api = Blueprint('api',__name__,url_prefix='/api/v1')

from . import authentication,posts,users,comments,errors