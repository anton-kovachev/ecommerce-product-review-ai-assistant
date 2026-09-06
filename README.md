# Sidekick AI Agent

Sidekick is an advanced AI-powered assistant built with LangGraph and LangChain, designed to handle complex product research and review evaluation workflows.

## 🚀 Overview

Sidekick acts as a specialized agent that can classify user intent, perform deep product research, evaluate product reviews against specific success criteria, and handle user feedback with sentiment analysis. It uses a state-machine architecture (LangGraph) to ensure reliable and predictable transitions between different research and evaluation phases.

## 🎯 Business Goal

The goal of Sidekick is to automate the quality assurance and research process for product reviews. By automating the evaluation of reviews against a set of success criteria, it ensures that only high-quality, compliant content is produced, while providing a seamless loop for rewriting and improving rejected reviews.

## 🛠 Technologies Used

- **Python**: Core language.
- **LangGraph**: For orchestrating the agentic workflow as a state machine.
- **LangChain**: For LLM integration and tool management.
- **OpenRouter**: To access a variety of high-performance LLMs.
- **Pydantic**: For structured data validation and state management.
- **DeepAgents**: For creating specialized deep-research agents.

## 📋 Key Features

- **Intent Classification**: Automatically determines if a user message is a product query or feedback.
- **Deep Product Research**: Leverages specialized research agents to gather comprehensive product information.
- **Automated Review Evaluation**: Evaluates generated reviews against strict success criteria and provides detailed reasoning for rejections.
- **Iterative Improvement**: Automatically triggers a rewrite loop if a review is rejected, passing the rejection reasons back to the researcher.
- **Sentiment Analysis**: Analyzes user feedback to improve the interaction experience.

## ⚙️ Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd new_sidekick
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment**:
   Copy the example environment file and add your API keys:
   ```bash
   cp .env.example .env
   ```

4. **Run the Agent**:
   ```bash
   python sidekick.py
   ```

## 🗺️ Workflow Architecture

The agent follows a structured graph:
`START` $\rightarrow$ `Message Type Analysis` $\rightarrow$ (`Product Query` $\rightarrow$ `Evaluation` $\rightarrow$ `Product Query` (if rejected)) OR (`Feedback` $\rightarrow$ `END`) OR (`Unknown` $\rightarrow$ `END`).

## 📄 License

This project is licensed under the MIT License.
