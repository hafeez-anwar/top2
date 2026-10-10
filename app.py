#!/usr/bin/env python
# coding: utf-8

# In[1]:


import streamlit as st
import pandas as pd
import re
import pycountry
import matplotlib.pyplot as plt

# 1. Set up the Web Page
st.set_page_config(page_title="Retraction Analysis", layout="wide")
st.title("🌍 Country Retraction Overlap Analysis")
st.markdown("Upload the Retraction Watch dataset and the Top-2% Authors dataset to generate independent rankings.")

# 2. Helper Functions (Same as your script)
def normalize_name(name_str):
    if pd.isna(name_str): return ""
    name_str = str(name_str).strip()
    if ',' in name_str:
        parts = name_str.split(',', 1)
        name_str = f"{parts[1].strip()} {parts[0].strip()}"
    return " ".join(re.sub(r'[^\w\s]', '', name_str.lower()).split())

def get_country_name(code):
    try:
        code = code.upper()
        country = pycountry.countries.get(alpha_3=code)
        if country: return country.name
        fallbacks = {'GER': 'Germany', 'ROM': 'Romania', 'UK': 'United Kingdom', 
                     'SCO': 'Scotland', 'WAL': 'Wales', 'ENG': 'England'}
        return fallbacks.get(code, None)
    except:
        return None

# 3. Sidebar UI for Inputs
with st.sidebar:
    st.header("Upload Data")
    rw_file = st.file_uploader("1. Retraction Watch CSV", type=['csv'])
    excel_file = st.file_uploader("2. Authors Dataset (Excel)", type=['xlsx'])
    
    st.header("Settings")
    min_retractions = st.slider("Minimum Matched Authors", min_value=1, max_value=20, value=5)
    top_n = st.slider("Top N Countries to Display", min_value=5, max_value=50, value=20)

# 4. Main App Logic
if rw_file and excel_file:
    with st.spinner("Processing data... this might take a minute."):
        df_rw = pd.read_csv(rw_file).dropna(subset=['Institution', 'Author'])
        df_excel = pd.read_excel(excel_file, sheet_name='Data').dropna(subset=['authfull', 'cntry'])
        df_excel['cntry'] = df_excel['cntry'].str.lower()
        
        total_global_retractions = len(df_rw)
        unique_codes = df_excel['cntry'].unique()
        results = []
        
        # Process logic (exact same as your script)
        for short_code in unique_codes:
            full_name = get_country_name(short_code)
            if not full_name: continue
                
            excel_subset = df_excel[df_excel['cntry'] == short_code]
            total_top2 = len(excel_subset)
            excel_authors_dict = {normalize_name(a): a.strip() for a in excel_subset['authfull'] if normalize_name(a)}
                    
            rw_subset = df_rw[df_rw['Institution'].str.contains(full_name, case=False, na=False)]
            total_country_retractions = len(rw_subset)
            rw_authors_dict = {}
            for author_field in rw_subset['Author']:
                authors = re.split(r';', str(author_field)) 
                if len(authors) == 1 and ',' in author_field: authors = re.split(r',', str(author_field))
                for author in authors:
                    norm = normalize_name(author)
                    if norm: rw_authors_dict[norm] = author.strip()
                        
            common_normalized = set(rw_authors_dict.keys()).intersection(set(excel_authors_dict.keys()))
            total_common = len(common_normalized)
            
            if total_common < min_retractions: continue
                
            results.append({
                'Country': full_name,
                'Code': short_code.upper(),
                'Top2_Authors': total_top2,
                'Total_Country_Retractions': total_country_retractions,
                'Overlap_Authors': total_common,
                'Author_Percentage': (total_common / total_top2) * 100 if total_top2 > 0 else 0,
                'Retraction_Percentage': (total_country_retractions / total_global_retractions) * 100 if total_global_retractions > 0 else 0
            })

        df_results = pd.DataFrame(results)
        
        if df_results.empty:
            st.warning(f"No countries met the minimum criteria of {min_retractions} retractions.")
        else:
            # Display Raw Data
            st.subheader("Raw Calculated Data")
            st.dataframe(df_results) # Creates an interactive, sortable table on the webpage
            
            # Allow users to download the results from the webpage
            csv = df_results.to_csv(index=False).encode('utf-8')
            st.download_button("Download Results as CSV", data=csv, file_name="retraction_results.csv", mime="text/csv")
            
            st.divider()
            
            # Subplots
            df_top_authors = df_results.sort_values(by='Author_Percentage', ascending=False).head(top_n)
            df_top_retractions = df_results.sort_values(by='Retraction_Percentage', ascending=False).head(top_n)
            
            df_plot_authors = df_top_authors.sort_values(by='Author_Percentage', ascending=True)
            df_plot_retractions = df_top_retractions.sort_values(by='Retraction_Percentage', ascending=True)
            
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 9))
            
            bars1 = ax1.barh(df_plot_authors['Country'], df_plot_authors['Author_Percentage'], color='steelblue', edgecolor='black')
            ax1.set_title(f'Top {top_n} by % of Top-2% Authors in Retraction List', fontsize=12, fontweight='bold')
            ax1.set_xlabel('Percentage (%)', fontsize=11, fontweight='bold')
            ax1.grid(axis='x', linestyle='--', alpha=0.7)
            for bar in bars1: ax1.text(bar.get_width() + (ax1.get_xlim()[1]*0.01), bar.get_y() + bar.get_height()/2, f"{bar.get_width():.1f}%", va='center')

            bars2 = ax2.barh(df_plot_retractions['Country'], df_plot_retractions['Retraction_Percentage'], color='indianred', edgecolor='black')
            ax2.set_title(f'Top {top_n} by % Share of Global Retractions', fontsize=12, fontweight='bold')
            ax2.set_xlabel('Percentage (%)', fontsize=11, fontweight='bold')
            ax2.grid(axis='x', linestyle='--', alpha=0.7)
            for bar in bars2: ax2.text(bar.get_width() + (ax2.get_xlim()[1]*0.01), bar.get_y() + bar.get_height()/2, f"{bar.get_width():.1f}%", va='center')

            ax1.set_xlim(0, df_plot_authors['Author_Percentage'].max() * 1.15)
            ax2.set_xlim(0, df_plot_retractions['Retraction_Percentage'].max() * 1.15)
            plt.tight_layout()
            
            # Display plot in the web app
            st.pyplot(fig)
else:
    st.info("Please upload both data files in the sidebar to begin the analysis.")


# In[ ]:




