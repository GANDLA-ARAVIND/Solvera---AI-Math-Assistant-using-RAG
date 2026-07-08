# 🧠 Solvera – AI Math Assistant using RAG

An intelligent AI-powered math assistant that leverages **Retrieval-Augmented Generation (RAG)** to solve mathematical queries with contextual understanding and step-by-step explanations.

---

## 🚀 Overview

Solvera is designed to help users solve mathematical problems by combining the power of:

* 📚 Knowledge retrieval
* 🤖 Large Language Models (LLMs)
* 🔍 Context-aware reasoning

Instead of relying only on a language model, Solvera retrieves relevant mathematical context and generates accurate, explainable solutions.

---

## 🎯 Features

* ✅ Solve mathematical problems using natural language queries
* ✅ Step-by-step explanations for better understanding
* ✅ RAG-based architecture for improved accuracy
* ✅ Context-aware responses using retrieved knowledge
* ✅ Clean and interactive user interface *(if frontend included)*

---

## 🏗️ Architecture

The system follows a **Retrieval-Augmented Generation (RAG)** pipeline:

1. User inputs a math query
2. Query is processed and embedded
3. Relevant documents are retrieved from the knowledge base
4. Retrieved context is passed to the LLM
5. LLM generates the final answer with explanation

---

## 🛠️ Tech Stack

* **Programming Language:** Python
* **Frameworks/Libraries:**

  * LangChain / LlamaIndex *(if used)*
  * OpenAI API / Hugging Face
  * FAISS / ChromaDB (for vector storage)
* **Frontend:** HTML, CSS, JavaScript *(if applicable)*
* **Backend:** Flask / FastAPI *(if applicable)*

---

## 📂 Project Structure

```
Solvera/
│
├── backend/
├── frontend/
├── models/
├── data/
├── utils/
├── app.py / main.py
├── requirements.txt
└── README.md
```

---

## ⚙️ Installation & Setup

### 1️⃣ Clone the repository

```bash
git clone https://github.com/gopireddy99/Solvera---AI-Math-Assistant-using-RAG.git
cd Solvera---AI-Math-Assistant-using-RAG
```

### 2️⃣ Create virtual environment

```bash
python -m venv .venv
source .venv/bin/activate   # Linux/Mac
.venv\Scripts\activate      # Windows
```

### 3️⃣ Install dependencies

```bash
pip install -r requirements.txt
```

### 4️⃣ Set environment variables

Create a `.env` file and add:

```
OPENAI_API_KEY=your_api_key_here
```

### 5️⃣ Run the application

```bash
python app.py
```

---

## 💡 Example Queries

* “Solve quadratic equation x² + 5x + 6 = 0”
* “Explain integration of sin(x)”
* “What is the derivative of x³?”

---

## 📈 Future Enhancements

* 🔹 Support for advanced math (calculus, linear algebra)
* 🔹 Voice-based interaction
* 🔹 Graph visualization for equations
* 🔹 Multi-language support

---

## 🤝 Contributing

Contributions are welcome! Feel free to fork the repository and submit pull requests.

---

## 📜 License

This project is licensed under the MIT License.

---

## 👨‍💻 Authors

**SRI RAM YADAV**
**ARAVIND GANDLA**
**Nitish Kumar Reddy**
**J.SAI RAM**

B.Tech CSE (AI & ML)
Malla Reddy University

---

## ⭐ Acknowledgements

* OpenAI / Hugging Face
* LangChain / Vector DB tools
* Research on Retrieval-Augmented Generation (RAG)

---
