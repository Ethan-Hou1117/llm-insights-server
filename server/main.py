from typing import Union, Optional
from fastapi import FastAPI, HTTPException
from openai import OpenAI
from supabase import create_client, Client
import os
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import json
from dotenv import load_dotenv

load_dotenv()



class QueryModel(BaseModel):
    query: str
    options: Optional[dict] = None


SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')

print("STUFF", os.environ.get('OPENAI_API_KEY'))

openai = OpenAI()

app = FastAPI()


supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# Define a list of origins that should be allowed to make cross-origin requests
# You can use ["*"] to allow all origins, but it's recommended to be more specific for security reasons
origins = [
   "*"
]

# Add CORSMiddleware to the application instance
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # List of origins that are allowed to make requests
    allow_credentials=True,  # Allow cookies to be included in cross-origin HTTP requests
    allow_methods=["*"],  # Allow all methods (GET, POST, PUT, etc.)
    allow_headers=["*"],  # Allow all headers
)

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.post("/llm")
async def post_llm(body: QueryModel):
    """
    Accepts a string, classifies its intent using OpenAI, and inserts the data into Supabase.
    """
    print("BODY", body)
    query = body.query  # Extract the query from the request body
    options = None
    if (body.options):
        options = body.options

    

    print("QUERY", query)

    try:
        # Classify the intent of the query using OpenAI
        response = openai.chat.completions.create(
          model="gpt-4",  # Adjust the engine as necessary
          messages=[{"role": "user", "content": f'What is the intent of this query: \"{query}\"?. Return format of {{"intent": ..., "detail": ...}}, where intent is one of SearchCode, Debug, Summarize, NavigateDependencies, FindUsageExamples, ObtainHighLevelUnderstanding, Other'}],
          temperature=0.7,
          max_tokens=60,
          top_p=1.0,
          frequency_penalty=0.0,
          presence_penalty=0.0
        )
        content = json.loads(response.choices[0].message.content)
        print("CONTENT", content)
        detail = content.get('detail')
        intent = content.get('intent')

        print("GOT HERE")

        # Insert the query and its classified intent into Supabase
        supabase.table("messages").insert({
            "content": query,
            "intent": intent,
            "detail": detail,
            "options": options,
        }).execute()

        print("GOT HERE")
        # Check if insert was successful, based on your Supabase table setup

        return {"query": query, "intent": intent, "inserted": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/llm")
def llm_data():
    response, count = supabase.table("messages").select('*').execute()
    data = response[1]
    print("DATA", response)
    labels = set([d['intent'] for d in data])
    counts = [len([d for d in data if d['intent'] == label]) for label in labels]



    return {'messages': response[1], 'labels': labels, 'counts': counts}