import streamlit as st
from person_crud_form import person_crud_form
from team_crud_form import team_crud_form
from department_crud_form import department_crud_form
from project_crud_form import add_project_form, edit_project_form


def display_manage_resources_tab():
    st.subheader("Resource Management")
    person_crud_form()
    team_crud_form()
    department_crud_form()


def display_manage_projects_tab():
    st.subheader("Project Management")
    add_project_form()
    edit_project_form()
