"""
send_bulk_email.py
Envía correos en lotes con Amazon SES v2 usando una plantilla existente.

Requisitos:
- boto3 instalado (`pip install boto3`)
- Credenciales configuradas (`aws configure` o SSO)
- Plantilla creada en la MISMA región
- Contact List para {{amazonSESUnsubscribeUrl}}

Uso (Windows / PowerShell):
  # Opción 1: Usar emails desde Contact List
  python send_bulk_email.py \
    --sender plataforma@preum30m.com \
    --template links_zoom_clases \
    --contact-list alumnos \
    --region us-east-2

  # Opción 2: Usar emails desde CSV
  python send_bulk_email.py --csv destinatarios.csv \
    --sender plataforma@preum30m.com \
    --template links_zoom_clases \
    --region us-east-2

El CSV debe tener al menos la columna: email
"""

import argparse
import csv
import json
import os
import sys
import time
from typing import Iterable, List

import boto3
from botocore.exceptions import ClientError

MAX_PER_BULK = 50  # límite de SES para send_bulk_email


def read_emails_from_csv(path: str) -> List[str]:
    emails = []
    seen = set()
    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if "email" not in reader.fieldnames:
                print("ERROR: el CSV debe tener una columna 'email' en la primera fila.", file=sys.stderr)
                sys.exit(2)
            for row in reader:
                e = (row.get("email") or "").strip()
                if not e or e.lower() in seen:
                    continue
                seen.add(e.lower())
                emails.append(e)
    except FileNotFoundError:
        print(f"ERROR: no se encontró el archivo CSV: {path}", file=sys.stderr)
        sys.exit(2)
    return emails


def read_emails_from_contact_list(ses_client, contact_list_name: str, topic_name: str = None) -> List[str]:
    """
    Recupera todos los emails de una Contact List de SES.
    Filtra por TopicName si se especifica.
    """
    emails = []
    next_token = None
    
    print(f"Recuperando contactos de la lista '{contact_list_name}'...")
    
    while True:
        params = {"ContactListName": contact_list_name}
        if next_token:
            params["NextToken"] = next_token
        if topic_name:
            params["Filter"] = {"FilteredStatus": "OPT_IN", "TopicFilter": {"TopicName": topic_name}}
        
        try:
            response = ses_client.list_contacts(**params)
            contacts = response.get("Contacts", [])
            
            for contact in contacts:
                email = contact.get("EmailAddress")
                if email:
                    emails.append(email)
            
            next_token = response.get("NextToken")
            if not next_token:
                break
                
        except ClientError as e:
            print(f"ERROR al recuperar contactos: {e}", file=sys.stderr)
            sys.exit(2)
    
    print(f"Se recuperaron {len(emails)} contactos de la lista.")
    return emails


def chunked(iterable: List[str], size: int) -> Iterable[List[str]]:
    for i in range(0, len(iterable), size):
        yield iterable[i:i + size]


def main():
    parser = argparse.ArgumentParser(description="Enviar correos en bulk con SES v2 y plantilla.")
    parser.add_argument("--csv", default=None, help="Ruta al CSV con columna 'email'. Si no se especifica, se usa --contact-list.")
    parser.add_argument("--sender", required=True, help="Remitente verificado en SES (From), p.ej. plataforma@preum30m.com")
    parser.add_argument("--template", required=True, help="Nombre de la plantilla en SES (misma región).")
    parser.add_argument("--region", default=os.getenv("AWS_REGION", "us-east-2"), help="Región de SES (por defecto usa AWS_REGION o us-east-2).")
    parser.add_argument("--contact-list", default=None, help="Nombre de la Contact List (para obtener emails y {{amazonSESUnsubscribeUrl}}).")
    parser.add_argument("--topic", default=None, help="TopicName (opcional) dentro de la Contact List.")
    parser.add_argument("--config-set", default=None, help="ConfigurationSetName para métricas/eventos (opcional).")
    parser.add_argument("--batch", type=int, default=MAX_PER_BULK, help=f"Tamaño de lote (<= {MAX_PER_BULK}).")
    parser.add_argument("--sleep", type=float, default=0.2, help="Pausa en segundos entre lotes (p.ej., 0.2).")
    args = parser.parse_args()

    if args.batch < 1 or args.batch > MAX_PER_BULK:
        print(f"ERROR: --batch debe estar entre 1 y {MAX_PER_BULK}", file=sys.stderr)
        sys.exit(2)

    # Validar que se proporcione al menos una fuente de emails
    if not args.csv and not args.contact_list:
        print("ERROR: Debes especificar --csv o --contact-list para obtener los destinatarios.", file=sys.stderr)
        sys.exit(2)

    ses = boto3.client("sesv2", region_name=args.region)

    # Obtener emails desde CSV o Contact List
    if args.csv:
        emails = read_emails_from_csv(args.csv)
        if not emails:
            print("No hay destinatarios válidos en el CSV.", file=sys.stderr)
            sys.exit(0)
    else:
        emails = read_emails_from_contact_list(ses, args.contact_list, args.topic)
        if not emails:
            print("No hay destinatarios en la Contact List.", file=sys.stderr)
            sys.exit(0)

    total_ok = 0
    total_fail = 0

    # Tu plantilla sólo usa {{amazonSESUnsubscribeUrl}}, así que TemplateData puede ser "{}"
    default_template_data = json.dumps({})

    start = time.time()
    source = "Contact List" if not args.csv else "CSV"
    print(f"Iniciando envío: {len(emails)} destinatarios (fuente: {source}), región={args.region}, plantilla={args.template}")
    if args.contact_list:
        print(f"Usando ContactList='{args.contact_list}' para List-Unsubscribe / one-click")

    # NOTA: ListManagementOptions solo funciona con send_email individual, NO con send_bulk_email
    # Por eso usamos send_email en lugar de send_bulk_email cuando se especifica --contact-list
    for batch_num, batch_emails in enumerate(chunked(emails, args.batch), start=1):
        batch_ok = 0
        batch_fail = []
        
        for email_addr in batch_emails:
            params = {
                "FromEmailAddress": args.sender,
                "Destination": {"ToAddresses": [email_addr]},
                "Content": {
                    "Template": {
                        "TemplateName": args.template,
                        "TemplateData": default_template_data
                    }
                }
            }
            
            if args.contact_list:
                params["ListManagementOptions"] = {"ContactListName": args.contact_list}
                if args.topic:
                    params["ListManagementOptions"]["TopicName"] = args.topic
            
            if args.config_set:
                params["ConfigurationSetName"] = args.config_set
            
            try:
                ses.send_email(**params)
                batch_ok += 1
                total_ok += 1
            except ClientError as e:
                batch_fail.append((email_addr, e))
                total_fail += 1
        
        print(f"[Lote {batch_num}] OK: {batch_ok}/{len(batch_emails)}  (Total OK: {total_ok}/{len(emails)})")
        
        if batch_fail:
            for addr, e in batch_fail[:5]:  # muestra hasta 5 fallos por lote
                code = e.response.get('Error', {}).get('Code', 'Unknown')
                msg = e.response.get('Error', {}).get('Message', str(e))
                print(f"  - FAIL {addr}: {code} - {msg}")
            if len(batch_fail) > 5:
                print(f"  ... y {len(batch_fail) - 5} fallos más en este lote.")

        time.sleep(max(0.0, args.sleep))

    secs = time.time() - start
    print(f"Terminado. OK={total_ok}, FAIL={total_fail}, Total={len(emails)} en {secs:.1f}s")


if __name__ == "__main__":
    main()
