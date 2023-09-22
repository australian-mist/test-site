from data import db_session
from data.users import Users
from data.news import News


db_session.global_init('news.sqlite')
db_sess = db_session.create_session()


# db_sess.add(Users(name='Voldemar', about='53 years old', email='voldemar@mail.ru'))
# db_sess.add(Users(name='Новость 2 от Володи', about='Успеваю', email=1))
#
# user = db_sess.query(Users).filter(Users.id).first()
# user.name = 'Volodya'
#
# db_sess.add(News(title='Новость 1 от Володи', content='Опаздываю', user_id=1, is_private=False))
# db_sess.add(News(title='Новость 2 от Володи', content='Успеваю', user_id=1, is_private=False))
#
# db_sess.commit()


users1 = db_sess.query(Users).filter(Users.name.like('%d%'))
[print(i) for i in users1]

users2 = db_sess.query(Users).filter(Users.email.notlike('%v%'))
[print(i) for i in users2]



