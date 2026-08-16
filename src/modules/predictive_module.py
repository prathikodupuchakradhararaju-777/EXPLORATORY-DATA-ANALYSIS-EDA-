"""
Module 5 Backward Compatibility Proxy
Redirects calls from predictive_module to preventive_module.
"""
from modules.preventive_module import render_preventive_module_page

def render_predictive_module_page(df):
    """Legacy redirect to render_preventive_module_page"""
    return render_preventive_module_page(df)
