# N8N Self-Annealing System (HEAS)

**HEAS (Healing & Error Analysis System)** is a robust monitoring and self-healing solution for n8n workflows. It combines a monitoring backend, an interactive dashboard, and an Agentic AI Healer to detect, analyze, and automatically fix workflow errors.

## 🚀 Features

*   **Real-time Monitoring**: Tracks n8n workflow executions and captures errors as they happen.
*   **Agentic AI Healer**: Powered by Google Gemini, this agent analyzes error logs and broken workflow JSON to propose and apply fixes automatically.
*   **Two-Way Architecture**: Support for both a human-friendly **Dashboard** and an AI-friendly **MCP Server**.
*   **MCP Server Integration**: Exposes healing tools directly to AI clients like Claude Desktop, Cursor, or any MCP-compatible agent.
*   **Interactive Dashboard**: A Next.js-based frontend to view system status, active repairs, and historical error data.
*   **Self-Annealing**: The system learns from errors to improve stability over time.

## 📂 Project Structure

*   `dashboard_next/`: Next.js frontend application.
*   `execution/`: Python scripts for backend logic, API, and the AI healer agent.
*     - `core_healer.py`: **[Shared Brain]** Unified logic used by both the Dashboard and MCP Server.
*     - `mcp_server.py`: **[AI Bridge]** The Model Context Protocol (MCP) implementation.
*     - `ai_healer.py`: Core logic for interacting with Gemini API.
*     - `api.py`: FastAPI application server.
*     - `agentic_healer.py`: Autonomous background monitor and healer.
*   `run_workflow.py`: Master entry point to start all services.

## 🛠️ Prerequisites

*   **Python 3.10+**
*   **Node.js & npm**
*   **n8n instance** (Local or Cloud)
*   **Google Gemini API Key**

## 📦 Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/MarshalMutisi/N8N-self-annealing.git
    cd N8N-self-annealing
    ```

2.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Environment Setup:** Create a `.env` file:
    ```env
    GEMINI_API_KEY=your_key
    N8N_API_URL=your_n8n_url
    N8N_API_KEY=your_n8n_key
    ```

## ▶️ Usage

### 1. The Standard Way (Dashboard)
To start the Dashboard, Backend, and Background Monitor:
```bash
python run_workflow.py
```
Visit `http://localhost:3000` to see the results.

### 2. The AI Power-User Way (MCP)
To connect this system to **Claude Desktop** or **Cursor**, add the following to your MCP configuration:
```json
{
  "command": "python",
  "args": ["c:/absolute/path/to/execution/mcp_server.py"]
}
```
For more details, see [TESTING_MCP.md](./TESTING_MCP.md).

## 📊 How It Works
For a deep dive into the "Two-Way" architecture and how the AI interacts with N8N, see [HOW_IT_WORKS.md](./HOW_IT_WORKS.md).
