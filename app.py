from flask import Flask, redirect, render_template, request, url_for, flash, session, make_response
from flask_login import LoginManager,login_user,login_required, logout_user
import models
import array
import xml.etree.ElementTree as ET
import uuid
from datetime import datetime
from random import randint
import re
import jwt
import psycopg2

app = Flask(__name__)
app.config['SECRET_KEY'] = '66b1132a0173910b01ee3a15ef4e69583bbf2f7f1e4462c99efbe1b9ab5bf808'
login_manager = LoginManager(app)
login_manager.login_view = 'login'
userlogin = ""

@app.route('/', methods=['GET','POST'])
def index():
    if request.method == "GET":
        return render_template("index.html")
    if request.method == "POST":
        return render_template("login.html")

@app.route('/logout')
def logout():
    logout_user()
    response = make_response(render_template("login.html",cookies = request.cookies))
    response.set_cookie("jwt","")
    flash("Вы вышли из аккаунта","success")
    return response

@app.route('/registration', methods=['GET','POST'])
def registration():
    if request.method == "GET":
        return render_template("registration.html")
    
    if request.method == "POST":
        login = str(request.form['username'])
        password = str(request.form['password'])
        if not validate(str(login)):
            flash("Допускается вводить только буквы и цифры")
            return render_template("registration.html")
        if not validate(str(password)):
            flash("Допускается вводить только буквы и цифры")
            return render_template("registration.html")

        out = models.getUser(login)
        if len(out)== 0:
            models.insertUser(login,password)
            flash("Успешная регистрация")
            return redirect(url_for('login'))
        else:
            flash("Учетная запись занята")
            return render_template('registration.html')
        return render_template("status.html",workersAmount = models.getWorkersAmount('\'Head\''), 
            headVagonStatus = models.getVagonStatus('\'Head\''), 
            capitansList = models.getCapitansList(), 
            timeToStation = getTime(),
            accountingStatus = models.getAccountingStatus("Accounting"), 
            accountingVagonStatus = models.getVagonStatus('\'Accounting\''), 
            cargoAmount= models.getAllCargoAmount(), cargoVagonStatus = models.getVagonStatus('\'Cargo\'') )

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == "GET":
        return render_template("login.html")
    if request.method == "POST":
        username = str(request.form['username'])
        password = str(request.form['password'])
        if not validate(str(username)):
            flash("Допускается вводить только буквы и цифры")
            return render_template("login.html")
        if not validate(str(password)):
            flash("Допускается вводить только буквы и цифры")
            return render_template("login.html")
        row = models.getUser(username)
        arr = []
        if len(row)!=0:
            for i in row[0]:
                arr.append(i)
            if(password!=arr[2]):
                flash("Неверный пароль / логин")
                return render_template("login.html")
            else:
                userlogin = UserLogin().create(arr[1])
                login_user(userlogin)
                flash("Успешный вход")
                content = {}
                content ['username'] = []
                content ['username'] = username
                is_admin = models.getUser(username)[0]
                data = {"user" : username, "password" : password, "is_admin" : is_admin[3], "comment": is_admin[4]}
                token = encodeJWT(data)
                response = make_response(render_template("status.html",workersAmount = models.getWorkersAmount('\'Head\''), headVagonStatus = models.getVagonStatus('\'Head\''), capitansList = models.getCapitansList(),timeToStation = getTime(),accountingStatus = models.getAccountingStatus("Accounting"), accountingVagonStatus = models.getVagonStatus('\'Accounting\''), cargoAmount= models.getAllCargoAmount(), cargoVagonStatus = models.getVagonStatus('\'Cargo\'')))
                response.set_cookie("jwt", token)
                return response
        else:
            flash("Неверный пароль / логин")
            return render_template("login.html")

#@login_required
@app.route('/status', methods=['GET','POST'])
def status():
    if request.method == "GET":    
        return render_template("status.html", 
            workersAmount = models.getWorkersAmount('\'Head\''), 
            headVagonStatus = models.getVagonStatus('\'Head\''), 
            capitansList = models.getCapitansList(), 
            timeToStation = getTime(),
            accountingStatus = models.getAccountingStatus("Accounting"), 
            accountingVagonStatus = models.getVagonStatus('\'Accounting\''), 
            cargoAmount= models.getAllCargoAmount(), cargoVagonStatus = models.getVagonStatus('\'Cargo\'') )

#@login_required
@app.route('/accounting', methods=['GET','POST'])
def accounting():
    if request.method == "GET":
        username = ""
        user_comment = ""
        try:
            token = request.cookies.get("jwt")
            token_data = decodeJWT(token)
            username = token_data['user']
            #user_comment = token_data['comment']
            user_comment = models.selectUserComment(username)
        except Exception as err:
            flash ("Пользователь неавторизован")
            
        return render_template("accounting.html",
         cargoAmountStatus = models.getAllCargoAmount(),
         headVagonStatus = models.getVagonStatus('\'Head\''), 
         accountingVagonStatus = models.getVagonStatus('\'Accounting\''), 
         cargoVagonStatus = models.getVagonStatus('\'Cargo\''), 
         humanTime = models.getWorkersAmount('\'Head\''),
         username = username, user_comment = user_comment)
    if request.method == "POST":
        if request.form.get('updateHumanTimeInput') == 'Обновить данные':
            token = request.cookies.get("jwt")
            token_data = decodeJWT(token)
            if token_data['is_admin'] == '1':
                if len(request.form['humanTimeInput']) == 0:
                    flash("Не указаны человекочасы")
                else:
                    out = request.form['humanTimeInput']
                    flash("Новое количество человекочасов:" + str(out))
                    models.updateWorkersAmount(out,'\'Head\'')
                    username = token_data['user']
                    user_comment = token_data['comment']
                    return render_template("accounting.html",
                        cargoAmountStatus = models.getAllCargoAmount(),
                        headVagonStatus = models.getVagonStatus('\'Head\''), 
                        accountingVagonStatus = models.getVagonStatus('\'Accounting\''), 
                        cargoVagonStatus = models.getVagonStatus('\'Cargo\''), 
                        humanTime = models.getWorkersAmount('\'Head\''),
                        username = username, user_comment = user_comment)
            else:
                flash('Только капитан может вносить изменения! Текущий пользователь:' + str(token_data))
            if request.form.get('changeVagonStatusButton') == 'Принудительная уборка':
                workers = models.getWorkersAmount('\'Head\'')
                if workers > 0:
                    models.updateVagonStatus("True",'\'Head\'')
                    models.updateVagonStatus("True",'\'Accounting\'')
                    models.updateVagonStatus("True",'\'Cargo\'')
                else:
                    flash ("Нет человекочасов для уборки!")
        if request.form.get('userCommentInput') == 'Обновить комментарий':
            token = request.cookies.get("jwt")
            token_data = decodeJWT(token)
            username = token_data['user']
            user_comment = request.form['userComment']
            token_data['comment'] = user_comment
            models.updateUserComment(username,user_comment)
            token = encodeJWT(token_data)
            response = make_response(render_template("accounting.html",cargoAmountStatus = models.getAllCargoAmount(),
                                                headVagonStatus = models.getVagonStatus('\'Head\''), 
                                                accountingVagonStatus = models.getVagonStatus('\'Accounting\''), 
                                                cargoVagonStatus = models.getVagonStatus('\'Cargo\''), 
                                                humanTime = models.getWorkersAmount('\'Head\''),username = username, user_comment = user_comment))
            response.set_cookie("jwt", token)
            return response

        return render_template("accounting.html",
                        cargoAmountStatus = models.getAllCargoAmount(),
                        headVagonStatus = models.getVagonStatus('\'Head\''), 
                        accountingVagonStatus = models.getVagonStatus('\'Accounting\''), 
                        cargoVagonStatus = models.getVagonStatus('\'Cargo\''), 
                        humanTime = models.getWorkersAmount('\'Head\''))

        

@app.route('/cargo', methods=['GET','POST'])
def cargo():
    if request.method == "GET":
        return render_template("cargo.html", 
        cargoTypeArray = models.getCargoTypeArray(),
        cargoFoodType= models.getCargoType('\'Мясо\''), cargoFoodAmount = models.getCargoAmount('\'Мясо\''), cargoFoodStatus = models.getCargoStatus('\'Мясо\''), cargoFoodPass= models.getCargoPass('\'Мясо\''),
        cargoTechType= models.getCargoType('\'Техника\''), cargoTechAmount = models.getCargoAmount('\'Техника\''), cargoTechStatus = models.getCargoStatus('\'Техника\''),cargoTechPass = models.getCargoPass('\'Техника\''),
        cargoScienceType = models.getCargoType('\'Наука\''),cargoScienceAmount= models.getCargoAmount('\'Наука\''), cargoScienceStatus= models.getCargoStatus('\'Наука\'') , cargoSciencePass= models.getCargoPass('\'Наука\''))
    if request.method == "POST":
        if request.form.get('cargoChangePassButton') == 'Сохранить пароль':
            if len(request.form['cargoChangePass']) == 0:
                flash("Введите пароль")
            else:
                passw = request.form['cargoChangePass']
                selectedName = request.form.get('cargoSelect')
                models.updateCargoPass(selectedName,passw)
                flash("Пароль: "+ str(passw)+" сохранен для груза: " + str(selectedName))
            
        return render_template("cargo.html", 
        cargoTypeArray = models.getCargoTypeArray(),
        cargoFoodType= models.getCargoType('\'Мясо\''), cargoFoodAmount = models.getCargoAmount('\'Мясо\''), cargoFoodStatus = models.getCargoStatus('\'Мясо\''), cargoFoodPass= models.getCargoPass('\'Мясо\''),
        cargoTechType= models.getCargoType('\'Техника\''), cargoTechAmount = models.getCargoAmount('\'Техника\''), cargoTechStatus = models.getCargoStatus('\'Техника\''),cargoTechPass = models.getCargoPass('\'Техника\''),
        cargoScienceType = models.getCargoType('\'Наука\''),cargoScienceAmount= models.getCargoAmount('\'Наука\''), cargoScienceStatus= models.getCargoStatus('\'Наука\'') , cargoSciencePass= models.getCargoPass('\'Наука\''))

        
@app.route('/station', methods=['GET','POST'])
def station():
    if request.method == "GET":      
        return render_template("station.html", timetotrain = getTime(), cargoVagonStatus=  models.getVagonStatus('\'Cargo\''),
        cargoFoodType= models.getCargoType('\'Мясо\''), cargoFoodAmount = models.getCargoAmount('\'Мясо\''), cargoFoodStatus = models.getCargoStatus('\'Мясо\''), cargoFoodPass= models.getCargoPass('\'Мясо\''),
        cargoTechType= models.getCargoType('\'Техника\''), cargoTechAmount = models.getCargoAmount('\'Техника\''), cargoTechStatus = models.getCargoStatus('\'Техника\''),cargoTechPass = models.getCargoPass('\'Техника\''),
        cargoScienceType = models.getCargoType('\'Наука\''),cargoScienceAmount= models.getCargoAmount('\'Наука\''), cargoScienceStatus= models.getCargoStatus('\'Наука\'') , cargoSciencePass= models.getCargoPass('\'Наука\''),
        cargoFoodName = models.getCargoName('\'Мясо\''),cargoTechName = models.getCargoName('\'Техника\''), cargoSciencename = models.getCargoName('\'Наука\'')
        )
    if request.method == "POST":
        types = []
        if request.form.get('ScienceSteal') == 'ScienceSteal':
            rightpass = models.getCargoPass('\'Наука\'')
            userpass = request.form['passScienceSteal']
            if rightpass == userpass:
                models.updateCargoStatus('\'Наука\'')
                newType = models.getHelp()
                models.updateCargoName(newType,'\'Наука\'')
                ar = models.getCargoTypeArray()
                for i in ar:
                    types.append(i)
                flash(types[2])
                return render_template("station.html", timetotrain = getTime(), cargoVagonStatus=  models.getVagonStatus('\'Cargo\''),
        cargoFoodType= models.getCargoType('\'Мясо\''), cargoFoodAmount = models.getCargoAmount('\'Мясо\''), cargoFoodStatus = models.getCargoStatus('\'Мясо\''), cargoFoodPass= models.getCargoPass('\'Мясо\''),
        cargoTechType= models.getCargoType('\'Техника\''), cargoTechAmount = models.getCargoAmount('\'Техника\''), cargoTechStatus = models.getCargoStatus('\'Техника\''),cargoTechPass = models.getCargoPass('\'Техника\''),
        cargoScienceType = models.getCargoType('\'Наука\''),cargoScienceAmount= models.getCargoAmount('\'Наука\''), cargoScienceStatus= models.getCargoStatus('\'Наука\'') , cargoSciencePass= models.getCargoPass('\'Наука\''),
        cargoFoodName = models.getCargoName('\'Мясо\''),cargoTechName = models.getCargoName('\'Техника\''), cargoSciencename = models.getCargoName('\'Наука\'')
        )
            else:
                flash('Неверный пароль!')
            
        if request.form.get('TechSteal') == 'TechSteal':
            rightpass = models.getCargoPass('\'Техника\'')
            userpass = request.form['passTechSteal']
            if rightpass == userpass:
                models.updateCargoStatus('\'Техника\'')
                flash('Груз украден!')
                return render_template("station.html", timetotrain = getTime(), cargoVagonStatus=  models.getVagonStatus('\'Cargo\''),
        cargoFoodType= models.getCargoType('\'Мясо\''), cargoFoodAmount = models.getCargoAmount('\'Мясо\''), cargoFoodStatus = models.getCargoStatus('\'Мясо\''), cargoFoodPass= models.getCargoPass('\'Мясо\''),
        cargoTechType= models.getCargoType('\'Техника\''), cargoTechAmount = models.getCargoAmount('\'Техника\''), cargoTechStatus = models.getCargoStatus('\'Техника\''),cargoTechPass = models.getCargoPass('\'Техника\''),
        cargoScienceType = models.getCargoType('\'Наука\''),cargoScienceAmount= models.getCargoAmount('\'Наука\''), cargoScienceStatus= models.getCargoStatus('\'Наука\'') , cargoSciencePass= models.getCargoPass('\'Наука\''),
        cargoFoodName = models.getCargoName('\'Мясо\''),cargoTechName = models.getCargoName('\'Техника\''), cargoSciencename = models.getCargoName('\'Наука\'')
        )
            else:
                flash("Неверный пароль!")

        if request.form.get('FoodSteal') == 'FoodSteal':
            rightpass = models.getCargoPass('\'Мясо\'')
            userpass = request.form['passFoodSteal']
            if rightpass == userpass:
                models.updateCargoStatus('\'Мясо\'')
                flash('Груз украден!')
                return render_template("station.html", timetotrain = getTime(), cargoVagonStatus=  models.getVagonStatus('\'Cargo\''),
        cargoFoodType= models.getCargoType('\'Мясо\''), cargoFoodAmount = models.getCargoAmount('\'Мясо\''), cargoFoodStatus = models.getCargoStatus('\'Мясо\''), cargoFoodPass= models.getCargoPass('\'Мясо\''),
        cargoTechType= models.getCargoType('\'Техника\''), cargoTechAmount = models.getCargoAmount('\'Техника\''), cargoTechStatus = models.getCargoStatus('\'Техника\''),cargoTechPass = models.getCargoPass('\'Техника\''),
        cargoScienceType = models.getCargoType('\'Наука\''),cargoScienceAmount= models.getCargoAmount('\'Наука\''), cargoScienceStatus= models.getCargoStatus('\'Наука\'') , cargoSciencePass= models.getCargoPass('\'Наука\''),
        cargoFoodName = models.getCargoName('\'Мясо\''),cargoTechName = models.getCargoName('\'Техника\''), cargoSciencename = models.getCargoName('\'Наука\'')
        )
            else:
                flash("Неверный пароль!")    
        return render_template("station.html", timetotrain = getTime(), cargoVagonStatus=  models.getVagonStatus('\'Cargo\''),
        cargoFoodType= models.getCargoType('\'Мясо\''), cargoFoodAmount = models.getCargoAmount('\'Мясо\''), cargoFoodStatus = models.getCargoStatus('\'Мясо\''), cargoFoodPass= models.getCargoPass('\'Мясо\''),
        cargoTechType= models.getCargoType('\'Техника\''), cargoTechAmount = models.getCargoAmount('\'Техника\''), cargoTechStatus = models.getCargoStatus('\'Техника\''),cargoTechPass = models.getCargoPass('\'Техника\''),
        cargoScienceType = models.getCargoType('\'Наука\''),cargoScienceAmount= models.getCargoAmount('\'Наука\''), cargoScienceStatus= models.getCargoStatus('\'Наука\'') , cargoSciencePass= models.getCargoPass('\'Наука\''),
        cargoFoodName = models.getCargoName('\'Мясо\''),cargoTechName = models.getCargoName('\'Техника\''), cargoSciencename = models.getCargoName('\'Наука\'')
        )
    
@app.route('/checker', methods=['GET','POST'])
def checker():  
    if request.method == "GET":
        ident = request.args.get('id')
        out = models.getHelp(ident)
        if len(out)>0:
            a = out[0]
            return make_response(str(a),200)
        else:
            return make_response('',503)

    if request.method == "POST":
        ident = request.args.get('id')
        value = request.args.get('value')
        try:
            models.addHelp(value,ident)
            return make_response(str(ident), 200)
        except Exception as e:
            return make_response("Exception!" + e.pgerror, 200)
            


@login_manager.unauthorized_handler
def unauthorized():
    return redirect(url_for('login'))

@login_manager.user_loader
def load_user(userlogin):
    return UserLogin().fromDB(userlogin)

def getTime():
    t = datetime.now()
    time = t.strftime("%M")

    if int(time)%30 == 0:
        num = randint(1,3)
        if num == 1:
            models.updateVagonStatus("False",'\'Head\'')
        elif num == 2:    
            models.updateVagonStatus("False",'\'Accounting\'')
        else:
            models.updateVagonStatus("False",'\'Cargo\'')

    if int(time)%5 == 0:
        models.renewCargo()
        return 'Поезд прибыл'
    else:
        out = 3 - int(time)%3 
        return out

class UserLogin():
    def fromDB(self,user):  
        self.__user = models.getUserID(user)
        return self
    def create (self,user):
        self.__user=user
        return self
    def is_authenticated(self):
        return True
    def is_active(self):
        return True
    def is_anonymous(self):
        return False
    def get_id(self):
        out = ""
        id = models.getUserID(self.__user)
        if len(id)!=0:
            for i in id:
                out = i
                break
            return out[0]
        else:
            return NULL

#регулярка
def validate(s):
    regex = re.compile(r'^[a-zA-Z0-9]+$')
    a = regex.match(str(s))
    if a !=None:
        return True
    else:
        return False

def encodeJWT(data):
    token = ""
    token = jwt.encode(data, "secret")
    return token.decode('UTF-8')

def decodeJWT(token):
    data = jwt.decode(token, "secret", algorithms=["HS256"], verify=False)
    return data

if __name__ == '__main__':
    models.createDB()
    app.run(debug=True, port = 11000, host='0.0.0.0')
