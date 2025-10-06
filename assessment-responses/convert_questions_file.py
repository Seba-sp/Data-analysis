import pandas as pd
import argparse
from storage import StorageClient
from analisis_responses import detect_question_columns

parser = argparse.ArgumentParser(description='Convert question/correct answer file to analysis format.')
parser.add_argument('--input', '-i', required=True, help='Input CSV file (downloaded format)')
parser.add_argument('--output', '-o', required=True, help='Output CSV file (for analysis, e.g. ..._questions.csv)')
args = parser.parse_args()

storage = StorageClient()

# Read input
input_path = args.input
# Use storage to read CSV
in_df = storage.read_csv(input_path)

# Find all answer columns
answer_cols = [col for col in in_df.columns if col.lower().startswith('answer')]

# Determine which columns contain questions and correct answer numbers
question_col, correct_ans_col = detect_question_columns(in_df, input_path)
if not question_col or not correct_ans_col:
    exit(1)

rows = []
for _, row in in_df.iterrows():
    question = row[question_col]
    correct_ans_num = int(row[correct_ans_col]) if not pd.isnull(row[correct_ans_col]) else None
    correct_answer = ''
    if correct_ans_num and 1 <= correct_ans_num <= len(answer_cols):
        correct_answer = row[answer_cols[correct_ans_num - 1]]
    rows.append({'question': question, 'correct_answer': correct_answer})

out_df = pd.DataFrame(rows)
# Use storage to write CSV
storage.write_csv(args.output, out_df, index=False)
print(f"Wrote {len(out_df)} questions to {args.output}") 