from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class ChatUser(db.Model):
    __tablename__ = 'chat_users'
    chat_session_id = db.Column(db.Integer, db.ForeignKey('chats.session_id'), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)

class Chat(db.Model):
    __tablename__ = 'chats'

    session_id = db.Column(db.Integer, primary_key=True, autoincrement=True)  
    name = db.Column(db.String(100), nullable=True)  
    roomCode = db.Column(db.String(6), nullable=False, unique=True)
    
    users = db.relationship('User', secondary='chat_users', backref='chat_s')
    
    messages = db.relationship('Message', backref='chat', cascade="all, delete-orphan")

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(25), unique=True, nullable=False)
    password_hashed = db.Column(db.String(100), nullable=False)
    language = db.Column(db.String(100), nullable=False)

    chats = db.relationship('Chat', secondary='chat_users', backref='users_in_chat')

    def set_password(self, password):
        self.password_hashed = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hashed, password)
 


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) 
    chat_session_id = db.Column(db.Integer, db.ForeignKey('chats.session_id'), nullable=False)

    org_cont = db.Column(db.Text, nullable=False)  
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp(), nullable=False)  

    translations = db.relationship('MessageTranslation',
                                   backref='message',
                                   cascade="all, delete-orphan")

#Extra db table to handle multiple translations for the same message
class MessageTranslation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('message.id'), nullable=False)
    language = db.Column(db.String(50), nullable=False)  
    trans_cont = db.Column(db.Text, nullable=False)  
