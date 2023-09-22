import datetime
import requests

from flask import Flask, request, redirect, abort
from flask import render_template, make_response, session
from flask_login import LoginManager, login_user, login_required
from flask_login import logout_user, current_user

from data import db_session
from data.news import News
from data.users import User
from forms.add_news import NewsForm
from forms.user import RegisterForm
from loginform import LoginForm

import smtplib
import mimetypes
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


app = Flask(__name__)
login_manager = LoginManager()
login_manager.init_app(app)

app.config['SECRET_KEY'] = 'too short key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db/news.sqlite'
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(days=365)  # год


@app.route('/')
@app.route('/index')
def index():
    db_sess = db_session.create_session()
    if current_user.is_authenticated:
        news = db_sess.query(News).filter(
            (News.user == current_user) | (News.is_private != True))
    else:
        news = db_sess.query(News).filter(News.is_private != True)
    return render_template('index.html',
                           title='Новости',
                           news=news)


@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.get(User, user_id)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.email == form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect('/')
        return render_template('login.html', title='Повторная авторизация',
                               message='Неверный логин или пароль',
                               form=form)
    return render_template('login.html',
                           title='Авторизация',
                           form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/')


@app.route('/news', methods=['GET', 'POST'])
@login_required
def add_news():
    form = NewsForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        news = News()  # ORM-модель News
        news.title = form.title.data
        news.content = form.content.data
        news.is_private = form.is_private.data
        current_user.news.append(news)
        db_sess.merge(current_user)  # слияние сессии с текущим пользователем
        db_sess.commit()
        return redirect('/')
    return render_template('news.html', title='Добавление новости',
                           form=form)


@app.route('/news/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_news(id):
    form = NewsForm()
    if request.method == 'GET':
        db_sess = db_session.create_session()
        news = db_sess.query(News).filter(News.id == id, News.user == current_user).first()
        if news:
            form.title.data = news.title
            form.content.data = news.content
            form.is_private.data = news.is_private
        else:
            abort(404)
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        news = db_sess.query(News).filter(News.id == id,
                                          News.user == current_user).first()
        if news:
            news.title = form.title.data
            news.content = form.content.data
            news.is_private = form.is_private.data
            db_sess.commit()
            return redirect('/')
        else:
            abort(404)
    return render_template('news.html', title='Редактирование новости',
                           form=form)


@app.route('/news_del/<int:id>', methods=['GET', 'POST'])
@login_required
def news_delete(id):
    db_sess = db_session.create_session()
    news = db_sess.query(News).filter(News.id == id, News.user == current_user).first()
    if news:
        db_sess.delete(news)
        db_sess.commit()
    else:
        abort(404)
    return redirect('/')


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('register.html',
                                   title='Проблемы с регистрацией',
                                   message='Пароли не совпадают',
                                   form=form)
        db_sess = db_session.create_session()
        if db_sess.query(User).filter(User.email == form.email.data).first():
            return render_template('register.html',
                                   title='Проблемы с регистрацией',
                                   message='Такой пользователь уже есть',
                                   form=form)
        user = User(name=form.name.data,
                    email=form.email.data,
                    about=form.about.data)
        user.set_password(form.password.data)
        db_sess.add(user)
        db_sess.commit()
        return redirect('/login')
    return render_template('register.html', title='Регистрация', form=form)


@app.route('/cookie')
def cookie():
    visit_count = int(request.cookies.get('visit_count', 0))
    if visit_count != 0 and visit_count <= 20:
        res = make_response(f'Были уже {visit_count + 1} раз')
        res.set_cookie('visit_count',
                       str(visit_count + 1),
                       max_age=60 * 60 * 24 * 365 * 2)
    elif visit_count > 20:
        print('Мы тут')
        res = make_response(f'Были уже {visit_count + 1} раз')
        res.set_cookie('visit_count', '1', max_age=0)
    else:
        res = make_response('Вы впервые здесь за 2 года')
        res.set_cookie('visit_count', '1',
                       max_age=60 * 60 * 24 * 365 * 2)
    return render_template('cookie.html', title='cookie', res=res)


@app.route('/photo', methods=['GET', 'POST'])
def photo():

    if request.method == 'GET':
        return render_template('photo.html', title='Фото')

    elif request.method == 'POST':
        f = request.files['file']  # request.form.get('file')
        f.save('static/loaded.png')

        return render_template('success.html', title='')


@app.route('/weather', methods=['GET', 'POST'])
def weather():

    if request.method == 'GET':
        return render_template('weather.html', title='Выбор города')

    elif request.method == 'POST':

        town = request.form.get('town')
        data = {}

        key = 'c747bf84924be997ff13ac5034fa3f86'
        url = 'http://api.openweathermap.org/data/2.5/weather'

        params = {'APPID': key, 'q': town, 'units': 'metric'}
        result = requests.get(url, params=params)

        w = result.json()
        code = w['cod']
        icon = w['weather'][0]['icon']
        temperature = w['main']['temp']

        data['code'] = code
        data['icon'] = icon
        data['temp'] = temperature

        return render_template('weather_show.html', title=f'Погода в городе {town}', town=town, data=data)


@app.route('/mail', methods=['GET', 'POST'])
def mail():
    if request.method == 'GET':
        return render_template('mail.html',title='e-mail')

    elif request.method == 'POST':
        email = 'NextProDanceHall@yandex.ru'
        password = 'pxtpfondojwvfsod'

        msg = MIMEMultipart()
        msg['From'] = email
        msg['To'] = request.form.get('email')
        msg['Subject'] = 'Новое письмо'
        text = request.form.get('letter')
        msg.attach(MIMEText(text, 'plain'))

        server = smtplib.SMTP_SSL(host='smtp.yandex.ru', port=465)
        server.login(email, password)
        server.send_message(msg)
        server.quit()
        return render_template('success.html')


@app.errorhandler(404)
def http_404_error():
    return render_template('error.html', title='error')


@app.route('/success')
def success():
    return render_template('success.html', title='--code--')


if __name__ == '__main__':
    db_session.global_init('db/news.sqlite')
    app.run(host='127.0.0.1', port=5000, debug=True)
