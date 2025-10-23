# Optimisable: AI-Powered Workforce Scheduler

**Optimisable** is an intelligent workforce optimisation prototype that combines  
mathematical optimisation (**Gurobi**), an interactive web interface (**Streamlit**),  
and AI-assisted configuration (**OpenAI GPT-4o-mini**) into a single application.

Users can:
- Define daily staffing requirements and staff constraints.  
- Run optimisation to generate a cost-minimised schedule.  
- Chat naturally with the AI assistant to update parameters  
  (for example: “Set Staff 3 cost to 90” or “Reduce Friday staff requirement by 1”).  
  The system automatically re-solves and refreshes the results in real time.

---

## Key Technologies
- **Python 3.11**
- **Gurobi Optimizer** for linear and mixed-integer programming
- **Streamlit** for browser-based interactivity
- **OpenAI GPT-4o-mini API** for natural-language command parsing
- **python-dotenv** for secure API-key management

---

## Features
- Dynamic demand and staff configuration
- Cost-minimised weekly scheduling
- Natural-language control through an integrated chatbot
- Instant re-optimisation and interface refresh
- Graceful error handling for invalid or infeasible models

## Project Structure
```
Optimisable/
├─ app.py               # Main Streamlit application
├─ optimiser.py         # Gurobi optimisation logic
├─ .env                 # Stores API keys (not tracked in Git)
├─ requirements.txt     # Dependencies list
├─ .gitignore           # Git exclusion rules
└─ README.md            # Project overview
```
---

## Setup Instructions

### 1. Clone the repository
```
git clone https://github.com/lokhanglee/Optimisable.git
cd Optimisable
```

### 2. Create and activate a virtual environment
```
python -m venv env
env\\Scripts\\activate        # on Windows
source env/bin/activate     # on macOS/Linux
```

### 3. Install dependencies
```
pip install -r requirements.txt
```

### 4. Set up your environment variables  
Create a .env file in the project root and add:
```
OPENAI_API_KEY=your_openai_api_key_here
```

### 5. Run the app
```
streamlit run app.py
```

The application will open in your browser at http://localhost:8501.

---

## Example Commands for the AI Assistant
| Command | Effect |
|----------|---------|
| Set Staff 3 cost to 90 | Updates Staff 3’s daily cost and re-optimises |
| Reduce Friday staff requirement by 1 | Lowers Friday demand and re-optimises |
| Set Sunday staff requirement to 4 | Updates Sunday’s required staff count |
| Who works on Wednesday? | Returns staff scheduled that day |

---

## License
This project is provided for learning and demonstration purposes only.  
It may not be used for commercial applications without permission.

---

## Author
Developed by **Louis Lee**  
[GitHub Profile](https://github.com/lokhanglee)