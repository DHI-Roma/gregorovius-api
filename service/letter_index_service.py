import csv
import os
def parse_gesamtdatenbank():
    unique_senders = []
    unique_recipients = []
    unique_sender_places = []
    unique_recipient_places = []
    results = []
    with open(os.path.dirname(__file__) + '/../data/gesamtdatenbank.csv', encoding='utf-8') as csvfile:
        csvreader = csv.DictReader(csvfile, delimiter=';')

        for entry in csvreader:
            senders = [entry['sender-1']]

            if entry['sender-1'] not in unique_senders and len(entry['sender-1']) :
                unique_senders.append(entry['sender-1'])

            if entry['sender-2']:
                senders.append(entry['sender-2'])

            if entry['sender-2'] not in unique_senders and len(entry['sender-2']):
                unique_senders.append(entry['sender-2'])

            recipients = [entry['recipient-1']]

            if entry['recipient-1'] not in unique_recipients and len(entry['recipient-1']):
                unique_recipients.append(entry['recipient-1'])

            if entry['recipient-2']:
                recipients.append(entry['recipient-2'])

            if entry['recipient-2'] not in unique_recipients and len(entry['recipient-2']):
                unique_recipients.append(entry['recipient-2'])

            if entry['sender-placeName'] not in unique_sender_places and len(entry['sender-placeName']):
                unique_sender_places.append(entry['sender-placeName'])

            if entry['recipient-placeName'] not in unique_recipient_places and len(entry['recipient-placeName']):
                unique_recipient_places.append(entry['recipient-placeName'])

            result = {
                'xml_id': entry['xml-id'],
                'lfdnr': entry['lfdnr'],
                'status': entry['auswahl'],
                'senders': senders,
                'recipients': recipients,
                'placename_sent': entry['sender-placeName'],
                'placename_received': entry['recipient-placeName'],
                'date_cert': entry['date-cert'],
                'date_from': entry['date-from'],
                'date_to': entry['date-to'],
                'date_not_before': entry['date-notBefore'],
                'date_not_after': entry['date-notAfter'],
                'incipit': entry['incipit'],
                'scope': entry['scope'],
                'reference': entry['Handschrift- oder Abschriftennachweis'],
                'print_reference': entry['Drucknachweis']
            }

            results.append(result)

        unique_senders.sort()
        unique_recipients.sort()
        unique_sender_places.sort()
        unique_recipient_places.sort()

    return {
        'letters': results,
        'unique_senders': unique_senders,
        'unique_recipients': unique_recipients,
        'unique_sender_places': unique_sender_places,
        'unique_recipient_places': unique_recipient_places
    }


