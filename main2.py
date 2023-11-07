from flask import Flask,render_template,request,flash,redirect,url_for,session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from flask_socketio import SocketIO,join_room,leave_room,send
import random,string
import os
from string import ascii_uppercase
app=Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"]='sqlite:///db.database'
app.config["SECRET_KEY"]='secret'
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"]=False

socketio = SocketIO(app,cors_allowed_origin="*")
db=SQLAlchemy(app)

class Users(db.Model):
    _id=db.Column("id",db.Integer,primary_key=True)
    name=db.Column(db.String(100))
    email=db.Column(db.String(100))
    password=db.Column(db.String(100))

    def __init__(self,name,email,password):
        self.name=name
        self.email=email
        self.password=password
    def to_dict(self,propagation):
        data = {
            "id" :self._id,
            "name" :self.name,
            
        }

        if propagation > 0:
            propagation = propagation -1

            if self._id:
                room_id = Room.query.filter(Room.user_id == self._id).first()
                if room_id:
                    data['room_id'] = room_id.room_id

        return data
    
class Room(db.Model):
    _id=db.Column("id",db.Integer,primary_key=True)
    room_id=db.Column(db.String(100))
    user_id=db.Column(db.String(100))

    def __init__(self,room_id,user_id):
        self.room_id=room_id
        self.user_id=user_id
class Messages(db.Model):
    _id = db.Column("id",db.Integer,primary_key=True)
    message_from = db.Column(db.String(100))
    message_to = db.Column(db.String(100))
    message = db.Column(db.String(100))
    time = db.Column(db.String(100))


    def __init__(self,message,message_from,message_to,time):
        
        self.message = message
        self.message_from = message_from
        self.message_to = message_to
        self.time = time

room={}
def generate_room_code(length):
    return os.urandom(length)





@app.route('/')
@app.route('/home')
def index():
    if "name" in session:
        return render_template("user.html",uname=session["name"],value=Users.query.all())
    else:
        return render_template("register.html")

@app.route('/register',methods=['POST','GET'])
def register():
    if request.method=="POST":
        uname=request.form['user_name']
        uemail=request.form['user_email']
        upassword=request.form['user_password']
        hash_pwd=generate_password_hash(upassword)
        search=Users.query.filter_by(email=uemail).first()
        if search:
            flash("user already regitered","")
            return render_template("register.html")
        else:
            usr=Users(uname,uemail,hash_pwd)
            db.session.add(usr)
            db.session.commit()
            rm=Room(''.join(random.SystemRandom().choice(string.digits) for _ in range(5)),usr._id)
            db.session.add(rm)
            db.session.commit()
            flash("You have been regitered sucessfully")
            return render_template("login.html")

@app.route('/login')
def login():
    if "name" in session:
        return render_template("user.html",uname=session["name"],value=Users.query.all())
    else:
        return render_template("login.html")
@app.route('/login2',methods=['POST'])
def login2():
    if request.method=="POST":
        uemail=request.form['user_email']
        upwd=request.form['user_password']
        search=Users.query.filter_by(email=uemail).first()
        if search:
            if check_password_hash(search.password,upwd):
                session["name"]=search.name
                session["user_id"]=search._id
                search2=Room.query.filter_by(user_id=search._id).first()
                session["room_id"]=search2.room_id
                return render_template("user.html",uname=session["name"],value=Users.query.all())
            else:
                flash("Can't Logg in!!!")
                return render_template("login.html")
        else:
            return render_template("login.html")
    return render_template("login.html")

@app.route('/logout')
def logout():
    session.pop("name",None)
    return redirect(url_for('login'))

@app.route('/view')
def view():
    details=Users.query.all()
    details2=Messages.query.all()
    return render_template('view.html',value=details,value2=details2)

@app.route('/user')
def user():
    if "name" in session:
        return render_template("user.html",uname=session["name"],value=Users.query.all())
    else:
        return render_template("register.html")
@app.route('/chat/<int:id>')
def chat(id):
    if "name" in session:
        usrf=Room.query.filter_by(_id=session["user_id"]).first()
        usrt=Room.query.filter_by(_id=id).first()

        # userf_message = Messages.query.filter_by(message_from = usrf.room_id,message_to = usrt.room_id).all()
        # usert_message = Messages.query.filter(Messages.message_from == usrt.room_id,Messages.message_to == usrf.room_id).all()
        roomid=session["room_id"]
        all_msg = Messages.query.filter(Messages.message_from.in_([usrf.room_id,usrt.room_id]),Messages.message_to.in_([usrf.room_id,usrt.room_id])).all()
        uf_name=Users.query.filter_by(_id=session["user_id"]).first()
        ut_name=Users.query.filter_by(_id=id).first()
        all_users = Users.query.all()
        all_users_dict = [user.to_dict(1) for user in all_users]
        print(all_users_dict,"all user")
        return render_template("chat.html",roomid=roomid,uf_name=uf_name,ut_name=ut_name,usrf_id=usrf.room_id,usrt_id=usrt.room_id,uname=session['name'],va=Users.query.filter_by(_id=id).first(),data=all_msg,value=all_users_dict)
    else:
        return render_template("register.html")
@app.route('/send/<int:id>',methods=['POST'])
def send__data(id):
    if "name" in session:
        if request.method=="POST":
            message=request.form['msg']
            usrf=Room.query.filter_by(_id=session["user_id"]).first()
            usrt=Room.query.filter_by(_id=id).first()                   
            a=Messages(message,usrf.room_id,usrt.room_id,datetime.now())
            db.session.add(a)
            db.session.commit()
            # session["sendr"]=usrf
            # session["recir"]=usrt
            roomid=session["room_id"]
            # userf_message = Messages.query.filter_by(message_from = usrf.room_id,message_to = usrt.room_id).all()
            # usert_message = Messages.query.filter(Messages.message_from == usrt.room_id,Messages.message_to == usrf.room_id).all()
            all_msg = Messages.query.filter(Messages.message_from.in_([usrf.room_id,usrt.room_id]),Messages.message_to.in_([usrf.room_id,usrt.room_id])).all()
            return render_template("chat.html",roomid=roomid,usrf_id=usrf.room_id,usrt_id=usrt.room_id,uname=session['name'],va=Users.query.filter_by(_id=id).first(),data=all_msg,value=Users.query.all())
    else:
        return render_template("register.html")       





@socketio.on("connect")
def connect():
    user_name = session["name"]
    room = session["room_id"]
    join_room(room)
    print(user_name,"connected!")

@socketio.on("message")
def get_and_store_message(data):
    if data['message_input']:
        msg = data['message_input']
        sender = data['sender']
        receiver = data['receiver']
        content = {
            "f_rid": data['sender'],
            "msg": data['message_input'],
            "t_rid": data["receiver"],
            "name": session["name"]
        }
        new_msg = Messages(msg,sender,receiver,data['currenttime'])
        db.session.add(new_msg)
        db.session.commit()

        send(content,to=sender)
        send(content,to=receiver)

socketio.on("disconnect")
def disconnect():
    user_name = session["name"]
    room = session["room_id"]
    leave_room(room)
    print(user_name,": disconnected!")

if __name__=="__main__":
    with app.app_context():
        db.create_all()
    socketio.run(app,debug=True)

