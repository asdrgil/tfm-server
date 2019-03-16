from app import db

#Check if user exists. Returns 0 if it does not exist, else return it's role (1 = therapist, 2 = admin)
def checkUser(mail, password):
    user = collection.find_one({"mail": mail})
    
    #Check if the given user is registered and the password is correct
    if not user or not user.get("password") == password:
        return -1
    
    return user.get("role")
