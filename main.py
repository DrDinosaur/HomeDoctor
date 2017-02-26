import urllib
import json
import os

from flask import Flask
from flask import request
from flask import make_response

import infermedica_api

from secrets import * #contains infermedica app id/key

#from google.appengine.api import urlfetch
#urlfetch.set_default_fetch_deadline(60)
import gae_fix

#import pyrebase
#firebase = pyrebase.initialize_app({
#    "apiKey": FIREBASE_API_KEY,
#    "authDomain": FIREBASE_AUTH_DOMAIN,
#    "databaseURL": FIREBASE_DB_URL,
#    "storageBucket": FIREBASE_STORAGE_BUCKET
#})

#db = firebase.database()

app = Flask(__name__)
app.config['DEBUG'] = True

infermedica_api.configure(app_id=INF_APP_ID, app_key=INF_APP_KEY)

sessionMap = {}

inf_api = infermedica_api.get_api()
conditions = inf_api.conditions_list()

@app.route('/webhook', methods=['POST'])
def webhook():
    req = request.get_json(silent=True, force=True)

    print("Request:")
    print(json.dumps(req, indent=4))

    res = processRequest(req)

    res = json.dumps(res, indent=4)
    print("Response:")
    print(res)
    r = make_response(res)
    r.headers['Content-Type'] = 'application/json'
    return r


def processRequest(req):
    print("Processing request")
    result = req.get("result")
    contexts = result.get("contexts")
    action = result.get("action")
    
    if action=="givesymptoms":
        return giveSymptoms(req)
    elif action=="followup":
        return followUp(req)
    return res


def finished(sessionId, diagnose_res):
    del sessionMap[sessionId]
    conditions = diagnose_res.get("conditions")
    if conditions is not None:
        if len(conditions) > 0:
            done = False
            out = []
            for condition in conditions:
                if condition.get("probability") > 0.5:
                    out.append(condition)
                    done = True
                    if len(out)==3:
                        break
            if len(out)==0:
                out.append(conditions[0])
            
            msg = "Ok... here is your diagnosis... "
            for x in range(len(out)):
                msg += condition_message(out[x], x!=0)
            #msg = "It looks like you have a chance of being diagnosed with: " + ",".join(out)
            msg += "Thank you for using home doctor. I hope you feel better."
            
            #save in db
            #reports = db.child("reports")
            #num_reports = len(reports.shallow().get())
            #age = sessionMap[sessionId]['age']
            #sex = sessionMap[sessionId]['sex']
            #report = {'age': age, 'sex': sex, 'conditions': conditions}
            #reports.set(str(num_reports), report)
            return {
                "speech": msg,
                "displayText": msg,
                "source": "apiai-homedoctor-webhook"
            }
    return {
        "speech": "I couldn't find anything that you are likely to be affected by. Please see a doctor if you aren't feeling well.",
        "displayText": "I couldn't find anything that you are likely to be affected by. Please see a doctor if you aren't feeling well.",
        "source": "apiai-homedoctor-webhook"
    }

def condition_message(condition, also):
    prob = "very low"
    if condition.get("probability") >= 0.9:
        prob = "extremely high"
    elif condition.get("probability") >= 0.7:
        prob = "high"
    elif condition.get("probability") >= 0.5:
        prob = "moderate"
    elif condition.get("probability") >= 0.1:
        prob = "low"

    rarity = "common"
    acuteness = "acute"
    severity = "mild"
    hint = "Please see a doctor."
    for cond in conditions:
        if cond.get("name")==condition.get("name"):
            if cond.get("extras"):
                if cond.get("extras").get("hint"):
                    hint = cond.get("extras").get("hint")
            rarity = cond.get("prevalence").replace("_"," ")
            acuteness = cond.get("acuteness").replace("_"," ")
            severity = cond.get("severity").replace("_"," ")
            break
    also = "also " if also else ""
    if rarity=="moderate":
        rarity = "moderate prevalence"
    return "There is "+also+"a "+prob+" chance of you having "+condition.get("name")+". This is a "+rarity+", "+acuteness+" condition of "+severity+" severity. " + hint+". "

def followUp(req):
    sessionId = req.get("sessionId")
    result = req.get("result")
    contexts = result.get("contexts")
    action = result.get("action")
    
    question_result = result.get("parameters").get("boolean_response")
    age = 38
    sex = "female"
    question_symptom_id = "NULL"
    symptoms = {}
    for context in contexts:
        if context.get("name")=="age_sex":
            parameters = context.get("parameters")
            age = parameters.get("age").get("amount")
            sex = parameters.get("sex")
        if context.get("name")=="question":
            parameters = context.get("parameters")
            question_symptom_id = parameters.get("id")
        if context.get("name")=="symptoms":
            symptoms = context.get("parameters")
    del symptoms["boolean_response.original"]
    del symptoms["boolean_response"]
    
    if question_result == "Yes":
        symptoms[question_symptom_id] = u'present'
    elif question_result == "No":
        symptoms[question_symptom_id] = u'absent'
    else:
        symptoms[question_symptom_id] = u'unknown'
    
    print(symptoms)
    
    # call diagnosis
    diagnose_res, question = doDiagnosis(sessionId, symptoms, sex, age)
    print(diagnose_res)
    
    if sessionMap[sessionId].get("num_asked")>8:
        return finished(sessionId, diagnose_res)
    else:
        sessionMap[sessionId]['num_asked'] += 1
    
    if question is not None:
        question_symptom_id = question.get("items")[0].get("id")
        return {
            "speech": "Ok. "+question.get("text"),
            "displayText": "Ok. "+question.get("text"),
            # "data": data,
            "contextOut": [{'name': "symptoms", 'lifespan': 20, 'parameters': symptoms}, {'name': "question", 'lifespan': 20, 'parameters': {"id": question_symptom_id}}],
            "source": "apiai-homedoctor-webhook"
        }
    else:
        return finished(sessionId, diagnose_res)

def doDiagnosis(sessionId, symptoms, sex, age):
    print("Starting diagnosis/question finding task...")
    while True:
        diagnose_req = infermedica_api.Diagnosis(sex=sex, age=age)
        diagnose_req.set_extras("ignore_groups", True)
        for symptom in symptoms:
            diagnose_req.add_symptom(symptom, symptoms[symptom])
        diagnose_res = inf_api.diagnosis(diagnose_req).to_dict()
        question = diagnose_res.get("question")
        if question is not None:
            text = question.get("text")
            seen_questions = sessionMap[sessionId].get("seen_questions")
            #if text in seen_questions:
            #    print("ERROR-- REPEATED QUESTION! EXITING!")
            #    return diagnose_res, None
            #else:
            #    seen_questions.append(text)
            print(question)
            if question.get("type")=="single":
                return diagnose_res, question
            else:
                print("ERROR-- question type not single?")
                items = question.get("items")
                for item in items:
                    question_symptom_id = item.get("id")
                    symptoms[question_symptom_id] = 'unknown'
                continue
        else:
            return diagnose_res, None

def giveSymptoms(req):
    sessionId = req.get("sessionId")
    sessionMap[sessionId] = {'seen_questions': [], 'num_asked': 0, 'age': 30, 'sex': "female"}
    result = req.get("result")
    contexts = result.get("contexts")
    action = result.get("action")
    age = 38
    sex = "female"
    for context in contexts:
        if context.get("name")=="age_sex":
            parameters = context.get("parameters")
            age = parameters.get("age").get("amount")
            sex = parameters.get("sex")
    sessionMap[sessionId]['age'] = age
    sessionMap[sessionId]['sex'] = sex
    symptomsQuery = result.get("resolvedQuery")
    #print("Query=", symptomsQuery)
    
    inf_response = inf_api.parse(symptomsQuery).to_dict()
    print(inf_response)
    
    mentions = inf_response.get("mentions")
    symptoms = {}
    for mention in mentions:
        symptoms[mention.get("id")] = mention.get("choice_id")
    
    # call diagnosis
    diagnose_res, question = doDiagnosis(sessionId, symptoms, sex, age)
    print(diagnose_res)
    if question is not None:
        question_symptom_id = question.get("items")[0].get("id")
        return {
            "speech": "Ok. "+question.get("text"),
            "displayText": "Ok. "+question.get("text"),
            # "data": data,
            "contextOut": [{'name': "symptoms", 'lifespan': 20, 'parameters': symptoms}, {'name': "question", 'lifespan': 20, 'parameters': {"id": question_symptom_id}}],
            "source": "apiai-homedoctor-webhook"
        }
    else:
        return finished(sessionId, diagnose_res)
@app.route('/')
def hello_world():
    return 'Hello World!'


if __name__ == '__main__':
    app.run()
