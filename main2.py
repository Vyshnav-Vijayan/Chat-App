from flask import Flask,render_template,request,flash,redirect,url_for,session,jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from flask_socketio import SocketIO,join_room,leave_room,send
import random,string
import os,base64
from string import ascii_uppercase

app=Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"]='sqlite:///db.database'
app.config["SECRET_KEY"]='secret'
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"]=False

socketio = SocketIO(app,cors_allowed_origin="*")
db=SQLAlchemy(app)

class RequestException(Exception):
    def __init__(self, status_code=500, message=""):
        self.status_code = status_code
        self.message = message
        super().__init__(self.message)

class BadRequestException(RequestException):
    def __init__(self, message=""):
        super().__init__(message=message, status_code=400)

class UnauthorisedAccessException(RequestException):
    def __init__(self, message=""):
        super().__init__(message=message, status_code=403)

class Users(db.Model):
    _id=db.Column("id",db.Integer,primary_key=True)
    name=db.Column(db.String(100))
    email=db.Column(db.String(100))
    password=db.Column(db.String(100))
    token=db.Column(db.String(100))
    token_expire=db.Column(db.String(100))

    def __init__(self,name,email,password):
        self.name=name
        self.email=email
        self.password=password
    def generate_token(self,validity_duration_hours=1):
        token = base64.b64encode(os.urandom(75)).decode('utf-8')
        current_time = datetime.utcnow()
        expire_time = current_time + timedelta(hours=validity_duration_hours)
        expire_time_str = expire_time.strftime("%Y-%m-%d %H:%M:%S UTC")
        
  
        setattr(self,'token',token)
        
        setattr(self,'token_expire',expire_time_str)
        db.session.commit()
   

        return (self.token,self.token_expire)
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
    
    def user_details(self):
        room_id = Room.query.filter_by(user_id = self._id).first()
        data = {
            "id" :self._id,
            "name" :self.name,
            "email" :self.email,
            "password" :self.password,
            
        }
        data["room_id"]=room_id.room_id
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
    def user_message(self):
        data = {
            "id" :self._id,
            "message_from" :self.message_from,
            "message_to" :self.message_to,
            "message" :self.message,
            "time" :self.time,
            
        }
        return data

room={}

def allowed_users():
    def wrapper(f):

        def wrapped_function(*args, **kwargs):
            unauthorised = False
            token = request.headers.get('Authorization')[7:]
            print(token,"this is token")
            search=Users.query.filter_by(token=token).first()
            if search is None:
                unauthorised = True
            else:
                current_time = datetime.utcnow()
                token_time=datetime.strptime(search.token_expire,"%Y-%m-%d %H:%M:%S UTC")
                if current_time > token_time:
                    unauthorised = True

            if unauthorised:
                raise UnauthorisedAccessException(message="Un-authorized access exception")

            return f(*args, **kwargs)

        # Renaming the function name:
        wrapped_function.__name__ = f.__name__

        return wrapped_function

    return wrapper


def generate_room_code(length):
    return os.urandom(length)





@app.route('/')
@app.route('/home')
def index():
    if "name" in session:
        return render_template("user.html",uname=session["name"],value=Users.query.all())
    else:
        return render_template("register.html")
    
@app.route('/home_flutter')
def index_flutter():
    if "name" in session:
        return jsonify(uname=session["name"],value=Users.query.all())
    else:
        return jsonify({'error': "user already regitered"}),404
    


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
        

@app.route('/register_flutter',methods=['POST','GET'])
def register_flutter():
    if request.method=="POST":
        uname=request.json.get('user_name')
        uemail=request.json.get('user_email')
        upassword=request.json.get('user_password')
        hash_pwd=generate_password_hash(upassword)
        search=Users.query.filter_by(email=uemail).first()
        if search:
            return jsonify({'error': "user already regitered!"}),404
        else:
            usr=Users(uname,uemail,hash_pwd)
            db.session.add(usr)
            db.session.commit()
            rm=Room(''.join(random.SystemRandom().choice(string.digits) for _ in range(5)),usr._id)
            db.session.add(rm)
            db.session.commit()
            return jsonify("Registered")




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


@app.route('/login2_flutter',methods=['POST'])
def login2_flutter():
    if request.method=="POST":
        uemail=request.json.get('user_email')
        upwd=request.json.get('user_password')
        search=Users.query.filter_by(email=uemail).first()
        if search:
            print(search)
            if check_password_hash(search.password,upwd):
                session["name"]=search.name
                session["user_id"]=search._id
                search2=Room.query.filter_by(user_id=search._id).first()
                session["room_id"]=search2.room_id

                search.generate_token()
                
                v=Users.query.all()
                value = [user.user_details() for user in v]
                print(session,"this is session")
                return jsonify({"value":value, "userid":search._id , "username":search.name ,"token":search.token,"room_id":search2.room_id })
            else:
                return jsonify({'error': " wrong password"}),404
        else:
            return jsonify({'error': " no user"}),404
    return jsonify({'error': " wrong request!!!"}),404

@app.route('/user_list')
def user_list():
    value=Users.query.all()
    result = [user.user_details() for user in value]

    # value2=Messages.query.all()
    # result2=[msg.user_message() for msg in value2]
    return jsonify(result)
        

@app.route('/logout')
def logout():
    session.pop("name",None)
    return redirect(url_for('login'))



@app.route('/user')
def user():
    if "name" in session:
        return render_template("user.html",uname=session["name"],value=Users.query.all())
    else:
        return render_template("register.html")
    
@app.route('/user_flutter')
def user_flutter():
    if "name" in session:
        return jsonify(uname=session["name"],value=Users.query.all())
    else:
        return jsonify({'error': " err!!!"}),404
    

@app.route('/chat/<int:id>')
def chat(id):
    if "name" in session:
        usrf=Room.query.filter_by(_id=session["user_id"]).first()
        usrt=Room.query.filter_by(_id=id).first()


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


@app.route('/chat_flutter',methods=['POST'])
@allowed_users()
def chat_flutter():
    if request.method=="POST":
        id=request.json.get('login_Id')
        user_id=request.json.get('chat_PersonId')   
        usrf=Room.query.filter_by(user_id=user_id).first()
        usrt=Room.query.filter_by(user_id=id).first()

        all_msg = Messages.query.filter(Messages.message_from.in_([usrf.room_id,usrt.room_id]),Messages.message_to.in_([usrf.room_id,usrt.room_id])).all()
        result = [user.user_message() for user in all_msg]
        print(result)
        return jsonify(result)      
    else:
        return jsonify({'error': " login error!!!"}),404






@socketio.on("connect")
@allowed_users()
def connect():
    token = request.headers.get('Authorization')[7:]
    print(token,"this is token")
    print("this is session :",session)
    user_name = session.get('name')
    room = session.get("room_id")
    join_room(room)
    print(user_name,"connected!")

@socketio.on("message")
def get_and_store_message(data):
    print("atlears rehced here")
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
    user_name = session.get("name")
    room = session["room_id"]
    leave_room(room)
    print(user_name,": disconnected!")

if __name__=="__main__":
    with app.app_context():
        db.create_all()
    socketio.run(app,debug=True)


