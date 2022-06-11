from re import sub
import sqlite3
import os
import numpy
from pymongo import MongoClient
import jwt
import time
import string    
import base64
import random
from frs import Face, FaceNotFound
from models import *
import cv2

class Code:
    def __init__(self,generated_by:str,subject_code:str,duration:int) -> None:
        self.code = self.__generate_random_code()
        self.generated_by = generated_by
        self.subject_code = subject_code
        self.generated_at = int(time.time())
        self.duration = int(duration)
    def __generate_random_code(self)-> str:
        chars = 6
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k = chars))   
        response = Database.findCode(code)
        if response is True:
            return self.__generate_random_code()
        return code
    def getCode(self):
        return self.code

class Database2:
    DB_NAME = "database.db"
    def __init__(self) -> None:
        self.cd = os.path.dirname(os.path.realpath(__file__))
        self.con = sqlite3.connect(self.cd+'\\'+Database2.DB_NAME+'.db', check_same_thread=False)
        self.cur = self.con.cursor()
    def createDatabase(self):
        self.con.execute('''CREATE TABLE students
                (first_name text, 
                last_name text, 
                enrollment_number text PRIMARY KEY, 
                email text, 
                password text, 
                picture_id text,
                authToken text)''')
        self.con.execute('''CREATE TABLE teachers
                        (first_name text,
                        last_name text,
                        teacher_id text PRIMARY KEY,
                        subject_main text,
                        email text,
                        password text,
                        authToken text)''')
        self.con.execute('''CREATE TABLE generated_codes
                         (code text PRIMARY KEY,
                         generated_by text,
                         generated_at text,
                         subject_issued text)''')
        self.con.execute("""CREATE TABLE subjects
                         (subject_id PRIMARY KEY,
                         name text,
                         )
                         """)
        self.con.execute("""CREATE TABLE attendance_data
                         (enrollment_number text,
                         
                         )""")

class Database:
    SECRET_KEY = "myFavKey"
    client =  MongoClient("mongodb+srv://ams:9826141207@ams.y7zpl.mongodb.net/ams?retryWrites=true&w=majority")
    db = client.ams
    def __init__(self) -> None:
        self.student_db = Database.db.students
        self.teacher_db = Database.db.teachers
        self.subjects_db = Database.db.subjects
        self.generated_codes_db = Database.db.generated_codes
        self.attendance_db = Database.db.attendance_data
        self.config_db = Database.db.config
        
    def addStudent(self,first_name,last_name,enrollment_number,branch,current_semester,email,password:str,picture_id=None):
        response = self.getStudent(enrollment_number.upper())
        if response:
            return
        authToken = jwt.encode({"first_name":first_name,"last_name":last_name,"enrollment_number":enrollment_number.upper(),"branch":branch,"current_semester":current_semester,"email":email},Database.SECRET_KEY,"HS256")
        password = base64.b64encode(password.encode("utf-8"))
        data = {"first_name":first_name,"last_name":last_name,"enrollment_number":enrollment_number,"branch":branch,"current_semester":current_semester,"email":email,"password":password,"picture_id":picture_id,"authToken":authToken}
        response = self.student_db.insert_one(data)
        return response
    
    def updateStudent(self,student:Student,face:Face,image):
        if not isinstance(face.img_encoding,numpy.ndarray): raise FaceNotFound()
        cv2.imwrite("src"+"//"+student.enrollment_number+".jpeg",image)
        face.exportImageData(student.enrollment_number)
        student.picture_id = student.enrollment_number
        update = {"$set":{"picture_id":student.enrollment_number}}
        data = {"enrollment_number":student.enrollment_number}
        self.student_db.find_one_and_update(data,update,upsert=True)
        return student
    
    def getStudent(self,enrollment_number=None,authToken=None,picture_id=None):
        if authToken:
            response = self.student_db.find_one({"authToken":authToken})
        elif enrollment_number:
            response = self.student_db.find_one({"enrollment_number":enrollment_number})
        elif picture_id:
            response = self.student_db.find_one({"picture_id":picture_id})
        if response:
            return Student(response)
    
    def addTeacher(self,first_name,last_name,teacher_id,subject_main,email,password):
        authToken = jwt.encode({"first_name":first_name,"last_name":last_name,"teacher_id":teacher_id.upper(),"subject_main":subject_main,"email":email},Database.SECRET_KEY,"HS256")
        password = base64.b64encode(password.encode("utf-8"))
        data = {"first_name":first_name,"last_name":last_name,"teacher_id":teacher_id,"email":email,"password":password,"subject_main":subject_main,"authToken":authToken}
        response = self.teacher_db.insert_one(data)
        return response
    
    def getTeacher(self,teacherId:str=None,authToken=None):
        if authToken:
            response = self.teacher_db.find_one({"authToken":authToken})
            if response:
                return Teacher(response)
        response = self.teacher_db.find_one({"teacher_id":teacherId})
        if response:
            return Teacher(response)
    
    def getCourses(self)->list:
        return self.config_db.find_one({"type":"courses"})["courses"]
    
    def addCourse(self,name:str):
        response = self.courseExist(name)
        if response:
            return
        data = {"type":"courses"}
        courses = self.getCourses()
        courses.append(name.upper())
        update = {"$set":{"courses":courses}}
        self.config_db.find_one_and_update(data,update=update,upsert=True)
        
    def deleteCourse(self,name:str):
        response = self.courseExist(name)
        if not response:
            return
        courses = self.getCourses()
        courses.remove(name.upper())
        update = {"$set":{"courses":courses}}
        data = {"type":"courses"}
        self.config_db.find_one_and_update(data,update=update,upsert=True)
        
    def courseExist(self,name):
        response = self.config_db.find_one({"type":"courses"})
        if response:
            if name.upper() in response.get("courses"):
                return True
        return False
    
    def addGeneratedCode(self,code:Code):
        data = {"code":code.code,"generated_by":code.generated_by,"subject_code":code.subject_code,"generated_at":code.generated_at,"duration":code.duration}
        self.generated_codes_db.insert_one(data)
        
    def getCode(self,code):
        data = {"code":code}
        response = self.generated_codes_db.find_one(data)
        return response
    def addSubject(self,name,subject_code,course,semester):
        course = course.upper()
        if self.courseExist(course) is False:
            return False
        data = {"name":name,"subject_code":subject_code,"course":course,"semester":semester}
        response = self.subjects_db.insert_one(data)
    
    def getSubject(self,subject_code=None,subject_name=None):
        if subject_name:
            data = {"name":subject_name}
            return self.subjects_db.find_one(data)
        data = {"subject_code":subject_code}
        return self.subjects_db.find_one(data)
    
    def getAllSubject(self,course_name=None,semester=None):
        data = {}
        if course_name:
            course_name = course_name.upper()
            data["course"] = course_name
        if semester:
            data["semester"] = semester
        response = list(self.subjects_db.find(data))
        response = [{k: v for k, v in d.items() if k != '_id'} for d in response]
        #for item in response:
        #    del item["_id"]
        return response
    
    def getAttendanceData(self,subject_code):
        data = {"subject_code":subject_code}
        response = self.attendance_db.find_one(data)
        if not response:
            self.addAttendanceSubject(subject_code)
            response = self.getAttendanceData(subject_code)
        return response
    def addAttendanceSubject(self,subject_code):
        data = {"subject_code":subject_code,"data":{}}
        self.attendance_db.insert_one(data)
        
    def updateAttendanceData(self,data):
        subject_code = data.get("subject_code")
        current_date = data.get("current_date")
        generated_code = data.get("generated_code")
        generated_by = data.get("generated_by")
        present = data.get("present")
        
        attendance_data = self.getAttendanceData(subject_code)["data"]
        if not attendance_data.get(current_date):
            attendance_data[current_date] = {
                "generated_code" : generated_code,
                "generated_by" : generated_by,
                "present": [
                    present
                ]
            }
        else:
            for record in attendance_data[current_date]["present"]:
                if record.get("enrollment_number") == present.get("enrollment_number"):
                    return 114
                if record.get("mac_address") == present.get("mac_address"):
                    return 116
            attendance_data[current_date]["present"].append(present)
        update = {"$set":{"data":attendance_data}}
        data = {"subject_code":subject_code}
        self.attendance_db.find_one_and_update(data,update,upsert=True)
        return 0
        
    def clearRecords(self):
        self.student_db.delete_many({})
        self.teacher_db.delete_many({})
        self.subjects_db.delete_many({})
        self.generated_codes_db.delete_many({})
    @staticmethod
    def findCode(code):
        data = {"code":code}
        response = Database.db.generated_codes.find_one(data)
        if response: return True
        else: return False