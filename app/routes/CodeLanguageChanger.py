from flask import Blueprint,request, jsonify
from dotenv import load_dotenv
from google import generativeai as genai
import os
import re

load_dotenv()

clc_bp = Blueprint('clc_bp', __name__)



@clc_bp.route('/code-change-request', methods=['POST'])
def get_ChangeCode(): 
    if(not request.is_json):
        return jsonify({'error', 'Request must be in json format'}), 400
    data = request.get_json()
    prompt = f'''
        Convert the following code to {data['Language']}, maintaining equivalent functionality. Provide only the {data['Language']} code, without any additional text or explanations. Ensure the code is self-contained and includes all necessary imports, Return only the code — no markdown formatting or explanations..
        Here's the Code : 
        {data['Code']}
    '''
    genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
    model = genai.GenerativeModel("gemini-2.0-flash")
    ChangedCode = model.generate_content(prompt).text
    cleanChangedCode = strip_code_markdowns(changed_code=ChangedCode)

    return jsonify({
        'status':'success',
        'message':'Recieved successfully',
        'ChangedCode':cleanChangedCode
    }),200

@clc_bp.route('/code-summarization-request', methods=['POST'])
def getSummarizedVersionOfCode():
    if(not request.is_json):
        return jsonify({'error', 'Request must in json format'}), 400
    data = request.get_json()
    prompt = f'''
        Summarize and optimize the following {data['Language']} code snippet. Provide only the optimized and concise version of the code. Do not include explanations, comments, markdown formatting, or additional text. Ensure all necessary imports are included and functionality remains equivalent.
        Code:
        {data['CurrentActiveCode']}
    '''
    genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
    model = genai.GenerativeModel("gemini-2.0-flash")
    summarizedCode = model.generate_content(prompt).text
    cleanSummaizedCode = strip_code_markdowns(changed_code=summarizedCode)

    return jsonify({
        'status':'success',
        'message':'Summarized Successfully',
        'summarizedCode':cleanSummaizedCode
    }),200

def strip_code_markdowns(changed_code:str):
    return re.sub(r"```[\s\S]*?\n([\s\S]*?)```", r"\1", changed_code)