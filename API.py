
from unicodedata import name
from matplotlib.pyplot import connect
import uvicorn
from fastapi import FastAPI
import py_functions
import config 
import pyodbc
import json
import hashlib
import pandas as pd

class Doctor:
    def __init__(self, name, email,number,specialty):
        self.name=name
        self.email=email
        self.number=number
        self.specialty=specialty


app=FastAPI()

def connect_db():

    server="localhost:3306"
    database="doctor"
    uid="root"
    passwd=""
    for drivers in pyodbc.drivers():
        print(drivers)
    con="DRIVER={MySQL ODBC 8.0 ANSI Driver};SERVER="+server+";DATABASE="+database+";UID="+uid+";PWD="+passwd
    connection=pyodbc.connect(con)
    connection.autocommit=True
    cur=connection.cursor()
    print("Connected")
    return connection,cur

connection,cur=connect_db()


#Starting server
@app.get('/')
def get_data():
    return "Hello"
@app.post('/signup')
def signup(Name: str, email:str,password:str,username:str,type:str="patient",API_KEY=""):
    if "@" not in email or "." not in email:
        return{"Invalid Email"}
    elif "=" in email or "=" in Name or '=' in username or '*' in username or '*' in email or '*' in Name:
        return{"Error"}
    elif API_KEY=="dabdde079bcaac65b939992610420dfc":#get API KEY 
        df = pd.read_sql("SELECT * FROM acc_info", connection)  #Check if email or username exists
        for i in df['email']:
            if email==i:
                return{"Email Already Exists"}
        for i in df['username']:
            if username==i:
                return{"Username Already Exists"}
        #Set UserType
        if type=="doctor":
            ntype=1
            connection.execute("INSERT INTO doc_info values (NULL,'{}','{}',NULL,NULL)".format(Name,email))
        elif type=="admin":
            ntype=0
        elif type=="patient":
            ntype=2
        #Hash Password
        hashp=hashlib.md5(password.encode('utf8')).hexdigest()
        #insert into Database
        connection.execute("INSERT INTO acc_info values (NULL,'{}','{}','{}','{}',{})".format(email,hashp,Name,username,ntype))
        return({"User Added Successfully"})
    else:
            return{"API Key not found"}
        

@app.post('/Login')
def login(password:str,username:str,):
    df = pd.read_sql("SELECT * FROM acc_info", connection) 
    for index,i in enumerate(df['username']):
        if username==i and hashlib.md5(password.encode('utf8')).hexdigest()==df['password'][index]: #Check if username and password are correct
            return {"Successfully Entered"}
    return("Wrong username or password")

@app.post('/setDocInfo/{email}')
#set doctor information seperately
def setInfo(Number:str,Specialty:str,email:str,API_KEY:str):
        if API_KEY=="dabdde079bcaac65b939992610420dfc":
            if len(Number)<=11:
                cur.execute("UPDATE doc_info SET ONumber ='{}',Specialty='{}' WHERE email='{}'".format(Number,Specialty,email)) 
                return("Set Successfully")
            else:
                return("Number should be less than 11 digits")
        else:
            return("API KEY WRONG")
@app.get('/doctors')
#get list of doctors
def getDoctorNames(API_KEY:str):
    if API_KEY=="dabdde079bcaac65b939992610420dfc":
        df = pd.read_sql("SELECT * FROM doc_info", connection) 
        arr=[]
        for index, i in df.iterrows():
            arr.append(i['Doctor_name'])
    return(arr) 
@app.get('/doctors/{ID}')
#using doctor class to output to api
def getDocInfo(API_KEY:str,ID:int):
    if API_KEY=="dabdde079bcaac65b939992610420dfc":
        df = pd.read_sql("SELECT * FROM doc_info WHERE docID={}".format(ID), connection) 
        arr=[]
        for index, i in df.iterrows():
            arr.append(Doctor(i['Doctor_name'],i['email'],i['ONumber'],i['Specialty']))
        print(arr)
    return(arr) 

@app.get('/doctors/{ID}/slots')
#using doctor class to output to api
def getDocInfoSlots(API_KEY:str,ID:int):
    timex=0
    if API_KEY=="dabdde079bcaac65b939992610420dfc":
        cur.execute("SELECT Doctor_name from doc_info where docID={}".format(ID))
        x=cur.fetchval()

    df = pd.read_sql("SELECT * FROM appointments WHERE Doctor_name='{}'".format(x), connection)
    timex=0
    if (df.size)==0:
        return{"Dr. {} is fully available".format(x)}
    for index, i in df.iterrows():
        timex=timex+i['App_time']
        indexes=index+1
    if indexes>=12 or timex>=480:
        return{"Dr. {} is not available at all for today...".format(x)}
    return{"Dr. {} is availabe for {} appointments or {} more hours".format(x,12-indexes,8-(timex/60))}
     

#FIFO Approach to Appointments with time being set after url 
       

    
@app.get('/createappointment/{time}/{var}') #set time and interval of appointment //dont have much experience in dealing with days and time with SQL
def createappointment(doc_name:str,patient_id:int,time:int,var:str):
    df = pd.read_sql("SELECT * FROM appointments WHERE Doctor_name='{}'".format(doc_name), connection)
    timex=0
    indexes=0
    for index, i in df.iterrows():
        timex=timex+i['App_time'] #Calculate time in minutes
        indexes=index+1
    if indexes>=12 or timex>=480: #if conditions met do not set the appointment
        return{"Doctor Unavailable"} 
    else:
        #If all true set the appointment
        if var=="min" and (time>=15 or time<=59):
            connection.execute("INSERT INTO appointments values (NULL,'{}','{}',{})".format(doc_name,patient_id,time))
            return{"Appointment set for {} mins".format(time)}
        elif var=="hrs" and (time>=1 or time<=2):
            time=time*60
            connection.execute("INSERT INTO appointments values (NULL,'{}','{}',{})".format(doc_name,patient_id,time))
            return{"Appointment set for {} hours".format(time/60)}
        else: 
            return("Setup Appointment Correctly Please")

@app.get('/findavailability')
def findAvailableDoctors():
    #Goes through all dr that have appointments

    df = pd.read_sql("SELECT * FROM appointments", connection)
    timex=0
    arr=[]
    for i in df['Doctor_name']:
        for index, j in df.iterrows():
            timex=timex+j['App_time']
            indexes=index+1

            if indexes>=12 or timex>=480:
                arr.append("Dr. {} is not available at all for today...".format(i))
            arr.append("Dr. {} is availabe for {} appointments or {} more hours".format(i,12-indexes,8-(timex/60)))
        return arr

@app.get('/getDetails') #if admin is set to true the admin can see the details, doctors can see the details but the patient does not see it 
def getDetailsofAppointments(doc_id:int, app_id:int,admin:str=""):
    df = pd.read_sql("SELECT * from appointments where app_id={}".format(app_id),connection)
    cur.execute("SELECT Doctor_name from doc_info where docID={}".format(doc_id))
    x=cur.fetchval()
    print(df)
    for index,i in df.iterrows():
        if i['Doctor_name']==x or admin=="true":
            if i['App_time']<=60:
              return{"Dr. {} | {} | {} mins".format(i['Doctor_name'],i['patient_ID'],i['App_time'])}
            else:
             return{"Dr. {} | {} | {} hours".format(i['Doctor_name'],i['patient_ID'],i['App_time'])}
        else:
            return{"You have no authority to view the details"}


@app.get('/doctors/highest/{size}')
def HighestNoofPatients(size:int):
    df = pd.read_sql("SELECT * FROM appointments", connection)
    timex=0
    arr = [[0]*2]*df['Doctor_name'].unique().size
    for ii,i in enumerate(df['Doctor_name'].unique()):
        for index, j in df.iterrows():
            timex=timex+j['App_time']
            indexes=index+1 
        arr[ii][0]=i
        arr[ii][1]=indexes
    print(arr)
    arr.sort(key=lambda x:x[1])
    return arr


@app.get('/doctors/highest6')
def HighestNoofPatients():
    df = pd.read_sql("SELECT * FROM appointments", connection)
    timex=0
    cntr=0
    arr = [[0]*2]*df['Doctor_name'].unique().size
    for ii,i in enumerate(df['Doctor_name'].unique()):
        for index, j in df.iterrows():
            timex=timex+j['App_time']
            indexes=index+1 
        if indexes>=6:
            cntr=cntr+1  
            arr[ii][0]=i
            arr[ii][1]=indexes
    arr.sort(key=lambda x:x[1])
    if cntr==0:
        return{"No doctor has higher than 6 appointments"}
    else:
        return arr
