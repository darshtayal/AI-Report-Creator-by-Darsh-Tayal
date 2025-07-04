# -*- coding: utf-8 -*-

# imports
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_community.document_loaders import WebBaseLoader
from langchain_core.messages import HumanMessage
import os
from dotenv import load_dotenv
from typing import List, Annotated
from typing_extensions import TypedDict
import operator
from langchain_community.tools import DuckDuckGoSearchResults
from langgraph.constants import Send
import re
from IPython.display import display, Image, Markdown
import time
import gradio as gr
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import tempfile

# define the state of the gragh
class State(TypedDict):
    report_title: str
    report_reason: str
    company_name: str
    report_plan: list
    final_report: str
    no_of_subsections: int
    current_title: str
    current_description: str
    completed_sections: Annotated[List, operator.add]

# define the other classes for llms to give structured outputs
class Section(BaseModel):
    title: str = Field(description='This is the title of the subsection')
    description: str = Field(description="This is short summary of the section")
class Sections(BaseModel):
    plan: List[Section]
class Creator(BaseModel):
    questions: List[str] = Field(description="Exactly 2 to 3 questions for researching the subtopic.")

# function to invoke a general llm
def invoke_llm(message):
    llm = ChatGroq(model='llama-3.1-8b-instant')
    response = llm.invoke([HumanMessage(content=message)])
    return response

# function to invoke a large parameter llm for complex and lengthy tasks
def invoke_big_llm(message):
    llm = ChatGroq(model='meta-llama/llama-4-scout-17b-16e-instruct')
    response = llm.invoke([HumanMessage(content=message)])
    return response

# function to invoke the planner llm for report planning tasks
def plannerllm(message):
    llm = ChatGroq(model='llama-3.1-8b-instant')
    so_llm = llm.with_structured_output(Sections)
    response = so_llm.invoke([HumanMessage(content=message)])
    return response

# function to invoke the creator llm for question creation task
def creator_llm(message):
    llm = ChatGroq(model='llama-3.1-8b-instant')
    crea_llm = llm.with_structured_output(Creator)
    response = crea_llm.invoke([HumanMessage(content=message)])
    return response

# initializing web search
search = DuckDuckGoSearchResults(output_format="list")

# This is the 1st Node for the graph. Here we plan the full report.
def planner(state: State):    
    prompt = f"""
You are an expert report planner. Your job is to produce a JSON list of section objects for a report.

Return a list of dictionaries in this format:
[
  {{
    "title": "<title>",
    "description": "<short summary>"
  }},
  ...
]

Do NOT wrap in markdown. Do NOT include any explanation — just return the list directly.

Create a report plan for the company "{state['company_name']}", titled "{state['report_title']}", for the purpose "{state['report_reason']}".
"""

    res = plannerllm(prompt)
    return {'report_plan': res.plan}

# define a function to clean the data recieved from the web
def clean_web_text(text: str) -> str:
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'<(script|style).*?>.*?</\1>', '', text, flags=re.DOTALL)
    text = re.sub(r'\n+', '\n', text)
    text = re.sub(r'\s{2,}', ' ', text)
    keywords = ['Privacy Policy', 'Terms of Service', 'Subscribe', 'Contact us', '©']
    for kw in keywords:
        text = text.replace(kw, '')
    text = text.strip()
    return text

# This is the Node which generates each subsection for the report.
def subsection_generator(state:State):
    prompt = f"We are creating a subsection of the report on the topic {state['report_title']}. The goal of our report is to make a decision about {state['report_reason']}. We have to search the internet to gather the information about the subtopic '{state['current_title']}' which have a description '{state['current_description']}'. So design 2-3 strong questions and sentences so that we can gather detailed information about it."
    res = creator_llm(prompt)
    final_text = []
    for question in res.questions:
        link_list = []
        text = []
        question_info = ""
        time.sleep(60) # Pause 60s between queries to avoid rate limiting (DuckDuckGo and GROQ API)
        info = search.invoke(question)
        for sub in info:
            link_list.append(sub['link'])
        for link in link_list:
            loader = WebBaseLoader(link)
            try:
                docs = loader.load()
            except Exception as e:
                continue 
            docs = clean_web_text(docs[0].page_content)
            avg_tokens = 1.4 * len(docs.split(" "))
            if avg_tokens > 5940:
                pass
            else:
                prompt = f"Please summarize the following website text in 1 paragraph of important information. Ignore all the stuff that's irrelevent. Include only the important facts and figures. Reply only with the summary and nothing else, not even here's the summary and all. Here's the text: {docs}"
                try:          
                    res = invoke_llm(prompt)
                    text.append(res.content)
                except:
                    continue
                finally:
                     question_info = '\n'.join(text)
                     link_prompt = f"Please summarize the following text into 2-3 paragraphs that contains all the facts and figures. Reply only with the summary and nothing else, not even here's the summary and all. Here's the text: {question_info}"
                     response = invoke_big_llm(link_prompt).content
                     final_text.append(response)
       
    all_info = '\n'.join(final_text)
    max_token_limit = 10500 
    token_estimate = 1.4 * len(all_info.split())
    if token_estimate > max_token_limit:
          trimmed_text = []
          total_tokens = 0
          for block in final_text:
              block_tokens = 1.4 * len(block.split())
              if total_tokens + block_tokens < max_token_limit:
                  trimmed_text.append(block)
                  total_tokens += block_tokens
              else:
                  break
    else:
        trimmed_text = final_text        
    all_info = '\n'.join(trimmed_text)
    final_subsection_prompt = f"Please summarize this text into 5-6 paragraphs. Return only the summary. Avoid any extra explanation or formatting:\n{all_info}"
    final_subsection = invoke_big_llm(final_subsection_prompt)
    return {'completed_sections': [final_subsection], 'no_of_subsections':state['no_of_subsections']+1}

# This node will take subsections from the planner and assign them to the subsection generator sequencially
def assigner(state:State):
    planner_list = state['report_plan']
    target_id = state['no_of_subsections']
    target_subsection = planner_list[target_id]
    cur_title = target_subsection.title
    cur_description = target_subsection.description
    return {'current_title': cur_title, 'current_description': cur_description} 

# This node will be used by langgraph to redirect the flow back to subsection generator from assigner and visa versa. Also, when the full report will be generated, it will redirect the flow towards the final node, compiler.
def smart_assigner(state:State):
    rp_len = len(state['report_plan'])
    cur_len = state['no_of_subsections']
    if cur_len < rp_len:
        return 'assigner'
    else:
        return 'compiler'

# This node will take in all the generated subsections in the form of list and compile them into a single report.
def compiler(state:State):
    title_list = []
    content_list = []
    for plan in state['report_plan']:
        title_list.append(plan.title)
    content_list.append(f"# {state['report_title']}")
    for index,info in enumerate(state['completed_sections']):
        content_list.append(f"## {title_list[index]}")
        content_list.append(f"**{info.content}**")
    final_rep = "\n\n --- \n\n".join(content_list)
    return {'final_report':final_rep} 

# And here we start building the graph!
builder = StateGraph(State)

# We first add all the nessasary nodes
builder.add_node('planner', planner)
builder.add_node('subsection_generator', subsection_generator)
builder.add_node('compiler', compiler)
builder.add_node("assigner", assigner)

# Connect nodes to define the flow of report generation using LangGraph 
builder.add_edge(START, 'planner')
builder.add_edge('planner','assigner')
builder.add_edge('assigner','subsection_generator')
builder.add_conditional_edges('subsection_generator', smart_assigner,
                             {'assigner': 'assigner', 'compiler': 'compiler'})
builder.add_edge('compiler', END)

# We then compile the graph
graph = builder.compile()

# We create functions for gradio, this is initializer to check the API key
def initializer(api_key):
    os.environ['GROQ_API_KEY'] = api_key
    llm_tester = ChatGroq(model="gemma2-9b-it")
    try:
        llm_tester.invoke('hey')
    except:
        return gr.update(visible=True), gr.update(visible=False), gr.update(visible=True)
    return gr.update(visible=False), gr.update(visible=True), gr.update(visible=False)

# This function will call the graph 
def get_markdown_text(rp_title, company, rp_reason):
    mess = {'report_title':rp_title, 'company_name':company, 'report_reason':rp_reason, 'no_of_subsections':0}
    res = graph.invoke(mess)
    return res['final_report'].split('\n')

# This function will convert the report into a PDF
def markdown_to_pdf(rp_title, company, rp_reason):
    yield gr.update(visible=False), gr.update(visible=True), gr.update(visible=False), None, gr.update(visible=False)
    try:
        markdown_text = get_markdown_text(rp_title, company, rp_reason)
    except:
        yield gr.update(visible=False), gr.update(visible=True), "❗ Internal Issue Error. Please try again later. Inconvenience is regretted.", None, gr.update(visible=True)
        return  
    temp_dir = tempfile.mkdtemp()
    safe_title = re.sub(r'[^a-zA-Z0-9_\-]', '_', rp_title.strip())[:30] or "report"
    filename = f"{safe_title}.pdf"
    pdf_path = os.path.join(temp_dir, filename)
    c = canvas.Canvas(pdf_path, pagesize=letter)
    c.drawString(72, 750, "Generated from Markdown:")
    text = c.beginText(72, 720)
    for line in markdown_text:
        text.textLine(line)
    c.drawText(text)
    c.save()
    yield gr.update(visible=True), gr.update(visible=False), f"✅ Your report '{filename}' is ready! Thank you! Send feedback to darshtayal8@gmail.com.", pdf_path, gr.update(visible=True)

# And here we built the gradio UI!
with gr.Blocks() as ui:
    api_key_valid = gr.State(value=True)
    with gr.Column(visible=True) as extractor:
        gr.Markdown('# Welcome To My Market Researcher Project! 📈')
        gr.Markdown("## My name is Darsh and I'm so glad to see you here! 😃")
        gr.Markdown('### But wait! In order to get started, we need the GROQ API KEY (It's free!)🤯:")
        api_error_msg = gr.Markdown("# ⚠️ Your API key doesn't work. Please Try again.", visible=False)
        key = gr.Textbox(label = "Please enter your GROQ API key here: ", lines=2)
        gr.Markdown("## If you don't have a GROQ API KEY then please go to: https://console.groq.com/keys")
        gr.Markdown("""\
**Here's a more detailed breakdown:**  
**Sign up for a Groq Cloud account:** If you don't already have one, visit the Groq Cloud website and sign up for a new account.  
**Log in:** Once you have an account, log in to your Groq Cloud account.  
**Navigate to API Keys:** Locate and click on the "API Keys" section in the left-hand navigation panel.  
**Create a new API key:** Click the "Create API Key" button.  
**Name your API key:** Enter a descriptive name for your API key (e.g., "My Groq API Key"). This helps you identify its purpose later.  
**Submit:** Click the "Submit" button to generate the API key.  
**Copy and Securely Store:** The newly generated API key will be displayed. Copy it and paste it here! And yes You're done!.
""")
        submit = gr.Button("SUBMIT!")

    with gr.Column(visible=False) as creator:
            gr.Markdown("# Heyy You're all set! Let's goo! 🚀")
            gr.Markdown('## Please answer the following questions: ')
            gr.Markdown('### Please follow the format given in examples to extract best results.')
            title = gr.Textbox(label='Please Enter Your Reasearch Title (eg: Indian AI Mission):', lines=1)
            company = gr.Textbox(label="Please Enter Your Company's Name (eg: Microsoft): ", lines=1)
            reason = gr.Textbox(label="Please enter the objective for the report (eg: To find if we should enter this space):", lines=2)
            sub = gr.Button("Go!!!")
    with gr.Column(visible=False) as processing_page:
            gr.Markdown("# Your Reseach is being cooked 📝")
            gr.Markdown('## Note: Creating a comprehensive Research Paper may take 10-15 minutes (not more!) 🤯')
    with gr.Column(visible=False) as final_page:
            result = gr.Label()
            download_btn = gr.File(label="Download PDF")
    submit.click(fn=initializer, inputs=[key], outputs = [extractor, creator, api_error_msg])
    sub.click(fn = markdown_to_pdf, inputs=[title, company, reason], outputs=[creator, processing_page, result, download_btn, final_page])

# And boom! We launch the app. 
ui.launch()
