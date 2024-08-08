from tkinter import *
from tkinter import messagebox
from tkinter import ttk  # Import ttk module explicitly

import cv2
import os
from pymongo import MongoClient
import gridfs
import numpy as np
from PIL import Image
import datetime
import time

# MongoDB connection setup
client = MongoClient('mongodb://localhost:27017/')
db = client['AttendanceDB']
collection_profiles = db['Profiles']
collection_attendance = db['Attendance']
fs = gridfs.GridFS(db)

def save_profile_to_db(Id, name, images):
    profile_data = {"Id": Id, "Name": name, "Images": images}
    collection_profiles.insert_one(profile_data)

def get_profiles_from_db():
    profiles = collection_profiles.find()
    profile_list = []
    for profile in profiles:
        profile_list.append(profile)
    return profile_list

def save_attendance_to_db(Id, name, date, timestamp):
    attendance_data = {"Id": Id, "Name": name, "Date": date, "Time": timestamp}
    collection_attendance.insert_one(attendance_data)

def get_attendance_from_db(date):
    attendance_records = collection_attendance.find({"Date": date})
    attendance_list = []
    for record in attendance_records:
        attendance_list.append(record)
    return attendance_list

def save_image_to_db(image, filename):
    with open(filename, "rb") as f:
        return fs.put(f, filename=filename)

def TakeImages():
    Id = txt_id.get()
    name = txt_name.get()
    if Id.isnumeric() and name.isalpha():
        images = []
        cam = cv2.VideoCapture(0)
        harcascadePath = "E:Face Recognition \\haarcascade_frontalface_default.xml"
        detector = cv2.CascadeClassifier(harcascadePath)
        sampleNum = 0
        while True:
            ret, img = cam.read()
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = detector.detectMultiScale(gray, 1.3, 5)
            for (x, y, w, h) in faces:
                sampleNum += 1
                image_name = f"{name}.{Id}.{sampleNum}.jpg"
                cv2.imwrite(image_name, gray[y:y + h, x:x + w])
                image_id = save_image_to_db(gray[y:y + h, x:x + w], image_name)
                images.append(image_id)
                cv2.rectangle(img, (x, y), (x + w, y + h), (255, 0, 0), 2)
                cv2.imshow('Frame', img)
            if cv2.waitKey(100) & 0xFF == ord('q'):
                break
            elif sampleNum > 60:
                break
        cam.release()
        cv2.destroyAllWindows()
        save_profile_to_db(Id, name, images)
        res = "Images Saved for ID : " + Id + " Name : " + name
        message.configure(text=res)
    else:
        if not Id.isnumeric():
            res = "Enter Numeric Id"
            message.configure(text=res)
        if not name.isalpha():
            res = "Enter Alphabetical Name"
            message.configure(text=res)

def TrainImages():
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    harcascadePath = "E:\\Face Recognition \\haarcascade_frontalface_default.xml"
    detector = cv2.CascadeClassifier(harcascadePath)
    faces, Id = getImagesAndLabels()
    recognizer.train(faces, np.array(Id))
    recognizer.save("E:\\Face Recognition \\TrainingImageLabel\\Trainner.yml")
    res = "Image Trained"
    message1.configure(text=res)

def getImagesAndLabels():
    profiles = get_profiles_from_db()
    faces = []
    Ids = []
    for profile in profiles:
        for image_id in profile["Images"]:
            image_data = fs.get(image_id).read()
            image_np = np.frombuffer(image_data, dtype=np.uint8)
            image_np = cv2.imdecode(image_np, cv2.IMREAD_GRAYSCALE)
            faces.append(image_np)
            Ids.append(int(profile["Id"]))
    return faces, Ids

def TrackImages():
    images_unknown_dir = "E:\\Face Recognition \\ImagesUnknown"
    if not os.path.exists(images_unknown_dir):
        os.makedirs(images_unknown_dir)

    for k in tv.get_children():
        tv.delete(k)
    msg = ''
    i = 0
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    exists3 = os.path.isfile("E:\\Face Recognition \\TrainingImageLabel\\Trainner.yml")
    if exists3:
        recognizer.read("E:\\Face Recognition \\TrainingImageLabel\\Trainner.yml")
    else:
        messagebox.showerror('Data Missing', 'Please click on Save Profile to reset data!!')
        return
    harcascadePath = "E:\\Face Recognition \\haarcascade_frontalface_default.xml"
    detector = cv2.CascadeClassifier(harcascadePath)
    cam = cv2.VideoCapture(0)
    font = cv2.FONT_HERSHEY_SIMPLEX
    col_names = ['ID', 'Name', 'Date', 'Time']
    while True:
        ret, im = cam.read()
        gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
        faces = detector.detectMultiScale(gray, 1.2, 5)
        for (x, y, w, h) in faces:
            cv2.rectangle(im, (x, y), (x + w, y + h), (225, 0, 0), 2)
            Id, conf = recognizer.predict(gray[y:y + h, x:x + w])
            if conf < 50:
                ts = time.time()
                date = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
                timeStamp = datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')
                profile = collection_profiles.find_one({"Id": Id})
                if profile:
                    name = profile['Name']
                    tt = str(Id) + "-" + name
                    save_attendance_to_db(Id, name, date, timeStamp)
                    attendance = [str(Id), '', name, '', date, '', timeStamp]
                    if str(Id) not in msg:
                        msg += str(Id) + ' '
                        tv.insert('', i, text=str(i), values=(str(Id), str(name), date, timeStamp))
                        i += 1
            else:
                Id = 'Unknown'
                tt = str(Id)
            if conf > 75:
                noOfFile = len(os.listdir(images_unknown_dir)) + 1
                cv2.imwrite(os.path.join(images_unknown_dir, "Image" + str(noOfFile) + ".jpg"), im[y:y + h, x:x + w])
            cv2.putText(im, str(tt), (x, y + h), font, 1, (255, 255, 255), 2)
        cv2.imshow('Taking Attendance', im)
        if cv2.waitKey(1) == ord('q'):
            break
    cam.release()
    cv2.destroyAllWindows()
    res = "Attendance Taken"
    message1.configure(text=res)
    for k in tv.get_children():
        tv.delete(k)
    attendance_records = get_attendance_from_db(date)
    for record in attendance_records:
        tv.insert('', 0, text='', values=(record["Id"], record["Name"], record["Date"], record["Time"]))


# create the main window
root = Tk()
root.title("Face Recognition Attendance System")

# create labels and entry widgets for ID and Name
Label(root, text="Enter ID:").grid(row=0, column=0)
txt_id = Entry(root)
txt_id.grid(row=0, column=1)
Label(root, text="Enter Name:").grid(row=1, column=0)
txt_name = Entry(root)
txt_name.grid(row=1, column=1)

# create buttons for actions
Button(root, text="Take Images", command=TakeImages).grid(row=2, column=0, columnspan=2, pady=10)
Button(root, text="Train Images", command=TrainImages).grid(row=3, column=0, columnspan=2, pady=10)
Button(root, text="Track Attendance", command=TrackImages).grid(row=4, column=0, columnspan=2, pady=10)

# create a Treeview widget to display attendance records
tv = ttk.Treeview(root, columns=(1, 2, 3, 4), show='headings', height=8)
tv.grid(row=5, column=0, columnspan=2)
tv.heading(1, text='ID')
tv.heading(2, text='Name')
tv.heading(3, text='Date')
tv.heading(4, text='Time')

# create a message label for displaying messages
message = Label(root, text="")
message.grid(row=6, column=0, columnspan=2)
message1 = Label(root, text="")
message1.grid(row=7, column=0, columnspan=2)

root.mainloop()
