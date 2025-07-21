import pandas as pd
import argparse
from pathlib import Path

parser = argparse.ArgumentParser(description='Convert question/correct answer file to analysis format.')
parser.add_argument('--input', '-i', required=True, help='Input CSV file (downloaded format)')
parser.add_argument('--output', '-o', required=True, help='Output CSV file (for analysis, e.g. ..._questions.csv)')
args = parser.parse_args()

# Read input
input_path = Path(args.input)
df = pd.read_csv(input_path)

# Find all answer columns
answer_cols = [col for col in df.columns if col.lower().startswith('answer')]

rows = []
for _, row in df.iterrows():
    question = row['Question']
    correct_ans_num = int(row['CorrectAns']) if not pd.isnull(row['CorrectAns']) else None
    correct_answer = ''
    if correct_ans_num and 1 <= correct_ans_num <= len(answer_cols):
        correct_answer = row[answer_cols[correct_ans_num - 1]]
    rows.append({'question': question, 'correct_answer': correct_answer})

out_df = pd.DataFrame(rows)
out_df.to_csv(args.output, index=False)
print(f"Wrote {len(out_df)} questions to {args.output}") 