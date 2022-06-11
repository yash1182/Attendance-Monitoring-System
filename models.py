import base64
import time,string,random

class Actor:
    def __init__(self,data:dict) -> None:
        self.first_name = data.get("first_name")
        self.last_name = data.get("last_name")
        self.email = data.get("email")
        self.password = data.get("password")
        self.decrypted_password = base64.b64decode(self.password).decode("utf-8")
        self.authToken = data.get("authToken")
    def isEquals(self,password:str):
        """password must be in encrypted form."""
        password = base64.b64decode(password).decode("utf-8")
        return password==self.decrypted_password
    
    def getDecryptedPassword(self):
        return self.decrypted_password
    def getPassword(self):
        return self.password
    def getAuthToken(self):
        return self.authToken
    def getName(self):
        return self.first_name+" "+self.last_name
        
class Student(Actor):
    def __init__(self,studentData:dict) -> None:
        super().__init__(studentData)
        self.enrollment_number = studentData.get("enrollment_number")
        self.picture_id = studentData.get("picture_id")
        self.branch = studentData.get("branch")
        self.current_semester = studentData.get("current_semester")
        
class Teacher(Actor):
    def __init__(self,teacherData:dict) -> None:
        super().__init__(teacherData)
        
        self.teacher_id = teacherData.get("teacher_id")
        self.subject_main = teacherData.get("subject_main")
      

    