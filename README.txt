基于flask框架的博客，实现了用户认证，角色权限，用户资料，关注者，文章，评论，rest web服务等功能。
引擎：
werkzeug:路由，调试和web服务器网关接口子系统
jinja2:模板系统

前端：
flask_bootstrap:
flask_wtf:
flask_moment:集成moment.js，渲染日期和时间
flask_pagedown:把pagedown集成到flask_wtf表单中

数据库：
pymysql:
flask_sqlalchemy:
flask_migrate：

用户认证：
flask_login:管理已登录用户的用户会话
itsdangerous:生成并核对加密安全令牌
werkzeug：计算密码散列值并进行核对
flask_mail:
flask_httpauth:实现了http认证协议

后端：
wtforms:支持多个框架的web表单
markdown:使用python实现的服务器端markdown到html的转换程序
bleach：使用python实现的html清理器
