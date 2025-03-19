from flask import Flask, url_for, session, render_template, request, redirect
# from werkzeug.security import generate_password_hash, check_password_hash
from models import User, Chat, Message, ChatUser, MessageTranslation, db
from messageHandeling import socketio
from dotenv import load_dotenv
import os
from flask_sqlalchemy import SQLAlchemy
import random
import string

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

socketio.init_app(app)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///new_chat_database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

def generate_room_code():
   while True:
        room_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        existing_chat = Chat.query.filter_by(roomCode=room_code).first()
        if not existing_chat:
            return room_code

@app.route("/")
def home():
    if "username" in session:
        return redirect(url_for('dashboard'))
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):    
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            return render_template("login.html", error="Invalid username or password")
    return render_template("login.html")
    
    
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        language = request.form["language"]
        user = User.query.filter_by(username=username).first()
        if user:
            return render_template("register.html", error="User already exists")
        else:
            new_user = User(username=username, language=language)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            session["username"] = username
            return redirect(url_for('dashboard'))
    return render_template("register.html")

@app.route("/dashboard")
def dashboard():
    if "username" not in session:
        return redirect(url_for('login'))
    
    user = User.query.filter_by(username=session["username"]).first()

    if user is None:
        session.pop("username", None)  
        return redirect(url_for('login'))  

    chats = user.chats

    return render_template("dashboard.html", username=session["username"], chats = chats)
 

@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for('home'))    


@app.route("/chat_users/<int:chat_id>")
def chat_users(chat_id):
    if "username" not in session:
        return redirect(url_for('login'))
    
    chat = Chat.query.get_or_404(chat_id)
    users_in_chat = db.session.query(User).join(ChatUser).filter(ChatUser.chat_session_id == chat.session_id).all()
    
    return render_template("chat_users.html", chat=chat, users_in_chat=users_in_chat)
    

@app.route("/create_chat", methods=["POST", "GET"])
def create_chat():
    if "username" not in session:
        return redirect(url_for('login'))
    
    if request.method == "POST":
        chat_name = request.form["chat_name"]
        user = User.query.filter_by(username=session["username"]).first()
        
        new_chat = Chat(name=chat_name, roomCode=generate_room_code())
        db.session.add(new_chat)
        db.session.commit()

        chat_user = ChatUser(chat_session_id=new_chat.session_id, user_id=user.id)
        db.session.add(chat_user)
        db.session.commit()
        
        return redirect(url_for('chat', chat_id=new_chat.session_id))
    
    return render_template("create_chat.html")

#User enters one of the already joined chats from dashboard
@app.route("/join_chat/<int:chat_id>")
def join_chat(chat_id):
    if "username" not in session:
        return redirect(url_for('login'))
    
    user = User.query.filter_by(username=session["username"]).first()
    chat = Chat.query.get_or_404(chat_id)

    if ChatUser.query.filter_by(chat_session_id=chat.session_id, user_id=user.id).first():
        return redirect(url_for('chat', chat_id=chat.session_id))
    
    chat_user = ChatUser(chat_session_id=chat.session_id, user_id=user.id)
    db.session.add(chat_user)
    db.session.commit()
    
    return redirect(url_for('dashboard'))

#User enters roomcode to enter an existing chat
@app.route("/join_existing_chat", methods=["GET","POST"])
def join_existing_chat():
    if "username" not in session:
        return redirect(url_for('login'))

    if request.method == "POST":
        roomCode=request.form.get("roomCode")
        user = User.query.filter_by(username=session["username"]).first()

        chat = Chat.query.filter_by(roomCode=roomCode).first()

        if not chat:
            return redirect(url_for('dashboard'))

        if ChatUser.query.filter_by(chat_session_id=chat.session_id, user_id=user.id).first():
            return redirect(url_for('chat', chat_id=chat.session_id))

        chat_user = ChatUser(chat_session_id=chat.session_id, user_id=user.id)
        db.session.add(chat_user)
        db.session.commit()

        return redirect(url_for('chat', chat_id=chat.session_id))
    return redirect(url_for("dashboard"))


@app.route("/chat/<int:chat_id>")
def chat(chat_id):
    if "username" not in session:
        return redirect(url_for('login'))
    
    user = User.query.filter_by(username=session["username"]).first()
    chat = Chat.query.get_or_404(chat_id)
    
    if not ChatUser.query.filter_by(chat_session_id=chat.session_id, user_id=user.id).first():
        return redirect(url_for('dashboard'))
    
    messages = db.session.query(
        Message.id,
        Message.org_cont,
        User.username,
        User.language
        ).join(User, Message.sender_id == User.id).filter(Message.chat_session_id == chat.session_id).all()
    formatted_messages = []
    for msg_id, org_content, sender_username, original_language in messages:
        # Get all translations for this message
        translations = db.session.query(
            MessageTranslation.language,
            MessageTranslation.trans_cont
        ).filter(
            MessageTranslation.message_id == msg_id
        ).all()

        # Convert translations to a dictionary
        translation_dict = {lang: trans for lang, trans in translations}

        formatted_messages.append({
            "id": msg_id,
            "username": sender_username,
            "original_language": original_language,
            "original_content": org_content,
            "translations": translation_dict  
        })

    return render_template("chat.html", chat=chat, messages=formatted_messages, user=user)



@app.route("/leave/<int:chat_id>")
def leave(chat_id):
    if "username" not in session:
        return redirect(url_for('login'))
    
    user = User.query.filter_by(username=session["username"]).first()
    chat_user = ChatUser.query.filter_by(chat_session_id=chat_id, user_id=user.id).first()
    
    if chat_user:
        db.session.delete(chat_user)
        db.session.commit()
        
        remaining_users = ChatUser.query.filter_by(chat_session_id=chat_id).count()
        if remaining_users == 0:
            chat = Chat.query.get(chat_id)
            if chat:
                db.session.delete(chat)
                db.session.commit()
                return redirect(url_for('dashboard'))
    return redirect(url_for('dashboard'))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)

