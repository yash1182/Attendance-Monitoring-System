import cv2
import face_recognition
import os
import numpy

class FaceNotFound(Exception):
    def __init__(self) -> None:
        super().__init__("Face not found!")

class Face:
    def __init__(self,img_path=None,img=None) -> None:
        self.img_path = img_path
        self.img = img
        self.rgb_img = None
        self.img_encoding = None
        if not isinstance(self.img,numpy.ndarray) and self.img_path is not None:
            self.img = cv2.imread(self.img_path)
        if isinstance(self.img,numpy.ndarray):
            self.rgb_img = cv2.cvtColor(self.img,cv2.COLOR_BGR2RGB)
            try:
                self.img_encoding = face_recognition.face_encodings(self.rgb_img)[0]
            except Exception:
                self.img_encoding = None
    def exportImageData(self,name):
        if self.img_encoding is None: raise FaceNotFound()
        numpy.savetxt(FaceRecognitionSystem.FACES_SRC+"\\"+name+".csv",self.img_encoding,delimiter=',')
        
    def loadFaceFromData(self,data):
        self.img_encoding = numpy.loadtxt(data,delimiter=',')
        

class FaceRecognitionSystem:
    FACES_SRC = "faces"
    def __init__(self) -> None:
        if not os.path.isdir(FaceRecognitionSystem.FACES_SRC): raise Exception(f"Faces Database not found! Please create a Directory '{FaceRecognitionSystem.FACES_SRC}'.")
        self.faces = []
    def loadKnownFaces(self):
        faces_data_list = os.listdir(FaceRecognitionSystem.FACES_SRC)
        self.faces = [(faceFile.split(".")[0],numpy.loadtxt(FaceRecognitionSystem.FACES_SRC+"\\"+faceFile)) for faceFile in faces_data_list]
    @staticmethod
    def compareFace(face1:Face,face2:Face):
        if not isinstance(face1,Face) or not isinstance(face2,Face):
            raise Exception("Parameters must be of type Face.")
        if face1.img_encoding is None or face2.img_encoding is None: return False
        result = face_recognition.compare_faces([face1.img_encoding],face2.img_encoding)
        return result[0]        
    def checkFaceExist(self,face:Face):
        faces_encoding = [face_encoding for id , face_encoding in self.faces]
        if face.img_encoding is None: raise FaceNotFound
        result = face_recognition.compare_faces(faces_encoding,face.img_encoding)
        encodings = [id for id , face_encoding in self.faces]
        id = None
        if True in result: 
            t1 = result.index(True)
            id = encodings[t1]
            return True , id
        else: return False , id
        
