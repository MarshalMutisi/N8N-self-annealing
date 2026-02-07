# N8N Self-Annealing System (HEAS)

**HEAS (Healing & Error Analysis System)** is a robust monitoring and self-healing solution for n8n workflows. It combines a monitoring backend, an interactive dashboard, and an Agentic AI Healer to detect, analyze, and automatically fix workflow errors.

## 🚀 Features

*   **Real-time Monitoring**: Tracks n8n workflow executions and captures errors as they happen.
*   **Agentic AI Healer**: Powered by Google Gemini, this agent analyzes error logs and broken workflow JSON to propose and apply fixes automatically.
*   **Interactive Dashboard**: A Next.js-based frontend to view system status, active repairs, and historical error data.
*   **FastAPI Backend**: Orchestrates component communication and manages the healing lifecycle.
*   **Self-Annealing**: The system learns from errors to improve stability over time.

## 📂 Project Structure

*   `dashboard_next/`: Next.js frontend application.
*   `execution/`: Python scripts for backend logic, API, and the AI healer agent.
    *   `ai_healer.py`: Core logic for interacting with Gemini API.
    *   `api.py`: FastAPI application server.
    *   `agentic_healer.py`: Independent healer module.
*   `directives/`: Operational directives and SOPs for the agentic system.
*   `run_workflow.py`: Master entry point to start all services (Backend, Frontend, Healer).

## 🛠️ Prerequisites

*   **Python 3.8+**
*   **Node.js & npm**
*   **n8n instance** (Local or Cloud)
*   **Google Gemini API Key** (for AI healing capabilities)

## 📦 Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/MarshalMutisi/N8N-self-annealing.git
    cd N8N-self-annealing
    ```

2.  **Install Python Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Install Frontend Dependencies:**
    ```bash
    cd dashboard_next
    npm install
    cd ..
    ```

4.  **Environment Setup:**
    Create a `.env` file in the root directory (based on `.env.example` if available) and add your credentials:
    ```env
    GEMINI_API_KEY=your_gemini_api_key_here
    N8N_API_KEY=your_n8n_api_key
    N8N_BASE_URL= your_n8n_url
    ```

## ▶️ Usage

To start the entire system (Backend, Frontend, and Healer agents), simply run:

```bash
python run_workflow.py
```

This will launch:
*   **FastAPI Backend**: `http://localhost:8000`
*   **Next.js Dashboard**: `http://localhost:3000`

## 🤝 Contributing

Contributions are welcome! Please open an issue or submit a pull request for any improvements or bug fixes.

## 📄 License

[MIT License](LICENSE)
