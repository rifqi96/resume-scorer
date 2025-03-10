import os
import json
import requests
import time
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration
RESULT_FOLDER = os.getenv('RESULT_FOLDER', 'results')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', '')
OPENROUTER_MODEL = os.getenv('OPENROUTER_MODEL', 'openai/gpt-4o-mini')
MAX_RETRIES = 3  # Maximum number of retry attempts for API calls

def list_candidates():
    """List all available candidates from the results folder"""
    candidates = []
    
    # Check all result folders
    result_folders = [folder for folder in os.listdir() if folder.startswith('results_')]
    
    for folder in result_folders:
        if os.path.isdir(folder):
            # Get all JSON files in the folder
            json_files = [f for f in os.listdir(folder) if f.endswith('.json') and not f.startswith('_')]
            
            for json_file in json_files:
                try:
                    with open(os.path.join(folder, json_file), 'r') as f:
                        data = json.load(f)
                        if 'name' in data and 'original_filename' in data:
                            candidates.append({
                                'name': data['name'],
                                'filename': data['original_filename'],
                                'result_file': os.path.join(folder, json_file),
                                'resume_file': os.path.join(folder, json_file.replace('.json', '.pdf.txt'))
                            })
                except Exception as e:
                    print(f"Error reading {json_file}: {e}")
    
    return candidates

def get_resume_text(resume_file):
    """Get the text content of a resume"""
    try:
        with open(resume_file, 'r') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading resume file: {e}")
        return ""

def generate_interview_questions(resume_text, additional_prompt=""):
    """Generate interview questions based on the resume text"""
    
    system_message = """You are an expert technical interviewer for a web development position. 
Your task is to analyze the candidate's resume and generate thoughtful interview questions.

Generate three categories of questions:
1. Experience-related questions: Questions about the candidate's past projects, roles, and achievements.
2. Technical questions: Questions to assess the candidate's technical knowledge and skills.
3. Behavioral questions: Questions to evaluate the candidate's soft skills, problem-solving approach, and cultural fit.

For each question, also provide a brief note on what to look for in the candidate's answer.

Your response should be in two formats:
1. A human-readable text format with questions organized by category.
2. A JSON format that can be programmatically processed.

The JSON format should follow this structure:
{
  "experience_questions": [
    {
      "question": "Question text here",
      "look_for": "What to look for in the answer"
    }
  ],
  "technical_questions": [
    {
      "question": "Question text here",
      "look_for": "What to look for in the answer"
    }
  ],
  "behavioral_questions": [
    {
      "question": "Question text here",
      "look_for": "What to look for in the answer"
    }
  ]
}"""

    user_content = f"""Resume Text:
{resume_text}

Additional Instructions: {additional_prompt}

Please generate appropriate interview questions based on this resume."""

    headers = {
        'Authorization': f'Bearer {OPENROUTER_API_KEY}',
        'Content-Type': 'application/json'
    }
    
    data = {
        'model': OPENROUTER_MODEL,
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
            print(f"Generating interview questions (attempt {attempt + 1})...")
            response = requests.post('https://openrouter.ai/api/v1/chat/completions', headers=headers, json=data)
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
        except Exception as e:
            print(f"API call attempt {attempt + 1} failed with error: {e}")
            if attempt < MAX_RETRIES - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                print(f"ERROR: API call failed after {MAX_RETRIES} attempts.")
                return "Error generating interview questions. Please try again later."

def save_questions(candidate_name, questions, additional_prompt):
    """Save the generated questions to a file"""
    # Create a sanitized filename
    sanitized_name = candidate_name.replace(" ", "_").lower()
    filename = f"interview_questions_{sanitized_name}.txt"
    
    with open(filename, 'w') as f:
        f.write(f"Interview Questions for: {candidate_name}\n")
        f.write(f"Additional Prompt: {additional_prompt}\n\n")
        f.write(questions)
    
    print(f"\nQuestions saved to {filename}")

def main():
    print("\n===== Interview Questions Generator =====\n")
    
    # Check if API key is set
    if not OPENROUTER_API_KEY:
        print("ERROR: OpenRouter API key is not set. Please set it in the .env file.")
        print("Get your OpenRouter API key at: https://openrouter.ai/keys")
        return
    
    # List all candidates
    candidates = list_candidates()
    
    if not candidates:
        print("No candidates found. Please run the resume scorer first.")
        return
    
    # Display candidates
    print("Available candidates:")
    for i, candidate in enumerate(candidates):
        print(f"{i+1}. {candidate['name']}")
    
    # Prompt for candidate selection
    while True:
        try:
            selection = int(input("\nEnter the number of the candidate (or 0 to exit): "))
            if selection == 0:
                return
            if 1 <= selection <= len(candidates):
                selected_candidate = candidates[selection-1]
                break
            else:
                print("Invalid selection. Please try again.")
        except ValueError:
            print("Please enter a valid number.")
    
    # Get additional prompt
    print("\nEnter additional instructions for question generation")
    print("(e.g., 'Focus on Vue.js experience', 'Include questions about team collaboration')")
    print("Default: 3 experience questions, 3 technical questions, 3 behavioral questions")
    additional_prompt = input("> ").strip()
    
    # Get resume text
    resume_text = get_resume_text(selected_candidate['resume_file'])
    
    if not resume_text:
        print(f"Could not read resume for {selected_candidate['name']}.")
        return
    
    # Generate questions
    print(f"\nGenerating interview questions for {selected_candidate['name']}...")
    questions = generate_interview_questions(resume_text, additional_prompt)
    
    # Display questions
    print("\n===== Generated Interview Questions =====\n")
    print(questions)
    
    # Save questions
    save_questions(selected_candidate['name'], questions, additional_prompt)

if __name__ == "__main__":
    main() 