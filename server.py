#from re import sub
from random import getrandbits
from urllib import response
from flask import Flask, request, current_app
import flask
from flask_restful import Api
from flask_restful import Resource
import os
import json
import base64
import ssl
import requests
import jwt
import sqlite3
import logging
import time
import datetime
import cv2
from models import *
import dbms
from dbms import Code   
import numpy as np
from frs import *

cd = os.path.dirname(os.path.realpath(__file__))
app = Flask(__name__)
api = Api(app)
logger = logging.Logger("logger")
db = dbms.Database()

def getResponse(errorCode=0,data:dict=None):
    error_codes = {"400":"Missing Parameters.",
                   "401":"Unauthorized.",
                   "403":"The server understands the request but refuses to authorize it.",
                   "101":"Something went Wrong.",
                   "102":"Invalid Enrollment Number/Teacher ID or password.",
                   "103":"Invalid Code! Please check again.",
                   "110":"Profile Picture Update Required!",
                   "111":"Face not Found!",
                   "112":"Face does not match with any registered Student!",
                   "113":"Attendance Code is expired!",
                   "114":"Attendance already marked!",
                   "115":"You are not inside Institute!",
                   "116":"An attendance with your phone is already marked!",
                   "117":"Face matched with other Student!",
                   "118":"Invalid Enrollment Number!"
                   }
    if errorCode!=0:
        status = "failed"
    else:
        status = "success"
    response = {"errorCode":errorCode,"error":error_codes.get(str(errorCode)),"status":status}
    if not data:
        return response
    return {**data,**response}

class login(Resource):
    def post(self):
        content = request.get_json()
        print(content)
        if request.is_json is False:
            data = {"errorCode":400,"error":"Paremeters Missing.","status":"failed"}
            return data
        mustneed = ["enrollNum","password"]
        for query in mustneed:
            if not content.get(query):
                return {"error":400,"error":f"{query} parameter missing."}
        enrollment_number = content.get("enrollNum")
        password = content.get("password")
        response = db.getStudent(enrollment_number)
        if not response:
            response= db.getTeacher(enrollment_number)
            if not response: return {"errorCode":102,"status":"failed","error":"Invalid Enrollment Number/Teacher ID or password."}
            else: obj = response
        else: obj = response
        try:
            if obj.isEquals(password) is False:
                return getResponse(102)
            if isinstance(obj,Teacher): loginType = "teacher"
            else: loginType = "student"
            return {"authToken":obj.getAuthToken(),"loginType":loginType,"status":"success","errorCode":0}
        except Exception as e:
            return getResponse(102)

        
class getProfile(Resource):
    def get(self):
        authToken = request.headers.get("Authorization")
        
        if not authToken: return getResponse(401)
        try:
            authToken = authToken.split(" ")[1]
        except IndexError:
            print("index error")
            return getResponse(401)
        response = db.getStudent(authToken=authToken)
        if not response:
            response = db.getTeacher(authToken=authToken)
            if not response: return getResponse(401)
            else: obj = response
        else: obj = response
        if isinstance(obj,Teacher): data = {"first_name":obj.first_name,"last_name":obj.last_name,"email":obj.email,"teacher_id":obj.teacher_id,"subject_main":obj.subject_main}    
        else: data = {"first_name":obj.first_name,"last_name":obj.last_name,"email":obj.email,"enrollment_number":obj.enrollment_number,"branch":obj.branch,"current_semester":obj.current_semester,"picture_id":obj.picture_id}
        return getResponse(data=data)
        
class getSubjectList(Resource):
    def get(self):
        subjects = db.getAllSubject()
        return getResponse(data={"subjects":subjects})
    def post(self):
        if request.is_json is False:
            return getResponse(errorCode=400)
        content = request.get_json()
        mustneed = ["semester"]
        course = "CSE"
        for query in mustneed:
            if not content.get(query):
                return {"error":400,"error":f"{query} parameter missing."}
        response = db.getAllSubject(course,semester=str(content.get("semester")))
        print(response)
        return getResponse(0,{"subjects":response}) 
class getFormList(Resource):
    def get(self):
        subjects = db.getAllSubject()
        data = {"data":[{"name":"Computer Science and Engineering","max_semesters":8,"max_section":3,"subjects":subjects}]}
        return getResponse(data=data)  
    
class generateCode(Resource):
    def post(self):
        if request.is_json is False:
            return getResponse(errorCode=400)
        content = request.get_json()
        mustneed = ["branch","semester","section","subject","duration"]
        for query in mustneed:
            if not content.get(query):
                return {"error":400,"error":f"{query} parameter missing."}
        authToken = request.headers.get("Authorization")
        if not authToken: return getResponse(401)
        try:
            authToken = authToken.split(" ")[1]
        except IndexError:
            return getResponse(401)
        teacher = db.getTeacher(authToken=authToken)
        if not teacher:
            return getResponse(401)
        subject = db.getSubject(subject_name=content.get("subject"))
        print(subject)
        code = Code(teacher.teacher_id,subject.get("subject_code"),content.get("duration"))
        
        db.addGeneratedCode(code)
        data = {"code":code.getCode()}
        return getResponse(data=data)
    

class updateProfile(Resource):
    def post(self):
        if request.is_json is False: return getResponse(errorCode=400)
        content = request.get_json()
        authToken = request.headers.get("Authorization")
        if not authToken: return getResponse(401)
        try:
            authToken = authToken.split(" ")[1]
        except IndexError:
            return getResponse(401)
        #obj = db.getTeacher(authToken=authToken)
        #if not obj: 
        obj = db.getStudent(authToken=authToken)
        if not obj: return getResponse(401)
        encodedImage = content["encoded_image"]
        try:   
            nparr = np.frombuffer(base64.b64decode(encodedImage), np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            image =cv2.rotate(image,cv2.ROTATE_90_COUNTERCLOCKWISE)
            #cv2.imwrite(cd+"/im.jpg",image)
            face = Face(img=image)
            #image = cv2.imread(image)
            frs = FaceRecognitionSystem()
            frs.loadKnownFaces()
            try:
                response,id = frs.checkFaceExist(face)
                if response is True and id!=obj.enrollment_number:
                    return getResponse(117)
                db.updateStudent(obj,face,image)
            except FaceNotFound as e:
                print(str(e))
                return getResponse(111)    
        except Exception as e:
            print(str(e))
            return getResponse(111)
        
        return getResponse()
          
class loadImage(Resource):
    def get(self):
        authToken = request.headers.get("Authorization")
        if not authToken: return getResponse(401)
        try:
            authToken = authToken.split(" ")[1]
        except IndexError:
            return getResponse(401)
        obj = db.getStudent(authToken=authToken)
        if not obj: return getResponse(401)
        if not obj.picture_id:
            return getResponse(110)
        return flask.send_file("src"+"//"+f"{obj.picture_id}.jpeg", mimetype='image/gif')


class submitCode(Resource):
    def post(self):
        if request.is_json is False: return getResponse(errorCode=400)
        content = request.get_json()
        
        code = content.get("code")
        macAddress = content.get("mac_address")
        #verify if student is inside institute
        ip_pool = request.remote_addr.split(".")
        ip_pool.pop()
        ip_address = ".".join(ip_pool)
        print(request.remote_addr)
        #if request.remote_addr != "49.35.169.20": phone
        if not ip_address.startswith("192.168.29"):
        
            return getResponse(115)
        response = db.getCode(code)
        if not response:
            return getResponse(103)
        generated_at = response.get("generated_at")
        current_time = int(time.time())
        duration = response.get("duration")
        #checking if code is expired
        if current_time-generated_at>duration: 
            return getResponse(113)
        return getResponse()
        

class markAttendance(Resource):
    def post(self):
        if request.is_json is False: return getResponse(errorCode=400)
        authToken = request.headers.get("Authorization")
        if authToken:
            try:
                authToken = authToken.split(" ")[1]
            except IndexError as e:
                print(str(e))
                return getResponse(401)
            except AttributeError as e:
                print(str(e))
                return getResponse(401)
            if not authToken: 
                print("auth invalid")
                return getResponse(401)
        
            if db.getTeacher(authToken=authToken) is None: 
                print("teacher invalid")
                return getResponse(401)

        content = request.get_json()
        code = content.get("code")
        mac_address = content.get("mac_address")
        manual = content.get("manual")
        enrollment_number = content.get("enrollment_number")
        encodedImage = content.get("encoded_image")
        if manual is True:
            code_response = db.getCode(code) #invalid code
            if not code_response:
                return getResponse(103)
            generated_at = code_response.get("generated_at")
            manual_date = datetime.datetime.fromtimestamp(generated_at)
            manual_date = str(manual_date.date().strftime("%d-%m-%Y"))
            teacher_response = db.getTeacher(authToken=authToken)
            student_response = db.getStudent(enrollment_number=enrollment_number)
            data = {
                "subject_code": code_response.get("subject_code"),
                "current_date":manual_date,
                "generated_code":code_response.get("code"),
                "generated_by":code_response.get("generated_by"),
                "present":{
                    "enrollment_number":student_response.enrollment_number,
                    "manual":manual,
                    "mac_address":None,
                    "marked_by":teacher_response.teacher_id
                }
            }
            response = db.updateAttendanceData(data)
            if not student_response: return getResponse(response)
            return getResponse(response)
        try:   
            nparr = np.frombuffer(base64.b64decode(encodedImage), np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            image =cv2.rotate(image,cv2.ROTATE_90_COUNTERCLOCKWISE)
            face = Face(img=image)            
            frs = FaceRecognitionSystem()
            frs.loadKnownFaces()
            try:
                response,picture_id = frs.checkFaceExist(face)
                if response is False:
                    print("face not exist in database!")
                    return getResponse(112)
            except FaceNotFound as e:
                print(str(e))
                print("Face not found!")
                return getResponse(111)    
        except Exception as e:
            print(str(e))
            return getResponse(111)
        # logic to verify face and mark their attendance repectively
        
        code_response = db.getCode(code) #invalid code
        if not code_response:
            print("invalid code")
            return getResponse(103)
        
        student_response = db.getStudent(picture_id)
        if not student_response:
            print("student not found!")
            return getResponse(101)
        current_date = str(datetime.datetime.now().date().strftime("%d-%m-%Y"))
        data = {
            "subject_code":code_response.get("subject_code"),
            "current_date": current_date,
            "generated_code": code_response.get("code"),
            "generated_by" : code_response.get("generated_by"),
            "present":{
                    "enrollment_number":student_response.enrollment_number,
                    "manual":manual,
                    "mac_address":mac_address,
                    "marked_by":None
                }
        }
        response = db.updateAttendanceData(data)
        print("Face verified Successfully!")
        return getResponse(response)
        
        
api.add_resource(login,"/login")
api.add_resource(getProfile,"/profile")
api.add_resource(getSubjectList,"/subjects")
api.add_resource(getFormList,"/config")
api.add_resource(generateCode,"/generatecode")
api.add_resource(updateProfile,"/updateprofile")
api.add_resource(loadImage,"/loadimage")
api.add_resource(submitCode,"/submitcode")
api.add_resource(markAttendance,"/markattendance")

if __name__ == '__main__':
    
    #app.run(debug=True,host="172.31.43.10",port=8080) #server
    app.run(debug=True,host="192.168.29.47",port=8080)

