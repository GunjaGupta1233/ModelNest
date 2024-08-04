import requests
from prettytable import PrettyTable
from datetime import datetime
from multiprocessing import Pool, cpu_count
import argparse
import multiprocessing
import subprocess
import json
import sys
import os

def get_ollama_models():
    try:
        response = requests.get("http://localhost:11434/api/tags")
        if response.status_code == 200:
            return response.json()['models']
        else:
            print(f"Error: Unable to fetch models. Status code: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error: Unable to connect to Ollama. Make sure it's running. Details: {e}")
        return None

def format_size(size_in_bytes):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_in_bytes < 1024.0:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024.0

def format_date(date_string):
    try:
        date = datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S.%fZ")
        return date.strftime("%Y-%m-%d %H:%M")  # Format to single line
    except ValueError:
        return date_string  # Return original string if parsing fails

def process_model(args):
    index, model = args
    name = model.get('name', 'N/A')
    size = format_size(model.get('size', 0))
    modified = format_date(model.get('modified_at', 'N/A'))
    details = model.get('details', {})
    parameters = details.get('parameter_size', 'N/A')
    format_type = details.get('format', 'N/A')  # Renamed to avoid conflict with built-in function
    quantization = details.get('quantization_level', 'N/A')
    family = details.get('family', 'N/A')
    
    return [index + 1, name, size, parameters, format_type, quantization, modified, family]

def display_models(models):
    table = PrettyTable()
    table.field_names = ["S.No.", "Model", "Size", "Parameters", "Format", "Quantization", "Modified", "Family"]
    table.align = "l"  # Left-align all columns
    
    # Use multiprocessing to process models in parallel
    with Pool(processes=cpu_count()) as pool:
        results = pool.map(process_model, enumerate(models))
    
    # Sort results by S.No. and add to table
    for row in sorted(results, key=lambda x: x[0]):
        table.add_row(row)
    
    print(f"\nModels ({len(models)}):")
    print(table)
    print("\nUse modelnest MODEL_NAME -v to see all the info of one model.")

def display_model_details(model_name, models):
    model = next((m for m in models if m['name'] == model_name), None)
    if not model:
        print(f"Model '{model_name}' not found.")
        return

    table = PrettyTable()
    table.field_names = ["Attribute", "Value"]
    table.align = "l"

    # Add basic information
    table.add_row(["Name", model.get('name', 'N/A')])
    table.add_row(["Size", format_size(model.get('size', 0))])
    table.add_row(["Modified", format_date(model.get('modified_at', 'N/A'))])

    # Add all details
    details = model.get('details', {})
    for key, value in details.items():
        table.add_row([key.replace('_', ' ').title(), str(value)])

    # Add any additional fields from the model object
    for key, value in model.items():
        if key not in ['name', 'size', 'modified_at', 'details']:
            table.add_row([key.replace('_', ' ').title(), str(value)])

    print(f"\nDetailed information for model '{model_name}':")
    print(table)

def run_ollama_command(command, model_name):
    try:
        if command == 'rm':
            confirm = input(f"Are you sure you want to remove the model '{model_name}'? (Y/N): ").lower()
            if confirm != 'y':
                print("Model removal cancelled.")
                return

        result = subprocess.run(['ollama', command, model_name], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"Successfully {command}ed model '{model_name}'.")
        else:
            print(f"Error {command}ing model '{model_name}': {result.stderr}")
    except Exception as e:
        print(f"Error executing ollama command: {e}")

def update_software():
    script_path = os.path.abspath(sys.argv[0])
    print(f"Current script path: {script_path}")
    
    try:
        print("Checking for updates...")
        # Replace this URL with your actual GitHub raw file URL
        url = "https://raw.githubusercontent.com/GunjaGupta1233/ModelNest/main/modelnest.py"
        response = requests.get(url)
        
        if response.status_code == 200:
            current_content = ''
            with open(script_path, 'r') as file:
                current_content = file.read()
            
            if current_content == response.text:
                print("You already have the latest version.")
                return
            
            # Create a backup of the current script
            backup_path = f"{script_path}.backup"
            with open(backup_path, 'w') as file:
                file.write(current_content)
            print(f"Backup created at: {backup_path}")
            
            # Write the new content
            with open(script_path, 'w') as file:
                file.write(response.text)
            
            print("Software updated successfully.")
            print("Please restart the application for changes to take effect.")
            print(f"If you experience issues, you can restore the backup from: {backup_path}")
            sys.exit(0)  # Exit immediately after update
        else:
            print(f"Failed to fetch updates. Status code: {response.status_code}")
    except Exception as e:
        print(f"Error updating software: {e}")

def main():
    if len(sys.argv) > 1 and sys.argv[1] == '-u':
        update_software()
        return
    
    multiprocessing.freeze_support()
    parser = argparse.ArgumentParser(description="Manage Ollama models.")
    parser.add_argument('model_name', nargs='*', help="Model name(s) to operate on")
    parser.add_argument('--delete', action='store_true', help="Remove specified model(s) from Ollama")
    parser.add_argument('-d', action='store_true', help="Download and run specified model(s) in Ollama")
    parser.add_argument('-s', choices=['n', 'd', 's', 'p'], help="Sort table by name (n), date (d), size (s), or parameters (p)")
    parser.add_argument('-u', action='store_true', help="Check for and apply software updates")
    parser.add_argument('--helpme', action='store_true', help="Display extended help information")
    parser.add_argument('-v', action='store_true', help="Display detailed information for a specific model")
    
    args = parser.parse_args()
    
    if args.helpme:
        parser.print_help()
        return
    
    models = get_ollama_models()
    
    if not models:
        return
    
    if args.model_name:
        if args.delete:
            for model_name in args.model_name:
                run_ollama_command('rm', model_name)
        elif args.d:
            for model_name in args.model_name:
                run_ollama_command('run', model_name)
        elif args.v:
            display_model_details(args.model_name[0], models)
        else:
            print("Please specify an action (--delete, -d, or -v) when providing a model name.")
    else:
        if args.s:
            # Implement sorting logic here
            sort_key = {'n': 'name', 'd': 'modified_at', 's': 'size', 'p': 'parameter_size'}[args.s]
            models.sort(key=lambda x: x.get(sort_key, x['details'].get(sort_key, '')), reverse=(args.s in ['s', 'p']))
        elif args.u:
            update_software()
        else:
            display_models(models)

if __name__ == "__main__":
    main()
