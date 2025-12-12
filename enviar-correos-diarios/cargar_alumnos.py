import csv, boto3, sys

REGION = "us-east-2"
CONTACT_LIST = "alumnos"

def main(csv_path):
    ses = boto3.client("sesv2", region_name=REGION)
    created, updated, skipped = 0, 0, 0

    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            email = (row.get("email") or "").strip()
            if not email:
                continue
            try:
                ses.create_contact(
                    ContactListName=CONTACT_LIST,
                    EmailAddress=email,
                    UnsubscribeAll=False,
                    # AttributesData y TopicPreferences son opcionales
                )
                created += 1
            except ses.exceptions.ConflictException:
                # Ya existía; asegúrate que no esté dado de baja
                ses.update_contact(
                    ContactListName=CONTACT_LIST,
                    EmailAddress=email,
                    UnsubscribeAll=False
                )
                updated += 1
            except Exception as e:
                print(f"SKIP {email}: {e}")
                skipped += 1

    print(f"Listo. creados={created}, actualizados={updated}, omitidos={skipped}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python cargar_contactos.py lista.csv")
        sys.exit(1)
    main(sys.argv[1])
