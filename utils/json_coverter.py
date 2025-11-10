import json
import pandas as pd
import sys
from pathlib import Path

def normalize_json_to_csv(json_file, output_csv=None):
    """
    Convert a JSON file to CSV with normalization for nested objects.
    
    Args:
        json_file: Path to input JSON file
        output_csv: Path to output CSV file (optional, defaults to same name with .csv)
    """
    try:
        # Read the JSON file
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle different JSON structures
        if isinstance(data, dict):
            # Check if it's a dictionary of objects (like {"1": {...}, "2": {...}})
            # by seeing if all values are dictionaries
            if all(isinstance(v, dict) for v in data.values()):
                # Extract just the values, ignore the keys
                data = list(data.values())
                print(f"  Detected object-keyed JSON, extracted {len(data)} records")
            else:
                # If it's a single object, wrap it in a list
                data = [data]
        
        if not isinstance(data, list):
            raise ValueError("JSON must be an object or array of objects")
        
        # Normalize the JSON data (flattens nested structures)
        df = pd.json_normalize(data)
        
        # Generate output filename if not provided
        if output_csv is None:
            output_csv = Path(json_file).stem + '.csv'
        
        # Write to CSV with proper formatting for DBeaver
        df.to_csv(
            output_csv,
            index=False,
            encoding='utf-8',
            quoting=1,  # QUOTE_ALL to ensure proper escaping
            lineterminator='\n'
        )
        
        print(f"✓ Successfully converted {json_file} to {output_csv}")
        print(f"  Rows: {len(df)}, Columns: {len(df.columns)}")
        print(f"  Column names: {', '.join(df.columns.tolist())}")
        
        return output_csv
        
    except FileNotFoundError:
        print(f"✗ Error: File '{json_file}' not found")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"✗ Error: Invalid JSON in '{json_file}': {e}")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)

def main():
    if len(sys.argv) < 2:
        print("Usage: python json_to_csv.py <input.json> [output.csv]")
        print("\nExample:")
        print("  python json_to_csv.py data.json")
        print("  python json_to_csv.py data.json output.csv")
        print("\nSupports:")
        print("  • Arrays: [{...}, {...}]")
        print("  • Object-keyed: {\"1\": {...}, \"2\": {...}}")
        print("  • Single objects: {...}")
        print("  • Nested structures (automatically flattened)")
        sys.exit(1)
    
    json_file = sys.argv[1]
    output_csv = sys.argv[2] if len(sys.argv) > 2 else None
    
    normalize_json_to_csv(json_file, output_csv)

if __name__ == "__main__":
    main()
