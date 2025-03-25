from flask_socketio import SocketIO, join_room, leave_room, emit
from flask import session
from models import db, Message, User, Chat, ChatUser, MessageTranslation
from sqlalchemy.exc import SQLAlchemyError
from translations import translate_text

socketio = SocketIO()



@socketio.on("join")
def handle_join(data):
    chat_id = data.get("chat_id")
    #print(chat_id)
    if not chat_id:
        emit("error", {"message": "chat_id is required"})
        return

    user = User.query.filter_by(username=session["username"]).first()
    if not user:
        emit("error", {"message": "User not found"})
        return

    chat = Chat.query.get(chat_id)
    if not chat:
        emit("error", {"message": "Chat not found"})
        return

    join_room(str(chat_id))
    print(f"{user.username} joined room {chat.roomCode}")
    emit("user_joined", {"username": user.username, "lang": user.language}, room=chat_id)

#recieves message from the client
@socketio.on("message")
def handle_message(data):
    print("Received message:", data)
    
    chat_id = str(data.get("chat_id"))
    content = data.get("content")
    
    if not chat_id or not content:
        emit("error", {"message": "chat_id and content are required"})
        print("Missing chat_id or content")
        return

    user = User.query.filter_by(username=session["username"]).first()
    if not user:
        emit("error", {"message": "User not found"})
        print("User not found")
        return

    chat = Chat.query.get(chat_id)
    if not chat:
        emit("error", {"message": "Chat not found"})
        print("Chat not found")
        return

  
    users_in_chat = db.session.query(User).join(ChatUser).filter(ChatUser.chat_session_id == chat.session_id).all()

    try:
        # Save the original message in the database
        sender_language = user.language

        new_message = Message(
            sender_id = user.id,
            chat_session_id = chat.session_id,
            org_cont=content
        )
        db.session.add(new_message)
        db.session.flush() #adds to the db without commiting yet
        
        translations = {}
        
        for recipient in users_in_chat:
            if recipient.id == user.id:
                continue
            
            target_language = recipient.language
            if sender_language != target_language:
                translated_content = translate_text(content, target_language)
            else:
                translated_content=content
                
            translations[recipient.language] = translated_content
            
            translation_entry = MessageTranslation(
                message_id=new_message.id,
                language = target_language,
                trans_cont = translated_content
            )
            print(recipient.language)
            db.session.add(translation_entry)
        db.session.commit()
        
        emit("new_message", {
                "username": user.username,
                "original_content": content,
                "translated_content": translations,
                "sender_language": sender_language
            }, room=chat_id)
        print(f"Message sent from {user.username} to room {chat.roomCode}")

    except SQLAlchemyError as e:
        db.session.rollback()
        emit("error", {"message": "Failed to save message"})
        print(f"Error saving message: {str(e)}")
    except Exception as e:
        emit("error", {"message": "Unexpected error occurred"})
        print(f"Unexpected error: {str(e)}")




@socketio.on("leave")
def handle_leave(data):
    chat_id = data.get("chat_id")
    if not chat_id:
        emit("error", {"message": "chat_id is required"})
        return

    user = User.query.filter_by(username=session["username"]).first()
    if not user:
        emit("error", {"message": "User not found"})
        return

    chat = Chat.query.get(chat_id)
    if not chat:
        emit("error", {"message": "Chat not found"})
        return

    leave_room(chat.roomCode)
    print(f"{user.username} left room {chat.roomCode}")
    emit("user_left", {"username": user.username}, room=chat_id)


@socketio.on("disconnect")
def handle_disconnect(data):
   # print("varmkorv: ",data)
    #chat = Chat.query.get(chat_id)
    username = session.get('username', 'Unknown user')
  #  print(f"{username} disconnected")
    #emit("user_left", {"username": username}, room=chat.roomCode)
