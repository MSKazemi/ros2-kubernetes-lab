import json
import pandas as pd
from IPython.display import display
import os
from pandas import json_normalize

def read_json(file_path):
    with open(file_path, 'rt', encoding='utf-8') as file:
        data = json.load(file)
    print(f"File: {file}\n")
    print("--- keys --------------------" + 20*'--')
    print(data[0].keys())
    print("--- Metric Keys -------------" + 20*'--')
    print(data[0]['metric'].keys())
    df = json_normalize(data)

    print("\nUnique values in each column except values columns: ------------------")
    for col in df.drop(columns=['values']).columns:
        print(f"{col}: {df[col].unique()}")
    print("=-=" * 24)
    display(df)
    print("\n")
    return df




def filter_filenames(path, substrings, and_or):
    # Normalize substrings to lower case for case-insensitive comparison
    substrings = [s.lower() for s in substrings]
    
    # Initialize list to hold matching filenames
    matching_files = []
    
    # Walk through the directory
    try:
        # List all files in the directory
        files = os.listdir(path)
    except Exception as e:
        print(f"Error accessing directory: {e}")
        return []
    
    # Check each file in the directory
    for file in files:
        # Convert filename to lower case
        file_lower = file.lower()
        
        # Check if 'and' or 'or' conditions are met
        if and_or == 'and':
            # Check if all substrings are in the filename
            if all(sub in file_lower for sub in substrings):
                matching_files.append(file)
        elif and_or == 'or':
            # Check if any substring is in the filename
            if any(sub in file_lower for sub in substrings):
                matching_files.append(file)

    return matching_files


def get_filename_and_root_path(file_path):
    # Extract the file name from the path
    file_name = os.path.basename(file_path)
    # Extract the directory (root path) from the path
    root_path = os.path.dirname(file_path)
    return file_name, root_path


def json_2_pandas(json_file_path):
    with open(json_file_path, 'rt', encoding='utf-8') as file:
        data = json.load(file)
    df = json_normalize(data)
    file_name, root_path = get_filename_and_root_path(json_file_path)
    # os.path.join keeps this portable (Windows) and avoids "/csv/" at the filesystem
    # root when json_file_path has no directory part.
    csv_dir = os.path.join(root_path, "csv")
    csv_file_path = os.path.join(csv_dir, file_name.replace('.json', '.csv'))
    os.makedirs(csv_dir, exist_ok=True)
    df.to_csv(csv_file_path, index=False)
    return df


import ast  # For converting string representation of lists into actual lists

def transform_data(data):
    # Convert the string representation of list in the 'values' column to actual lists
    # data['values'] = data['values'].apply(ast.literal_eval)
    
    display(data)

    # Explode the 'values' column into multiple rows
    exploded_data = data.explode('values')

    # Split the 'values' column into 'timestamp' and 'value' columns
    exploded_data[['timestamp', 'value']] = pd.DataFrame(exploded_data['values'].tolist(), index=exploded_data.index)

    # Now let's display the first few rows of the transformed DataFrame
    display(exploded_data)

    exploded_data['timestamp'] = pd.to_datetime(exploded_data['timestamp'], unit='s')
    exploded_data.drop(columns=['values'], inplace=True, axis=0)
    exploded_data.fillna("_", inplace=True)
    # display(exploded_data)
    pivoted_data = exploded_data.pivot(index='timestamp', columns=[col for col in exploded_data.columns if col not in ['value', 'timestamp']], values='value')

    if isinstance(pivoted_data, pd.Series):
        display(pivoted_data)
        pivoted_data = pd.DataFrame(pivoted_data, columns=['val'])
        pivoted_data.reset_index(drop=False, inplace=True)
        pivoted_data.set_index('timestamp', inplace=True) 
    
    pivoted_data.sort_index(inplace=True) 
    display(pivoted_data)
    

    # Remove the name of the column index
    pivoted_data.columns.name = None
    
    pivoted_data.index.name = None

    # pivoted_data.reset_index(drop=False, inplace=True)  
    display("Pivoted Data:")
    display(pivoted_data)
    # Resetting the index

    # pivoted_data.columns = ['_'.join(col).strip() for col in pivoted_data.columns.values]
    # pivoted_data.columns = pivoted_data.columns.str.replace(":", "_").str.replace(" ", "-")

    # Identify non-numeric columns
    non_numeric_columns = pivoted_data.select_dtypes(exclude=['int', 'float']).columns
    print(non_numeric_columns)

    # Convert non-numeric columns to float
    for col in non_numeric_columns:
        pivoted_data[col] = pd.to_numeric(pivoted_data[col], errors='coerce')

    display(pivoted_data)

    return pivoted_data


def unique_values(data):
    unique_values = {col: data[col].unique() for col in data.columns}
    for column, values in unique_values.items():
        print(f"Unique values for {column}: {values}")
    return unique_values
