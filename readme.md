# Resource Management App

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)

A comprehensive resource management application built with Streamlit. This app allows you to manage people, teams, departments, and projects, visualize resource allocation, and track utilization metrics.

---

## Features

- **Dashboard**: View a summary of resources and projects, including visualizations like timelines and pie charts.
- **Resource Management**: Add, edit, or delete people, teams, and departments. View consolidated resources with search, sort, and filter options.
- **Project Management**: Manage projects, including assigning resources, tracking budgets, and filtering projects by various criteria.
- **Workload Distribution**: Visualize resource allocation across projects using Gantt charts and matrix views.
- **Performance Metrics**: Track resource utilization, overallocation, and underutilization with detailed visualizations.
- **Availability Forecast**: Plan resource capacity and availability with advanced filtering options.
- **Resource Calendar**: View resource schedules and assignments in a calendar format with daily, weekly, and monthly views.
- **Data Tools**: Import and export data in JSON format for easy data management.
- **Configuration**: Customize settings such as colors, currency, and daily cost limits.

---

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/niksavis/resource-management.git
   cd resource-management
   ```

2. Create a virtual environment and activate it (Windows):

   ```bash
   python -m venv .venv
   .venv\Scripts\activate # On macOS and Linux use `source .venv/bin/activate`
   ```

3. Install the required dependencies:

   ```bash
   python -m pip install -r requirements.txt
   ```

---

## Running the Application

Start the application with:

```bash
streamlit run main.py
```

The application will open in your default web browser at `http://localhost:8501`.

---

## Data Structure

The application stores data in a JSON format with the following structure:

- People (resources with skills, costs, and work schedules)
- Teams (groups of people)
- Departments (organizational units containing teams and people)
- Projects (with timelines, allocated resources, and priority)

---

## Usage Guide

1. **Initial Setup**: Configure your currency and display settings in the Configuration tab.
2. **Add Resources**: Create people, teams, and departments in the Resource Management tab.
3. **Create Projects**: Set up projects and allocate resources in the Project Management tab.
4. **Analyze Workload**: Use the analytics tabs to visualize workload distribution and resource utilization.
5. **Plan Capacity**: Use the Availability Forecast to identify resource availability for future planning.

---

## License

This project is licensed under the MIT License - see the LICENSE file for details.
