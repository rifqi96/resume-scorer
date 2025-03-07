# Resume Scoring Application

This application automatically scores resumes against a job description using AI, helping you identify the most qualified candidates efficiently.

## Overview

The Resume Scoring Application:

1. Extracts text from resume PDFs
2. Compares each resume against a job description
3. Uses AI to score candidates on a 0-100 scale
4. Provides reasoning for each score
5. Ranks candidates from highest to lowest score

## Requirements

- Python 3.7+
- OpenRouter API key (free options available)
- Resume PDFs
- Job description in Markdown format

## Setup Instructions

### 1. Clone or Download the Repository

```bash
git clone <repository-url>
cd resume-scoring-app
```

### 2. Set Up Virtual Environment

It's recommended to use a virtual environment to avoid package conflicts.

#### For Windows:
```bash
# Create a virtual environment
python -m venv env

# Activate the virtual environment
env\Scripts\activate
```

#### For macOS/Linux:
```bash
# Create a virtual environment
python3 -m venv env

# Activate the virtual environment
source env/bin/activate
```

### 3. Install Required Packages

With the virtual environment activated, install the required packages:

```bash
pip install -r requirements.txt
```

### 4. Get an OpenRouter API Key

1. Go to [OpenRouter.ai](https://openrouter.ai/)
2. Sign up for a free account
3. Navigate to the API Keys section: [https://openrouter.ai/keys](https://openrouter.ai/keys)
4. Create a new API key and copy it

#### Free Models vs. Paid Models

- **Free Options**: OpenRouter provides free access to certain models with daily limits
- **Paid Options**: For better accuracy, you can add credit to your account ($5 minimum) for access to more advanced models
- **Recommended Model**: `openai/gpt-4o-mini` (default) offers a good balance of cost and performance

### 5. Prepare Your Files

1. Create the following folders if they don't exist:
   ```
   resumes/          # Where your resume PDFs go
   job_descriptions/ # Where your job description file goes
   results/          # Where scores will be saved
   ```

2. Add your resume PDFs to the `resumes/` folder
3. Create a file named `job_description.md` in the `job_descriptions/` folder
4. Write your job description in the Markdown file

### 6. Run the Application

Make sure your virtual environment is activated, then run:


```bash
python resume_scorer.py
```

The application will:
1. Check for an existing `.env` file or create one from `.env.example`
2. Prompt you for your OpenRouter API key (or use the existing one)
3. Allow you to select an AI model (or use the default)
4. Ask for any additional prioritization criteria
5. Process the resumes in batches
6. Save individual results and a final ranking

To deactivate the virtual environment when you're done:
```bash
deactivate
```

## How It Works

1. **Configuration**: The app loads or prompts for settings on first run
2. **Job Description**: The job description is used as the scoring criteria
3. **Resume Extraction**: Text is extracted from PDF resumes
4. **AI Scoring**: The AI service compares each resume to the job description
5. **Results Processing**: Scores and reasons are parsed and saved
6. **Final Ranking**: All candidates are ranked in descending order by score

## Features

- **Checkpoint Recovery**: Can resume processing if interrupted
- **Result Persistence**: Saves extracted text and scores for future runs
- **Additional Criteria**: Supports custom prioritization rules
- **Batch Processing**: Processes resumes in configurable batches
- **Error Handling**: Retries API calls and handles failures gracefully

## Troubleshooting

- **API Key Issues**: Ensure your OpenRouter API key is correctly entered
- **File Format Problems**: Make sure resumes are PDF files
- **Job Description Missing**: Create a job_description.md file with detailed requirements
- **Rate Limiting**: If processing many resumes, consider increasing the delay between batches
- **Virtual Environment Issues**: 
  - Make sure you activate the virtual environment before running the script
  - If you see "command not found" on macOS/Linux for the activate script, try running `chmod +x env/bin/activate` first
  - For Windows PowerShell users, you may need to run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` to allow script execution

## Advanced Usage

### Configuration Options

The `.env` file contains several options you can customize:

```
RESUME_FOLDER=resumes
JOB_DESC_FOLDER=job_descriptions
RESULT_FOLDER=results
BATCH_SIZE=5
OPENROUTER_API_KEY=your_api_key_here
OPENROUTER_MODEL=openai/gpt-4o-mini
DEBUG=False
```

- **BATCH_SIZE**: Number of resumes to process in each API call
- **DEBUG**: Set to True for detailed logging

### Additional Prioritization Criteria

When running the application, you can specify additional criteria to consider. For example:
- "Prioritize candidates with experience in Python and React"
- "Give higher scores to candidates from engineering backgrounds"
- "Consider leadership experience as an important factor"

Note that these criteria supplement but don't override the job description.

## Output Format

Results are saved in JSON format with the following structure:

```json
{
  "id": "unique-identifier",
  "name": "Candidate Name",
  "score": 85.5,
  "reason": "Relevant experience in required technologies...",
  "original_filename": "resume.pdf"
}
```

A final sorted ranking (`_final_results.json`) is also generated.