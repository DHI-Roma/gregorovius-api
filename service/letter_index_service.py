import csv
import os
from fixtures.aufbewahrungsorte import aufbewahrungsorte

def parse_gesamtdatenbank():
    unique_senders = []
    unique_recipients = []
    unique_sender_places = []
    unique_recipient_places = []
    results = []
    date_earliest = ''
    date_latest = ''
    index = 0
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


            date_earliest_candidates = []
            if entry['date-when'].startswith('1'):
                date_earliest_candidates.append(entry['date-when'])

            if entry['date-from'].startswith('1'):
                date_earliest_candidates.append(entry['date-from'])

            if entry['date-notBefore'].startswith('1'):
                date_earliest_candidates.append(entry['date-notBefore'])


            if len(date_earliest_candidates):
                date_earliest_candidate = min(date_earliest_candidates)

                if date_earliest_candidate and not date_earliest:
                    date_earliest = date_earliest_candidate

                date_earliest = min([date_earliest, date_earliest_candidate])


            date_latest_candidates = []

            if entry['date-when'].startswith('1'):
                date_latest_candidates.append(entry['date-when'])

            if entry['date-to'].startswith('1'):
                date_latest_candidates.append(entry['date-to'])

            if entry['date-notAfter'].startswith('1'):
                date_latest_candidates.append(entry['date-notAfter'])

            if len(date_latest_candidates):
                date_latest_candidate = min(date_latest_candidates)

                if date_latest_candidate and not date_latest:
                    date_latest = date_latest_candidate

                date_latest = max([date_latest, date_latest_candidate])

            result = {
                'index': index,
                'xml_id': entry['xml-id'],
                'lfdnr': entry['lfdnr'],
                'status': entry['auswahl'],
                'senders': senders,
                'recipients': recipients,
                'placename_sent': entry['sender-placeName'],
                'placename_received': entry['recipient-placeName'],
                'date_cert': entry['date-cert'],
                'date_from': entry['date-from'] if len(entry['date-from']) > 0 else None,
                'date_to': entry['date-to'] if len(entry['date-to']) > 0 else None,
                'date_not_before': entry['date-notBefore'] if len(entry['date-notBefore']) > 0 else None,
                'date_not_after': entry['date-notAfter'] if len(entry['date-notAfter']) > 0 else None,
                'date_when':entry['date-when'].strip() if len(entry['date-when'].strip()) > 0 else None,
                'incipit': entry['incipit'],
                'scope': entry['Umfang'],
                'reference': entry['Handschrift- oder Abschriftennachweis'],
                'print_reference': entry['Drucknachweis'],
            }

            results.append(result)
            index += 1

        unique_senders.sort()
        unique_recipients.sort()
        unique_sender_places.sort()
        unique_recipient_places.sort()

    return {
        'letters': results,
        'unique_senders': unique_senders,
        'unique_recipients': unique_recipients,
        'unique_sender_places': unique_sender_places,
        'unique_recipient_places': unique_recipient_places,
        'aufbewahrungsorte_short': aufbewahrungsorte,
        'date_earliest': date_earliest,
        'date_latest': date_latest
    }


