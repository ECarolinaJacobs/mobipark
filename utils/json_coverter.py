import pandas as pd
import json

def json_file_to_csv(json_file, output_file):
    """
    Convert a JSON file to a flat CSV, automatically flattening nested structures.

    Args:
        json_file (str): Path to the input JSON file.
        output_file (str): Path to the output CSV file.
    """
    # Read JSON from file
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Check if data is a dict (like your parking-lots example)
    if isinstance(data, dict) and not isinstance(data, list):
        # Convert dict to list of records, preserving keys as a column if needed
        if all(isinstance(v, dict) for v in data.values()):
            # If all values are dicts, use orient='index' to keep keys
            df = pd.DataFrame.from_dict(data, orient='index')
        else:
            # Otherwise treat as single record
            df = pd.DataFrame([data])
    else:
        # If it's already a list, convert directly
        df = pd.DataFrame(data)

    # Flatten all nested dictionaries
    nested_cols = [col for col in df.columns if df[col].apply(lambda x: isinstance(x, dict)).any()]
    
    for col in nested_cols:
        # Extract nested keys into separate columns
        nested_df = df[col].apply(lambda x: x if isinstance(x, dict) else {})
        nested_df = pd.json_normalize(nested_df)
        
        # Rename columns to include parent column name
        nested_df.columns = [f"{col}_{subcol}" for subcol in nested_df.columns]
        
        # Add to main dataframe
        df = pd.concat([df.drop(columns=[col]), nested_df], axis=1)

    # Save as CSV
    df.to_csv(output_file, index=False)
    print(f"✅ CSV saved to {output_file}")


# Example usage:
json_file_to_csv("../data/payments.json", "payments.csv")