import json
import yaml
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Hardcoded KPIs for all courses
HARDCODED_KPIS = [
    "attendance_rate",
    "average_grade",
    "completion_rate",
    "response_rate"
]

RAW_JSON_PATH = "courses_raw.json"


def load_courses_from_json(json_path=RAW_JSON_PATH):
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_cursos_txt_and_yml(courses):
    txt_lines = []
    yml_data = {"courses": {}}
    for course in courses:
        course_id = course.get("id")
        name = course.get("title") or course_id
        categories = course.get("categories") or []
        category = categories[0] if categories else "SinCategoria"
        # TXT
        txt_lines.append(f"{category},{course_id}")
        # YML
        if category not in yml_data["courses"]:
            yml_data["courses"][category] = {}
        yml_data["courses"][category][course_id] = {
            "name": name,
            "kpis": HARDCODED_KPIS
        }
    return txt_lines, yml_data


def write_files(txt_lines, yml_data, txt_path="cursos.txt", yml_path="cursos.yml"):
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(txt_lines) + "\n")
    print(f"Wrote {txt_path} with {len(txt_lines)} lines.")
    with open(yml_path, "w", encoding="utf-8") as f:
        yaml.dump(yml_data, f, allow_unicode=True, sort_keys=False)
    print(f"Wrote {yml_path}.")


def main():
    courses = load_courses_from_json()
    txt_lines, yml_data = build_cursos_txt_and_yml(courses)
    print("Writing files...")
    write_files(txt_lines, yml_data)
    print("Done.")


if __name__ == "__main__":
    main() 