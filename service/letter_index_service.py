import csv
import os
from fixtures.aufbewahrungsorte import aufbewahrungsorte

def parse_gesamtdatenbank():
    unique_senders = []
    unique_recipients = []
    unique_sender_places = []
    unique_recipient_places = []
    unique_years = []
    results = []
    date_earliest = ''
    date_latest = ''
    index = 0
    with open(os.path.dirname(__file__) + '/../data/gesamtdatenbank.csv', encoding='utf-8') as csvfile:
        csvreader = csv.DictReader(csvfile, delimiter=';')

        for entry in csvreader:
            if not len(entry['sender-1']) and not len(entry['recipient-1']):
                continue

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


            relevant_years = []
            date_earliest_candidates = []
            if entry['date-when'].startswith('1'):
                date_earliest_candidates.append(entry['date-when'])

            if entry['date-from'].startswith('1'):
                date_earliest_candidates.append(entry['date-from'])

            if entry['date-notBefore'].startswith('1'):
                date_earliest_candidates.append(entry['date-notBefore'])

            for date in date_earliest_candidates:
                year = date.split('-')[0]
                if year not in unique_years:
                    unique_years.append(year)

                if year not in relevant_years:
                    relevant_years.append(year)


            if len(date_earliest_candidates):
                date_earliest_candidate = min(date_earliest_candidates)

                if date_earliest_candidate and not date_earliest:
                    date_earliest = date_earliest_candidate

                date_earliest = min([date_earliest, date_earliest_candidate])


            date_latest_candidates = []

            if entry['date-when'].startswith('1'):
                date_latest_candidates.append(entry['date-when'])

            if entry['date-when'].startswith('0'):
                relevant_years.append(entry['date-when'].split('-')[0])

            if entry['date-to'].startswith('1'):
                date_latest_candidates.append(entry['date-to'])

            if entry['date-notAfter'].startswith('1'):
                date_latest_candidates.append(entry['date-notAfter'])

            for date in date_latest_candidates:
                year = date.split('-')[0]
                if year not in unique_years:
                    unique_years.append(year)

            if len(date_latest_candidates):
                date_latest_candidate = min(date_latest_candidates)

                if date_latest_candidate and not date_latest:
                    date_latest = date_latest_candidate

                if year not in relevant_years:
                    relevant_years.append(year)

                date_latest = max([date_latest, date_latest_candidate])

            date_index_hierarchy = ['date-when', 'date-to', 'date-notAfter', 'date-notBefore']
            date_index = None
            for hierarchy_step in date_index_hierarchy:
                if not date_index:
                    date_index = entry[hierarchy_step].strip() if (len(entry[hierarchy_step].strip())) else None

            if not date_index:
                date_index = '0000-00-00'

            ## Ensure that it will be sorted at end of year
            date_index = date_index.replace('-00', '-99').replace('0000', '9999')

            result = {
                'index': index,
                'xml_id': entry['xml-id'],
                'lfdnr': entry['lfdnr'],
                'date_index': date_index,
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
                'relevant_years': relevant_years,
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
        unique_years.sort()
        unique_years.append("0000")

        letters = sorted(results, key=lambda d: d['date_index'])

    return {
        'letters': letters,
        'unique_senders': unique_senders,
        'unique_recipients': unique_recipients,
        'unique_sender_places': unique_sender_places,
        'unique_recipient_places': unique_recipient_places,
        'unique_years': unique_years,
        'aufbewahrungsorte_short': aufbewahrungsorte,
        'date_earliest': date_earliest,
        'date_latest': date_latest
    }


