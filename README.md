# 📊 AI Report Creator by Darsh Tayal

Welcome to the **AI Report Creator**, a fully automated research agent that generates professional market research reports in PDF format — powered by LangGraph, Groq LLMs, and real-time web search.

Built by **Darsh Tayal**, this project showcases how stateful AI pipelines can be used to automate complex research tasks end-to-end.

---

## 🚀 What This App Does

1. **Takes a Research Topic** (e.g. "Indian AI Mission")
2. **Accepts a Company & Objective** (e.g. "Microsoft", "To decide if we should enter this space")
3. **Plans Subsections Using LLMs**
4. **Searches the Internet** for current, reliable sources
5. **Summarizes Using Groq's LLMs**
6. **Compiles a Multi-Section Report**
7. **Exports a Ready-to-Use PDF**

---

## 🧠 Powered By

- ⚙️ [LangGraph](https://github.com/langchain-ai/langgraph) – to manage the report-building state machine
- 🧠 [Groq](https://groq.com/) LLMs – lightning-fast inference from Llama 3 & Llama 4 models
- 🌐 DuckDuckGo Search API – real-time information gathering
- 🧾 ReportLab – PDF report generation
- 🤖 Gradio – interactive front-end for user input

---

## 🔐 How to Use

### 1. Get a FREE Groq API Key  
Go to 👉 https://console.groq.com/keys

### 2. Paste Your API Key  
When prompted in the app, paste your Groq API key to activate LLM access.

### 3. Enter Your Research Info  
- **Title**: Your topic of research  
- **Company**: Target organization  
- **Objective**: Why you need this report

### 4. Sit Back and Wait ⏳  
Your report will be ready in **10–15 minutes** and available for **download as a PDF**.

---

## 📌 Known Limitations

- Generation may take 10–15 minutes depending on internet response time and LLM processing.
- Some reports may have repetition or verbose sections — under active optimization.
- Works best with topics that have **rich online content**.

---

## ✨ Contact me

- Please e-mail me at darshtayal8@gmail.com

---


## 🛠️ How It Works (For Developers)

The entire system is managed as a LangGraph state machine:

```

```markdown
Start
  ↓
Planner: Create Section Plan
  ↓
Assigner: Pick One Subsection
  ↓
Subsection Generator: Search, Summarize, Clean
  ↓
(If sections left → back to Assigner)
  ↓
Compiler: Build Final Report
  ↓
Output PDF
