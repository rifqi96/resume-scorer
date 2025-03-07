import os
import json
import uuid
import PyPDF2
import requests
import time
import shutil
from dotenv import load_dotenv

# Check if .env file exists, if not copy from .env.example
if not os.path.exists('.env'):
    if os.path.exists('.env.example'):
        shutil.copy('.env.example', '.env')
        print("Created .env file from .env.example")
    else:
        # Create a basic .env file with default values
        with open('.env', 'w') as f:
            f.write("""RESUME_FOLDER=resumes
JOB_DESC_FOLDER=job_descriptions
RESULT_FOLDER=results
BATCH_SIZE=5
OPENROUTER_API_KEY=
OPENROUTER_MODEL=openai/gpt-4o-mini
DEBUG=False
""")
        print("Created new .env file with default values")

# Load environment variables from .env file
load_dotenv()

# Prompt for API key and model
def prompt_for_credentials():
    current_api_key = os.getenv('OPENROUTER_API_KEY', '')
    current_model = os.getenv('OPENROUTER_MODEL', 'openai/gpt-4o-mini')
    
    api_key_display = current_api_key[:5] + '...' + current_api_key[-5:] if current_api_key and len(current_api_key) > 10 else current_api_key
    
    print("\n=== OpenRouter API Configuration ===")
    print(f"Current API Key: {api_key_display if current_api_key else 'Not set'}")
    api_key = input(f"Enter your OpenRouter API key (press Enter to keep current): ").strip()
    
    if not api_key and not current_api_key:
        print("ERROR: No API key provided. You need an API key to continue.")
        print("Get your OpenRouter API key at: https://openrouter.ai/keys")
        return False
    
    if api_key:
        # Update .env file with new API key
        update_env_file('OPENROUTER_API_KEY', api_key)
        os.environ['OPENROUTER_API_KEY'] = api_key
    
    print(f"\nCurrent Model: {current_model}")
    model = input(f"Enter model name (press Enter for default '{current_model}'): ").strip()
    
    if model:
        # Update .env file with new model
        update_env_file('OPENROUTER_MODEL', model)
        os.environ['OPENROUTER_MODEL'] = model
    elif not current_model:
        # Set default model if none provided
        update_env_file('OPENROUTER_MODEL', 'openai/gpt-4o-mini')
        os.environ['OPENROUTER_MODEL'] = 'openai/gpt-4o-mini'
    
    return True

def update_env_file(key, value):
    """Update a specific key in the .env file"""
    env_lines = []
    key_updated = False
    
    # Read current .env file
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            env_lines = f.readlines()
    
    # Update or add the key
    for i, line in enumerate(env_lines):
        if line.strip().startswith(f"{key}="):
            env_lines[i] = f"{key}={value}\n"
            key_updated = True
            break
    
    if not key_updated:
        env_lines.append(f"{key}={value}\n")
    
    # Write back to .env file
    with open('.env', 'w') as f:
        f.writelines(env_lines)

# Configuration (will be loaded or prompted for)
RESUME_FOLDER = os.getenv('RESUME_FOLDER', 'resumes')
JOB_DESC_FOLDER = os.getenv('JOB_DESC_FOLDER', 'job_descriptions')
RESULT_FOLDER = os.getenv('RESULT_FOLDER', 'results')
BATCH_SIZE = int(os.getenv('BATCH_SIZE', '5'))
MAX_RETRIES = 3  # Maximum number of retry attempts for API calls
DEBUG = os.getenv('DEBUG', 'False').lower() in ['true', '1', 't', 'yes']

# Get user additional prioritization criteria (if any)
def get_additional_criteria():
    print("\nOptional: Enter additional prioritization criteria (e.g., 'Prioritize candidates from NUS and NTU')")
    print("Leave blank if none. This will be added as supplementary guidance and won't override the main criteria.")
    print("NOTE: Your input won't affect the required output format and will only be used for scoring consideration.")
    additional_criteria = input("> ").strip()
    
    # Filter out any potentially harmful instructions that might try to override format
    harmful_keywords = ["format", "output", "semicolon", "comma", "system", "message", "instruction", 
                       "ignore", "disregard", "instead", "override", "follow", "json", "xml", 
                       "restructure", "change", "modify"]
    
    contains_harmful = any(keyword in additional_criteria.lower() for keyword in harmful_keywords)
    
    if additional_criteria:
        if contains_harmful:
            print("WARNING: Your input contains words that may be attempting to change the output format.")
            print("These instructions will be filtered out to preserve the system's functionality.")
            # Filter out sentences containing harmful keywords
            filtered_criteria = []
            for sentence in additional_criteria.split('.'):
                if not any(keyword in sentence.lower() for keyword in harmful_keywords):
                    filtered_criteria.append(sentence)
            
            if filtered_criteria:
                additional_criteria = '. '.join(filtered_criteria)
                print(f"Filtered criteria: '{additional_criteria}'")
            else:
                print("All criteria were filtered out due to potential format override attempts.")
                additional_criteria = ""
        else:
            print(f"Additional criteria added: '{additional_criteria}'")
    else:
        print("No additional criteria specified.")
    
    return additional_criteria

# Ensure result folder exists
os.makedirs(RESULT_FOLDER, exist_ok=True)

# Function to extract text from PDF
def extract_text_from_pdf(pdf_path):
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ''
        for page in reader.pages:
            text += page.extract_text()
    return text

# Function to read job description from .md file
def read_job_description(job_desc_path):
    with open(job_desc_path, 'r') as file:
        job_desc = file.read()
    return job_desc

# Function to process a batch of resumes
def process_batch(resume_texts, job_desc, additional_criteria=None):
    headers = {
        'Authorization': f'Bearer {os.environ.get("OPENROUTER_API_KEY")}',
        'Content-Type': 'application/json'
    }
    
    # Keep the system message absolutely intact - this defines the required output format
    system_message = 'You are a resume scorer. Score each resume based on the provided job description. The score is on the scale of 0-100. The score can be in decimal. Format your answer as "name,score,reason" separated by semicolons. For example, "name1,87.5,The reason without comma.;name2,90, Another reason." Please ONLY answer STRICTLY in this format and DON\'T use ANY comma when giving the reason, because it will break the format.'
    
    # If additional criteria are provided, insert them safely within the user content
    # but with explicit instructions to maintain the required output format
    additional_content = ""
    if additional_criteria and additional_criteria.strip():
        additional_content = f'''
Additional prioritization note: {additional_criteria}

IMPORTANT: The above is ONLY for consideration in scoring. You must STILL follow the EXACT output format specified in the system instructions:
"name,score,reason" separated by semicolons with NO commas in the reason section.
'''
    
    user_content = f'''Job Description: {job_desc}

Resumes:
{resume_texts}
{additional_content}'''
    
    data = {
        'model': os.environ.get('OPENROUTER_MODEL', 'openai/gpt-4o-mini'),
        'messages': [
            {
                'role': 'system',
                'content': system_message
            },
            {
                'role': 'user',
                'content': user_content
            }
        ]
    }
    
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post('https://openrouter.ai/api/v1/chat/completions', headers=headers, json=data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            if DEBUG: print(f"DEBUG: API call attempt {attempt + 1} failed with error: {e}")
            if attempt < MAX_RETRIES - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                if DEBUG: print(f"DEBUG: Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                print(f"ERROR: API call failed after {MAX_RETRIES} attempts. Stopping the program.")
                raise

# Function to save results
def save_results(results, result_folder, original_filenames):
    saved_files = []
    for i, result in enumerate(results):
        if i >= len(original_filenames):
            if DEBUG: print(f"DEBUG: No filename available for result {i}, skipping")
            continue
            
        original_filename = original_filenames[i]
        candidate_name = result['name']
        parts = result['response'].split(',')
        if len(parts) < 2:
            if DEBUG: print(f"DEBUG: Skipping candidate response for {candidate_name} due to invalid format: {result['response']}")
            continue
        
        # Use the first element as name, second as score, rest as reason
        score_str = parts[1].strip()
        try:
            score = float(score_str)
        except Exception as e:
            if DEBUG: print(f"DEBUG: Error converting score for {candidate_name} with response: {result['response']}. Error: {e}")
            continue
        
        reason = ','.join(parts[2:]).strip() if len(parts) > 2 else ''
        result_data = {
            'id': str(uuid.uuid4()),
            'name': candidate_name,
            'score': score,
            'reason': reason,
            'original_filename': original_filename
        }
        
        # Save with original filename (without extension)
        base_filename = os.path.splitext(original_filename)[0]
        result_file = os.path.join(result_folder, f'{base_filename}.json')
        with open(result_file, 'w') as f:
            json.dump(result_data, f, indent=4)
        
        saved_files.append(result_file)
        if DEBUG: print(f"DEBUG: Saved candidate result for {candidate_name} in {result_file}")
    
    return saved_files

# Main function
def main():
    # Ensure API credentials are set
    if not prompt_for_credentials():
        print("Exiting program due to missing API credentials.")
        return
    
    # Ensure required folders exist
    for folder in [RESUME_FOLDER, JOB_DESC_FOLDER, RESULT_FOLDER]:
        os.makedirs(folder, exist_ok=True)
        
    # Check if job description exists
    job_desc_path = os.path.join(JOB_DESC_FOLDER, 'job_description.md')
    if not os.path.exists(job_desc_path):
        print(f"Job description file not found at: {job_desc_path}")
        print(f"Please create a job description file at this location and try again.")
        return
        
    # Get any additional prioritization criteria from the user
    additional_criteria = get_additional_criteria()
    
    # Read job description from .md file
    job_desc = read_job_description(job_desc_path)
    if DEBUG: print(f"DEBUG: Loaded job description from {job_desc_path}, length: {len(job_desc)}")

    # Check for existing results to avoid reprocessing
    existing_json_files = [f for f in os.listdir(RESULT_FOLDER) if f.endswith('.json') and not f.startswith('_')]
    existing_json_basenames = [os.path.splitext(f)[0] for f in existing_json_files]
    
    if DEBUG: print(f"DEBUG: Found {len(existing_json_files)} existing JSON result files")

    # Load resumes that haven't been processed yet
    all_resume_files = [f for f in os.listdir(RESUME_FOLDER) if f.endswith('.pdf')]
    resume_files = []
    
    for resume_file in all_resume_files:
        base_filename = os.path.splitext(resume_file)[0]
        if base_filename in existing_json_basenames:
            if DEBUG: print(f"DEBUG: Skipping {resume_file} as it already has a JSON result file")
            continue
        resume_files.append(resume_file)
    
    if DEBUG: print(f"DEBUG: Found {len(resume_files)} resume files that need processing out of {len(all_resume_files)} total")
    
    if not resume_files:
        print("No new resumes to process. All files have corresponding JSON results.")
        # Still aggregate and save final results
        aggregate_and_save_results(RESULT_FOLDER)
        return

    # Process the remaining resumes
    resume_texts = []
    for resume_file in resume_files:
        result_text_file = os.path.join(RESULT_FOLDER, f'{resume_file}.txt')
        if os.path.exists(result_text_file):
            print(f'{resume_file} text already extracted. Loading from {result_text_file}')
            with open(result_text_file, 'r') as f:
                resume_text = f.read()
            if DEBUG: print(f"DEBUG: Loaded resume {resume_file} with length {len(resume_text)}")
            resume_texts.append((resume_file, resume_text))
        else:
            resume_path = os.path.join(RESUME_FOLDER, resume_file)
            resume_text = extract_text_from_pdf(resume_path)
            if DEBUG: print(f"DEBUG: Extracted resume {resume_file} with length {len(resume_text)}")
            resume_texts.append((resume_file, resume_text))
            print(f'Extracted text from {resume_file}')
            with open(result_text_file, 'w') as f:
                f.write(resume_text)
    
    if DEBUG: print(f"DEBUG: Total resumes to process: {len(resume_texts)}")

    # Process resumes in batches
    for i in range(0, len(resume_texts), BATCH_SIZE):
        batch = resume_texts[i:i + BATCH_SIZE]
        batch_texts = '\n'.join([f'{file};{text}' for file, text in batch])
        batch_filenames = [file for file, _ in batch]
        
        try:
            response = process_batch(batch_texts, job_desc, additional_criteria)
            if DEBUG: print(f"DEBUG: API response for batch {i//BATCH_SIZE + 1}: {response}")
            print(f'Processed batch {i//BATCH_SIZE + 1} of {(len(resume_texts) - 1)//BATCH_SIZE + 1}')
            
            results = []
            if len(response.get('choices', [])) == len(batch):
                for j, (file, _) in enumerate(batch):
                    candidate_response = response['choices'][j]['message']['content']
                    if DEBUG: print(f"DEBUG: Candidate response for {file}: {candidate_response}")
                    try:
                        name, score, reason = candidate_response.split(',', 2)
                        results.append({
                            'name': name.strip(),
                            'response': candidate_response.strip()
                        })
                    except Exception as e:
                        if DEBUG: print(f"DEBUG: Error parsing candidate response for {file}: {candidate_response}. Error: {e}")
            else:
                combined_response = response['choices'][0]['message']['content']
                if DEBUG: print(f"DEBUG: Combined candidate responses: {combined_response}")
                responses = combined_response.split(';')
                for resp in responses:
                    if not resp.strip():
                        continue
                    try:
                        name, score, reason = resp.split(',', 2)
                        results.append({
                            'name': name.strip(),
                            'response': resp.strip()
                        })
                    except Exception as e:
                        if DEBUG: print(f"DEBUG: Error parsing combined candidate response: {resp}. Error: {e}")
            
            save_results(results, RESULT_FOLDER, batch_filenames)
            time.sleep(2)  # Avoid rate limiting
            
        except Exception as e:
            print(f"ERROR: Failed to process batch {i//BATCH_SIZE + 1}: {e}")
            # This batch failed after retries, stop the program
            break

    # Aggregate and save final results
    aggregate_and_save_results(RESULT_FOLDER)

def aggregate_and_save_results(result_folder):
    """Aggregate all results and save the final sorted list"""
    all_results = []
    for result_file in os.listdir(result_folder):
        if result_file.endswith('.json') and not result_file.startswith('_'):
            with open(os.path.join(result_folder, result_file), 'r') as f:
                result = json.load(f)
                if isinstance(result, dict) and 'score' in result:
                    all_results.append(result)

    # Sort results by score
    all_results.sort(key=lambda x: x['score'], reverse=True)
    print(f'Processed {len(all_results)} resumes in total')
    
    # Save final sorted results
    print(f'Saving final sorted results to {result_folder}')
    final_result_file = os.path.join(result_folder, '_final_results.json')
    with open(final_result_file, 'w') as f:
        json.dump(all_results, f, indent=4)

if __name__ == '__main__':
    main()